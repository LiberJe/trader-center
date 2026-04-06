"""
Alphalens适配器

将自研系统的数据格式转换为Alphalens-Reloaded所需的格式，
并封装Alphalens的核心分析功能。
"""

from typing import Optional, Dict, List, Union
import pandas as pd
import numpy as np
import logging

try:
    import alphalens
    from alphalens.utils import get_clean_factor_and_forward_returns
    from alphalens.tears import create_full_tear_sheet, create_returns_tear_sheet, create_information_tear_sheet
    from alphalens.performance import (
        factor_information_coefficient,
        mean_information_coefficient,
        factor_returns,
        factor_alpha_beta,
        mean_return_by_quantile,
        compute_mean_returns_spread,
    )
    from alphalens.plotting import (
        plot_ic_ts,
        plot_ic_hist,
        plot_ic_qq,
        plot_cumulative_returns,
        plot_cumulative_returns_by_quantile,
        plot_quantile_average_cumulative_return,
        plot_top_bottom_cumulative_returns,
    )
    ALPHALENS_AVAILABLE = True
except ImportError:
    ALPHALENS_AVAILABLE = False


logger = logging.getLogger(__name__)


class AlphalensAdapter:
    """
    Alphalens适配器
    
    将自研系统的数据格式转换为Alphalens格式，并封装核心分析功能。
    
    Example:
        adapter = AlphalensAdapter(periods=[1, 5, 10, 20])
        
        # 转换数据格式
        factor_data = adapter.create_factor_data(factor_df, price_df)
        
        # 运行分析
        result = adapter.run_full_analysis(factor_data)
        
        # 生成完整报告
        adapter.create_tear_sheet(factor_data)
    """
    
    def __init__(
        self,
        periods: List[int] = None,
        quantiles: int = 5,
        bins: int = None,
        filter_zscore: float = 20.0,
        max_loss: float = 0.35,
    ):
        """
        初始化Alphalens适配器
        
        Args:
            periods: 未来收益计算周期列表，默认[1, 5, 10, 20]
            quantiles: 分层数量，默认5
            bins: 分箱数量（与quantiles二选一）
            filter_zscore: 因子值zscore过滤阈值，默认20
            max_loss: 最大数据丢失比例，默认0.35
        """
        if not ALPHALENS_AVAILABLE:
            raise ImportError(
                "alphalens-reloaded未安装，请运行: pip install alphalens-reloaded"
            )
        
        self.periods = periods or [1, 5, 10, 20]
        self.quantiles = quantiles
        self.bins = bins
        self.filter_zscore = filter_zscore
        self.max_loss = max_loss
    
    def convert_factor_format(
        self,
        factor_df: pd.DataFrame,
    ) -> pd.Series:
        """
        将因子DataFrame转换为Alphalens格式
        
        Args:
            factor_df: 因子值DataFrame，index为日期，columns为资产代码
        
        Returns:
            MultiIndex Series，index为(date, asset)
        """
        factor_series = factor_df.stack()
        factor_series.index.names = ['date', 'asset']
        return factor_series
    
    def convert_price_format(
        self,
        price_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        将价格DataFrame转换为Alphalens格式
        
        Args:
            price_df: 价格DataFrame，index为日期，columns为资产代码
        
        Returns:
            DataFrame，index为日期，columns为资产代码
        """
        return price_df.copy()
    
    def create_factor_data(
        self,
        factor_df: pd.DataFrame,
        price_df: pd.DataFrame,
        groupby: pd.Series = None,
        by_group: bool = False,
    ) -> pd.DataFrame:
        """
        创建Alphalens因子数据
        
        将因子数据和价格数据转换为Alphalens所需的格式，
        并计算未来收益。
        
        Args:
            factor_df: 因子值DataFrame，index为日期，columns为资产代码
            price_df: 价格DataFrame，index为日期，columns为资产代码
            groupby: 行业分组Series，index为资产代码
            by_group: 是否按组处理
        
        Returns:
            Alphalens格式的因子数据，包含因子值和未来收益
        
        Example:
            factor_data = adapter.create_factor_data(
                factor_df=momentum_values,
                price_df=close_prices,
            )
        """
        factor_series = self.convert_factor_format(factor_df)
        prices = self.convert_price_format(price_df)
        
        factor_data = get_clean_factor_and_forward_returns(
            factor=factor_series,
            prices=prices,
            periods=self.periods,
            quantiles=self.quantiles,
            bins=self.bins,
            filter_zscore=self.filter_zscore,
            max_loss=self.max_loss,
            groupby=groupby,
            by_group=by_group,
        )
        
        logger.info(f"创建因子数据成功，形状: {factor_data.shape}")
        
        return factor_data
    
    def compute_ic(
        self,
        factor_data: pd.DataFrame,
        by_group: bool = False,
    ) -> pd.DataFrame:
        """
        计算因子IC
        
        Args:
            factor_data: Alphalens格式的因子数据
            by_group: 是否按组计算
        
        Returns:
            IC DataFrame
        """
        ic = factor_information_coefficient(factor_data, by_group=by_group)
        return ic
    
    def compute_mean_ic(
        self,
        factor_data: pd.DataFrame,
        by_time: str = None,
        by_group: bool = False,
    ) -> Union[pd.Series, pd.DataFrame]:
        """
        计算平均IC
        
        Args:
            factor_data: Alphalens格式的因子数据
            by_time: 按时间聚合 ('D', 'W', 'M', 'Q', 'A')
            by_group: 是否按组计算
        
        Returns:
            平均IC
        """
        mean_ic = mean_information_coefficient(
            factor_data,
            by_time=by_time,
            by_group=by_group,
        )
        return mean_ic
    
    def compute_factor_returns(
        self,
        factor_data: pd.DataFrame,
        long_short: bool = True,
        group_neutral: bool = False,
        equal_weight: bool = True,
    ) -> pd.DataFrame:
        """
        计算因子收益
        
        Args:
            factor_data: Alphalens格式的因子数据
            long_short: 是否计算多空收益
            group_neutral: 是否行业中性
            equal_weight: 是否等权
        
        Returns:
            因子收益DataFrame
        """
        returns = factor_returns(
            factor_data,
            long_short=long_short,
            group_neutral=group_neutral,
            equal_weight=equal_weight,
        )
        return returns
    
    def compute_alpha_beta(
        self,
        factor_data: pd.DataFrame,
        returns: pd.DataFrame = None,
        benchmark_rets: pd.Series = None,
    ) -> pd.DataFrame:
        """
        计算因子Alpha和Beta
        
        Args:
            factor_data: Alphalens格式的因子数据
            returns: 因子收益
            benchmark_rets: 基准收益
        
        Returns:
            Alpha和Beta DataFrame
        """
        ab = factor_alpha_beta(
            factor_data,
            returns=returns,
            benchmark_rets=benchmark_rets,
        )
        return ab
    
    def compute_quantile_returns(
        self,
        factor_data: pd.DataFrame,
        by_date: bool = True,
        by_group: bool = False,
        demeaned: bool = True,
        group_adjust: bool = False,
    ) -> pd.DataFrame:
        """
        计算各分层的平均收益
        
        Args:
            factor_data: Alphalens格式的因子数据
            by_date: 是否按日期聚合
            by_group: 是否按组聚合
            demeaned: 是否去均值
            group_adjust: 是否组调整
        
        Returns:
            分层收益DataFrame
        """
        quantile_returns = mean_return_by_quantile(
            factor_data,
            by_date=by_date,
            by_group=by_group,
            demeaned=demeaned,
            group_adjust=group_adjust,
        )
        return quantile_returns
    
    def compute_mean_returns_spread(
        self,
        factor_data: pd.DataFrame,
        upper_quant: int = None,
        lower_quant: int = None,
        by_date: bool = True,
        by_group: bool = False,
        demeaned: bool = True,
        group_adjust: bool = False,
    ) -> pd.DataFrame:
        """
        计算多空收益差
        
        Args:
            factor_data: Alphalens格式的因子数据
            upper_quant: 上层分位数，默认最高层
            lower_quant: 下层分位数，默认最低层
            by_date: 是否按日期聚合
            by_group: 是否按组聚合
            demeaned: 是否去均值
            group_adjust: 是否组调整
        
        Returns:
            多空收益差DataFrame
        """
        if upper_quant is None:
            upper_quant = self.quantiles
        if lower_quant is None:
            lower_quant = 1
        
        spread = compute_mean_returns_spread(
            factor_data,
            upper_quant=upper_quant,
            lower_quant=lower_quant,
            by_date=by_date,
            by_group=by_group,
            demeaned=demeaned,
            group_adjust=group_adjust,
        )
        return spread
    
    def run_full_analysis(
        self,
        factor_data: pd.DataFrame,
        long_short: bool = True,
        group_neutral: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        """
        运行完整的因子分析
        
        Args:
            factor_data: Alphalens格式的因子数据
            long_short: 是否计算多空收益
            group_neutral: 是否行业中性
        
        Returns:
            包含各项分析结果的字典
        
        Example:
            result = adapter.run_full_analysis(factor_data)
            print(result['ic'].mean())
            print(result['mean_ic'])
        """
        results = {}
        
        results['ic'] = self.compute_ic(factor_data)
        results['mean_ic'] = self.compute_mean_ic(factor_data)
        
        results['factor_returns'] = self.compute_factor_returns(
            factor_data,
            long_short=long_short,
            group_neutral=group_neutral,
        )
        
        results['alpha_beta'] = self.compute_alpha_beta(factor_data)
        
        results['quantile_returns'] = self.compute_quantile_returns(factor_data)
        
        results['mean_returns_spread'] = self.compute_mean_returns_spread(factor_data)
        
        results['summary'] = self._create_summary(results)
        
        logger.info("因子分析完成")
        
        return results
    
    def _create_summary(self, results: Dict) -> Dict:
        """
        创建分析摘要
        
        Args:
            results: 分析结果字典
        
        Returns:
            摘要字典
        """
        ic = results['ic']
        mean_ic = results['mean_ic']
        
        summary = {
            'ic_mean': ic.mean().mean(),
            'ic_std': ic.std().mean(),
            'icir': mean_ic.mean() / mean_ic.std() if mean_ic.std() != 0 else 0,
            'ic_positive_ratio': (ic > 0).mean().mean(),
            'ic_skew': ic.skew().mean(),
            'ic_kurtosis': ic.kurtosis().mean(),
        }
        
        if 'factor_returns' in results:
            fr = results['factor_returns']
            if not fr.empty:
                summary['factor_return_mean'] = fr.mean().mean()
                summary['factor_return_std'] = fr.std().mean()
                if fr.std().mean() != 0:
                    summary['factor_sharpe'] = fr.mean().mean() / fr.std().mean()
        
        return summary
    
    def create_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        long_short: bool = True,
        group_neutral: bool = False,
        by_group: bool = False,
        show_plots: bool = True,
    ) -> None:
        """
        生成Alphalens完整分析报告
        
        包含IC分析、分层收益分析、收益分析等多个图表。
        
        Args:
            factor_data: Alphalens格式的因子数据
            long_short: 是否计算多空收益
            group_neutral: 是否行业中性
            by_group: 是否按组分析
            show_plots: 是否显示图表
        """
        create_full_tear_sheet(
            factor_data,
            long_short=long_short,
            group_neutral=group_neutral,
            by_group=by_group,
        )
    
    def create_returns_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        long_short: bool = True,
        group_neutral: bool = False,
        by_group: bool = False,
    ) -> None:
        """
        生成收益分析报告
        
        Args:
            factor_data: Alphalens格式的因子数据
            long_short: 是否计算多空收益
            group_neutral: 是否行业中性
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
        生成IC分析报告
        
        Args:
            factor_data: Alphalens格式的因子数据
            group_neutral: 是否行业中性
            by_group: 是否按组分析
        """
        create_information_tear_sheet(
            factor_data,
            group_neutral=group_neutral,
            by_group=by_group,
        )


def check_alphalens_available() -> bool:
    """
    检查Alphalens是否可用
    
    Returns:
        True如果可用
    """
    return ALPHALENS_AVAILABLE


def quick_analyze(
    factor_df: pd.DataFrame,
    price_df: pd.DataFrame,
    periods: List[int] = None,
    quantiles: int = 5,
    show_tear_sheet: bool = True,
) -> Dict:
    """
    快速因子分析
    
    一键完成因子分析，适合快速验证因子有效性。
    
    Args:
        factor_df: 因子值DataFrame
        price_df: 价格DataFrame
        periods: 未来收益周期
        quantiles: 分层数量
        show_tear_sheet: 是否显示完整报告
    
    Returns:
        分析结果字典
    
    Example:
        result = quick_analyze(momentum_df, close_df)
        print(f"IC均值: {result['summary']['ic_mean']:.4f}")
    """
    adapter = AlphalensAdapter(periods=periods, quantiles=quantiles)
    
    factor_data = adapter.create_factor_data(factor_df, price_df)
    
    result = adapter.run_full_analysis(factor_data)
    
    if show_tear_sheet:
        adapter.create_tear_sheet(factor_data)
    
    return result
