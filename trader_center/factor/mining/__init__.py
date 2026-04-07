"""
因子挖掘

提供因子计算、分析、预处理、存储和遗传规划挖掘功能。
"""

from .engine import FactorEngine
from .pipeline import FactorAnalysisPipeline, quick_analyze
from .alphalens_adapter import AlphalensAdapter, check_alphalens_available
from .visualization import FactorVisualizer
from .scoring import FactorScorer, compute_monotonicity
from .report import FactorReport
from .data_adapter import (
    wide_to_dict,
    dict_to_wide,
    prepare_ohlcv_data,
    align_dataframes,
    validate_wide_format,
)

from .genetic_programming import (
    GeneticProgrammingEngine,
    run_factor_mining,
    PrimitiveSet,
    FactorExpression,
    create_default_pset,
)

__all__ = [
    'FactorEngine',
    'FactorAnalysisPipeline',
    'quick_analyze',
    'AlphalensAdapter',
    'check_alphalens_available',
    'FactorVisualizer',
    'FactorScorer',
    'compute_monotonicity',
    'FactorReport',
    'GeneticProgrammingEngine',
    'run_factor_mining',
    'PrimitiveSet',
    'FactorExpression',
    'create_default_pset',
    'wide_to_dict',
    'dict_to_wide',
    'prepare_ohlcv_data',
    'align_dataframes',
    'validate_wide_format',
]
