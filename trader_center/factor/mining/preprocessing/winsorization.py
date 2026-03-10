"""
因子去极值

提供因子数据的去极值处理功能。
"""

from typing import Optional, Union
import pandas as pd
import numpy as np


class MADWinsorizer:
    """
    中位数绝对偏差去极值器
    
    使用MAD（Median Absolute Deviation）方法识别和处理极值。
    
    Params:
        threshold: MAD倍数阈值，默认3.0
    
    Example:
        winsorizer = MADWinsorizer(threshold=3.0)
        winsorized = winsorizer.transform(factor_data)
    """
    
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold
        self.median_: Optional[float] = None
        self.mad_: Optional[float] = None
        self.lower_bound_: Optional[float] = None
        self.upper_bound_: Optional[float] = None
    
    def fit(self, data: pd.Series) -> 'MADWinsorizer':
        """
        拟合数据，计算MAD和边界
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        self.median_ = data.median()
        
        self.mad_ = np.median(np.abs(data - self.median_))
        
        self.lower_bound_ = self.median_ - self.threshold * self.mad_
        self.upper_bound_ = self.median_ + self.threshold * self.mad_
        
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据，将极值截断到边界
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        if self.lower_bound_ is None or self.upper_bound_ is None:
            raise ValueError("请先调用 fit 方法")
        
        return data.clip(lower=self.lower_bound_, upper=self.upper_bound_)
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        return self.fit(data).transform(data)


class PercentileWinsorizer:
    """
    分位数去极值器
    
    将超出指定分位数范围的值截断到边界。
    
    Params:
        lower_percentile: 下分位数，默认2.5
        upper_percentile: 上分位数，默认97.5
    
    Example:
        winsorizer = PercentileWinsorizer(lower_percentile=2.5, upper_percentile=97.5)
        winsorized = winsorizer.transform(factor_data)
    """
    
    def __init__(
        self,
        lower_percentile: float = 2.5,
        upper_percentile: float = 97.5,
    ):
        self.lower_percentile = lower_percentile
        self.upper_percentile = upper_percentile
        self.lower_bound_: Optional[float] = None
        self.upper_bound_: Optional[float] = None
    
    def fit(self, data: pd.Series) -> 'PercentileWinsorizer':
        """
        拟合数据，计算分位数边界
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        self.lower_bound_ = data.quantile(self.lower_percentile / 100)
        self.upper_bound_ = data.quantile(self.upper_percentile / 100)
        
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据，将极值截断到边界
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        if self.lower_bound_ is None or self.upper_bound_ is None:
            raise ValueError("请先调用 fit 方法")
        
        return data.clip(lower=self.lower_bound_, upper=self.upper_bound_)
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        return self.fit(data).transform(data)


class SigmaWinsorizer:
    """
    标准差去极值器
    
    将超出均值±N倍标准差范围的值截断到边界。
    
    Params:
        n_sigma: 标准差倍数，默认3.0
    
    Example:
        winsorizer = SigmaWinsorizer(n_sigma=3.0)
        winsorized = winsorizer.transform(factor_data)
    """
    
    def __init__(self, n_sigma: float = 3.0):
        self.n_sigma = n_sigma
        self.mean_: Optional[float] = None
        self.std_: Optional[float] = None
        self.lower_bound_: Optional[float] = None
        self.upper_bound_: Optional[float] = None
    
    def fit(self, data: pd.Series) -> 'SigmaWinsorizer':
        """
        拟合数据，计算均值、标准差和边界
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        self.mean_ = data.mean()
        self.std_ = data.std()
        
        self.lower_bound_ = self.mean_ - self.n_sigma * self.std_
        self.upper_bound_ = self.mean_ + self.n_sigma * self.std_
        
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据，将极值截断到边界
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        if self.lower_bound_ is None or self.upper_bound_ is None:
            raise ValueError("请先调用 fit 方法")
        
        return data.clip(lower=self.lower_bound_, upper=self.upper_bound_)
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        return self.fit(data).transform(data)


class IQRWinsorizer:
    """
    四分位距去极值器
    
    将超出Q1-N*IQR到Q3+N*IQR范围的值截断到边界。
    
    Params:
        n_iqr: IQR倍数，默认1.5
    
    Example:
        winsorizer = IQRWinsorizer(n_iqr=1.5)
        winsorized = winsorizer.transform(factor_data)
    """
    
    def __init__(self, n_iqr: float = 1.5):
        self.n_iqr = n_iqr
        self.q1_: Optional[float] = None
        self.q3_: Optional[float] = None
        self.iqr_: Optional[float] = None
        self.lower_bound_: Optional[float] = None
        self.upper_bound_: Optional[float] = None
    
    def fit(self, data: pd.Series) -> 'IQRWinsorizer':
        """
        拟合数据，计算四分位数和边界
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        self.q1_ = data.quantile(0.25)
        self.q3_ = data.quantile(0.75)
        self.iqr_ = self.q3_ - self.q1_
        
        self.lower_bound_ = self.q1_ - self.n_iqr * self.iqr_
        self.upper_bound_ = self.q3_ + self.n_iqr * self.iqr_
        
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据，将极值截断到边界
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        if self.lower_bound_ is None or self.upper_bound_ is None:
            raise ValueError("请先调用 fit 方法")
        
        return data.clip(lower=self.lower_bound_, upper=self.upper_bound_)
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            去极值后的因子值Series
        """
        return self.fit(data).transform(data)


def winsorize_cross_sectional(
    factor_data: pd.DataFrame,
    method: str = 'mad',
    **kwargs,
) -> pd.DataFrame:
    """
    横截面去极值
    
    对每一期的因子值进行去极值处理。
    
    Args:
        factor_data: 因子值DataFrame，index为日期，columns为股票代码
        method: 去极值方法 ('mad', 'percentile', 'sigma', 'iqr')
        **kwargs: 传递给去极值器的参数
    
    Returns:
        去极值后的因子值DataFrame
    
    Example:
        winsorized = winsorize_cross_sectional(factor_df, method='mad', threshold=3.0)
    """
    if method == 'mad':
        winsorizer = MADWinsorizer(**kwargs)
    elif method == 'percentile':
        winsorizer = PercentileWinsorizer(**kwargs)
    elif method == 'sigma':
        winsorizer = SigmaWinsorizer(**kwargs)
    elif method == 'iqr':
        winsorizer = IQRWinsorizer(**kwargs)
    else:
        raise ValueError(f"未知的去极值方法: {method}")
    
    result = pd.DataFrame(index=factor_data.index, columns=factor_data.columns)
    
    for date in factor_data.index:
        row_data = factor_data.loc[date].dropna()
        
        if len(row_data) == 0:
            continue
        
        winsorized = winsorizer.fit_transform(row_data)
        result.loc[date, winsorized.index] = winsorized
    
    return result


def winsorize_time_series(
    factor_data: pd.DataFrame,
    method: str = 'mad',
    window: Optional[int] = None,
    **kwargs,
) -> pd.DataFrame:
    """
    时间序列去极值
    
    对每个股票的因子值进行时间序列去极值。
    
    Args:
        factor_data: 因子值DataFrame，index为日期，columns为股票代码
        method: 去极值方法 ('mad', 'percentile', 'sigma', 'iqr')
        window: 滚动窗口大小（None表示使用全部历史数据）
        **kwargs: 传递给去极值器的参数
    
    Returns:
        去极值后的因子值DataFrame
    
    Example:
        winsorized = winsorize_time_series(factor_df, method='mad', window=20)
    """
    result = pd.DataFrame(index=factor_data.index, columns=factor_data.columns)
    
    for symbol in factor_data.columns:
        series = factor_data[symbol].dropna()
        
        if len(series) == 0:
            continue
        
        if window is None:
            if method == 'mad':
                winsorizer = MADWinsorizer(**kwargs)
            elif method == 'percentile':
                winsorizer = PercentileWinsorizer(**kwargs)
            elif method == 'sigma':
                winsorizer = SigmaWinsorizer(**kwargs)
            elif method == 'iqr':
                winsorizer = IQRWinsorizer(**kwargs)
            else:
                raise ValueError(f"未知的去极值方法: {method}")
            
            winsorized = winsorizer.fit_transform(series)
            result.loc[winsorized.index, symbol] = winsorized
        else:
            for i in range(window - 1, len(series)):
                window_data = series.iloc[i-window+1:i+1]
                
                if method == 'mad':
                    winsorizer = MADWinsorizer(**kwargs)
                elif method == 'percentile':
                    winsorizer = PercentileWinsorizer(**kwargs)
                elif method == 'sigma':
                    winsorizer = SigmaWinsorizer(**kwargs)
                elif method == 'iqr':
                    winsorizer = IQRWinsorizer(**kwargs)
                else:
                    raise ValueError(f"未知的去极值方法: {method}")
                
                winsorized = winsorizer.fit_transform(window_data)
                result.loc[series.index[i], symbol] = winsorized.iloc[-1]
    
    return result


def identify_outliers(
    data: pd.Series,
    method: str = 'mad',
    **kwargs,
) -> pd.Series:
    """
    识别异常值
    
    返回一个布尔Series，标识哪些值是异常值。
    
    Args:
        data: 因子值Series
        method: 去极值方法 ('mad', 'percentile', 'sigma', 'iqr')
        **kwargs: 传递给去极值器的参数
    
    Returns:
        布尔Series，True表示异常值
    
    Example:
        outliers = identify_outliers(factor_series, method='mad', threshold=3.0)
    """
    if method == 'mad':
        winsorizer = MADWinsorizer(**kwargs)
    elif method == 'percentile':
        winsorizer = PercentileWinsorizer(**kwargs)
    elif method == 'sigma':
        winsorizer = SigmaWinsorizer(**kwargs)
    elif method == 'iqr':
        winsorizer = IQRWinsorizer(**kwargs)
    else:
        raise ValueError(f"未知的去极值方法: {method}")
    
    winsorizer.fit(data)
    
    is_outlier = (data < winsorizer.lower_bound_) | (data > winsorizer.upper_bound_)
    
    return is_outlier
