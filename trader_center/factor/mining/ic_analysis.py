"""
因子IC分析

提供因子IC（Information Coefficient）分析功能。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np
from scipy import stats


class ICAnalyzer:
    """
    IC分析器
    
    计算因子的IC、ICIR、IC衰减等指标。
    
    Example:
        analyzer = ICAnalyzer()
        ic_result = analyzer.compute(factor_data, forward_returns)
    """
    
    def __init__(self):
        self.ic_series_: Optional[pd.Series] = None
        self.ic_mean_: Optional[float] = None
        self.ic_std_: Optional[float] = None
        self.icir_: Optional[float] = None
        self.ic_t_stat_: Optional[float] = None
        self.ic_p_value_: Optional[float] = None
    
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
    
    def compute(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        method: str = 'spearman',
    ) -> Dict[str, Union[pd.Series, float]]:
        """
        计算多期IC
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            method: 相关性计算方法 ('pearson' 或 'spearman')
        
        Returns:
            包含IC分析结果的字典
        
        Example:
            result = analyzer.compute(factor_df, forward_returns_df)
            print(f"IC均值: {result['ic_mean']}")
            print(f"ICIR: {result['icir']}")
        """
        ic_list = []
        dates = factor_data.index.intersection(forward_returns.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            
            ic = self.compute_ic(factor_series, return_series, method)
            ic_list.append({'date': date, 'ic': ic})
        
        self.ic_series_ = pd.Series(
            [item['ic'] for item in ic_list],
            index=[item['date'] for item in ic_list]
        )
        
        self.ic_mean_ = self.ic_series_.mean()
        self.ic_std_ = self.ic_series_.std()
        
        if self.ic_std_ > 0:
            self.icir_ = self.ic_mean_ / self.ic_std_
        else:
            self.icir_ = 0
        
        valid_ics = self.ic_series_.dropna()
        if len(valid_ics) > 1:
            self.ic_t_stat_, self.ic_p_value_ = stats.ttest_1samp(
                valid_ics, 0
            )
        else:
            self.ic_t_stat_ = np.nan
            self.ic_p_value_ = np.nan
        
        return {
            'ic_series': self.ic_series_,
            'ic_mean': self.ic_mean_,
            'ic_std': self.ic_std_,
            'icir': self.icir_,
            'ic_t_stat': self.ic_t_stat_,
            'ic_p_value': self.ic_p_value_,
            'ic_positive_ratio': (self.ic_series_ > 0).mean(),
            'ic_significant_ratio': (np.abs(self.ic_series_) > 0.02).mean(),
        }
    
    def compute_ic_decay(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        periods: List[int] = [1, 5, 10, 20, 60],
        method: str = 'spearman',
    ) -> pd.Series:
        """
        计算IC衰减
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            periods: 未来收益的计算周期列表
            method: 相关性计算方法
        
        Returns:
            各周期的IC均值Series
        """
        ic_decay = {}
        
        for period in periods:
            shifted_returns = forward_returns.shift(-period)
            
            result = self.compute(factor_data, shifted_returns, method)
            ic_decay[period] = result['ic_mean']
        
        return pd.Series(ic_decay)
    
    def compute_rolling_ic(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        window: int = 20,
        method: str = 'spearman',
    ) -> pd.Series:
        """
        计算滚动IC
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            window: 滚动窗口大小
            method: 相关性计算方法
        
        Returns:
            滚动IC均值Series
        """
        result = self.compute(factor_data, forward_returns, method)
        
        rolling_ic_mean = result['ic_series'].rolling(window=window).mean()
        
        return rolling_ic_mean
    
    def get_summary(self) -> Dict[str, float]:
        """
        获取IC分析摘要
        
        Returns:
            IC分析摘要字典
        """
        if self.ic_series_ is None:
            raise ValueError("请先调用 compute 方法")
        
        return {
            'IC均值': self.ic_mean_,
            'IC标准差': self.ic_std_,
            'ICIR': self.icir_,
            'IC t统计量': self.ic_t_stat_,
            'IC p值': self.ic_p_value_,
            'IC>0比例': (self.ic_series_ > 0).mean(),
            'IC显著比例': (np.abs(self.ic_series_) > 0.02).mean(),
            'IC最大值': self.ic_series_.max(),
            'IC最小值': self.ic_series_.min(),
        }


def compute_rank_ic(
    factor_data: pd.Series,
    forward_returns: pd.Series,
) -> float:
    """
    计算Rank IC
    
    Args:
        factor_data: 因子值Series，index为股票代码
        forward_returns: 未来收益Series，index为股票代码
    
    Returns:
        Rank IC值
    """
    common_index = factor_data.index.intersection(forward_returns.index)
    
    if len(common_index) < 5:
        return np.nan
    
    factor_rank = factor_data.loc[common_index].rank()
    return_rank = forward_returns.loc[common_index].rank()
    
    valid_mask = ~(factor_rank.isna() | return_rank.isna())
    factor_rank = factor_rank[valid_mask]
    return_rank = return_rank[valid_mask]
    
    if len(factor_rank) < 5:
        return np.nan
    
    ic, _ = stats.spearmanr(factor_rank, return_rank)
    
    return ic


def compute_normal_ic(
    factor_data: pd.Series,
    forward_returns: pd.Series,
) -> float:
    """
    计算Normal IC（Pearson IC）
    
    Args:
        factor_data: 因子值Series，index为股票代码
        forward_returns: 未来收益Series，index为股票代码
    
    Returns:
        Normal IC值
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
    
    ic, _ = stats.pearsonr(factor_values, return_values)
    
    return ic


def batch_compute_ic(
    factor_data_dict: Dict[str, pd.DataFrame],
    forward_returns: pd.DataFrame,
    method: str = 'spearman',
) -> pd.DataFrame:
    """
    批量计算多个因子的IC
    
    Args:
        factor_data_dict: 因子数据字典，{因子名称: DataFrame}
        forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
        method: 相关性计算方法
    
    Returns:
        IC分析结果DataFrame，index为因子名称，columns为IC指标
    
    Example:
        result = batch_compute_ic(
            {'momentum': momentum_df, 'rsi': rsi_df},
            forward_returns_df
        )
    """
    results = []
    
    for factor_name, factor_data in factor_data_dict.items():
        analyzer = ICAnalyzer()
        result = analyzer.compute(factor_data, forward_returns, method)
        
        results.append({
            'factor': factor_name,
            'ic_mean': result['ic_mean'],
            'ic_std': result['ic_std'],
            'icir': result['icir'],
            'ic_t_stat': result['ic_t_stat'],
            'ic_p_value': result['ic_p_value'],
            'ic_positive_ratio': result['ic_positive_ratio'],
            'ic_significant_ratio': result['ic_significant_ratio'],
        })
    
    return pd.DataFrame(results).set_index('factor')


def plot_ic_series(
    ic_series: pd.Series,
    figsize: tuple = (12, 6),
) -> None:
    """
    绘制IC时间序列图
    
    Args:
        ic_series: IC时间序列Series
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
    
    ax1.bar(ic_series.index, ic_series.values, alpha=0.7)
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.axhline(y=ic_series.mean(), color='red', linestyle='--', 
                label=f'Mean: {ic_series.mean():.4f}')
    ax1.set_title('IC Time Series')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('IC')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    cumulative_ic = ic_series.cumsum()
    ax2.plot(cumulative_ic.index, cumulative_ic.values, linewidth=2)
    ax2.set_title('Cumulative IC')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Cumulative IC')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
