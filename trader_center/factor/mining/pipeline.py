"""
因子挖掘流水线

提供完整的因子挖掘流程，包括数据准备、因子生成、评估、筛选和输出。
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
import logging
from datetime import datetime
import json

from .gp.factor_generator import GPFactorGenerator, SimpleFactorGenerator
from .gp.expression import FactorExpression, evaluate_expression
from .evaluator import FactorEvaluator, FactorReport, FactorMetrics
from .preprocessing.standardization import standardize_cross_sectional
from .preprocessing.winsorization import winsorize_cross_sectional
from .engine import FactorEngine
from .ic_analysis import ICAnalyzer
from .layering import LayeringAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class MiningConfig:
    """挖掘配置"""
    population_size: int = 1000
    generations: int = 20
    n_factors_to_generate: int = 50
    n_factors_to_select: int = 10
    
    min_ic: float = 0.02
    min_icir: float = 0.5
    max_correlation: float = 0.7
    min_monotonicity: float = 0.3
    
    preprocessing_steps: List[str] = field(default_factory=lambda: ['winsorize', 'standardize'])
    
    method: str = 'gp'
    
    n_jobs: int = 1
    random_state: Optional[int] = None
    verbose: int = 1


@dataclass
class MiningResult:
    """挖掘结果"""
    config: MiningConfig
    generated_factors: List[FactorExpression] = field(default_factory=list)
    selected_factors: List[FactorExpression] = field(default_factory=list)
    report: Optional[FactorReport] = None
    metrics_df: Optional[pd.DataFrame] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def summary(self) -> str:
        """生成摘要"""
        lines = [
            "=" * 60,
            "因子挖掘结果摘要",
            "=" * 60,
            f"挖掘方法: {self.config.method}",
            f"生成因子数: {len(self.generated_factors)}",
            f"筛选因子数: {len(self.selected_factors)}",
            f"耗时: {(self.end_time - self.start_time).total_seconds():.2f}秒" if self.start_time and self.end_time else "",
            "",
        ]
        
        if self.selected_factors:
            lines.append("筛选出的因子:")
            for i, f in enumerate(self.selected_factors[:10], 1):
                lines.append(f"  {i}. {f.name}: {f.expression_str[:50]}...")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'config': {
                'population_size': self.config.population_size,
                'generations': self.config.generations,
                'n_factors_to_generate': self.config.n_factors_to_generate,
                'n_factors_to_select': self.config.n_factors_to_select,
                'method': self.config.method,
            },
            'generated_count': len(self.generated_factors),
            'selected_count': len(self.selected_factors),
            'selected_factors': [
                {
                    'name': f.name,
                    'expression': f.expression_str,
                    'fitness': f.fitness,
                }
                for f in self.selected_factors
            ],
            'start_time': str(self.start_time) if self.start_time else None,
            'end_time': str(self.end_time) if self.end_time else None,
        }
    
    def save(self, filepath: str) -> None:
        """保存结果到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"结果已保存到: {filepath}")
    
    def register_factors(self) -> None:
        """将筛选的因子注册到因子库"""
        from trader_center.factor.library.registry import register_factor
        
        for factor_expr in self.selected_factors:
            factor = factor_expr.to_factor()
            register_factor(factor)
        
        logger.info(f"已注册 {len(self.selected_factors)} 个因子")


class FactorMiningPipeline:
    """
    因子挖掘流水线
    
    提供完整的因子挖掘流程。
    
    Example:
        pipeline = FactorMiningPipeline(config=MiningConfig())
        result = pipeline.run(data, forward_returns)
        print(result.summary())
    """
    
    def __init__(
        self,
        config: Optional[MiningConfig] = None,
        generator: Optional[Union[GPFactorGenerator, SimpleFactorGenerator]] = None,
        evaluator: Optional[FactorEvaluator] = None,
    ):
        """
        初始化流水线
        
        Args:
            config: 挖掘配置
            generator: 因子生成器
            evaluator: 因子评估器
        """
        self.config = config or MiningConfig()
        
        if generator is not None:
            self.generator = generator
        elif self.config.method == 'gp':
            self.generator = GPFactorGenerator(
                population_size=self.config.population_size,
                generations=self.config.generations,
                n_jobs=self.config.n_jobs,
                random_state=self.config.random_state,
                verbose=self.config.verbose,
            )
        else:
            self.generator = SimpleFactorGenerator()
        
        self.evaluator = evaluator or FactorEvaluator(n_jobs=self.config.n_jobs)
    
    def run(
        self,
        data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> MiningResult:
        """
        运行因子挖掘流程
        
        Args:
            data: 包含OHLCV等数据的DataFrame
            forward_returns: 未来收益DataFrame
            progress_callback: 进度回调函数
        
        Returns:
            挖掘结果
        """
        result = MiningResult(
            config=self.config,
            start_time=datetime.now(),
        )
        
        if progress_callback:
            progress_callback("开始因子生成", 0)
        
        logger.info("Step 1: 生成因子表达式")
        if isinstance(self.generator, GPFactorGenerator):
            generated_factors = self.generator.generate(
                data,
                forward_returns.iloc[:, 0] if forward_returns.shape[1] == 1 else forward_returns.mean(axis=1),
                n_factors=self.config.n_factors_to_generate,
            )
        else:
            generated_factors = self.generator.generate(
                n_factors=self.config.n_factors_to_generate,
            )
        
        result.generated_factors = generated_factors
        logger.info(f"生成了 {len(generated_factors)} 个因子表达式")
        
        if progress_callback:
            progress_callback("因子评估", 30)
        
        logger.info("Step 2: 评估因子")
        report = self.evaluator.evaluate(
            factors=generated_factors,
            data=data,
            forward_returns=forward_returns,
        )
        result.report = report
        result.metrics_df = report.to_dataframe()
        
        if progress_callback:
            progress_callback("因子筛选", 60)
        
        logger.info("Step 3: 筛选因子")
        filtered_metrics = self.evaluator.filter_factors(
            report.metrics,
            min_ic=self.config.min_ic,
            min_icir=self.config.min_icir,
            max_correlation=self.config.max_correlation,
            min_monotonicity=self.config.min_monotonicity,
        )
        
        selected_names = {m.factor_name for m in filtered_metrics}
        result.selected_factors = [
            f for f in generated_factors if f.name in selected_names
        ]
        
        result.selected_factors = result.selected_factors[:self.config.n_factors_to_select]
        
        if progress_callback:
            progress_callback("完成", 100)
        
        result.end_time = datetime.now()
        
        logger.info(f"筛选出 {len(result.selected_factors)} 个因子")
        
        return result
    
    def run_with_universe(
        self,
        data_dict: Dict[str, pd.DataFrame],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        forward_period: int = 5,
    ) -> MiningResult:
        """
        对股票池运行因子挖掘
        
        Args:
            data_dict: 股票代码到数据的映射
            start_date: 开始日期
            end_date: 结束日期
            forward_period: 未来收益周期
        
        Returns:
            挖掘结果
        """
        combined_data = self._combine_data(data_dict)
        
        forward_returns = self._compute_forward_returns(
            data_dict,
            forward_period,
            start_date,
            end_date,
        )
        
        return self.run(combined_data, forward_returns)
    
    def _combine_data(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """合并多股票数据"""
        all_data = []
        for symbol, df in data_dict.items():
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            all_data.append(df_copy)
        
        return pd.concat(all_data, axis=0)
    
    def _compute_forward_returns(
        self,
        data_dict: Dict[str, pd.DataFrame],
        period: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """计算未来收益"""
        returns_dict = {}
        
        for symbol, df in data_dict.items():
            forward_return = df['close'].pct_change(period).shift(-period)
            returns_dict[symbol] = forward_return
        
        returns_df = pd.DataFrame(returns_dict)
        
        if start_date:
            returns_df = returns_df.loc[start_date:]
        if end_date:
            returns_df = returns_df.loc[:end_date]
        
        return returns_df


def run_factor_mining(
    data: pd.DataFrame,
    forward_returns: pd.DataFrame,
    method: str = 'gp',
    n_factors: int = 10,
    min_ic: float = 0.02,
    min_icir: float = 0.5,
    **kwargs,
) -> MiningResult:
    """
    快速运行因子挖掘
    
    Args:
        data: 数据
        forward_returns: 未来收益
        method: 方法 ('gp' 或 'simple')
        n_factors: 生成因子数量
        min_ic: 最小IC
        min_icir: 最小ICIR
        **kwargs: 其他参数
    
    Returns:
        挖掘结果
    """
    config = MiningConfig(
        method=method,
        n_factors_to_generate=n_factors * 5,
        n_factors_to_select=n_factors,
        min_ic=min_ic,
        min_icir=min_icir,
        **kwargs,
    )
    
    pipeline = FactorMiningPipeline(config=config)
    return pipeline.run(data, forward_returns)
