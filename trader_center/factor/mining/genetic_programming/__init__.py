"""
遗传规划因子挖掘模块

通过遗传规划算法自动挖掘有效因子。

主要组件:
- PrimitiveSet: 基元集合，定义可用的操作符和数据
- FactorExpression: 因子表达式，表示一个因子公式
- FitnessEvaluator: 适应度评估器
- GeneticOperators: 遗传操作（交叉、变异、选择）
- GeneticProgrammingEngine: 进化引擎

快速使用:
    from trader_center.factor.mining.genetic_programming import run_factor_mining
    
    factors = run_factor_mining(
        price_df=close_prices,
        data_dict={'close': close_prices, 'volume': volumes},
        population_size=50,
        n_generations=20,
    )
    
    for factor in factors[:5]:
        print(f"{factor}: fitness={factor.fitness:.4f}")
"""

from .primitives import (
    Primitive,
    PrimitiveSet,
    PrimitiveType,
    create_default_pset,
)

from .expression import (
    ExpressionNode,
    FactorExpression,
    create_random_expression,
)

from .fitness import (
    FitnessEvaluator,
    MultiObjectiveFitness,
)

from .genetic_operators import (
    GeneticOperators,
    Selection,
    apply_genetic_operations,
)

from .evolution import (
    GeneticProgrammingEngine,
    run_factor_mining,
)

__all__ = [
    'Primitive',
    'PrimitiveSet',
    'PrimitiveType',
    'create_default_pset',
    'ExpressionNode',
    'FactorExpression',
    'create_random_expression',
    'FitnessEvaluator',
    'MultiObjectiveFitness',
    'GeneticOperators',
    'Selection',
    'apply_genetic_operations',
    'GeneticProgrammingEngine',
    'run_factor_mining',
]
