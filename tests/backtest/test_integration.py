"""
回测集成测试

测试完整回测流程：DataFeed -> Strategy -> Broker -> Result
"""

import pytest
from datetime import date
import pandas as pd


@pytest.fixture
def sample_data():
    """创建模拟K线数据"""
    dates = pd.date_range('2024-01-01', '2024-03-01', freq='B')
    n = len(dates)

    # 生成简单的趋势数据
    base_price = 10.0
    prices = [base_price + i * 0.05 for i in range(n)]

    df = pd.DataFrame({
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [10000 + i * 100 for i in range(n)],
    }, index=dates)

    return df


def test_backtest_full_flow(sample_data, monkeypatch):
    """测试完整回测流程"""
    from trader_center.backtest.runner import BacktestRunner
    from trader_center.backtest.strategy.examples import BuyAndHoldStrategy
    from trader_center.backtest.data_feed import PandasDataFeed
    import trader_center.backtest.runner as runner_module

    # Mock DataHub at the runner module level
    def mock_get_daily_bars(symbol, start, end):
        return sample_data

    monkeypatch.setattr(runner_module, 'dh', type('obj', (object,), {'get_daily_bars': mock_get_daily_bars}))

    # 执行回测
    runner = BacktestRunner(max_workers=1)
    result = runner.run(
        strategy=BuyAndHoldStrategy,
        symbols=["TEST.SZ"],
        start="2024-01-01",
        end="2024-03-01",
        initial_cash=100000.0,
    )

    # 验证结果
    assert result.strategy_name == "buy_and_hold"
    assert result.initial_cash == 100000.0
    assert result.error_message is None
    # 买入持有应该有盈利（上升趋势）
    assert result.final_value > result.initial_cash
    # 验证 daily_values 已填充
    assert len(result.daily_values) > 0
    # 验证分析器结果
    assert 'total_return' in result.analyzer_results
    assert result.analyzer_results['total_return'] > 0


def test_backtest_with_error_handling(sample_data, monkeypatch):
    """测试错误处理"""
    from trader_center.backtest.runner import BacktestRunner
    from trader_center.backtest.strategy.base import BaseStrategy
    import trader_center.backtest.runner as runner_module

    # Mock DataHub at the runner module level
    def mock_get_daily_bars(symbol, start, end):
        return sample_data

    monkeypatch.setattr(runner_module, 'dh', type('obj', (object,), {'get_daily_bars': mock_get_daily_bars}))

    class BrokenStrategy(BaseStrategy):
        name = "broken"

        def next(self):
            raise ValueError("模拟错误")

    runner = BacktestRunner(max_workers=1)
    result = runner.run(
        strategy=BrokenStrategy,
        symbols=["000001.SZ"],
        start="2024-01-01",
        end="2024-01-10",
        initial_cash=100000.0,
    )

    # 应该返回错误结果而不是抛出异常
    assert result.error_message is not None
    assert "模拟错误" in result.error_message
