"""
A股 Broker 配置

实现 A股交易规则：
- 买入：佣金万2.5，最低5元
- 卖出：佣金万2.5 + 印花税千1，最低5元
- 涨跌停限制（需在策略中检查）
- T+1 限制（需在策略中检查）
- 最小交易单位：1手 = 100股（通过AStockSizer实现）
"""

import backtrader as bt
from dataclasses import dataclass
from typing import Optional, Type


class AStockCommissionScheme(bt.CommInfoBase):
    """
    A股手续费计算方案

    规则：
    - 佣金：万2.5 (0.025%)
    - 印花税：千1 (0.1%)，仅卖出收取
    - 最低佣金：5元
    - 最小交易单位：100股（1手）

    注意：由于完全重写了手续费计算逻辑，commtype 设置为 COMM_FIXED 以避免 backtrader 的百分比处理。
    """

    params = (
        ('commission', 0.00025),   # 万2.5 = 0.025% = 0.00025 (decimal form)
        ('stamp_duty', 0.001),      # 千1 = 0.1% = 0.001 印花税 (only on sell)
        ('min_commission', 5.0),    # 最低5元
        ('lot_size', 100),          # 最小交易单位：100股
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED),  # 使用 FIXED 模式，避免百分比转换
    )

    def getsize(self, price: float, cash: float) -> int:
        """
        计算给定资金和价格下可交易的数量

        重写此方法以确保数量为 lot_size 的整数倍（向下取整）。
        这是 order_target_percent / order_target_value 实际调用的方法。

        Args:
            price: 标的当前价格
            cash: 可用资金

        Returns:
            可交易数量（lot_size 的整数倍）
        """
        if price <= 0:
            return 0

        # 先计算不考虑 lot_size 的最大数量
        size = int(cash // price)

        # 向下取整到 lot_size 的整数倍
        size = (size // self.p.lot_size) * self.p.lot_size

        return size

    def getcommission(self, size: float, price: float, pseudoexec: bool = False) -> float:
        """
        计算手续费

        Args:
            size: 成交数量（正数=买入，负数=卖出）
            price: 成交价格
            pseudoexec: 是否预执行（backtrader内部使用）

        Returns:
            总费用（元）
        """
        amount = abs(size) * price
        is_buy = size > 0

        # 佣金（买卖都收）- commission is in decimal (0.00025 = 万2.5)
        commission = amount * self.p.commission
        commission = max(commission, self.p.min_commission)

        # 印花税（仅卖出）- stamp_duty is in decimal (0.001 = 千1)
        stamp_duty = 0
        if not is_buy:
            stamp_duty = amount * self.p.stamp_duty

        return commission + stamp_duty


# 别名，方便导入
AStockCommission = AStockCommissionScheme


@dataclass
class AStockConstraints:
    """
    A股交易限制检查器

    用于在策略中检查 A股特有规则：
    - 涨跌停限制
    - T+1 交易限制
    """

    # 涨跌停幅度（默认 10%，ST 股票 5%，创业板/科创板 20%）
    limit_up_pct: float = 0.10
    limit_down_pct: float = 0.10

    def can_buy(self, data: bt.DataBase, last_close: float) -> bool:
        """
        检查是否可以买入（非涨停）

        Args:
            data: backtrader Data 对象
            last_close: 昨日收盘价

        Returns:
            True 如果可以买入
        """
        limit_up = last_close * (1 + self.limit_up_pct)
        current_price = data.close[0]

        # 当前价格低于涨停价才能买入
        return current_price < limit_up * 0.999  # 留一点容差

    def can_sell(self, data: bt.DataBase, last_close: float) -> bool:
        """
        检查是否可以卖出（非跌停）

        Args:
            data: backtrader Data 对象
            last_close: 昨日收盘价

        Returns:
            True 如果可以卖出
        """
        limit_down = last_close * (1 - self.limit_down_pct)
        current_price = data.close[0]

        # 当前价格高于跌停价才能卖出
        return current_price > limit_down * 1.001  # 留一点容差


class AStockSizer(bt.Sizer):
    """
    A股交易数量Sizer

    确保交易数量为100股的整数倍（向下取整）。

    使用方式：
        # 方式1：使用默认配置（通过configure_astock_broker自动设置）
        configure_astock_broker(cerebro, cash=100000, use_lot_sizer=True)

        # 方式2：手动添加到cerebro
        cerebro.addsizer(AStockSizer)

        # 方式3：配合其他Sizer使用（如PercentSizer）
        cerebro.addsizer(AStockSizer, base_sizer=bt.sizers.PercentSizer, percents=95)

    Params:
        lot_size: 每手股数（默认100股）
        base_sizer: 基础Sizer类，用于计算原始数量
        **kwargs: 传递给基础Sizer的参数
    """

    params = (
        ('lot_size', 100),
        ('base_sizer', None),
    )

    def __init__(self):
        super().__init__()
        # 收集额外参数传递给基础Sizer
        self._base_sizer_kwargs = {}
        for param_name in self.p._getkeys():
            if param_name not in ('lot_size', 'base_sizer'):
                self._base_sizer_kwargs[param_name] = getattr(self.p, param_name)

    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        计算交易数量，确保为lot_size的整数倍（向下取整）
        """
        # 如果有指定基础Sizer，使用它计算原始数量
        if self.p.base_sizer is not None:
            base = self.p.base_sizer(**self._base_sizer_kwargs)
            base._owner = self._owner
            base._data = self._data
            base.strategy = self.strategy
            base.broker = self.broker
            size = base._getsizing(comminfo, cash, data, isbuy)
        else:
            # 默认逻辑：使用标准Sizer计算
            size = self._calculate_size(comminfo, cash, data, isbuy)

        # 向下取整到lot_size的整数倍
        if size and size > 0:
            size = (int(size) // self.p.lot_size) * self.p.lot_size

        return int(size) if size > 0 else 0

    def _calculate_size(self, comminfo, cash, data, isbuy):
        """
        默认数量计算逻辑
        """
        price = data.close[0]
        if price == 0:
            return 0

        if isbuy:
            # 买入时根据可用资金计算
            # 预留手续费空间
            commission_rate = max(comminfo.commission, 0.00025)
            affordable_price = price * (1 + commission_rate)
            size = int(cash / affordable_price)
        else:
            # 卖出时返回当前持仓
            position = self.strategy.getposition(data)
            size = abs(int(position.size)) if position else 0

        return size


def configure_astock_broker(
    cerebro: bt.Cerebro,
    cash: float = 100000.0,
    slip_perc: float = 0.0,
    slip_fixed: float = 0.0,
    use_lot_sizer: bool = True,
) -> bt.Broker:
    """
    配置 A股 Broker

    Args:
        cerebro: backtrader Cerebro 实例
        cash: 初始资金
        slip_perc: 滑点百分比
        slip_fixed: 固定滑点金额
        use_lot_sizer: 是否使用A股100股整数倍Sizer（默认True）

    Returns:
        配置好的 Broker 实例
    """
    # 设置初始资金
    cerebro.broker.setcash(cash)

    # 添加手续费方案
    comminfo = AStockCommissionScheme()
    cerebro.broker.addcommissioninfo(comminfo)

    # 设置滑点
    if slip_perc > 0 or slip_fixed > 0:
        cerebro.broker.set_slippage_perc(slip_perc, slip_fixed)

    # 设置A股100股整数倍Sizer
    if use_lot_sizer:
        cerebro.addsizer(AStockSizer)

    return cerebro.broker