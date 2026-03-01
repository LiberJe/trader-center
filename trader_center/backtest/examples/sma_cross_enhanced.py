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

        # ATR用于仓位管理和止损
        if self.p.use_volatility_sizing or self.p.use_stop_loss:
            self.atr = bt.ind.ATR(period=self.p.atr_period)

        # 状态变量
        self.entry_price = None
        self.stop_price = None
        self.stop_order = None

    def next(self):
        """每个bar执行一次."""
        # 没有持仓时，检查入场条件
        if not self.position:
            if self._can_enter_long():
                size = self._calculate_position_size()
                if size:
                    self.buy(size=size)
                else:
                    self.buy()
        else:
            # 有持仓时，更新移动止损
            if self.p.use_trailing_stop:
                self._update_trailing_stop()

            # 检查止损或死叉出场
            should_exit = False

            # 死叉信号
            if self.crossover[0] < 0:
                should_exit = True

            # 止损触发
            if self._check_stop_exit():
                should_exit = True

            # 趋势反转出场（价格跌破大趋势MA）
            if self.p.use_trend_confirm and hasattr(self, 'trend_ma'):
                if self.data.close[0] < self.trend_ma[0]:
                    should_exit = True

            if should_exit:
                self.close()

    def _can_enter_long(self):
        """检查是否可以开多仓.

        条件:
        1. 金叉信号
        2. ADX > 阈值（如果启用ADX过滤）
        3. 价格在大趋势MA之上（如果启用趋势确认）
        """
        # 必须有金叉信号
        if self.crossover[0] <= 0:
            return False

        # ADX过滤
        if self.p.use_adx_filter:
            if not hasattr(self, 'adx') or self.adx[0] <= self.p.adx_threshold:
                return False

        # 趋势确认
        if self.p.use_trend_confirm:
            if not hasattr(self, 'trend_ma') or self.data.close[0] <= self.trend_ma[0]:
                return False

        return True

    def _calculate_position_size(self):
        """计算仓位大小.

        基于ATR的仓位管理:
        仓位 = (资金 × 风险比例) / (ATR × 止损倍数)
        """
        if not self.p.use_volatility_sizing:
            return None  # 使用默认仓位

        cash = self.broker.getcash()
        price = self.data.close[0]

        if not hasattr(self, 'atr') or self.atr[0] == 0:
            return None

        # 计算风险金额
        risk_amount = cash * self.p.risk_per_trade

        # 计算止损距离
        stop_distance = self.atr[0] * self.p.stop_loss_atr_mult

        # 计算仓位
        position_size = risk_amount / stop_distance

        # 应用最大仓位限制
        max_position_value = cash * self.p.max_position_pct
        max_position_size = max_position_value / price

        return int(min(position_size, max_position_size))

    def _calculate_stop_price(self, entry_price):
        """计算止损价格."""
        if not self.p.use_stop_loss:
            return None

        if not hasattr(self, 'atr') or self.atr[0] == 0:
            return None

        stop_distance = self.atr[0] * self.p.stop_loss_atr_mult
        return entry_price - stop_distance

    def _update_trailing_stop(self):
        """更新移动止损价格."""
        if not self.p.use_trailing_stop or self.stop_price is None:
            return

        if not hasattr(self, 'atr') or self.atr[0] == 0:
            return

        # 新高时提高止损
        new_stop = self.data.close[0] - self.atr[0] * self.p.stop_loss_atr_mult
        if new_stop > self.stop_price:
            self.stop_price = new_stop

    def _check_stop_exit(self):
        """检查是否触发止损出场."""
        if self.stop_price is None:
            return False

        if self.data.close[0] <= self.stop_price:
            return True

        return False

    def notify_order(self, order):
        """订单状态回调.

        记录入场价格和设置止损价。
        """
        if order.status in [order.Completed]:
            if order.isbuy():
                # 记录入场价格
                self.entry_price = order.executed.price
                # 计算止损价格
                self.stop_price = self._calculate_stop_price(self.entry_price)
            elif order.issell():
                # 重置状态
                self.entry_price = None
                self.stop_price = None
