"""
技术因子

包含动量、反转、波动率、成交量、趋势、夏普比率、回撤等技术分析因子。
"""

from .momentum import (
    MomentumFactor,
    RSIFactor,
    MACDFactor,
    PriceRateOfChangeFactor,
    MomentumQualityFactor,
    VolumeAdjustedMomentumFactor,
)
from .volatility import (
    ATRFactor,
    HistoricalVolatilityFactor,
    ParkinsonVolatilityFactor,
    GarmanKlassVolatilityFactor,
    VolatilityRatioFactor,
    TrueRangeFactor,
    VolatilityRegimeFactor,
)
from .trend import TrendStrengthFactor
from .sharpe import (
    SharpeRatioFactor,
    SortinoRatioFactor,
    CalmarRatioFactor,
    InformationRatioFactor,
)
from .drawdown import (
    MaxDrawdownFactor,
    DrawdownDurationFactor,
    AverageDrawdownFactor,
    DrawdownRecoveryFactor,
    UlcerIndexFactor,
    PainIndexFactor,
)

__all__ = [
    "MomentumFactor",
    "RSIFactor",
    "MACDFactor",
    "PriceRateOfChangeFactor",
    "MomentumQualityFactor",
    "VolumeAdjustedMomentumFactor",
    "ATRFactor",
    "HistoricalVolatilityFactor",
    "ParkinsonVolatilityFactor",
    "GarmanKlassVolatilityFactor",
    "VolatilityRatioFactor",
    "TrueRangeFactor",
    "VolatilityRegimeFactor",
    "TrendStrengthFactor",
    "SharpeRatioFactor",
    "SortinoRatioFactor",
    "CalmarRatioFactor",
    "InformationRatioFactor",
    "MaxDrawdownFactor",
    "DrawdownDurationFactor",
    "AverageDrawdownFactor",
    "DrawdownRecoveryFactor",
    "UlcerIndexFactor",
    "PainIndexFactor",
]
