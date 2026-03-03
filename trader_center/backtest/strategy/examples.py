"""
示例策略

提供几个常用的示例策略作为参考和测试。
"""

import backtrader as bt
from .base import BaseStrategy


class SmaCrossStrategy(BaseStrategy):
    """
    双均线交叉策略

    当短期均线上穿长期均线时买入，下穿时卖出。

    Params:
        fast: 短期均线周期（默认5日）
        slow: 长期均线周期（默认20日）
    """

    name = "sma_cross"
    description = "双均线交叉策略"

    params = (
        ('fast', 5),
        ('slow', 20),
    )

    def __init__(self):
        super().__init__()
        self.sma_fast = bt.indicators.SMA(period=self.p.fast)
        self.sma_slow = bt.indicators.SMA(period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        # 无持仓时，金叉买入
        if not self.position:
            if self.crossover > 0:
                self.log(f"金叉买入，价格: {self.data.close[0]:.2f}")
                self.buy()
        # 有持仓时，死叉卖出
        else:
            if self.crossover < 0:
                self.log(f"死叉卖出，价格: {self.data.close[0]:.2f}")
                self.sell()


class RsiStrategy(BaseStrategy):
    """
    RSI 策略

    RSI < 30 超卖买入，RSI > 70 超买卖出。

    Params:
        period: RSI周期（默认14日）
        oversold: 超卖阈值（默认30）
        overbought: 超买阈值（默认70）
    """

    name = "rsi"
    description = "RSI超买超卖策略"

    params = (
        ('period', 14),
        ('oversold', 30),
        ('overbought', 70),
    )

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(period=self.p.period)

    def next(self):
        if not self.position:
            if self.rsi < self.p.oversold:
                self.log(f"RSI超卖买入: {self.rsi[0]:.1f}")
                self.buy()
        else:
            if self.rsi > self.p.overbought:
                self.log(f"RSI超买卖出: {self.rsi[0]:.1f}")
                self.sell()


class BuyAndHoldStrategy(BaseStrategy):
    """
    买入持有策略（基准策略）

    第一天买入，持有到期末。
    """

    name = "buy_and_hold"
    description = "买入持有基准策略"

    def __init__(self):
        super().__init__()
        self.bought = False

    def next(self):
        if not self.bought:
            self.log(f"买入持有: {self.data.close[0]:.2f}")
            self.order_target_percent(target=0.99)  # 99%仓位
            self.bought = True
