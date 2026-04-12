"""
稳健性测试模块

提供因子在不同市场环境下的稳定性测试功能。
"""

from typing import Optional, Dict, List, Union, Tuple
import pandas as pd
import numpy as np
from scipy import stats


class RobustnessTester:
    """
    稳健性测试器
    
    测试因子在不同市场环境下的稳定性。
    
    Example:
        tester = RobustnessTester()
        period_test = tester.test_by_time_period(factor_data, forward_returns)
    """
    
    def __init__(self):
        self.period_results_: Optional[Dict[str, Dict[str, float]]] = None
        self.sector_results_: Optional[Dict[str, Dict[str, float]]] = None
        self.cap_results_: Optional[Dict[str, Dict[str, float]]] = None
        self.rolling_results_: Optional[pd.DataFrame] = None
        
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
    
    def test_by_time_period(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        market_data: Optional[pd.Series] = None,
        method: str = 'spearman',
    ) -> Dict[str, Dict[str, float]]:
        """
        分时间段测试
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            market_data: 市场指数数据，用于划分牛熊市
            method: 相关性计算方法
        
        Returns:
            各时间段的测试结果
        """
        results = {}
        dates = factor_data.index.intersection(forward_returns.index)
        
        if market_data is not None:
            # 使用市场数据划分牛熊市
            market_returns = market_data.pct_change().dropna()
            
            # 简单的牛熊市划分：连续上涨为牛市，连续下跌为熊市，否则为震荡市
            market_trend = []
            for date in dates:
                if date not in market_returns.index:
                    market_trend.append('unknown')
                else:
                    # 计算过去20天的市场表现
                    past_returns = market_returns.loc[:date].tail(20)
                    if len(past_returns) < 10:
                        market_trend.append('unknown')
                    else:
                        avg_return = past_returns.mean()
                        if avg_return > 0.0005:
                            market_trend.append('bull')
                        elif avg_return < -0.0005:
                            market_trend.append('bear')
                        else:
                            market_trend.append('neutral')
            
            # 按市场状态分组
            for trend in ['bull', 'bear', 'neutral']:
                trend_dates = [date for date, t in zip(dates, market_trend) if t == trend]
                if len(trend_dates) < 10:
                    continue
                
                ic_list = []
                for date in trend_dates:
                    factor_series = factor_data.loc[date].dropna()
                    return_series = forward_returns.loc[date].dropna()
                    ic = self.compute_ic(factor_series, return_series, method)
                    if not np.isnan(ic):
                        ic_list.append(ic)
                
                if ic_list:
                    results[trend] = {
                        'ic_mean': np.mean(ic_list),
                        'ic_std': np.std(ic_list),
                        'icir': np.mean(ic_list) / np.std(ic_list) if np.std(ic_list) > 0 else 0,
                        'positive_ratio': (np.array(ic_list) > 0).mean(),
                        'n_observations': len(ic_list)
                    }
        else:
            # 按时间等分为3段
            n_periods = 3
            period_length = len(dates) // n_periods
            
            for i in range(n_periods):
                start_idx = i * period_length
                end_idx = (i + 1) * period_length if i < n_periods - 1 else len(dates)
                period_dates = dates[start_idx:end_idx]
                
                ic_list = []
                for date in period_dates:
                    factor_series = factor_data.loc[date].dropna()
                    return_series = forward_returns.loc[date].dropna()
                    ic = self.compute_ic(factor_series, return_series, method)
                    if not np.isnan(ic):
                        ic_list.append(ic)
                
                if ic_list:
                    results[f'period_{i+1}'] = {
                        'ic_mean': np.mean(ic_list),
                        'ic_std': np.std(ic_list),
                        'icir': np.mean(ic_list) / np.std(ic_list) if np.std(ic_list) > 0 else 0,
                        'positive_ratio': (np.array(ic_list) > 0).mean(),
                        'n_observations': len(ic_list)
                    }
        
        self.period_results_ = results
        
        return results
    
    def test_by_market_cap(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        market_cap_data: pd.DataFrame,
        n_groups: int = 3,
        method: str = 'spearman',
    ) -> Dict[str, Dict[str, float]]:
        """
        分市值测试
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            market_cap_data: 市值数据DataFrame，index为日期，columns为股票代码
            n_groups: 分组数量
            method: 相关性计算方法
        
        Returns:
            各市值分组的测试结果
        """
        results = {}
        dates = factor_data.index.intersection(forward_returns.index).intersection(market_cap_data.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            cap_series = market_cap_data.loc[date].dropna()
            
            common_index = factor_series.index.intersection(return_series.index).intersection(cap_series.index)
            if len(common_index) < 10:
                continue
            
            factor_series = factor_series.loc[common_index]
            return_series = return_series.loc[common_index]
            cap_series = cap_series.loc[common_index]
            
            # 按市值分组
            groups = pd.qcut(cap_series, n_groups, labels=[f'cap_group_{i+1}' for i in range(n_groups)])
            
            for group in groups.unique():
                group_stocks = groups[groups == group].index
                if len(group_stocks) < 5:
                    continue
                
                group_factor = factor_series.loc[group_stocks]
                group_return = return_series.loc[group_stocks]
                
                ic = self.compute_ic(group_factor, group_return, method)
                if not np.isnan(ic):
                    if group not in results:
                        results[group] = []
                    results[group].append(ic)
        
        # 计算统计指标
        for group, ic_list in results.items():
            results[group] = {
                'ic_mean': np.mean(ic_list),
                'ic_std': np.std(ic_list),
                'icir': np.mean(ic_list) / np.std(ic_list) if np.std(ic_list) > 0 else 0,
                'positive_ratio': (np.array(ic_list) > 0).mean(),
                'n_observations': len(ic_list)
            }
        
        self.cap_results_ = results
        
        return results
    
    def test_by_sector(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        sector_data: pd.DataFrame,
        method: str = 'spearman',
    ) -> Dict[str, Dict[str, float]]:
        """
        分行业测试
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            sector_data: 行业数据DataFrame，index为日期，columns为股票代码
            method: 相关性计算方法
        
        Returns:
            各行业的测试结果
        """
        results = {}
        dates = factor_data.index.intersection(forward_returns.index).intersection(sector_data.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            sector_series = sector_data.loc[date].dropna()
            
            common_index = factor_series.index.intersection(return_series.index).intersection(sector_series.index)
            if len(common_index) < 10:
                continue
            
            factor_series = factor_series.loc[common_index]
            return_series = return_series.loc[common_index]
            sector_series = sector_series.loc[common_index]
            
            # 按行业分组
            for sector in sector_series.unique():
                sector_stocks = sector_series[sector_series == sector].index
                if len(sector_stocks) < 5:
                    continue
                
                sector_factor = factor_series.loc[sector_stocks]
                sector_return = return_series.loc[sector_stocks]
                
                ic = self.compute_ic(sector_factor, sector_return, method)
                if not np.isnan(ic):
                    if sector not in results:
                        results[sector] = []
                    results[sector].append(ic)
        
        # 计算统计指标
        for sector, ic_list in results.items():
            results[sector] = {
                'ic_mean': np.mean(ic_list),
                'ic_std': np.std(ic_list),
                'icir': np.mean(ic_list) / np.std(ic_list) if np.std(ic_list) > 0 else 0,
                'positive_ratio': (np.array(ic_list) > 0).mean(),
                'n_observations': len(ic_list)
            }
        
        self.sector_results_ = results
        
        return results
    
    def test_rolling_window(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        window: int = 60,
        step: int = 20,
        method: str = 'spearman',
    ) -> pd.DataFrame:
        """
        滚动窗口测试
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            window: 滚动窗口大小
            step: 步长
            method: 相关性计算方法
        
        Returns:
            滚动窗口测试结果DataFrame
        """
        results = []
        dates = factor_data.index.intersection(forward_returns.index).sort_values()
        
        for i in range(0, len(dates) - window + 1, step):
            window_dates = dates[i:i+window]
            if len(window_dates) < window:
                continue
            
            ic_list = []
            for date in window_dates:
                factor_series = factor_data.loc[date].dropna()
                return_series = forward_returns.loc[date].dropna()
                ic = self.compute_ic(factor_series, return_series, method)
                if not np.isnan(ic):
                    ic_list.append(ic)
            
            if ic_list:
                results.append({
                    'start_date': window_dates[0],
                    'end_date': window_dates[-1],
                    'ic_mean': np.mean(ic_list),
                    'ic_std': np.std(ic_list),
                    'icir': np.mean(ic_list) / np.std(ic_list) if np.std(ic_list) > 0 else 0,
                    'positive_ratio': (np.array(ic_list) > 0).mean(),
                    'n_observations': len(ic_list)
                })
        
        self.rolling_results_ = pd.DataFrame(results)
        
        return self.rolling_results_
    
    def test_bootstrapping(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        n_iterations: int = 100,
        sample_size: float = 0.8,
        method: str = 'spearman',
    ) -> Dict[str, float]:
        """
        自助法测试
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            n_iterations: 迭代次数
            sample_size: 样本比例
            method: 相关性计算方法
        
        Returns:
            自助法测试结果
        """
        ic_list = []
        dates = factor_data.index.intersection(forward_returns.index)
        
        for i in range(n_iterations):
            # 随机抽样日期
            sample_dates = np.random.choice(dates, size=int(len(dates) * sample_size), replace=True)
            
            iteration_ics = []
            for date in sample_dates:
                factor_series = factor_data.loc[date].dropna()
                return_series = forward_returns.loc[date].dropna()
                ic = self.compute_ic(factor_series, return_series, method)
                if not np.isnan(ic):
                    iteration_ics.append(ic)
            
            if iteration_ics:
                ic_list.append(np.mean(iteration_ics))
        
        if ic_list:
            return {
                'mean_ic': np.mean(ic_list),
                'std_ic': np.std(ic_list),
                'icir': np.mean(ic_list) / np.std(ic_list) if np.std(ic_list) > 0 else 0,
                'positive_ratio': (np.array(ic_list) > 0).mean(),
                'n_iterations': len(ic_list)
            }
        else:
            return {
                'mean_ic': 0,
                'std_ic': 0,
                'icir': 0,
                'positive_ratio': 0,
                'n_iterations': 0
            }
    
    def get_robustness_score(
        self,
        results: Dict[str, Dict[str, float]],
    ) -> float:
        """
        计算稳健性得分
        
        Args:
            results: 测试结果字典
        
        Returns:
            稳健性得分（0-1）
        """
        if not results:
            return 0.0
        
        # 计算方向一致性
        ic_means = [v['ic_mean'] for v in results.values()]
        positive_ics = [ic for ic in ic_means if ic > 0]
        negative_ics = [ic for ic in ic_means if ic < 0]
        
        if len(positive_ics) > len(negative_ics):
            direction_consistency = len(positive_ics) / len(ic_means)
        else:
            direction_consistency = len(negative_ics) / len(ic_means)
        
        # 计算显著性比例
        positive_ratios = [v['positive_ratio'] for v in results.values()]
        significant_ratio = np.mean([pr for pr in positive_ratios if pr > 0.5])
        
        # 计算稳健性得分
        robustness_score = (direction_consistency + significant_ratio) / 2
        
        return robustness_score


def plot_period_comparison(
    period_results: Dict[str, Dict[str, float]],
    metric: str = 'ic_mean',
    title: str = 'Performance by Time Period',
    figsize: tuple = (10, 6),
) -> None:
    """
    绘制分时期表现对比
    
    Args:
        period_results: 分时期测试结果
        metric: 要显示的指标
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    periods = list(period_results.keys())
    values = [period_results[p][metric] for p in periods]
    
    plt.bar(periods, values)
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    plt.title(title)
    plt.xlabel('Period')
    plt.ylabel(metric)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()


def plot_sector_performance(
    sector_results: Dict[str, Dict[str, float]],
    metric: str = 'ic_mean',
    title: str = 'Performance by Sector',
    figsize: tuple = (12, 8),
) -> None:
    """
    绘制分行业表现
    
    Args:
        sector_results: 分行业测试结果
        metric: 要显示的指标
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    sectors = list(sector_results.keys())
    values = [sector_results[s][metric] for s in sectors]
    
    plt.barh(sectors, values)
    plt.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    plt.title(title)
    plt.xlabel(metric)
    plt.ylabel('Sector')
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.show()


def plot_robustness_heatmap(
    results: Dict[str, Dict[str, float]],
    title: str = 'Robustness Heatmap',
    figsize: tuple = (12, 8),
) -> None:
    """
    绘制稳健性热力图
    
    Args:
        results: 测试结果
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    plt.figure(figsize=figsize)
    
    # 准备数据
    data = []
    for group, metrics in results.items():
        row = {'group': group}
        row.update(metrics)
        data.append(row)
    
    df = pd.DataFrame(data).set_index('group')
    
    # 选择要显示的指标
    metrics_to_show = ['ic_mean', 'icir', 'positive_ratio']
    df_subset = df[metrics_to_show]
    
    sns.heatmap(df_subset, annot=True, cmap='RdYlGn', center=0, fmt='.4f')
    plt.title(title)
    plt.tight_layout()
    plt.show()
