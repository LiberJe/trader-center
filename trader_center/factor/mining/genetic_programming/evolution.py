"""
遗传规划进化引擎

实现因子挖掘的进化主循环。
"""

from typing import List, Dict, Any, Optional, Callable
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from pathlib import Path
import json

from .primitives import PrimitiveSet, create_default_pset
from .expression import FactorExpression, create_random_expression
from .fitness import FitnessEvaluator
from .genetic_operators import GeneticOperators, Selection, apply_genetic_operations

logger = logging.getLogger(__name__)


class GeneticProgrammingEngine:
    """
    遗传规划因子挖掘引擎
    
    通过进化算法自动挖掘有效因子。
    
    Example:
        engine = GeneticProgrammingEngine(
            price_df=price_data,
            data_dict=data,
            population_size=100,
            n_generations=50,
        )
        
        best_factors = engine.run()
        
        for factor in best_factors[:5]:
            print(f"{factor}: fitness={factor.fitness:.4f}")
    """
    
    def __init__(
        self,
        price_df: pd.DataFrame,
        data_dict: Dict[str, pd.DataFrame],
        pset: PrimitiveSet = None,
        population_size: int = 100,
        n_generations: int = 50,
        max_depth: int = 8,
        init_depth: int = 4,
        fitness_metric: str = 'ic_mean',
        crossover_prob: float = 0.8,
        mutation_prob: float = 0.2,
        elitism_size: int = 5,
        tournament_size: int = 3,
        selection_method: str = 'tournament',
        n_jobs: int = 1,
        verbose: int = 1,
        output_dir: str = None,
        seed: int = None,
    ):
        """
        初始化遗传规划引擎
        
        Args:
            price_df: 价格数据，index为日期，columns为资产代码
            data_dict: 数据字典，包含 open, high, low, close, volume 等
            pset: 基元集合，默认使用默认集合
            population_size: 种群大小
            n_generations: 进化代数
            max_depth: 表达式最大深度
            init_depth: 初始表达式深度
            fitness_metric: 适应度指标
            crossover_prob: 交叉概率
            mutation_prob: 变异概率
            elitism_size: 精英保留数量
            tournament_size: 锦标赛大小
            selection_method: 选择方法
            n_jobs: 并行数（暂不支持）
            verbose: 日志级别
            output_dir: 输出目录
            seed: 随机种子
        """
        if seed is not None:
            np.random.seed(seed)
            import random
            random.seed(seed)
        
        self.price_df = price_df
        self.data_dict = data_dict
        self.pset = pset or create_default_pset()
        
        self.population_size = population_size
        self.n_generations = n_generations
        self.max_depth = max_depth
        self.init_depth = init_depth
        
        self.fitness_evaluator = FitnessEvaluator(
            price_df=price_df,
            fitness_metric=fitness_metric,
        )
        
        self.operators = GeneticOperators(
            pset=self.pset,
            crossover_prob=crossover_prob,
            mutation_prob=mutation_prob,
            max_depth=max_depth,
        )
        
        self.elitism_size = elitism_size
        self.tournament_size = tournament_size
        self.selection_method = selection_method
        self.n_jobs = n_jobs
        self.verbose = verbose
        self.output_dir = Path(output_dir) if output_dir else None
        
        self.population: List[FactorExpression] = []
        self.history: List[Dict[str, Any]] = []
        self.best_individual: Optional[FactorExpression] = None
    
    def initialize_population(self) -> None:
        """初始化种群"""
        logger.info(f"初始化种群，大小: {self.population_size}")
        
        self.population = []
        for i in range(self.population_size):
            if i < self.population_size // 2:
                method = 'grow'
            else:
                method = 'full'
            
            expr = create_random_expression(
                self.pset,
                max_depth=self.init_depth,
                method=method,
            )
            self.population.append(expr)
        
        self._evaluate_population()
        
        logger.info("种群初始化完成")
    
    def _evaluate_population(self) -> None:
        """评估种群中所有个体的适应度"""
        for individual in self.population:
            fitness = self.fitness_evaluator.evaluate(individual, self.data_dict)
            individual.fitness = fitness
    
    def run(self) -> List[FactorExpression]:
        """
        运行进化算法
        
        Returns:
            排序后的因子列表（按适应度降序）
        """
        logger.info("=" * 60)
        logger.info("开始遗传规划因子挖掘")
        logger.info(f"种群大小: {self.population_size}, 进化代数: {self.n_generations}")
        logger.info("=" * 60)
        
        self.initialize_population()
        
        for gen in range(self.n_generations):
            self._evolve_one_generation(gen)
            
            if self.output_dir:
                self._save_generation_results(gen)
        
        self.population.sort(key=lambda x: x.fitness or -np.inf, reverse=True)
        
        self.best_individual = self.population[0] if self.population else None
        
        if self.output_dir:
            self._save_final_results()
        
        logger.info("=" * 60)
        logger.info("进化完成")
        logger.info(f"最佳因子: {self.best_individual}")
        logger.info(f"最佳适应度: {self.best_individual.fitness:.4f}" if self.best_individual else "无")
        logger.info("=" * 60)
        
        return self.population
    
    def _evolve_one_generation(self, generation: int) -> None:
        """进化一代"""
        self.population.sort(key=lambda x: x.fitness or -np.inf, reverse=True)
        
        best_fitness = self.population[0].fitness if self.population else -np.inf
        avg_fitness = np.mean([ind.fitness for ind in self.population if ind.fitness is not None])
        
        self.history.append({
            'generation': generation,
            'best_fitness': best_fitness,
            'avg_fitness': avg_fitness,
            'best_individual': str(self.population[0]) if self.population else None,
        })
        
        if self.verbose >= 1:
            logger.info(
                f"第 {generation + 1}/{self.n_generations} 代 | "
                f"最佳适应度: {best_fitness:.4f} | "
                f"平均适应度: {avg_fitness:.4f} | "
                f"最佳因子: {str(self.population[0])[:50]}..."
            )
        
        elites = Selection.elitism_selection(self.population, self.elitism_size)
        
        new_population = apply_genetic_operations(
            self.population,
            self.operators,
            selection_method=self.selection_method,
            tournament_size=self.tournament_size,
        )
        
        self._evaluate_population()
        
        new_population.sort(key=lambda x: x.fitness or -np.inf, reverse=True)
        
        self.population = elites + new_population[:self.population_size - self.elitism_size]
    
    def _save_generation_results(self, generation: int) -> None:
        """保存每代结果"""
        if not self.output_dir:
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        gen_file = self.output_dir / f"generation_{generation:04d}.json"
        with open(gen_file, 'w', encoding='utf-8') as f:
            json.dump({
                'generation': generation,
                'population': [
                    {
                        'expression': str(ind),
                        'fitness': ind.fitness,
                        'depth': ind.depth(),
                        'size': ind.size(),
                    }
                    for ind in sorted(self.population, key=lambda x: x.fitness or -np.inf, reverse=True)
                ]
            }, f, ensure_ascii=False, indent=2)
    
    def _save_final_results(self) -> None:
        """保存最终结果"""
        if not self.output_dir:
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = self.output_dir / "final_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'best_individual': str(self.best_individual) if self.best_individual else None,
                'best_fitness': self.best_individual.fitness if self.best_individual else None,
                'history': self.history,
                'top_factors': [
                    {
                        'expression': str(ind),
                        'fitness': ind.fitness,
                        'depth': ind.depth(),
                        'size': ind.size(),
                    }
                    for ind in self.population[:20]
                ]
            }, f, ensure_ascii=False, indent=2)
    
    def get_best_factors(self, top_n: int = 10) -> List[FactorExpression]:
        """获取最佳因子"""
        sorted_pop = sorted(self.population, key=lambda x: x.fitness or -np.inf, reverse=True)
        return sorted_pop[:top_n]
    
    def get_unique_factors(self, top_n: int = 10) -> List[FactorExpression]:
        """获取不重复的最佳因子"""
        seen = set()
        unique = []
        
        for ind in sorted(self.population, key=lambda x: x.fitness or -np.inf, reverse=True):
            expr_str = str(ind)
            if expr_str not in seen:
                seen.add(expr_str)
                unique.append(ind)
                if len(unique) >= top_n:
                    break
        
        return unique
    
    def get_evolution_history(self) -> pd.DataFrame:
        """获取进化历史"""
        return pd.DataFrame(self.history)


def run_factor_mining(
    price_df: pd.DataFrame,
    data_dict: Dict[str, pd.DataFrame],
    population_size: int = 100,
    n_generations: int = 50,
    max_depth: int = 8,
    fitness_metric: str = 'ic_mean',
    output_dir: str = None,
    seed: int = None,
    verbose: int = 1,
) -> List[FactorExpression]:
    """
    快速运行因子挖掘
    
    便捷函数，一键运行遗传规划因子挖掘。
    
    Args:
        price_df: 价格数据
        data_dict: 数据字典
        population_size: 种群大小
        n_generations: 进化代数
        max_depth: 最大深度
        fitness_metric: 适应度指标
        output_dir: 输出目录
        seed: 随机种子
        verbose: 日志级别
    
    Returns:
        排序后的因子列表
    
    Example:
        factors = run_factor_mining(
            price_df=close_prices,
            data_dict={'close': close_prices, 'volume': volumes},
            population_size=50,
            n_generations=20,
        )
        
        for factor in factors[:5]:
            print(f"{factor}: fitness={factor.fitness:.4f}")
    """
    engine = GeneticProgrammingEngine(
        price_df=price_df,
        data_dict=data_dict,
        population_size=population_size,
        n_generations=n_generations,
        max_depth=max_depth,
        fitness_metric=fitness_metric,
        output_dir=output_dir,
        seed=seed,
        verbose=verbose,
    )
    
    return engine.run()
