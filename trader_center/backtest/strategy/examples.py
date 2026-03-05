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
        self._log_daily_state()
        
        if not self.position:
            if self.crossover > 0:
                self.log_signal(
                    signal_type='buy',
                    data=self.data,
                    trigger_condition=f'SMA金叉: 快线{self.sma_fast[0]:.2f} > 慢线{self.sma_slow[0]:.2f}',
                    indicator_values={
                        'sma_fast': self.sma_fast[0],
                        'sma_slow': self.sma_slow[0],
                        'close': self.data.close[0],
                        'crossover': self.crossover[0],
                    },
                    confidence=0.8,
                    target_price=self.data.close[0] * 1.1,
                    stop_loss=self.data.close[0] * 0.95,
                )
                self.buy()
        else:
            if self.crossover < 0:
                self.log_signal(
                    signal_type='sell',
                    data=self.data,
                    trigger_condition=f'SMA死叉: 快线{self.sma_fast[0]:.2f} < 慢线{self.sma_slow[0]:.2f}',
                    indicator_values={
                        'sma_fast': self.sma_fast[0],
                        'sma_slow': self.sma_slow[0],
                        'close': self.data.close[0],
                        'crossover': self.crossover[0],
                    },
                    confidence=0.8,
                )
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
        self._log_daily_state()
        
        if not self.position:
            if self.rsi < self.p.oversold:
                self.log_signal(
                    signal_type='buy',
                    data=self.data,
                    trigger_condition=f'RSI超卖: {self.rsi[0]:.1f} < {self.p.oversold}',
                    indicator_values={
                        'rsi': self.rsi[0],
                        'close': self.data.close[0],
                    },
                    confidence=min(1.0, (self.p.oversold - self.rsi[0]) / self.p.oversold + 0.5),
                    target_price=self.data.close[0] * 1.15,
                    stop_loss=self.data.close[0] * 0.92,
                )
                self.buy()
        else:
            if self.rsi > self.p.overbought:
                self.log_signal(
                    signal_type='sell',
                    data=self.data,
                    trigger_condition=f'RSI超买: {self.rsi[0]:.1f} > {self.p.overbought}',
                    indicator_values={
                        'rsi': self.rsi[0],
                        'close': self.data.close[0],
                    },
                    confidence=min(1.0, (self.rsi[0] - self.p.overbought) / (100 - self.p.overbought) + 0.5),
                )
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
        self._log_daily_state()
        
        if not self.bought:
            self.log_signal(
                signal_type='buy',
                data=self.data,
                trigger_condition='买入持有策略初始建仓',
                indicator_values={
                    'close': self.data.close[0],
                },
                confidence=1.0,
            )
            self.order_target_percent(target=0.99)
            self.bought = True
