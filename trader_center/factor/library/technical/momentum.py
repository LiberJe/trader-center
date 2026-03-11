"""
动量因子

包含价格动量、RSI、MACD等动量相关因子。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class MomentumFactor(BaseFactor):
    """
    价格动量因子
    
    计算N日的价格收益率作为动量指标。
    
    Params:
        period: 回看周期，默认20天
    """
    
    name = "momentum"
    category = "technical"
    description = "价格动量因子（N日收益率）"
    
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
        计算动量因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            动量值Series
        """
        period = self.params['period']
        return data['close'].pct_change(period)


class RSIFactor(BaseFactor):
    """
    相对强弱指标因子 (RSI)
    
    衡量价格变动的速度和变化，判断超买超卖。
    
    Params:
        period: RSI周期，默认14天
    """
    
    name = "rsi"
    category = "technical"
    description = "相对强弱指标因子"
    
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
        计算RSI因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            RSI值Series (0-100)
        """
        period = self.params['period']
        close = data['close']
        
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class MACDFactor(BaseFactor):
    """
    MACD因子
    
    计算MACD指标，包括MACD线、信号线和柱状图。
    
    Params:
        fast_period: 快线周期，默认12
        slow_period: 慢线周期，默认26
        signal_period: 信号线周期，默认9
    """
    
    name = "macd"
    category = "technical"
    description = "MACD因子"
    
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
        计算MACD因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            MACD值Series
        """
        close = data['close']
        fast_period = self.params['fast_period']
        slow_period = self.params['slow_period']
        signal_period = self.params['signal_period']
        
        ema_fast = close.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=slow_period, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        
        return macd
    
    def compute_full(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        计算完整的MACD指标
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            包含MACD、Signal、Histogram的字典
        """
        macd = self.compute(data)
        signal_period = self.params['signal_period']
        
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram,
        }


class PriceRateOfChangeFactor(BaseFactor):
    """
    价格变化率因子 (ROC)
    
    计算价格相对于N天前的变化率。
    
    Params:
        period: 回看周期，默认12天
    """
    
    name = "price_roc"
    category = "technical"
    description = "价格变化率因子"
    
    def __init__(self, period: int = 12):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 12) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算价格变化率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            ROC值Series
        """
        period = self.params['period']
        close = data['close']
        
        roc = ((close - close.shift(period)) / close.shift(period)) * 100
        
        return roc


class MomentumQualityFactor(BaseFactor):
    """
    动量质量因子
    
    衡量动量的稳定性和一致性。
    
    Params:
        period: 回看周期，默认20天
    """
    
    name = "momentum_quality"
    category = "technical"
    description = "动量质量因子（衡量动量稳定性）"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算动量质量因子
        
        使用收益率的标准差和方向的稳定性来衡量动量质量。
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            动量质量值Series
        """
        period = self.params['period']
        close = data['close']
        
        returns = close.pct_change()
        
        momentum = close.pct_change(period)
        
        momentum_std = returns.rolling(window=period).std()
        
        positive_returns = (returns > 0).rolling(window=period).mean()
        
        momentum_quality = momentum / momentum_std * positive_returns
        
        return momentum_quality


class VolumeAdjustedMomentumFactor(BaseFactor):
    """
    成交量调整动量因子
    
    结合成交量的动量因子，成交量放大时的动量更可靠。
    
    Params:
        period: 回看周期，默认20天
        volume_ma_period: 成交量均线周期，默认20天
    """
    
    name = "volume_adjusted_momentum"
    category = "technical"
    description = "成交量调整动量因子"
    
    def __init__(self, period: int = 20, volume_ma_period: int = 20):
        super().__init__(period=period, volume_ma_period=volume_ma_period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算成交量调整动量因子
        
        Args:
            data: 包含close和volume列的DataFrame
        
        Returns:
            成交量调整动量值Series
        """
        period = self.params['period']
        volume_ma_period = self.params['volume_ma_period']
        
        close = data['close']
        volume = data['volume']
        
        momentum = close.pct_change(period)
        
        volume_ratio = volume / volume.rolling(window=volume_ma_period).mean()
        
        adjusted_momentum = momentum * np.log1p(volume_ratio)
        
        return adjusted_momentum
