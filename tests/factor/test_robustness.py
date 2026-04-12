"""
稳健性测试模块测试
"""

import pytest
import pandas as pd
import numpy as np
from trader_center.factor.mining.robustness import RobustnessTester


@pytest.fixture
def sample_factor_data():
    """创建测试用的因子数据"""
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
    """创建测试用的未来收益数据"""
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
def sample_sector_data():
    """
    创建测试用的行业数据
    """
    dates = pd.date_range('2020-01-01', '2020-06-30')
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建行业数据
    sectors = ['Tech', 'Finance', 'Healthcare', 'Tech', 'Finance', 
               'Healthcare', 'Tech', 'Finance', 'Healthcare', 'Tech']
    data = [sectors for _ in range(len(dates))]
    
    sector_data = pd.DataFrame(data, index=dates, columns=stocks)
    return sector_data


@pytest.fixture
def sample_market_cap_data():
    """
    创建测试用的市值数据
    """
    dates = pd.date_range('2020-01-01', '2020-06-30')
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建市值数据
    market_caps = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    data = [market_caps for _ in range(len(dates))]
    
    market_cap_data = pd.DataFrame(data, index=dates, columns=stocks)
    return market_cap_data


@pytest.fixture
def sample_market_data():
    """
    创建测试用的市场数据
    """
    dates = pd.date_range('2020-01-01', '2020-06-30')
    
    # 创建市场指数数据
    data = []
    value = 1000
    for i, date in enumerate(dates):
        # 模拟市场上涨趋势
        value *= (1 + 0.0005 + np.random.normal(0, 0.01))
        data.append(value)
    
    market_data = pd.Series(data, index=dates, name='market')
    return market_data


def test_test_by_time_period(sample_factor_data, sample_forward_returns, sample_market_data):
    """
    测试分时间段测试
    """
    tester = RobustnessTester()
    
    # 测试带市场数据
    period_results = tester.test_by_time_period(
        sample_factor_data, 
        sample_forward_returns, 
        sample_market_data
    )
    assert isinstance(period_results, dict)
    assert all(key in ['bull', 'bear', 'neutral'] for key in period_results.keys())
    
    # 测试不带市场数据
    period_results_no_market = tester.test_by_time_period(
        sample_factor_data, 
        sample_forward_returns
    )
    assert isinstance(period_results_no_market, dict)
    assert all('period_' in key for key in period_results_no_market.keys())


def test_test_by_market_cap(sample_factor_data, sample_forward_returns, sample_market_cap_data):
    """
    测试分市值测试
    """
    tester = RobustnessTester()
    
    cap_results = tester.test_by_market_cap(
        sample_factor_data, 
        sample_forward_returns, 
        sample_market_cap_data
    )
    
    assert isinstance(cap_results, dict)
    assert len(cap_results) == 3  # 默认3个分组
    assert all('cap_group_' in key for key in cap_results.keys())


def test_test_by_sector(sample_factor_data, sample_forward_returns, sample_sector_data):
    """
    测试分行业测试
    """
    tester = RobustnessTester()
    
    sector_results = tester.test_by_sector(
        sample_factor_data, 
        sample_forward_returns, 
        sample_sector_data
    )
    
    assert isinstance(sector_results, dict)
    assert 'Tech' in sector_results
    assert 'Finance' in sector_results
    assert 'Healthcare' in sector_results


def test_test_rolling_window(sample_factor_data, sample_forward_returns):
    """
    测试滚动窗口测试
    """
    tester = RobustnessTester()
    
    rolling_results = tester.test_rolling_window(
        sample_factor_data, 
        sample_forward_returns
    )
    
    assert isinstance(rolling_results, pd.DataFrame)
    assert 'start_date' in rolling_results.columns
    assert 'end_date' in rolling_results.columns
    assert 'ic_mean' in rolling_results.columns


def test_test_bootstrapping(sample_factor_data, sample_forward_returns):
    """
    测试自助法测试
    """
    tester = RobustnessTester()
    
    bootstrap_results = tester.test_bootstrapping(
        sample_factor_data, 
        sample_forward_returns
    )
    
    assert isinstance(bootstrap_results, dict)
    assert 'mean_ic' in bootstrap_results
    assert 'std_ic' in bootstrap_results
    assert 'icir' in bootstrap_results


def test_get_robustness_score(sample_factor_data, sample_forward_returns, sample_sector_data):
    """
    测试计算稳健性得分
    """
    tester = RobustnessTester()
    sector_results = tester.test_by_sector(
        sample_factor_data, 
        sample_forward_returns, 
        sample_sector_data
    )
    
    robustness_score = tester.get_robustness_score(sector_results)
    assert isinstance(robustness_score, (float, np.floating))
    assert 0 <= robustness_score <= 1


def test_edge_cases():
    """
    测试边界情况
    """
    tester = RobustnessTester()
    
    # 测试空数据
    empty_data = pd.DataFrame()
    empty_returns = pd.DataFrame()
    
    period_results = tester.test_by_time_period(empty_data, empty_returns)
    assert isinstance(period_results, dict)
    assert len(period_results) == 0
    
    # 测试数据不足
    short_data = pd.DataFrame(
        [[1, 2, 3], [4, 5, 6]],
        index=pd.date_range('2020-01-01', '2020-01-02'),
        columns=['A', 'B', 'C']
    )
    
    rolling_results = tester.test_rolling_window(short_data, short_data)
    assert isinstance(rolling_results, pd.DataFrame)
    assert len(rolling_results) == 0


def test_invalid_parameters():
    """
    测试无效参数
    """
    tester = RobustnessTester()
    
    # 测试无效的相关性方法
    factor_series = pd.Series([1, 2, 3, 4, 5], index=['A', 'B', 'C', 'D', 'E'])
    return_series = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5], index=['A', 'B', 'C', 'D', 'E'])
    
    with pytest.raises(ValueError):
        tester.compute_ic(factor_series, return_series, method='invalid')
