"""
因子分层回测

提供因子分层回测分析功能。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np


class LayeringAnalyzer:
    """
    分层回测分析器
    
    按因子值分组，计算各组的收益表现。
    
    Example:
        analyzer = LayeringAnalyzer(n_groups=5)
        result = analyzer.compute(factor_data, forward_returns)
    """
    
    def __init__(self, n_groups: int = 5):
        """
        初始化分层回测分析器
        
        Args:
            n_groups: 分组数量，默认5组
        """
        self.n_groups = n_groups
        self.group_returns_: Optional[pd.DataFrame] = None
        self.group_stats_: Optional[pd.DataFrame] = None
    
    def compute(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
    ) -> Dict[str, Union[pd.DataFrame, pd.Series]]:
        """
        计算分层回测
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
        
        Returns:
            包含分层回测结果的字典
        
        Example:
            result = analyzer.compute(factor_df, forward_returns_df)
            print(result['group_returns'])
        """
        dates = factor_data.index.intersection(forward_returns.index)
        
        group_returns_list = []
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            
            common_stocks = factor_series.index.intersection(return_series.index)
            
            if len(common_stocks) < self.n_groups:
                continue
            
            factor_values = factor_series.loc[common_stocks]
            return_values = return_series.loc[common_stocks]
            
            labels = pd.qcut(
                factor_values, 
                self.n_groups, 
                labels=False, 
                duplicates='drop'
            )
            
            group_avg_returns = {}
            for group_id in range(self.n_groups):
                group_stocks = labels[labels == group_id].index
                if len(group_stocks) > 0:
                    group_avg_returns[group_id] = return_values.loc[group_stocks].mean()
                else:
                    group_avg_returns[group_id] = np.nan
            
            group_returns_list.append({
                'date': date,
                **{f'group_{i}': group_avg_returns.get(i, np.nan) 
                   for i in range(self.n_groups)}
            })
        
        self.group_returns_ = pd.DataFrame(group_returns_list).set_index('date')
        
        self._compute_group_stats()
        
        long_short = self.group_returns_[f'group_{self.n_groups-1}'] - \
                     self.group_returns_['group_0']
        
        return {
            'group_returns': self.group_returns_,
            'group_stats': self.group_stats_,
            'long_short_returns': long_short,
            'long_short_mean': long_short.mean(),
            'long_short_std': long_short.std(),
            'long_short_sharpe': long_short.mean() / long_short.std() if long_short.std() > 0 else 0,
        }
    
    def _compute_group_stats(self) -> None:
        """计算各组的统计指标"""
        if self.group_returns_ is None:
            return
        
        stats_list = []
        
        for group_col in self.group_returns_.columns:
            group_series = self.group_returns_[group_col]
            
            stats_list.append({
                'group': group_col,
                'mean_return': group_series.mean(),
                'std_return': group_series.std(),
                'sharpe_ratio': group_series.mean() / group_series.std() if group_series.std() > 0 else 0,
                'win_rate': (group_series > 0).mean(),
                'max_return': group_series.max(),
                'min_return': group_series.min(),
            })
        
        self.group_stats_ = pd.DataFrame(stats_list).set_index('group')
    
    def compute_monotonicity(self) -> float:
        """
        计算单调性
        
        Returns:
            单调性得分（-1到1）
        """
        if self.group_stats_ is None:
            raise ValueError("请先调用 compute 方法")
        
        mean_returns = self.group_stats_['mean_return'].values
        
        n = len(mean_returns)
        monotonic_score = 0
        
        for i in range(n):
            for j in range(i+1, n):
                if mean_returns[i] < mean_returns[j]:
                    monotonic_score += 1
                elif mean_returns[i] > mean_returns[j]:
                    monotonic_score -= 1
        
        max_pairs = n * (n - 1) / 2
        return monotonic_score / max_pairs if max_pairs > 0 else 0
    
    def compute_turnover(
        self,
        factor_data: pd.DataFrame,
        top_n: int = 50,
    ) -> pd.Series:
        """
        计算换手率
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            top_n: 选取前N只股票
        
        Returns:
            换手率Series
        """
        dates = factor_data.index
        turnover_list = []
        
        for i in range(1, len(dates)):
            prev_date = dates[i-1]
            curr_date = dates[i]
            
            prev_factor = factor_data.loc[prev_date].dropna()
            curr_factor = factor_data.loc[curr_date].dropna()
            
            prev_top = set(prev_factor.nlargest(top_n).index)
            curr_top = set(curr_factor.nlargest(top_n).index)
            
            turnover = len(prev_top.symmetric_difference(curr_top)) / (2 * top_n)
            
            turnover_list.append({
                'date': curr_date,
                'turnover': turnover
            })
        
        return pd.DataFrame(turnover_list).set_index('date')['turnover']
    
    def get_summary(self) -> Dict[str, float]:
        """
        获取分层回测摘要
        
        Returns:
            分层回测摘要字典
        """
        if self.group_stats_ is None:
            raise ValueError("请先调用 compute 方法")
        
        return {
            '单调性': self.compute_monotonicity(),
            '最高组收益': self.group_stats_.loc[f'group_{self.n_groups-1}', 'mean_return'],
            '最低组收益': self.group_stats_.loc['group_0', 'mean_return'],
            '多空收益差': self.group_stats_.loc[f'group_{self.n_groups-1}', 'mean_return'] - 
                        self.group_stats_.loc['group_0', 'mean_return'],
        }


def compute_group_returns(
    factor_series: pd.Series,
    return_series: pd.Series,
    n_groups: int = 5,
) -> pd.Series:
    """
    计算单期分组收益
    
    Args:
        factor_series: 因子值Series，index为股票代码
        return_series: 收益Series，index为股票代码
        n_groups: 分组数量
    
    Returns:
        各组平均收益Series
    """
    common_stocks = factor_series.index.intersection(return_series.index)
    
    if len(common_stocks) < n_groups:
        return pd.Series([np.nan] * n_groups, 
                        index=[f'group_{i}' for i in range(n_groups)])
    
    factor_values = factor_series.loc[common_stocks]
    return_values = return_series.loc[common_stocks]
    
    labels = pd.qcut(
        factor_values, 
        n_groups, 
        labels=False, 
        duplicates='drop'
    )
    
    group_avg_returns = {}
    for group_id in range(n_groups):
        group_stocks = labels[labels == group_id].index
        if len(group_stocks) > 0:
            group_avg_returns[f'group_{group_id}'] = return_values.loc[group_stocks].mean()
        else:
            group_avg_returns[f'group_{group_id}'] = np.nan
    
    return pd.Series(group_avg_returns)


def compute_long_short_returns(
    group_returns: pd.DataFrame,
    long_group: int = -1,
    short_group: int = 0,
) -> pd.Series:
    """
    计算多空组合收益
    
    Args:
        group_returns: 分组收益DataFrame
        long_group: 做多组别（-1表示最后一组）
        short_group: 做空组别
    
    Returns:
        多空收益Series
    """
    if long_group == -1:
        long_group = len(group_returns.columns) - 1
    
    long_col = f'group_{long_group}'
    short_col = f'group_{short_group}'
    
    return group_returns[long_col] - group_returns[short_col]


def plot_layering_results(
    group_returns: pd.DataFrame,
    figsize: tuple = (14, 10),
) -> None:
    """
    绘制分层回测结果
    
    Args:
        group_returns: 分组收益DataFrame
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    
    ax1 = axes[0, 0]
    cumulative_returns = (1 + group_returns).cumprod()
    for col in cumulative_returns.columns:
        ax1.plot(cumulative_returns.index, cumulative_returns[col], 
                label=col, linewidth=2)
    ax1.set_title('Cumulative Returns by Group')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative Return')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2 = axes[0, 1]
    mean_returns = group_returns.mean()
    std_returns = group_returns.std()
    x = range(len(mean_returns))
    ax2.bar(x, mean_returns.values, yerr=std_returns.values, 
           capsize=5, alpha=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(mean_returns.index, rotation=45)
    ax2.set_title('Mean Return by Group')
    ax2.set_xlabel('Group')
    ax2.set_ylabel('Mean Return')
    ax2.grid(True, alpha=0.3, axis='y')
    
    ax3 = axes[1, 0]
    long_short = group_returns.iloc[:, -1] - group_returns.iloc[:, 0]
    cumulative_ls = (1 + long_short).cumprod()
    ax3.plot(cumulative_ls.index, cumulative_ls.values, linewidth=2, color='red')
    ax3.set_title('Long-Short Cumulative Return')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Cumulative Return')
    ax3.grid(True, alpha=0.3)
    
    ax4 = axes[1, 1]
    sharpe_ratios = group_returns.mean() / group_returns.std()
    x = range(len(sharpe_ratios))
    colors = ['green' if sr > 0 else 'red' for sr in sharpe_ratios]
    ax4.bar(x, sharpe_ratios.values, color=colors, alpha=0.7)
    ax4.set_xticks(x)
    ax4.set_xticklabels(sharpe_ratios.index, rotation=45)
    ax4.set_title('Sharpe Ratio by Group')
    ax4.set_xlabel('Group')
    ax4.set_ylabel('Sharpe Ratio')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.show()


def compute_ic_ir_by_group(
    factor_data: pd.DataFrame,
    forward_returns: pd.DataFrame,
    n_groups: int = 5,
) -> pd.DataFrame:
    """
    计算各组的IC和IR
    
    Args:
        factor_data: 因子值DataFrame
        forward_returns: 未来收益DataFrame
        n_groups: 分组数量
    
    Returns:
        各组IC和IR统计DataFrame
    """
    from .ic_analysis import ICAnalyzer
    
    dates = factor_data.index.intersection(forward_returns.index)
    
    group_ic_dict = {f'group_{i}': [] for i in range(n_groups)}
    
    for date in dates:
        factor_series = factor_data.loc[date].dropna()
        return_series = forward_returns.loc[date].dropna()
        
        common_stocks = factor_series.index.intersection(return_series.index)
        
        if len(common_stocks) < n_groups:
            continue
        
        factor_values = factor_series.loc[common_stocks]
        return_values = return_series.loc[common_stocks]
        
        labels = pd.qcut(
            factor_values, 
            n_groups, 
            labels=False, 
            duplicates='drop'
        )
        
        for group_id in range(n_groups):
            group_stocks = labels[labels == group_id].index
            if len(group_stocks) > 0:
                group_factor = factor_values.loc[group_stocks]
                group_return = return_values.loc[group_stocks]
                
                analyzer = ICAnalyzer()
                ic = analyzer.compute_ic(group_factor, group_return)
                group_ic_dict[f'group_{group_id}'].append(ic)
    
    result_list = []
    for group_name, ic_list in group_ic_dict.items():
        ic_series = pd.Series(ic_list)
        result_list.append({
            'group': group_name,
            'ic_mean': ic_series.mean(),
            'ic_std': ic_series.std(),
            'icir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0,
        })
    
    return pd.DataFrame(result_list).set_index('group')
