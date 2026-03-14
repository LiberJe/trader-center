"""
因子评价报告生成器

整合alphalens分析，生成完整的因子评价报告。
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import logging
import warnings

from .alphalens_adapter import AlphalensAdapter, ALPHALENS_AVAILABLE
from .data_converter import DataConverter

logger = logging.getLogger(__name__)


class FactorReportGenerator:
    """
    因子评价报告生成器
    
    整合alphalens进行专业因子分析，生成完整的评价报告。
    
    Example:
        generator = FactorReportGenerator(output_dir='./reports')
        
        # 生成完整报告
        report_path = generator.generate_full_report(
            factor_values, prices, title="因子评价报告"
        )
    """
    
    def __init__(
        self,
        output_dir: str = './reports',
        use_alphalens: bool = True,
    ):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
            use_alphalens: 是否使用alphalens
        """
        self.output_dir = output_dir
        self.use_alphalens = use_alphalens and ALPHALENS_AVAILABLE
        
        if self.use_alphalens:
            self.alphalens = AlphalensAdapter()
        else:
            self.alphalens = None
            if use_alphalens:
                warnings.warn(
                    "alphalens-reloaded not available. "
                    "Install with: pip install alphalens-reloaded"
                )
        
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_full_report(
        self,
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
        title: str = "因子评价报告",
        quantiles: int = 5,
        periods: Tuple[int, ...] = (1, 5, 10, 20),
        groupby: Optional[Dict[str, str]] = None,
        save_charts: bool = True,
        show_charts: bool = True,
    ) -> Dict[str, Any]:
        """
        生成完整因子评价报告
        
        Args:
            factor_values: 因子值DataFrame，index为日期，columns为股票代码
            prices: 价格DataFrame，index为日期，columns为股票代码
            title: 报告标题
            quantiles: 分组数量
            periods: 前瞻收益周期
            groupby: 行业分组字典
            save_charts: 是否保存图表
            show_charts: 是否显示图表
        
        Returns:
            报告结果字典
        """
        result = {
            'title': title,
            'generated_at': datetime.now().isoformat(),
            'factor_shape': factor_values.shape,
            'prices_shape': prices.shape,
            'quantiles': quantiles,
            'periods': periods,
        }
        
        if self.use_alphalens:
            factor_data = self.alphalens.prepare_factor_data(
                factor_values=factor_values,
                prices=prices,
                quantiles=quantiles,
                periods=periods,
                groupby=groupby,
            )
            
            result['factor_data_shape'] = factor_data.shape
            
            stats = self.alphalens.compute_factor_stats(factor_data)
            
            def safe_float(val):
                if val is None:
                    return np.nan
                if isinstance(val, pd.Series):
                    return float(val.iloc[0]) if len(val) > 0 else np.nan
                if isinstance(val, pd.DataFrame):
                    return float(val.iloc[0, 0]) if val.size > 0 else np.nan
                if isinstance(val, np.ndarray):
                    return float(val.flatten()[0]) if val.size > 0 else np.nan
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return np.nan
            
            result['stats'] = {
                'mean_factor_return': safe_float(stats.get('mean_factor_return')),
                'factor_sharpe': safe_float(stats.get('factor_sharpe')),
                'ic_mean': safe_float(stats.get('ic_mean')),
                'icir': safe_float(stats.get('icir')),
                'ic_positive_ratio': safe_float(stats.get('ic_positive_ratio')),
                'alpha': safe_float(stats.get('alpha')),
                'beta': safe_float(stats.get('beta')),
            }
            
            if show_charts:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                plt.ioff()
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                chart_dir = os.path.join(self.output_dir, f'charts_{timestamp}')
                os.makedirs(chart_dir, exist_ok=True)
                
                chart_count = 0
                
                try:
                    from alphalens import plotting
                    from alphalens import performance
                    
                    def save_current_figures(prefix):
                        nonlocal chart_count
                        for fig_num in list(plt.get_fignums()):
                            fig = plt.figure(fig_num)
                            chart_count += 1
                            fig.savefig(
                                os.path.join(chart_dir, f'{prefix}_{chart_count}.png'),
                                dpi=150,
                                bbox_inches='tight',
                                facecolor='white',
                                edgecolor='none'
                            )
                            plt.close(fig)
                    
                    mean_ret_q = None
                    ic = None
                    
                    try:
                        mean_ret_q_result = performance.mean_return_by_quantile(factor_data)
                        if isinstance(mean_ret_q_result, tuple):
                            mean_ret_q = mean_ret_q_result[0]
                        else:
                            mean_ret_q = mean_ret_q_result
                        plotting.plot_quantile_returns_bar(mean_ret_q)
                        save_current_figures('quantile_returns_bar')
                    except Exception as e:
                        logger.debug(f"Failed to plot quantile returns bar: {e}")
                    
                    try:
                        if mean_ret_q is not None and '1D' in factor_data.columns:
                            plotting.plot_cumulative_returns_by_quantile(mean_ret_q, factor_data['1D'])
                            save_current_figures('cumulative_returns')
                    except Exception as e:
                        logger.debug(f"Failed to plot cumulative returns: {e}")
                    
                    try:
                        if mean_ret_q is not None and not mean_ret_q.empty:
                            plotting.plot_quantile_returns_violin(mean_ret_q)
                            save_current_figures('quantile_returns_violin')
                    except Exception as e:
                        logger.debug(f"Failed to plot quantile returns violin: {e}")
                    
                    try:
                        ic_result = performance.factor_information_coefficient(factor_data)
                        if isinstance(ic_result, tuple):
                            ic = ic_result[0]
                        else:
                            ic = ic_result
                        plotting.plot_ic_ts(ic)
                        save_current_figures('ic_ts')
                    except Exception as e:
                        logger.debug(f"Failed to plot IC time series: {e}")
                    
                    try:
                        if ic is not None:
                            plotting.plot_ic_hist(ic)
                            save_current_figures('ic_hist')
                    except Exception as e:
                        logger.debug(f"Failed to plot IC histogram: {e}")
                    
                    try:
                        if ic is not None:
                            plotting.plot_ic_qq(ic)
                            save_current_figures('ic_qq')
                    except Exception as e:
                        logger.debug(f"Failed to plot IC QQ: {e}")
                    
                    try:
                        plotting.plot_monthly_ic_heatmap(ic)
                        save_current_figures('ic_monthly_heatmap')
                    except Exception as e:
                        logger.debug(f"Failed to plot monthly IC heatmap: {e}")
                    
                    try:
                        autocorr = performance.factor_rank_autocorrelation(factor_data)
                        if autocorr is not None and not autocorr.empty:
                            if isinstance(autocorr, tuple):
                                autocorr = autocorr[0]
                            plotting.plot_factor_rank_auto_correlation(autocorr)
                            save_current_figures('autocorr')
                    except Exception as e:
                        logger.debug(f"Failed to plot autocorrelation: {e}")
                    
                    try:
                        turnover = performance.quantile_turnover(factor_data)
                        if isinstance(turnover, tuple):
                            turnover = turnover[0]
                        plotting.plot_top_bottom_quantile_turnover(turnover)
                        save_current_figures('turnover')
                    except Exception as e:
                        logger.debug(f"Failed to plot turnover: {e}")
                    
                    try:
                        plotting.plot_returns_table(factor_data)
                        save_current_figures('returns_table')
                    except Exception as e:
                        logger.debug(f"Failed to plot returns table: {e}")
                    
                    try:
                        plotting.plot_quantile_statistics_table(factor_data)
                        save_current_figures('quantile_stats_table')
                    except Exception as e:
                        logger.debug(f"Failed to plot quantile statistics table: {e}")
                    
                    result['chart_dir'] = chart_dir
                    result['n_charts'] = chart_count
                    logger.info(f"Saved {chart_count} charts to {chart_dir}")
                    
                except Exception as e:
                    logger.warning(f"Failed to save charts: {e}")
                    result['chart_error'] = str(e)
                finally:
                    plt.close('all')
        else:
            result['stats'] = self._compute_basic_stats(factor_values, prices)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_path = os.path.join(self.output_dir, f'report_{timestamp}.json')
        
        import json
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        result['report_path'] = result_path
        
        logger.info(f"Report generated: {result_path}")
        return result
    
    def _compute_basic_stats(
        self,
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> Dict[str, float]:
        """计算基础统计指标（不依赖alphalens）"""
        from scipy.stats import spearmanr
        
        forward_returns = prices.pct_change(5).shift(-5)
        
        common_dates = factor_values.index.intersection(forward_returns.index)
        common_symbols = factor_values.columns.intersection(forward_returns.columns)
        
        ic_list = []
        for date in common_dates:
            try:
                factor_row = factor_values.loc[date, common_symbols].dropna()
                return_row = forward_returns.loc[date, common_symbols].dropna()
                
                common = factor_row.index.intersection(return_row.index)
                if len(common) > 10:
                    ic, _ = spearmanr(factor_row[common], return_row[common])
                    if not np.isnan(ic):
                        ic_list.append(ic)
            except Exception:
                continue
        
        if ic_list:
            ic_mean = np.mean(ic_list)
            ic_std = np.std(ic_list)
            icir = ic_mean / ic_std if ic_std > 0 else 0
            ic_positive_ratio = np.mean([ic > 0 for ic in ic_list])
        else:
            ic_mean = ic_std = icir = ic_positive_ratio = np.nan
        
        return {
            'ic_mean': float(ic_mean),
            'ic_std': float(ic_std),
            'icir': float(icir),
            'ic_positive_ratio': float(ic_positive_ratio),
            'n_periods': len(ic_list),
        }
    
    def analyze_single_factor(
        self,
        factor_expr: Any,
        data_dict: Dict[str, pd.DataFrame],
        title: Optional[str] = None,
        quantiles: int = 5,
        periods: Tuple[int, ...] = (1, 5, 10, 20),
    ) -> Dict[str, Any]:
        """
        分析单个因子
        
        Args:
            factor_expr: 因子表达式
            data_dict: 股票数据字典
            title: 报告标题
            quantiles: 分组数量
            periods: 前瞻收益周期
        
        Returns:
            分析结果字典
        """
        from .data_converter import prepare_single_factor
        
        factor_values, prices = prepare_single_factor(
            factor_expr, data_dict
        )
        
        title = title or f"因子分析: {factor_expr.name}"
        
        return self.generate_full_report(
            factor_values, prices,
            title=title,
            quantiles=quantiles,
            periods=periods,
        )
    
    def analyze_mining_result(
        self,
        result: Any,
        data_dict: Dict[str, pd.DataFrame],
        title: str = "因子挖掘评价报告",
    ) -> Dict[str, Any]:
        """
        分析因子挖掘结果
        
        Args:
            result: MiningResult实例
            data_dict: 股票数据字典
            title: 报告标题
        
        Returns:
            分析结果字典
        """
        factor_values, prices = DataConverter.mining_result_to_alphalens_format(
            result, data_dict
        )
        
        return self.generate_full_report(
            factor_values, prices,
            title=title,
        )
    
    def batch_analyze_factors(
        self,
        factors_dict: Dict[str, pd.DataFrame],
        prices: pd.DataFrame,
        quantiles: int = 5,
        periods: Tuple[int, ...] = (1, 5, 10, 20),
    ) -> pd.DataFrame:
        """
        批量分析多个因子
        
        Args:
            factors_dict: 因子字典 {因子名称: 因子值DataFrame}
            prices: 价格DataFrame
            quantiles: 分组数量
            periods: 前瞻收益周期
        
        Returns:
            因子统计汇总DataFrame
        """
        results = []
        
        for factor_name, factor_values in factors_dict.items():
            try:
                report = self.generate_full_report(
                    factor_values, prices,
                    title=f"因子分析: {factor_name}",
                    quantiles=quantiles,
                    periods=periods,
                    show_charts=False,
                    save_charts=False,
                )
                
                stats = report.get('stats', {})
                results.append({
                    'factor_name': factor_name,
                    'ic_mean': stats.get('ic_mean', np.nan),
                    'icir': stats.get('icir', np.nan),
                    'ic_positive_ratio': stats.get('ic_positive_ratio', np.nan),
                    'factor_sharpe': stats.get('factor_sharpe', np.nan),
                    'alpha': stats.get('alpha', np.nan),
                })
                
            except Exception as e:
                logger.warning(f"Failed to analyze factor {factor_name}: {e}")
                results.append({
                    'factor_name': factor_name,
                    'error': str(e),
                })
        
        return pd.DataFrame(results)
    
    def export_to_excel(
        self,
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
        filename: str = "factor_analysis.xlsx",
        quantiles: int = 5,
    ) -> str:
        """
        导出分析结果到Excel
        
        Args:
            factor_values: 因子值DataFrame
            prices: 价格DataFrame
            filename: 文件名
            quantiles: 分组数量
        
        Returns:
            文件路径
        """
        filepath = os.path.join(self.output_dir, filename)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            factor_values.to_excel(writer, sheet_name='因子值')
            prices.to_excel(writer, sheet_name='价格')
            
            if self.use_alphalens:
                factor_data = self.alphalens.prepare_factor_data(
                    factor_values, prices, quantiles=quantiles
                )
                factor_data.to_excel(writer, sheet_name='Alphalens数据')
                
                stats = self.alphalens.compute_factor_stats(factor_data)
                
                stats_df = pd.DataFrame([
                    {'指标': k, '值': v} 
                    for k, v in stats.items() 
                    if not isinstance(v, pd.DataFrame)
                ])
                stats_df.to_excel(writer, sheet_name='统计指标', index=False)
        
        logger.info(f"Exported to Excel: {filepath}")
        return filepath
    
    def print_summary(
        self,
        result: Dict[str, Any],
    ) -> str:
        """
        打印报告摘要
        
        Args:
            result: 报告结果字典
        
        Returns:
            摘要文本
        """
        lines = [
            "=" * 60,
            f" {result.get('title', '因子评价报告')}",
            "=" * 60,
            f"生成时间: {result.get('generated_at', 'N/A')}",
            f"因子数据: {result.get('factor_shape', 'N/A')}",
            f"价格数据: {result.get('prices_shape', 'N/A')}",
            f"分组数量: {result.get('quantiles', 'N/A')}",
            "",
        ]
        
        stats = result.get('stats', {})
        if stats:
            lines.append("统计指标:")
            lines.append(f"  IC均值: {stats.get('ic_mean', 'N/A'):.4f}" if isinstance(stats.get('ic_mean'), (int, float)) else f"  IC均值: N/A")
            lines.append(f"  ICIR: {stats.get('icir', 'N/A'):.4f}" if isinstance(stats.get('icir'), (int, float)) else f"  ICIR: N/A")
            lines.append(f"  IC正向比例: {stats.get('ic_positive_ratio', 'N/A'):.2%}" if isinstance(stats.get('ic_positive_ratio'), (int, float)) else f"  IC正向比例: N/A")
            lines.append(f"  因子夏普: {stats.get('factor_sharpe', 'N/A'):.4f}" if isinstance(stats.get('factor_sharpe'), (int, float)) else f"  因子夏普: N/A")
            lines.append(f"  Alpha: {stats.get('alpha', 'N/A'):.4f}" if isinstance(stats.get('alpha'), (int, float)) else f"  Alpha: N/A")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


def generate_factor_report(
    factor_values: pd.DataFrame,
    prices: pd.DataFrame,
    output_dir: str = './reports',
    title: str = "因子评价报告",
    **kwargs,
) -> Dict[str, Any]:
    """
    便捷函数：生成因子评价报告
    
    Args:
        factor_values: 因子值DataFrame
        prices: 价格DataFrame
        output_dir: 输出目录
        title: 报告标题
        **kwargs: 其他参数
    
    Returns:
        报告结果字典
    """
    generator = FactorReportGenerator(output_dir=output_dir)
    return generator.generate_full_report(
        factor_values, prices,
        title=title,
        **kwargs,
    )
