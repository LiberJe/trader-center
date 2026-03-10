"""
波动率因子

包含ATR、历史波动率、Parkinson波动率等波动率相关因子。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class ATRFactor(BaseFactor):
    """
    平均真实波幅因子 (ATR)
    
    衡量市场波动性的指标。
    
    Params:
        period: 计算周期，默认14天
    """
    
    name = "atr"
    category = "technical"
    description = "平均真实波幅因子"
    
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
        计算ATR因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            ATR值Series
        """
        period = self.params['period']
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period, min_periods=period).mean()
        
        return atr


class HistoricalVolatilityFactor(BaseFactor):
    """
    历史波动率因子
    
    基于收益率标准差计算的波动率。
    
    Params:
        period: 计算周期，默认20天
        annualize: 是否年化，默认True
        trading_days: 年交易日数，默认252
    """
    
    name = "historical_volatility"
    category = "technical"
    description = "历史波动率因子"
    
    def __init__(
        self,
        period: int = 20,
        annualize: bool = True,
        trading_days: int = 252,
    ):
        super().__init__(
            period=period,
            annualize=annualize,
            trading_days=trading_days,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
        if self.params['trading_days'] <= 0:
            raise ValueError("trading_days 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算历史波动率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            历史波动率值Series
        """
        period = self.params['period']
        annualize = self.params['annualize']
        trading_days = self.params['trading_days']
        
        close = data['close']
        returns = close.pct_change()
        
        volatility = returns.rolling(window=period).std()
        
        if annualize:
            volatility = volatility * np.sqrt(trading_days)
        
        return volatility


class ParkinsonVolatilityFactor(BaseFactor):
    """
    Parkinson波动率因子
    
    基于高低价计算的波动率，对价格跳跃不敏感。
    
    Params:
        period: 计算周期，默认20天
        annualize: 是否年化，默认True
        trading_days: 年交易日数，默认252
    """
    
    name = "parkinson_volatility"
    category = "technical"
    description = "Parkinson波动率因子"
    
    def __init__(
        self,
        period: int = 20,
        annualize: bool = True,
        trading_days: int = 252,
    ):
        super().__init__(
            period=period,
            annualize=annualize,
            trading_days=trading_days,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算Parkinson波动率因子
        
        Args:
            data: 包含high、low列的DataFrame
        
        Returns:
            Parkinson波动率值Series
        """
        period = self.params['period']
        annualize = self.params['annualize']
        trading_days = self.params['trading_days']
        
        high = data['high']
        low = data['low']
        
        hl_ratio = np.log(high / low)
        hl_ratio_sq = hl_ratio ** 2
        
        k = 1 / (4 * np.log(2))
        
        parkinson_vol = np.sqrt(
            k * hl_ratio_sq.rolling(window=period).mean()
        )
        
        if annualize:
            parkinson_vol = parkinson_vol * np.sqrt(trading_days)
        
        return parkinson_vol


class GarmanKlassVolatilityFactor(BaseFactor):
    """
    Garman-Klass波动率因子
    
    结合开盘价、收盘价、最高价、最低价计算的波动率。
    
    Params:
        period: 计算周期，默认20天
        annualize: 是否年化，默认True
        trading_days: 年交易日数，默认252
    """
    
    name = "garman_klass_volatility"
    category = "technical"
    description = "Garman-Klass波动率因子"
    
    def __init__(
        self,
        period: int = 20,
        annualize: bool = True,
        trading_days: int = 252,
    ):
        super().__init__(
            period=period,
            annualize=annualize,
            trading_days=trading_days,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算Garman-Klass波动率因子
        
        Args:
            data: 包含open、high、low、close列的DataFrame
        
        Returns:
            Garman-Klass波动率值Series
        """
        period = self.params['period']
        annualize = self.params['annualize']
        trading_days = self.params['trading_days']
        
        open_price = data['open']
        high = data['high']
        low = data['low']
        close = data['close']
        
        hl_ratio = np.log(high / low)
        co_ratio = np.log(close / open_price)
        
        gk = 0.5 * hl_ratio ** 2 - (2 * np.log(2) - 1) * co_ratio ** 2
        
        gk_vol = np.sqrt(gk.rolling(window=period).mean())
        
        if annualize:
            gk_vol = gk_vol * np.sqrt(trading_days)
        
        return gk_vol


class VolatilityRatioFactor(BaseFactor):
    """
    波动率比率因子
    
    短期波动率与长期波动率的比值，用于判断波动率的变化趋势。
    
    Params:
        short_period: 短期周期，默认10天
        long_period: 长期周期，默认60天
    """
    
    name = "volatility_ratio"
    category = "technical"
    description = "波动率比率因子"
    
    def __init__(self, short_period: int = 10, long_period: int = 60):
        super().__init__(short_period=short_period, long_period=long_period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['short_period'] <= 0:
            raise ValueError("short_period 必须大于0")
        if self.params['long_period'] <= 0:
            raise ValueError("long_period 必须大于0")
        if self.params['short_period'] >= self.params['long_period']:
            raise ValueError("short_period 必须小于 long_period")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算波动率比率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            波动率比率值Series
        """
        short_period = self.params['short_period']
        long_period = self.params['long_period']
        
        close = data['close']
        returns = close.pct_change()
        
        short_vol = returns.rolling(window=short_period).std()
        long_vol = returns.rolling(window=long_period).std()
        
        vol_ratio = short_vol / long_vol
        
        return vol_ratio


class TrueRangeFactor(BaseFactor):
    """
    真实波幅因子 (TR)
    
    衡量单日价格波动的最大范围。
    """
    
    name = "true_range"
    category = "technical"
    description = "真实波幅因子"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算真实波幅因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            真实波幅值Series
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr


class VolatilityRegimeFactor(BaseFactor):
    """
    波动率状态因子
    
    判断当前处于高波动还是低波动状态。
    
    Params:
        period: 计算周期，默认20天
        threshold: 高波动阈值（标准差倍数），默认1.5
    """
    
    name = "volatility_regime"
    category = "technical"
    description = "波动率状态因子"
    
    def __init__(self, period: int = 20, threshold: float = 1.5):
        super().__init__(period=period, threshold=threshold)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算波动率状态因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            波动率状态值Series (1: 高波动, 0: 正常, -1: 低波动)
        """
        period = self.params['period']
        threshold = self.params['threshold']
        
        close = data['close']
        returns = close.pct_change()
        
        current_vol = returns.rolling(window=period).std()
        
        avg_vol = current_vol.rolling(window=period * 3).mean()
        vol_std = current_vol.rolling(window=period * 3).std()
        
        regime = pd.Series(0, index=data.index)
        
        high_vol_threshold = avg_vol + threshold * vol_std
        low_vol_threshold = avg_vol - threshold * vol_std
        
        regime[current_vol >= high_vol_threshold] = 1
        regime[current_vol <= low_vol_threshold] = -1
        
        return regime
