"""
因子相关性分析

提供因子间相关性、自相关性等分析功能。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np
from scipy import stats


class CorrelationAnalyzer:
    """
    相关性分析器
    
    计算因子间的相关性、自相关性等。
    
    Example:
        analyzer = CorrelationAnalyzer()
        corr_matrix = analyzer.compute_correlation_matrix(factor_data_dict)
    """
    
    def __init__(self):
        self.corr_matrix_: Optional[pd.DataFrame] = None
    
    def compute_correlation_matrix(
        self,
        factor_data_dict: Dict[str, pd.Series],
        method: str = 'pearson',
    ) -> pd.DataFrame:
        """
        计算因子间相关性矩阵
        
        Args:
            factor_data_dict: 因子数据字典，{因子名称: Series}
            method: 相关性计算方法 ('pearson' 或 'spearman')
        
        Returns:
            相关性矩阵DataFrame
        
        Example:
            corr_matrix = analyzer.compute_correlation_matrix(
                {'momentum': momentum_series, 'rsi': rsi_series}
            )
        """
        factor_names = list(factor_data_dict.keys())
        n_factors = len(factor_names)
        
        corr_matrix = pd.DataFrame(
            np.eye(n_factors),
            index=factor_names,
            columns=factor_names
        )
        
        for i in range(n_factors):
            for j in range(i+1, n_factors):
                factor_i = factor_data_dict[factor_names[i]]
                factor_j = factor_data_dict[factor_names[j]]
                
                common_index = factor_i.index.intersection(factor_j.index)
                
                if len(common_index) < 5:
                    corr = np.nan
                else:
                    values_i = factor_i.loc[common_index]
                    values_j = factor_j.loc[common_index]
                    
                    valid_mask = ~(values_i.isna() | values_j.isna())
                    values_i = values_i[valid_mask]
                    values_j = values_j[valid_mask]
                    
                    if len(values_i) < 5:
                        corr = np.nan
                    elif method == 'pearson':
                        corr, _ = stats.pearsonr(values_i, values_j)
                    elif method == 'spearman':
                        corr, _ = stats.spearmanr(values_i, values_j)
                    else:
                        raise ValueError(f"未知的相关性方法: {method}")
                
                corr_matrix.loc[factor_names[i], factor_names[j]] = corr
                corr_matrix.loc[factor_names[j], factor_names[i]] = corr
        
        self.corr_matrix_ = corr_matrix
        return corr_matrix
    
    def compute_autocorrelation(
        self,
        factor_series: pd.Series,
        lag: int = 1,
    ) -> float:
        """
        计算因子自相关性
        
        Args:
            factor_series: 因子值Series
            lag: 滞后期数
        
        Returns:
            自相关系数
        """
        if len(factor_series) < lag + 5:
            return np.nan
        
        shifted = factor_series.shift(lag)
        
        common_index = factor_series.index.intersection(shifted.index)
        
        if len(common_index) < 5:
            return np.nan
        
        values = factor_series.loc[common_index]
        shifted_values = shifted.loc[common_index]
        
        valid_mask = ~(values.isna() | shifted_values.isna())
        values = values[valid_mask]
        shifted_values = shifted_values[valid_mask]
        
        if len(values) < 5:
            return np.nan
        
        corr, _ = stats.pearsonr(values, shifted_values)
        
        return corr
    
    def compute_autocorrelation_series(
        self,
        factor_series: pd.Series,
        max_lag: int = 20,
    ) -> pd.Series:
        """
        计算多期自相关性
        
        Args:
            factor_series: 因子值Series
            max_lag: 最大滞后期数
        
        Returns:
            各滞后期的自相关系数Series
        """
        autocorr_dict = {}
        
        for lag in range(1, max_lag + 1):
            autocorr_dict[lag] = self.compute_autocorrelation(factor_series, lag)
        
        return pd.Series(autocorr_dict)
    
    def compute_factor_return_correlation(
        self,
        factor_data: pd.Series,
        forward_returns: pd.Series,
        method: str = 'pearson',
    ) -> float:
        """
        计算因子与收益的相关性
        
        Args:
            factor_data: 因子值Series
            forward_returns: 未来收益Series
            method: 相关性计算方法
        
        Returns:
            相关系数
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
            corr, _ = stats.pearsonr(factor_values, return_values)
        elif method == 'spearman':
            corr, _ = stats.spearmanr(factor_values, return_values)
        else:
            raise ValueError(f"未知的相关性方法: {method}")
        
        return corr
    
    def find_highly_correlated_pairs(
        self,
        threshold: float = 0.7,
    ) -> List[tuple]:
        """
        找出高相关性的因子对
        
        Args:
            threshold: 相关性阈值
        
        Returns:
            高相关性因子对列表 [(factor1, factor2, correlation), ...]
        """
        if self.corr_matrix_ is None:
            raise ValueError("请先调用 compute_correlation_matrix 方法")
        
        pairs = []
        n_factors = len(self.corr_matrix_)
        
        for i in range(n_factors):
            for j in range(i+1, n_factors):
                corr = self.corr_matrix_.iloc[i, j]
                if abs(corr) >= threshold:
                    pairs.append((
                        self.corr_matrix_.index[i],
                        self.corr_matrix_.columns[j],
                        corr
                    ))
        
        return pairs
    
    def compute_cross_sectional_correlation(
        self,
        factor_data: pd.DataFrame,
        method: str = 'pearson',
    ) -> pd.Series:
        """
        计算横截面相关性（逐期计算相关性）
        
        Args:
            factor_data: 因子值DataFrame，index为日期，columns为股票代码
            method: 相关性计算方法
        
        Returns:
            各期的平均横截面相关性Series
        """
        corr_list = []
        
        for date in factor_data.index:
            row_data = factor_data.loc[date].dropna()
            
            if len(row_data) < 5:
                continue
            
            corr_matrix = row_data.to_frame().T.corr(method=method)
            
            n = len(corr_matrix)
            if n > 1:
                upper_triangle = corr_matrix.values[np.triu_indices(n, k=1)]
                mean_corr = np.nanmean(upper_triangle)
                corr_list.append({'date': date, 'mean_corr': mean_corr})
        
        return pd.DataFrame(corr_list).set_index('date')['mean_corr']


def compute_rolling_correlation(
    series1: pd.Series,
    series2: pd.Series,
    window: int = 20,
    method: str = 'pearson',
) -> pd.Series:
    """
    计算滚动相关性
    
    Args:
        series1: 序列1
        series2: 序列2
        window: 滚动窗口大小
        method: 相关性计算方法
    
    Returns:
        滚动相关性Series
    """
    common_index = series1.index.intersection(series2.index)
    
    if len(common_index) < window:
        return pd.Series(dtype=float)
    
    series1 = series1.loc[common_index]
    series2 = series2.loc[common_index]
    
    corr_list = []
    
    for i in range(window - 1, len(common_index)):
        window_series1 = series1.iloc[i-window+1:i+1]
        window_series2 = series2.iloc[i-window+1:i+1]
        
        valid_mask = ~(window_series1.isna() | window_series2.isna())
        window_series1 = window_series1[valid_mask]
        window_series2 = window_series2[valid_mask]
        
        if len(window_series1) < 5:
            corr = np.nan
        elif method == 'pearson':
            corr, _ = stats.pearsonr(window_series1, window_series2)
        elif method == 'spearman':
            corr, _ = stats.spearmanr(window_series1, window_series2)
        else:
            raise ValueError(f"未知的相关性方法: {method}")
        
        corr_list.append({
            'date': common_index[i],
            'correlation': corr
        })
    
    return pd.DataFrame(corr_list).set_index('date')['correlation']


def compute_partial_correlation(
    factor_data: pd.Series,
    forward_returns: pd.Series,
    control_factors: pd.DataFrame,
) -> float:
    """
    计算偏相关系数
    
    控制其他因子后，计算因子与收益的相关性。
    
    Args:
        factor_data: 因子值Series
        forward_returns: 未来收益Series
        control_factors: 控制因子DataFrame
    
    Returns:
        偏相关系数
    """
    from sklearn.linear_model import LinearRegression
    
    common_index = factor_data.index.intersection(
        forward_returns.index
    ).intersection(control_factors.index)
    
    if len(common_index) < 10:
        return np.nan
    
    factor_values = factor_data.loc[common_index].values
    return_values = forward_returns.loc[common_index].values
    control_values = control_factors.loc[common_index].values
    
    valid_mask = ~(np.isnan(factor_values) | np.isnan(return_values) | 
                   np.isnan(control_values).any(axis=1))
    
    factor_values = factor_values[valid_mask]
    return_values = return_values[valid_mask]
    control_values = control_values[valid_mask]
    
    if len(factor_values) < 10:
        return np.nan
    
    model1 = LinearRegression()
    model1.fit(control_values, factor_values)
    residual1 = factor_values - model1.predict(control_values)
    
    model2 = LinearRegression()
    model2.fit(control_values, return_values)
    residual2 = return_values - model2.predict(control_values)
    
    corr, _ = stats.pearsonr(residual1, residual2)
    
    return corr


def plot_correlation_matrix(
    corr_matrix: pd.DataFrame,
    figsize: tuple = (10, 8),
    cmap: str = 'RdYlGn',
) -> None:
    """
    绘制相关性矩阵热力图
    
    Args:
        corr_matrix: 相关性矩阵DataFrame
        figsize: 图表大小
        cmap: 颜色映射
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    fig, ax = plt.subplots(figsize=figsize)
    
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        fmt='.2f',
        cmap=cmap,
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
        ax=ax
    )
    
    ax.set_title('Factor Correlation Matrix', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.show()


def plot_autocorrelation(
    autocorr_series: pd.Series,
    figsize: tuple = (10, 6),
) -> None:
    """
    绘制自相关图
    
    Args:
        autocorr_series: 自相关系数Series
        figsize: 图表大小
    """
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=figsize)
    
    ax.bar(autocorr_series.index, autocorr_series.values, alpha=0.7)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.axhline(y=0.2, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axhline(y=-0.2, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
    
    ax.set_title('Factor Autocorrelation', fontsize=14, fontweight='bold')
    ax.set_xlabel('Lag')
    ax.set_ylabel('Autocorrelation')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


def batch_compute_correlation(
    factor_data_dict: Dict[str, pd.Series],
    method: str = 'pearson',
) -> Dict[str, float]:
    """
    批量计算因子间的平均相关性
    
    Args:
        factor_data_dict: 因子数据字典
        method: 相关性计算方法
    
    Returns:
        各因子的平均相关性字典
    """
    analyzer = CorrelationAnalyzer()
    corr_matrix = analyzer.compute_correlation_matrix(factor_data_dict, method)
    
    mean_corr_dict = {}
    
    for factor_name in corr_matrix.index:
        other_corrs = corr_matrix.loc[factor_name].drop(factor_name)
        mean_corr_dict[factor_name] = other_corrs.abs().mean()
    
    return mean_corr_dict
