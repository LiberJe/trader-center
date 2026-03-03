import pytest
from datetime import date


def test_backtest_runner_creation():
    """测试运行器创建"""
    from trader_center.backtest.runner import BacktestRunner

    runner = BacktestRunner()
    assert runner is not None


def test_backtest_runner_with_max_workers():
    """测试带进程数限制的创建"""
    from trader_center.backtest.runner import BacktestRunner

    runner = BacktestRunner(max_workers=2)
    assert runner.max_workers == 2
