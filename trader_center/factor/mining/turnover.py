"""
换手率分析模块

提供因子策略的换手率分析功能，评估交易成本。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np


class TurnoverAnalyzer:
    """
    换手率分析器
    
    计算因子策略的换手率，评估交易成本。
    
    Example:
        analyzer = TurnoverAnalyzer()
        turnover_result = analyzer.compute_factor_turnover(factor_data)
    """
    
    def __init__(self):
        self.turnover_series_: Optional[pd.Series] = None
        self.group_turnover_: Optional[pd.DataFrame] = None
        self.top_n_turnover_: Optional[Dict[int, pd.Series]] = None
        
    def compute_factor_turnover(
        self,
        factor_data: pd.DataFrame,
        holding_period: int = 1,
    ) -> pd.Series:
        """
        计算因子整体换手率
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            holding_period: 持仓周期（天）
        
        Returns:
            换手率时间序列Series
        """
        if holding_period < 1:
            raise ValueError("持仓周期必须大于等于1")
        
        turnover_list = []
        dates = factor_data.index.sort_values()
        
        for i in range(holding_period, len(dates)):
            current_date = dates[i]
            prev_date = dates[i - holding_period]
            
            current_stocks = set(factor_data.loc[current_date].dropna().index)
            prev_stocks = set(factor_data.loc[prev_date].dropna().index)
            
            common_stocks = current_stocks.intersection(prev_stocks)
            total_stocks = len(current_stocks.union(prev_stocks))
            
            if total_stocks > 0:
                turnover = 1 - len(common_stocks) / total_stocks
            else:
                turnover = 0
            
            turnover_list.append({'date': current_date, 'turnover': turnover})
        
        self.turnover_series_ = pd.Series(
            [item['turnover'] for item in turnover_list],
            index=[item['date'] for item in turnover_list]
        )
        
        return self.turnover_series_
    
    def compute_group_turnover(
        self,
        factor_data: pd.DataFrame,
        n_groups: int = 5,
        holding_period: int = 1,
    ) -> pd.DataFrame:
        """
        计算各分组的换手率
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            n_groups: 分组数量
            holding_period: 持仓周期（天）
        
        Returns:
            各分组换手率DataFrame，index为日期，columns为分组
        """
        if n_groups < 2:
            raise ValueError("分组数量必须大于等于2")
        
        group_turnover_list = []
        dates = factor_data.index.sort_values()
        
        for i in range(holding_period, len(dates)):
            current_date = dates[i]
            prev_date = dates[i - holding_period]
            
            current_factor = factor_data.loc[current_date].dropna()
            prev_factor = factor_data.loc[prev_date].dropna()
            
            if len(current_factor) == 0 or len(prev_factor) == 0:
                continue
            
            # 计算分组
            current_groups = pd.qcut(current_factor, n_groups, labels=False)
            prev_groups = pd.qcut(prev_factor, n_groups, labels=False)
            
            group_turnover = {}
            for group in range(n_groups):
                current_group_stocks = set(current_factor[current_groups == group].index)
                prev_group_stocks = set(prev_factor[prev_groups == group].index)
                
                common_stocks = current_group_stocks.intersection(prev_group_stocks)
                total_stocks = len(current_group_stocks.union(prev_group_stocks))
                
                if total_stocks > 0:
                    group_turnover[f'group_{group+1}'] = 1 - len(common_stocks) / total_stocks
                else:
                    group_turnover[f'group_{group+1}'] = 0
            
            group_turnover['date'] = current_date
            group_turnover_list.append(group_turnover)
        
        self.group_turnover_ = pd.DataFrame(group_turnover_list).set_index('date')
        
        return self.group_turnover_
    
    def compute_top_n_turnover(
        self,
        factor_data: pd.DataFrame,
        n_values: List[int] = [10, 20, 50],
        holding_period: int = 1,
    ) -> Dict[int, pd.Series]:
        """
        计算Top-N持仓的换手率
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            n_values: Top-N的N值列表
            holding_period: 持仓周期（天）
        
        Returns:
            各Top-N换手率的字典，{N: 换手率时间序列}
        """
        top_n_turnover = {}
        dates = factor_data.index.sort_values()
        
        for n in n_values:
            turnover_list = []
            
            for i in range(holding_period, len(dates)):
                current_date = dates[i]
                prev_date = dates[i - holding_period]
                
                current_factor = factor_data.loc[current_date].dropna()
                prev_factor = factor_data.loc[prev_date].dropna()
                
                if len(current_factor) < n or len(prev_factor) < n:
                    continue
                
                # 获取Top-N股票
                current_top_n = set(current_factor.nlargest(n).index)
                prev_top_n = set(prev_factor.nlargest(n).index)
                
                common_stocks = current_top_n.intersection(prev_top_n)
                total_stocks = len(current_top_n.union(prev_top_n))
                
                if total_stocks > 0:
                    turnover = 1 - len(common_stocks) / total_stocks
                else:
                    turnover = 0
                
                turnover_list.append({'date': current_date, 'turnover': turnover})
            
            if turnover_list:
                top_n_turnover[n] = pd.Series(
                    [item['turnover'] for item in turnover_list],
                    index=[item['date'] for item in turnover_list]
                )
        
        self.top_n_turnover_ = top_n_turnover
        
        return top_n_turnover
    
    def analyze_turnover_cost(
        self,
        turnover_series: pd.Series,
        cost_per_trade: float = 0.001,
    ) -> Dict[str, float]:
        """
        分析换手率与交易成本的关系
        
        Args:
            turnover_series: 换手率时间序列
            cost_per_trade: 单次交易成本（百分比）
        
        Returns:
            交易成本分析结果
        """
        if len(turnover_series) == 0:
            return {
                'average_turnover': 0,
                'annualized_turnover': 0,
                'average_daily_cost': 0,
                'annualized_cost': 0,
                'estimated_holding_period': 0
            }
        
        average_turnover = turnover_series.mean()
        annualized_turnover = average_turnover * 252
        
        average_daily_cost = average_turnover * cost_per_trade
        annualized_cost = annualized_turnover * cost_per_trade
        
        estimated_holding_period = 1 / average_turnover if average_turnover > 0 else float('inf')
        
        return {
            'average_turnover': average_turnover,
            'annualized_turnover': annualized_turnover,
            'average_daily_cost': average_daily_cost,
            'annualized_cost': annualized_cost,
            'estimated_holding_period': estimated_holding_period
        }
    
    def get_turnover_summary(
        self,
        cost_per_trade: float = 0.001,
    ) -> Dict[str, float]:
        """
        获取换手率统计摘要
        
        Args:
            cost_per_trade: 单次交易成本（百分比）
        
        Returns:
            换手率统计摘要
        """
        if self.turnover_series_ is None:
            raise ValueError("请先调用 compute_factor_turnover 方法")
        
        summary = {
            'mean_turnover': self.turnover_series_.mean(),
            'median_turnover': self.turnover_series_.median(),
            'std_turnover': self.turnover_series_.std(),
            'min_turnover': self.turnover_series_.min(),
            'max_turnover': self.turnover_series_.max(),
            'annualized_turnover': self.turnover_series_.mean() * 252,
        }
        
        cost_analysis = self.analyze_turnover_cost(self.turnover_series_, cost_per_trade)
        summary.update(cost_analysis)
        
        return summary


def plot_turnover_series(
    turnover_series: pd.Series,
    title: str = 'Turnover Time Series',
    figsize: tuple = (12, 6),
) -> None:
    """
    绘制换手率时间序列
    
    Args:
        turnover_series: 换手率时间序列
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    plt.plot(turnover_series.index, turnover_series.values, linewidth=2)
    plt.axhline(y=turnover_series.mean(), color='red', linestyle='--', 
                label=f'Mean: {turnover_series.mean():.4f}')
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Turnover')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_turnover_distribution(
    turnover_series: pd.Series,
    bins: int = 50,
    title: str = 'Turnover Distribution',
    figsize: tuple = (10, 6),
) -> None:
    """
    绘制换手率分布图
    
    Args:
        turnover_series: 换手率时间序列
        bins: 直方图 bins 数量
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    plt.hist(turnover_series.values, bins=bins, alpha=0.7, edgecolor='black')
    plt.axvline(x=turnover_series.mean(), color='red', linestyle='--', 
                label=f'Mean: {turnover_series.mean():.4f}')
    plt.title(title)
    plt.xlabel('Turnover')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()


def plot_group_turnover(
    group_turnover: pd.DataFrame,
    title: str = 'Group Turnover Comparison',
    figsize: tuple = (12, 6),
) -> None:
    """
    绘制分组换手率对比图
    
    Args:
        group_turnover: 分组换手率DataFrame
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    for column in group_turnover.columns:
        plt.plot(group_turnover.index, group_turnover[column], label=column)
    
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Turnover')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_top_n_turnover(
    top_n_turnover: Dict[int, pd.Series],
    title: str = 'Top-N Turnover Comparison',
    figsize: tuple = (12, 6),
) -> None:
    """
    绘制Top-N换手率对比图
    
    Args:
        top_n_turnover: Top-N换手率字典
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    for n, turnover_series in top_n_turnover.items():
        plt.plot(turnover_series.index, turnover_series.values, label=f'Top-{n}')
    
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Turnover')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
