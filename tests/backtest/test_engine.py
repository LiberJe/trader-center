# tests/backtest/test_engine.py
import pandas as pd
import pytest
import backtrader as bt
from datetime import datetime


class DummyStrategy(bt.Strategy):
    """用于测试的简单策略"""
    params = (('value', 0),)

    def __init__(self):
        pass

    def next(self):
        pass


def test_engine_initialization():
    """测试引擎初始化"""
    from trader_center.backtest.engine import BacktestEngine

    engine = BacktestEngine(initial_cash=200000, commission=0.001)

    assert engine.initial_cash == 200000
    assert engine.commission == 0.001


def test_engine_run_requires_valid_dataframe():
    """测试引擎检查 DataFrame 有效性"""
    from trader_center.backtest.engine import BacktestEngine

    engine = BacktestEngine()

    # 无效的 DataFrame
    bad_df = pd.DataFrame({'invalid': [1, 2]})

    with pytest.raises(ValueError, match="Missing required columns"):
        engine.run(data=bad_df, strategy=DummyStrategy)


def test_engine_run_basic():
    """测试引擎基本运行"""
    from trader_center.backtest.engine import BacktestEngine

    # 创建有效数据
    dates = pd.date_range('2024-01-01', periods=20, freq='B')
    df = pd.DataFrame({
        'open': [100.0 + i for i in range(20)],
        'high': [102.0 + i for i in range(20)],
        'low': [99.0 + i for i in range(20)],
        'close': [101.0 + i for i in range(20)],
        'volume': [1000 + i * 100 for i in range(20)],
    }, index=dates)

    engine = BacktestEngine(initial_cash=100000)
    result = engine.run(data=df, strategy=DummyStrategy)

    assert result is not None
    assert 'total_return' in result.metrics
