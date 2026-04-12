"""
分组IC分析模块

提供因子在不同市场环境下的IC分析功能。
"""

from typing import Optional, Dict, List, Union, Tuple
import pandas as pd
import numpy as np
from scipy import stats


class GroupedICAnalyzer:
    """
    分组IC分析器
    
    计算因子在不同分组（如行业、市值、波动率）下的IC值。
    
    Example:
        analyzer = GroupedICAnalyzer()
        ic_by_sector = analyzer.compute_ic_by_sector(factor_data, forward_returns, sector_data)
    """
    
    def __init__(self):
        self.ic_by_group_: Optional[Dict[str, pd.Series]] = None
        self.group_summary_: Optional[pd.DataFrame] = None
        
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
    
    def compute_ic_by_sector(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        sector_data: pd.DataFrame,
        method: str = 'spearman',
    ) -> Dict[str, pd.Series]:
        """
        按行业计算IC
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            sector_data: 行业数据DataFrame，index为日期，columns为股票代码，值为行业名称
            method: 相关性计算方法
        
        Returns:
            各行业IC时间序列的字典，{行业名称: IC序列}
        """
        ic_by_sector = {}
        dates = factor_data.index.intersection(forward_returns.index).intersection(sector_data.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            sector_series = sector_data.loc[date].dropna()
            
            common_index = factor_series.index.intersection(return_series.index).intersection(sector_series.index)
            if len(common_index) < 5:
                continue
            
            factor_series = factor_series.loc[common_index]
            return_series = return_series.loc[common_index]
            sector_series = sector_series.loc[common_index]
            
            # 按行业分组计算IC
            for sector in sector_series.unique():
                sector_stocks = sector_series[sector_series == sector].index
                if len(sector_stocks) < 5:
                    continue
                
                sector_factor = factor_series.loc[sector_stocks]
                sector_return = return_series.loc[sector_stocks]
                
                ic = self.compute_ic(sector_factor, sector_return, method)
                
                if sector not in ic_by_sector:
                    ic_by_sector[sector] = []
                ic_by_sector[sector].append({'date': date, 'ic': ic})
        
        # 转换为Series
        for sector, data in ic_by_sector.items():
            ic_by_sector[sector] = pd.Series(
                [item['ic'] for item in data],
                index=[item['date'] for item in data]
            )
        
        self.ic_by_group_ = ic_by_sector
        
        return ic_by_sector
    
    def compute_ic_by_market_cap(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        market_cap_data: pd.DataFrame,
        n_groups: int = 5,
        method: str = 'spearman',
    ) -> Dict[str, pd.Series]:
        """
        按市值计算IC
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            market_cap_data: 市值数据DataFrame，index为日期，columns为股票代码
            n_groups: 分组数量
            method: 相关性计算方法
        
        Returns:
            各市值分组IC时间序列的字典，{分组名称: IC序列}
        """
        ic_by_cap = {}
        dates = factor_data.index.intersection(forward_returns.index).intersection(market_cap_data.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            cap_series = market_cap_data.loc[date].dropna()
            
            common_index = factor_series.index.intersection(return_series.index).intersection(cap_series.index)
            if len(common_index) < 5:
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
                
                if group not in ic_by_cap:
                    ic_by_cap[group] = []
                ic_by_cap[group].append({'date': date, 'ic': ic})
        
        # 转换为Series
        for group, data in ic_by_cap.items():
            ic_by_cap[group] = pd.Series(
                [item['ic'] for item in data],
                index=[item['date'] for item in data]
            )
        
        self.ic_by_group_ = ic_by_cap
        
        return ic_by_cap
    
    def compute_ic_by_volatility(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        volatility_data: pd.DataFrame,
        n_groups: int = 5,
        method: str = 'spearman',
    ) -> Dict[str, pd.Series]:
        """
        按波动率计算IC
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            volatility_data: 波动率数据DataFrame，index为日期，columns为股票代码
            n_groups: 分组数量
            method: 相关性计算方法
        
        Returns:
            各波动率分组IC时间序列的字典，{分组名称: IC序列}
        """
        ic_by_vol = {}
        dates = factor_data.index.intersection(forward_returns.index).intersection(volatility_data.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            vol_series = volatility_data.loc[date].dropna()
            
            common_index = factor_series.index.intersection(return_series.index).intersection(vol_series.index)
            if len(common_index) < 5:
                continue
            
            factor_series = factor_series.loc[common_index]
            return_series = return_series.loc[common_index]
            vol_series = vol_series.loc[common_index]
            
            # 按波动率分组
            groups = pd.qcut(vol_series, n_groups, labels=[f'vol_group_{i+1}' for i in range(n_groups)])
            
            for group in groups.unique():
                group_stocks = groups[groups == group].index
                if len(group_stocks) < 5:
                    continue
                
                group_factor = factor_series.loc[group_stocks]
                group_return = return_series.loc[group_stocks]
                
                ic = self.compute_ic(group_factor, group_return, method)
                
                if group not in ic_by_vol:
                    ic_by_vol[group] = []
                ic_by_vol[group].append({'date': date, 'ic': ic})
        
        # 转换为Series
        for group, data in ic_by_vol.items():
            ic_by_vol[group] = pd.Series(
                [item['ic'] for item in data],
                index=[item['date'] for item in data]
            )
        
        self.ic_by_group_ = ic_by_vol
        
        return ic_by_vol
    
    def compute_ic_by_double_group(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        group_data1: pd.DataFrame,
        group_data2: pd.DataFrame,
        method: str = 'spearman',
    ) -> Dict[Tuple[str, str], pd.Series]:
        """
        双维度分组计算IC
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            group_data1: 第一维度分组数据（如行业）
            group_data2: 第二维度分组数据（如市值）
            method: 相关性计算方法
        
        Returns:
            双维度分组IC时间序列的字典，{(分组1, 分组2): IC序列}
        """
        ic_by_double_group = {}
        dates = factor_data.index.intersection(forward_returns.index).intersection(group_data1.index).intersection(group_data2.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            group1_series = group_data1.loc[date].dropna()
            group2_series = group_data2.loc[date].dropna()
            
            common_index = factor_series.index.intersection(return_series.index).intersection(group1_series.index).intersection(group2_series.index)
            if len(common_index) < 5:
                continue
            
            factor_series = factor_series.loc[common_index]
            return_series = return_series.loc[common_index]
            group1_series = group1_series.loc[common_index]
            group2_series = group2_series.loc[common_index]
            
            # 双维度分组
            for g1 in group1_series.unique():
                for g2 in group2_series.unique():
                    mask = (group1_series == g1) & (group2_series == g2)
                    group_stocks = mask[mask].index
                    
                    if len(group_stocks) < 5:
                        continue
                    
                    group_factor = factor_series.loc[group_stocks]
                    group_return = return_series.loc[group_stocks]
                    
                    ic = self.compute_ic(group_factor, group_return, method)
                    
                    key = (g1, g2)
                    if key not in ic_by_double_group:
                        ic_by_double_group[key] = []
                    ic_by_double_group[key].append({'date': date, 'ic': ic})
        
        # 转换为Series
        for key, data in ic_by_double_group.items():
            ic_by_double_group[key] = pd.Series(
                [item['ic'] for item in data],
                index=[item['date'] for item in data]
            )
        
        return ic_by_double_group
    
    def find_best_environment(
        self,
        ic_by_group: Dict[str, pd.Series],
    ) -> Dict[str, Dict[str, float]]:
        """
        识别因子最佳使用环境
        
        Args:
            ic_by_group: 分组IC字典
        
        Returns:
            各分组的IC统计信息，{分组名称: {统计指标: 值}}
        """
        best_env = {}
        
        for group, ic_series in ic_by_group.items():
            if len(ic_series) < 1:
                continue
            
            ic_mean = ic_series.mean()
            ic_std = ic_series.std()
            icir = ic_mean / ic_std if ic_std > 0 else 0
            positive_ratio = (ic_series > 0).mean()
            significant_ratio = (np.abs(ic_series) > 0.02).mean()
            
            best_env[group] = {
                'ic_mean': ic_mean,
                'ic_std': ic_std,
                'icir': icir,
                'positive_ratio': positive_ratio,
                'significant_ratio': significant_ratio,
                'n_observations': len(ic_series)
            }
        
        # 按IC均值排序
        best_env = dict(sorted(best_env.items(), key=lambda x: x[1]['ic_mean'], reverse=True))
        
        return best_env
    
    def get_group_summary(
        self,
        ic_by_group: Dict[str, pd.Series],
    ) -> pd.DataFrame:
        """
        获取分组IC摘要
        
        Args:
            ic_by_group: 分组IC字典
        
        Returns:
            分组IC摘要DataFrame
        """
        summary_data = []
        
        for group, ic_series in ic_by_group.items():
            if len(ic_series) < 1:
                continue
            
            ic_mean = ic_series.mean()
            ic_std = ic_series.std()
            icir = ic_mean / ic_std if ic_std > 0 else 0
            positive_ratio = (ic_series > 0).mean()
            significant_ratio = (np.abs(ic_series) > 0.02).mean()
            
            summary_data.append({
                'group': group,
                'ic_mean': ic_mean,
                'ic_std': ic_std,
                'icir': icir,
                'positive_ratio': positive_ratio,
                'significant_ratio': significant_ratio,
                'n_observations': len(ic_series)
            })
        
        self.group_summary_ = pd.DataFrame(summary_data).sort_values('ic_mean', ascending=False)
        
        return self.group_summary_


def plot_grouped_ic_heatmap(
    group_summary: pd.DataFrame,
    value_col: str = 'ic_mean',
    title: str = 'Grouped IC Heatmap',
    figsize: tuple = (12, 8),
) -> None:
    """
    绘制分组IC热力图
    
    Args:
        group_summary: 分组IC摘要DataFrame
        value_col: 要显示的值列
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    plt.figure(figsize=figsize)
    
    # 准备数据
    pivot_data = group_summary.pivot_table(
        values=value_col,
        index='group',
        columns='group',
        fill_value=0
    )
    
    sns.heatmap(pivot_data, annot=True, cmap='RdYlGn', center=0, fmt='.4f')
    plt.title(title)
    plt.tight_layout()
    plt.show()


def plot_ic_by_group_bar(
    group_summary: pd.DataFrame,
    value_col: str = 'ic_mean',
    title: str = 'IC by Group',
    figsize: tuple = (12, 6),
) -> None:
    """
    绘制分组IC柱状图
    
    Args:
        group_summary: 分组IC摘要DataFrame
        value_col: 要显示的值列
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    plt.bar(group_summary['group'], group_summary[value_col])
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    plt.title(title)
    plt.xlabel('Group')
    plt.ylabel(value_col)
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()


def plot_ic_by_group_time_series(
    ic_by_group: Dict[str, pd.Series],
    title: str = 'IC by Group Time Series',
    figsize: tuple = (12, 6),
) -> None:
    """
    绘制分组IC时间序列
    
    Args:
        ic_by_group: 分组IC字典
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    for group, ic_series in ic_by_group.items():
        plt.plot(ic_series.index, ic_series.values, label=group)
    
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('IC')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
