"""
A股 Broker 配置

实现 A股交易规则：
- 买入：佣金万2.5，最低5元
- 卖出：佣金万2.5 + 印花税千1，最低5元
- 涨跌停限制（需在策略中检查）
- T+1 限制（需在策略中检查）
"""

import backtrader as bt
from dataclasses import dataclass
from typing import Optional


@dataclass
class AStockCommissionScheme(bt.CommInfoBase):
    """
    A股手续费计算方案

    规则：
    - 佣金：万2.5 (0.025%)
    - 印花税：千1 (0.1%)，仅卖出收取
    - 最低佣金：5元
    """

    params = (
        ('commission', 0.00025),   # 万2.5
        ('stamp_duty', 0.001),      # 千1印花税
        ('min_commission', 5.0),    # 最低5元
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_PERC),
    )

    def getcommission(self, size: float, price: float, is_buy: bool) -> float:
        """
        计算手续费

        Args:
            size: 成交数量
            price: 成交价格
            is_buy: 是否买入

        Returns:
            总费用（元）
        """
        amount = abs(size) * price

        # 佣金（买卖都收）
        commission = amount * self.p.commission
        commission = max(commission, self.p.min_commission)

        # 印花税（仅卖出）
        stamp_duty = 0
        if not is_buy:
            stamp_duty = amount * self.p.stamp_duty

        return commission + stamp_duty


# 别名，方便导入
AStockCommission = AStockCommissionScheme


def configure_astock_broker(
    cerebro: bt.Cerebro,
    cash: float = 100000.0,
    slip_perc: float = 0.0,
    slip_fixed: float = 0.0,
) -> bt.Broker:
    """
    配置 A股 Broker

    Args:
        cerebro: backtrader Cerebro 实例
        cash: 初始资金
        slip_perc: 滑点百分比
        slip_fixed: 固定滑点金额

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

    return cerebro.broker


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
