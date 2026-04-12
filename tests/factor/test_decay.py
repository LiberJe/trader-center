"""
因子衰减分析模块测试
"""

import pytest
import pandas as pd
import numpy as np
from trader_center.factor.mining.decay import DecayAnalyzer


@pytest.fixture
def sample_factor_data():
    """创建测试用的因子数据"""
    dates = pd.date_range('2020-01-01', '2020-03-01')  # 60天数据
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建因子数据
    data = []
    for i, date in enumerate(dates):
        # 因子值随时间变化
        row = [i*0.1 + j for j in range(len(stocks))]
        data.append(row)
    
    factor_data = pd.DataFrame(data, index=dates, columns=stocks)
    return factor_data


@pytest.fixture
def sample_forward_returns():
    """创建测试用的未来收益数据"""
    dates = pd.date_range('2020-01-01', '2020-03-01')  # 60天数据
    stocks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    # 创建收益数据
    data = []
    for i, date in enumerate(dates):
        # 收益与因子值相关，但随时间衰减
        base_return = 0.01 * (60 - i) / 60  # 衰减效果
        row = [base_return + j*0.001 + np.random.normal(0, 0.01) for j in range(len(stocks))]
        data.append(row)
    
    returns_data = pd.DataFrame(data, index=dates, columns=stocks)
    return returns_data


def test_compute_ic_decay(sample_factor_data, sample_forward_returns):
    """测试计算IC衰减曲线"""
    analyzer = DecayAnalyzer()
    
    ic_decay = analyzer.compute_ic_decay(sample_factor_data, sample_forward_returns)
    assert isinstance(ic_decay, pd.Series)
    assert list(ic_decay.index) == [1, 5, 10, 20, 60]
    assert all(not np.isnan(v) for v in ic_decay.values)


def test_compute_return_decay(sample_factor_data, sample_forward_returns):
    """测试计算收益衰减曲线"""
    analyzer = DecayAnalyzer()
    
    # 测试最高分组
    return_decay_top = analyzer.compute_return_decay(sample_factor_data, sample_forward_returns, quantile=1)
    assert isinstance(return_decay_top, pd.Series)
    assert list(return_decay_top.index) == [1, 5, 10, 20, 60]
    
    # 测试最低分组
    return_decay_bottom = analyzer.compute_return_decay(sample_factor_data, sample_forward_returns, quantile=-1)
    assert isinstance(return_decay_bottom, pd.Series)


def test_compute_half_life(sample_factor_data, sample_forward_returns):
    """测试计算IC半衰期"""
    analyzer = DecayAnalyzer()
    ic_decay = analyzer.compute_ic_decay(sample_factor_data, sample_forward_returns)
    
    half_life = analyzer.compute_half_life(ic_decay)
    assert isinstance(half_life, (float, np.floating))
    assert half_life >= 0


def test_find_optimal_holding_period(sample_factor_data, sample_forward_returns):
    """测试寻找最优持仓周期"""
    analyzer = DecayAnalyzer()
    ic_decay = analyzer.compute_ic_decay(sample_factor_data, sample_forward_returns)
    
    optimal_period = analyzer.find_optimal_holding_period(ic_decay)
    assert isinstance(optimal_period, int)
    assert optimal_period in [1, 5, 10, 20, 60]


def test_get_decay_summary(sample_factor_data, sample_forward_returns):
    """测试获取衰减分析摘要"""
    analyzer = DecayAnalyzer()
    analyzer.compute_ic_decay(sample_factor_data, sample_forward_returns)
    analyzer.compute_return_decay(sample_factor_data, sample_forward_returns)
    
    summary = analyzer.get_decay_summary()
    assert isinstance(summary, dict)
    assert 'ic_decay' in summary
    assert 'return_decay' in summary
    assert 'half_life' in summary
    assert 'optimal_holding_period' in summary
    assert 'decay_score' in summary


def test_edge_cases():
    """测试边界情况"""
    analyzer = DecayAnalyzer()
    
    # 测试空数据
    empty_data = pd.DataFrame()
    empty_returns = pd.DataFrame()
    
    ic_decay = analyzer.compute_ic_decay(empty_data, empty_returns)
    assert isinstance(ic_decay, pd.Series)
    assert all(np.isnan(v) for v in ic_decay.values)
    
    # 测试数据不足
    short_data = pd.DataFrame(
        [[1, 2, 3], [4, 5, 6]],
        index=pd.date_range('2020-01-01', '2020-01-02'),
        columns=['A', 'B', 'C']
    )
    short_returns = short_data.copy()
    
    ic_decay = analyzer.compute_ic_decay(short_data, short_returns, periods=[1, 5])
    assert isinstance(ic_decay, pd.Series)


def test_invalid_parameters():
    """测试无效参数"""
    analyzer = DecayAnalyzer()
    
    # 测试无效的相关性方法
    factor_series = pd.Series([1, 2, 3, 4, 5], index=['A', 'B', 'C', 'D', 'E'])
    return_series = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5], index=['A', 'B', 'C', 'D', 'E'])
    
    with pytest.raises(ValueError):
        analyzer.compute_ic(factor_series, return_series, method='invalid')
    
    # 测试无效的quantile值
    sample_data = pd.DataFrame(
        [[1, 2, 3], [4, 5, 6]],
        index=pd.date_range('2020-01-01', '2020-01-02'),
        columns=['A', 'B', 'C']
    )
    
    with pytest.raises(ValueError):
        analyzer.compute_return_decay(sample_data, sample_data, quantile=0)


def test_get_decay_summary_error():
    """测试未计算衰减时的错误"""
    analyzer = DecayAnalyzer()
    
    with pytest.raises(ValueError):
        analyzer.get_decay_summary()
