import pytest
from datetime import date


def test_backtest_result_creation():
    """测试结果对象创建"""
    from trader_center.backtest.results import BacktestResult

    result = BacktestResult(
        strategy_name="test",
        initial_cash=100000.0,
        final_value=110000.0,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result.strategy_name == "test"
    assert result.return_pct == 0.10  # 10%


def test_backtest_result_metrics():
    """测试绩效指标计算"""
    from trader_center.backtest.results import BacktestResult

    result = BacktestResult(
        strategy_name="test",
        initial_cash=100000.0,
        final_value=90000.0,
        trades=[
            {'date': date(2024, 1, 1), 'pnl': 1000},
            {'date': date(2024, 1, 2), 'pnl': -2000},
            {'date': date(2024, 1, 3), 'pnl': 500},
        ],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result.total_trades == 3
    assert result.win_rate == 2/3  # 2胜1负
    assert result.return_pct == -0.10  # -10%
