"""
因子评分模块

提供因子综合评分和排名功能，
从IC有效性、收益贡献、稳定性、独立性四个维度评估因子质量。
"""

from typing import Optional, Dict, List, Tuple
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FactorScorer:
    """
    因子评分器
    
    从四个维度对因子进行综合评分：
    1. IC有效性 (30%): IC均值、ICIR
    2. 收益贡献 (30%): 多空收益、夏普比率
    3. 稳定性 (20%): IC>0比例、单调性
    4. 独立性 (20%): 与其他因子的相关性
    
    Example:
        scorer = FactorScorer()
        
        # 单因子评分
        score = scorer.score(analysis_result)
        
        # 多因子排名
        ranking = scorer.rank_factors(analysis_results)
    """
    
    def __init__(
        self,
        weights: Dict[str, float] = None,
        ic_threshold: float = 0.02,
        icir_threshold: float = 0.5,
        sharpe_threshold: float = 1.0,
        monotonicity_threshold: float = 0.5,
        correlation_threshold: float = 0.3,
    ):
        """
        初始化因子评分器
        
        Args:
            weights: 各维度权重，默认 {'ic': 0.3, 'return': 0.3, 'stability': 0.2, 'independence': 0.2}
            ic_threshold: IC有效阈值
            icir_threshold: ICIR有效阈值
            sharpe_threshold: 夏普比率阈值
            monotonicity_threshold: 单调性阈值
            correlation_threshold: 相关性阈值
        """
        self.weights = weights or {
            'ic': 0.3,
            'return': 0.3,
            'stability': 0.2,
            'independence': 0.2,
        }
        
        self.ic_threshold = ic_threshold
        self.icir_threshold = icir_threshold
        self.sharpe_threshold = sharpe_threshold
        self.monotonicity_threshold = monotonicity_threshold
        self.correlation_threshold = correlation_threshold
        
        self._validate_weights()
    
    def _validate_weights(self) -> None:
        """验证权重配置"""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"权重总和必须为1.0，当前为 {total}")
    
    def score(
        self,
        analysis_result: Dict,
        correlation_with_others: float = None,
    ) -> Dict[str, float]:
        """
        计算因子综合评分
        
        Args:
            analysis_result: 分析结果字典，包含IC、收益等指标
            correlation_with_others: 与其他因子的平均相关性
        
        Returns:
            评分字典，包含各维度得分和总分
        
        Example:
            result = {
                'summary': {
                    'ic_mean': 0.05,
                    'icir': 0.8,
                    'factor_return_mean': 0.02,
                    'factor_sharpe': 1.5,
                    'ic_positive_ratio': 0.6,
                }
            }
            score = scorer.score(result)
        """
        summary = analysis_result.get('summary', {})
        
        ic_score = self._score_ic(summary)
        
        return_score = self._score_return(summary)
        
        stability_score = self._score_stability(summary, analysis_result)
        
        independence_score = self._score_independence(correlation_with_others)
        
        total_score = (
            ic_score * self.weights['ic'] +
            return_score * self.weights['return'] +
            stability_score * self.weights['stability'] +
            independence_score * self.weights['independence']
        )
        
        grade = self._get_grade(total_score)
        
        return {
            'ic_score': ic_score,
            'return_score': return_score,
            'stability_score': stability_score,
            'independence_score': independence_score,
            'total_score': total_score,
            'grade': grade,
        }
    
    def _score_ic(self, summary: Dict) -> float:
        """
        计算IC维度得分
        
        评分标准:
        - IC均值 > threshold: 0.5分
        - ICIR > threshold: 0.5分
        - 额外奖励: IC均值 > 0.05 或 ICIR > 1.0
        
        Args:
            summary: 分析摘要字典
        
        Returns:
            IC得分 (0-1)
        """
        score = 0.0
        
        ic_mean = summary.get('ic_mean', 0)
        icir = summary.get('icir', 0)
        
        if abs(ic_mean) >= self.ic_threshold:
            score += 0.4
        if abs(ic_mean) >= 0.05:
            score += 0.1
        
        if abs(icir) >= self.icir_threshold:
            score += 0.4
        if abs(icir) >= 1.0:
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_return(self, summary: Dict) -> float:
        """
        计算收益维度得分
        
        评分标准:
        - 多空收益 > 0: 0.5分
        - 夏普比率 > threshold: 0.5分
        - 额外奖励: 夏普比率 > 2.0
        
        Args:
            summary: 分析摘要字典
        
        Returns:
            收益得分 (0-1)
        """
        score = 0.0
        
        factor_return = summary.get('factor_return_mean', 0)
        sharpe = summary.get('factor_sharpe', 0)
        
        if factor_return > 0:
            score += 0.4
        if factor_return > 0.01:
            score += 0.1
        
        if sharpe > self.sharpe_threshold:
            score += 0.4
        if sharpe > 2.0:
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_stability(
        self,
        summary: Dict,
        analysis_result: Dict,
    ) -> float:
        """
        计算稳定性维度得分
        
        评分标准:
        - IC>0比例 > 50%: 0.5分
        - 单调性 > threshold: 0.5分
        
        Args:
            summary: 分析摘要字典
            analysis_result: 完整分析结果
        
        Returns:
            稳定性得分 (0-1)
        """
        score = 0.0
        
        ic_positive_ratio = summary.get('ic_positive_ratio', 0.5)
        
        if ic_positive_ratio > 0.5:
            score += 0.3
        if ic_positive_ratio > 0.6:
            score += 0.2
        
        monotonicity = analysis_result.get('monotonicity', 0)
        
        if abs(monotonicity) > self.monotonicity_threshold:
            score += 0.3
        if abs(monotonicity) > 0.7:
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_independence(
        self,
        correlation_with_others: Optional[float],
    ) -> float:
        """
        计算独立性维度得分
        
        评分标准:
        - 平均相关性 < threshold: 1.0分
        - 平均相关性 < 0.5: 0.5分
        - 无相关性数据: 0.5分（默认中等）
        
        Args:
            correlation_with_others: 与其他因子的平均相关性
        
        Returns:
            独立性得分 (0-1)
        """
        if correlation_with_others is None:
            return 0.5
        
        score = 0.0
        
        if abs(correlation_with_others) < self.correlation_threshold:
            score += 0.6
        if abs(correlation_with_others) < 0.2:
            score += 0.4
        elif abs(correlation_with_others) < 0.5:
            score += 0.3
        
        return min(score, 1.0)
    
    def _get_grade(self, total_score: float) -> str:
        """
        根据总分获取等级
        
        Args:
            total_score: 总分 (0-1)
        
        Returns:
            等级 (A/B/C/D/F)
        """
        if total_score >= 0.8:
            return 'A'
        elif total_score >= 0.6:
            return 'B'
        elif total_score >= 0.4:
            return 'C'
        elif total_score >= 0.2:
            return 'D'
        else:
            return 'F'
    
    def rank_factors(
        self,
        analysis_results: Dict[str, Dict],
        correlation_matrix: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """
        对多个因子进行排名
        
        Args:
            analysis_results: 分析结果字典 {factor_name: result}
            correlation_matrix: 因子相关性矩阵（可选）
        
        Returns:
            排名DataFrame，包含各维度得分和总分
        
        Example:
            results = {
                'momentum': {...},
                'rsi': {...},
                'macd': {...},
            }
            ranking = scorer.rank_factors(results)
            print(ranking.sort_values('total_score', ascending=False))
        """
        scores = []
        
        for factor_name, result in analysis_results.items():
            corr_with_others = None
            if correlation_matrix is not None and factor_name in correlation_matrix.index:
                other_corrs = correlation_matrix.loc[factor_name].drop(factor_name)
                corr_with_others = other_corrs.abs().mean()
            
            score = self.score(result, corr_with_others)
            score['factor'] = factor_name
            scores.append(score)
        
        df = pd.DataFrame(scores)
        df = df.set_index('factor')
        
        df = df.sort_values('total_score', ascending=False)
        
        df['rank'] = range(1, len(df) + 1)
        
        logger.info(f"因子排名完成，共 {len(df)} 个因子")
        
        return df
    
    def get_top_factors(
        self,
        ranking_df: pd.DataFrame,
        top_n: int = 5,
        min_score: float = 0.5,
    ) -> pd.DataFrame:
        """
        获取排名靠前的因子
        
        Args:
            ranking_df: 排名DataFrame
            top_n: 返回数量
            min_score: 最低分数阈值
        
        Returns:
            筛选后的排名DataFrame
        """
        filtered = ranking_df[ranking_df['total_score'] >= min_score]
        return filtered.head(top_n)
    
    def get_grade_distribution(
        self,
        ranking_df: pd.DataFrame,
    ) -> Dict[str, int]:
        """
        获取等级分布
        
        Args:
            ranking_df: 排名DataFrame
        
        Returns:
            等级分布字典
        """
        return ranking_df['grade'].value_counts().to_dict()


def compute_monotonicity(
    quantile_returns: pd.DataFrame,
) -> float:
    """
    计算单调性
    
    衡量分层收益是否单调递增或递减。
    
    Args:
        quantile_returns: 分层收益DataFrame
    
    Returns:
        单调性得分 (-1到1)
    
    Example:
        monotonicity = compute_monotonicity(quantile_returns)
        # 1.0 表示完全单调递增
        # -1.0 表示完全单调递减
        # 0.0 表示无单调性
    """
    mean_returns = quantile_returns.mean()
    
    n = len(mean_returns)
    if n < 2:
        return 0
    
    monotonic_score = 0
    total_pairs = 0
    
    for i in range(n):
        for j in range(i + 1, n):
            if mean_returns.iloc[i] < mean_returns.iloc[j]:
                monotonic_score += 1
            elif mean_returns.iloc[i] > mean_returns.iloc[j]:
                monotonic_score -= 1
            total_pairs += 1
    
    return monotonic_score / total_pairs if total_pairs > 0 else 0


def compute_factor_quality_score(
    ic_mean: float,
    icir: float,
    sharpe: float,
    turnover: float = None,
    max_drawdown: float = None,
) -> float:
    """
    计算因子质量得分（简化版）
    
    快速评估因子质量的便捷函数。
    
    Args:
        ic_mean: IC均值
        icir: ICIR
        sharpe: 夏普比率
        turnover: 换手率（可选）
        max_drawdown: 最大回撤（可选）
    
    Returns:
        质量得分 (0-1)
    """
    score = 0.0
    
    if abs(ic_mean) >= 0.02:
        score += 0.25
    if abs(ic_mean) >= 0.05:
        score += 0.1
    
    if abs(icir) >= 0.5:
        score += 0.25
    if abs(icir) >= 1.0:
        score += 0.1
    
    if sharpe >= 1.0:
        score += 0.2
    if sharpe >= 2.0:
        score += 0.1
    
    if turnover is not None:
        if turnover < 0.5:
            score += 0.1
        elif turnover > 1.0:
            score -= 0.1
    
    if max_drawdown is not None:
        if max_drawdown > -0.1:
            score += 0.1
        elif max_drawdown < -0.3:
            score -= 0.1
    
    return min(max(score, 0), 1.0)
