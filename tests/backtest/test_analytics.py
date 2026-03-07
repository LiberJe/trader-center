"""
绩效分析模块测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime
from pathlib import Path
import tempfile

from trader_center.backtest.analytics import (
    PerformanceAnalytics,
    create_returns_series,
    load_benchmark_returns,
    HAS_QUANTSTATS,
)


class TestPerformanceAnalytics:
    """PerformanceAnalytics 类测试"""

    @pytest.fixture
    def sample_returns(self):
        """创建示例收益率序列"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='B')
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        return returns

    @pytest.fixture
    def sample_benchmark(self):
        """创建示例基准收益率序列"""
        np.random.seed(43)
        dates = pd.date_range('2024-01-01', periods=100, freq='B')
        returns = pd.Series(np.random.normal(0.0008, 0.015, 100), index=dates)
        return returns

    def test_init_with_valid_returns(self, sample_returns):
        """测试使用有效收益率序列初始化"""
        analytics = PerformanceAnalytics(sample_returns)
        
        assert len(analytics.returns) == 100
        assert isinstance(analytics.returns.index, pd.DatetimeIndex)
        assert analytics.benchmark is None

    def test_init_with_benchmark(self, sample_returns, sample_benchmark):
        """测试使用基准收益率初始化"""
        analytics = PerformanceAnalytics(sample_returns, sample_benchmark)
        
        assert len(analytics.returns) == 100
        assert len(analytics.benchmark) == 100

    def test_init_with_invalid_returns(self):
        """测试使用无效收益率序列初始化"""
        with pytest.raises(ValueError, match="returns 必须是 pd.Series"):
            PerformanceAnalytics([0.01, 0.02])
        
        with pytest.raises(ValueError, match="returns 不能为空"):
            PerformanceAnalytics(pd.Series(dtype=float))

    def test_metrics_basic(self, sample_returns):
        """测试基础绩效指标计算"""
        analytics = PerformanceAnalytics(sample_returns)
        metrics = analytics.metrics()
        
        assert 'total_return' in metrics
        assert 'sharpe' in metrics
        assert 'max_drawdown' in metrics
        assert 'volatility' in metrics
        assert 'sortino' in metrics
        assert 'calmar' in metrics
        assert 'win_rate' in metrics
        
        assert isinstance(metrics['total_return'], float)
        assert isinstance(metrics['sharpe'], float)
        assert metrics['win_rate'] >= 0 and metrics['win_rate'] <= 1

    def test_metrics_with_benchmark(self, sample_returns, sample_benchmark):
        """测试带基准的绩效指标计算"""
        analytics = PerformanceAnalytics(sample_returns, sample_benchmark)
        metrics = analytics.metrics()
        
        if HAS_QUANTSTATS:
            assert 'alpha' in metrics
            assert 'beta' in metrics
            assert 'information_ratio' in metrics

    def test_monthly_returns(self, sample_returns):
        """测试月度收益计算"""
        analytics = PerformanceAnalytics(sample_returns)
        monthly = analytics.monthly_returns()
        
        assert isinstance(monthly, pd.DataFrame)
        assert len(monthly) > 0

    def test_yearly_returns(self, sample_returns):
        """测试年度收益计算"""
        analytics = PerformanceAnalytics(sample_returns)
        yearly = analytics.yearly_returns()
        
        assert isinstance(yearly, pd.DataFrame)
        assert len(yearly) > 0

    def test_drawdown_details(self, sample_returns):
        """测试回撤详情"""
        analytics = PerformanceAnalytics(sample_returns)
        details = analytics.drawdown_details()
        
        assert isinstance(details, pd.DataFrame)

    def test_report_generation(self, sample_returns):
        """测试 HTML 报告生成"""
        analytics = PerformanceAnalytics(sample_returns)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.html"
            result = analytics.report(output_path=output_path, title="Test Report")
            
            if HAS_QUANTSTATS:
                assert result is not None
                assert Path(result).exists()
            else:
                assert result is None

    def test_snapshot_generation(self, sample_returns):
        """测试快照图表生成"""
        analytics = PerformanceAnalytics(sample_returns)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "snapshot.png"
            result = analytics.plot_snapshot(output_path=output_path)
            
            if HAS_QUANTSTATS:
                pass
            else:
                assert result is None


class TestCreateReturnsSeries:
    """create_returns_series 函数测试"""

    def test_create_from_daily_values(self):
        """测试从每日资产价值创建收益率序列"""
        daily_values = [
            {'date': '2024-01-01', 'value': 100000},
            {'date': '2024-01-02', 'value': 101000},
            {'date': '2024-01-03', 'value': 100500},
            {'date': '2024-01-04', 'value': 102000},
        ]
        
        returns = create_returns_series(daily_values)
        
        assert len(returns) == 3
        assert isinstance(returns.index, pd.DatetimeIndex)
        assert returns.iloc[0] == pytest.approx(0.01, rel=1e-3)

    def test_create_with_empty_values(self):
        """测试空数据"""
        with pytest.raises(ValueError, match="daily_values 不能为空"):
            create_returns_series([])

    def test_create_with_missing_fields(self):
        """测试缺少必要字段"""
        with pytest.raises(ValueError, match="必须包含"):
            create_returns_series([{'date': '2024-01-01'}])
        
        with pytest.raises(ValueError, match="必须包含"):
            create_returns_series([{'value': 100000}])


class TestLoadBenchmarkReturns:
    """load_benchmark_returns 函数测试"""

    def test_load_benchmark_returns(self):
        """测试加载基准收益率"""
        try:
            returns = load_benchmark_returns(
                "000300.SH",
                "2024-01-01",
                "2024-01-31"
            )
            
            if returns is not None:
                assert isinstance(returns, pd.Series)
                assert isinstance(returns.index, pd.DatetimeIndex)
        except Exception:
            pytest.skip("DataHub not available")


class TestBacktestResultIntegration:
    """BacktestResult 集成测试"""

    def test_get_returns_series(self):
        """测试 BacktestResult.get_returns_series"""
        from trader_center.backtest.results import BacktestResult
        
        result = BacktestResult(
            strategy_name="test",
            initial_cash=100000,
            final_value=110000,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            daily_values=[
                {'date': '2024-01-01', 'value': 100000},
                {'date': '2024-01-02', 'value': 101000},
                {'date': '2024-01-03', 'value': 100500},
            ]
        )
        
        returns = result.get_returns_series()
        
        assert len(returns) == 2
        assert isinstance(returns.index, pd.DatetimeIndex)

    def test_get_extended_metrics(self):
        """测试 BacktestResult.get_extended_metrics"""
        from trader_center.backtest.results import BacktestResult
        
        np.random.seed(42)
        daily_values = [
            {'date': d, 'value': 100000 * (1 + r)}
            for d, r in zip(
                pd.date_range('2024-01-01', periods=50, freq='B'),
                np.random.normal(0.001, 0.02, 50).cumsum()
            )
        ]
        
        result = BacktestResult(
            strategy_name="test",
            initial_cash=100000,
            final_value=daily_values[-1]['value'],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 15),
            daily_values=daily_values
        )
        
        metrics = result.get_extended_metrics()
        
        assert 'sharpe' in metrics
        assert 'sortino' in metrics
        assert 'max_drawdown' in metrics

    def test_generate_performance_report(self):
        """测试 BacktestResult.generate_performance_report"""
        from trader_center.backtest.results import BacktestResult
        
        np.random.seed(42)
        daily_values = [
            {'date': d, 'value': 100000 * (1 + r)}
            for d, r in zip(
                pd.date_range('2024-01-01', periods=50, freq='B'),
                np.random.normal(0.001, 0.02, 50).cumsum()
            )
        ]
        
        result = BacktestResult(
            strategy_name="test",
            initial_cash=100000,
            final_value=daily_values[-1]['value'],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 15),
            daily_values=daily_values
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = result.generate_performance_report(
                output_dir=Path(tmpdir),
                title="Test Report"
            )
            
            if HAS_QUANTSTATS:
                pass


class TestEdgeCases:
    """边界情况测试"""

    def test_single_day_returns(self):
        """测试单日收益率 - 应该能创建，但计算指标时可能返回有限结果"""
        returns = pd.Series([0.01], index=pd.date_range('2024-01-01', periods=1))
        
        analytics = PerformanceAnalytics(returns)
        metrics = analytics.metrics()
        
        assert 'total_return' in metrics

    def test_all_positive_returns(self):
        """测试全部正收益"""
        dates = pd.date_range('2024-01-01', periods=20, freq='B')
        returns = pd.Series([0.01] * 20, index=dates)
        
        analytics = PerformanceAnalytics(returns)
        metrics = analytics.metrics()
        
        assert metrics['win_rate'] == 1.0
        assert metrics['max_drawdown'] >= 0

    def test_all_negative_returns(self):
        """测试全部负收益"""
        dates = pd.date_range('2024-01-01', periods=20, freq='B')
        returns = pd.Series([-0.01] * 20, index=dates)
        
        analytics = PerformanceAnalytics(returns)
        metrics = analytics.metrics()
        
        assert metrics['win_rate'] == 0.0
        assert metrics['total_return'] < 0

    def test_zero_volatility(self):
        """测试零波动率"""
        dates = pd.date_range('2024-01-01', periods=20, freq='B')
        returns = pd.Series([0.0] * 20, index=dates)
        
        analytics = PerformanceAnalytics(returns)
        metrics = analytics.metrics()
        
        assert metrics['volatility'] == 0.0
        assert metrics['sharpe'] == 0.0 or np.isnan(metrics['sharpe'])


@pytest.mark.skipif(not HAS_QUANTSTATS, reason="QuantStats not installed")
class TestQuantStatsFeatures:
    """QuantStats 特有功能测试"""

    def test_quantstats_metrics(self):
        """测试 QuantStats 特有指标"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='B')
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        
        analytics = PerformanceAnalytics(returns)
        metrics = analytics.metrics()
        
        assert 'var_95' in metrics
        assert 'cvar_95' in metrics
        assert 'omega' in metrics
        assert 'tail_ratio' in metrics

    def test_quantstats_report_with_benchmark(self):
        """测试带基准的 QuantStats 报告"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='B')
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        benchmark = pd.Series(np.random.normal(0.0008, 0.015, 100), index=dates)
        
        analytics = PerformanceAnalytics(returns, benchmark)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            result = analytics.report(output_path=output_path)
            
            assert result is not None
            assert Path(result).exists()
