"""
Alpha/Beta分析模块

提供因子的风险调整收益评估功能。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np
from scipy import stats


class AlphaBetaAnalyzer:
    """
    Alpha/Beta分析器
    
    计算因子的Alpha、Beta和风险调整收益指标。
    
    Example:
        analyzer = AlphaBetaAnalyzer()
        alpha_beta = analyzer.compute_factor_alpha_beta(factor_returns, benchmark_returns)
    """
    
    def __init__(self):
        self.alpha_: Optional[float] = None
        self.beta_: Optional[float] = None
        self.alpha_series_: Optional[pd.Series] = None
        self.beta_series_: Optional[pd.Series] = None
        
    def compute_factor_returns(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        quantile: int = 1,
    ) -> pd.Series:
        """
        计算因子组合收益
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            forward_returns: 未来收益DataFrame，index为日期，columns为股票代码
            quantile: 分组序号（1为最高分组，-1为最低分组）
        
        Returns:
            因子组合收益时间序列
        """
        factor_returns = []
        dates = factor_data.index.intersection(forward_returns.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            return_series = forward_returns.loc[date].dropna()
            
            common_index = factor_series.index.intersection(return_series.index)
            if len(common_index) < 10:
                continue
            
            factor_series = factor_series.loc[common_index]
            return_series = return_series.loc[common_index]
            
            # 按因子值分组，处理重复值
            try:
                groups = pd.qcut(factor_series, 5, labels=False)
            except ValueError:
                # 处理重复值的情况
                groups = pd.qcut(factor_series, 5, labels=False, duplicates='drop')
            
            # 取最高或最低分组
            if quantile == 1:
                group_stocks = groups == 4  # 最高分组
            elif quantile == -1:
                group_stocks = groups == 0  # 最低分组
            else:
                raise ValueError("quantile 只能是 1 或 -1")
            
            if group_stocks.sum() < 5:
                continue
            
            # 等权计算组合收益
            group_return = return_series[group_stocks].mean()
            factor_returns.append({'date': date, 'return': group_return})
        
        if factor_returns:
            return pd.Series(
                [item['return'] for item in factor_returns],
                index=[item['date'] for item in factor_returns]
            )
        else:
            return pd.Series(dtype='float64')
    
    def compute_factor_alpha_beta(
        self,
        factor_returns: pd.Series,
        benchmark_returns: pd.Series,
        risk_free_rate: float = 0.0,
    ) -> Dict[str, float]:
        """
        计算因子Alpha和Beta
        
        Args:
            factor_returns: 因子组合收益时间序列
            benchmark_returns: 基准收益时间序列
            risk_free_rate: 无风险利率
        
        Returns:
            Alpha、Beta等指标
        """
        # 对齐数据
        common_dates = factor_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 2:
            return {
                'alpha': np.nan,
                'beta': np.nan,
                'r_squared': np.nan,
                'tracking_error': np.nan,
                'information_ratio': np.nan,
                'sharpe_ratio': np.nan,
                'treynor_ratio': np.nan
            }
        
        factor_series = factor_returns.loc[common_dates]
        benchmark_series = benchmark_returns.loc[common_dates]
        
        # 计算超额收益
        factor_excess = factor_series - risk_free_rate
        benchmark_excess = benchmark_series - risk_free_rate
        
        # 线性回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            benchmark_excess.values, factor_excess.values
        )
        
        self.alpha_ = intercept
        self.beta_ = slope
        
        # 计算其他指标
        tracking_error = np.std(factor_excess - slope * benchmark_excess)
        information_ratio = intercept / tracking_error if tracking_error > 0 else 0
        sharpe_ratio = factor_excess.mean() / factor_excess.std() if factor_excess.std() > 0 else 0
        treynor_ratio = factor_excess.mean() / slope if slope > 0 else 0
        
        return {
            'alpha': intercept,
            'beta': slope,
            'r_squared': r_value ** 2,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'sharpe_ratio': sharpe_ratio,
            'treynor_ratio': treynor_ratio
        }
    
    def compute_alpha_by_period(
        self,
        factor_returns: pd.Series,
        benchmark_returns: pd.Series,
        period: str = 'month',
        risk_free_rate: float = 0.0,
    ) -> pd.Series:
        """
        分时期计算Alpha
        
        Args:
            factor_returns: 因子组合收益时间序列
            benchmark_returns: 基准收益时间序列
            period: 时期类型 ('month', 'quarter', 'year')
            risk_free_rate: 无风险利率
        
        Returns:
            各时期的Alpha值
        """
        # 对齐数据
        common_dates = factor_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 2:
            return pd.Series(dtype='float64')
        
        factor_series = factor_returns.loc[common_dates]
        benchmark_series = benchmark_returns.loc[common_dates]
        
        # 按时期分组
        if period == 'month':
            groups = factor_series.index.to_period('M')
        elif period == 'quarter':
            groups = factor_series.index.to_period('Q')
        elif period == 'year':
            groups = factor_series.index.to_period('Y')
        else:
            raise ValueError("period 只能是 'month', 'quarter' 或 'year'")
        
        alpha_by_period = {}
        
        for group in groups.unique():
            group_dates = groups[groups == group].index
            if len(group_dates) < 2:
                continue
            
            group_factor = factor_series.loc[group_dates]
            group_benchmark = benchmark_series.loc[group_dates]
            
            result = self.compute_factor_alpha_beta(group_factor, group_benchmark, risk_free_rate)
            alpha_by_period[group] = result['alpha']
        
        return pd.Series(alpha_by_period)
    
    def compute_alpha_exposure(
        self,
        factor_data: pd.DataFrame,
        market_factor: pd.DataFrame,
    ) -> pd.Series:
        """
        计算因子暴露
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            market_factor: 市场因子DataFrame，index为日期，columns为股票代码
        
        Returns:
            因子暴露时间序列
        """
        exposure = []
        dates = factor_data.index.intersection(market_factor.index)
        
        for date in dates:
            factor_series = factor_data.loc[date].dropna()
            market_series = market_factor.loc[date].dropna()
            
            common_index = factor_series.index.intersection(market_series.index)
            if len(common_index) < 5:
                continue
            
            factor_series = factor_series.loc[common_index]
            market_series = market_series.loc[common_index]
            
            # 计算相关系数作为暴露度
            corr = stats.pearsonr(factor_series, market_series)[0]
            exposure.append({'date': date, 'exposure': corr})
        
        if exposure:
            return pd.Series(
                [item['exposure'] for item in exposure],
                index=[item['date'] for item in exposure]
            )
        else:
            return pd.Series(dtype='float64')
    
    def compute_tracking_error(
        self,
        factor_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """
        计算跟踪误差
        
        Args:
            factor_returns: 因子组合收益时间序列
            benchmark_returns: 基准收益时间序列
        
        Returns:
            跟踪误差
        """
        # 对齐数据
        common_dates = factor_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 2:
            return np.nan
        
        factor_series = factor_returns.loc[common_dates]
        benchmark_series = benchmark_returns.loc[common_dates]
        
        # 计算跟踪误差
        tracking_error = np.std(factor_series - benchmark_series)
        
        return tracking_error
    
    def get_risk_adjusted_metrics(
        self,
        factor_returns: pd.Series,
        benchmark_returns: pd.Series,
        risk_free_rate: float = 0.0,
    ) -> Dict[str, float]:
        """
        获取风险调整指标
        
        Args:
            factor_returns: 因子组合收益时间序列
            benchmark_returns: 基准收益时间序列
            risk_free_rate: 无风险利率
        
        Returns:
            风险调整指标
        """
        # 对齐数据
        common_dates = factor_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 2:
            return {
                'annualized_return': 0,
                'annualized_volatility': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'calmar_ratio': 0,
                'sortino_ratio': 0
            }
        
        factor_series = factor_returns.loc[common_dates]
        benchmark_series = benchmark_returns.loc[common_dates]
        
        # 计算年化收益
        annualized_return = factor_series.mean() * 252
        
        # 计算年化波动率
        annualized_volatility = factor_series.std() * np.sqrt(252)
        
        # 计算夏普比率
        excess_return = factor_series - risk_free_rate
        sharpe_ratio = (excess_return.mean() * 252) / (excess_return.std() * np.sqrt(252)) if excess_return.std() > 0 else 0
        
        # 计算最大回撤
        cumulative_returns = (1 + factor_series).cumprod()
        rolling_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 计算卡玛比率
        calmar_ratio = -annualized_return / max_drawdown if max_drawdown < 0 else 0
        
        # 计算索提诺比率
        downside_returns = excess_return[excess_return < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 1
        sortino_ratio = (excess_return.mean() * 252) / downside_volatility
        
        return {
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio
        }


def plot_alpha_beta_ts(
    alpha_series: pd.Series,
    beta_series: pd.Series,
    title: str = 'Alpha/Beta Time Series',
    figsize: tuple = (12, 8),
) -> None:
    """
    绘制Alpha/Beta时间序列
    
    Args:
        alpha_series: Alpha时间序列
        beta_series: Beta时间序列
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
    
    # 绘制Alpha
    ax1.plot(alpha_series.index, alpha_series.values, linewidth=2)
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.set_title('Alpha Time Series')
    ax1.set_ylabel('Alpha')
    ax1.grid(True, alpha=0.3)
    
    # 绘制Beta
    ax2.plot(beta_series.index, beta_series.values, linewidth=2, color='orange')
    ax2.axhline(y=1, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('Beta Time Series')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Beta')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


def plot_alpha_distribution(
    alpha_series: pd.Series,
    title: str = 'Alpha Distribution',
    bins: int = 50,
    figsize: tuple = (10, 6),
) -> None:
    """
    绘制Alpha分布图
    
    Args:
        alpha_series: Alpha时间序列
        title: 图表标题
        bins: 直方图 bins 数量
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    plt.hist(alpha_series.values, bins=bins, alpha=0.7, edgecolor='black')
    plt.axvline(x=alpha_series.mean(), color='red', linestyle='--', 
                label=f'Mean: {alpha_series.mean():.4f}')
    plt.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    plt.title(title)
    plt.xlabel('Alpha')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()


def plot_risk_return_scatter(
    factor_returns: pd.Series,
    benchmark_returns: pd.Series,
    title: str = 'Risk-Return Scatter',
    figsize: tuple = (10, 6),
) -> None:
    """
    绘制风险收益散点图
    
    Args:
        factor_returns: 因子组合收益时间序列
        benchmark_returns: 基准收益时间序列
        title: 图表标题
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=figsize)
    
    # 计算累计收益
    factor_cumulative = (1 + factor_returns).cumprod() - 1
    benchmark_cumulative = (1 + benchmark_returns).cumprod() - 1
    
    # 计算风险（波动率）
    factor_volatility = factor_returns.std() * np.sqrt(252)
    benchmark_volatility = benchmark_returns.std() * np.sqrt(252)
    
    # 计算收益（年化）
    factor_return = factor_returns.mean() * 252
    benchmark_return = benchmark_returns.mean() * 252
    
    # 绘制散点
    plt.scatter(factor_volatility, factor_return, s=100, label='Factor')
    plt.scatter(benchmark_volatility, benchmark_return, s=100, label='Benchmark')
    
    # 绘制标签
    plt.annotate('Factor', (factor_volatility, factor_return), 
                xytext=(10, 10), textcoords='offset points')
    plt.annotate('Benchmark', (benchmark_volatility, benchmark_return), 
                xytext=(10, 10), textcoords='offset points')
    
    plt.title(title)
    plt.xlabel('Annualized Volatility')
    plt.ylabel('Annualized Return')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
