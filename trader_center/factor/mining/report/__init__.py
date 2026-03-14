"""
因子评价报告模块

提供基于alphalens的专业因子分析和报告生成功能。
"""

from .alphalens_adapter import AlphalensAdapter
from .data_converter import DataConverter
from .generator import FactorReportGenerator

__all__ = [
    'AlphalensAdapter',
    'DataConverter',
    'FactorReportGenerator',
]
