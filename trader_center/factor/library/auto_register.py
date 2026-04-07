"""
因子自动注册

自动发现并注册所有因子类到 FactorRegistry。
"""

import logging
from typing import List, Dict, Type, Optional

from trader_center.factor.library.base import BaseFactor
from trader_center.factor.library.registry import FactorRegistry

logger = logging.getLogger(__name__)


def get_all_factor_classes() -> List[Type[BaseFactor]]:
    """
    获取所有因子类
    
    Returns:
        因子类列表
    """
    factor_classes = []
    
    try:
        from trader_center.factor.library.technical.momentum import (
            MomentumFactor,
            RSIFactor,
            MACDFactor,
            PriceRateOfChangeFactor,
            MomentumQualityFactor,
            VolumeAdjustedMomentumFactor,
        )
        factor_classes.extend([
            MomentumFactor,
            RSIFactor,
            MACDFactor,
            PriceRateOfChangeFactor,
            MomentumQualityFactor,
            VolumeAdjustedMomentumFactor,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 momentum 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.volatility import (
            ATRFactor,
            HistoricalVolatilityFactor,
            ParkinsonVolatilityFactor,
            GarmanKlassVolatilityFactor,
            VolatilityRatioFactor,
            TrueRangeFactor,
            VolatilityRegimeFactor,
        )
        factor_classes.extend([
            ATRFactor,
            HistoricalVolatilityFactor,
            ParkinsonVolatilityFactor,
            GarmanKlassVolatilityFactor,
            VolatilityRatioFactor,
            TrueRangeFactor,
            VolatilityRegimeFactor,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 volatility 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.trend import TrendStrengthFactor
        factor_classes.append(TrendStrengthFactor)
    except ImportError as e:
        logger.warning(f"无法导入 trend 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.sharpe import (
            SharpeRatioFactor,
            SortinoRatioFactor,
            CalmarRatioFactor,
            InformationRatioFactor,
        )
        factor_classes.extend([
            SharpeRatioFactor,
            SortinoRatioFactor,
            CalmarRatioFactor,
            InformationRatioFactor,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 sharpe 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.drawdown import (
            MaxDrawdownFactor,
            DrawdownDurationFactor,
            AverageDrawdownFactor,
            DrawdownRecoveryFactor,
            UlcerIndexFactor,
            PainIndexFactor,
        )
        factor_classes.extend([
            MaxDrawdownFactor,
            DrawdownDurationFactor,
            AverageDrawdownFactor,
            DrawdownRecoveryFactor,
            UlcerIndexFactor,
            PainIndexFactor,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 drawdown 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.indicators import (
            StochasticKD,
            StochasticKSlow,
            WilliamsR,
            CCIFactor,
            BollingerPosition,
            BollingerWidth,
            BollingerSqueeze,
            DMIPlus,
            DMIMinus,
            ADXTrend,
            SARFactor,
            IchimokuCloud,
            ParabolicSAR,
            TRIXFactor,
            UltimateOscillator,
            AwesomeOscillator,
            KeltnerChannel,
            DonchianChannel,
            ChaikinOscillator,
            ChaikinMoneyFlow,
        )
        factor_classes.extend([
            StochasticKD,
            StochasticKSlow,
            WilliamsR,
            CCIFactor,
            BollingerPosition,
            BollingerWidth,
            BollingerSqueeze,
            DMIPlus,
            DMIMinus,
            ADXTrend,
            SARFactor,
            IchimokuCloud,
            ParabolicSAR,
            TRIXFactor,
            UltimateOscillator,
            AwesomeOscillator,
            KeltnerChannel,
            DonchianChannel,
            ChaikinOscillator,
            ChaikinMoneyFlow,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 indicators 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.ma_extensions import (
            WMAFactor,
            VWMAFactor,
            DEMAFactor,
            TEMAFactor,
            KAMAFactor,
            ALMAFactor,
            HullMAFactor,
            ZLEMAFactor,
        )
        factor_classes.extend([
            WMAFactor,
            VWMAFactor,
            DEMAFactor,
            TEMAFactor,
            KAMAFactor,
            ALMAFactor,
            HullMAFactor,
            ZLEMAFactor,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 ma_extensions 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.statistical import (
            LinearRegressionSlope,
            LinearRegressionAngle,
            LinearRegressionIntercept,
            RSquared,
            CorrelationPriceVolume,
            AutocorrelationFactor,
            SkewnessFactor,
            KurtosisFactor,
            VarianceFactor,
            StandardErrorFactor,
            MeanAbsoluteDeviation,
            MedianPriceFactor,
        )
        factor_classes.extend([
            LinearRegressionSlope,
            LinearRegressionAngle,
            LinearRegressionIntercept,
            RSquared,
            CorrelationPriceVolume,
            AutocorrelationFactor,
            SkewnessFactor,
            KurtosisFactor,
            VarianceFactor,
            StandardErrorFactor,
            MeanAbsoluteDeviation,
            MedianPriceFactor,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 statistical 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.price_volume import (
            EaseOfMovement,
            ForceIndex,
            NegativeVolumeIndex,
            PositiveVolumeIndex,
            VolumeRateOfChange,
            PriceVolumeTrend,
            TradeIntensity,
            VolumeProfile,
            OBVEMFactor,
            VolumeDivergence,
        )
        factor_classes.extend([
            EaseOfMovement,
            ForceIndex,
            NegativeVolumeIndex,
            PositiveVolumeIndex,
            VolumeRateOfChange,
            PriceVolumeTrend,
            TradeIntensity,
            VolumeProfile,
            OBVEMFactor,
            VolumeDivergence,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 price_volume 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.volume import (
            OBVFactor,
            VWAPFactor,
            MFI,
            VolumeOscillator,
            AccumulationDistribution,
        )
        factor_classes.extend([
            OBVFactor,
            VWAPFactor,
            MFI,
            VolumeOscillator,
            AccumulationDistribution,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 volume 因子: {e}")
    
    try:
        from trader_center.factor.library.technical.reversal import (
            RSIReversalFactor,
            StochasticReversalFactor,
            CCIReversalFactor,
            BollingerReversalFactor,
        )
        factor_classes.extend([
            RSIReversalFactor,
            StochasticReversalFactor,
            CCIReversalFactor,
            BollingerReversalFactor,
        ])
    except ImportError as e:
        logger.warning(f"无法导入 reversal 因子: {e}")
    
    return factor_classes


def auto_register_factors(
    registry: FactorRegistry = None,
    default_params: Dict = None,
    factor_classes: List[Type[BaseFactor]] = None,
) -> List[str]:
    """
    自动注册所有因子
    
    Args:
        registry: 因子注册器，默认使用全局单例
        default_params: 默认参数，格式为 {factor_name: {param: value}}
        factor_classes: 要注册的因子类列表，默认为所有可用因子
    
    Returns:
        注册成功的因子名称列表
    
    Example:
        >>> registry = FactorRegistry()
        >>> registered = auto_register_factors(registry)
        >>> print(f"注册了 {len(registered)} 个因子")
    """
    registry = registry or FactorRegistry()
    default_params = default_params or {}
    
    if factor_classes is None:
        factor_classes = get_all_factor_classes()
    
    registered = []
    failed = []
    
    for factor_class in factor_classes:
        try:
            params = default_params.get(factor_class.name, {})
            factor = factor_class(**params)
            registry.register(factor)
            registered.append(factor.name)
            logger.debug(f"注册因子: {factor.name}")
        except Exception as e:
            failed.append((factor_class.__name__, str(e)))
            logger.warning(f"注册因子 {factor_class.__name__} 失败: {e}")
    
    if registered:
        logger.info(f"成功注册 {len(registered)} 个因子")
    
    if failed:
        logger.warning(f"注册失败 {len(failed)} 个因子: {failed}")
    
    return registered


def register_factor_with_params(
    factor_class: Type[BaseFactor],
    registry: FactorRegistry = None,
    **params,
) -> str:
    """
    注册单个因子并指定参数
    
    Args:
        factor_class: 因子类
        registry: 因子注册器
        **params: 因子参数
    
    Returns:
        注册的因子名称
    
    Example:
        >>> from trader_center.factor.library.technical.momentum import MomentumFactor
        >>> name = register_factor_with_params(MomentumFactor, period=20)
    """
    registry = registry or FactorRegistry()
    factor = factor_class(**params)
    registry.register(factor)
    return factor.name


def ensure_factors_registered(
    factor_names: List[str] = None,
    registry: FactorRegistry = None,
) -> bool:
    """
    确保指定因子已注册
    
    如果因子未注册，则自动注册所有因子。
    
    Args:
        factor_names: 需要确保注册的因子名称列表
        registry: 因子注册器
    
    Returns:
        True 如果所有因子都已注册
    """
    registry = registry or FactorRegistry()
    
    if factor_names is None:
        return len(registry.list_factors()) > 0
    
    missing = [name for name in factor_names if not registry.exists(name)]
    
    if missing:
        logger.info(f"发现未注册的因子: {missing}，正在自动注册...")
        auto_register_factors(registry)
    
    return all(registry.exists(name) for name in factor_names)
