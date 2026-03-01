"""Backtest engine - core wrapper around backtrader."""

import backtrader as bt
import pandas as pd
from typing import Any, Dict, Optional, Type
from datetime import datetime

from .data_feed import PandasDataFeed
from .metrics import calculate_metrics
from .result import BacktestResult


class TradeRecorder(bt.Analyzer):
    """记录每笔交易的分析器."""

    def __init__(self):
        self.trades = []

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append({
                'ref': trade.ref,
                'datetime': trade.data.datetime.datetime(0),
                'size': trade.size,
                'price': trade.price,
                'value': trade.value,
                'commission': trade.commission,
                'pnl': trade.pnl,
                'pnlcomm': trade.pnlcomm,
            })

    def get_analysis(self):
        return self.trades


class DailyValueRecorder(bt.Analyzer):
    """记录每日资金曲线的分析器."""

    def __init__(self):
        self.values = []
        self.dates = []

    def next(self):
        self.values.append(self.strategy.broker.getvalue())
        self.dates.append(self.data.datetime.datetime(0))

    def get_analysis(self):
        return {'dates': self.dates, 'values': self.values}


class BacktestEngine:
    """回测引擎 - backtrader 的统一封装.

    使用示例:
        engine = BacktestEngine(initial_cash=100000, commission=0.0003)
        result = engine.run(data=df, strategy=MyStrategy, params=dict(fast=5, slow=20))
        print(result.report())
    """

    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission: float = 0.0003,
        slippage: float = 0.0,
        stake: int = 100,
        cheat_on_open: bool = False
    ):
        """初始化回测引擎.

        Args:
            initial_cash: 初始资金
            commission: 手续费率 (默认 0.03%)
            slippage: 滑点 (默认 0)
            stake: 每笔交易股数
            cheat_on_open: 是否允许开盘价成交
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.stake = stake
        self.cheat_on_open = cheat_on_open

    def run(
        self,
        data: pd.DataFrame,
        strategy: Type[bt.Strategy],
        params: Optional[Dict[str, Any]] = None,
        indicators: Optional[list] = None
    ) -> BacktestResult:
        """运行回测.

        Args:
            data: DataHub 提供的 DataFrame (必需包含 open/high/low/close/volume 列)
            strategy: backtrader Strategy 类
            params: 策略参数字典
            indicators: 要添加到绘图的指标列表

        Returns:
            BacktestResult 包含完整的回测结果
        """
        # 验证数据
        PandasDataFeed.validate_dataframe(data)

        # 创建 Cerebro 引擎
        cerebro = bt.Cerebro()

        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)

        # 设置手续费
        cerebro.broker.setcommission(commission=self.commission)

        # 设置滑点
        if self.slippage > 0:
            cerebro.broker.set_slippage_perc(self.slippage)

        # 设置 sizer
        cerebro.addsizer(bt.sizers.FixedSize, stake=self.stake)

        # 添加数据
        data_feed = PandasDataFeed(dataname=data)
        cerebro.adddata(data_feed)

        # 添加策略
        strat_params = params or {}
        cerebro.addstrategy(strategy, **strat_params)

        # 添加分析器
        cerebro.addanalyzer(TradeRecorder, _name='trade_recorder')
        cerebro.addanalyzer(DailyValueRecorder, _name='value_recorder')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        # 运行回测
        results = cerebro.run(cheat_on_open=self.cheat_on_open)
        strat = results[0]

        # 提取分析结果
        trade_recorder = strat.analyzers.trade_recorder.get_analysis()
        value_recorder = strat.analyzers.value_recorder.get_analysis()

        # 构建结果 DataFrame
        trades_df = pd.DataFrame(trade_recorder)

        daily_values = pd.DataFrame({
            'value': value_recorder['values']
        }, index=value_recorder['dates'])

        # 计算指标
        metrics = calculate_metrics(daily_values)

        # 补充 backtrader 计算的指标
        drawdown = strat.analyzers.drawdown.get_analysis()
        returns = strat.analyzers.returns.get_analysis()

        metrics['max_drawdown'] = drawdown.get('max', {}).get('drawdown', 0) / 100
        metrics['max_drawdown_pct'] = drawdown.get('max', {}).get('drawdown', 0)
        metrics['max_drawdown_len'] = drawdown.get('max', {}).get('len', 0)

        # 构建结果对象
        start_date = daily_values.index[0]
        end_date = daily_values.index[-1]
        duration = end_date - start_date

        # 构建持仓 DataFrame (简化版)
        positions_df = pd.DataFrame()  # 可以后续扩展

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            duration=duration,
            metrics=metrics,
            trades=trades_df,
            daily_values=daily_values,
            positions=positions_df
        )
