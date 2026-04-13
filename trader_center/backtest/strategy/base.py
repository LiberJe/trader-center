"""
策略基类

封装 backtrader 的 bt.Strategy，添加 A股特性和日志功能。
"""

import backtrader as bt
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import logging

from trader_center.backtest.trade_logger import TradeLogger


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

        self.trade_logger = TradeLogger(self.name)

        self.orders: List[bt.Order] = []
        self.trades: List[Dict[str, Any]] = []
        self.closed_trades: List[Dict[str, Any]] = []
        self._trade_records: List[Dict[str, Any]] = []  # 手动计算的交易闭环盈亏
        self._position_lots: Dict[str, List[Dict[str, Any]]] = {}  # 按标的记录的买入批次(FIFO)

        self._buy_dates: Dict[str, datetime] = {}
        self._order_id_map: Dict[int, str] = {}
        self._position_entry_dates: Dict[str, date] = {}
        self._last_capital_date: Optional[date] = None
        self._last_total_value: Optional[float] = None

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

    def log_signal(
        self,
        signal_type: str,
        data: Optional[bt.DataBase] = None,
        trigger_condition: str = "",
        indicator_values: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ):
        """
        记录交易信号

        Args:
            signal_type: 信号类型 ('buy' / 'sell')
            data: 数据对象，默认使用第一个数据
            trigger_condition: 触发条件描述
            indicator_values: 指标值快照
            confidence: 信号强度 (0-1)
            target_price: 目标价格
            stop_loss: 止损价
            take_profit: 止盈价
        """
        data = data or self.datas[0]
        symbol = data._name if hasattr(data, '_name') else 'unknown'
        dt = data.datetime.datetime(0)
        
        self.trade_logger.log_signal(
            signal_type=signal_type,
            symbol=symbol,
            trigger_condition=trigger_condition,
            indicator_values=indicator_values or {},
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            dt=dt,
        )
        
        self.log(f"信号 [{signal_type.upper()}] {symbol}: {trigger_condition}")

    def log_daily_capital(self):
        """
        记录每日资金状态

        在 next() 中调用，记录当天的资金快照。
        """
        current_date = self.datas[0].datetime.date(0)
        
        if self._last_capital_date == current_date:
            return
        
        cash = self.broker.getcash()
        total_value = self.broker.getvalue()
        position_value = total_value - cash
        
        daily_pnl = 0.0
        if self._last_total_value is not None:
            daily_pnl = total_value - self._last_total_value
        
        self.trade_logger.log_capital(
            log_date=current_date,
            cash=cash,
            position_value=position_value,
            total_value=total_value,
            daily_pnl=daily_pnl,
        )
        
        self._last_capital_date = current_date
        self._last_total_value = total_value

    def log_daily_positions(self):
        """
        记录每日持仓状态

        在 next() 中调用，记录当天的持仓详情。
        """
        current_date = self.datas[0].datetime.date(0)
        
        for data in self.datas:
            symbol = data._name if hasattr(data, '_name') else 'unknown'
            position = self.getposition(data)
            
            if position.size == 0:
                continue
            
            cost_price = position.price
            current_price = data.close[0]
            size = int(position.size)
            
            holding_days = 0
            if symbol in self._position_entry_dates:
                entry_date = self._position_entry_dates[symbol]
                holding_days = (current_date - entry_date).days
            
            self.trade_logger.log_position(
                log_date=current_date,
                symbol=symbol,
                size=size,
                cost_price=cost_price,
                current_price=current_price,
                holding_days=holding_days,
            )

    def notify_order(self, order: bt.Order):
        """
        订单状态通知回调

        子类可重写此方法处理订单状态变化。

        Args:
            order: backtrader Order 对象
        """
        symbol = order.data._name if hasattr(order.data, '_name') else 'unknown'
        action = 'buy' if order.isbuy() else 'sell'
        dt = self.datas[0].datetime.datetime(0)
        order_key = str(order.ref)

        if order.status == order.Submitted:
            if order_ref not in self._order_id_map:
                order_log = self.trade_logger.log_order_submit(
                    symbol=symbol,
                    action=action,
                    expected_price=order.created.price if order.created.price > 0 else self.datas[0].close[0],
                    expected_size=int(abs(order.created.size)),
                    order_type='limit' if order.exectype == bt.Order.Limit else 'market',
                    dt=dt,
                )
                self._order_id_map[order_ref] = order_log.order_id
            return

        if order.status == order.Accepted:
            return

        if order.status == order.Completed:
            self.log(
                f"订单成交 {action}: 价格={order.executed.price:.2f}, "
                f"数量={order.executed.size}, "
                f"金额={order.executed.value:.2f}, "
                f"手续费={order.executed.comm:.2f}"
            )

            exec_size = int(abs(order.executed.size))
            exec_price = order.executed.price

            # 记录逐笔订单
            self.trades.append({
                'date': self.datas[0].datetime.date(0),
                'action': action,
                'price': exec_price,
                'size': exec_size,
                'value': order.executed.value,
                'commission': order.executed.comm,
                'symbol': symbol,
            })

            if order_ref in self._order_id_map:
                self.trade_logger.log_order_status(
                    order_id=self._order_id_map[order_ref],
                    status='completed',
                    executed_price=exec_price,
                    executed_size=exec_size,
                    commission=order.executed.comm,
                )

            if order.isbuy():
                self._buy_dates[symbol] = self.datas[0].datetime.date(0)
                self._position_entry_dates[symbol] = self.datas[0].datetime.date(0)
                # 记录买入批次用于FIFO盈亏计算
                self._position_lots.setdefault(symbol, []).append({
                    'price': exec_price,
                    'size': exec_size,
                })
            else:
                # 卖出时按FIFO计算闭环交易盈亏
                sell_size = exec_size
                sell_price = exec_price
                lots = self._position_lots.get(symbol, [])
                total_commission = order.executed.comm

                while sell_size > 0 and lots:
                    lot = lots[0]
                    matched_size = min(sell_size, lot['size'])
                    cost = matched_size * lot['price']
                    revenue = matched_size * sell_price
                    pnl = revenue - cost
                    # 将佣金按比例分摊到各笔记录（简化处理）
                    comm_share = total_commission * (matched_size / exec_size) if exec_size > 0 else 0
                    pnlcomm = pnl - comm_share

                    self._trade_records.append({
                        'date': self.datas[0].datetime.date(0),
                        'symbol': symbol,
                        'size': matched_size,
                        'buy_price': lot['price'],
                        'sell_price': sell_price,
                        'pnl': pnl,
                        'pnlcomm': pnlcomm,
                        'commission': comm_share,
                    })

                    sell_size -= matched_size
                    lot['size'] -= matched_size
                    if lot['size'] <= 0:
                        lots.pop(0)

                if sell_size > 0:
                    self.log(f"警告: 卖出数量超过已记录持仓 {symbol} 剩余{sell_size}股")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            status_name = {
                order.Canceled: 'canceled',
                order.Margin: 'margin',
                order.Rejected: 'rejected',
            }.get(order.status, 'unknown')

            self.log(f"订单失败: {status_name}")

            if order_ref in self._order_id_map:
                self.trade_logger.log_order_status(
                    order_id=self._order_id_map[order_ref],
                    status=status_name,
                    message=f"Order {status_name}",
                )

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

    def _log_daily_state(self):
        """
        记录每日状态（资金和持仓）

        子类可以在 next() 方法中调用此方法来自动记录每日状态。
        """
        self.log_daily_capital()
        self.log_daily_positions()

    def next(self):
        """
        逐 K 线执行

        子类必须重写此方法实现策略逻辑。
        建议在子类的 next() 方法开头调用 self._log_daily_state() 来记录每日状态。
        """
        raise NotImplementedError("子类必须实现 next() 方法")

    def stop(self):
        """回测结束时调用"""
        self._log_daily_state()
        
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
        # 优先使用手动计算的闭环交易记录（适配始终持仓策略）
        trades_source = self._trade_records if self._trade_records else self.closed_trades
        return pd.DataFrame(trades_source) if trades_source else pd.DataFrame()
