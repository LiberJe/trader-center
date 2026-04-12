"""
因子衰减分析模块

提供因子时效性评估功能，确定最佳持仓周期。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit


class DecayAnalyzer:
    """
    因子衰减分析器
    
    计算因子的IC衰减曲线和收益衰减曲线，确定最佳持仓周期。
    
    Example:
        analyzer = DecayAnalyzer()
        ic_decay = analyzer.compute_ic_decay(factor_data, forward_returns)
    """
    
    def __init__(self):
        self.ic_decay_: Optional[pd.Series] = None
        self.return_decay_: Optional[pd.Series] = None
        self.half_life_: Optional[float] = None
        self.optimal_holding_period_: Optional[int] = None
        
    def compute_ic(
        self,
        factor_data: pd.Series,
        forward_returns: pd.Series,
        method: str = 'spearman',
    ) -> float:
        """
        计算单期IC
        
        Args:
            factor_data: 因子值Series，index为股票代码
            forward_returns: 未来收益Series，index为股票代码
            method: 相关性计算方法 ('pearson' 或 'spearman')
        
        Returns:
            IC值
        """
        common_index = factor_data.index.intersection(forward_returns.index)
        
        if len(common_index) < 5:
            return np.nan
        
        factor_values = factor_data.loc[common_index]
        return_values = forward_returns.loc[common_index]
        
        valid_mask = ~(factor_values.isna() | return_values.isna())
        factor_values = factor_values[valid_mask]
        return_values = return_values[valid_mask]
        
        if len(factor_values) < 5:
            return np.nan
        
        if method == 'pearson':
            ic, _ = stats.pearsonr(factor_values, return_values)
        elif method == 'spearman':
            ic, _ = stats.spearmanr(factor_values, return_values)
        else:
            raise ValueError(f"未知的相关性方法: {method}")
        
        return ic
    
    def compute_ic_decay(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        periods: List[int] = [1, 5, 10, 20, 60],
        method: str = 'spearman',
    ) -> pd.Series:
        """
        计算IC衰减曲线
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            periods: 未来收益的计算周期列表
            method: 相关性计算方法
        
        Returns:
            各周期的IC均值Series
        """
        ic_decay = {}
        dates = factor_data.index.intersection(forward_returns.index)
        
        for period in periods:
            ic_list = []
            
            # 确保有足够的数据计算该周期的收益
            max_shift = max(periods)
            valid_dates = dates[:-max_shift]
            
            for date in valid_dates:
                # 计算该日期对应的未来收益日期
                try:
                    future_date = dates[dates.get_loc(date) + period]
                except KeyError:
                    continue
                
                if future_date not in forward_returns.index:
                    continue
                
                factor_series = factor_data.loc[date].dropna()
                return_series = forward_returns.loc[future_date].dropna()
                
                ic = self.compute_ic(factor_series, return_series, method)
                if not np.isnan(ic):
                    ic_list.append(ic)
            
            if ic_list:
                ic_decay[period] = np.mean(ic_list)
            else:
                ic_decay[period] = np.nan
        
        self.ic_decay_ = pd.Series(ic_decay)
        
        return self.ic_decay_
    
    def compute_return_decay(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        periods: List[int] = [1, 5, 10, 20, 60],
        quantile: int = 1,
    ) -> pd.Series:
        """
        计算收益衰减曲线
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            periods: 未来收益的计算周期列表
            quantile: 分组序号（1为最高分组，-1为最低分组）
        
        Returns:
            各周期的收益均值Series
        """
        return_decay = {}
        dates = factor_data.index.intersection(forward_returns.index)
        
        for period in periods:
            return_list = []
            
            # 确保有足够的数据计算该周期的收益
            max_shift = max(periods)
            valid_dates = dates[:-max_shift]
            
            for date in valid_dates:
                # 计算该日期对应的未来收益日期
                try:
                    future_date = dates[dates.get_loc(date) + period]
                except KeyError:
                    continue
                
                if future_date not in forward_returns.index:
                    continue
                
                factor_series = factor_data.loc[date].dropna()
                return_series = forward_returns.loc[future_date].dropna()
                
                common_index = factor_series.index.intersection(return_series.index)
                if len(common_index) < 10:
                    continue
                
                # 按因子值分组
                factor_series = factor_series.loc[common_index]
                return_series = return_series.loc[common_index]
                
                # 分为5组
                groups = pd.qcut(factor_series, 5, labels=False)
                
                # 取最高或最低分组
                if quantile == 1:
                    group_stocks = groups == 4  # 最高分组
                elif quantile == -1:
                    group_stocks = groups == 0  # 最低分组
                else:
                    raise ValueError("quantile 只能是 1 或 -1")
                
                if group_stocks.sum() < 5:
                    continue
                
                group_return = return_series[group_stocks].mean()
                return_list.append(group_return)
            
            if return_list:
                return_decay[period] = np.mean(return_list)
            else:
                return_decay[period] = np.nan
        
        self.return_decay_ = pd.Series(return_decay)
        
        return self.return_decay_
    
    def compute_half_life(
        self,
        ic_decay: pd.Series,
    ) -> float:
        """
        计算IC半衰期
        
        Args:
            ic_decay: IC衰减曲线
        
        Returns:
            IC半衰期（天）
        """
        # 过滤掉NaN值
        valid_decay = ic_decay.dropna()
        if len(valid_decay) < 2:
            return np.nan
        
        # 确保period是递增的
        valid_decay = valid_decay.sort_index()
        
        # 归一化IC值
        max_ic = valid_decay.max()
        normalized_ic = valid_decay / max_ic
        
        # 定义指数衰减函数
        def exponential_decay(x, half_life, amplitude):
            return amplitude * (0.5 ** (x / half_life))
        
        try:
            # 拟合指数衰减曲线
            x = valid_decay.index.values
            y = normalized_ic.values
            
            # 初始猜测值
            initial_guess = [10, 1.0]
            
            # 曲线拟合
            params, _ = curve_fit(exponential_decay, x, y, p0=initial_guess)
            half_life = params[0]
            
            self.half_life_ = half_life
            return half_life
        except:
            return np.nan
    
    def find_optimal_holding_period(
        self,
        ic_decay: pd.Series,
    ) -> int:
        """
        寻找最优持仓周期
        
        Args:
            ic_decay: IC衰减曲线
        
        Returns:
            最优持仓周期（天）
        """
        # 过滤掉NaN值
        valid_decay = ic_decay.dropna()
        if len(valid_decay) == 0:
            return 0
        
        # 找到IC值最大的周期
        optimal_period = valid_decay.idxmax()
        
        self.optimal_holding_period_ = optimal_period
        return optimal_period
    
    def get_decay_summary(
        self,
    ) -> Dict[str, Union[float, int, pd.Series]]:
        """
        获取衰减分析摘要
        
        Returns:
            衰减分析摘要
        """
        if self.ic_decay_ is None:
            raise ValueError("请先调用 compute_ic_decay 方法")
        
        summary = {
            'ic_decay': self.ic_decay_,
            'return_decay': self.return_decay_,
            'half_life': self.half_life_,
            'optimal_holding_period': self.optimal_holding_period_,
            'max_ic_period': self.ic_decay_.idxmax() if not self.ic_decay_.isna().all() else None,
            'max_ic_value': self.ic_decay_.max() if not self.ic_decay_.isna().all() else None,
        }
        
        # 计算衰减速度评分
        if self.half_life_ is not None:
            if self.half_life_ > 20:
                summary['decay_score'] = 1.0
            elif self.half_life_ >= 10:
                summary['decay_score'] = 0.7
            elif self.half_life_ >= 5:
                summary['decay_score'] = 0.4
            else:
                summary['decay_score'] = 0.1
        else:
            summary['decay_score'] = 0.0
        
        return summary


def plot_ic_decay_curve(
    ic_decay: pd.Series,
    title: str = 'IC Decay Curve',
    figsize: tuple = (10, 6),
) -> None:
    """
    绘制IC衰减曲线
    
    Args:
        ic_decay: IC衰减曲线
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    # 绘制IC衰减曲线
    plt.plot(ic_decay.index, ic_decay.values, 'o-', linewidth=2, markersize=8)
    
    # 绘制参考线
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 标注最大值
    if not ic_decay.isna().all():
        max_period = ic_decay.idxmax()
        max_ic = ic_decay.max()
        plt.annotate(f'Max: {max_ic:.4f} at {max_period}d',
                    xy=(max_period, max_ic),
                    xytext=(max_period + 2, max_ic + 0.01),
                    arrowprops=dict(facecolor='black', shrink=0.05))
    
    plt.title(title)
    plt.xlabel('Holding Period (days)')
    plt.ylabel('IC')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_return_decay_curve(
    return_decay: pd.Series,
    title: str = 'Return Decay Curve',
    figsize: tuple = (10, 6),
) -> None:
    """
    绘制收益衰减曲线
    
    Args:
        return_decay: 收益衰减曲线
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    # 绘制收益衰减曲线
    plt.plot(return_decay.index, return_decay.values, 'o-', linewidth=2, markersize=8)
    
    # 绘制参考线
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 标注最大值
    if not return_decay.isna().all():
        max_period = return_decay.idxmax()
        max_return = return_decay.max()
        plt.annotate(f'Max: {max_return:.4f} at {max_period}d',
                    xy=(max_period, max_return),
                    xytext=(max_period + 2, max_return + 0.001),
                    arrowprops=dict(facecolor='black', shrink=0.05))
    
    plt.title(title)
    plt.xlabel('Holding Period (days)')
    plt.ylabel('Return')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_decay_comparison(
    decay_dict: Dict[str, pd.Series],
    title: str = 'Factor Decay Comparison',
    figsize: tuple = (12, 8),
) -> None:
    """
    多因子衰减对比
    
    Args:
        decay_dict: 因子衰减字典，{因子名称: 衰减曲线}
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    for factor_name, decay_series in decay_dict.items():
        plt.plot(decay_series.index, decay_series.values, 'o-', linewidth=2, markersize=6, label=factor_name)
    
    # 绘制参考线
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.title(title)
    plt.xlabel('Holding Period (days)')
    plt.ylabel('IC')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
