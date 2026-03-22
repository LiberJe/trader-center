"""
夏普比率因子

包含滚动夏普比率、索提诺比率等风险调整收益相关因子。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class SharpeRatioFactor(BaseFactor):
    """
    滚动夏普比率因子
    
    计算N日滚动夏普比率，用于衡量风险调整后的收益。
    
    公式: Sharpe = (年化收益率 - 无风险利率) / 年化波动率
    
    Params:
        period: 计算周期，默认60个交易日
        risk_free_rate: 无风险利率（年化），默认0.03
        annualization_factor: 年化因子，默认252（交易日）
    """
    
    name = "sharpe_ratio"
    category = "technical"
    description = "滚动夏普比率因子"
    
    def __init__(
        self,
        period: int = 60,
        risk_free_rate: float = 0.03,
        annualization_factor: int = 252,
    ):
        super().__init__(
            period=period,
            risk_free_rate=risk_free_rate,
            annualization_factor=annualization_factor,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
        if self.params.get('risk_free_rate', 0.03) < 0:
            raise ValueError("risk_free_rate 不能为负数")
        if self.params.get('annualization_factor', 252) <= 0:
            raise ValueError("annualization_factor 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算滚动夏普比率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            夏普比率值Series
        """
        period = self.params['period']
        risk_free_rate = self.params['risk_free_rate']
        annualization_factor = self.params['annualization_factor']
        
        close = data['close']
        returns = close.pct_change()
        
        ann_return = returns.rolling(window=period).mean() * annualization_factor
        
        ann_volatility = returns.rolling(window=period).std() * np.sqrt(annualization_factor)
        
        daily_rf = risk_free_rate / annualization_factor
        excess_return = ann_return - risk_free_rate
        
        sharpe = excess_return / ann_volatility
        
        sharpe = sharpe.replace([np.inf, -np.inf], np.nan)
        
        return sharpe


class SortinoRatioFactor(BaseFactor):
    """
    滚动索提诺比率因子
    
    与夏普比率类似，但只考虑下行波动率，更适合衡量不对称收益分布。
    
    公式: Sortino = (年化收益率 - 无风险利率) / 年化下行波动率
    
    Params:
        period: 计算周期，默认60个交易日
        risk_free_rate: 无风险利率（年化），默认0.03
        annualization_factor: 年化因子，默认252（交易日）
        target_return: 目标收益率（日），默认0
    """
    
    name = "sortino_ratio"
    category = "technical"
    description = "滚动索提诺比率因子"
    
    def __init__(
        self,
        period: int = 60,
        risk_free_rate: float = 0.03,
        annualization_factor: int = 252,
        target_return: float = 0.0,
    ):
        super().__init__(
            period=period,
            risk_free_rate=risk_free_rate,
            annualization_factor=annualization_factor,
            target_return=target_return,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
        if self.params.get('risk_free_rate', 0.03) < 0:
            raise ValueError("risk_free_rate 不能为负数")
        if self.params.get('annualization_factor', 252) <= 0:
            raise ValueError("annualization_factor 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算滚动索提诺比率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            索提诺比率值Series
        """
        period = self.params['period']
        risk_free_rate = self.params['risk_free_rate']
        annualization_factor = self.params['annualization_factor']
        target_return = self.params['target_return']
        
        close = data['close']
        returns = close.pct_change()
        
        ann_return = returns.rolling(window=period).mean() * annualization_factor
        
        def calc_downside_vol(window):
            excess = window - target_return
            negative_excess = excess[excess < 0]
            if len(negative_excess) == 0:
                return 0.0
            return np.sqrt((negative_excess ** 2).mean())
        
        downside_vol = returns.rolling(window=period).apply(
            calc_downside_vol, raw=False
        ) * np.sqrt(annualization_factor)
        
        excess_return = ann_return - risk_free_rate
        
        sortino = excess_return / downside_vol
        
        sortino = sortino.replace([np.inf, -np.inf], np.nan)
        
        return sortino


class CalmarRatioFactor(BaseFactor):
    """
    滚动卡玛比率因子
    
    年化收益率与最大回撤的比值，衡量收益与回撤的关系。
    
    公式: Calmar = 年化收益率 / 最大回撤
    
    Params:
        period: 计算周期，默认60个交易日
        annualization_factor: 年化因子，默认252（交易日）
    """
    
    name = "calmar_ratio"
    category = "technical"
    description = "滚动卡玛比率因子"
    
    def __init__(
        self,
        period: int = 60,
        annualization_factor: int = 252,
    ):
        super().__init__(
            period=period,
            annualization_factor=annualization_factor,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
        if self.params.get('annualization_factor', 252) <= 0:
            raise ValueError("annualization_factor 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算滚动卡玛比率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            卡玛比率值Series
        """
        period = self.params['period']
        annualization_factor = self.params['annualization_factor']
        
        close = data['close']
        returns = close.pct_change()
        
        ann_return = returns.rolling(window=period).mean() * annualization_factor
        
        def calc_max_drawdown(window):
            cumulative = (1 + window).cumprod()
            peak = cumulative.expanding().max()
            drawdown = (cumulative - peak) / peak
            return drawdown.min()
        
        max_drawdown = returns.rolling(window=period).apply(
            calc_max_drawdown, raw=False
        )
        
        max_drawdown = max_drawdown.abs()
        
        calmar = ann_return / max_drawdown
        
        calmar = calmar.replace([np.inf, -np.inf], np.nan)
        
        return calmar


class InformationRatioFactor(BaseFactor):
    """
    滚动信息比率因子
    
    超额收益与跟踪误差的比值，需要基准收益率。
    
    公式: IR = (组合收益率 - 基准收益率) / 跟踪误差
    
    Params:
        period: 计算周期，默认60个交易日
        annualization_factor: 年化因子，默认252（交易日）
        benchmark_returns: 基准收益率Series（可选）
    """
    
    name = "information_ratio"
    category = "technical"
    description = "滚动信息比率因子"
    
    def __init__(
        self,
        period: int = 60,
        annualization_factor: int = 252,
        benchmark_returns: pd.Series = None,
    ):
        super().__init__(
            period=period,
            annualization_factor=annualization_factor,
            benchmark_returns=benchmark_returns,
        )
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")
        if self.params.get('annualization_factor', 252) <= 0:
            raise ValueError("annualization_factor 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算滚动信息比率因子
        
        Args:
            data: 包含close列的DataFrame
        
        Returns:
            信息比率值Series
        """
        period = self.params['period']
        annualization_factor = self.params['annualization_factor']
        benchmark_returns = self.params.get('benchmark_returns')
        
        close = data['close']
        returns = close.pct_change()
        
        if benchmark_returns is not None:
            excess_returns = returns - benchmark_returns
        else:
            excess_returns = returns
        
        ann_excess_return = excess_returns.rolling(window=period).mean() * annualization_factor
        
        tracking_error = excess_returns.rolling(window=period).std() * np.sqrt(annualization_factor)
        
        ir = ann_excess_return / tracking_error
        
        ir = ir.replace([np.inf, -np.inf], np.nan)
        
        return ir
