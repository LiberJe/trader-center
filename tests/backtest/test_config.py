import pytest


def test_config_defaults():
    """测试默认配置"""
    from trader_center.backtest.config import BacktestConfig

    config = BacktestConfig()
    assert config.initial_cash == 100000.0
    assert config.commission_rate == 0.00025


def test_config_custom_values():
    """测试自定义配置"""
    from trader_center.backtest.config import BacktestConfig

    config = BacktestConfig(
        initial_cash=500000.0,
        commission_rate=0.0003,
    )
    assert config.initial_cash == 500000.0
    assert config.commission_rate == 0.0003
