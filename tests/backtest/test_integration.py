"""Integration tests for backtest module."""

import pandas as pd
import pytest
from datetime import datetime

from trader_center.backtest import BacktestEngine, BacktestResult
from trader_center.backtest.examples import SmaCross


def test_full_backtest_workflow():
    """测试完整的回测流程"""
    # 创建模拟数据
    dates = pd.date_range('2020-01-01', '2024-01-01', freq='B')
    n = len(dates)

    # 生成随机游走价格
    import numpy as np
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, n)
    prices = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n),
    }, index=dates)

    # 运行回测
    engine = BacktestEngine(
        initial_cash=100000,
        commission=0.0003,
        slippage=0.001
    )

    result = engine.run(
        data=df,
        strategy=SmaCross,
        params=dict(fast=10, slow=30)
    )

    # 验证结果
    assert isinstance(result, BacktestResult)
    assert result.start_date == dates[0]
    assert result.end_date == dates[-1]

    # 验证指标
    assert 'total_return' in result.metrics
    assert 'cagr' in result.metrics
    assert 'max_drawdown' in result.metrics
    assert 'sharpe_ratio' in result.metrics

    # 验证报告
    report = result.report()
    assert 'Backtest Report' in report
    assert 'Total Return' in report

    print(result.report())


def test_backtest_result_save_and_plot(tmp_path):
    """测试结果保存功能"""
    dates = pd.date_range('2024-01-01', periods=50, freq='B')
    df = pd.DataFrame({
        'open': [100.0 + i * 0.1 for i in range(50)],
        'high': [102.0 + i * 0.1 for i in range(50)],
        'low': [99.0 + i * 0.1 for i in range(50)],
        'close': [101.0 + i * 0.1 for i in range(50)],
        'volume': [10000] * 50,
    }, index=dates)

    engine = BacktestEngine(initial_cash=100000)
    result = engine.run(data=df, strategy=SmaCross, params=dict(fast=5, slow=20))

    # 测试保存
    prefix = str(tmp_path / "backtest")
    result.save(prefix)

    # 验证文件生成
    import os
    assert os.path.exists(f"{prefix}_trades.csv")
    assert os.path.exists(f"{prefix}_daily.csv")
    assert os.path.exists(f"{prefix}_metrics.json")

    # 测试绘图 (不实际显示)
    plot_path = str(tmp_path / "backtest.png")
    result.plot(path=plot_path)
    assert os.path.exists(plot_path)
