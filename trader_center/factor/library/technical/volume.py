"""
成交量因子

包含量比、OBV、量价趋势、资金流量指标等成交量相关因子。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class VolumeRatioFactor(BaseFactor):
    """
    量比因子
    
    当前成交量与平均成交量的比值。
    
    Params:
        period: 平均成交量计算周期，默认20天
    """
    
    name = "volume_ratio"
    category = "technical"
    description = "量比因子"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算量比因子
        
        Args:
            data: 包含volume列的DataFrame
        
        Returns:
            量比值Series
        """
        period = self.params['period']
        volume = data['volume']
        
        avg_volume = volume.rolling(window=period).mean()
        
        volume_ratio = volume / avg_volume
        
        return volume_ratio


class OBVFactor(BaseFactor):
    """
    能量潮因子 (OBV)
    
    基于成交量变化的累积指标。
    """
    
    name = "obv"
    category = "technical"
    description = "能量潮因子"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算OBV因子
        
        Args:
            data: 包含close、volume列的DataFrame
        
        Returns:
            OBV值Series
        """
        close = data['close']
        volume = data['volume']
        
        direction = np.where(close > close.shift(1), 1,
                            np.where(close < close.shift(1), -1, 0))
        
        obv = (volume * direction).cumsum()
        
        return pd.Series(obv, index=data.index)


class VolumePriceTrendFactor(BaseFactor):
    """
    量价趋势因子 (VPT)
    
    结合价格变化和成交量的累积指标。
    """
    
    name = "volume_price_trend"
    category = "technical"
    description = "量价趋势因子"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算量价趋势因子
        
        Args:
            data: 包含close、volume列的DataFrame
        
        Returns:
            VPT值Series
        """
        close = data['close']
        volume = data['volume']
        
        price_change_pct = close.pct_change()
        
        vpt = (volume * price_change_pct).cumsum()
        
        return vpt


class MoneyFlowIndexFactor(BaseFactor):
    """
    资金流量指标因子 (MFI)
    
    结合价格和成交量的动量指标。
    
    Params:
        period: 计算周期，默认14天
    """
    
    name = "money_flow_index"
    category = "technical"
    description = "资金流量指标因子"
    
    def __init__(self, period: int = 14):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 14) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算MFI因子
        
        Args:
            data: 包含high、low、close、volume列的DataFrame
        
        Returns:
            MFI值Series (0-100)
        """
        period = self.params['period']
        
        tp = (data['high'] + data['low'] + data['close']) / 3
        
        mf = tp * data['volume']
        
        positive_mf = pd.Series(0.0, index=data.index)
        negative_mf = pd.Series(0.0, index=data.index)
        
        positive_mf[tp > tp.shift(1)] = mf[tp > tp.shift(1)]
        negative_mf[tp < tp.shift(1)] = mf[tp < tp.shift(1)]
        
        positive_mf_sum = positive_mf.rolling(window=period).sum()
        negative_mf_sum = negative_mf.rolling(window=period).sum()
        
        mf_ratio = positive_mf_sum / (positive_mf_sum + negative_mf_sum)
        
        mfi = 100 - (100 / (1 + mf_ratio))
        
        return mfi


class AccumulationDistributionFactor(BaseFactor):
    """
    累积/派发线因子 (A/D)
    
    基于价格位置和成交量的累积指标。
    """
    
    name = "accumulation_distribution"
    category = "technical"
    description = "累积/派发线因子"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算A/D因子
        
        Args:
            data: 包含high、low、close、volume列的DataFrame
        
        Returns:
            A/D值Series
        """
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        
        clv = ((close - low) - (high - close)) / (high - low)
        clv = clv.fillna(0)
        
        ad = (clv * volume).cumsum()
        
        return ad


class VolumeOscillatorFactor(BaseFactor):
    """
    成交量震荡因子
    
    短期和长期成交量均线的差值。
    
    Params:
        short_period: 短期周期，默认5天
        long_period: 长期周期，默认10天
    """
    
    name = "volume_oscillator"
    category = "technical"
    description = "成交量震荡因子"
    
    def __init__(self, short_period: int = 5, long_period: int = 10):
        super().__init__(short_period=short_period, long_period=long_period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['short_period'] <= 0:
            raise ValueError("short_period 必须大于0")
        if self.params['long_period'] <= 0:
            raise ValueError("long_period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算成交量震荡因子
        
        Args:
            data: 包含volume列的DataFrame
        
        Returns:
            成交量震荡值Series
        """
        short_period = self.params['short_period']
        long_period = self.params['long_period']
        
        volume = data['volume']
        
        short_ma = volume.rolling(window=short_period).mean()
        long_ma = volume.rolling(window=long_period).mean()
        
        oscillator = short_ma - long_ma
        
        return oscillator


class VolumeWeightedPriceFactor(BaseFactor):
    """
    成交量加权价格因子 (VWAP)
    
    成交量加权平均价格。
    
    Params:
        period: 计算周期，默认20天
    """
    
    name = "volume_weighted_price"
    category = "technical"
    description = "成交量加权价格因子"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算VWAP因子
        
        Args:
            data: 包含high、low、close、volume列的DataFrame
        
        Returns:
            VWAP值Series
        """
        period = self.params['period']
        
        tp = (data['high'] + data['low'] + data['close']) / 3
        volume = data['volume']
        
        vwap = (tp * volume).rolling(window=period).sum() / \
               volume.rolling(window=period).sum()
        
        return vwap


class VolumeTrendFactor(BaseFactor):
    """
    成交量趋势因子
    
    成交量的变化趋势。
    
    Params:
        period: 计算周期，默认20天
    """
    
    name = "volume_trend"
    category = "technical"
    description = "成交量趋势因子"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算成交量趋势因子
        
        Args:
            data: 包含volume列的DataFrame
        
        Returns:
            成交量趋势值Series
        """
        period = self.params['period']
        volume = data['volume']
        
        volume_ma = volume.rolling(window=period).mean()
        
        volume_trend = (volume - volume_ma) / volume_ma
        
        return volume_trend


class VolumeSpikeFactor(BaseFactor):
    """
    成交量异常因子
    
    检测成交量异常放大的情况。
    
    Params:
        period: 平均成交量计算周期，默认20天
        threshold: 异常阈值（标准差倍数），默认2.0
    """
    
    name = "volume_spike"
    category = "technical"
    description = "成交量异常因子"
    
    def __init__(self, period: int = 20, threshold: float = 2.0):
        super().__init__(period=period, threshold=threshold)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算成交量异常因子
        
        Args:
            data: 包含volume列的DataFrame
        
        Returns:
            成交量异常信号Series (1: 异常放量, 0: 正常)
        """
        period = self.params['period']
        threshold = self.params['threshold']
        
        volume = data['volume']
        
        volume_mean = volume.rolling(window=period).mean()
        volume_std = volume.rolling(window=period).std()
        
        z_score = (volume - volume_mean) / volume_std
        
        spike = pd.Series(0, index=data.index)
        spike[z_score >= threshold] = 1
        
        return spike
