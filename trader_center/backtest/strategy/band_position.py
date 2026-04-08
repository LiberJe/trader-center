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
    分仓波段策略

    底仓+波段仓的组合策略：
    - 底仓：长期持有，获取市场beta收益
    - 波段仓：围绕60日均线进行高抛低吸，获取alpha收益

    买入逻辑（波段仓）：
    - 价格跌破60日均线时，触发定投买入
    - 将波段资金分批投入，降低择时风险

    卖出逻辑（波段仓）：
    - 价格回到60日均线以上后，启用移动止盈
    - 追踪最高价，当回撤超过一定比例时卖出

    Params:
        base_position_pct: 底仓比例，默认80%，设为100%则为买入持有
        ma_period: 移动平均线周期，默认60日
        dca_batches: 定投批次，默认5次（跌破均线后将波段资金分5次投入）
        dca_interval: 定投间隔天数，默认5天（每5个交易日定投一次）
        trailing_stop_pct: 移动止盈比例，默认5%（从最高点回撤5%卖出）
    """

    name = "band_position"
    description = "分仓波段策略：底仓持有+波段定投+移动止盈"

    params = (
        ('base_position_pct', 80),      # 底仓比例（%）
        ('ma_period', 60),               # 均线周期
        ('dca_batches', 5),              # 定投批次
        ('dca_interval', 5),             # 定投间隔天数（默认每5个交易日定投一次）
        ('trailing_stop_pct', 5),        # 移动止盈比例（%）
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
        self.last_dca_date = None             # 上次定投日期

        # 记录底仓信息
        self.base_position_size = 0           # 底仓股数
        self.base_position_price = 0          # 底仓买入价格

    def _log_daily_state(self):
        """记录每日状态，增加分仓信息"""
        super()._log_daily_state()

        if self.p.base_position_pct < 100:
            self.log(
                f'分仓状态: 底仓{self.p.base_position_pct}%({self.base_position_size}股) | '
                f'波段{self.band_position_pct}% 可用资金:{self.band_cash_available:.2f} | '
                f'波段持仓:{self.band_position_size}股 成本:{self.band_position_cost:.3f} | '
                f'60日均线:{self.ma60[0]:.3f}'
            )

    def start(self):
        """回测开始时的初始化"""
        super().start()

        # 计算波段资金
        total_cash = self.broker.getcash()
        self.band_cash_available = total_cash * self.band_position_pct / 100

        # 计算每批定投金额
        if self.p.dca_batches > 0:
            self.band_cash_per_batch = self.band_cash_available / self.p.dca_batches
        else:
            self.band_cash_per_batch = self.band_cash_available

        self.band_batches_remaining = self.p.dca_batches

        self.log(
            f'策略启动: 总资金{total_cash:.2f} | '
            f'底仓比例{self.p.base_position_pct}% | 波段比例{self.band_position_pct}% | '
            f'波段资金{self.band_cash_available:.2f} 分{self.p.dca_batches}批投入 | '
            f'定投间隔{self.p.dca_interval}天'
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

        # 检测穿越事件
        cross_above = self.price_cross_ma > 0  # 价格上穿均线
        cross_below = self.price_cross_ma < 0  # 价格下穿均线

        if cross_above:
            self.log(f'信号: 价格上穿60日均线 {current_price:.3f} > {self.ma60[0]:.3f}')
        if cross_below:
            self.log(f'信号: 价格下穿60日均线 {current_price:.3f} < {self.ma60[0]:.3f}')

        # ========== 第三步：波段仓操作 ==========

        # 情况1：跌破均线且有剩余批次，且达到定投间隔，执行定投买入
        # 检查是否达到定投间隔天数
        can_dca = False
        if self.below_ma and self.band_batches_remaining > 0:
            if self.last_dca_date is None:
                can_dca = True  # 首次定投
            else:
                days_since_last_dca = (current_date - self.last_dca_date).days
                can_dca = days_since_last_dca >= self.p.dca_interval

        if can_dca:
            self._execute_dca_buy(current_price, current_date)

        # 情况2：价格上穿均线（突破），重置最高价追踪起点
        if cross_above:
            self.ma_breakout_since = current_date
            self.band_highest_price = current_price
            if self.band_in_position:
                self.log(f'波段: 价格突破60日均线，重置最高价追踪起点为{current_price:.3f}')

        # 情况3：价格回到均线上方，且有波段持仓，启用移动止盈
        # 追踪从最近一次突破均线后的最高价
        elif not self.below_ma and self.band_in_position and self.ma_breakout_since is not None:
            # 更新最高价（从突破后的最高价）
            if current_price > self.band_highest_price:
                self.band_highest_price = current_price
                self.log(f'波段: 更新突破后最高价 {self.band_highest_price:.3f}')

            # 检查移动止盈条件
            trailing_stop_price = self.band_highest_price * (1 - self.p.trailing_stop_pct / 100)

            if current_price <= trailing_stop_price:
                self._execute_trailing_sell(current_price, trailing_stop_price)
            else:
                # 记录当前回撤
                drawdown = (self.band_highest_price - current_price) / self.band_highest_price * 100
                self.log(f'波段: 持有中 回撤{drawdown:.2f}% 止盈线{trailing_stop_price:.3f}')

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

    def _execute_dca_buy(self, current_price, current_date):
        """执行定投买入 - 当跌破均线时分批买入"""
        if self.band_cash_per_batch <= 0:
            return

        # 计算本次可买入股数
        size = int(self.band_cash_per_batch / current_price / 100) * 100

        if size <= 0:
            # 资金不足以买入100股，尝试用全部剩余资金买入
            remaining_cash = self.broker.getcash()
            size = int(remaining_cash / current_price / 100) * 100

        if size > 0:
            buy_amount = size * current_price
            order = self.buy(size=size)

            # 更新波段仓状态
            prev_cost = self.band_position_cost * self.band_position_size
            self.band_position_size += size
            self.band_position_cost = (prev_cost + buy_amount) / self.band_position_size
            self.band_cash_available -= buy_amount
            self.band_batches_remaining -= 1
            self.last_dca_date = current_date  # 记录本次定投日期

            if self.band_position_size > 0:
                self.band_in_position = True
                # 注意：不在买入时设置最高价，等到价格突破60均线后再开始追踪

            self.log_signal(
                signal_type='buy',
                data=self.data,
                trigger_condition=f'波段定投(剩余{self.band_batches_remaining}批) 价格跌破60日均线',
                indicator_values={
                    'close': current_price,
                    'ma60': self.ma60[0],
                    'band_buy_size': size,
                    'band_buy_amount': buy_amount,
                    'band_total_size': self.band_position_size,
                    'band_avg_cost': self.band_position_cost,
                    'band_batches_remaining': self.band_batches_remaining,
                    'dca_interval': self.p.dca_interval,
                },
                confidence=0.7,
            )

            self.log(
                f'波段定投: 买入{size}股 @ {current_price:.3f} | '
                f'总持仓{self.band_position_size}股 成本{self.band_position_cost:.3f} | '
                f'剩余{self.band_batches_remaining}批 | '
                f'下次定投需间隔{self.p.dca_interval}天'
            )

    def _execute_trailing_sell(self, current_price, trailing_stop_price):
        """执行移动止盈卖出 - 当价格从高点回撤超过设定比例时卖出"""
        if self.band_position_size <= 0:
            return

        # 卖出全部波段持仓
        size = self.band_position_size
        sell_amount = size * current_price
        profit = (current_price - self.band_position_cost) * size
        profit_pct = (current_price / self.band_position_cost - 1) * 100

        order = self.sell(size=size)

        self.log_signal(
            signal_type='sell',
            data=self.data,
            trigger_condition=f'波段移动止盈: 价格从突破后高点{self.band_highest_price:.3f}回撤至{current_price:.3f}，超过{self.p.trailing_stop_pct}%',
            indicator_values={
                'close': current_price,
                'ma60': self.ma60[0],
                'highest_price': self.band_highest_price,
                'trailing_stop_price': trailing_stop_price,
                'band_sell_size': size,
                'band_sell_amount': sell_amount,
                'band_profit': profit,
                'band_profit_pct': profit_pct,
            },
            confidence=0.8,
        )

        self.log(
            f'波段卖出: 卖出{size}股 @ {current_price:.3f} | '
            f'盈亏{profit:.2f} ({profit_pct:+.2f}%) | '
            f'最高价{self.band_highest_price:.3f} 止盈线{trailing_stop_price:.3f}'
        )

        # 重置波段仓状态
        self.band_position_size = 0
        self.band_position_cost = 0
        self.band_highest_price = 0
        self.band_in_position = False
        self.band_batches_remaining = self.p.dca_batches
        self.ma_breakout_since = None
        self.last_dca_date = None

    def stop(self):
        """回测结束时的汇总"""
        super().stop()

        final_value = self.broker.getvalue()
        final_cash = self.broker.getcash()
        current_price = self.data.close[0]

        # 计算底仓市值
        base_value = self.base_position_size * current_price

        # 计算波段仓状态
        if self.band_position_size > 0:
            band_value = self.band_position_size * current_price
            band_unrealized = (current_price - self.band_position_cost) * self.band_position_size
            self.log(
                f'回测结束: 底仓市值{base_value:.2f} | '
                f'波段持仓{self.band_position_size}股 市值{band_value:.2f} 浮盈{band_unrealized:.2f}'
            )
        else:
            self.log(f'回测结束: 底仓市值{base_value:.2f} | 波段空仓')

        self.log(f'分仓策略总结: 底仓比例{self.p.base_position_pct}% 波段比例{self.band_position_pct}%')
