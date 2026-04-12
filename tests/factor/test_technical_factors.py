"""
技术因子测试

测试技术因子的计算和功能。
"""

import pandas as pd
import numpy as np
import pytest

from trader_center.factor.library.technical.reversal import BiasFactor


@pytest.fixture
def sample_data():
    """创建测试数据"""
    dates = pd.date_range('2020-01-01', periods=30, freq='B')
    close = pd.Series(
        [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 
         110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 
         120, 121, 122, 123, 124, 125, 126, 127, 128, 129],
        index=dates
    )
    data = pd.DataFrame({'close': close})
    return data


def test_bias_factor_basic(sample_data):
    """测试Bias因子的基本计算"""
    factor = BiasFactor(period=5)
    result = factor.compute(sample_data)
    
    # 验证结果类型
    assert isinstance(result, pd.Series)
    assert len(result) == len(sample_data)
    
    # 验证前4个值为NaN（因为周期为5）
    assert all(pd.isna(result.iloc[:4]))
    
    # 计算第5天的预期值
    # 前5天的平均值：(100+101+102+103+104)/5 = 102
    # 第5天收盘价：104
    # 乖离率：(104-102)/102 * 100 ≈ 1.9608%
    expected = (104 - 102) / 102 * 100
    assert abs(result.iloc[4] - expected) < 0.0001


def test_bias_factor_different_ma_types(sample_data):
    """测试不同移动平均线类型的Bias因子"""
    # 测试简单移动平均
    factor_sma = BiasFactor(period=5, ma_type="sma")
    result_sma = factor_sma.compute(sample_data)
    
    # 测试指数移动平均
    factor_ema = BiasFactor(period=5, ma_type="ema")
    result_ema = factor_ema.compute(sample_data)
    
    # 测试加权移动平均
    factor_wma = BiasFactor(period=5, ma_type="wma")
    result_wma = factor_wma.compute(sample_data)
    
    # 验证结果类型
    assert isinstance(result_sma, pd.Series)
    assert isinstance(result_ema, pd.Series)
    assert isinstance(result_wma, pd.Series)
    
    # 验证不同移动平均线类型的结果不同
    assert not result_sma.equals(result_ema)
    assert not result_sma.equals(result_wma)
    assert not result_ema.equals(result_wma)


def test_bias_factor_invalid_params():
    """测试无效参数"""
    # 测试无效的周期参数
    with pytest.raises(ValueError, match="period 必须大于0"):
        BiasFactor(period=0)
    
    # 测试无效的移动平均线类型
    with pytest.raises(ValueError, match="ma_type 必须是 'sma', 'ema' 或 'wma'"):
        BiasFactor(ma_type="invalid")


def test_bias_factor_metadata():
    """测试Bias因子的元数据"""
    factor = BiasFactor(period=10, ma_type="ema")
    metadata = factor.get_metadata()
    
    assert metadata['name'] == "bias"
    assert metadata['category'] == "technical"
    assert metadata['description'] == "价格乖离率因子"
    assert metadata['params']['period'] == 10
    assert metadata['params']['ma_type'] == "ema"
    assert metadata['required_data'] == ['close']


def test_bias_factor_validation(sample_data):
    """测试数据验证"""
    factor = BiasFactor()
    
    # 测试有效数据
    assert factor.validate_data(sample_data)
    
    # 测试缺少close列的数据
    data_without_close = sample_data.drop('close', axis=1)
    with pytest.raises(ValueError, match="数据缺少必需字段"):
        factor.validate_data(data_without_close)


def test_bias_factor_set_params():
    """测试设置参数"""
    factor = BiasFactor(period=20)
    assert factor.params['period'] == 20
    
    # 更新参数
    factor.set_params(period=30, ma_type="wma")
    assert factor.params['period'] == 30
    assert factor.params['ma_type'] == "wma"
    
    # 测试设置无效参数
    with pytest.raises(ValueError, match="period 必须大于0"):
        factor.set_params(period=-1)
