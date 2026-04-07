"""
遗传规划因子挖掘示例

演示如何使用遗传规划算法自动挖掘有效因子。
"""

import pandas as pd
import numpy as np
from pathlib import Path

from trader_center.factor.mining.genetic_programming import (
    GeneticProgrammingEngine,
    run_factor_mining,
    create_default_pset,
    FactorExpression,
)
from trader_center.factor.mining import FactorAnalysisPipeline


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'factor_research_results' / 'genetic_programming'


def create_sample_data(n_dates: int = 500, n_assets: int = 100) -> tuple:
    """
    创建示例数据
    
    Args:
        n_dates: 交易日数量
        n_assets: 资产数量
    
    Returns:
        (价格DataFrame, 数据字典)
    """
    np.random.seed(42)
    
    dates = pd.date_range('2022-01-01', periods=n_dates, freq='B')
    assets = [f'Stock_{i:03d}' for i in range(n_assets)]
    
    price_data = pd.DataFrame(
        np.random.randn(n_dates, n_assets).cumsum(axis=0) + 100,
        index=dates,
        columns=assets
    )
    
    volume_data = pd.DataFrame(
        np.random.randint(100000, 1000000, size=(n_dates, n_assets)),
        index=dates,
        columns=assets
    )
    
    high_data = price_data * (1 + np.random.rand(n_dates, n_assets) * 0.02)
    low_data = price_data * (1 - np.random.rand(n_dates, n_assets) * 0.02)
    open_data = price_data * (1 + (np.random.rand(n_dates, n_assets) - 0.5) * 0.01)
    
    vwap_data = (high_data + low_data + price_data) / 3
    
    returns_data = price_data.pct_change()
    log_returns_data = np.log(price_data / price_data.shift(1))
    
    data_dict = {
        'open': open_data,
        'high': high_data,
        'low': low_data,
        'close': price_data,
        'volume': volume_data,
        'vwap': vwap_data,
        'returns': returns_data,
        'log_returns': log_returns_data,
    }
    
    return price_data, data_dict


def example_1_quick_mining():
    """示例1: 快速因子挖掘"""
    print("\n" + "=" * 60)
    print("示例1: 快速因子挖掘")
    print("=" * 60)
    
    price_df, data_dict = create_sample_data(n_dates=252, n_assets=50)
    
    factors = run_factor_mining(
        price_df=price_df,
        data_dict=data_dict,
        population_size=30,
        n_generations=10,
        max_depth=6,
        fitness_metric='ic_mean',
        seed=42,
        verbose=1,
    )
    
    print("\n--- 最佳因子 Top 5 ---")
    for i, factor in enumerate(factors[:5], 1):
        print(f"{i}. {factor}")
        print(f"   适应度: {factor.fitness:.4f}")
        print(f"   深度: {factor.depth()}, 节点数: {factor.size()}")
        print()
    
    return factors


def example_2_full_engine():
    """示例2: 完整引擎配置"""
    print("\n" + "=" * 60)
    print("示例2: 完整引擎配置")
    print("=" * 60)
    
    price_df, data_dict = create_sample_data(n_dates=252, n_assets=50)
    
    engine = GeneticProgrammingEngine(
        price_df=price_df,
        data_dict=data_dict,
        population_size=50,
        n_generations=20,
        max_depth=8,
        init_depth=4,
        fitness_metric='icir',
        crossover_prob=0.8,
        mutation_prob=0.2,
        elitism_size=5,
        tournament_size=3,
        selection_method='tournament',
        seed=42,
        verbose=1,
        output_dir=str(OUTPUT_DIR / 'example_2'),
    )
    
    factors = engine.run()
    
    print("\n--- 进化历史 ---")
    history_df = engine.get_evolution_history()
    print(history_df.head(10))
    
    print("\n--- 最佳因子 ---")
    best = engine.best_individual
    if best:
        print(f"表达式: {best}")
        print(f"适应度: {best.fitness:.4f}")
    
    return engine


def example_3_custom_primitives():
    """示例3: 自定义基元"""
    print("\n" + "=" * 60)
    print("示例3: 自定义基元")
    print("=" * 60)
    
    from trader_center.factor.mining.genetic_programming import PrimitiveSet
    
    pset = PrimitiveSet()
    
    pset.add_terminal('close', '收盘价')
    pset.add_terminal('volume', '成交量')
    pset.add_terminal('returns', '收益率')
    
    def _my_custom_func(x):
        return x.rolling(10).mean() - x.rolling(20).mean()
    
    pset.add_function('my_ma_diff', _my_custom_func, 1, '自定义均线差')
    
    def _add(x, y):
        return x + y
    
    def _sub(x, y):
        return x - y
    
    def _mul(x, y):
        return x * y
    
    def _div(x, y):
        return x / y.replace(0, np.nan).fillna(0)
    
    pset.add_function('add', _add, 2, '加法')
    pset.add_function('sub', _sub, 2, '减法')
    pset.add_function('mul', _mul, 2, '乘法')
    pset.add_function('div', _div, 2, '除法')
    
    price_df, data_dict = create_sample_data(n_dates=252, n_assets=50)
    
    engine = GeneticProgrammingEngine(
        price_df=price_df,
        data_dict=data_dict,
        pset=pset,
        population_size=30,
        n_generations=10,
        seed=42,
        verbose=1,
    )
    
    factors = engine.run()
    
    print("\n--- 最佳因子 ---")
    for i, factor in enumerate(factors[:3], 1):
        print(f"{i}. {factor}")
    
    return factors


def example_4_validate_with_pipeline():
    """示例4: 使用因子评价流水线验证挖掘结果"""
    print("\n" + "=" * 60)
    print("示例4: 使用因子评价流水线验证挖掘结果")
    print("=" * 60)
    
    price_df, data_dict = create_sample_data(n_dates=252, n_assets=50)
    
    print("运行遗传规划挖掘...")
    factors = run_factor_mining(
        price_df=price_df,
        data_dict=data_dict,
        population_size=30,
        n_generations=10,
        fitness_metric='ic_mean',
        seed=42,
        verbose=1,
    )
    
    print("\n使用因子评价流水线验证最佳因子...")
    
    pipeline = FactorAnalysisPipeline(
        output_dir=str(OUTPUT_DIR / 'validation'),
        use_alphalens=False,
    )
    
    best_factor = factors[0]
    
    try:
        factor_values = best_factor.evaluate(data_dict)
        
        result = pipeline.run(
            factor_name=f'gp_factor_{hash(str(best_factor)) % 10000}',
            factor_df=factor_values,
            price_df=price_df,
            preprocessing=True,
            scoring=True,
            visualize=False,
            generate_report=False,
        )
        
        print("\n--- 因子评价结果 ---")
        print(f"IC均值: {result['summary'].get('ic_mean', 0):.4f}")
        print(f"ICIR: {result['summary'].get('icir', 0):.4f}")
        print(f"IC>0比例: {result['summary'].get('ic_positive_ratio', 0):.2%}")
        
        if 'score' in result:
            print(f"\n综合评分: {result['score']['total_score']:.2f}")
            print(f"评级: {result['score']['grade']}")
    
    except Exception as e:
        print(f"验证失败: {e}")
    
    return factors


def example_5_multi_objective():
    """示例5: 多目标优化"""
    print("\n" + "=" * 60)
    print("示例5: 多目标优化")
    print("=" * 60)
    
    price_df, data_dict = create_sample_data(n_dates=252, n_assets=50)
    
    metrics = ['ic_mean', 'icir', 'sharpe']
    results = {}
    
    for metric in metrics:
        print(f"\n--- 优化目标: {metric} ---")
        
        factors = run_factor_mining(
            price_df=price_df,
            data_dict=data_dict,
            population_size=30,
            n_generations=10,
            fitness_metric=metric,
            seed=42,
            verbose=0,
        )
        
        if factors:
            best = factors[0]
            results[metric] = {
                'expression': str(best),
                'fitness': best.fitness,
            }
            print(f"最佳因子: {best}")
            print(f"适应度: {best.fitness:.4f}")
    
    print("\n--- 多目标对比 ---")
    comparison_df = pd.DataFrame(results).T
    print(comparison_df)
    
    return results


def main():
    """运行所有示例"""
    print("=" * 60)
    print("遗传规划因子挖掘示例")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    example_1_quick_mining()
    
    example_2_full_engine()
    
    example_3_custom_primitives()
    
    example_4_validate_with_pipeline()
    
    example_5_multi_objective()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print(f"结果保存在: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
