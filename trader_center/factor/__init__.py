"""
因子模块

提供因子定义、计算、分析和存储功能。
"""

from trader_center.factor.library import (
    BaseFactor,
    FactorRegistry,
    register_factor,
    get_factor,
    list_factors,
)
from trader_center.factor.mining import FactorEngine

__all__ = [
    'BaseFactor',
    'FactorRegistry',
    'register_factor',
    'get_factor',
    'list_factors',
    'FactorEngine',
]
