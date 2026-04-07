"""
单因子复现研究 - 价格动量因子

研究流程：
1. 获取股票数据
2. 计算因子值（使用 library 中的 MomentumFactor）
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
from typing import Type, List
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import trader_center.data_hub as dh
from trader_center.factor.mining import FactorAnalysisPipeline
from trader_center.factor.library.base import BaseFactor
from trader_center.factor.library.technical.momentum import MomentumFactor
from trader_center.factor.library.registry import FactorRegistry


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_BASE_DIR = PROJECT_ROOT / 'factor_research_results'


def get_index_constituents(index_code: str) -> List[str]:
    """
    获取指数成分股
    
    Args:
        index_code: 指数代码
            - '000300': 沪深300
            - '000905': 中证500
            - '000852': 中证1000
    
    Returns:
        股票代码列表，格式如 ['000001.SZ', '600000.SH']
    """
    import akshare as ak
    
    df = ak.index_stock_cons(symbol=index_code)
    symbols = []
    
    for _, row in df.iterrows():
        code = str(row['品种代码'])
        if code.startswith(('60', '68', '88', '89')):
            exchange = 'SH'
        elif code.startswith(('00', '30', '82', '83')):
            exchange = 'SZ'
        else:
            exchange = 'SH'
        symbols.append(f"{code}.{exchange}")
    
    return symbols


def get_stock_data(symbols: list, start_date: str, end_date: str, max_workers: int = 20) -> pd.DataFrame:
    """
    并发获取股票数据（使用 data_hub 统一接口）
    
    利用 data_hub 内置缓存机制，避免重复请求。
    使用线程池并发获取，大幅提升获取速度。
    
    Args:
        symbols: 股票代码列表，如 ['000001.SZ', '600000.SH']
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        max_workers: 并发线程数，默认 20
    
    Returns:
        价格DataFrame，index为日期，columns为股票代码
    """
    price_data = {}
    failed_symbols = []
    lock = threading.Lock()
    
    total = len(symbols)
    start_time = datetime.now()
    completed_count = [0]
    
    def fetch_single(symbol: str) -> tuple:
        """获取单只股票数据"""
        try:
            df = dh.get_daily_bars(symbol, start_date, end_date)
            if df is not None and not df.empty:
                return (symbol, df['close'], None)
            return (symbol, None, "empty data")
        except Exception as e:
            return (symbol, None, str(e))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single, symbol): symbol for symbol in symbols}
        
        for future in as_completed(futures):
            symbol, close_series, error = future.result()
            completed_count[0] += 1
            
            if close_series is not None:
                with lock:
                    price_data[symbol] = close_series
            else:
                failed_symbols.append(symbol)
            
            progress = completed_count[0] / total
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if completed_count[0] > 0 and elapsed > 0:
                avg_time = elapsed / completed_count[0]
                remaining = avg_time * (total - completed_count[0])
                eta_str = f"ETA: {int(remaining)}s"
            else:
                eta_str = "ETA: --"
            
            status = f"\r  进度: {completed_count[0]}/{total} ({progress*100:.1f}%) | 成功: {len(price_data)} | 失败: {len(failed_symbols)} | {eta_str}    "
            sys.stdout.write(status)
            sys.stdout.flush()
    
    print()
    
    if failed_symbols:
        print(f"  警告: {len(failed_symbols)} 只股票获取失败")
    
    if not price_data:
        raise ValueError("未获取到任何股票数据")
    
    price_df = pd.DataFrame(price_data)
    price_df.index = pd.to_datetime(price_df.index)
    price_df = price_df.sort_index()
    
    return price_df


def create_sample_data() -> pd.DataFrame:
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
    factor_class: Type[BaseFactor] = MomentumFactor,
    periods: list = [5, 10, 20, 60],
    volume_df: pd.DataFrame = None,
):
    """
    运行因子研究
    
    使用 library 中的因子类进行分析。
    
    Args:
        price_df: 价格数据（宽表格式）
        factor_class: 因子类
        periods: 因子参数列表
        volume_df: 成交量数据（可选）
    
    Returns:
        results: 分析结果字典
        pipeline: FactorAnalysisPipeline 实例
    """
    print("=" * 60)
    print(f"因子研究: {factor_class.name}")
    print("=" * 60)
    
    output_dir = OUTPUT_BASE_DIR / factor_class.name
    
    registry = FactorRegistry()
    
    pipeline = FactorAnalysisPipeline(
        registry=registry,
        output_dir=str(output_dir),
        use_alphalens=False,
    )
    
    results = {}
    
    for period in periods:
        print(f"\n--- 参数: period={period} ---")
        
        factor = factor_class(period=period)
        
        try:
            result = pipeline.run_with_factor(
                factor=factor,
                price_df=price_df,
                volume_df=volume_df,
                preprocessing=True,
                scoring=True,
                visualize=True,
                generate_report=True,
                metadata={
                    'factor_type': factor_class.name,
                    'period': period,
                    'n_assets': len(price_df.columns),
                    'n_dates': len(price_df),
                }
            )
            
            results[f'{factor_class.name}_{period}'] = result
            
            print(f"IC均值: {result['summary'].get('ic_mean', 0):.4f}")
            print(f"ICIR: {result['summary'].get('icir', 0):.4f}")
            if 'score' in result:
                print(f"评分: {result['score']['total_score']:.2f} ({result['score']['grade']})")
        except Exception as e:
            print(f"分析失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("所有参数分析完成")
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
    
    # 配置参数
    POOL_TYPE = 'hs300'  # 沪深300 + 中证500
    START_DATE = '2019-01-01'
    END_DATE = '2024-12-31'
    MAX_WORKERS = 20  # 并发线程数，建议 10-30
    
    # 获取股票池
    print(f"\n获取股票池: {POOL_TYPE}")
    symbols = []
    
    if POOL_TYPE in ['hs300', 'hs300_zz500']:
        print("  获取沪深300成分股...")
        hs300 = get_index_constituents('000300')
        symbols.extend(hs300)
        print(f"  沪深300: {len(hs300)} 只")
    
    if POOL_TYPE in ['zz500', 'hs300_zz500']:
        print("  获取中证500成分股...")
        zz500 = get_index_constituents('000905')
        symbols.extend(zz500)
        print(f"  中证500: {len(zz500)} 只")
    
    # 去重
    symbols = list(set(symbols))
    print(f"股票池总计: {len(symbols)} 只")
    
    # 获取数据（并发）
    print(f"\n获取数据: {START_DATE} 至 {END_DATE}")
    print(f"(并发获取，线程数: {MAX_WORKERS})")
    
    try:
        price_df = get_stock_data(symbols, START_DATE, END_DATE, max_workers=MAX_WORKERS)
        print(f"获取到 {len(price_df)} 天的数据，{len(price_df.columns)} 只股票")
    except Exception as e:
        print(f"获取数据失败: {e}")
        return
    
    # 运行因子研究
    results, pipeline = run_factor_research(
        price_df=price_df,
        factor_class=MomentumFactor,
        periods=[5, 10, 20, 60],
    )
    
    compare_different_periods(results)
    
    print("\n研究完成！")
    print(f"结果保存在: {OUTPUT_BASE_DIR / 'momentum'}")


if __name__ == "__main__":
    main()
