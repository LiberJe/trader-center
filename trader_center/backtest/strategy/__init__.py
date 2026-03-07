"""策略模块"""
from .base import BaseStrategy
from .asset_allocation import EqualWeightAssetAllocation, ASSET_CONFIG

__all__ = ["BaseStrategy", "EqualWeightAssetAllocation", "ASSET_CONFIG"]
