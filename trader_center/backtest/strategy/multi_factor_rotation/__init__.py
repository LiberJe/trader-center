"""
多因子轮动策略模块

基于多因子打分的资产轮动策略，支持灵活配置。
"""

from .config import ASSET_CONFIG, MultiFactorRotationConfig
from .index import MultiFactorRotationStrategy

__all__ = [
    "MultiFactorRotationStrategy",
    "MultiFactorRotationConfig",
    "ASSET_CONFIG",
]
