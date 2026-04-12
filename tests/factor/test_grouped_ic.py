"""
分组IC分析模块测试
"""

import pytest
import pandas as pd
import numpy as np
from trader_center.factor.mining.grouped_ic import GroupedICAnalyzer


@pytest.fixture
def sample_factor_data():
    """创建测试用的因子数据"""
    dates = pd.date_range('2020-01-01', '2020-01-10')
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
    dates = pd.date_range('2020-01-01', '2020-01-10')
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建收益数据
    data = []
    for i, date in enumerate(dates):
        # 收益与因子值相关
        row = [i*0.01 + j*0.001 + np.random.normal(0, 0.01) for j in range(len(stocks))]
        data.append(row)
    
    returns_data = pd.DataFrame(data, index=dates, columns=stocks)
    return returns_data


@pytest.fixture
def sample_sector_data():
    """创建测试用的行业数据"""
    dates = pd.date_range('2020-01-01', '2020-01-10')
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建行业数据
    sectors = ['Tech', 'Finance', 'Healthcare', 'Tech', 'Finance', 
               'Healthcare', 'Tech', 'Finance', 'Healthcare', 'Tech']
    data = [sectors for _ in range(len(dates))]
    
    sector_data = pd.DataFrame(data, index=dates, columns=stocks)
    return sector_data


@pytest.fixture
def sample_market_cap_data():
    """创建测试用的市值数据"""
    dates = pd.date_range('2020-01-01', '2020-01-10')
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建市值数据
    market_caps = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    data = [market_caps for _ in range(len(dates))]
    
    market_cap_data = pd.DataFrame(data, index=dates, columns=stocks)
    return market_cap_data


def test_compute_ic_by_sector(sample_factor_data, sample_forward_returns, sample_sector_data):
    """测试按行业计算IC"""
    analyzer = GroupedICAnalyzer()
    
    ic_by_sector = analyzer.compute_ic_by_sector(
        sample_factor_data, 
        sample_forward_returns, 
        sample_sector_data
    )
    
    assert isinstance(ic_by_sector, dict)
    assert 'Tech' in ic_by_sector
    assert 'Finance' in ic_by_sector
    assert 'Healthcare' in ic_by_sector
    assert isinstance(ic_by_sector['Tech'], pd.Series)


def test_compute_ic_by_market_cap(sample_factor_data, sample_forward_returns, sample_market_cap_data):
    """测试按市值计算IC"""
    analyzer = GroupedICAnalyzer()
    
    ic_by_cap = analyzer.compute_ic_by_market_cap(
        sample_factor_data, 
        sample_forward_returns, 
        sample_market_cap_data
    )
    
    assert isinstance(ic_by_cap, dict)
    assert len(ic_by_cap) == 5  # 默认5个分组
    assert all('cap_group_' in key for key in ic_by_cap.keys())


def test_compute_ic_by_volatility(sample_factor_data, sample_forward_returns, sample_market_cap_data):
    """测试按波动率计算IC"""
    analyzer = GroupedICAnalyzer()
    
    # 使用市值数据模拟波动率数据
    ic_by_vol = analyzer.compute_ic_by_volatility(
        sample_factor_data, 
        sample_forward_returns, 
        sample_market_cap_data
    )
    
    assert isinstance(ic_by_vol, dict)
    assert len(ic_by_vol) == 5  # 默认5个分组
    assert all('vol_group_' in key for key in ic_by_vol.keys())


def test_compute_ic_by_double_group(sample_factor_data, sample_forward_returns, sample_sector_data, sample_market_cap_data):
    """测试双维度分组计算IC"""
    analyzer = GroupedICAnalyzer()
    
    ic_by_double = analyzer.compute_ic_by_double_group(
        sample_factor_data, 
        sample_forward_returns, 
        sample_sector_data, 
        sample_market_cap_data
    )
    
    assert isinstance(ic_by_double, dict)
    assert all(isinstance(key, tuple) for key in ic_by_double.keys())
    assert all(len(key) == 2 for key in ic_by_double.keys())


def test_find_best_environment(sample_factor_data, sample_forward_returns, sample_sector_data):
    """测试识别因子最佳使用环境"""
    analyzer = GroupedICAnalyzer()
    ic_by_sector = analyzer.compute_ic_by_sector(
        sample_factor_data, 
        sample_forward_returns, 
        sample_sector_data
    )
    
    best_env = analyzer.find_best_environment(ic_by_sector)
    assert isinstance(best_env, dict)
    assert all('ic_mean' in value for value in best_env.values())
    assert all('icir' in value for value in best_env.values())


def test_get_group_summary(sample_factor_data, sample_forward_returns, sample_sector_data):
    """测试获取分组IC摘要"""
    analyzer = GroupedICAnalyzer()
    ic_by_sector = analyzer.compute_ic_by_sector(
        sample_factor_data, 
        sample_forward_returns, 
        sample_sector_data
    )
    
    summary = analyzer.get_group_summary(ic_by_sector)
    assert isinstance(summary, pd.DataFrame)
    assert 'group' in summary.columns
    assert 'ic_mean' in summary.columns
    assert 'icir' in summary.columns
    assert 'positive_ratio' in summary.columns


def test_edge_cases():
    """测试边界情况"""
    analyzer = GroupedICAnalyzer()
    
    # 测试空数据
    empty_data = pd.DataFrame()
    empty_returns = pd.DataFrame()
    empty_sector = pd.DataFrame()
    
    ic_by_sector = analyzer.compute_ic_by_sector(empty_data, empty_returns, empty_sector)
    assert isinstance(ic_by_sector, dict)
    assert len(ic_by_sector) == 0
    
    # 测试数据不匹配
    dates1 = pd.date_range('2020-01-01', '2020-01-05')
    dates2 = pd.date_range('2020-01-06', '2020-01-10')
    
    data1 = pd.DataFrame(np.random.randn(5, 3), index=dates1, columns=['A', 'B', 'C'])
    data2 = pd.DataFrame(np.random.randn(5, 3), index=dates2, columns=['A', 'B', 'C'])
    
    ic_by_sector = analyzer.compute_ic_by_sector(data1, data1, data2)
    assert isinstance(ic_by_sector, dict)
    assert len(ic_by_sector) == 0


def test_invalid_method():
    """测试无效的相关性方法"""
    analyzer = GroupedICAnalyzer()
    
    # 创建测试数据
    factor_series = pd.Series([1, 2, 3, 4, 5], index=['A', 'B', 'C', 'D', 'E'])
    return_series = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5], index=['A', 'B', 'C', 'D', 'E'])
    
    with pytest.raises(ValueError):
        analyzer.compute_ic(factor_series, return_series, method='invalid')
