"""策略模块"""
from .base import BaseStrategy
from .asset_allocation import EqualWeightAssetAllocation, ASSET_CONFIG
from .factor_scorer import FactorScorer, DEFAULT_FACTOR_CONFIGS
from .multi_factor_rotation import MultiFactorRotationStrategy, MultiFactorRotationConfig, ASSET_CONFIG as ROTATION_ASSET_CONFIG

__all__ = [
    "BaseStrategy",
    "EqualWeightAssetAllocation",
    "ASSET_CONFIG",
    "FactorScorer",
    "DEFAULT_FACTOR_CONFIGS",
    "MultiFactorRotationStrategy",
    "MultiFactorRotationConfig",
    "ROTATION_ASSET_CONFIG",
]
