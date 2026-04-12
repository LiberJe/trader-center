"""
反转因子

包含RSI反转、布林带反转、KDJ反转等反转相关因子。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class RSIReversalFactor(BaseFactor):
    """
    RSI反转因子
    
    基于RSI超买超卖的反转信号。
    
    Params:
        period: RSI周期，默认14天
        overbought: 超买阈值，默认70
        oversold: 超卖阈值，默认30
    """
    
    name = "rsi_reversal"
    category = "technical"
    description = "RSI反转因子（超买超卖信号）"
    
    def __init__(
        self,
        period: int = 14,
        overbought: float = 70,
        oversold: float = 30,
    ):
        super().__init__(
            period=period,
            overbought=overbought,
            oversold=oversold,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
        if not (0 < self.params['oversold'] < self.params['overbought'] < 100):
            raise ValueError("阈值必须满足: 0 < oversold < overbought < 100")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算RSI反转因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            RSI反转信号Series (-1: 超买, 0: 中性, 1: 超卖)
        """
        period = self.params['period']
        overbought = self.params['overbought']
        oversold = self.params['oversold']
        
        close = data['close']
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        reversal = pd.Series(0, index=rsi.index)
        reversal[rsi >= overbought] = -1
        reversal[rsi <= oversold] = 1
        
        return reversal


class BollingerReversalFactor(BaseFactor):
    """
    布林带反转因子
    
    基于价格触及布林带上下轨的反转信号。
    
    Params:
        period: 移动平均周期，默认20天
        std_dev: 标准差倍数，默认2
    """
    
    name = "bollinger_reversal"
    category = "technical"
    description = "布林带反转因子"
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(period=period, std_dev=std_dev)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
        if self.params['std_dev'] <= 0:
            raise ValueError("std_dev 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算布林带反转因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            布林带反转信号Series (-1: 触上轨, 0: 中性, 1: 触下轨)
        """
        period = self.params['period']
        std_dev = self.params['std_dev']
        
        close = data['close']
        
        middle_band = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        reversal = pd.Series(0, index=close.index)
        reversal[close >= upper_band] = -1
        reversal[close <= lower_band] = 1
        
        return reversal
    
    def compute_full(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        计算完整的布林带指标
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            包含upper、middle、lower、reversal的字典
        """
        period = self.params['period']
        std_dev = self.params['std_dev']
        
        close = data['close']
        
        middle_band = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        reversal = pd.Series(0, index=close.index)
        reversal[close >= upper_band] = -1
        reversal[close <= lower_band] = 1
        
        return {
            'upper': upper_band,
            'middle': middle_band,
            'lower': lower_band,
            'reversal': reversal,
        }


class KDJReversalFactor(BaseFactor):
    """
    KDJ反转因子
    
    基于KDJ指标的金叉死叉和超买超卖信号。
    
    Params:
        n: KDJ周期，默认9天
        m1: K值平滑周期，默认3
        m2: D值平滑周期，默认3
        overbought: 超买阈值，默认80
        oversold: 超卖阈值，默认20
    """
    
    name = "kdj_reversal"
    category = "technical"
    description = "KDJ反转因子"
    
    def __init__(
        self,
        n: int = 9,
        m1: int = 3,
        m2: int = 3,
        overbought: float = 80,
        oversold: float = 20,
    ):
        super().__init__(
            n=n,
            m1=m1,
            m2=m2,
            overbought=overbought,
            oversold=oversold,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['n'] <= 0 or self.params['m1'] <= 0 or self.params['m2'] <= 0:
            raise ValueError("周期参数必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算KDJ反转因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            KDJ反转信号Series (-2: 死叉, -1: 超买, 0: 中性, 1: 超卖, 2: 金叉)
        """
        n = self.params['n']
        m1 = self.params['m1']
        m2 = self.params['m2']
        overbought = self.params['overbought']
        oversold = self.params['oversold']
        
        low_min = data['low'].rolling(window=n, min_periods=1).min()
        high_max = data['high'].rolling(window=n, min_periods=1).max()
        
        rsv = (data['close'] - low_min) / (high_max - low_min) * 100
        
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        reversal = pd.Series(0, index=data.index)
        
        reversal[k >= overbought] = -1
        reversal[k <= oversold] = 1
        
        golden_cross = (k > d) & (k.shift(1) <= d.shift(1))
        death_cross = (k < d) & (k.shift(1) >= d.shift(1))
        
        reversal[golden_cross] = 2
        reversal[death_cross] = -2
        
        return reversal
    
    def compute_full(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        计算完整的KDJ指标
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            包含K、D、J值的字典
        """
        n = self.params['n']
        m1 = self.params['m1']
        m2 = self.params['m2']
        
        low_min = data['low'].rolling(window=n, min_periods=1).min()
        high_max = data['high'].rolling(window=n, min_periods=1).max()
        
        rsv = (data['close'] - low_min) / (high_max - low_min) * 100
        
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return {
            'K': k,
            'D': d,
            'J': j,
        }


class WilliamsReversalFactor(BaseFactor):
    """
    威廉指标反转因子
    
    基于威廉指标的超买超卖信号。
    
    Params:
        period: 回看周期，默认14天
        overbought: 超买阈值，默认-20
        oversold: 超卖阈值，默认-80
    """
    
    name = "williams_reversal"
    category = "technical"
    description = "威廉指标反转因子"
    
    def __init__(
        self,
        period: int = 14,
        overbought: float = -20,
        oversold: float = -80,
    ):
        super().__init__(
            period=period,
            overbought=overbought,
            oversold=oversold,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
        if not (-100 < self.params['oversold'] < self.params['overbought'] < 0):
            raise ValueError("阈值必须满足: -100 < oversold < overbought < 0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算威廉指标反转因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            威廉指标反转信号Series (-1: 超买, 0: 中性, 1: 超卖)
        """
        period = self.params['period']
        overbought = self.params['overbought']
        oversold = self.params['oversold']
        
        high_max = data['high'].rolling(window=period).max()
        low_min = data['low'].rolling(window=period).min()
        
        williams = ((high_max - data['close']) / (high_max - low_min)) * -100
        
        reversal = pd.Series(0, index=data.index)
        reversal[williams >= overbought] = -1
        reversal[williams <= oversold] = 1
        
        return reversal


class CCIFactor(BaseFactor):
    """
    顺势指标因子 (CCI)
    
    衡量价格偏离统计平均值的程度。
    
    Params:
        period: 计算周期，默认20天
        constant: 常数，默认0.015
    """
    
    name = "cci"
    category = "technical"
    description = "顺势指标因子"
    
    def __init__(self, period: int = 20, constant: float = 0.015):
        super().__init__(period=period, constant=constant)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
        if self.params['constant'] <= 0:
            raise ValueError("constant 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算CCI因子
        
        Args:
            data: 包含high、low、close列的DataFrame
        
        Returns:
            CCI值Series
        """
        period = self.params['period']
        constant = self.params['constant']
        
        tp = (data['high'] + data['low'] + data['close']) / 3
        
        ma = tp.rolling(window=period).mean()
        
        md = tp.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        
        cci = (tp - ma) / (constant * md)
        
        return cci


class BiasFactor(BaseFactor):
    """
    乖离率因子
    
    衡量价格与移动平均线之间的偏离程度。
    
    Params:
        period: 移动平均线周期，默认20天
        ma_type: 移动平均线类型，可选值: sma(简单移动平均)、ema(指数移动平均)、wma(加权移动平均)
    """
    
    name = "bias"
    category = "technical"
    description = "价格乖离率因子"
    
    def __init__(self, period: int = 20, ma_type: str = "sma"):
        super().__init__(period=period, ma_type=ma_type)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> list:
        """
        所需数据字段
        
        Returns:
            所需的数据字段列表
        """
        return ['close']
    
    def _validate_params(self):
        if self.params['period'] <= 0:
            raise ValueError("period 必须大于0")
        if self.params['ma_type'] not in ["sma", "ema", "wma"]:
            raise ValueError("ma_type 必须是 'sma', 'ema' 或 'wma'")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算乖离率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            乖离率值Series
        """
        period = self.params['period']
        ma_type = self.params['ma_type']
        
        close = data['close']
        
        # 计算移动平均线
        if ma_type == "sma":
            ma = close.rolling(period).mean()
        elif ma_type == "ema":
            ma = close.ewm(span=period).mean()
        elif ma_type == "wma":
            weights = np.arange(1, period + 1)
            ma = close.rolling(period).apply(
                lambda x: np.dot(x, weights) / weights.sum()
            )
        
        # 计算乖离率
        bias = (close - ma) / ma * 100
        
        return bias
