"""
因子库

提供各类因子的定义和注册功能。
"""

from .base import BaseFactor
from .registry import FactorRegistry, register_factor, get_factor, list_factors

__all__ = [
    'BaseFactor',
    'FactorRegistry',
    'register_factor',
    'get_factor',
    'list_factors',
]
