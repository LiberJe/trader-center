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
from .risk_parity import RiskParityStrategy4A, LEG_CONFIG
from .risk_parity_math import (
    ledoit_wolf_cov,
    erc_weights,
    erc_weights_with_cap,
    risk_contributions,
)

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
    "RiskParityStrategy4A",
    "LEG_CONFIG",
    "ledoit_wolf_cov",
    "erc_weights",
    "erc_weights_with_cap",
    "risk_contributions",
]
