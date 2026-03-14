"""
遗传规划因子生成器

使用遗传规划自动生成因子表达式。
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Callable
import logging
from concurrent.futures import ProcessPoolExecutor
import warnings

from .primitives import make_function_set, make_terminal_set, FUNCTION_MAP
from .expression import FactorExpression, ExpressionConverter, evaluate_expression

logger = logging.getLogger(__name__)

try:
    from gplearn.genetic import SymbolicTransformer
    from gplearn.functions import make_function
    from gplearn.fitness import make_fitness
    GPLEARN_AVAILABLE = True
except ImportError:
    GPLEARN_AVAILABLE = False
    warnings.warn("gplearn not installed. Install with: pip install gplearn")


class GPFactorGenerator:
    """
    基于遗传规划的因子生成器
    
    使用遗传规划自动搜索有效的因子表达式。
    
    Example:
        generator = GPFactorGenerator(
            population_size=1000,
            generations=20
        )
        
        factors = generator.generate(data, forward_returns, n_factors=10)
    """
    
    def __init__(
        self,
        population_size: int = 1000,
        generations: int = 20,
        tournament_size: int = 20,
        p_crossover: float = 0.7,
        p_mutation: float = 0.1,
        p_hoist_mutation: float = 0.05,
        p_point_mutation: float = 0.1,
        max_samples: float = 0.9,
        parsimony_coefficient: float = 0.001,
        const_range: Tuple[float, float] = (-1.0, 1.0),
        init_depth: Tuple[int, int] = (2, 6),
        init_method: str = 'half and half',
        function_set: Optional[List[str]] = None,
        terminal_set: Optional[List[str]] = None,
        n_jobs: int = 1,
        random_state: Optional[int] = None,
        verbose: int = 0,
    ):
        """
        初始化因子生成器
        
        Args:
            population_size: 种群大小
            generations: 迭代代数
            tournament_size: 锦标赛选择大小
            p_crossover: 交叉概率
            p_mutation: 子树变异概率
            p_hoist_mutation: 提升变异概率
            p_point_mutation: 点变异概率
            max_samples: 最大采样比例
            parsimony_coefficient: 简约系数（惩罚复杂表达式）
            const_range: 常数范围
            init_depth: 初始深度范围
            init_method: 初始化方法
            function_set: 函数集
            terminal_set: 终端集
            n_jobs: 并行数
            random_state: 随机种子
            verbose: 日志级别
        """
        if not GPLEARN_AVAILABLE:
            raise ImportError("gplearn is required. Install with: pip install gplearn")
        
        self.population_size = population_size
        self.generations = generations
        self.tournament_size = tournament_size
        self.p_crossover = p_crossover
        self.p_mutation = p_mutation
        self.p_hoist_mutation = p_hoist_mutation
        self.p_point_mutation = p_point_mutation
        self.max_samples = max_samples
        self.parsimony_coefficient = parsimony_coefficient
        self.const_range = const_range
        self.init_depth = init_depth
        self.init_method = init_method
        self.n_jobs = n_jobs
        self.random_state = random_state
        self.verbose = verbose
        
        self.function_set = function_set or self._build_function_set()
        self.terminal_set = terminal_set or make_terminal_set()
        
        self._model: Optional[Any] = None
        self._best_programs: List[Any] = []
    
    def _build_function_set(self) -> List:
        """构建gplearn函数集"""
        functions = []
        
        def make_np_func(np_func, name):
            def wrapper(*args):
                return np_func(*args)
            wrapper.__name__ = name
            return wrapper
        
        function_defs = make_function_set()
        
        for func, name, arity in function_defs:
            gp_func = make_function(function=func, name=name, arity=arity)
            functions.append(gp_func)
        
        return functions
    
    def _prepare_data(
        self,
        data: pd.DataFrame,
        forward_returns: pd.Series,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据
        
        Args:
            data: OHLCV数据
            forward_returns: 未来收益
        
        Returns:
            特征矩阵和目标向量
        """
        feature_names = self.terminal_set
        
        X_list = []
        for name in feature_names:
            if name in data.columns:
                X_list.append(data[name].values)
            elif name == 'vwap':
                vwap = (data['high'] + data['low'] + data['close']) / 3
                X_list.append(vwap.values)
            elif name == 'returns':
                returns = data['close'].pct_change().fillna(0)
                X_list.append(returns.values)
            else:
                X_list.append(np.zeros(len(data)))
        
        X = np.column_stack(X_list)
        
        if isinstance(forward_returns, pd.DataFrame):
            if forward_returns.shape[1] == 1:
                y = forward_returns.iloc[:, 0].values
            else:
                y = forward_returns.mean(axis=1).values
        elif isinstance(forward_returns, pd.Series):
            y = forward_returns.values
        else:
            y = np.array(forward_returns)
        
        if len(y) != len(X):
            min_len = min(len(X), len(y))
            X = X[:min_len]
            y = y[:min_len]
        
        valid_mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[valid_mask]
        y = y[valid_mask]
        
        return X, y
    
    @staticmethod
    def _ic_fitness(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
    ) -> float:
        """
        IC适应度函数
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            sample_weight: 样本权重
        
        Returns:
            IC值（取绝对值，越大越好）
        """
        from scipy.stats import spearmanr
        
        valid_mask = ~(np.isnan(y_pred) | np.isnan(y_true))
        if valid_mask.sum() < 10:
            return -np.inf
        
        y_pred_valid = y_pred[valid_mask]
        y_true_valid = y_true[valid_mask]
        
        try:
            ic, _ = spearmanr(y_pred_valid, y_true_valid)
            if np.isnan(ic):
                return -np.inf
            return abs(ic)
        except Exception:
            return -np.inf
    
    def generate(
        self,
        data: pd.DataFrame,
        forward_returns: pd.Series,
        n_factors: int = 10,
        metric: str = 'ic',
    ) -> List[FactorExpression]:
        """
        生成因子表达式
        
        Args:
            data: 包含OHLCV等数据的DataFrame
            forward_returns: 未来收益Series
            n_factors: 要生成的因子数量
            metric: 评估指标 ('ic', 'pearson')
        
        Returns:
            因子表达式列表
        """
        X, y = self._prepare_data(data, forward_returns)
        
        if metric == 'ic':
            fitness_func = make_fitness(
                function=self._ic_fitness,
                greater_is_better=True,
                wrap=False
            )
        else:
            from gplearn.fitness import _pearson_r
            fitness_func = _pearson_r
        
        self._model = SymbolicTransformer(
            feature_names=self.terminal_set,
            function_set=self.function_set,
            population_size=self.population_size,
            generations=self.generations,
            tournament_size=self.tournament_size,
            stopping_criteria=0.5,
            p_crossover=self.p_crossover,
            p_subtree_mutation=self.p_mutation,
            p_hoist_mutation=self.p_hoist_mutation,
            p_point_mutation=self.p_point_mutation,
            max_samples=self.max_samples,
            parsimony_coefficient=self.parsimony_coefficient,
            const_range=self.const_range,
            init_depth=self.init_depth,
            init_method=self.init_method,
            metric=fitness_func,
            n_jobs=self.n_jobs,
            random_state=self.random_state,
            verbose=self.verbose,
            hall_of_fame=n_factors,
        )
        
        logger.info(f"Starting GP factor generation with {self.population_size} population, {self.generations} generations")
        
        self._model.fit(X, y)
        
        self._best_programs = list(self._model._best_programs)
        
        factors = ExpressionConverter.batch_from_gplearn(self._best_programs)
        
        logger.info(f"Generated {len(factors)} factor expressions")
        
        return factors
    
    def evaluate_factor(
        self,
        factor_expr: FactorExpression,
        data: pd.DataFrame,
        forward_returns: pd.Series,
    ) -> Dict[str, float]:
        """
        评估单个因子
        
        Args:
            factor_expr: 因子表达式
            data: 数据
            forward_returns: 未来收益
        
        Returns:
            评估指标字典
        """
        from scipy.stats import spearmanr, pearsonr
        
        factor_values = evaluate_expression(factor_expr.expression_str, data)
        
        valid_mask = ~(factor_values.isna() | forward_returns.isna())
        factor_valid = factor_values[valid_mask]
        returns_valid = forward_returns[valid_mask]
        
        if len(factor_valid) < 10:
            return {'ic': np.nan, 'icir': np.nan, 'pearson': np.nan}
        
        ic, _ = spearmanr(factor_valid, returns_valid)
        pearson, _ = pearsonr(factor_valid, returns_valid)
        
        return {
            'ic': ic,
            'icir': abs(ic) / factor_valid.std() if factor_valid.std() > 0 else 0,
            'pearson': pearson,
        }
    
    def get_best_factors(
        self,
        top_n: int = 10,
        min_ic: float = 0.02,
    ) -> List[FactorExpression]:
        """
        获取最佳因子
        
        Args:
            top_n: 返回数量
            min_ic: 最小IC阈值
        
        Returns:
            最佳因子列表
        """
        if not self._best_programs:
            return []
        
        factors = ExpressionConverter.batch_from_gplearn(self._best_programs)
        
        valid_factors = [f for f in factors if f.fitness is not None and f.fitness >= min_ic]
        
        valid_factors.sort(key=lambda x: x.fitness if x.fitness is not None else -np.inf, reverse=True)
        
        return valid_factors[:top_n]
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        if self._model is None:
            return {'status': 'not_fitted'}
        
        return {
            'status': 'fitted',
            'population_size': self.population_size,
            'generations': self.generations,
            'n_best_programs': len(self._best_programs),
            'best_fitness': max([p.fitness_ for p in self._best_programs]) if self._best_programs else None,
        }


class SimpleFactorGenerator:
    """
    简单因子生成器
    
    不依赖gplearn，使用预定义模板生成因子。
    """
    
    def __init__(self):
        """初始化简单因子生成器"""
        self.templates = self._build_templates()
    
    def _build_templates(self) -> List[str]:
        """构建因子模板"""
        templates = [
            "ts_delta(close, {window})",
            "ts_mean(close, {window}) / close",
            "ts_std(close, {window}) / close",
            "ts_rank(close, {window})",
            "(close - ts_min(low, {window})) / (ts_max(high, {window}) - ts_min(low, {window}))",
            "volume / ts_mean(volume, {window})",
            "ts_delta(close, {window}) / ts_std(close, {window})",
            "rank(close / ts_mean(close, {window}))",
            "ts_mean(volume, {window}) / ts_mean(volume, {window2})",
            "(high - low) / close",
            "abs(ts_delta(close, {window})) / volume",
            "ts_rank(volume, {window}) * ts_delta(close, {window})",
            "log(close) - log(ts_mean(close, {window}))",
            "sign(ts_delta(close, {window})) * abs(ts_delta(volume, {window}))",
            "ts_sum(volume, {window}) / ts_sum(amount, {window})",
        ]
        return templates
    
    def generate(
        self,
        windows: Optional[List[int]] = None,
        n_factors: int = 50,
    ) -> List[FactorExpression]:
        """
        生成因子表达式
        
        Args:
            windows: 窗口大小列表
            n_factors: 生成数量
        
        Returns:
            因子表达式列表
        """
        windows = windows or [5, 10, 20, 60]
        factors = []
        
        for template in self.templates:
            for w1 in windows:
                if '{window2}' in template:
                    for w2 in windows:
                        if w1 != w2:
                            expr = template.format(window=w1, window2=w2)
                            factors.append(FactorExpression(expression_str=expr))
                else:
                    expr = template.format(window=w1)
                    factors.append(FactorExpression(expression_str=expr))
                
                if len(factors) >= n_factors:
                    return factors
        
        return factors


def generate_factors_from_data(
    data: pd.DataFrame,
    forward_returns: pd.Series,
    method: str = 'gp',
    n_factors: int = 10,
    **kwargs,
) -> List[FactorExpression]:
    """
    从数据生成因子
    
    Args:
        data: 数据
        forward_returns: 未来收益
        method: 生成方法 ('gp' 或 'simple')
        n_factors: 生成数量
        **kwargs: 其他参数
    
    Returns:
        因子表达式列表
    """
    if method == 'gp':
        generator = GPFactorGenerator(**kwargs)
        return generator.generate(data, forward_returns, n_factors)
    else:
        generator = SimpleFactorGenerator()
        return generator.generate(n_factors=n_factors)
