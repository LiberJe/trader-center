"""Simple Moving Average Crossover Strategy."""

import backtrader as bt


class SmaCross(bt.Strategy):
    """双均线交叉策略.

    当短期均线上穿长期均线时买入，下穿时卖出。

    Params:
        fast: 短期均线周期 (默认 5)
        slow: 长期均线周期 (默认 20)
    """
    params = (
        ('fast', 5),
        ('slow', 20),
    )

    def __init__(self):
        """初始化指标."""
        self.fast_ma = bt.ind.SMA(period=self.p.fast)
        self.slow_ma = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        """每个 bar 执行一次."""
        # 没有持仓时
        if not self.position:
            # 金叉买入
            if self.crossover > 0:
                self.buy()
        # 有持仓时
        else:
            # 死叉卖出
            if self.crossover < 0:
                self.sell()

    def notify_order(self, order):
        """订单状态回调."""
        if order.status in [order.Completed]:
            if order.isbuy():
                pass  # 可以添加日志
            elif order.issell():
                pass
