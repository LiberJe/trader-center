"""
因子系统基础测试

测试因子库和因子挖掘的基本功能。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from trader_center.factor_library import BaseFactor, FactorRegistry, register_factor
from trader_center.factor_library.technical.momentum import MomentumFactor, RSIFactor
from trader_center.factor_mining import FactorEngine


class TestFactor(BaseFactor):
    """测试因子"""
    
    name = "test_factor"
    category = "technical"
    description = "测试因子"
    
    def __init__(self, period: int = 10):
        super().__init__(period=period)
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data['close'].pct_change(self.params['period'])


def test_factor_base():
    """测试因子基类"""
    print("测试因子基类...")
    
    factor = TestFactor(period=10)
    
    assert factor.name == "test_factor"
    assert factor.category == "technical"
    assert factor.params == {'period': 10}
    
    dates = pd.date_range('2024-01-01', periods=100)
    data = pd.DataFrame({
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 101,
        'low': np.random.randn(100).cumsum() + 99,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, 100),
    }, index=dates)
    
    result = factor.compute(data)
    
    assert len(result) == 100
    assert result.isna().sum() == 10
    
    print("✓ 因子基类测试通过")


def test_factor_registry():
    """测试因子注册器"""
    print("\n测试因子注册器...")
    
    registry = FactorRegistry()
    
    factor = TestFactor(period=20)
    registry.register(factor)
    
    assert registry.exists('test_factor')
    
    retrieved = registry.get('test_factor')
    assert retrieved.name == 'test_factor'
    assert retrieved.params == {'period': 20}
    
    factors = registry.list_factors()
    assert 'test_factor' in factors
    
    print("✓ 因子注册器测试通过")


def test_factor_engine():
    """测试因子计算引擎"""
    print("\n测试因子计算引擎...")
    
    dates = pd.date_range('2024-01-01', periods=100)
    data = pd.DataFrame({
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 101,
        'low': np.random.randn(100).cumsum() + 99,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, 100),
    }, index=dates)
    
    registry = FactorRegistry()
    registry.register(MomentumFactor(period=20))
    registry.register(RSIFactor(period=14))
    
    engine = FactorEngine(registry=registry)
    
    momentum = engine.compute_factor('momentum', data)
    assert len(momentum) == 100
    
    rsi = engine.compute_factor('rsi', data)
    assert len(rsi) == 100
    
    factors_df = engine.compute_factors(['momentum', 'rsi'], data)
    assert factors_df.shape == (100, 2)
    assert 'momentum' in factors_df.columns
    assert 'rsi' in factors_df.columns
    
    print("✓ 因子计算引擎测试通过")


def test_momentum_factor():
    """测试动量因子"""
    print("\n测试动量因子...")
    
    dates = pd.date_range('2024-01-01', periods=100)
    data = pd.DataFrame({
        'close': np.random.randn(100).cumsum() + 100,
    }, index=dates)
    
    factor = MomentumFactor(period=20)
    result = factor.compute(data)
    
    assert len(result) == 100
    assert result.isna().sum() == 20
    
    print("✓ 动量因子测试通过")


def test_rsi_factor():
    """测试RSI因子"""
    print("\n测试RSI因子...")
    
    dates = pd.date_range('2024-01-01', periods=100)
    data = pd.DataFrame({
        'close': np.random.randn(100).cumsum() + 100,
    }, index=dates)
    
    factor = RSIFactor(period=14)
    result = factor.compute(data)
    
    assert len(result) == 100
    assert result.min() >= 0
    assert result.max() <= 100
    
    print("✓ RSI因子测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("因子系统基础功能测试")
    print("=" * 60)
    
    test_factor_base()
    test_factor_registry()
    test_factor_engine()
    test_momentum_factor()
    test_rsi_factor()
    
    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
