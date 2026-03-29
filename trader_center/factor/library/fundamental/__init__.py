"""
基本面因子

包含估值、质量、成长、财务健康、现金流、分红等基本面分析因子。
"""

from trader_center.factor.library.fundamental.valuation import (
    PEFactor,
    PBFactor,
    PSFactor,
    EVEBITDAFactor,
    PEGFactor,
    PCFFactor,
)
from trader_center.factor.library.fundamental.quality import (
    ROEFactor,
    ROAFactor,
    GrossMarginFactor,
    NetMarginFactor,
    AssetTurnoverFactor,
    GrossProfitabilityFactor,
)
from trader_center.factor.library.fundamental.growth import (
    RevenueGrowthFactor,
    EarningsGrowthFactor,
    EPSGrowthFactor,
    AssetGrowthFactor,
    OCFGrowthFactor,
)
from trader_center.factor.library.fundamental.financial_health import (
    DebtRatioFactor,
    CurrentRatioFactor,
    QuickRatioFactor,
    InterestCoverageFactor,
    AltmanZScoreFactor,
    PiotroskiFScoreFactor,
    CashRatioFactor,
)
from trader_center.factor.library.fundamental.cashflow import (
    FCFYieldFactor,
    OCFToNetIncomeFactor,
    CashConversionCycleFactor,
    CapExRatioFactor,
)
from trader_center.factor.library.fundamental.dividend import (
    DividendYieldFactor,
    PayoutRatioFactor,
    DividendGrowthFactor,
)

__all__ = [
    'PEFactor',
    'PBFactor',
    'PSFactor',
    'EVEBITDAFactor',
    'PEGFactor',
    'PCFFactor',
    'ROEFactor',
    'ROAFactor',
    'GrossMarginFactor',
    'NetMarginFactor',
    'AssetTurnoverFactor',
    'GrossProfitabilityFactor',
    'RevenueGrowthFactor',
    'EarningsGrowthFactor',
    'EPSGrowthFactor',
    'AssetGrowthFactor',
    'OCFGrowthFactor',
    'DebtRatioFactor',
    'CurrentRatioFactor',
    'QuickRatioFactor',
    'InterestCoverageFactor',
    'AltmanZScoreFactor',
    'PiotroskiFScoreFactor',
    'CashRatioFactor',
    'FCFYieldFactor',
    'OCFToNetIncomeFactor',
    'CashConversionCycleFactor',
    'CapExRatioFactor',
    'DividendYieldFactor',
    'PayoutRatioFactor',
    'DividendGrowthFactor',
]
