"""
因子标准化

提供因子数据的标准化处理功能。
"""

from typing import Optional, Union
import pandas as pd
import numpy as np


class ZScoreStandardizer:
    """
    Z-score标准化器
    
    将因子值转换为标准正态分布（均值为0，标准差为1）。
    
    Example:
        standardizer = ZScoreStandardizer()
        standardized = standardizer.transform(factor_data)
    """
    
    def __init__(self):
        self.mean_: Optional[float] = None
        self.std_: Optional[float] = None
    
    def fit(self, data: pd.Series) -> 'ZScoreStandardizer':
        """
        拟合数据，计算均值和标准差
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        self.mean_ = data.mean()
        self.std_ = data.std()
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        if self.mean_ is None or self.std_ is None:
            raise ValueError("请先调用 fit 方法")
        
        if self.std_ == 0:
            return pd.Series(0, index=data.index)
        
        return (data - self.mean_) / self.std_
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        return self.fit(data).transform(data)


class MinMaxStandardizer:
    """
    Min-Max标准化器
    
    将因子值缩放到指定范围（默认[0, 1]）。
    
    Params:
        feature_range: 目标范围，默认(0, 1)
    
    Example:
        standardizer = MinMaxStandardizer(feature_range=(0, 1))
        standardized = standardizer.transform(factor_data)
    """
    
    def __init__(self, feature_range: tuple = (0, 1)):
        self.feature_range = feature_range
        self.min_: Optional[float] = None
        self.max_: Optional[float] = None
    
    def fit(self, data: pd.Series) -> 'MinMaxStandardizer':
        """
        拟合数据，计算最小值和最大值
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        self.min_ = data.min()
        self.max_ = data.max()
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        if self.min_ is None or self.max_ is None:
            raise ValueError("请先调用 fit 方法")
        
        if self.max_ == self.min_:
            return pd.Series(
                (self.feature_range[0] + self.feature_range[1]) / 2,
                index=data.index
            )
        
        scale = self.feature_range[1] - self.feature_range[0]
        return scale * (data - self.min_) / (self.max_ - self.min_) + self.feature_range[0]
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        return self.fit(data).transform(data)


class RankStandardizer:
    """
    排名标准化器
    
    将因子值转换为排名百分比（0到1之间）。
    
    Example:
        standardizer = RankStandardizer()
        standardized = standardizer.transform(factor_data)
    """
    
    def __init__(self, method: str = 'average'):
        """
        初始化排名标准化器
        
        Args:
            method: 排名方法 ('average', 'min', 'max', 'dense', 'ordinal')
        """
        self.method = method
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            排名标准化后的因子值Series (0-1)
        """
        ranks = data.rank(method=self.method, pct=True)
        return ranks


class RobustStandardizer:
    """
    鲁棒标准化器
    
    使用中位数和四分位距进行标准化，对异常值不敏感。
    
    Example:
        standardizer = RobustStandardizer()
        standardized = standardizer.transform(factor_data)
    """
    
    def __init__(self):
        self.median_: Optional[float] = None
        self.iqr_: Optional[float] = None
    
    def fit(self, data: pd.Series) -> 'RobustStandardizer':
        """
        拟合数据，计算中位数和四分位距
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        self.median_ = data.median()
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        self.iqr_ = q3 - q1
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        if self.median_ is None or self.iqr_ is None:
            raise ValueError("请先调用 fit 方法")
        
        if self.iqr_ == 0:
            return pd.Series(0, index=data.index)
        
        return (data - self.median_) / self.iqr_
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        return self.fit(data).transform(data)


class DecimalScaleStandardizer:
    """
    小数定标标准化器
    
    通过移动小数点位置进行标准化。
    
    Example:
        standardizer = DecimalScaleStandardizer()
        standardized = standardizer.transform(factor_data)
    """
    
    def __init__(self):
        self.scale_: Optional[int] = None
    
    def fit(self, data: pd.Series) -> 'DecimalScaleStandardizer':
        """
        拟合数据，计算缩放因子
        
        Args:
            data: 因子值Series
        
        Returns:
            self
        """
        max_abs = abs(data).max()
        if max_abs == 0:
            self.scale_ = 0
        else:
            self.scale_ = int(np.ceil(np.log10(max_abs + 1)))
        return self
    
    def transform(self, data: pd.Series) -> pd.Series:
        """
        转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        if self.scale_ is None:
            raise ValueError("请先调用 fit 方法")
        
        return data / (10 ** self.scale_)
    
    def fit_transform(self, data: pd.Series) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
        
        Returns:
            标准化后的因子值Series
        """
        return self.fit(data).transform(data)


def standardize_cross_sectional(
    factor_data: pd.DataFrame,
    method: str = 'zscore',
    **kwargs,
) -> pd.DataFrame:
    """
    横截面标准化
    
    对每一期的因子值进行标准化处理。
    
    Args:
        factor_data: 因子值DataFrame，index为日期，columns为股票代码
        method: 标准化方法 ('zscore', 'minmax', 'rank', 'robust')
        **kwargs: 传递给标准化器的参数
    
    Returns:
        标准化后的因子值DataFrame
    
    Example:
        standardized = standardize_cross_sectional(factor_df, method='zscore')
    """
    if method == 'zscore':
        standardizer = ZScoreStandardizer()
    elif method == 'minmax':
        standardizer = MinMaxStandardizer(**kwargs)
    elif method == 'rank':
        standardizer = RankStandardizer(**kwargs)
    elif method == 'robust':
        standardizer = RobustStandardizer()
    else:
        raise ValueError(f"未知的标准化方法: {method}")
    
    result = pd.DataFrame(index=factor_data.index, columns=factor_data.columns)
    
    for date in factor_data.index:
        row_data = factor_data.loc[date].dropna()
        
        if len(row_data) == 0:
            continue
        
        if method in ['zscore', 'minmax', 'robust']:
            standardized = standardizer.fit_transform(row_data)
        else:
            standardized = standardizer.transform(row_data)
        
        result.loc[date, standardized.index] = standardized
    
    return result


def standardize_time_series(
    factor_data: pd.DataFrame,
    method: str = 'zscore',
    window: Optional[int] = None,
    **kwargs,
) -> pd.DataFrame:
    """
    时间序列标准化
    
    对每个股票的因子值进行时间序列标准化。
    
    Args:
        factor_data: 因子值DataFrame，index为日期，columns为股票代码
        method: 标准化方法 ('zscore', 'minmax', 'rank', 'robust')
        window: 滚动窗口大小（None表示使用全部历史数据）
        **kwargs: 传递给标准化器的参数
    
    Returns:
        标准化后的因子值DataFrame
    
    Example:
        standardized = standardize_time_series(factor_df, method='zscore', window=20)
    """
    result = pd.DataFrame(index=factor_data.index, columns=factor_data.columns)
    
    for symbol in factor_data.columns:
        series = factor_data[symbol].dropna()
        
        if len(series) == 0:
            continue
        
        if window is None:
            if method == 'zscore':
                standardizer = ZScoreStandardizer()
            elif method == 'minmax':
                standardizer = MinMaxStandardizer(**kwargs)
            elif method == 'robust':
                standardizer = RobustStandardizer()
            else:
                raise ValueError(f"未知的标准化方法: {method}")
            
            standardized = standardizer.fit_transform(series)
            result.loc[standardized.index, symbol] = standardized
        else:
            for i in range(window - 1, len(series)):
                window_data = series.iloc[i-window+1:i+1]
                
                if method == 'zscore':
                    standardizer = ZScoreStandardizer()
                elif method == 'minmax':
                    standardizer = MinMaxStandardizer(**kwargs)
                elif method == 'robust':
                    standardizer = RobustStandardizer()
                else:
                    raise ValueError(f"未知的标准化方法: {method}")
                
                standardized = standardizer.fit_transform(window_data)
                result.loc[series.index[i], symbol] = standardized.iloc[-1]
    
    return result
