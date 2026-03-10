"""
因子系统使用示例

演示如何使用因子库和因子挖掘功能。
"""

import pandas as pd
import numpy as np
from datetime import datetime

from trader_center.factor_library import (
    BaseFactor,
    FactorRegistry,
    register_factor,
    get_factor,
    list_factors,
)
from trader_center.factor_library.technical.momentum import (
    MomentumFactor,
    RSIFactor,
    MACDFactor,
)
from trader_center.factor_library.technical.volatility import (
    ATRFactor,
    HistoricalVolatilityFactor,
)
from trader_center.factor_mining import FactorEngine
from trader_center.factor_mining.preprocessing.standardization import (
    standardize_cross_sectional,
    ZScoreStandardizer,
)
from trader_center.factor_mining.preprocessing.winsorization import (
    winsorize_cross_sectional,
    MADWinsorizer,
)


def create_sample_data():
    """创建示例数据"""
    dates = pd.date_range('2023-01-01', '2024-12-31', freq='D')
    n_days = len(dates)
    
    np.random.seed(42)
    
    data = pd.DataFrame({
        'open': np.random.randn(n_days).cumsum() + 100,
        'high': np.random.randn(n_days).cumsum() + 101,
        'low': np.random.randn(n_days).cumsum() + 99,
        'close': np.random.randn(n_days).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, n_days),
    }, index=dates)
    
    data['high'] = data[['open', 'close', 'high']].max(axis=1)
    data['low'] = data[['open', 'close', 'low']].min(axis=1)
    
    return data


def example_1_basic_factor():
    """示例1: 基础因子使用"""
    print("\n" + "="*60)
    print("示例1: 基础因子使用")
    print("="*60)
    
    data = create_sample_data()
    
    momentum = MomentumFactor(period=20)
    momentum_values = momentum.compute(data)
    
    print(f"\n动量因子 (20日):")
    print(f"  名称: {momentum.name}")
    print(f"  类别: {momentum.category}")
    print(f"  描述: {momentum.description}")
    print(f"  最新值: {momentum_values.iloc[-1]:.4f}")
    print(f"  均值: {momentum_values.mean():.4f}")
    print(f"  标准差: {momentum_values.std():.4f}")
    
    rsi = RSIFactor(period=14)
    rsi_values = rsi.compute(data)
    
    print(f"\nRSI因子 (14日):")
    print(f"  最新值: {rsi_values.iloc[-1]:.2f}")
    print(f"  均值: {rsi_values.mean():.2f}")
    print(f"  超买天数: {(rsi_values > 70).sum()}")
    print(f"  超卖天数: {(rsi_values < 30).sum()}")


def example_2_factor_registry():
    """示例2: 因子注册器"""
    print("\n" + "="*60)
    print("示例2: 因子注册器")
    print("="*60)
    
    registry = FactorRegistry()
    
    registry.register(MomentumFactor(period=20))
    registry.register(RSIFactor(period=14))
    registry.register(ATRFactor(period=14))
    
    print(f"\n已注册因子数量: {len(registry)}")
    print(f"已注册因子列表: {registry.list_factors()}")
    
    factor = registry.get('momentum')
    print(f"\n获取因子: {factor}")
    print(f"因子元数据: {factor.get_metadata()}")


def example_3_factor_engine():
    """示例3: 因子计算引擎"""
    print("\n" + "="*60)
    print("示例3: 因子计算引擎")
    print("="*60)
    
    data = create_sample_data()
    
    registry = FactorRegistry()
    registry.register(MomentumFactor(period=20))
    registry.register(RSIFactor(period=14))
    registry.register(ATRFactor(period=14))
    registry.register(HistoricalVolatilityFactor(period=20))
    
    engine = FactorEngine(registry=registry, enable_cache=True)
    
    momentum = engine.compute_factor('momentum', data)
    print(f"\n单个因子计算:")
    print(f"  动量因子最新值: {momentum.iloc[-1]:.4f}")
    
    factors_df = engine.compute_factors(
        ['momentum', 'rsi', 'atr', 'historical_volatility'],
        data,
        parallel=False
    )
    
    print(f"\n批量因子计算:")
    print(f"  因子数量: {len(factors_df.columns)}")
    print(f"  数据形状: {factors_df.shape}")
    print(f"\n最新因子值:")
    print(factors_df.iloc[-1].to_string())
    
    cache_info = engine.get_cache_info()
    print(f"\n缓存信息:")
    print(f"  缓存大小: {cache_info['cache_size']}")
    print(f"  最大缓存: {cache_info['max_cache_size']}")


def example_4_preprocessing():
    """示例4: 因子预处理"""
    print("\n" + "="*60)
    print("示例4: 因子预处理")
    print("="*60)
    
    data = create_sample_data()
    
    momentum = MomentumFactor(period=20)
    factor_values = momentum.compute(data)
    
    print(f"\n原始因子值:")
    print(f"  均值: {factor_values.mean():.4f}")
    print(f"  标准差: {factor_values.std():.4f}")
    print(f"  最小值: {factor_values.min():.4f}")
    print(f"  最大值: {factor_values.max():.4f}")
    
    standardizer = ZScoreStandardizer()
    standardized = standardizer.fit_transform(factor_values.dropna())
    
    print(f"\n标准化后:")
    print(f"  均值: {standardized.mean():.4f}")
    print(f"  标准差: {standardized.std():.4f}")
    print(f"  最小值: {standardized.min():.4f}")
    print(f"  最大值: {standardized.max():.4f}")
    
    winsorizer = MADWinsorizer(threshold=3.0)
    winsorized = winsorizer.fit_transform(factor_values.dropna())
    
    print(f"\n去极值后:")
    print(f"  均值: {winsorized.mean():.4f}")
    print(f"  标准差: {winsorized.std():.4f}")
    print(f"  最小值: {winsorized.min():.4f}")
    print(f"  最大值: {winsorized.max():.4f}")


def example_5_custom_factor():
    """示例5: 自定义因子"""
    print("\n" + "="*60)
    print("示例5: 自定义因子")
    print("="*60)
    
    class CustomMomentumVolume(BaseFactor):
        """自定义动量成交量因子"""
        
        name = "custom_momentum_volume"
        category = "technical"
        description = "结合动量和成交量的自定义因子"
        
        def __init__(self, period: int = 20):
            super().__init__(period=period)
        
        def compute(self, data: pd.DataFrame) -> pd.Series:
            momentum = data['close'].pct_change(self.params['period'])
            volume_ratio = data['volume'] / data['volume'].rolling(20).mean()
            return momentum * np.log1p(volume_ratio)
    
    data = create_sample_data()
    
    custom_factor = CustomMomentumVolume(period=20)
    result = custom_factor.compute(data)
    
    print(f"\n自定义因子信息:")
    print(f"  名称: {custom_factor.name}")
    print(f"  类别: {custom_factor.category}")
    print(f"  描述: {custom_factor.description}")
    print(f"  最新值: {result.iloc[-1]:.4f}")
    print(f"  均值: {result.mean():.4f}")
    
    registry = FactorRegistry()
    registry.register(custom_factor)
    
    print(f"\n注册后可用因子: {registry.list_factors()}")


def main():
    """运行所有示例"""
    print("="*60)
    print("因子系统使用示例")
    print("="*60)
    
    example_1_basic_factor()
    example_2_factor_registry()
    example_3_factor_engine()
    example_4_preprocessing()
    example_5_custom_factor()
    
    print("\n" + "="*60)
    print("示例运行完成！")
    print("="*60)


if __name__ == "__main__":
    main()
