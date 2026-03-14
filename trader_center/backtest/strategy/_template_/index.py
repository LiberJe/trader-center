"""
策略名称

策略简短描述...
"""

import backtrader as bt
from trader_center.backtest.strategy.base import BaseStrategy


class TemplateStrategy(BaseStrategy):
    """
    策略中文名称

    策略逻辑详细描述...

    买入条件:
    1. 条件1
    2. 条件2

    卖出条件:
    1. 条件1
    2. 条件2

    Params:
        param1: 参数1说明（默认10）
        param2: 参数2说明（默认0.5）
    """

    name = "template_strategy"
    description = "策略简短描述"

    params = (
        ('param1', 10),
        ('param2', 0.5),
    )

    def __init__(self):
        super().__init__()
        # 初始化技术指标
        # self.sma = bt.indicators.SMA(period=self.p.param1)

    def next(self):
        self._log_daily_state()

        # 没有持仓时的逻辑
        if not self.position:
            if self._should_buy():
                self.log_signal(
                    signal_type='buy',
                    data=self.data,
                    trigger_condition='买入触发条件描述',
                    indicator_values={
                        'close': self.data.close[0],
                        # 'indicator': self.sma[0],
                    },
                    confidence=0.8,
                    target_price=self.data.close[0] * 1.1,
                    stop_loss=self.data.close[0] * 0.95,
                )
                self.buy()
        else:
            # 有持仓时的逻辑
            if self._should_sell():
                self.log_signal(
                    signal_type='sell',
                    data=self.data,
                    trigger_condition='卖出触发条件描述',
                    indicator_values={
                        'close': self.data.close[0],
                        # 'indicator': self.sma[0],
                    },
                    confidence=0.8,
                )
                self.sell()

    def _should_buy(self) -> bool:
        """判断是否应该买入"""
        # 实现买入逻辑
        return False

    def _should_sell(self) -> bool:
        """判断是否应该卖出"""
        # 实现卖出逻辑
        return False
