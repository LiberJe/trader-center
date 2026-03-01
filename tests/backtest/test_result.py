# tests/backtest/test_result.py
import pandas as pd
import pytest
from datetime import datetime, timedelta


def test_backtest_result_creation():
    """测试 BacktestResult 创建"""
    from trader_center.backtest.result import BacktestResult

    metrics = {'total_return': 0.2, 'max_drawdown': 0.1}
    trades = pd.DataFrame({'size': [100, -100]})
    daily = pd.DataFrame({'value': [100000, 110000]})

    result = BacktestResult(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        duration=timedelta(days=365),
        metrics=metrics,
        trades=trades,
        daily_values=daily,
        positions=pd.DataFrame()
    )

    assert result.metrics['total_return'] == 0.2


def test_backtest_result_report():
    """测试生成文字报告"""
    from trader_center.backtest.result import BacktestResult

    metrics = {
        'total_return': 0.25,
        'total_return_pct': 25.0,
        'cagr_pct': 25.0,
        'max_drawdown_pct': 10.0,
        'sharpe_ratio': 1.5,
    }

    result = BacktestResult(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        duration=timedelta(days=365),
        metrics=metrics,
        trades=pd.DataFrame(),
        daily_values=pd.DataFrame({'value': [100000, 125000]}),
        positions=pd.DataFrame()
    )

    report = result.report()
    assert '25.00%' in report
    assert '10.00%' in report
