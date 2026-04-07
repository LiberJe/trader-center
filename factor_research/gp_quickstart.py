"""
遗传规划因子挖掘快速入门

这是一个简化的示例，展示如何快速开始使用遗传规划挖掘因子。
"""

import pandas as pd
import numpy as np
from trader_center.factor.mining import run_factor_mining, FactorAnalysisPipeline


def quick_start():
    """
    快速开始示例
    
    展示最简单的因子挖掘流程。
    """
    print("=" * 60)
    print("遗传规划因子挖掘 - 快速入门")
    print("=" * 60)
    
    print("\n步骤1: 准备数据...")
    np.random.seed(42)
    
    n_dates = 252
    n_assets = 50
    dates = pd.date_range('2023-01-01', periods=n_dates, freq='B')
    assets = [f'Stock_{i:03d}' for i in range(n_assets)]
    
    close = pd.DataFrame(
        np.random.randn(n_dates, n_assets).cumsum(axis=0) + 100,
        index=dates,
        columns=assets
    )
    
    volume = pd.DataFrame(
        np.random.randint(100000, 1000000, size=(n_dates, n_assets)),
        index=dates,
        columns=assets
    )
    
    returns = close.pct_change()
    
    data_dict = {
        'close': close,
        'volume': volume,
        'returns': returns,
    }
    
    print(f"数据准备完成: {n_dates}天, {n_assets}只股票")
    
    print("\n步骤2: 运行遗传规划挖掘...")
    print("种群大小: 30, 进化代数: 10")
    
    factors = run_factor_mining(
        price_df=close,
        data_dict=data_dict,
        population_size=30,
        n_generations=10,
        max_depth=6,
        fitness_metric='ic_mean',
        seed=42,
        verbose=1,
    )
    
    print("\n步骤3: 查看挖掘结果...")
    print("\n最佳因子 Top 5:")
    print("-" * 60)
    
    for i, factor in enumerate(factors[:5], 1):
        print(f"\n{i}. 因子表达式:")
        print(f"   {factor}")
        print(f"   适应度: {factor.fitness:.4f}")
        print(f"   深度: {factor.depth()}, 节点数: {factor.size()}")
    
    print("\n步骤4: 验证最佳因子...")
    best_factor = factors[0]
    
    try:
        factor_values = best_factor.evaluate(data_dict)
        
        pipeline = FactorAnalysisPipeline(use_alphalens=False)
        result = pipeline.run(
            factor_name='gp_best_factor',
            factor_df=factor_values,
            price_df=close,
            preprocessing=True,
            scoring=True,
            visualize=False,
        )
        
        print("\n因子评价结果:")
        print(f"  IC均值: {result['summary'].get('ic_mean', 0):.4f}")
        print(f"  ICIR: {result['summary'].get('icir', 0):.4f}")
        print(f"  IC>0比例: {result['summary'].get('ic_positive_ratio', 0):.2%}")
        
        if 'score' in result:
            print(f"  综合评分: {result['score']['total_score']:.2f}")
            print(f"  评级: {result['score']['grade']}")
    
    except Exception as e:
        print(f"验证失败: {e}")
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    
    return factors


def advanced_usage():
    """
    高级用法示例
    
    展示如何自定义参数和基元。
    """
    print("\n" + "=" * 60)
    print("高级用法 - 自定义配置")
    print("=" * 60)
    
    from trader_center.factor.mining import GeneticProgrammingEngine, PrimitiveSet
    
    np.random.seed(42)
    
    n_dates = 252
    n_assets = 50
    dates = pd.date_range('2023-01-01', periods=n_dates, freq='B')
    assets = [f'Stock_{i:03d}' for i in range(n_assets)]
    
    close = pd.DataFrame(
        np.random.randn(n_dates, n_assets).cumsum(axis=0) + 100,
        index=dates,
        columns=assets
    )
    
    volume = pd.DataFrame(
        np.random.randint(100000, 1000000, size=(n_dates, n_assets)),
        index=dates,
        columns=assets
    )
    
    data_dict = {
        'close': close,
        'volume': volume,
    }
    
    print("\n配置1: 优化ICIR...")
    engine1 = GeneticProgrammingEngine(
        price_df=close,
        data_dict=data_dict,
        population_size=50,
        n_generations=20,
        fitness_metric='icir',
        seed=42,
        verbose=1,
    )
    factors1 = engine1.run()
    
    print(f"\n最佳因子(ICIR优化): {factors1[0]}")
    print(f"适应度: {factors1[0].fitness:.4f}")
    
    print("\n配置2: 优化夏普比率...")
    engine2 = GeneticProgrammingEngine(
        price_df=close,
        data_dict=data_dict,
        population_size=50,
        n_generations=20,
        fitness_metric='sharpe',
        seed=42,
        verbose=1,
    )
    factors2 = engine2.run()
    
    print(f"\n最佳因子(夏普优化): {factors2[0]}")
    print(f"适应度: {factors2[0].fitness:.4f}")
    
    return factors1, factors2


if __name__ == "__main__":
    quick_start()
