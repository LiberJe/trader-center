"""
策略模块
"""
from .base import BaseStrategy
from .asset_allocation import EqualWeightAssetAllocation, ASSET_CONFIG
from .factor_scorer import (
    FactorScorer,
    DEFAULT_FACTOR_CONFIGS,
    ETF_SHARP_FACTOR_CONFIGS,
    DEFAULT_NORMALIZATION_CONFIG,
)
from .multi_factor_rotation import MultiFactorRotationStrategy
from .etf_sharp import ETFSharpStrategy

__all__ = [
    "BaseStrategy",
    "EqualWeightAssetAllocation",
    "ASSET_CONFIG",
    "FactorScorer",
    "DEFAULT_FACTOR_CONFIGS",
    "ETF_SHARP_FACTOR_CONFIGS",
    "DEFAULT_NORMALIZATION_CONFIG",
    "MultiFactorRotationStrategy",
    "ETFSharpStrategy",
]
