"""
单因子复现研究 - 价格动量因子

研究流程：
1. 获取股票数据
2. 计算因子值
3. 因子分析（IC、分层回测）
4. 生成报告

因子说明：
- 价格动量 (Momentum): 过去N天的收益率
- 预期：高动量股票未来收益更高（趋势延续）
- 数据需求：仅需收盘价
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from trader_center.factor.mining import (
    FactorAnalysisPipeline,
    FactorScorer,
)
from trader_center.factor.library.technical.momentum import MomentumFactor


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_BASE_DIR = PROJECT_ROOT / 'factor_research_results'


def get_stock_data(symbols: list, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取股票数据
    
    Args:
        symbols: 股票代码列表，如 ['000001.SZ', '600000.SH']
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
    
    Returns:
        价格DataFrame，index为日期，columns为股票代码
    """
    from trader_center.data_hub.fetchers.akshare_fetcher import AkshareFetcher
    
    fetcher = AkshareFetcher()
    
    price_data = {}
    for symbol in symbols:
        bars = fetcher.get_bars(
            symbol=symbol,
            frequency='1d',
            start_date=start_date,
            end_date=end_date,
        )
        if bars is not None and len(bars) > 0:
            price_data[symbol] = bars['close']
    
    if not price_data:
        raise ValueError("未获取到任何股票数据")
    
    price_df = pd.DataFrame(price_data)
    price_df.index = pd.to_datetime(price_df.index)
    price_df = price_df.sort_index()
    
    return price_df


def calculate_momentum_factor(
    price_df: pd.DataFrame,
    period: int = 20,
) -> pd.DataFrame:
    """
    计算动量因子
    
    Args:
        price_df: 价格DataFrame
        period: 回看周期，默认20天
    
    Returns:
        因子值DataFrame
    """
    momentum = price_df.pct_change(period)
    return momentum


def create_sample_data() -> tuple:
    """
    创建示例数据（用于测试）
    
    如果没有真实数据，可以用这个生成模拟数据。
    """
    np.random.seed(42)
    
    n_days = 252
    n_assets = 50
    
    dates = pd.date_range('2023-01-01', periods=n_days, freq='B')
    assets = [f'Asset_{i:03d}' for i in range(n_assets)]
    
    price_data = pd.DataFrame(
        np.random.randn(n_days, n_assets).cumsum(axis=0) + 100,
        index=dates,
        columns=assets
    )
    
    return price_data


def run_factor_research(
    price_df: pd.DataFrame,
    factor_name: str = 'momentum',
    periods: list = [5, 10, 20, 60],
    use_real_data: bool = False,
):
    """
    运行因子研究
    
    Args:
        price_df: 价格DataFrame
        factor_name: 因子名称
        periods: 因子回看周期列表
        use_real_data: 是否使用真实数据分析
    """
    print("=" * 60)
    print(f"因子研究: {factor_name}")
    print("=" * 60)
    
    output_dir = OUTPUT_BASE_DIR / factor_name
    
    pipeline = FactorAnalysisPipeline(
        output_dir=str(output_dir),
        use_alphalens=False,
    )
    
    results = {}
    
    for period in periods:
        print(f"\n--- 周期: {period}天 ---")
        
        if factor_name == 'momentum':
            factor_df = calculate_momentum_factor(price_df, period)
        else:
            raise ValueError(f"未知因子: {factor_name}")
        
        factor_df = factor_df.dropna(how='all')
        
        if len(factor_df) < 60:
            print(f"数据不足，跳过")
            continue
        
        result = pipeline.run(
            factor_name=f'{factor_name}_{period}',
            factor_df=factor_df,
            price_df=price_df,
            preprocessing=True,
            scoring=True,
            visualize=True,
            generate_report=True,
            metadata={
                'factor_type': factor_name,
                'period': period,
                'n_assets': len(factor_df.columns),
                'n_dates': len(factor_df),
            }
        )
        
        results[f'{factor_name}_{period}'] = result
        
        print(f"IC均值: {result['summary'].get('ic_mean', 0):.4f}")
        print(f"ICIR: {result['summary'].get('icir', 0):.4f}")
        if 'score' in result:
            print(f"评分: {result['score']['total_score']:.2f} ({result['score']['grade']})")
    
    print("\n" + "=" * 60)
    print("所有周期分析完成")
    print("=" * 60)
    
    ranking = pipeline.get_ranking()
    print("\n--- 因子排名 ---")
    print(ranking)
    
    return results, pipeline


def compare_different_periods(results: dict):
    """
    比较不同周期的因子表现
    """
    print("\n" + "=" * 60)
    print("不同周期对比")
    print("=" * 60)
    
    comparison = []
    for name, result in results.items():
        summary = result.get('summary', {})
        score = result.get('score', {})
        
        comparison.append({
            'factor': name,
            'ic_mean': summary.get('ic_mean', 0),
            'icir': summary.get('icir', 0),
            'ic_positive_ratio': summary.get('ic_positive_ratio', 0),
            'total_score': score.get('total_score', 0),
            'grade': score.get('grade', 'F'),
        })
    
    comp_df = pd.DataFrame(comparison)
    print(comp_df.to_string(index=False))
    
    return comp_df


def main():
    """主函数"""
    print("因子复现研究 - 价格动量因子")
    print("=" * 60)
    
    USE_REAL_DATA = False
    
    if USE_REAL_DATA:
        print("使用真实数据...")
        
        symbols = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ']
        
        try:
            price_df = get_stock_data(
                symbols=symbols,
                start_date='2023-01-01',
                end_date='2024-12-31',
            )
            print(f"获取到 {len(price_df)} 天的数据，{len(price_df.columns)} 只股票")
        except Exception as e:
            print(f"获取数据失败: {e}，使用示例数据")
            price_df = create_sample_data()
    else:
        print("使用示例数据...")
        price_df = create_sample_data()
        print(f"生成数据: {len(price_df)} 天，{len(price_df.columns)} 只股票")
    
    results, pipeline = run_factor_research(
        price_df=price_df,
        factor_name='momentum',
        periods=[5, 10, 20, 60],
        use_real_data=USE_REAL_DATA,
    )
    
    compare_different_periods(results)
    
    print("\n研究完成！")
    print(f"结果保存在: {OUTPUT_BASE_DIR / 'momentum'}")


if __name__ == "__main__":
    main()
