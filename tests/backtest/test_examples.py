import pytest


def test_sma_cross_strategy_exists():
    """测试 SMA 交叉策略可导入"""
    from trader_center.backtest.strategy.examples import SmaCrossStrategy
    assert SmaCrossStrategy.name == "sma_cross"
