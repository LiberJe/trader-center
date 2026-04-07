"""
适应度评估

集成因子评价系统，评估因子表达式的优劣。
"""

from typing import Dict, Any, Optional, Callable
import pandas as pd
import numpy as np
import logging

from .expression import FactorExpression

logger = logging.getLogger(__name__)


class FitnessEvaluator:
    """
    适应度评估器
    
    评估因子表达式的适应度，集成因子评价系统。
    
    Example:
        evaluator = FitnessEvaluator(price_df)
        fitness = evaluator.evaluate(expression, data)
    """
    
    def __init__(
        self,
        price_df: pd.DataFrame,
        fitness_metric: str = 'ic_mean',
        penalize_complexity: bool = True,
        complexity_penalty: float = 0.001,
        min_periods: int = 60,
    ):
        """
        初始化适应度评估器
        
        Args:
            price_df: 价格数据，index为日期，columns为资产代码
            fitness_metric: 适应度指标，可选:
                - 'ic_mean': IC均值
                - 'icir': ICIR
                - 'sharpe': 因子夏普比率
                - 'combined': 综合得分
            penalize_complexity: 是否惩罚复杂度
            complexity_penalty: 复杂度惩罚系数
            min_periods: 最小数据期数
        """
        self.price_df = price_df
        self.fitness_metric = fitness_metric
        self.penalize_complexity = penalize_complexity
        self.complexity_penalty = complexity_penalty
        self.min_periods = min_periods
        
        self._forward_returns = price_df.pct_change().shift(-1)
        
        self._cache: Dict[str, float] = {}
    
    def evaluate(
        self,
        expression: FactorExpression,
        data: Dict[str, pd.DataFrame],
    ) -> float:
        """
        评估因子表达式的适应度
        
        Args:
            expression: 因子表达式
            data: 数据字典
        
        Returns:
            适应度值（越大越好）
        """
        expr_str = str(expression)
        if expr_str in self._cache:
            return self._cache[expr_str]
        
        try:
            factor_values = expression.evaluate(data)
            
            if factor_values is None or len(factor_values) == 0:
                return -np.inf
            
            if isinstance(factor_values, pd.Series):
                factor_df = factor_values.to_frame()
            else:
                factor_df = factor_values
            
            if len(factor_df) < self.min_periods:
                return -np.inf
            
            factor_df = factor_df.dropna(how='all')
            
            if len(factor_df) < self.min_periods:
                return -np.inf
            
            fitness = self._compute_fitness(factor_df)
            
            if self.penalize_complexity:
                complexity = expression.size()
                fitness -= self.complexity_penalty * complexity
            
            self._cache[expr_str] = fitness
            
            return fitness
            
        except Exception as e:
            logger.debug(f"评估因子失败: {e}")
            return -np.inf
    
    def _compute_fitness(self, factor_df: pd.DataFrame) -> float:
        """计算适应度"""
        if self.fitness_metric == 'ic_mean':
            return self._compute_ic_mean(factor_df)
        elif self.fitness_metric == 'icir':
            return self._compute_icir(factor_df)
        elif self.fitness_metric == 'sharpe':
            return self._compute_sharpe(factor_df)
        elif self.fitness_metric == 'combined':
            return self._compute_combined(factor_df)
        else:
            return self._compute_ic_mean(factor_df)
    
    def _compute_ic_mean(self, factor_df: pd.DataFrame) -> float:
        """计算IC均值"""
        ic_series = self._compute_ic_series(factor_df)
        if ic_series is None or len(ic_series) == 0:
            return -np.inf
        return abs(ic_series.mean())
    
    def _compute_icir(self, factor_df: pd.DataFrame) -> float:
        """计算ICIR"""
        ic_series = self._compute_ic_series(factor_df)
        if ic_series is None or len(ic_series) == 0:
            return -np.inf
        
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        
        if ic_std == 0 or np.isnan(ic_std):
            return -np.inf
        
        return abs(ic_mean / ic_std)
    
    def _compute_sharpe(self, factor_df: pd.DataFrame) -> float:
        """计算因子夏普比率"""
        try:
            factor_rank = factor_df.rank(axis=1, pct=True)
            
            long_portfolio = factor_rank >= 0.8
            short_portfolio = factor_rank <= 0.2
            
            long_returns = (long_portfolio * self._forward_returns).mean(axis=1)
            short_returns = (short_portfolio * self._forward_returns).mean(axis=1)
            
            ls_returns = long_returns - short_returns
            ls_returns = ls_returns.dropna()
            
            if len(ls_returns) < self.min_periods:
                return -np.inf
            
            mean_return = ls_returns.mean()
            std_return = ls_returns.std()
            
            if std_return == 0 or np.isnan(std_return):
                return -np.inf
            
            return abs(mean_return / std_return)
            
        except Exception:
            return -np.inf
    
    def _compute_combined(self, factor_df: pd.DataFrame) -> float:
        """计算综合得分"""
        ic_mean = self._compute_ic_mean(factor_df)
        icir = self._compute_icir(factor_df)
        sharpe = self._compute_sharpe(factor_df)
        
        score = 0.0
        
        if ic_mean > 0.02:
            score += 0.3
        if ic_mean > 0.05:
            score += 0.1
        
        if icir > 0.5:
            score += 0.3
        if icir > 1.0:
            score += 0.1
        
        if sharpe > 1.0:
            score += 0.2
        
        return score
    
    def _compute_ic_series(self, factor_df: pd.DataFrame) -> Optional[pd.Series]:
        """计算IC序列"""
        try:
            ic_list = []
            dates = factor_df.index.intersection(self._forward_returns.index)
            
            for date in dates:
                factor_vals = factor_df.loc[date].dropna()
                return_vals = self._forward_returns.loc[date].dropna()
                
                common_assets = factor_vals.index.intersection(return_vals.index)
                
                if len(common_assets) < 10:
                    ic_list.append(np.nan)
                    continue
                
                ic = factor_vals[common_assets].corr(
                    return_vals[common_assets],
                    method='spearman'
                )
                ic_list.append(ic)
            
            return pd.Series(ic_list, index=dates)
            
        except Exception:
            return None
    
    def evaluate_batch(
        self,
        expressions: list,
        data: Dict[str, pd.DataFrame],
        n_jobs: int = 1,
    ) -> Dict[str, float]:
        """
        批量评估因子表达式
        
        Args:
            expressions: 因子表达式列表
            data: 数据字典
            n_jobs: 并行数（暂不支持）
        
        Returns:
            表达式字符串到适应度的映射
        """
        results = {}
        for expr in expressions:
            fitness = self.evaluate(expr, data)
            results[str(expr)] = fitness
        return results
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class MultiObjectiveFitness:
    """
    多目标适应度评估
    
    支持同时优化多个目标（如IC、ICIR、夏普）。
    """
    
    def __init__(
        self,
        price_df: pd.DataFrame,
        objectives: list = None,
        weights: list = None,
    ):
        """
        初始化多目标适应度评估器
        
        Args:
            price_df: 价格数据
            objectives: 目标列表 ['ic_mean', 'icir', 'sharpe']
            weights: 权重列表
        """
        self.price_df = price_df
        self.objectives = objectives or ['ic_mean', 'icir']
        self.weights = weights or [0.5, 0.5]
        
        self._evaluators = {
            obj: FitnessEvaluator(price_df, fitness_metric=obj)
            for obj in self.objectives
        }
    
    def evaluate(
        self,
        expression: FactorExpression,
        data: Dict[str, pd.DataFrame],
    ) -> Dict[str, float]:
        """
        评估多个目标
        
        Returns:
            各目标的适应度值
        """
        results = {}
        for obj, evaluator in self._evaluators.items():
            results[obj] = evaluator.evaluate(expression, data)
        return results
    
    def get_weighted_fitness(
        self,
        scores: Dict[str, float],
    ) -> float:
        """计算加权适应度"""
        total = 0.0
        for obj, weight in zip(self.objectives, self.weights):
            if obj in scores and scores[obj] != -np.inf:
                total += weight * scores[obj]
        return total
