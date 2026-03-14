"""
因子挖掘运行脚本

演示如何使用因子挖掘模块自动挖掘因子，并生成评价报告。
"""

import os
import sys
import argparse
import logging
from datetime import datetime
import json

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trader_center.factor.mining.pipeline import (
    FactorMiningPipeline,
    MiningConfig,
    run_factor_mining,
)
from trader_center.factor.mining.evaluator import FactorEvaluator, quick_evaluate
from trader_center.factor.mining.combination import FactorCombiner, create_factor_portfolio
from trader_center.factor.mining.gp.factor_generator import SimpleFactorGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_data(
    n_days: int = 500,
    n_stocks: int = 50,
    start_date: str = '2022-01-01',
) -> tuple:
    """
    创建示例数据
    
    Args:
        n_days: 天数
        n_stocks: 股票数量
        start_date: 开始日期
    
    Returns:
        (数据字典, 未来收益DataFrame)
    """
    dates = pd.date_range(start_date, periods=n_days, freq='D')
    
    data_dict = {}
    for i in range(n_stocks):
        symbol = f"stock_{i:04d}"
        
        np.random.seed(42 + i)
        
        returns = np.random.randn(n_days) * 0.02
        close = 100 * np.cumprod(1 + returns)
        
        high = close * (1 + np.abs(np.random.randn(n_days)) * 0.01)
        low = close * (1 - np.abs(np.random.randn(n_days)) * 0.01)
        open_price = close * (1 + np.random.randn(n_days) * 0.005)
        volume = np.random.randint(1000000, 10000000, n_days) * (1 + i * 0.1)
        
        data_dict[symbol] = pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        }, index=dates)
    
    forward_returns = pd.DataFrame(index=dates)
    for symbol, df in data_dict.items():
        forward_returns[symbol] = df['close'].pct_change(5).shift(-5)
    
    return data_dict, forward_returns


def run_simple_mining(data_dict: dict, forward_returns: pd.DataFrame):
    """
    运行简单因子挖掘（不依赖gplearn）
    """
    print("\n" + "=" * 60)
    print("简单因子挖掘（基于模板）")
    print("=" * 60)
    
    generator = SimpleFactorGenerator()
    factors = generator.generate(n_factors=30)
    
    print(f"\n生成了 {len(factors)} 个因子表达式")
    
    first_symbol = list(data_dict.keys())[0]
    sample_data = data_dict[first_symbol]
    
    print("\n因子表达式示例:")
    for i, f in enumerate(factors[:5], 1):
        print(f"  {i}. {f.expression_str}")
    
    print("\n评估因子...")
    evaluator = FactorEvaluator()
    
    factor_values = {}
    for factor_expr in factors:
        try:
            values = []
            for symbol, data in data_dict.items():
                from trader_center.factor.mining.gp.expression import evaluate_expression
                val = evaluate_expression(factor_expr.expression_str, data)
                values.append(val)
            
            combined = pd.concat(values, axis=1)
            combined.columns = list(data_dict.keys())
            factor_values[factor_expr.name] = combined.mean(axis=1)
        except Exception as e:
            continue
    
    if factor_values:
        factors_df = pd.DataFrame(factor_values)
        
        results = []
        for name in factors_df.columns:
            factor_series = factors_df[name]
            returns_series = forward_returns.mean(axis=1)
            
            common_idx = factor_series.dropna().index.intersection(returns_series.dropna().index)
            
            if len(common_idx) < 20:
                continue
            
            from scipy.stats import spearmanr
            ic, _ = spearmanr(factor_series.loc[common_idx], returns_series.loc[common_idx])
            
            results.append({
                'factor': name,
                'ic': ic,
                'abs_ic': abs(ic),
            })
        
        results_df = pd.DataFrame(results).sort_values('abs_ic', ascending=False)
        
        print("\n因子IC排名（前10）:")
        print(results_df.head(10).to_string(index=False))
        
        return results_df
    
    return None


def run_gp_mining(data_dict: dict, forward_returns: pd.DataFrame, use_gp: bool = True):
    """
    运行遗传规划因子挖掘
    """
    print("\n" + "=" * 60)
    print("遗传规划因子挖掘")
    print("=" * 60)
    
    first_symbol = list(data_dict.keys())[0]
    sample_data = data_dict[first_symbol]
    sample_returns = forward_returns[first_symbol].dropna()
    
    config = MiningConfig(
        method='gp' if use_gp else 'simple',
        population_size=500,
        generations=10,
        n_factors_to_generate=20,
        n_factors_to_select=5,
        min_ic=0.01,
        min_icir=0.3,
        n_jobs=1,
        random_state=42,
        verbose=1,
    )
    
    try:
        pipeline = FactorMiningPipeline(config=config)
        result = pipeline.run(sample_data, sample_returns.to_frame().T)
        
        print(result.summary())
        
        if result.selected_factors:
            print("\n筛选出的因子表达式:")
            for i, f in enumerate(result.selected_factors, 1):
                print(f"  {i}. {f.name}: {f.expression_str}")
                if f.fitness is not None:
                    print(f"     Fitness: {f.fitness:.4f}")
        
        return result
    
    except ImportError as e:
        print(f"\n无法使用GP方法: {e}")
        print("请安装gplearn: pip install gplearn")
        print("将使用简单方法...")
        return run_simple_mining(data_dict, forward_returns)


def run_factor_combination(data_dict: dict, forward_returns: pd.DataFrame, factors_df: pd.DataFrame):
    """
    运行因子组合优化
    """
    print("\n" + "=" * 60)
    print("因子组合优化")
    print("=" * 60)
    
    combiner = FactorCombiner(weight_method='icir')
    
    print("\n计算因子相关性...")
    corr_matrix = combiner.compute_factor_correlation(factors_df)
    print(f"平均相关性: {corr_matrix.values[np.triu_indices(len(corr_matrix), k=1)].mean():.4f}")
    
    print("\n正交化因子...")
    orthogonal_factors = combiner.orthogonalize(factors_df, method='schmidt')
    print(f"正交化后因子数: {len(orthogonal_factors.columns)}")
    
    print("\n优化因子权重...")
    returns_series = forward_returns.mean(axis=1)
    weights = combiner.optimize_weights(factors_df, returns_series, method='icir')
    
    print("\n因子权重:")
    for name, weight in weights.items():
        print(f"  {name}: {weight:.4f}")
    
    print("\n合成复合因子...")
    result = combiner.combine(factors_df, weights)
    
    print(f"复合因子均值: {result.combined_factor.mean():.4f}")
    print(f"复合因子标准差: {result.combined_factor.std():.4f}")
    
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='因子挖掘运行脚本')
    parser.add_argument('--method', type=str, default='simple', 
                        choices=['simple', 'gp'],
                        help='挖掘方法 (simple或gp)')
    parser.add_argument('--n-days', type=int, default=500, help='数据天数')
    parser.add_argument('--n-stocks', type=int, default=50, help='股票数量')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    parser.add_argument('--report', action='store_true', help='生成alphalens评价报告')
    parser.add_argument('--report-dir', type=str, default='./reports', help='报告输出目录')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("因子挖掘系统")
    print("=" * 60)
    print(f"方法: {args.method}")
    print(f"数据天数: {args.n_days}")
    print(f"股票数量: {args.n_stocks}")
    print(f"生成报告: {'是' if args.report else '否'}")
    
    print("\n生成示例数据...")
    data_dict, forward_returns = create_sample_data(
        n_days=args.n_days,
        n_stocks=args.n_stocks,
    )
    print(f"生成了 {len(data_dict)} 只股票的数据")
    
    mining_result = None
    
    if args.method == 'simple':
        results_df = run_simple_mining(data_dict, forward_returns)
    else:
        mining_result = run_gp_mining(data_dict, forward_returns, use_gp=True)
    
    if args.report:
        print("\n" + "=" * 60)
        print("生成因子评价报告")
        print("=" * 60)
        
        try:
            from trader_center.factor.mining.report import (
                FactorReportGenerator,
                DataConverter,
            )
            
            generator = FactorReportGenerator(output_dir=args.report_dir)
            
            prices = DataConverter.get_pricing_data(data_dict)
            
            if mining_result and hasattr(mining_result, 'selected_factors') and mining_result.selected_factors:
                factor_panel = DataConverter.factor_expression_to_panel(
                    mining_result.selected_factors, data_dict
                )
                
                if factor_panel:
                    first_factor_name = list(factor_panel.keys())[0]
                    factor_values = factor_panel[first_factor_name]
                    
                    report = generator.generate_full_report(
                        factor_values, prices,
                        title=f"因子评价报告: {first_factor_name}",
                        show_charts=True,
                        save_charts=True,
                    )
                    
                    print(generator.print_summary(report))
                    print(f"\n报告已保存到: {args.report_dir}")
            else:
                print("无可用的因子数据生成报告")
                
        except ImportError as e:
            print(f"无法导入报告模块: {e}")
            print("请安装alphalens-reloaded: pip install alphalens-reloaded")
        except Exception as e:
            print(f"生成报告失败: {e}")
    
    print("\n" + "=" * 60)
    print("因子挖掘完成！")
    print("=" * 60)
    
    if args.output and 'results_df' in dir():
        results_df.to_csv(args.output, index=False)
        print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
