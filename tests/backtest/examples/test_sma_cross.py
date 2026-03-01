"""Tests for example strategies."""

import pandas as pd
import pytest

from trader_center.backtest import BacktestEngine
from trader_center.backtest.examples import SmaCross


def test_sma_cross_strategy():
    """测试双均线策略可以正常回测"""
    # 创建测试数据 (30 个交易日)
    dates = pd.date_range('2024-01-01', periods=30, freq='B')
    df = pd.DataFrame({
        'open': [100.0] * 30,
        'high': [105.0] * 30,
        'low': [95.0] * 30,
        'close': list(range(100, 130)),  # 上涨趋势
        'volume': [10000] * 30,
    }, index=dates)

    engine = BacktestEngine(initial_cash=100000, commission=0.0003)
    result = engine.run(
        data=df,
        strategy=SmaCross,
        params=dict(fast=5, slow=10)
    )

    assert result is not None
    assert 'total_return' in result.metrics
    assert isinstance(result.trades, pd.DataFrame)
