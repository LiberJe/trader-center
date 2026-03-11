"""
因子中性化

提供因子数据的行业、市场和规模中性化处理功能。
"""

from typing import Optional, Dict, List
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


class IndustryNeutralizer:
    """
    行业中性化器
    
    消除因子在不同行业间的差异，使因子在行业内均值为0。
    
    Example:
        neutralizer = IndustryNeutralizer()
        neutralized = neutralizer.transform(factor_data, industry_mapping)
    """
    
    def __init__(self):
        self.industry_means_: Optional[Dict[str, float]] = None
    
    def fit(
        self,
        data: pd.Series,
        industry_mapping: pd.Series,
    ) -> 'IndustryNeutralizer':
        """
        拟合数据，计算各行业的因子均值
        
        Args:
            data: 因子值Series，index为股票代码
            industry_mapping: 行业映射Series，index为股票代码，value为行业代码
        
        Returns:
            self
        """
        common_index = data.index.intersection(industry_mapping.index)
        
        self.industry_means_ = {}
        for industry in industry_mapping.loc[common_index].unique():
            industry_stocks = industry_mapping[industry_mapping == industry].index
            industry_stocks = industry_stocks.intersection(data.index)
            if len(industry_stocks) > 0:
                self.industry_means_[industry] = data.loc[industry_stocks].mean()
        
        return self
    
    def transform(
        self,
        data: pd.Series,
        industry_mapping: pd.Series,
    ) -> pd.Series:
        """
        转换数据，进行行业中性化
        
        Args:
            data: 因子值Series，index为股票代码
            industry_mapping: 行业映射Series，index为股票代码，value为行业代码
        
        Returns:
            行业中性化后的因子值Series
        """
        if self.industry_means_ is None:
            raise ValueError("请先调用 fit 方法")
        
        result = data.copy()
        
        common_index = data.index.intersection(industry_mapping.index)
        
        for stock in common_index:
            industry = industry_mapping.loc[stock]
            if industry in self.industry_means_:
                result.loc[stock] = data.loc[stock] - self.industry_means_[industry]
        
        return result
    
    def fit_transform(
        self,
        data: pd.Series,
        industry_mapping: pd.Series,
    ) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series，index为股票代码
            industry_mapping: 行业映射Series，index为股票代码，value为行业代码
        
        Returns:
            行业中性化后的因子值Series
        """
        return self.fit(data, industry_mapping).transform(data, industry_mapping)


class MarketNeutralizer:
    """
    市场中性化器
    
    消除因子与市场收益的相关性。
    
    Example:
        neutralizer = MarketNeutralizer()
        neutralized = neutralizer.transform(factor_data, market_returns)
    """
    
    def __init__(self):
        self.beta_: Optional[float] = None
        self.alpha_: Optional[float] = None
    
    def fit(
        self,
        data: pd.Series,
        market_returns: pd.Series,
    ) -> 'MarketNeutralizer':
        """
        拟合数据，计算因子对市场的beta
        
        Args:
            data: 因子值Series
            market_returns: 市场收益Series
        
        Returns:
            self
        """
        common_index = data.index.intersection(market_returns.index)
        
        if len(common_index) == 0:
            self.beta_ = 0
            self.alpha_ = 0
            return self
        
        X = market_returns.loc[common_index].values.reshape(-1, 1)
        y = data.loc[common_index].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        self.beta_ = model.coef_[0]
        self.alpha_ = model.intercept_
        
        return self
    
    def transform(
        self,
        data: pd.Series,
        market_returns: pd.Series,
    ) -> pd.Series:
        """
        转换数据，进行市场中性化
        
        Args:
            data: 因子值Series
            market_returns: 市场收益Series
        
        Returns:
            市场中性化后的因子值Series
        """
        if self.beta_ is None:
            raise ValueError("请先调用 fit 方法")
        
        common_index = data.index.intersection(market_returns.index)
        
        result = data.copy()
        result.loc[common_index] = (
            data.loc[common_index] - 
            self.alpha_ - 
            self.beta_ * market_returns.loc[common_index]
        )
        
        return result
    
    def fit_transform(
        self,
        data: pd.Series,
        market_returns: pd.Series,
    ) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series
            market_returns: 市场收益Series
        
        Returns:
            市场中性化后的因子值Series
        """
        return self.fit(data, market_returns).transform(data, market_returns)


class SizeNeutralizer:
    """
    规模中性化器
    
    消除因子与市值的相关性。
    
    Example:
        neutralizer = SizeNeutralizer()
        neutralized = neutralizer.transform(factor_data, market_cap)
    """
    
    def __init__(self):
        self.beta_: Optional[float] = None
        self.alpha_: Optional[float] = None
    
    def fit(
        self,
        data: pd.Series,
        market_cap: pd.Series,
    ) -> 'SizeNeutralizer':
        """
        拟合数据，计算因子对市值（对数）的beta
        
        Args:
            data: 因子值Series，index为股票代码
            market_cap: 市值Series，index为股票代码
        
        Returns:
            self
        """
        common_index = data.index.intersection(market_cap.index)
        
        if len(common_index) == 0:
            self.beta_ = 0
            self.alpha_ = 0
            return self
        
        log_market_cap = np.log(market_cap.loc[common_index])
        
        X = log_market_cap.values.reshape(-1, 1)
        y = data.loc[common_index].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        self.beta_ = model.coef_[0]
        self.alpha_ = model.intercept_
        
        return self
    
    def transform(
        self,
        data: pd.Series,
        market_cap: pd.Series,
    ) -> pd.Series:
        """
        转换数据，进行规模中性化
        
        Args:
            data: 因子值Series，index为股票代码
            market_cap: 市值Series，index为股票代码
        
        Returns:
            规模中性化后的因子值Series
        """
        if self.beta_ is None:
            raise ValueError("请先调用 fit 方法")
        
        common_index = data.index.intersection(market_cap.index)
        
        result = data.copy()
        log_market_cap = np.log(market_cap.loc[common_index])
        result.loc[common_index] = (
            data.loc[common_index] - 
            self.alpha_ - 
            self.beta_ * log_market_cap
        )
        
        return result
    
    def fit_transform(
        self,
        data: pd.Series,
        market_cap: pd.Series,
    ) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series，index为股票代码
            market_cap: 市值Series，index为股票代码
        
        Returns:
            规模中性化后的因子值Series
        """
        return self.fit(data, market_cap).transform(data, market_cap)


class MultiFactorNeutralizer:
    """
    多因子中性化器
    
    同时对多个风险因子进行中性化。
    
    Example:
        neutralizer = MultiFactorNeutralizer()
        neutralized = neutralizer.transform(factor_data, risk_factors)
    """
    
    def __init__(self):
        self.model_: Optional[LinearRegression] = None
        self.risk_factor_names_: Optional[List[str]] = None
    
    def fit(
        self,
        data: pd.Series,
        risk_factors: pd.DataFrame,
    ) -> 'MultiFactorNeutralizer':
        """
        拟合数据，计算因子对各风险因子的暴露
        
        Args:
            data: 因子值Series，index为股票代码
            risk_factors: 风险因子DataFrame，index为股票代码，columns为风险因子名称
        
        Returns:
            self
        """
        common_index = data.index.intersection(risk_factors.index)
        
        if len(common_index) == 0:
            self.model_ = None
            return self
        
        X = risk_factors.loc[common_index].values
        y = data.loc[common_index].values
        
        self.model_ = LinearRegression()
        self.model_.fit(X, y)
        
        self.risk_factor_names_ = list(risk_factors.columns)
        
        return self
    
    def transform(
        self,
        data: pd.Series,
        risk_factors: pd.DataFrame,
    ) -> pd.Series:
        """
        转换数据，进行多因子中性化
        
        Args:
            data: 因子值Series，index为股票代码
            risk_factors: 风险因子DataFrame，index为股票代码，columns为风险因子名称
        
        Returns:
            中性化后的因子值Series
        """
        if self.model_ is None:
            raise ValueError("请先调用 fit 方法")
        
        common_index = data.index.intersection(risk_factors.index)
        
        result = data.copy()
        X = risk_factors.loc[common_index].values
        predicted = self.model_.predict(X)
        result.loc[common_index] = data.loc[common_index] - predicted
        
        return result
    
    def fit_transform(
        self,
        data: pd.Series,
        risk_factors: pd.DataFrame,
    ) -> pd.Series:
        """
        拟合并转换数据
        
        Args:
            data: 因子值Series，index为股票代码
            risk_factors: 风险因子DataFrame，index为股票代码，columns为风险因子名称
        
        Returns:
            中性化后的因子值Series
        """
        return self.fit(data, risk_factors).transform(data, risk_factors)


def neutralize_cross_sectional(
    factor_data: pd.DataFrame,
    neutralize_type: str = 'industry',
    industry_mapping: Optional[pd.DataFrame] = None,
    market_cap: Optional[pd.DataFrame] = None,
    market_returns: Optional[pd.Series] = None,
    risk_factors: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    横截面中性化
    
    对每一期的因子值进行中性化处理。
    
    Args:
        factor_data: 因子值DataFrame，index为日期，columns为股票代码
        neutralize_type: 中性化类型 ('industry', 'market', 'size', 'multi')
        industry_mapping: 行业映射DataFrame，index为日期，columns为股票代码
        market_cap: 市值DataFrame，index为日期，columns为股票代码
        market_returns: 市场收益Series，index为日期
        risk_factors: 风险因子字典，{日期: DataFrame}
    
    Returns:
        中性化后的因子值DataFrame
    
    Example:
        neutralized = neutralize_cross_sectional(
            factor_df, 
            neutralize_type='industry',
            industry_mapping=industry_df
        )
    """
    result = pd.DataFrame(index=factor_data.index, columns=factor_data.columns)
    
    for date in factor_data.index:
        row_data = factor_data.loc[date].dropna()
        
        if len(row_data) == 0:
            continue
        
        if neutralize_type == 'industry':
            if industry_mapping is None:
                raise ValueError("行业中性化需要提供 industry_mapping")
            
            industry_series = industry_mapping.loc[date]
            neutralizer = IndustryNeutralizer()
            neutralized = neutralizer.fit_transform(row_data, industry_series)
            
        elif neutralize_type == 'market':
            if market_returns is None:
                raise ValueError("市场中性化需要提供 market_returns")
            
            neutralizer = MarketNeutralizer()
            neutralized = neutralizer.fit_transform(row_data, market_returns)
            
        elif neutralize_type == 'size':
            if market_cap is None:
                raise ValueError("规模中性化需要提供 market_cap")
            
            cap_series = market_cap.loc[date]
            neutralizer = SizeNeutralizer()
            neutralized = neutralizer.fit_transform(row_data, cap_series)
            
        elif neutralize_type == 'multi':
            if risk_factors is None:
                raise ValueError("多因子中性化需要提供 risk_factors")
            
            risk_df = risk_factors.get(date)
            if risk_df is None:
                neutralized = row_data
            else:
                neutralizer = MultiFactorNeutralizer()
                neutralized = neutralizer.fit_transform(row_data, risk_df)
        else:
            raise ValueError(f"未知的中性化类型: {neutralize_type}")
        
        result.loc[date, neutralized.index] = neutralized
    
    return result


def orthogonalize(
    factor_data: pd.Series,
    other_factors: pd.DataFrame,
) -> pd.Series:
    """
    正交化
    
    消除因子与其他因子的相关性。
    
    Args:
        factor_data: 因子值Series，index为股票代码
        other_factors: 其他因子DataFrame，index为股票代码，columns为因子名称
    
    Returns:
        正交化后的因子值Series
    
    Example:
        orthogonal = orthogonalize(factor_series, other_factors_df)
    """
    common_index = factor_data.index.intersection(other_factors.index)
    
    if len(common_index) == 0:
        return factor_data
    
    X = other_factors.loc[common_index].values
    y = factor_data.loc[common_index].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    predicted = model.predict(X)
    
    result = factor_data.copy()
    result.loc[common_index] = y - predicted
    
    return result
