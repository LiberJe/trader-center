"""
数据转换工具

将框架数据转换为alphalens所需的格式。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

from ..gp.expression import FactorExpression, evaluate_expression

logger = logging.getLogger(__name__)


class DataConverter:
    """
    数据格式转换器
    
    将因子挖掘结果转换为alphalens所需的格式。
    
    Example:
        converter = DataConverter()
        
        # 转换因子表达式
        factor_panel = converter.factor_expression_to_panel(
            expressions, data_dict
        )
        
        # 提取价格数据
        prices = converter.get_pricing_data(data_dict)
    """
    
    @staticmethod
    def factor_expression_to_panel(
        expressions: List[FactorExpression],
        data_dict: Dict[str, pd.DataFrame],
        window_sizes: Optional[List[int]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        将因子表达式转换为面板数据
        
        Args:
            expressions: 因子表达式列表
            data_dict: 股票数据字典 {symbol: DataFrame}
            window_sizes: 窗口大小列表
        
        Returns:
            因子面板数据字典 {factor_name: DataFrame}
        """
        factor_panel = {}
        
        for expr in expressions:
            try:
                factor_values = {}
                for symbol, data in data_dict.items():
                    values = evaluate_expression(
                        expr.expression_str, 
                        data,
                        window_sizes
                    )
                    factor_values[symbol] = values
                
                factor_df = pd.DataFrame(factor_values)
                factor_df.index.name = 'date'
                factor_panel[expr.name] = factor_df
                
                logger.debug(f"Converted factor: {expr.name}")
                
            except Exception as e:
                logger.warning(f"Failed to convert factor {expr.name}: {e}")
                continue
        
        logger.info(f"Converted {len(factor_panel)} factors to panel format")
        return factor_panel
    
    @staticmethod
    def get_pricing_data(
        data_dict: Dict[str, pd.DataFrame],
        price_col: str = 'close',
    ) -> pd.DataFrame:
        """
        从数据字典提取价格数据
        
        Args:
            data_dict: 股票数据字典 {symbol: DataFrame}
            price_col: 价格列名
        
        Returns:
            价格DataFrame，index为日期，columns为股票代码
        """
        prices = {}
        
        for symbol, data in data_dict.items():
            if price_col in data.columns:
                prices[symbol] = data[price_col]
        
        prices_df = pd.DataFrame(prices)
        prices_df.index.name = 'date'
        
        logger.info(f"Extracted pricing data for {len(prices_df.columns)} symbols")
        return prices_df
    
    @staticmethod
    def mining_result_to_alphalens_format(
        result: Any,
        data_dict: Dict[str, pd.DataFrame],
        window_sizes: Optional[List[int]] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        将挖掘结果转换为alphalens格式
        
        Args:
            result: MiningResult实例
            data_dict: 股票数据字典
            window_sizes: 窗口大小列表
        
        Returns:
            (因子值DataFrame, 价格DataFrame)
        """
        if hasattr(result, 'selected_factors') and result.selected_factors:
            expressions = result.selected_factors
        elif hasattr(result, 'generated_factors') and result.generated_factors:
            expressions = result.generated_factors
        else:
            raise ValueError("No factors found in mining result")
        
        factor_panel = DataConverter.factor_expression_to_panel(
            expressions, data_dict, window_sizes
        )
        
        if not factor_panel:
            raise ValueError("Failed to convert any factors")
        
        first_factor_name = list(factor_panel.keys())[0]
        factor_values = factor_panel[first_factor_name]
        
        prices = DataConverter.get_pricing_data(data_dict)
        
        common_dates = factor_values.index.intersection(prices.index)
        common_symbols = factor_values.columns.intersection(prices.columns)
        
        factor_values = factor_values.loc[common_dates, common_symbols]
        prices = prices.loc[common_dates, common_symbols]
        
        logger.info(
            f"Prepared alphalens data: "
            f"factor shape={factor_values.shape}, "
            f"prices shape={prices.shape}"
        )
        
        return factor_values, prices
    
    @staticmethod
    def stack_factor_values(
        factor_values: pd.DataFrame,
    ) -> pd.Series:
        """
        将因子值DataFrame转换为MultiIndex Series
        
        Args:
            factor_values: 因子值DataFrame，index为日期，columns为股票代码
        
        Returns:
            MultiIndex Series (date, asset) -> factor_value
        """
        stacked = factor_values.stack()
        stacked.index.names = ['date', 'asset']
        stacked.name = 'factor'
        return stacked
    
    @staticmethod
    def unstack_factor_values(
        factor_series: pd.Series,
    ) -> pd.DataFrame:
        """
        将MultiIndex Series转换为DataFrame
        
        Args:
            factor_series: MultiIndex Series
        
        Returns:
            因子值DataFrame
        """
        return factor_series.unstack()
    
    @staticmethod
    def align_data(
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
        method: str = 'inner',
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        对齐因子值和价格数据
        
        Args:
            factor_values: 因子值DataFrame
            prices: 价格DataFrame
            method: 对齐方法 ('inner', 'outer', 'left', 'right')
        
        Returns:
            (对齐后的因子值, 对齐后的价格)
        """
        common_dates = factor_values.index.intersection(prices.index)
        common_symbols = factor_values.columns.intersection(prices.columns)
        
        if method == 'inner':
            factor_aligned = factor_values.loc[common_dates, common_symbols]
            prices_aligned = prices.loc[common_dates, common_symbols]
        elif method == 'outer':
            all_dates = factor_values.index.union(prices.index)
            all_symbols = factor_values.columns.union(prices.columns)
            factor_aligned = factor_values.reindex(index=all_dates, columns=all_symbols)
            prices_aligned = prices.reindex(index=all_dates, columns=all_symbols)
        elif method == 'left':
            factor_aligned = factor_values
            prices_aligned = prices.reindex(
                index=factor_values.index, 
                columns=factor_values.columns
            )
        elif method == 'right':
            factor_aligned = factor_values.reindex(
                index=prices.index, 
                columns=prices.columns
            )
            prices_aligned = prices
        else:
            raise ValueError(f"Unknown alignment method: {method}")
        
        return factor_aligned, prices_aligned
    
    @staticmethod
    def clean_factor_data(
        factor_values: pd.DataFrame,
        dropna: bool = True,
        winsorize: bool = False,
        winsorize_limit: float = 0.025,
        standardize: bool = False,
    ) -> pd.DataFrame:
        """
        清洗因子数据
        
        Args:
            factor_values: 因子值DataFrame
            dropna: 是否删除缺失值
            winsorize: 是否去极值
            winsorize_limit: 去极值分位数
            standardize: 是否标准化
        
        Returns:
            清洗后的因子值
        """
        cleaned = factor_values.copy()
        
        if winsorize:
            lower = cleaned.quantile(winsorize_limit)
            upper = cleaned.quantile(1 - winsorize_limit)
            cleaned = cleaned.clip(lower=lower, upper=upper, axis=1)
        
        if standardize:
            mean = cleaned.mean(axis=1)
            std = cleaned.std(axis=1)
            std[std == 0] = 1
            cleaned = cleaned.sub(mean, axis=0).div(std, axis=0)
        
        if dropna:
            cleaned = cleaned.dropna(how='all')
        
        return cleaned
    
    @staticmethod
    def get_sector_mapping(
        data_dict: Dict[str, pd.DataFrame],
        sector_col: str = 'sector',
    ) -> Dict[str, str]:
        """
        获取股票行业映射
        
        Args:
            data_dict: 股票数据字典
            sector_col: 行业列名
        
        Returns:
            股票到行业的映射字典
        """
        sector_map = {}
        
        for symbol, data in data_dict.items():
            if sector_col in data.columns:
                sector = data[sector_col].iloc[-1]
                if pd.notna(sector):
                    sector_map[symbol] = str(sector)
        
        return sector_map
    
    @staticmethod
    def create_sample_weights(
        factor_values: pd.DataFrame,
        method: str = 'equal',
    ) -> Optional[pd.Series]:
        """
        创建样本权重
        
        Args:
            factor_values: 因子值DataFrame
            method: 权重方法 ('equal', 'inverse_vol', 'market_cap')
        
        Returns:
            权重Series或None
        """
        if method == 'equal':
            return None
        elif method == 'inverse_vol':
            vol = factor_values.std(axis=1)
            vol[vol == 0] = 1
            weights = 1 / vol
            weights = weights / weights.sum()
            return weights
        else:
            return None


def convert_to_alphalens_format(
    factor_values: pd.DataFrame,
    prices: pd.DataFrame,
    clean: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    便捷函数：转换为alphalens格式
    
    Args:
        factor_values: 因子值DataFrame
        prices: 价格DataFrame
        clean: 是否清洗数据
    
    Returns:
        (因子值DataFrame, 价格DataFrame)
    """
    if clean:
        factor_values = DataConverter.clean_factor_data(factor_values)
    
    return DataConverter.align_data(factor_values, prices, method='inner')


def prepare_single_factor(
    factor_expr: FactorExpression,
    data_dict: Dict[str, pd.DataFrame],
    window_sizes: Optional[List[int]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    便捷函数：准备单个因子数据
    
    Args:
        factor_expr: 因子表达式
        data_dict: 股票数据字典
        window_sizes: 窗口大小列表
    
    Returns:
        (因子值DataFrame, 价格DataFrame)
    """
    factor_panel = DataConverter.factor_expression_to_panel(
        [factor_expr], data_dict, window_sizes
    )
    
    if not factor_panel:
        raise ValueError(f"Failed to convert factor: {factor_expr.name}")
    
    factor_values = list(factor_panel.values())[0]
    prices = DataConverter.get_pricing_data(data_dict)
    
    return DataConverter.align_data(factor_values, prices, method='inner')
