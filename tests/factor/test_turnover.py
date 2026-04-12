"""
换手率分析模块测试
"""

import pytest
import pandas as pd
import numpy as np
from trader_center.factor.mining.turnover import TurnoverAnalyzer


@pytest.fixture
def sample_factor_data():
    """创建测试用的因子数据"""
    dates = pd.date_range('2020-01-01', '2020-01-10')
    stocks = ['A', 'B', 'C', 'D', 'E']
    
    # 创建因子数据
    data = []
    for i, date in enumerate(dates):
        # 每个日期生成不同的因子值
        row = [i*0.1 + j for j in range(len(stocks))]
        data.append(row)
    
    factor_data = pd.DataFrame(data, index=dates, columns=stocks)
    return factor_data


def test_compute_factor_turnover(sample_factor_data):
    """测试计算因子整体换手率"""
    analyzer = TurnoverAnalyzer()
    
    # 测试默认持仓周期
    turnover_series = analyzer.compute_factor_turnover(sample_factor_data)
    assert isinstance(turnover_series, pd.Series)
    assert len(turnover_series) == 9  # 10天数据，9个换手率
    assert all(0 <= t <= 1 for t in turnover_series)
    
    # 测试不同持仓周期
    turnover_series_2 = analyzer.compute_factor_turnover(sample_factor_data, holding_period=2)
    assert len(turnover_series_2) == 8  # 10天数据，8个换手率


def test_compute_group_turnover(sample_factor_data):
    """测试计算分组换手率"""
    analyzer = TurnoverAnalyzer()
    
    # 测试默认分组
    group_turnover = analyzer.compute_group_turnover(sample_factor_data)
    assert isinstance(group_turnover, pd.DataFrame)
    assert len(group_turnover) == 9
    assert list(group_turnover.columns) == ['group_1', 'group_2', 'group_3', 'group_4', 'group_5']
    
    # 测试不同分组数量
    group_turnover_3 = analyzer.compute_group_turnover(sample_factor_data, n_groups=3)
    assert list(group_turnover_3.columns) == ['group_1', 'group_2', 'group_3']


def test_compute_top_n_turnover(sample_factor_data):
    """测试计算Top-N换手率"""
    analyzer = TurnoverAnalyzer()
    
    # 测试默认Top-N值
    top_n_turnover = analyzer.compute_top_n_turnover(sample_factor_data)
    assert isinstance(top_n_turnover, dict)
    assert 10 in top_n_turnover
    assert 20 in top_n_turnover
    assert 50 in top_n_turnover
    assert isinstance(top_n_turnover[10], pd.Series)
    
    # 测试自定义Top-N值
    top_n_turnover_custom = analyzer.compute_top_n_turnover(sample_factor_data, n_values=[2, 3])
    assert 2 in top_n_turnover_custom
    assert 3 in top_n_turnover_custom


def test_analyze_turnover_cost(sample_factor_data):
    """测试分析换手率与交易成本的关系"""
    analyzer = TurnoverAnalyzer()
    turnover_series = analyzer.compute_factor_turnover(sample_factor_data)
    
    cost_analysis = analyzer.analyze_turnover_cost(turnover_series)
    assert isinstance(cost_analysis, dict)
    assert 'average_turnover' in cost_analysis
    assert 'annualized_turnover' in cost_analysis
    assert 'average_daily_cost' in cost_analysis
    assert 'annualized_cost' in cost_analysis
    assert 'estimated_holding_period' in cost_analysis


def test_get_turnover_summary(sample_factor_data):
    """测试获取换手率统计摘要"""
    analyzer = TurnoverAnalyzer()
    analyzer.compute_factor_turnover(sample_factor_data)
    
    summary = analyzer.get_turnover_summary()
    assert isinstance(summary, dict)
    assert 'mean_turnover' in summary
    assert 'median_turnover' in summary
    assert 'std_turnover' in summary
    assert 'min_turnover' in summary
    assert 'max_turnover' in summary
    assert 'annualized_turnover' in summary
    assert 'average_daily_cost' in summary
    assert 'annualized_cost' in summary


def test_edge_cases():
    """测试边界情况"""
    analyzer = TurnoverAnalyzer()
    
    # 测试空数据
    empty_data = pd.DataFrame()
    turnover_series = analyzer.compute_factor_turnover(empty_data)
    assert len(turnover_series) == 0
    
    # 测试单只股票
    single_stock_data = pd.DataFrame(
        [[1.0], [2.0], [3.0]],
        index=pd.date_range('2020-01-01', '2020-01-03'),
        columns=['A']
    )
    turnover_series = analyzer.compute_factor_turnover(single_stock_data)
    assert len(turnover_series) == 2
    assert all(turnover_series == 0)  # 单只股票换手率为0


def test_invalid_parameters():
    """测试无效参数"""
    analyzer = TurnoverAnalyzer()
    sample_data = pd.DataFrame(
        [[1.0, 2.0], [3.0, 4.0]],
        index=pd.date_range('2020-01-01', '2020-01-02'),
        columns=['A', 'B']
    )
    
    # 测试无效的持仓周期
    with pytest.raises(ValueError):
        analyzer.compute_factor_turnover(sample_data, holding_period=0)
    
    # 测试无效的分组数量
    with pytest.raises(ValueError):
        analyzer.compute_group_turnover(sample_data, n_groups=1)


def test_get_turnover_summary_error():
    """测试未计算换手率时的错误"""
    analyzer = TurnoverAnalyzer()
    
    with pytest.raises(ValueError):
        analyzer.get_turnover_summary()
