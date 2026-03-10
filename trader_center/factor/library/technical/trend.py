"""
趋势因子

包含移动平均线、EMA、MACD趋势、ADX等趋势相关因子。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class MAFactor(BaseFactor):
    """
    移动平均线因子
    
    简单移动平均线。
    
    Params:
        period: 移动平均周期，默认20天
    """
    
    name = "ma"
    category = "technical"
    description = "移动平均线因子"
    
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
        计算移动平均线因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            MA值Series
        """
        period = self.params['period']
        return data['close'].rolling(window=period).mean()


class EMAFactor(BaseFactor):
    """
    指数移动平均线因子
    
    指数加权移动平均线。
    
    Params:
        period: 移动平均周期，默认20天
    """
    
    name = "ema"
    category = "technical"
    description = "指数移动平均线因子"
    
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
        计算EMA因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            EMA值Series
        """
        period = self.params['period']
        return data['close'].ewm(span=period, adjust=False).mean()


class MACDTrendFactor(BaseFactor):
    """
    MACD趋势因子
    
    基于MACD的趋势判断。
    
    Params:
        fast_period: 快线周期，默认12
        slow_period: 慢线周期，默认26
        signal_period: 信号线周期，默认9
    """
    
    name = "macd_trend"
    category = "technical"
    description = "MACD趋势因子"
    
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        super().__init__(
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['fast_period'] <= 0:
            raise ValueError("fast_period 必须大于0")
        if self.params['slow_period'] <= 0:
            raise ValueError("slow_period 必须大于0")
        if self.params['signal_period'] <= 0:
            raise ValueError("signal_period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算MACD趋势因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            MACD趋势值Series (1: 上升趋势, -1: 下降趋势, 0: 中性)
        """
        close = data['close']
        fast_period = self.params['fast_period']
        slow_period = self.params['slow_period']
        signal_period = self.params['signal_period']
        
        ema_fast = close.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=slow_period, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal
        
        trend = pd.Series(0, index=data.index)
        
        trend[(macd > signal) & (histogram > 0)] = 1
        trend[(macd < signal) & (histogram < 0)] = -1
        
        return trend


class ADXFactor(BaseFactor):
    """
    平均趋向指标因子 (ADX)
    
    衡量趋势的强度。
    
    Params:
        period: 计算周期，默认14天
    """
    
    name = "adx"
    category = "technical"
    description = "平均趋向指标因子"
    
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
        计算ADX因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            ADX值Series (0-100)
        """
        period = self.params['period']
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        adx = dx.rolling(window=period).mean()
        
        return adx


class TrendStrengthFactor(BaseFactor):
    """
    趋势强度因子
    
    基于价格与移动平均线的关系衡量趋势强度。
    
    Params:
        period: 移动平均周期，默认20天
    """
    
    name = "trend_strength"
    category = "technical"
    description = "趋势强度因子"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算趋势强度因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            趋势强度值Series (-1到1)
        """
        period = self.params['period']
        close = data['close']
        
        ma = close.rolling(window=period).mean()
        
        strength = (close - ma) / ma
        
        return strength


class GoldenCrossFactor(BaseFactor):
    """
    金叉死叉因子
    
    基于短期和长期移动平均线的交叉信号。
    
    Params:
        short_period: 短期周期，默认5天
        long_period: 长期周期，默认20天
    """
    
    name = "golden_cross"
    category = "technical"
    description = "金叉死叉因子"
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
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
        计算金叉死叉因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            金叉死叉信号Series (1: 金叉, -1: 死叉, 0: 无信号)
        """
        short_period = self.params['short_period']
        long_period = self.params['long_period']
        
        close = data['close']
        
        short_ma = close.rolling(window=short_period).mean()
        long_ma = close.rolling(window=long_period).mean()
        
        signal = pd.Series(0, index=data.index)
        
        golden_cross = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
        death_cross = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))
        
        signal[golden_cross] = 1
        signal[death_cross] = -1
        
        return signal


class TrendDirectionFactor(BaseFactor):
    """
    趋势方向因子
    
    判断当前的趋势方向。
    
    Params:
        period: 判断周期，默认20天
    """
    
    name = "trend_direction"
    category = "technical"
    description = "趋势方向因子"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算趋势方向因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            趋势方向值Series (1: 上升, -1: 下降, 0: 横盘)
        """
        period = self.params['period']
        close = data['close']
        
        returns = close.pct_change()
        
        positive_returns = (returns > 0).rolling(window=period).sum()
        negative_returns = (returns < 0).rolling(window=period).sum()
        
        direction = pd.Series(0, index=data.index)
        
        threshold = period * 0.6
        direction[positive_returns >= threshold] = 1
        direction[negative_returns >= threshold] = -1
        
        return direction


class PricePositionFactor(BaseFactor):
    """
    价格位置因子
    
    当前价格在N日内的相对位置。
    
    Params:
        period: 计算周期，默认20天
    """
    
    name = "price_position"
    category = "technical"
    description = "价格位置因子"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算价格位置因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            价格位置值Series (0-100)
        """
        period = self.params['period']
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        highest = high.rolling(window=period).max()
        lowest = low.rolling(window=period).min()
        
        position = 100 * (close - lowest) / (highest - lowest)
        
        return position


class SupertrendFactor(BaseFactor):
    """
    超级趋势因子
    
    基于ATR的趋势跟踪指标。
    
    Params:
        period: ATR周期，默认10天
        multiplier: ATR倍数，默认3.0
    """
    
    name = "supertrend"
    category = "technical"
    description = "超级趋势因子"
    
    def __init__(self, period: int = 10, multiplier: float = 3.0):
        super().__init__(period=period, multiplier=multiplier)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
        if self.params['multiplier'] <= 0:
            raise ValueError("multiplier 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算超级趋势因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            超级趋势信号Series (1: 上升趋势, -1: 下降趋势)
        """
        period = self.params['period']
        multiplier = self.params['multiplier']
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        hl2 = (high + low) / 2
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        supertrend = pd.Series(1.0, index=data.index)
        
        for i in range(1, len(data)):
            if close.iloc[i] > upper_band.iloc[i-1]:
                supertrend.iloc[i] = 1
            elif close.iloc[i] < lower_band.iloc[i-1]:
                supertrend.iloc[i] = -1
            else:
                supertrend.iloc[i] = supertrend.iloc[i-1]
        
        return supertrend
