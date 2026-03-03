import pytest


def test_astock_commission_scheme():
    """测试 A股手续费计算"""
    from trader_center.backtest.broker import AStockCommission

    comm = AStockCommission()

    # 买入 10万元，万2.5佣金
    buy_cost = comm.getcommission(size=1000, price=100.0)
    # 1000 * 100 = 100000，万2.5 = 25元
    assert buy_cost == 25.0

    # 卖出 10万元，万2.5佣金 + 千1印花税 = 25 + 100 = 125
    sell_cost = comm.getcommission(size=-1000, price=100.0)
    assert sell_cost == 125.0


def test_minimum_commission():
    """测试最低5元佣金"""
    from trader_center.backtest.broker import AStockCommission

    comm = AStockCommission()

    # 买入 1万元，万2.5 = 2.5元，但最低5元
    buy_cost = comm.getcommission(size=100, price=100.0)
    assert buy_cost == 5.0


def test_configure_broker():
    """测试配置 backtrader broker"""
    import backtrader as bt
    from trader_center.backtest.broker import configure_astock_broker

    cerebro = bt.Cerebro()
    configure_astock_broker(cerebro, cash=100000.0)

    assert cerebro.broker.getcash() == 100000.0
