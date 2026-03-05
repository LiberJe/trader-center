"""
策略基类

封装 backtrader 的 bt.Strategy，添加 A股特性和日志功能。
"""

import backtrader as bt
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging


class BaseStrategy(bt.Strategy):
    """
    A股策略基类

    封装 backtrader 原生 Strategy，添加：
    - 统一日志记录
    - A股交易限制检查
    - 订单跟踪
    - 独立账户支持

    Attributes:
        name: 策略名称（类属性，必须设置）
        description: 策略描述（类属性）

    Example:
        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            description = "我的策略"

            params = (('period', 20),)

            def __init__(self):
                super().__init__()
                self.sma = bt.indicators.SMA(period=self.p.period)

            def next(self):
                if self.sma > self.data.close:
                    self.buy()
    """

    # 类属性，子类必须设置
    name: str = "base"
    description: str = ""

    # backtrader params
    params = ()

    def __init__(self):
        """初始化策略"""
        super().__init__()
        self.logger = logging.getLogger(f"backtest.strategy.{self.name}")

        # 订单跟踪
        self.orders: List[bt.Order] = []
        # 交易记录（订单级别）
        self.trades: List[Dict[str, Any]] = []
        # 交易闭环记录（包含 pnl）
        self.closed_trades: List[Dict[str, Any]] = []

        # 持仓信息（用于T+1检查）
        self._buy_dates: Dict[str, datetime] = {}

    def log(self, txt: str, dt: Optional[datetime] = None):
        """
        记录日志

        Args:
            txt: 日志内容
            dt: 日期时间，默认使用当前数据日期
        """
        dt = dt or self.datas[0].datetime.date(0)
        msg = f"[{dt.isoformat()}] {txt}"
        self.logger.info(msg)

    def notify_order(self, order: bt.Order):
        """
        订单状态通知回调

        子类可重写此方法处理订单状态变化。

        Args:
            order: backtrader Order 对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            action = "买入" if order.isbuy() else "卖出"
            self.log(
                f"订单成交 {action}: 价格={order.executed.price:.2f}, "
                f"数量={order.executed.size}, "
                f"金额={order.executed.value:.2f}, "
                f"手续费={order.executed.comm:.2f}"
            )

            # 记录交易
            self.trades.append({
                'date': self.datas[0].datetime.date(0),
                'action': 'buy' if order.isbuy() else 'sell',
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm,
            })

            # 记录买入日期（用于T+1检查）
            if order.isbuy():
                symbol = order.data._name
                self._buy_dates[symbol] = self.datas[0].datetime.date(0)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单失败: {order.status}")

        # 从跟踪列表中移除已完成/失败的订单
        if order in self.orders:
            self.orders.remove(order)

    def notify_trade(self, trade: bt.Trade):
        """
        交易通知回调

        Args:
            trade: backtrader Trade 对象
        """
        if not trade.isclosed:
            return

        # 记录交易闭环（包含 pnl）
        self.closed_trades.append({
            'date': self.datas[0].datetime.date(0),
            'symbol': trade.data._name if hasattr(trade.data, '_name') else 'unknown',
            'pnl': trade.pnl,           # 毛盈亏
            'pnlcomm': trade.pnlcomm,   # 净盈亏（扣除手续费）
            'commission': trade.commission,
        })

        self.log(
            f"交易闭环: 毛盈亏={trade.pnl:.2f}, "
            f"净盈亏={trade.pnlcomm:.2f}"
        )

    def can_sell_today(self, data: bt.DataBase) -> bool:
        """
        检查今天是否可以卖出（T+1检查）

        Args:
            data: 数据对象

        Returns:
            True 如果可以卖出
        """
        symbol = data._name
        if symbol not in self._buy_dates:
            return True  # 不是今天买的

        buy_date = self._buy_dates[symbol]
        today = data.datetime.date(0)

        return today > buy_date  # 必须是次日及以后

    def prenext(self):
        """预热期，数据不足时调用"""
        pass

    def nextstart(self):
        """第一个有完整数据的 bar"""
        pass

    def next(self):
        """
        逐 K 线执行

        子类必须重写此方法实现策略逻辑。
        """
        raise NotImplementedError("子类必须实现 next() 方法")

    def stop(self):
        """回测结束时调用"""
        # 计算并记录最终收益
        portfolio_value = self.broker.getvalue()
        cash = self.broker.getcash()
        self.log(f"回测结束: 总资产={portfolio_value:.2f}, 现金={cash:.2f}")

    def get_trades_df(self):
        """
        获取交易记录 DataFrame

        Returns:
            pandas DataFrame，包含 pnl 字段
        """
        import pandas as pd
        return pd.DataFrame(self.closed_trades) if self.closed_trades else pd.DataFrame()
