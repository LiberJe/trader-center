"""
Alpha/Beta分析模块测试
"""

import pytest
import pandas as pd
import numpy as np
from trader_center.factor.mining.alpha_beta import AlphaBetaAnalyzer


@pytest.fixture
def sample_factor_data():
    """
    创建测试用的因子数据
    """
    dates = pd.date_range('2020-01-01', '2020-06-30')  # 6个月数据
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建因子数据
    data = []
    for i, date in enumerate(dates):
        row = [i*0.1 + j for j in range(len(stocks))]
        data.append(row)
    
    factor_data = pd.DataFrame(data, index=dates, columns=stocks)
    return factor_data


@pytest.fixture
def sample_forward_returns():
    """
    创建测试用的未来收益数据
    """
    dates = pd.date_range('2020-01-01', '2020-06-30')  # 6个月数据
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建收益数据
    data = []
    for i, date in enumerate(dates):
        # 收益与因子值相关
        row = [i*0.001 + j*0.0001 + np.random.normal(0, 0.01) for j in range(len(stocks))]
        data.append(row)
    
    returns_data = pd.DataFrame(data, index=dates, columns=stocks)
    return returns_data


@pytest.fixture
def sample_benchmark_returns():
    """
    创建测试用的基准收益数据
    """
    dates = pd.date_range('2020-01-01', '2020-06-30')
    
    # 创建基准收益数据
    data = []
    for i, date in enumerate(dates):
        # 模拟市场收益
        return_val = 0.0005 + np.random.normal(0, 0.008)
        data.append(return_val)
    
    benchmark_data = pd.Series(data, index=dates, name='benchmark')
    return benchmark_data


@pytest.fixture
def sample_market_factor():
    """
    创建测试用的市场因子数据
    """
    dates = pd.date_range('2020-01-01', '2020-06-30')
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建市场因子数据
    data = []
    for i, date in enumerate(dates):
        # 模拟市场因子
        row = [0.0005 + np.random.normal(0, 0.008) for _ in range(len(stocks))]
        data.append(row)
    
    market_factor = pd.DataFrame(data, index=dates, columns=stocks)
    return market_factor


def test_compute_factor_returns(sample_factor_data, sample_forward_returns):
    """
    测试计算因子组合收益
    """
    analyzer = AlphaBetaAnalyzer()
    
    # 测试最高分组
    factor_returns_top = analyzer.compute_factor_returns(
        sample_factor_data, 
        sample_forward_returns, 
        quantile=1
    )
    assert isinstance(factor_returns_top, pd.Series)
    assert len(factor_returns_top) > 0
    
    # 测试最低分组
    factor_returns_bottom = analyzer.compute_factor_returns(
        sample_factor_data, 
        sample_forward_returns, 
        quantile=-1
    )
    assert isinstance(factor_returns_bottom, pd.Series)


def test_compute_factor_alpha_beta(sample_factor_data, sample_forward_returns, sample_benchmark_returns):
    """
    测试计算因子Alpha和Beta
    """
    analyzer = AlphaBetaAnalyzer()
    factor_returns = analyzer.compute_factor_returns(
        sample_factor_data, 
        sample_forward_returns
    )
    
    alpha_beta = analyzer.compute_factor_alpha_beta(
        factor_returns, 
        sample_benchmark_returns
    )
    
    assert isinstance(alpha_beta, dict)
    assert 'alpha' in alpha_beta
    assert 'beta' in alpha_beta
    assert 'r_squared' in alpha_beta
    assert 'tracking_error' in alpha_beta
    assert 'information_ratio' in alpha_beta


def test_compute_alpha_by_period(sample_factor_data, sample_forward_returns, sample_benchmark_returns):
    """
    测试分时期计算Alpha
    """
    analyzer = AlphaBetaAnalyzer()
    factor_returns = analyzer.compute_factor_returns(
        sample_factor_data, 
        sample_forward_returns
    )
    
    # 测试月度Alpha
    alpha_by_month = analyzer.compute_alpha_by_period(
        factor_returns, 
        sample_benchmark_returns, 
        period='month'
    )
    assert isinstance(alpha_by_month, pd.Series)
    
    # 测试季度Alpha
    alpha_by_quarter = analyzer.compute_alpha_by_period(
        factor_returns, 
        sample_benchmark_returns, 
        period='quarter'
    )
    assert isinstance(alpha_by_quarter, pd.Series)


def test_compute_alpha_exposure(sample_factor_data, sample_market_factor):
    """
    测试计算因子暴露
    """
    analyzer = AlphaBetaAnalyzer()
    
    exposure = analyzer.compute_alpha_exposure(
        sample_factor_data, 
        sample_market_factor
    )
    
    assert isinstance(exposure, pd.Series)
    assert all(-1 <= v <= 1 for v in exposure.values)


def test_compute_tracking_error(sample_factor_data, sample_forward_returns, sample_benchmark_returns):
    """
    测试计算跟踪误差
    """
    analyzer = AlphaBetaAnalyzer()
    factor_returns = analyzer.compute_factor_returns(
        sample_factor_data, 
        sample_forward_returns
    )
    
    tracking_error = analyzer.compute_tracking_error(
        factor_returns, 
        sample_benchmark_returns
    )
    
    assert isinstance(tracking_error, (float, np.floating))
    assert tracking_error >= 0


def test_get_risk_adjusted_metrics(sample_factor_data, sample_forward_returns, sample_benchmark_returns):
    """
    测试获取风险调整指标
    """
    analyzer = AlphaBetaAnalyzer()
    factor_returns = analyzer.compute_factor_returns(
        sample_factor_data, 
        sample_forward_returns
    )
    
    metrics = analyzer.get_risk_adjusted_metrics(
        factor_returns, 
        sample_benchmark_returns
    )
    
    assert isinstance(metrics, dict)
    assert 'annualized_return' in metrics
    assert 'annualized_volatility' in metrics
    assert 'sharpe_ratio' in metrics
    assert 'max_drawdown' in metrics
    assert 'calmar_ratio' in metrics
    assert 'sortino_ratio' in metrics


def test_edge_cases():
    """
    测试边界情况
    """
    analyzer = AlphaBetaAnalyzer()
    
    # 测试空数据
    empty_data = pd.DataFrame()
    empty_returns = pd.Series()
    
    factor_returns = analyzer.compute_factor_returns(empty_data, empty_data)
    assert isinstance(factor_returns, pd.Series)
    assert len(factor_returns) == 0
    
    # 测试数据不足
    short_returns = pd.Series([0.01, 0.02], index=pd.date_range('2020-01-01', '2020-01-02'))
    short_benchmark = pd.Series([0.005, 0.006], index=pd.date_range('2020-01-01', '2020-01-02'))
    
    alpha_beta = analyzer.compute_factor_alpha_beta(short_returns, short_benchmark)
    assert isinstance(alpha_beta, dict)


def test_invalid_parameters():
    """
    测试无效参数
    """
    analyzer = AlphaBetaAnalyzer()
    
    # 测试无效的quantile值
    sample_data = pd.DataFrame(
        [[1, 2, 3], [4, 5, 6]],
        index=pd.date_range('2020-01-01', '2020-01-02'),
        columns=['A', 'B', 'C']
    )
    
    with pytest.raises(ValueError):
        analyzer.compute_factor_returns(sample_data, sample_data, quantile=0)
    
    # 测试无效的period值
    factor_returns = pd.Series([0.01, 0.02, 0.03], index=pd.date_range('2020-01-01', '2020-01-03'))
    benchmark_returns = pd.Series([0.005, 0.006, 0.007], index=pd.date_range('2020-01-01', '2020-01-03'))
    
    with pytest.raises(ValueError):
        analyzer.compute_alpha_by_period(factor_returns, benchmark_returns, period='invalid')
