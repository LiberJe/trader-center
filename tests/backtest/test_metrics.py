# tests/backtest/test_metrics.py
import pandas as pd
import numpy as np
import pytest


def test_calculate_cagr():
    """测试年化收益率计算"""
    from trader_center.backtest.metrics import calculate_cagr

    # 2年翻倍
    result = calculate_cagr(1.0, 2.0, days=730)
    assert abs(result - 0.4142) < 0.01  # 约 41.42%


def test_calculate_max_drawdown():
    """测试最大回撤计算"""
    from trader_center.backtest.metrics import calculate_max_drawdown

    # 从 100 跌到 80，再涨到 120
    values = pd.Series([100, 110, 90, 80, 95, 120])
    dd, peak_idx, trough_idx = calculate_max_drawdown(values)

    assert abs(dd - 0.2727) < 0.01  # (110-80)/110 = 27.27%


def test_calculate_sharpe_ratio():
    """测试夏普比率计算"""
    from trader_center.backtest.metrics import calculate_sharpe_ratio

    # 每日收益 0.1%，无风险利率 3% 年化
    returns = pd.Series([0.001] * 252)  # 一年交易日
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.03)

    assert sharpe > 0


def test_calculate_metrics_integration():
    """测试完整的指标计算"""
    from trader_center.backtest.metrics import calculate_metrics

    # 模拟资金曲线：从 10万 到 12万
    daily_values = pd.DataFrame({
        'value': [100000, 101000, 100500, 102000, 120000],
    }, index=pd.date_range('2024-01-01', periods=5))

    metrics = calculate_metrics(daily_values)

    assert 'total_return' in metrics
    assert 'cagr' in metrics
    assert 'max_drawdown' in metrics
