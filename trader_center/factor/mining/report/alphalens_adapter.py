"""
Alphalens适配器

将框架数据转换为alphalens格式，并提供因子分析功能。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List, Union
import logging
import warnings

logger = logging.getLogger(__name__)

try:
    import alphalens
    from alphalens.utils import get_clean_factor_and_forward_returns
    from alphalens.tears import (
        create_full_tear_sheet,
        create_returns_tear_sheet,
        create_information_tear_sheet,
        create_turnover_tear_sheet,
        create_event_returns_tear_sheet,
    )
    ALPHALENS_AVAILABLE = True
except ImportError:
    ALPHALENS_AVAILABLE = False
    warnings.warn("alphalens-reloaded not installed. Install with: pip install alphalens-reloaded")


class AlphalensAdapter:
    """
    Alphalens适配器
    
    将框架数据转换为alphalens格式，并提供专业的因子分析功能。
    
    Example:
        adapter = AlphalensAdapter()
        
        # 准备数据
        factor_data = adapter.prepare_factor_data(
            factor_values=factor_df,
            prices=price_df,
            quantiles=5,
        )
        
        # 生成完整报告
        adapter.create_tear_sheet(factor_data)
    """
    
    def __init__(self):
        """初始化Alphalens适配器"""
        self._check_availability()
    
    def _check_availability(self) -> bool:
        """检查alphalens是否可用"""
        if not ALPHALENS_AVAILABLE:
            raise ImportError(
                "alphalens-reloaded is required for factor analysis. "
                "Install with: pip install alphalens-reloaded"
            )
        return True
    
    def prepare_factor_data(
        self,
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
        quantiles: int = 5,
        periods: Tuple[int, ...] = (1, 5, 10, 20),
        groupby: Optional[Dict[str, str]] = None,
        groupby_labels: Optional[Dict[str, str]] = None,
        filter_zscore: float = 20.0,
        max_loss: float = 0.35,
    ) -> pd.DataFrame:
        """
        准备alphalens格式的因子数据
        
        Args:
            factor_values: 因子值DataFrame，index为日期，columns为股票代码
            prices: 价格数据DataFrame，index为日期，columns为股票代码
            quantiles: 分组数量
            periods: 前瞻收益计算周期
            groupby: 股票分组字典 {股票代码: 分组名}
            groupby_labels: 分组标签映射
            filter_zscore: Z-score过滤阈值
            max_loss: 最大允许数据丢失比例
        
        Returns:
            alphalens格式的因子数据
        
        Example:
            factor_data = adapter.prepare_factor_data(
                factor_values=factor_df,
                prices=price_df,
                quantiles=5,
                periods=(1, 5, 10, 20),
            )
        """
        factor_stack = self._stack_factor(factor_values)
        
        if groupby is not None:
            groupby_series = pd.Series(groupby)
        else:
            groupby_series = None
        
        factor_data = get_clean_factor_and_forward_returns(
            factor=factor_stack,
            prices=prices,
            quantiles=quantiles,
            bins=None,
            periods=periods,
            filter_zscore=filter_zscore,
            groupby=groupby_series,
            groupby_labels=groupby_labels,
            max_loss=max_loss,
        )
        
        logger.info(f"Prepared factor data with shape: {factor_data.shape}")
        
        return factor_data
    
    def _stack_factor(self, factor_values: pd.DataFrame) -> pd.Series:
        """
        将因子DataFrame转换为MultiIndex Series
        
        Args:
            factor_values: 因子值DataFrame
        
        Returns:
            MultiIndex Series (date, asset) -> factor_value
        """
        factor_stack = factor_values.stack()
        factor_stack.index.names = ['date', 'asset']
        factor_stack.name = 'factor'
        return factor_stack
    
    def create_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        long_short: bool = True,
        group_neutral: bool = False,
        by_group: bool = False,
        set_context: bool = True,
    ) -> None:
        """
        创建完整的因子分析报告（Tear Sheet）
        
        Args:
            factor_data: alphalens格式的因子数据
            long_short: 是否计算多空组合
            group_neutral: 是否进行组中性化
            by_group: 是否按组分析
            set_context: 是否设置上下文
        
        Example:
            adapter.create_tear_sheet(factor_data)
        """
        create_full_tear_sheet(
            factor_data,
            long_short=long_short,
            group_neutral=group_neutral,
            by_group=by_group,
            set_context=set_context,
        )
    
    def create_returns_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        long_short: bool = True,
        group_neutral: bool = False,
        by_group: bool = False,
    ) -> None:
        """
        创建收益分析报告
        
        Args:
            factor_data: alphalens格式的因子数据
            long_short: 是否计算多空组合
            group_neutral: 是否进行组中性化
            by_group: 是否按组分析
        """
        create_returns_tear_sheet(
            factor_data,
            long_short=long_short,
            group_neutral=group_neutral,
            by_group=by_group,
        )
    
    def create_information_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        group_neutral: bool = False,
        by_group: bool = False,
    ) -> None:
        """
        创建IC分析报告
        
        Args:
            factor_data: alphalens格式的因子数据
            group_neutral: 是否进行组中性化
            by_group: 是否按组分析
        """
        create_information_tear_sheet(
            factor_data,
            group_neutral=group_neutral,
            by_group=by_group,
        )
    
    def create_turnover_tear_sheet(
        self,
        factor_data: pd.DataFrame,
    ) -> None:
        """
        创建换手率分析报告
        
        Args:
            factor_data: alphalens格式的因子数据
        """
        create_turnover_tear_sheet(factor_data)
    
    def create_event_study_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        prices: pd.DataFrame,
        avgretplot: Tuple[int, int] = (5, 15),
        long_short: bool = True,
        group_neutral: bool = False,
        std_dev: float = 1.0,
    ) -> None:
        """
        创建事件研究报告
        
        Args:
            factor_data: alphalens格式的因子数据
            prices: 价格数据
            avgretplot: 平均收益图参数
            long_short: 是否计算多空组合
            group_neutral: 是否进行组中性化
            std_dev: 标准差阈值
        """
        create_event_returns_tear_sheet(
            factor_data,
            prices,
            avgretplot=avgretplot,
            long_short=long_short,
            group_neutral=group_neutral,
            std_dev=std_dev,
        )
    
    def compute_factor_stats(
        self,
        factor_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        计算因子统计指标
        
        Args:
            factor_data: alphalens格式的因子数据
        
        Returns:
            因子统计指标字典
        """
        from alphalens.performance import (
            factor_returns,
            factor_alpha_beta,
            mean_return_by_quantile,
            compute_mean_returns_spread,
            factor_information_coefficient,
        )
        from alphalens.utils import rate_of_return
        
        stats = {}
        
        try:
            factor_ret = factor_returns(factor_data)
            stats['factor_returns'] = factor_ret
            if isinstance(factor_ret, pd.DataFrame):
                stats['mean_factor_return'] = factor_ret.mean().mean()
                stats['factor_return_std'] = factor_ret.std().mean()
                stats['factor_sharpe'] = stats['mean_factor_return'] / stats['factor_return_std'] if stats['factor_return_std'] > 0 else 0
            else:
                stats['mean_factor_return'] = float(factor_ret.mean())
                stats['factor_return_std'] = float(factor_ret.std())
                stats['factor_sharpe'] = stats['mean_factor_return'] / stats['factor_return_std'] if stats['factor_return_std'] > 0 else 0
        except Exception as e:
            logger.warning(f"Failed to compute factor returns: {e}")
        
        try:
            alpha_beta = factor_alpha_beta(factor_data)
            if isinstance(alpha_beta, pd.DataFrame):
                if 'Ann. alpha' in alpha_beta.index:
                    stats['alpha'] = float(alpha_beta.loc['Ann. alpha'].iloc[0])
                elif 'Ann Alpha' in alpha_beta.index:
                    stats['alpha'] = float(alpha_beta.loc['Ann Alpha'].iloc[0])
                else:
                    stats['alpha'] = np.nan
                
                if 'beta' in alpha_beta.index:
                    stats['beta'] = float(alpha_beta.loc['beta'].iloc[0])
                elif 'Beta' in alpha_beta.index:
                    stats['beta'] = float(alpha_beta.loc['Beta'].iloc[0])
                else:
                    stats['beta'] = np.nan
            else:
                stats['alpha'] = np.nan
                stats['beta'] = np.nan
        except Exception as e:
            logger.warning(f"Failed to compute alpha/beta: {e}")
        
        try:
            ic = factor_information_coefficient(factor_data)
            if isinstance(ic, pd.DataFrame):
                ic_series = ic.mean(axis=1)
                stats['ic_mean'] = float(ic_series.mean())
                stats['ic_std'] = float(ic_series.std())
                stats['icir'] = stats['ic_mean'] / stats['ic_std'] if stats['ic_std'] > 0 else 0
                stats['ic_positive_ratio'] = float((ic_series > 0).mean())
            elif isinstance(ic, pd.Series):
                stats['ic_mean'] = float(ic.mean())
                stats['ic_std'] = float(ic.std())
                stats['icir'] = stats['ic_mean'] / stats['ic_std'] if stats['ic_std'] > 0 else 0
                stats['ic_positive_ratio'] = float((ic > 0).mean())
            else:
                stats['ic_mean'] = np.nan
                stats['ic_std'] = np.nan
                stats['icir'] = np.nan
                stats['ic_positive_ratio'] = np.nan
        except Exception as e:
            logger.warning(f"Failed to compute IC: {e}")
        
        try:
            mean_ret_q = mean_return_by_quantile(factor_data)
            stats['mean_returns_by_quantile'] = mean_ret_q
        except Exception as e:
            logger.warning(f"Failed to compute mean returns by quantile: {e}")
        
        return stats
    
    def get_quantile_returns(
        self,
        factor_data: pd.DataFrame,
        by_date: bool = True,
    ) -> pd.DataFrame:
        """
        获取各分位数组的收益
        
        Args:
            factor_data: alphalens格式的因子数据
            by_date: 是否按日期聚合
        
        Returns:
            各分位数组收益DataFrame
        """
        from alphalens.performance import mean_return_by_quantile
        
        mean_ret = mean_return_by_quantile(factor_data, by_date=by_date)
        return mean_ret
    
    def get_ic_summary(
        self,
        factor_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        获取IC汇总统计
        
        Args:
            factor_data: alphalens格式的因子数据
        
        Returns:
            IC汇总统计DataFrame
        """
        from alphalens.tears import get_ic_summary_table
        
        return get_ic_summary_table(factor_data)


def check_alphalens_availability() -> bool:
    """
    检查alphalens是否可用
    
    Returns:
        True如果可用，否则False
    """
    return ALPHALENS_AVAILABLE


def get_alphalens_version() -> Optional[str]:
    """
    获取alphalens版本
    
    Returns:
        版本字符串，如果不可用则返回None
    """
    if ALPHALENS_AVAILABLE:
        return alphalens.__version__
    return None
