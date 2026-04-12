"""
分仓波段策略 (Band Position Strategy)

将仓位分为底仓和波段仓两部分：
- 底仓：回测开始时一次性买入并长期持有
- 波段仓：根据价格与60日均线的关系进行波段操作

策略逻辑：
1. 底仓在回测开始时一次性买入，持有至回测结束
2. 当价格跌破60日均线时，波段仓位以定投形式分批买入
3. 当价格回到60日均线以上时，波段仓位使用移动止盈逐步卖出

特殊说明：
- base_position_pct 参数控制底仓比例，设为100%时退化为买入持有策略
- band_position_pct = 100% - base_position_pct
"""

import backtrader as bt
from trader_center.backtest.strategy.base import BaseStrategy


class BandPositionStrategy(BaseStrategy):
    """
    分仓波段策略 (BIAS智能加权版)

    底仓+波段仓的组合策略：
    - 底仓：长期持有，获取市场beta收益
    - 波段仓：围绕60日均线进行高抛低吸，获取alpha收益

    买入逻辑（波段仓）：
    - 价格跌破60日均线时，触发定投买入
    - 智能加权：基于时间和跌幅双重因子动态调整加仓金额
      * 时间因子：跌破均线时间越长，加仓权重越高
      * 跌幅因子：BIAS60（乖离率）越大，加仓权重越高
    - 公式：加仓权重 = min_weight + (max_weight - min_weight) × (time_ratio × time_factor + drop_ratio × drop_factor)

    卖出逻辑（波段仓）：
    - 价格回到60日均线以上后，启用移动止盈
    - 追踪最高价，当回撤超过一定比例时卖出

    Params:
        base_position_pct: 底仓比例，默认80%，设为100%则为买入持有
        ma_period: 移动平均线周期，默认60日
        dca_batches: 定投批次，默认5次（跌破均线后将波段资金分5次投入）
        dca_interval: 定投间隔交易日数，默认5（每5个交易日定投一次）
        trailing_stop_pct: 移动止盈比例，默认5%（从最高点回撤5%卖出）

        # BIAS智能加权参数
        use_bias_weighting: 是否启用BIAS加权加仓，默认True
        min_dca_weight: 最小加仓权重，默认1.0x
        max_dca_weight: 最大加仓权重，默认3.0x
        time_decay_days: 时间衰减周期（天），默认30天
        time_factor_ratio: 时间因子占比，默认0.4（40%）
        drop_factor_ratio: 跌幅因子占比，默认0.6（60%）
        max_bias_ref: 最大参考跌幅，默认20%

        # 动态移动止盈参数
        use_dynamic_trailing_stop: 是否启用动态止盈，默认True
        trailing_tighten_bias_1: 第一档BIAS阈值，默认8%
        trailing_tighten_stop_1: 第一档回撤比例，默认2%
        trailing_tighten_bias_2: 第二档BIAS阈值，默认10%
        trailing_tighten_stop_2: 第二档回撤比例，默认1.5%
        trailing_tighten_bias_3: 第三档BIAS阈值，默认12%
        trailing_tighten_stop_3: 第三档回撤比例，默认1%

        # 移动止盈激活参数
        trailing_activation_bars: 突破确认期（交易bar数），默认3。价格上穿均线后需站稳该周期才真正启用移动止盈，避免暴跌后的假突破被立刻止盈洗出。
    """

    name = "band_position"
    description = "分仓波段策略：底仓持有+波段定投+移动止盈"

    params = (
        ('base_position_pct', 80),       # 底仓比例（%）
        ('ma_period', 60),                # 均线周期
        ('dca_batches', 5),               # 定投批次
        ('dca_interval', 5),              # 定投间隔交易日数（默认每5个交易日定投一次）
        ('dca_trigger_bias', 3.0),        # 定投触发阈值（%），BIAS60跌破该阈值才开始定投
        ('trailing_stop_pct', 5),         # 移动止盈比例（%）

        # === BIAS智能加权加仓参数（方案C：时间+跌幅双重衰减）===
        ('use_bias_weighting', True),     # 是否启用BIAS加权加仓
        ('min_dca_weight', 1.0),          # 最小加仓权重（基础倍数）
        ('max_dca_weight', 3.0),          # 最大加仓权重（最高倍数）
        ('time_decay_days', 30),          # 时间衰减周期（交易日数），达到此周期后时间因子满额
        ('time_factor_ratio', 0.4),       # 时间因子占比（0-1）
        ('drop_factor_ratio', 0.6),       # 跌幅因子占比（0-1）
        ('max_bias_ref', 20),             # 最大参考跌幅（%），BIAS达到此跌幅时跌幅因子满额

        # === 杠杆系统参数 ===
        ('max_leverage_pct', 20),         # 最大杠杆资金占初始总资金百分比
        ('leverage_interest_rate', 3.0),  # 杠杆年化利率（%）

        # === 动态移动止盈参数 ===
        ('use_dynamic_trailing_stop', True),   # 是否启用动态止盈
        ('trailing_tighten_bias_1', 8.0),      # 第一档BIAS阈值（%）
        ('trailing_tighten_stop_1', 2.0),      # 第一档回撤比例（%）
        ('trailing_tighten_bias_2', 10.0),     # 第二档BIAS阈值（%）
        ('trailing_tighten_stop_2', 1.5),      # 第二档回撤比例（%）
        ('trailing_tighten_bias_3', 12.0),     # 第三档BIAS阈值（%）
        ('trailing_tighten_stop_3', 1.0),      # 第三档回撤比例（%）

        # === 移动止盈激活参数 ===
        ('trailing_activation_bars', 3),       # 突破确认期（交易bar数），上穿均线后需站稳该时长才启用移动止盈
    )

    def __init__(self):
        super().__init__()

        # 计算波段仓位比例
        self.band_position_pct = 100 - self.p.base_position_pct

        # 60日均线指标
        self.ma60 = bt.indicators.SMA(period=self.p.ma_period)

        # 价格与均线的交叉检测
        self.price_cross_ma = bt.indicators.CrossOver(self.data.close, self.ma60)

        # 状态变量
        self.base_position_built = False      # 底仓是否已建立
        self.band_cash_available = 0          # 波段资金可用额度
        self.band_cash_per_batch = 0          # 每批定投金额
        self.band_batches_remaining = 0       # 剩余定投批次
        self.band_position_size = 0           # 当前波段仓位（股数）
        self.band_position_cost = 0           # 波段仓位成本
        self.band_highest_price = 0           # 波段持仓期间最高价（用于移动止盈）
        self.band_in_position = False         # 波段仓位是否持有中
        self.below_ma = False                 # 当前是否处于均线下方
        self.ma_breakout_since = None         # 最近一次突破60均线的日期
        self.ma_breakout_bar = None           # 最近一次突破60均线时的bar序号
        self.last_dca_bar = None              # 上次定投的bar序号（用于交易日间隔）

        # 记录底仓信息
        self.base_position_size = 0           # 底仓股数
        self.base_position_price = 0          # 底仓买入价格

        # === BIAS加权加仓状态变量 ===
        self.first_below_ma_date = None       # 首次跌破均线日期（用于时间因子计算）
        self.first_below_ma_bar = None        # 首次跌破均线时的bar序号（交易日时间因子）

        # === 杠杆系统状态变量 ===
        self.initial_total_cash = 0           # 初始总资金
        self.leverage_used = 0                # 已使用的杠杆本金
        self.leverage_available = 0           # 可用杠杆额度
        self.leverage_start_date = None       # 首次使用杠杆的日期

    def _log_daily_state(self):
        """记录每日状态，增加分仓信息"""
        super()._log_daily_state()

        if self.p.base_position_pct < 100:
            leverage_info = ""
            if self.leverage_used > 0:
                leverage_info = f" | 杠杆已用{self.leverage_used:.2f}"
            self.log(
                f'分仓状态: 底仓{self.p.base_position_pct}%({self.base_position_size}股) | '
                f'波段{self.band_position_pct}% 可用资金:{self.band_cash_available:.2f} | '
                f'波段持仓:{self.band_position_size}股 成本:{self.band_position_cost:.3f} | '
                f'60日均线:{self.ma60[0]:.3f}{leverage_info}'
            )

    def start(self):
        """回测开始时的初始化"""
        super().start()

        # 计算波段资金
        total_cash = self.broker.getcash()
        self.band_cash_available = total_cash * self.band_position_pct / 100

        # 记录初始总资金并计算杠杆额度
        self.initial_total_cash = total_cash
        self.leverage_available = self.initial_total_cash * self.p.max_leverage_pct / 100

        # 计算每批定投金额
        if self.p.dca_batches > 0:
            self.band_cash_per_batch = self.band_cash_available / self.p.dca_batches
        else:
            self.band_cash_per_batch = self.band_cash_available

        self.band_batches_remaining = self.p.dca_batches

        bias_info = ""
        if self.p.use_bias_weighting:
            bias_info = (f' | BIAS加权启用: 权重范围{self.p.min_dca_weight:.1f}x~{self.p.max_dca_weight:.1f}x | '
                        f'时间因子{self.p.time_factor_ratio:.0%} 跌幅因子{self.p.drop_factor_ratio:.0%}')

        trigger_info = f' | 定投触发阈值BIAS60<=-{self.p.dca_trigger_bias}%'

        ts_info = ""
        if self.p.use_dynamic_trailing_stop:
            ts_info = (
                f' | 动态止盈: 基础{self.p.trailing_stop_pct}% '
                f'BIAS≥{self.p.trailing_tighten_bias_1}%→{self.p.trailing_tighten_stop_1}% '
                f'≥{self.p.trailing_tighten_bias_2}%→{self.p.trailing_tighten_stop_2}% '
                f'≥{self.p.trailing_tighten_bias_3}%→{self.p.trailing_tighten_stop_3}%'
            )
        else:
            ts_info = f' | 移动止盈{self.p.trailing_stop_pct}%'
        ts_info += f' 确认期{self.p.trailing_activation_bars}bar'

        leverage_info = ""
        if self.p.max_leverage_pct > 0:
            leverage_info = f' | 杠杆额度{self.leverage_available:.2f}(利率{self.p.leverage_interest_rate:.1f}%)'

        self.log(
            f'策略启动: 总资金{total_cash:.2f} | '
            f'底仓比例{self.p.base_position_pct}% | 波段比例{self.band_position_pct}% | '
            f'波段资金{self.band_cash_available:.2f} 分{self.p.dca_batches}批投入 | '
            f'定投间隔{self.p.dca_interval}个交易日{trigger_info}{ts_info}{bias_info}{leverage_info}'
        )

    def next(self):
        self._log_daily_state()

        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)

        # ========== 第一步：建立底仓 ==========
        if not self.base_position_built:
            self._build_base_position()
            return

        # 如果底仓比例为100%，则无需波段操作
        if self.p.base_position_pct >= 100:
            return

        # ========== 第二步：更新均线状态 ==========
        prev_below_ma = self.below_ma
        self.below_ma = current_price < self.ma60[0]

        # 计算当前BIAS
        current_bias = (current_price - self.ma60[0]) / self.ma60[0] * 100

        # 检测穿越事件
        cross_above = self.price_cross_ma > 0  # 价格上穿均线
        cross_below = self.price_cross_ma < 0  # 价格下穿均线

        if cross_above:
            self.log(f'信号: 价格上穿60日均线 {current_price:.3f} > {self.ma60[0]:.3f}')
            # 突破均线后重置BIAS加仓状态，为下一次波段做准备
            self._reset_bias_state()
        if cross_below:
            self.log(f'信号: 价格下穿60日均线 {current_price:.3f} < {self.ma60[0]:.3f}')

        # 如果当前跌破均线，清除旧的移动止盈状态，防止后续几天微幅站回均线时
        # 仍用旧的高点做回撤判断而被误止盈（如2025-04暴跌反弹场景）
        if self.below_ma and self.ma_breakout_since is not None:
            self.ma_breakout_since = None
            self.ma_breakout_bar = None
            self.band_highest_price = 0
            self.log('波段: 价格跌破均线，清除移动止盈状态')

        # 兜底：如果当前在均线下方但还没有记录首次跌破时间，立即记录
        # （兼容回测起始已在下方、或底仓建立日跳过cross检测的情况）
        if self.below_ma and self.first_below_ma_date is None:
            self.first_below_ma_date = current_date
            self.first_below_ma_bar = len(self)
            self.log(f'BIAS状态: 首次跌破均线，当前BIAS={current_bias:.2f}%，开始计时加仓周期')

        # ========== 第三步：波段仓操作 ==========

        # 情况1：跌破均线且满足加仓条件，执行定投买入
        # 检查是否达到定投间隔交易日
        can_dca = False
        has_own_capital = self.band_batches_remaining > 0 and self.band_cash_available > 0
        has_leverage = self.band_batches_remaining <= 0 and self.leverage_available > 0
        dca_triggered = current_bias <= -self.p.dca_trigger_bias
        if self.below_ma and dca_triggered and (has_own_capital or has_leverage):
            if self.last_dca_bar is None:
                can_dca = True  # 首次定投
            else:
                bars_since_last_dca = len(self) - self.last_dca_bar
                can_dca = bars_since_last_dca >= self.p.dca_interval

        if can_dca:
            self._execute_dca_buy(current_price, current_date)

        # 情况2：价格上穿均线（突破），进入突破确认期
        if cross_above:
            self.ma_breakout_since = current_date
            self.ma_breakout_bar = len(self)
            self.band_highest_price = 0
            if self.band_in_position:
                self.log(f'波段: 价格突破60日均线，进入{self.p.trailing_activation_bars}bar确认期')

        # 情况3：价格回到均线上方，且有波段持仓，启用移动止盈
        # 追踪从最近一次突破均线后的最高价
        elif not self.below_ma and self.band_in_position and self.ma_breakout_since is not None:
            bars_since_breakout = len(self) - self.ma_breakout_bar

            # 更新最高价（从突破后的最高价）
            if current_price > self.band_highest_price:
                self.band_highest_price = current_price
                self.log(f'波段: 更新突破后最高价 {self.band_highest_price:.3f}')

            # 检查移动止盈条件（动态止盈），需度过确认期后才真正启用
            if bars_since_breakout >= self.p.trailing_activation_bars:
                current_trailing_stop_pct = self._get_current_trailing_stop_pct(current_bias)
                trailing_stop_price = self.band_highest_price * (1 - current_trailing_stop_pct / 100)

                if current_price <= trailing_stop_price:
                    self._execute_trailing_sell(current_price, trailing_stop_price, current_trailing_stop_pct)
                else:
                    # 记录当前回撤
                    drawdown = (self.band_highest_price - current_price) / self.band_highest_price * 100
                    self.log(
                        f'波段: 持有中 BIAS={current_bias:.2f}% 回撤{drawdown:.2f}% '
                        f'动态止盈{current_trailing_stop_pct:.1f}% 止盈线{trailing_stop_price:.3f}'
                    )
            else:
                self.log(
                    f'波段: 突破确认期内 ({bars_since_breakout}/{self.p.trailing_activation_bars}bar) '
                    f'暂不移止盈，当前价{current_price:.3f}'
                )

    def _build_base_position(self):
        """建立底仓 - 一次性买入底仓比例对应的仓位"""
        total_cash = self.broker.getcash()
        base_cash = total_cash * self.p.base_position_pct / 100
        current_price = self.data.close[0]

        # 计算可买入股数（向下取整到100的整数倍，A股规则）
        size = int(base_cash / current_price / 100) * 100

        if size > 0:
            self.base_position_size = size
            self.base_position_price = current_price

            order = self.buy(size=size)

            self.log_signal(
                signal_type='buy',
                data=self.data,
                trigger_condition=f'建立底仓({self.p.base_position_pct}%)',
                indicator_values={
                    'close': current_price,
                    'base_position_pct': self.p.base_position_pct,
                    'buy_size': size,
                    'buy_amount': size * current_price,
                },
                confidence=1.0,
            )

            self.log(f'底仓建立: 买入{size}股 @ {current_price:.3f}，金额{size * current_price:.2f}')
            self.base_position_built = True
        else:
            self.log(f'底仓建立失败: 资金不足以买入100股')

    def _get_current_trailing_stop_pct(self, current_bias):
        """获取当前动态移动止盈比例，基于BIAS阈值逐步收紧"""
        if not self.p.use_dynamic_trailing_stop:
            return self.p.trailing_stop_pct

        levels = [
            (self.p.trailing_tighten_bias_3, self.p.trailing_tighten_stop_3),
            (self.p.trailing_tighten_bias_2, self.p.trailing_tighten_stop_2),
            (self.p.trailing_tighten_bias_1, self.p.trailing_tighten_stop_1),
        ]
        for threshold, stop_pct in levels:
            if threshold > 0 and current_bias >= threshold:
                return stop_pct
        return self.p.trailing_stop_pct

    def _calculate_dca_weight(self, current_price):
        """计算BIAS加权加仓倍数（方案C：时间+跌幅双重衰减）"""
        if not self.p.use_bias_weighting:
            return 1.0

        if self.first_below_ma_bar is None:
            return 1.0

        # 计算时间因子（基于实际交易bar数，与自然日脱钩）
        bars_since_start = len(self) - self.first_below_ma_bar
        time_factor = min(bars_since_start / self.p.time_decay_days, 1.0)

        # 计算跌幅因子（基于当前BIAS）
        current_bias = abs((current_price - self.ma60[0]) / self.ma60[0] * 100)
        drop_factor = min(current_bias / self.p.max_bias_ref, 1.0)

        # 综合权重计算
        # 权重 = 最小权重 + (最大权重 - 最小权重) × (时间因子 × 时间占比 + 跌幅因子 × 跌幅占比)
        combined_factor = (
            time_factor * self.p.time_factor_ratio +
            drop_factor * self.p.drop_factor_ratio
        )
        weight = self.p.min_dca_weight + (self.p.max_dca_weight - self.p.min_dca_weight) * combined_factor

        self.log(
            f'BIAS加权: 时间{bars_since_start}bar(因子{time_factor:.2f}) | '
            f'跌幅{current_bias:.2f}%(因子{drop_factor:.2f}) | '
            f'综合权重{weight:.2f}x'
        )

        return weight

    def _reset_bias_state(self):
        """重置BIAS加仓状态（当价格突破均线后调用）"""
        if self.first_below_ma_date is not None:
            self.log('BIAS状态: 价格突破均线，重置BIAS加仓计时周期')
        self.first_below_ma_date = None
        self.first_below_ma_bar = None

    def _execute_dca_buy(self, current_price, current_date):
        """执行定投买入 - 当跌破均线时分批买入（支持BIAS加权+杠杆）"""
        using_leverage = self.band_batches_remaining <= 0

        if not using_leverage:
            if self.band_cash_per_batch <= 0 or self.band_cash_available <= 0:
                return
        else:
            if self.band_cash_per_batch <= 0 or self.leverage_available <= 0:
                return

        # 计算BIAS加权倍数
        weight = self._calculate_dca_weight(current_price)

        # 计算本次实际加仓金额（基础金额 × 权重）
        actual_cash = self.band_cash_per_batch * weight

        # 限制不超过剩余资金的50%（防止单次打光）
        if not using_leverage:
            max_cash = self.band_cash_available * 0.5
        else:
            max_cash = self.leverage_available * 0.5
        actual_cash = min(actual_cash, max_cash)

        # 确保加仓金额有效
        if actual_cash <= 0:
            return

        # 计算本次可买入股数
        size = int(actual_cash / current_price / 100) * 100

        if size <= 0:
            if not using_leverage:
                self.log(f'波段定投: 资金不足以买入100股，跳过本次定投 (可用{self.band_cash_available:.2f})')
            else:
                self.log(f'杠杆加仓: 资金不足以买入100股，跳过本次定投 (可用杠杆{self.leverage_available:.2f})')
            return

        buy_amount = size * current_price

        # 确保不超过剩余资金
        if not using_leverage:
            if buy_amount > self.band_cash_available:
                size = int(self.band_cash_available / current_price / 100) * 100
                if size <= 0:
                    return
                buy_amount = size * current_price
        else:
            if buy_amount > self.leverage_available:
                size = int(self.leverage_available / current_price / 100) * 100
                if size <= 0:
                    return
                buy_amount = size * current_price

        order = self.buy(size=size)

        # 更新波段仓状态
        prev_cost = self.band_position_cost * self.band_position_size
        self.band_position_size += size
        self.band_position_cost = (prev_cost + buy_amount) / self.band_position_size
        self.last_dca_bar = len(self)  # 记录本次定投的bar序号

        if not using_leverage:
            self.band_cash_available -= buy_amount
            self.band_batches_remaining -= 1
            trigger_desc = f'波段定投(剩余{self.band_batches_remaining}批) 价格跌破60日均线'
        else:
            if self.leverage_start_date is None:
                self.leverage_start_date = current_date
                self.log(f'杠杆启用: 首次使用杠杆加仓 @ {current_date}')
            self.leverage_used += buy_amount
            self.leverage_available -= buy_amount
            trigger_desc = f'杠杆加仓(已用{self.leverage_used:.2f}) 价格跌破60日均线'

        if self.band_position_size > 0:
            self.band_in_position = True
            # 注意：不在买入时设置最高价，等到价格突破60均线后再开始追踪

        # 计算当前BIAS用于日志
        current_bias = (current_price - self.ma60[0]) / self.ma60[0] * 100

        self.log_signal(
            signal_type='buy',
            data=self.data,
            trigger_condition=trigger_desc,
            indicator_values={
                'close': current_price,
                'ma60': self.ma60[0],
                'bias60': current_bias,
                'dca_weight': weight,
                'band_buy_size': size,
                'band_buy_amount': buy_amount,
                'band_total_size': self.band_position_size,
                'band_avg_cost': self.band_position_cost,
                'band_batches_remaining': self.band_batches_remaining,
                'leverage_used': self.leverage_used,
                'leverage_available': self.leverage_available,
                'dca_interval': self.p.dca_interval,
            },
            confidence=0.7,
        )

        if not using_leverage:
            self.log(
                f'波段定投: 买入{size}股 @ {current_price:.3f} | '
                f'总持仓{self.band_position_size}股 成本{self.band_position_cost:.3f} | '
                f'剩余{self.band_batches_remaining}批 | '
                f'加权倍数{weight:.2f}x | BIAS60={current_bias:.2f}%'
            )
        else:
            self.log(
                f'杠杆加仓: 买入{size}股 @ {current_price:.3f} | '
                f'总持仓{self.band_position_size}股 成本{self.band_position_cost:.3f} | '
                f'已用杠杆{self.leverage_used:.2f} 剩余杠杆{self.leverage_available:.2f} | '
                f'加权倍数{weight:.2f}x | BIAS60={current_bias:.2f}%'
            )

    def _execute_trailing_sell(self, current_price, trailing_stop_price, trailing_stop_pct=None):
        """执行移动止盈卖出 - 当价格从高点回撤超过设定比例时卖出"""
        if self.band_position_size <= 0:
            return

        current_date = self.data.datetime.date(0)
        stop_pct = trailing_stop_pct if trailing_stop_pct is not None else self.p.trailing_stop_pct

        # 卖出全部波段持仓
        size = self.band_position_size
        sell_amount = size * current_price
        profit = (current_price - self.band_position_cost) * size
        profit_pct = (current_price / self.band_position_cost - 1) * 100

        order = self.sell(size=size)

        self.log_signal(
            signal_type='sell',
            data=self.data,
            trigger_condition=f'波段移动止盈: 价格从突破后高点{self.band_highest_price:.3f}回撤至{current_price:.3f}，超过{stop_pct}%',
            indicator_values={
                'close': current_price,
                'ma60': self.ma60[0],
                'highest_price': self.band_highest_price,
                'trailing_stop_price': trailing_stop_price,
                'trailing_stop_pct': stop_pct,
                'band_sell_size': size,
                'band_sell_amount': sell_amount,
                'band_profit': profit,
                'band_profit_pct': profit_pct,
                'leverage_used': self.leverage_used,
            },
            confidence=0.8,
        )

        self.log(
            f'波段卖出: 卖出{size}股 @ {current_price:.3f} | '
            f'盈亏{profit:.2f} ({profit_pct:+.2f}%) | '
            f'最高价{self.band_highest_price:.3f} 止盈线{trailing_stop_price:.3f} 动态止盈{stop_pct}%'
        )

        # 处理杠杆还款（如有）
        if self.leverage_used > 0:
            days = (current_date - self.leverage_start_date).days
            interest = self.leverage_used * days * self.p.leverage_interest_rate / 100 / 365
            repayment = self.leverage_used + interest
            self.band_cash_available += sell_amount - repayment
            self.log(
                f'杠杆还款: 本金{self.leverage_used:.2f} + 利息{interest:.2f} '
                f'(使用{days}天 利率{self.p.leverage_interest_rate:.1f}%) | '
                f'总还款{repayment:.2f} | 波段资金结余{self.band_cash_available:.2f}'
            )
            self.leverage_used = 0
            self.leverage_available = self.initial_total_cash * self.p.max_leverage_pct / 100
            self.leverage_start_date = None
        else:
            # 将卖出资金加回波段可用资金
            self.band_cash_available += sell_amount

        # 重新计算每批金额
        if self.p.dca_batches > 0:
            self.band_cash_per_batch = self.band_cash_available / self.p.dca_batches
        else:
            self.band_cash_per_batch = self.band_cash_available
        self.log(f'波段资金更新: 卖出回款后可用{self.band_cash_available:.2f} 每批{self.band_cash_per_batch:.2f}')

        # 重置波段仓状态
        self.band_position_size = 0
        self.band_position_cost = 0
        self.band_highest_price = 0
        self.band_in_position = False
        self.band_batches_remaining = self.p.dca_batches
        self.ma_breakout_since = None
        self.ma_breakout_bar = None
        self.last_dca_bar = None

        # 重置BIAS加仓状态，为下一次波段做准备
        self._reset_bias_state()

    def stop(self):
        """回测结束时的汇总"""
        super().stop()

        final_value = self.broker.getvalue()
        final_cash = self.broker.getcash()
        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)

        # 计算底仓市值
        base_value = self.base_position_size * current_price

        # 计算波段仓状态
        if self.band_position_size > 0:
            band_value = self.band_position_size * current_price
            band_unrealized = (current_price - self.band_position_cost) * self.band_position_size
            band_info = (
                f'波段持仓{self.band_position_size}股 市值{band_value:.2f} 浮盈{band_unrealized:.2f}'
            )
        else:
            band_info = '波段空仓'

        # 如果还有杠杆未清偿，计算应付利息
        if self.leverage_used > 0:
            days = (current_date - self.leverage_start_date).days
            interest = self.leverage_used * days * self.p.leverage_interest_rate / 100 / 365
            self.log(
                f'回测结束: 底仓市值{base_value:.2f} | {band_info} | '
                f'杠杆未清偿{self.leverage_used:.2f} 应付利息{interest:.2f}(使用{days}天)'
            )
        else:
            self.log(f'回测结束: 底仓市值{base_value:.2f} | {band_info}')

        self.log(f'分仓策略总结: 底仓比例{self.p.base_position_pct}% 波段比例{self.band_position_pct}%')
