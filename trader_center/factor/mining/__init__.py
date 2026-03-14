"""
因子挖掘

提供因子计算、分析、预处理、自动生成、组合优化和评价报告功能。
"""

from .engine import FactorEngine
from .evaluator import FactorEvaluator, FactorMetrics, FactorReport
from .pipeline import FactorMiningPipeline, MiningConfig, MiningResult, run_factor_mining
from .combination import FactorCombiner, CombinationResult, create_factor_portfolio

__all__ = [
    'FactorEngine',
    'FactorEvaluator',
    'FactorMetrics',
    'FactorReport',
    'FactorMiningPipeline',
    'MiningConfig',
    'MiningResult',
    'run_factor_mining',
    'FactorCombiner',
    'CombinationResult',
    'create_factor_portfolio',
]
