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

from .turnover import TurnoverAnalyzer, plot_turnover_series, plot_turnover_distribution, plot_group_turnover, plot_top_n_turnover
from .grouped_ic import GroupedICAnalyzer, plot_grouped_ic_heatmap, plot_ic_by_group_bar, plot_ic_by_group_time_series
from .decay import DecayAnalyzer, plot_ic_decay_curve, plot_return_decay_curve, plot_decay_comparison
from .robustness import RobustnessTester, plot_period_comparison, plot_sector_performance, plot_robustness_heatmap
from .alpha_beta import AlphaBetaAnalyzer, plot_alpha_beta_ts, plot_alpha_distribution, plot_risk_return_scatter

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
    'TurnoverAnalyzer',
    'plot_turnover_series',
    'plot_turnover_distribution',
    'plot_group_turnover',
    'plot_top_n_turnover',
    'GroupedICAnalyzer',
    'plot_grouped_ic_heatmap',
    'plot_ic_by_group_bar',
    'plot_ic_by_group_time_series',
    'DecayAnalyzer',
    'plot_ic_decay_curve',
    'plot_return_decay_curve',
    'plot_decay_comparison',
    'RobustnessTester',
    'plot_period_comparison',
    'plot_sector_performance',
    'plot_robustness_heatmap',
    'AlphaBetaAnalyzer',
    'plot_alpha_beta_ts',
    'plot_alpha_distribution',
    'plot_risk_return_scatter',
]
