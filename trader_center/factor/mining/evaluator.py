"""
因子评估器

提供因子综合评估功能，包括IC分析、分层回测、相关性分析等。
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import logging
from concurrent.futures import ThreadPoolExecutor

from .ic_analysis import ICAnalyzer, batch_compute_ic
from .layering import LayeringAnalyzer
from .correlation import CorrelationAnalyzer as FactorCorrelationAnalyzer
from .gp.expression import FactorExpression, evaluate_expression

logger = logging.getLogger(__name__)


@dataclass
class FactorMetrics:
    """因子评估指标"""
    factor_name: str
    ic_mean: float = np.nan
    ic_std: float = np.nan
    icir: float = np.nan
    ic_t_stat: float = np.nan
    ic_p_value: float = np.nan
    ic_positive_ratio: float = np.nan
    long_short_return: float = np.nan
    long_short_sharpe: float = np.nan
    monotonicity: float = np.nan
    turnover: float = np.nan
    correlation_with_others: float = np.nan
    complexity: int = 0
    expression: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'factor_name': self.factor_name,
            'ic_mean': self.ic_mean,
            'ic_std': self.ic_std,
            'icir': self.icir,
            'ic_t_stat': self.ic_t_stat,
            'ic_p_value': self.ic_p_value,
            'ic_positive_ratio': self.ic_positive_ratio,
            'long_short_return': self.long_short_return,
            'long_short_sharpe': self.long_short_sharpe,
            'monotonicity': self.monotonicity,
            'turnover': self.turnover,
            'correlation_with_others': self.correlation_with_others,
            'complexity': self.complexity,
            'expression': self.expression,
        }


@dataclass
class FactorReport:
    """因子评估报告"""
    metrics: List[FactorMetrics] = field(default_factory=list)
    ic_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    layering_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    correlation_matrix: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    def get_top_factors(self, metric: str = 'icir', top_n: int = 10) -> List[FactorMetrics]:
        """
        获取排名靠前的因子
        
        Args:
            metric: 排序指标
            top_n: 返回数量
        
        Returns:
            排序后的因子列表
        """
        metric_attr = {
            'ic': 'ic_mean',
            'icir': 'icir',
            'return': 'long_short_return',
            'sharpe': 'long_short_sharpe',
            'monotonicity': 'monotonicity',
        }
        
        attr = metric_attr.get(metric, metric)
        
        valid_metrics = [m for m in self.metrics if not np.isnan(getattr(m, attr, np.nan))]
        sorted_metrics = sorted(valid_metrics, key=lambda x: abs(getattr(x, attr, 0)), reverse=True)
        
        return sorted_metrics[:top_n]
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame"""
        return pd.DataFrame([m.to_dict() for m in self.metrics])
    
    def summary(self) -> str:
        """生成摘要文本"""
        lines = [
            "=" * 60,
            "因子评估报告",
            "=" * 60,
            f"评估因子数量: {len(self.metrics)}",
            "",
        ]
        
        top_icir = self.get_top_factors('icir', 5)
        if top_icir:
            lines.append("ICIR排名前5的因子:")
            for i, m in enumerate(top_icir, 1):
                lines.append(f"  {i}. {m.factor_name}: ICIR={m.icir:.4f}, IC={m.ic_mean:.4f}")
        
        lines.append("")
        
        top_return = self.get_top_factors('return', 5)
        if top_return:
            lines.append("多空收益排名前5的因子:")
            for i, m in enumerate(top_return, 1):
                lines.append(f"  {i}. {m.factor_name}: Return={m.long_short_return:.4f}, Sharpe={m.long_short_sharpe:.4f}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class FactorEvaluator:
    """
    因子评估器
    
    综合评估因子表现，包括IC分析、分层回测、相关性分析等。
    
    Example:
        evaluator = FactorEvaluator()
        report = evaluator.evaluate(factors, data, forward_returns)
        print(report.summary())
    """
    
    def __init__(
        self,
        n_groups: int = 5,
        ic_method: str = 'spearman',
        top_n_for_turnover: int = 50,
        n_jobs: int = 1,
    ):
        """
        初始化因子评估器
        
        Args:
            n_groups: 分层回测组数
            ic_method: IC计算方法
            top_n_for_turnover: 换手率计算时的top N
            n_jobs: 并行数
        """
        self.n_groups = n_groups
        self.ic_method = ic_method
        self.top_n_for_turnover = top_n_for_turnover
        self.n_jobs = n_jobs
    
    def evaluate_single_factor(
        self,
        factor_data: pd.Series,
        forward_returns: pd.Series,
        factor_name: str = "",
    ) -> FactorMetrics:
        """
        评估单个因子
        
        Args:
            factor_data: 因子值Series
            forward_returns: 未来收益Series
            factor_name: 因子名称
        
        Returns:
            因子评估指标
        """
        ic_analyzer = ICAnalyzer()
        ic_result = ic_analyzer.compute(
            factor_data.to_frame().T if isinstance(factor_data, pd.Series) else factor_data,
            forward_returns.to_frame().T if isinstance(forward_returns, pd.Series) else forward_returns,
            self.ic_method
        )
        
        layering_analyzer = LayeringAnalyzer(n_groups=self.n_groups)
        layering_result = layering_analyzer.compute(
            factor_data.to_frame().T if isinstance(factor_data, pd.Series) else factor_data,
            forward_returns.to_frame().T if isinstance(forward_returns, pd.Series) else forward_returns
        )
        
        try:
            turnover = layering_analyzer.compute_turnover(
                factor_data.to_frame().T if isinstance(factor_data, pd.Series) else factor_data,
                self.top_n_for_turnover
            ).mean()
        except Exception:
            turnover = np.nan
        
        monotonicity = layering_analyzer.compute_monotonicity()
        
        return FactorMetrics(
            factor_name=factor_name,
            ic_mean=ic_result.get('ic_mean', np.nan),
            ic_std=ic_result.get('ic_std', np.nan),
            icir=ic_result.get('icir', np.nan),
            ic_t_stat=ic_result.get('ic_t_stat', np.nan),
            ic_p_value=ic_result.get('ic_p_value', np.nan),
            ic_positive_ratio=ic_result.get('ic_positive_ratio', np.nan),
            long_short_return=layering_result.get('long_short_mean', np.nan),
            long_short_sharpe=layering_result.get('long_short_sharpe', np.nan),
            monotonicity=monotonicity,
            turnover=turnover,
        )
    
    def evaluate(
        self,
        factors: Union[List[FactorExpression], Dict[str, pd.Series]],
        data: Optional[pd.DataFrame] = None,
        forward_returns: pd.DataFrame = None,
    ) -> FactorReport:
        """
        批量评估因子
        
        Args:
            factors: 因子列表或因子数据字典
            data: 原始数据（用于计算因子值）
            forward_returns: 未来收益DataFrame
        
        Returns:
            因子评估报告
        """
        if forward_returns is None:
            raise ValueError("forward_returns is required")
        
        factor_data_dict: Dict[str, pd.Series] = {}
        expressions: Dict[str, str] = {}
        
        if isinstance(factors, list):
            for factor_expr in factors:
                if data is not None:
                    factor_values = evaluate_expression(factor_expr.expression_str, data)
                    factor_data_dict[factor_expr.name] = factor_values
                    expressions[factor_expr.name] = factor_expr.expression_str
        else:
            factor_data_dict = factors
        
        metrics_list: List[FactorMetrics] = []
        
        if self.n_jobs > 1:
            with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
                futures = []
                for name, factor_data in factor_data_dict.items():
                    future = executor.submit(
                        self._evaluate_single_cross_sectional,
                        name,
                        factor_data,
                        forward_returns,
                        expressions.get(name, "")
                    )
                    futures.append(future)
                
                for future in futures:
                    metrics_list.append(future.result())
        else:
            for name, factor_data in factor_data_dict.items():
                metrics = self._evaluate_single_cross_sectional(
                    name,
                    factor_data,
                    forward_returns,
                    expressions.get(name, "")
                )
                metrics_list.append(metrics)
        
        factor_df = pd.DataFrame(factor_data_dict)
        correlation_matrix = factor_df.corr()
        
        for i, name in enumerate(factor_data_dict.keys()):
            other_corrs = correlation_matrix.loc[name].drop(name)
            metrics_list[i].correlation_with_others = other_corrs.abs().mean()
        
        report = FactorReport(
            metrics=metrics_list,
            correlation_matrix=correlation_matrix,
        )
        
        return report
    
    def _evaluate_single_cross_sectional(
        self,
        factor_name: str,
        factor_data: pd.Series,
        forward_returns: pd.DataFrame,
        expression: str,
    ) -> FactorMetrics:
        """评估单个因子（横截面）"""
        from scipy.stats import spearmanr
        
        if isinstance(factor_data, pd.Series):
            factor_series = factor_data.dropna()
        else:
            factor_series = pd.Series(factor_data).dropna()
        
        if isinstance(forward_returns, pd.DataFrame):
            if forward_returns.shape[1] == 1:
                returns_series = forward_returns.iloc[:, 0].dropna()
            else:
                returns_series = forward_returns.mean(axis=1).dropna()
        else:
            returns_series = pd.Series(forward_returns).dropna()
        
        common_idx = factor_series.index.intersection(returns_series.index)
        
        if len(common_idx) < 10:
            return FactorMetrics(
                factor_name=factor_name,
                expression=expression,
            )
        
        factor_valid = factor_series.loc[common_idx]
        returns_valid = returns_series.loc[common_idx]
        
        ic_list = []
        for i in range(len(common_idx)):
            try:
                ic, _ = spearmanr([factor_valid.iloc[i]], [returns_valid.iloc[i]])
                if not np.isnan(ic):
                    ic_list.append(ic)
            except Exception:
                pass
        
        if len(ic_list) > 0:
            ic_mean = np.mean(ic_list)
            ic_std = np.std(ic_list) if len(ic_list) > 1 else 0
            icir = ic_mean / ic_std if ic_std > 0 else 0
        else:
            ic_mean = np.nan
            ic_std = np.nan
            icir = np.nan
        
        try:
            overall_ic, _ = spearmanr(factor_valid, returns_valid)
        except Exception:
            overall_ic = np.nan
        
        from .gp.expression import expression_complexity
        
        return FactorMetrics(
            factor_name=factor_name,
            ic_mean=overall_ic if not np.isnan(overall_ic) else ic_mean,
            ic_std=ic_std,
            icir=icir,
            ic_positive_ratio=np.mean([ic > 0 for ic in ic_list]) if ic_list else np.nan,
            long_short_return=np.nan,
            long_short_sharpe=np.nan,
            monotonicity=np.nan,
            turnover=np.nan,
            complexity=expression_complexity(expression) if expression else 0,
            expression=expression,
        )
    
    def rank_factors(
        self,
        factors: List[FactorMetrics],
        metric: str = 'icir',
        ascending: bool = False,
    ) -> pd.DataFrame:
        """
        因子排名
        
        Args:
            factors: 因子指标列表
            metric: 排名指标
            ascending: 是否升序
        
        Returns:
            排名后的DataFrame
        """
        df = pd.DataFrame([f.to_dict() for f in factors])
        
        if metric in df.columns:
            df = df.sort_values(metric, ascending=ascending)
            df['rank'] = range(1, len(df) + 1)
        
        return df
    
    def filter_factors(
        self,
        factors: List[FactorMetrics],
        min_ic: float = 0.02,
        min_icir: float = 0.5,
        max_correlation: float = 0.7,
        min_monotonicity: float = 0.3,
    ) -> List[FactorMetrics]:
        """
        筛选因子
        
        Args:
            factors: 因子指标列表
            min_ic: 最小IC绝对值
            min_icir: 最小ICIR绝对值
            max_correlation: 最大与其他因子相关性
            min_monotonicity: 最小单调性
        
        Returns:
            筛选后的因子列表
        """
        filtered = []
        
        for f in factors:
            if abs(f.ic_mean) < min_ic:
                continue
            if abs(f.icir) < min_icir:
                continue
            if f.correlation_with_others > max_correlation:
                continue
            if abs(f.monotonicity) < min_monotonicity:
                continue
            
            filtered.append(f)
        
        return filtered


def quick_evaluate(
    factor_expr: str,
    data: pd.DataFrame,
    forward_returns: pd.Series,
) -> Dict[str, float]:
    """
    快速评估单个因子表达式
    
    Args:
        factor_expr: 因子表达式字符串
        data: 数据
        forward_returns: 未来收益
    
    Returns:
        评估指标字典
    """
    factor_values = evaluate_expression(factor_expr, data)
    
    from scipy.stats import spearmanr
    
    valid_mask = ~(factor_values.isna() | forward_returns.isna())
    ic, _ = spearmanr(factor_values[valid_mask], forward_returns[valid_mask])
    
    return {
        'ic': ic,
        'valid_count': valid_mask.sum(),
        'mean': factor_values.mean(),
        'std': factor_values.std(),
    }
