"""
因子分析流水线使用示例

演示如何使用因子分析流水线进行因子评估。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)


def create_sample_data(n_dates: int = 252, n_assets: int = 100) -> tuple:
    """
    创建示例数据
    
    Args:
        n_dates: 交易日数量
        n_assets: 资产数量
    
    Returns:
        (价格DataFrame, 因子DataFrame字典)
    """
    dates = pd.date_range('2023-01-01', periods=n_dates, freq='B')
    assets = [f'Asset_{i:03d}' for i in range(n_assets)]
    
    price_data = pd.DataFrame(
        np.random.randn(n_dates, n_assets).cumsum(axis=0) + 100,
        index=dates,
        columns=assets
    )
    
    momentum_20 = price_data.pct_change(20)
    
    returns = price_data.pct_change()
    volatility_20 = returns.rolling(20).std()
    
    ma_20 = price_data.rolling(20).mean()
    price_ma_ratio = price_data / ma_20
    
    factor_data = {
        'momentum_20': momentum_20,
        'volatility_20': volatility_20,
        'price_ma_ratio': price_ma_ratio,
    }
    
    return price_data, factor_data


def example_1_quick_analyze():
    """示例1: 快速因子分析"""
    print("\n" + "=" * 60)
    print("示例1: 快速因子分析 (quick_analyze)")
    print("=" * 60)
    
    from trader_center.factor.mining import quick_analyze
    
    price_data, factor_data = create_sample_data()
    
    result = quick_analyze(
        factor_df=factor_data['momentum_20'],
        price_df=price_data,
        factor_name='momentum_20',
        show_tear_sheet=False,
    )
    
    print(f"\nIC均值: {result['summary']['ic_mean']:.4f}")
    print(f"ICIR: {result['summary']['icir']:.4f}")
    print(f"IC>0比例: {result['summary']['ic_positive_ratio']:.2%}")
    
    if 'score' in result:
        print(f"\n综合评分: {result['score']['total_score']:.2f}")
        print(f"评级: {result['score']['grade']}")
    
    plt.show()


def example_2_full_pipeline():
    """示例2: 完整流水线分析"""
    print("\n" + "=" * 60)
    print("示例2: 完整流水线分析 (FactorAnalysisPipeline)")
    print("=" * 60)
    
    from trader_center.factor.mining import FactorAnalysisPipeline
    
    price_data, factor_data = create_sample_data()
    
    pipeline = FactorAnalysisPipeline(
        output_dir='./factor_analysis_output',
        use_alphalens=False,
    )
    
    result = pipeline.run(
        factor_name='momentum_20',
        factor_df=factor_data['momentum_20'],
        price_df=price_data,
        preprocessing=True,
        scoring=True,
        visualize=True,
        generate_report=False,
    )
    
    print(f"\n因子名称: {result['factor_name']}")
    print(f"IC均值: {result['summary']['ic_mean']:.4f}")
    print(f"ICIR: {result['summary']['icir']:.4f}")
    print(f"因子收益均值: {result['summary'].get('factor_return_mean', 0):.4f}")
    print(f"因子夏普: {result['summary'].get('factor_sharpe', 0):.4f}")
    
    if 'score' in result:
        print(f"\n--- 评分 ---")
        print(f"IC有效性得分: {result['score']['ic_score']:.2f}")
        print(f"收益贡献得分: {result['score']['return_score']:.2f}")
        print(f"稳定性得分: {result['score']['stability_score']:.2f}")
        print(f"独立性得分: {result['score']['independence_score']:.2f}")
        print(f"综合评分: {result['score']['total_score']:.2f}")
        print(f"评级: {result['score']['grade']}")
    
    plt.show()


def example_3_batch_analysis():
    """示例3: 批量因子分析"""
    print("\n" + "=" * 60)
    print("示例3: 批量因子分析 (run_batch)")
    print("=" * 60)
    
    from trader_center.factor.mining import FactorAnalysisPipeline
    
    price_data, factor_data = create_sample_data()
    
    pipeline = FactorAnalysisPipeline(
        output_dir='./factor_analysis_output',
        use_alphalens=False,
    )
    
    results = pipeline.run_batch(
        factor_names=['momentum_20', 'volatility_20', 'price_ma_ratio'],
        factor_data_dict=factor_data,
        price_df=price_data,
        preprocessing=True,
        scoring=True,
        visualize=False,
    )
    
    print(f"\n批量分析完成，共 {len(results)} 个因子")
    
    summary = pipeline.get_summary()
    print("\n--- 因子摘要 ---")
    print(summary)
    
    ranking = pipeline.get_ranking()
    print("\n--- 因子排名 ---")
    print(ranking)
    
    plt.show()


def example_4_with_alphalens():
    """示例4: 使用Alphalens进行分析"""
    print("\n" + "=" * 60)
    print("示例4: 使用Alphalens进行分析")
    print("=" * 60)
    
    try:
        from trader_center.factor.mining import FactorAnalysisPipeline, check_alphalens_available
        
        if not check_alphalens_available():
            print("Alphalens未安装，跳过此示例")
            return
        
        price_data, factor_data = create_sample_data()
        
        pipeline = FactorAnalysisPipeline(
            output_dir='./factor_analysis_output',
            use_alphalens=True,
        )
        
        result = pipeline.run(
            factor_name='momentum_20',
            factor_df=factor_data['momentum_20'],
            price_df=price_data,
            preprocessing=True,
            use_alphalens_analysis=True,
            scoring=True,
            visualize=True,
            show_plots=False,
            generate_report=False,
        )
        
        print(f"\nIC均值: {result['summary']['ic_mean']:.4f}")
        print(f"ICIR: {result['summary']['icir']:.4f}")
        
        if 'score' in result:
            print(f"综合评分: {result['score']['total_score']:.2f}")
            print(f"评级: {result['score']['grade']}")
        
        plt.show()
        
    except ImportError as e:
        print(f"Alphalens导入失败: {e}")


def example_5_custom_factor_analysis():
    """示例5: 自定义因子分析流程"""
    print("\n" + "=" * 60)
    print("示例5: 自定义因子分析流程")
    print("=" * 60)
    
    from trader_center.factor.mining import (
        FactorAnalysisPipeline,
        FactorScorer,
        FactorVisualizer,
    )
    
    price_data, factor_data = create_sample_data()
    
    pipeline = FactorAnalysisPipeline(
        preprocessing_config={
            'winsorize': {'method': 'mad', 'threshold': 3.0},
            'standardize': {'method': 'zscore'},
            'neutralize': None,
        },
        analysis_config={
            'periods': [1, 5, 10],
            'quantiles': 5,
            'ic_method': 'spearman',
        },
        output_dir='./factor_analysis_output',
        use_alphalens=False,
    )
    
    result = pipeline.run(
        factor_name='momentum_20',
        factor_df=factor_data['momentum_20'],
        price_df=price_data,
        preprocessing=True,
        scoring=True,
        visualize=True,
    )
    
    scorer = FactorScorer()
    
    print(f"\n原始评分: {result['score']['total_score']:.2f}")
    
    new_weights = {
        'ic': 0.4,
        'return': 0.3,
        'stability': 0.2,
        'independence': 0.1,
    }
    scorer_weighted = FactorScorer(weights=new_weights)
    
    score_weighted = scorer_weighted.score(result)
    print(f"加权评分 (IC权重40%): {score_weighted['total_score']:.2f}")
    
    visualizer = FactorVisualizer()
    if 'distribution' in result.get('figures', {}):
        fig = result['figures']['distribution']
        plt.show()
    
    plt.show()


def example_6_report_generation():
    """示例6: 报告生成"""
    print("\n" + "=" * 60)
    print("示例6: 报告生成")
    print("=" * 60)
    
    from trader_center.factor.mining import FactorAnalysisPipeline
    
    price_data, factor_data = create_sample_data()
    
    pipeline = FactorAnalysisPipeline(
        output_dir='./factor_analysis_output',
        use_alphalens=False,
    )
    
    pipeline.run(
        factor_name='momentum_20',
        factor_df=factor_data['momentum_20'],
        price_df=price_data,
        preprocessing=True,
        scoring=True,
        visualize=True,
        generate_report=True,
    )
    
    pipeline.run(
        factor_name='volatility_20',
        factor_df=factor_data['volatility_20'],
        price_df=price_data,
        preprocessing=True,
        scoring=True,
        visualize=False,
        generate_report=False,
    )
    
    report_path = pipeline.generate_multi_factor_report()
    print(f"\n多因子报告已生成: {report_path}")
    
    plt.show()


def main():
    """运行所有示例"""
    print("=" * 60)
    print("因子分析流水线使用示例")
    print("=" * 60)
    
    example_1_quick_analyze()
    
    example_2_full_pipeline()
    
    example_3_batch_analysis()
    
    example_4_with_alphalens()
    
    example_5_custom_factor_analysis()
    
    example_6_report_generation()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
