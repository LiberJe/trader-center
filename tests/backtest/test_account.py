import pytest
from datetime import date


def test_strategy_account_creation():
    """测试账户创建"""
    from trader_center.backtest.account import StrategyAccount

    account = StrategyAccount(
        strategy_name="test_strategy",
        initial_cash=100000.0
    )

    assert account.strategy_name == "test_strategy"
    assert account.initial_cash == 100000.0
    assert account.cash == 100000.0
    assert account.positions == {}


def test_strategy_account_position_update():
    """测试持仓更新"""
    from trader_center.backtest.account import StrategyAccount

    account = StrategyAccount(
        strategy_name="test",
        initial_cash=100000.0
    )

    # 买入
    account.update_position("000001.SZ", 100, 10.0)
    assert account.positions["000001.SZ"].size == 100

    # 卖出
    account.update_position("000001.SZ", -100, 11.0)
    assert "000001.SZ" not in account.positions


def test_strategy_account_equity_calculation():
    """测试权益计算"""
    from trader_center.backtest.account import StrategyAccount

    account = StrategyAccount(
        strategy_name="test",
        initial_cash=100000.0
    )

    account.update_position("000001.SZ", 100, 10.0)
    account.cash -= 1000.0  # 扣除买入成本

    # 持仓市值 100 * 12 = 1200
    equity = account.calculate_equity({"000001.SZ": 12.0})
    assert equity == 100000.0 - 1000.0 + 1200.0
