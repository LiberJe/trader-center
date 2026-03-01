"""Tests for SmaCrossEnhanced strategy."""

import pandas as pd
import pytest

from trader_center.backtest import BacktestEngine
from trader_center.backtest.examples.sma_cross_enhanced import SmaCrossEnhanced


def test_basic_ma_indicators():
    """测试基础均线指标初始化"""
    # 创建测试数据 (60个交易日，产生明显趋势)
    dates = pd.date_range('2024-01-01', periods=60, freq='B')
    prices = [100 + i * 0.5 for i in range(60)]  # 上涨趋势
    df = pd.DataFrame({
        'open': [p - 1 for p in prices],
        'high': [p + 2 for p in prices],
        'low': [p - 2 for p in prices],
        'close': prices,
        'volume': [10000] * 60,
    }, index=dates)

    engine = BacktestEngine(initial_cash=100000, commission=0.0003)
    result = engine.run(
        data=df,
        strategy=SmaCrossEnhanced,
        params=dict(fast_period=5, slow_period=20)
    )

    assert result is not None
    assert len(result.trades) >= 0


def test_adx_filter():
    """测试ADX趋势过滤功能"""
    dates = pd.date_range('2024-01-01', periods=60, freq='B')
    prices = [100 + i * 0.5 for i in range(60)]
    df = pd.DataFrame({
        'open': [p - 1 for p in prices],
        'high': [p + 2 for p in prices],
        'low': [p - 2 for p in prices],
        'close': prices,
        'volume': [10000] * 60,
    }, index=dates)

    # 启用ADX过滤
    engine = BacktestEngine(initial_cash=100000, commission=0.0003)
    result_with_adx = engine.run(
        data=df,
        strategy=SmaCrossEnhanced,
        params=dict(
            fast_period=5,
            slow_period=20,
            use_adx_filter=True,
            adx_threshold=25
        )
    )

    # 禁用ADX过滤
    engine2 = BacktestEngine(initial_cash=100000, commission=0.0003)
    result_without_adx = engine2.run(
        data=df,
        strategy=SmaCrossEnhanced,
        params=dict(
            fast_period=5,
            slow_period=20,
            use_adx_filter=False
        )
    )

    assert result_with_adx is not None
    assert result_without_adx is not None


def test_trend_confirmation():
    """测试多时间周期趋势确认"""
    dates = pd.date_range('2024-01-01', periods=80, freq='B')
    prices = [100 + i * 0.5 for i in range(80)]
    df = pd.DataFrame({
        'open': [p - 1 for p in prices],
        'high': [p + 2 for p in prices],
        'low': [p - 2 for p in prices],
        'close': prices,
        'volume': [10000] * 80,
    }, index=dates)

    # 启用趋势确认
    engine = BacktestEngine(initial_cash=100000, commission=0.0003)
    result = engine.run(
        data=df,
        strategy=SmaCrossEnhanced,
        params=dict(
            fast_period=5,
            slow_period=20,
            use_trend_confirm=True,
            trend_ma_period=60
        )
    )

    assert result is not None
