"""
回撤因子

包含最大回撤、回撤持续时间等回撤相关因子。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class MaxDrawdownFactor(BaseFactor):
    """
    滚动最大回撤因子
    
    计算N日滚动窗口内的最大回撤，用于衡量历史风险。
    
    公式: MaxDD = max((peak - price) / peak)
    
    Params:
        period: 计算周期，默认60个交易日
    """
    
    name = "max_drawdown"
    category = "technical"
    description = "滚动最大回撤因子"
    
    def __init__(self, period: int = 60):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算滚动最大回撤因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            最大回撤值Series（负数，表示回撤幅度）
        """
        period = self.params['period']
        close = data['close']
        
        def calc_max_drawdown(window):
            if len(window) < 2:
                return 0.0
            cumulative = (1 + pd.Series(window).pct_change().fillna(0)).cumprod()
            peak = cumulative.expanding().max()
            drawdown = (cumulative - peak) / peak
            return drawdown.min()
        
        max_dd = close.rolling(window=period).apply(calc_max_drawdown, raw=False)
        
        return max_dd


class DrawdownDurationFactor(BaseFactor):
    """
    回撤持续时间因子
    
    计算当前回撤持续的交易日数。
    
    Params:
        period: 最大回看周期，默认252个交易日
    """
    
    name = "drawdown_duration"
    category = "technical"
    description = "回撤持续时间因子"
    
    def __init__(self, period: int = 252):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 252) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算回撤持续时间因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            回撤持续天数Series
        """
        close = data['close']
        
        rolling_max = close.expanding().max()
        
        in_drawdown = close < rolling_max
        
        duration = pd.Series(0, index=close.index)
        current_duration = 0
        
        for i in range(len(close)):
            if in_drawdown.iloc[i]:
                current_duration += 1
            else:
                current_duration = 0
            duration.iloc[i] = current_duration
        
        return duration


class AverageDrawdownFactor(BaseFactor):
    """
    平均回撤因子
    
    计算N日滚动窗口内的平均回撤幅度。
    
    Params:
        period: 计算周期，默认60个交易日
    """
    
    name = "average_drawdown"
    category = "technical"
    description = "平均回撤因子"
    
    def __init__(self, period: int = 60):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算平均回撤因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            平均回撤值Series（负数）
        """
        period = self.params['period']
        close = data['close']
        
        rolling_max = close.rolling(window=period, min_periods=1).max()
        drawdown = (close - rolling_max) / rolling_max
        
        avg_drawdown = drawdown.rolling(window=period).mean()
        
        return avg_drawdown


class DrawdownRecoveryFactor(BaseFactor):
    """
    回撤恢复能力因子
    
    衡量从回撤中恢复的速度，恢复越快得分越高。
    
    公式: Recovery = 1 / (恢复天数 + 1)
    
    Params:
        period: 计算周期，默认60个交易日
    """
    
    name = "drawdown_recovery"
    category = "technical"
    description = "回撤恢复能力因子"
    
    def __init__(self, period: int = 60):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算回撤恢复能力因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            回撤恢复能力值Series（0-1之间，越高越好）
        """
        period = self.params['period']
        close = data['close']
        
        rolling_max = close.rolling(window=period, min_periods=1).max()
        
        recovery = pd.Series(0.0, index=close.index)
        
        for i in range(period, len(close)):
            window_close = close.iloc[i-period+1:i+1]
            window_max = rolling_max.iloc[i-period+1:i+1]
            
            peak_idx = window_max.idxmax()
            peak_value = window_max.loc[peak_idx]
            
            if window_close.iloc[-1] >= peak_value * 0.99:
                peak_pos = window_close.index.get_loc(peak_idx)
                recovery_days = len(window_close) - 1 - peak_pos
                if recovery_days > 0:
                    recovery.iloc[i] = 1.0 / (recovery_days + 1)
                else:
                    recovery.iloc[i] = 1.0
            else:
                recovery.iloc[i] = 0.0
        
        return recovery


class UlcerIndexFactor(BaseFactor):
    """
    Ulcer指数因子
    
    衡量价格下行的深度和持续时间，是波动率的替代指标。
    
    公式: UI = sqrt(sum((close - rolling_max)^2 / rolling_max^2) / n)
    
    Params:
        period: 计算周期，默认14个交易日
    """
    
    name = "ulcer_index"
    category = "technical"
    description = "Ulcer指数因子"
    
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
        计算Ulcer指数因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            Ulcer指数值Series
        """
        period = self.params['period']
        close = data['close']
        
        rolling_max = close.rolling(window=period, min_periods=1).max()
        
        pct_drawdown_sq = ((close - rolling_max) / rolling_max) ** 2
        
        ulcer_index = np.sqrt(pct_drawdown_sq.rolling(window=period).mean())
        
        return ulcer_index


class PainIndexFactor(BaseFactor):
    """
    Pain指数因子
    
    平均回撤的绝对值，衡量投资的"痛苦"程度。
    
    公式: PI = mean(|drawdown|)
    
    Params:
        period: 计算周期，默认60个交易日
    """
    
    name = "pain_index"
    category = "technical"
    description = "Pain指数因子"
    
    def __init__(self, period: int = 60):
        super().__init__(period=period)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算Pain指数因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            Pain指数值Series（正数，越小越好）
        """
        period = self.params['period']
        close = data['close']
        
        rolling_max = close.rolling(window=period, min_periods=1).max()
        drawdown = (close - rolling_max) / rolling_max
        
        pain_index = drawdown.abs().rolling(window=period).mean()
        
        return pain_index
