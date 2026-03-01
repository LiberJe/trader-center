"""增强型双均线交叉策略."""

import backtrader as bt


class SmaCrossEnhanced(bt.Strategy):
    """增强型双均线交叉策略.

    功能特性:
    - 双均线交叉信号（金叉买入、死叉卖出）
    - ADX趋势过滤（只在强趋势时交易）
    - 多时间周期趋势确认
    - 基于ATR的动态仓位管理
    - 基于ATR的止损止盈

    Params:
        fast_period: 短期均线周期 (默认 5)
        slow_period: 长期均线周期 (默认 20)
        use_adx_filter: 是否使用ADX过滤 (默认 True)
        adx_period: ADX周期 (默认 14)
        adx_threshold: ADX阈值 (默认 25)
        use_trend_confirm: 是否使用趋势确认 (默认 True)
        trend_ma_period: 大趋势均线周期 (默认 60)
        use_volatility_sizing: 是否使用波动率仓位管理 (默认 True)
        atr_period: ATR周期 (默认 14)
        risk_per_trade: 单笔交易风险比例 (默认 0.02)
        max_position_pct: 最大仓位比例 (默认 0.5)
        use_stop_loss: 是否使用止损 (默认 True)
        stop_loss_atr_mult: 止损ATR倍数 (默认 2.0)
        use_trailing_stop: 是否使用移动止损 (默认 False)
    """

    params = (
        ('fast_period', 5),
        ('slow_period', 20),
        ('use_adx_filter', True),
        ('adx_period', 14),
        ('adx_threshold', 25),
        ('use_trend_confirm', True),
        ('trend_ma_period', 60),
        ('use_volatility_sizing', True),
        ('atr_period', 14),
        ('risk_per_trade', 0.02),
        ('max_position_pct', 0.5),
        ('use_stop_loss', True),
        ('stop_loss_atr_mult', 2.0),
        ('use_trailing_stop', False),
    )

    def __init__(self):
        """初始化指标."""
        # 基础均线
        self.fast_ma = bt.ind.SMA(period=self.p.fast_period)
        self.slow_ma = bt.ind.SMA(period=self.p.slow_period)

        # 交叉信号
        self.crossover = bt.ind.CrossOver(self.fast_ma, self.slow_ma)

        # ADX趋势过滤
        if self.p.use_adx_filter:
            self.adx = bt.ind.AverageDirectionalMovementIndex(
                period=self.p.adx_period
            )

        # 大趋势确认
        if self.p.use_trend_confirm:
            self.trend_ma = bt.ind.SMA(period=self.p.trend_ma_period)

    def next(self):
        """每个bar执行一次."""
        pass

    def notify_order(self, order):
        """订单状态回调."""
        pass
