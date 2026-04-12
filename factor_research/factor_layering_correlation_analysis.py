"""
因子分层与相关性分析研究

研究内容：
1. 因子分层分析：分析不同因子值分组的表现差异
2. 因子相关性分析：分析因子间的相关关系，避免冗余
3. 多因子组合策略：构建有效的多因子投资组合

因子列表：
- 动量因子 (Momentum): period=20
- RSI因子: period=14
- 波动率因子 (Volatility): period=20
- 乖离率因子 (Bias): period=20, ma_type='sma'
- MACD因子: fast=12, slow=26, signal=9
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import seaborn as sns

import trader_center.data_hub as dh
from trader_center.factor.mining import FactorAnalysisPipeline
from trader_center.factor.mining.layering import LayeringAnalyzer
from trader_center.factor.mining.correlation import CorrelationAnalyzer
from trader_center.factor.mining.ic_analysis import ICAnalyzer
from trader_center.factor.library.base import BaseFactor
from trader_center.factor.library.technical.momentum import MomentumFactor, RSIFactor, MACDFactor
from trader_center.factor.library.technical.volatility import HistoricalVolatilityFactor
from trader_center.factor.library.technical.reversal import BiasFactor
from trader_center.factor.library.registry import FactorRegistry
from trader_center.factor.mining.preprocessing.winsorization import winsorize_cross_sectional
from trader_center.factor.mining.preprocessing.standardization import standardize_cross_sectional


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_BASE_DIR = PROJECT_ROOT / 'factor_research_results' / 'layering_correlation_analysis'


plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


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
                return (symbol, df, None)
            return (symbol, None, "empty data")
        except Exception as e:
            return (symbol, None, str(e))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single, symbol): symbol for symbol in symbols}
        
        for future in as_completed(futures):
            symbol, stock_df, error = future.result()
            completed_count[0] += 1
            
            if stock_df is not None:
                with lock:
                    price_data[symbol] = stock_df
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
    
    return price_data


def compute_factors(
    price_data: Dict[str, pd.DataFrame],
    factor_configs: List[Dict],
) -> Dict[str, pd.DataFrame]:
    """
    批量计算多个因子
    
    Args:
        price_data: 股票数据字典 {symbol: DataFrame}
        factor_configs: 因子配置列表
    
    Returns:
        因子数据字典 {factor_name: DataFrame}
    """
    print("\n开始计算因子...")
    
    factor_values = {}
    
    for config in factor_configs:
        factor_name = config['name']
        factor_class = config['class']
        params = config.get('params', {})
        
        print(f"  计算 {factor_name}...")
        
        factor_instance = factor_class(**params)
        
        factor_dict = {}
        for symbol, df in price_data.items():
            try:
                factor_series = factor_instance.compute(df)
                factor_dict[symbol] = factor_series
            except Exception as e:
                print(f"    警告: {symbol} 计算失败: {e}")
                factor_dict[symbol] = pd.Series(dtype=float)
        
        factor_df = pd.DataFrame(factor_dict)
        
        if not isinstance(factor_df.index, pd.DatetimeIndex):
            factor_df.index = pd.to_datetime(factor_df.index)
        
        factor_df.index.name = 'date'
        
        factor_values[factor_name] = factor_df
    
    print(f"完成，共计算 {len(factor_values)} 个因子")
    
    return factor_values


def preprocess_factors(
    factor_values: Dict[str, pd.DataFrame],
    winsorize: bool = True,
    standardize: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    因子预处理
    
    Args:
        factor_values: 因子数据字典
        winsorize: 是否去极值
        standardize: 是否标准化
    
    Returns:
        处理后的因子数据字典
    """
    print("\n因子预处理...")
    
    processed_factors = {}
    
    for factor_name, factor_df in factor_values.items():
        print(f"  处理 {factor_name}...")
        
        processed = factor_df.copy()
        
        if winsorize:
            processed = winsorize_cross_sectional(processed, method='mad', threshold=3.0)
        
        if standardize:
            processed = standardize_cross_sectional(processed, method='zscore')
        
        processed = processed.astype(float)
        
        processed_factors[factor_name] = processed
    
    print("预处理完成")
    
    return processed_factors


def run_layering_analysis(
    factor_values: Dict[str, pd.DataFrame],
    price_df: pd.DataFrame,
    n_groups: int = 5,
) -> Dict[str, Dict]:
    """
    运行分层分析
    
    Args:
        factor_values: 因子数据字典
        price_df: 价格数据
        n_groups: 分组数量
    
    Returns:
        分层分析结果字典
    """
    print("\n" + "=" * 60)
    print("因子分层分析")
    print("=" * 60)
    
    forward_returns = price_df.pct_change(fill_method=None).shift(-1)
    
    layering_results = {}
    
    for factor_name, factor_df in factor_values.items():
        print(f"\n分析因子: {factor_name}")
        
        analyzer = LayeringAnalyzer(n_groups=n_groups)
        
        try:
            common_dates = factor_df.index.intersection(forward_returns.index)
            if len(common_dates) == 0:
                print(f"  警告: 因子数据和收益数据没有共同的日期")
                layering_results[factor_name] = None
                continue
            
            factor_aligned = factor_df.loc[common_dates]
            returns_aligned = forward_returns.loc[common_dates]
            
            result = analyzer.compute(factor_aligned, returns_aligned)
            
            monotonicity = analyzer.compute_monotonicity()
            
            turnover = analyzer.compute_turnover(factor_aligned, top_n=50)
            
            layering_results[factor_name] = {
                'group_returns': result['group_returns'],
                'group_stats': result['group_stats'],
                'long_short_returns': result['long_short_returns'],
                'long_short_mean': result['long_short_mean'],
                'long_short_std': result['long_short_std'],
                'long_short_sharpe': result['long_short_sharpe'],
                'monotonicity': monotonicity,
                'turnover': turnover,
            }
            
            print(f"  单调性: {monotonicity:.4f}")
            print(f"  多空收益: {result['long_short_mean']:.4f}")
            print(f"  多空夏普: {result['long_short_sharpe']:.4f}")
            print(f"  平均换手率: {turnover.mean():.4f}")
            
        except Exception as e:
            print(f"  分析失败: {e}")
            import traceback
            traceback.print_exc()
            layering_results[factor_name] = None
    
    return layering_results


def run_correlation_analysis(
    factor_values: Dict[str, pd.DataFrame],
    price_df: pd.DataFrame,
    method: str = 'spearman',
) -> Dict:
    """
    运行相关性分析
    
    Args:
        factor_values: 因子数据字典
        price_df: 价格数据
        method: 相关性计算方法
    
    Returns:
        相关性分析结果字典
    """
    print("\n" + "=" * 60)
    print("因子相关性分析")
    print("=" * 60)
    
    forward_returns = price_df.pct_change(fill_method=None).shift(-1)
    
    print("\n计算因子间相关性...")
    
    analyzer = CorrelationAnalyzer()
    
    factor_data_dict = {}
    for factor_name, factor_df in factor_values.items():
        factor_series = factor_df.stack()
        factor_series.index.names = ['date', 'asset']
        factor_data_dict[factor_name] = factor_series
    
    corr_matrix = analyzer.compute_correlation_matrix(factor_data_dict, method=method)
    
    print("\n相关性矩阵:")
    print(corr_matrix.round(3))
    
    high_corr_pairs = analyzer.find_highly_correlated_pairs(threshold=0.7)
    
    if high_corr_pairs:
        print("\n高相关性因子对 (|corr| > 0.7):")
        for factor1, factor2, corr in high_corr_pairs:
            print(f"  {factor1} <-> {factor2}: {corr:.4f}")
    else:
        print("\n未发现高相关性因子对")
    
    print("\n计算因子IC...")
    ic_results = {}
    for factor_name, factor_df in factor_values.items():
        ic_analyzer = ICAnalyzer()
        ic_result = ic_analyzer.compute(factor_df, forward_returns, method=method)
        ic_results[factor_name] = ic_result
        
        print(f"  {factor_name}: IC均值={ic_result['ic_mean']:.4f}, ICIR={ic_result['icir']:.4f}")
    
    print("\n计算因子自相关性...")
    autocorr_results = {}
    for factor_name, factor_df in factor_values.items():
        factor_series = factor_df.stack()
        factor_series.index.names = ['date', 'asset']
        
        autocorr_series = analyzer.compute_autocorrelation_series(factor_series, max_lag=20)
        autocorr_results[factor_name] = autocorr_series
        
        print(f"  {factor_name}: 1期自相关={autocorr_series.iloc[0]:.4f}")
    
    mean_corr = {}
    for factor_name in corr_matrix.index:
        other_corrs = corr_matrix.loc[factor_name].drop(factor_name)
        mean_corr[factor_name] = other_corrs.abs().mean()
    
    print("\n因子独立性（平均相关性）:")
    for factor_name, avg_corr in sorted(mean_corr.items(), key=lambda x: x[1]):
        print(f"  {factor_name}: {avg_corr:.4f}")
    
    return {
        'correlation_matrix': corr_matrix,
        'high_corr_pairs': high_corr_pairs,
        'ic_results': ic_results,
        'autocorr_results': autocorr_results,
        'mean_correlation': mean_corr,
    }


def construct_factor_portfolio(
    factor_values: Dict[str, pd.DataFrame],
    ic_results: Dict[str, Dict],
    method: str = 'equal_weight',
) -> Tuple[pd.DataFrame, Dict]:
    """
    构建多因子组合
    
    Args:
        factor_values: 因子数据字典
        ic_results: IC分析结果
        method: 加权方法
            - 'equal_weight': 等权
            - 'ic_weight': IC加权
            - 'icir_weight': ICIR加权
    
    Returns:
        (组合因子值, 权重字典)
    """
    print("\n" + "=" * 60)
    print(f"多因子组合构建 - {method}")
    print("=" * 60)
    
    factor_names = list(factor_values.keys())
    n_factors = len(factor_names)
    
    if method == 'equal_weight':
        weights = {name: 1.0 / n_factors for name in factor_names}
        print(f"等权组合: 各因子权重 = {1.0/n_factors:.4f}")
    
    elif method == 'ic_weight':
        ic_means = {name: abs(ic_results[name]['ic_mean']) for name in factor_names}
        total_ic = sum(ic_means.values())
        if total_ic > 0:
            weights = {name: ic_means[name] / total_ic for name in factor_names}
        else:
            weights = {name: 1.0 / n_factors for name in factor_names}
        print("IC加权组合:")
        for name, weight in weights.items():
            print(f"  {name}: {weight:.4f}")
    
    elif method == 'icir_weight':
        icirs = {name: abs(ic_results[name]['icir']) for name in factor_names}
        total_icir = sum(icirs.values())
        if total_icir > 0:
            weights = {name: icirs[name] / total_icir for name in factor_names}
        else:
            weights = {name: 1.0 / n_factors for name in factor_names}
        print("ICIR加权组合:")
        for name, weight in weights.items():
            print(f"  {name}: {weight:.4f}")
    
    else:
        raise ValueError(f"未知的加权方法: {method}")
    
    dates = factor_values[factor_names[0]].index
    assets = factor_values[factor_names[0]].columns
    
    portfolio_factor = pd.DataFrame(0.0, index=dates, columns=assets)
    
    for factor_name, weight in weights.items():
        portfolio_factor += factor_values[factor_name] * weight
    
    return portfolio_factor, weights


def evaluate_portfolio(
    portfolio_factor: pd.DataFrame,
    price_df: pd.DataFrame,
    portfolio_name: str = 'Portfolio',
) -> Dict:
    """
    评估组合表现
    
    Args:
        portfolio_factor: 组合因子值
        price_df: 价格数据
        portfolio_name: 组合名称
    
    Returns:
        评估结果字典
    """
    print(f"\n评估组合: {portfolio_name}")
    
    forward_returns = price_df.pct_change(fill_method=None).shift(-1)
    
    common_dates = portfolio_factor.index.intersection(forward_returns.index)
    if len(common_dates) == 0:
        print(f"  警告: 组合因子数据和收益数据没有共同的日期")
        return {
            'ic_mean': 0.0,
            'icir': 0.0,
            'long_short_mean': 0.0,
            'long_short_sharpe': 0.0,
            'monotonicity': 0.0,
            'group_stats': pd.DataFrame(),
        }
    
    portfolio_aligned = portfolio_factor.loc[common_dates]
    returns_aligned = forward_returns.loc[common_dates]
    
    ic_analyzer = ICAnalyzer()
    ic_result = ic_analyzer.compute(portfolio_aligned, returns_aligned)
    
    layering_analyzer = LayeringAnalyzer(n_groups=5)
    layering_result = layering_analyzer.compute(portfolio_aligned, returns_aligned)
    
    monotonicity = layering_analyzer.compute_monotonicity()
    
    result = {
        'ic_mean': ic_result['ic_mean'],
        'icir': ic_result['icir'],
        'long_short_mean': layering_result['long_short_mean'],
        'long_short_sharpe': layering_result['long_short_sharpe'],
        'monotonicity': monotonicity,
        'group_stats': layering_result['group_stats'],
    }
    
    print(f"  IC均值: {ic_result['ic_mean']:.4f}")
    print(f"  ICIR: {ic_result['icir']:.4f}")
    print(f"  多空收益: {layering_result['long_short_mean']:.4f}")
    print(f"  多空夏普: {layering_result['long_short_sharpe']:.4f}")
    print(f"  单调性: {monotonicity:.4f}")
    
    return result


def plot_layering_comparison(
    layering_results: Dict[str, Dict],
    output_dir: Path,
):
    """
    绘制分层对比图
    
    Args:
        layering_results: 分层分析结果
        output_dir: 输出目录
    """
    print("\n生成分层对比图...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    n_factors = len([r for r in layering_results.values() if r is not None])
    fig, axes = plt.subplots(n_factors, 1, figsize=(12, 4 * n_factors))
    
    if n_factors == 1:
        axes = [axes]
    
    idx = 0
    for factor_name, result in layering_results.items():
        if result is None:
            continue
        
        ax = axes[idx]
        
        group_returns = result['group_returns']
        cumulative_returns = (1 + group_returns).cumprod()
        
        for col in cumulative_returns.columns:
            ax.plot(cumulative_returns.index, cumulative_returns[col], 
                   label=col, linewidth=2)
        
        ax.set_title(f'{factor_name} - 分层累计收益', fontsize=12, fontweight='bold')
        ax.set_xlabel('日期')
        ax.set_ylabel('累计收益')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        idx += 1
    
    plt.tight_layout()
    
    save_path = output_dir / 'layering_comparison.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"  保存到: {save_path}")
    plt.close()
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1 = axes[0]
    factor_names = []
    monotonicity_values = []
    for factor_name, result in layering_results.items():
        if result is not None:
            factor_names.append(factor_name)
            monotonicity_values.append(result['monotonicity'])
    
    colors = ['green' if m > 0.5 else 'orange' if m > 0 else 'red' for m in monotonicity_values]
    ax1.bar(range(len(factor_names)), monotonicity_values, color=colors, alpha=0.7)
    ax1.set_xticks(range(len(factor_names)))
    ax1.set_xticklabels(factor_names, rotation=45, ha='right')
    ax1.set_title('因子单调性对比', fontsize=12, fontweight='bold')
    ax1.set_ylabel('单调性得分')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.axhline(y=0.5, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax1.grid(True, alpha=0.3, axis='y')
    
    ax2 = axes[1]
    ls_sharpe_values = []
    for factor_name in factor_names:
        if layering_results[factor_name] is not None:
            ls_sharpe_values.append(layering_results[factor_name]['long_short_sharpe'])
    
    colors = ['green' if s > 0.5 else 'orange' if s > 0 else 'red' for s in ls_sharpe_values]
    ax2.bar(range(len(factor_names)), ls_sharpe_values, color=colors, alpha=0.7)
    ax2.set_xticks(range(len(factor_names)))
    ax2.set_xticklabels(factor_names, rotation=45, ha='right')
    ax2.set_title('多空夏普比率对比', fontsize=12, fontweight='bold')
    ax2.set_ylabel('夏普比率')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.axhline(y=0.5, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    save_path = output_dir / 'factor_metrics_comparison.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"  保存到: {save_path}")
    plt.close()


def plot_correlation_heatmap(
    corr_matrix: pd.DataFrame,
    output_dir: Path,
):
    """
    绘制相关性热力图
    
    Args:
        corr_matrix: 相关性矩阵
        output_dir: 输出目录
    """
    print("\n生成相关性热力图...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        fmt='.2f',
        cmap='RdYlGn',
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
        ax=ax
    )
    
    ax.set_title('因子相关性矩阵', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    save_path = output_dir / 'correlation_heatmap.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"  保存到: {save_path}")
    plt.close()


def plot_ic_comparison(
    ic_results: Dict[str, Dict],
    output_dir: Path,
):
    """
    绘制IC对比图
    
    Args:
        ic_results: IC分析结果
        output_dir: 输出目录
    """
    print("\n生成IC对比图...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    factor_names = list(ic_results.keys())
    ic_means = [ic_results[name]['ic_mean'] for name in factor_names]
    icirs = [ic_results[name]['icir'] for name in factor_names]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1 = axes[0]
    colors = ['green' if ic > 0.02 else 'orange' if ic > 0 else 'red' for ic in ic_means]
    ax1.bar(range(len(factor_names)), ic_means, color=colors, alpha=0.7)
    ax1.set_xticks(range(len(factor_names)))
    ax1.set_xticklabels(factor_names, rotation=45, ha='right')
    ax1.set_title('因子IC均值对比', fontsize=12, fontweight='bold')
    ax1.set_ylabel('IC均值')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.axhline(y=0.02, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax1.grid(True, alpha=0.3, axis='y')
    
    ax2 = axes[1]
    colors = ['green' if icir > 0.5 else 'orange' if icir > 0 else 'red' for icir in icirs]
    ax2.bar(range(len(factor_names)), icirs, color=colors, alpha=0.7)
    ax2.set_xticks(range(len(factor_names)))
    ax2.set_xticklabels(factor_names, rotation=45, ha='right')
    ax2.set_title('因子ICIR对比', fontsize=12, fontweight='bold')
    ax2.set_ylabel('ICIR')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.axhline(y=0.5, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    save_path = output_dir / 'ic_comparison.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"  保存到: {save_path}")
    plt.close()


def generate_report(
    layering_results: Dict[str, Dict],
    correlation_results: Dict,
    portfolio_results: Dict,
    output_dir: Path,
):
    """
    生成研究报告
    
    Args:
        layering_results: 分层分析结果
        correlation_results: 相关性分析结果
        portfolio_results: 组合分析结果
        output_dir: 输出目录
    """
    print("\n生成研究报告...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_lines = []
    report_lines.append("# 因子分层与相关性分析研究报告\n")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    report_lines.append("## 一、因子分层分析结果\n\n")
    
    layering_table = []
    for factor_name, result in layering_results.items():
        if result is None:
            continue
        
        layering_table.append({
            '因子': factor_name,
            '单调性': f"{result['monotonicity']:.4f}",
            '多空收益': f"{result['long_short_mean']:.4f}",
            '多空夏普': f"{result['long_short_sharpe']:.4f}",
            '平均换手率': f"{result['turnover'].mean():.4f}",
        })
    
    if layering_table:
        layering_df = pd.DataFrame(layering_table)
        report_lines.append("### 1.1 因子分层表现汇总\n\n")
        report_lines.append(layering_df.to_markdown(index=False))
        report_lines.append("\n\n")
    
    report_lines.append("### 1.2 分层分析解读\n\n")
    report_lines.append("**单调性说明**：\n")
    report_lines.append("- 单调性得分范围：-1 到 1\n")
    report_lines.append("- 得分越接近 1，表示因子单调性越好（因子值越大，收益越高）\n")
    report_lines.append("- 得分接近 -1，表示反向单调（因子值越大，收益越低）\n")
    report_lines.append("- 得分接近 0，表示因子缺乏单调性\n\n")
    
    report_lines.append("**多空收益说明**：\n")
    report_lines.append("- 多空收益 = 最高组收益 - 最低组收益\n")
    report_lines.append("- 多空收益越高，因子区分度越好\n")
    report_lines.append("- 多空夏普比率衡量多空策略的风险调整收益\n\n")
    
    report_lines.append("## 二、因子相关性分析结果\n\n")
    
    report_lines.append("### 2.1 因子相关性矩阵\n\n")
    corr_matrix = correlation_results['correlation_matrix']
    report_lines.append(corr_matrix.round(3).to_markdown())
    report_lines.append("\n\n")
    
    high_corr_pairs = correlation_results['high_corr_pairs']
    if high_corr_pairs:
        report_lines.append("### 2.2 高相关性因子对\n\n")
        report_lines.append("以下因子对的相关性绝对值大于 0.7，可能存在信息冗余：\n\n")
        for factor1, factor2, corr in high_corr_pairs:
            report_lines.append(f"- {factor1} <-> {factor2}: {corr:.4f}\n")
        report_lines.append("\n")
    else:
        report_lines.append("### 2.2 高相关性因子对\n\n")
        report_lines.append("未发现高相关性因子对，各因子独立性较好。\n\n")
    
    report_lines.append("### 2.3 因子独立性评分\n\n")
    mean_corr = correlation_results['mean_correlation']
    report_lines.append("因子独立性通过平均相关性衡量，平均相关性越低，独立性越好：\n\n")
    for factor_name, avg_corr in sorted(mean_corr.items(), key=lambda x: x[1]):
        report_lines.append(f"- {factor_name}: {avg_corr:.4f}\n")
    report_lines.append("\n")
    
    report_lines.append("### 2.4 因子IC表现\n\n")
    ic_results = correlation_results['ic_results']
    ic_table = []
    for factor_name, ic_result in ic_results.items():
        ic_table.append({
            '因子': factor_name,
            'IC均值': f"{ic_result['ic_mean']:.4f}",
            'IC标准差': f"{ic_result['ic_std']:.4f}",
            'ICIR': f"{ic_result['icir']:.4f}",
            'IC>0比例': f"{ic_result['ic_positive_ratio']:.2%}",
        })
    
    ic_df = pd.DataFrame(ic_table)
    report_lines.append(ic_df.to_markdown(index=False))
    report_lines.append("\n\n")
    
    report_lines.append("## 三、多因子组合结果\n\n")
    
    portfolio_table = []
    for portfolio_name, result in portfolio_results.items():
        portfolio_table.append({
            '组合': portfolio_name,
            'IC均值': f"{result['ic_mean']:.4f}",
            'ICIR': f"{result['icir']:.4f}",
            '多空收益': f"{result['long_short_mean']:.4f}",
            '多空夏普': f"{result['long_short_sharpe']:.4f}",
            '单调性': f"{result['monotonicity']:.4f}",
        })
    
    if portfolio_table:
        portfolio_df = pd.DataFrame(portfolio_table)
        report_lines.append("### 3.1 组合表现对比\n\n")
        report_lines.append(portfolio_df.to_markdown(index=False))
        report_lines.append("\n\n")
    
    report_lines.append("## 四、研究结论与建议\n\n")
    
    report_lines.append("### 4.1 因子选择建议\n\n")
    report_lines.append("基于以上分析，建议：\n\n")
    report_lines.append("1. **优先选择单调性好、IC高的因子**：这些因子具有较强的预测能力\n")
    report_lines.append("2. **避免高相关性因子同时使用**：高相关性因子会降低组合的多样性\n")
    report_lines.append("3. **关注换手率**：换手率过高的因子会增加交易成本\n")
    report_lines.append("4. **考虑因子稳定性**：自相关性高的因子更稳定\n\n")
    
    report_lines.append("### 4.2 组合构建建议\n\n")
    report_lines.append("1. **ICIR加权通常优于等权**：能更好地利用因子信息\n")
    report_lines.append("2. **定期重新评估因子权重**：市场环境变化可能影响因子表现\n")
    report_lines.append("3. **控制因子数量**：并非越多越好，建议 3-5 个独立因子\n")
    report_lines.append("4. **结合其他分析**：如因子衰减、稳健性测试等\n\n")
    
    report_lines.append("### 4.3 后续研究方向\n\n")
    report_lines.append("1. 行业中性化分析\n")
    report_lines.append("2. 市值中性化分析\n")
    report_lines.append("3. 动态因子权重调整\n")
    report_lines.append("4. 因子衰减分析\n")
    report_lines.append("5. 不同市场环境下的稳健性测试\n")
    
    report_content = ''.join(report_lines)
    
    report_path = output_dir / 'factor_analysis_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"  报告已保存到: {report_path}")


def main():
    """主函数"""
    print("=" * 60)
    print("因子分层与相关性分析研究")
    print("=" * 60)
    
    POOL_TYPE = 'hs300_zz500'
    START_DATE = '2019-01-01'
    END_DATE = '2024-12-31'
    MAX_WORKERS = 20
    
    FACTOR_CONFIGS = [
        {
            'name': 'momentum_20',
            'class': MomentumFactor,
            'params': {'period': 20},
        },
        {
            'name': 'rsi_14',
            'class': RSIFactor,
            'params': {'period': 14},
        },
        {
            'name': 'volatility_20',
            'class': HistoricalVolatilityFactor,
            'params': {'period': 20, 'annualize': False},
        },
        {
            'name': 'bias_20',
            'class': BiasFactor,
            'params': {'period': 20, 'ma_type': 'sma'},
        },
        {
            'name': 'macd',
            'class': MACDFactor,
            'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
        },
    ]
    
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
    
    symbols = list(set(symbols))
    print(f"股票池总计: {len(symbols)} 只")
    
    print(f"\n获取数据: {START_DATE} 至 {END_DATE}")
    print(f"(并发获取，线程数: {MAX_WORKERS})")
    
    try:
        price_data = get_stock_data(symbols, START_DATE, END_DATE, max_workers=MAX_WORKERS)
        print(f"获取到 {len(price_data)} 只股票的数据")
    except Exception as e:
        print(f"获取数据失败: {e}")
        return
    
    price_df_dict = {}
    for symbol, df in price_data.items():
        price_df_dict[symbol] = df['close']
    
    price_df = pd.DataFrame(price_df_dict)
    price_df.index = pd.to_datetime(price_df.index)
    price_df = price_df.sort_index()
    
    print(f"价格数据: {len(price_df)} 天, {len(price_df.columns)} 只股票")
    
    factor_values = compute_factors(price_data, FACTOR_CONFIGS)
    
    factor_values = preprocess_factors(factor_values, winsorize=True, standardize=True)
    
    layering_results = run_layering_analysis(factor_values, price_df, n_groups=5)
    
    correlation_results = run_correlation_analysis(factor_values, price_df, method='spearman')
    
    portfolio_results = {}
    portfolio_factors = {}
    
    for method in ['equal_weight', 'ic_weight', 'icir_weight']:
        portfolio_factor, weights = construct_factor_portfolio(
            factor_values, correlation_results['ic_results'], method=method
        )
        portfolio_factors[method] = portfolio_factor
        
        portfolio_name = {
            'equal_weight': '等权组合',
            'ic_weight': 'IC加权组合',
            'icir_weight': 'ICIR加权组合',
        }[method]
        
        result = evaluate_portfolio(portfolio_factor, price_df, portfolio_name)
        portfolio_results[portfolio_name] = result
    
    print("\n" + "=" * 60)
    print("生成可视化图表和报告")
    print("=" * 60)
    
    layering_dir = OUTPUT_BASE_DIR / 'layering_analysis'
    correlation_dir = OUTPUT_BASE_DIR / 'correlation_analysis'
    portfolio_dir = OUTPUT_BASE_DIR / 'portfolio_analysis'
    reports_dir = OUTPUT_BASE_DIR / 'reports'
    
    plot_layering_comparison(layering_results, layering_dir)
    
    plot_correlation_heatmap(correlation_results['correlation_matrix'], correlation_dir)
    
    plot_ic_comparison(correlation_results['ic_results'], correlation_dir)
    
    generate_report(layering_results, correlation_results, portfolio_results, reports_dir)
    
    print("\n" + "=" * 60)
    print("研究完成！")
    print("=" * 60)
    print(f"\n结果保存在: {OUTPUT_BASE_DIR}")
    print(f"  - 分层分析: {layering_dir}")
    print(f"  - 相关性分析: {correlation_dir}")
    print(f"  - 组合分析: {portfolio_dir}")
    print(f"  - 研究报告: {reports_dir / 'factor_analysis_report.md'}")


if __name__ == "__main__":
    main()
