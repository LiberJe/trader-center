"""
因子分层与相关性分析研究 - 快速测试版本

使用少量股票和短时间范围进行快速测试
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

from trader_center.factor.mining.layering import LayeringAnalyzer
from trader_center.factor.mining.correlation import CorrelationAnalyzer
from trader_center.factor.mining.ic_analysis import ICAnalyzer
from trader_center.factor.library.technical.momentum import MomentumFactor, RSIFactor, MACDFactor
from trader_center.factor.library.technical.volatility import HistoricalVolatilityFactor
from trader_center.factor.library.technical.reversal import BiasFactor
from trader_center.factor.mining.preprocessing.winsorization import winsorize_cross_sectional
from trader_center.factor.mining.preprocessing.standardization import standardize_cross_sectional


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_BASE_DIR = PROJECT_ROOT / 'factor_research_results' / 'layering_correlation_analysis_test'


plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def create_sample_data(n_dates: int = 252, n_assets: int = 50) -> tuple:
    """
    创建示例数据
    
    Args:
        n_dates: 交易日数量
        n_assets: 资产数量
    
    Returns:
        (价格DataFrame, 股票数据字典)
    """
    print("\n创建示例数据...")
    
    np.random.seed(42)
    
    dates = pd.date_range('2023-01-01', periods=n_dates, freq='B')
    assets = [f'Stock_{i:03d}' for i in range(n_assets)]
    
    price_data = {}
    for asset in assets:
        base_price = np.random.uniform(10, 100)
        returns = np.random.randn(n_dates) * 0.02
        prices = base_price * (1 + returns).cumprod()
        
        df = pd.DataFrame({
            'open': prices * np.random.uniform(0.98, 1.02, n_dates),
            'high': prices * np.random.uniform(1.0, 1.05, n_dates),
            'low': prices * np.random.uniform(0.95, 1.0, n_dates),
            'close': prices,
            'volume': np.random.uniform(1e6, 1e7, n_dates),
        }, index=dates)
        
        price_data[asset] = df
    
    price_df = pd.DataFrame({asset: df['close'] for asset, df in price_data.items()})
    
    print(f"创建 {n_assets} 只股票，{n_dates} 天的数据")
    
    return price_df, price_data


def compute_factors(
    price_data: dict,
    factor_configs: list,
) -> dict:
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
        factor_values[factor_name] = factor_df
    
    print(f"完成，共计算 {len(factor_values)} 个因子")
    
    return factor_values


def preprocess_factors(
    factor_values: dict,
    winsorize: bool = True,
    standardize: bool = True,
) -> dict:
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
    factor_values: dict,
    price_df: pd.DataFrame,
    n_groups: int = 5,
) -> dict:
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
    
    forward_returns = price_df.pct_change().shift(-1)
    
    layering_results = {}
    
    for factor_name, factor_df in factor_values.items():
        print(f"\n分析因子: {factor_name}")
        
        analyzer = LayeringAnalyzer(n_groups=n_groups)
        
        try:
            result = analyzer.compute(factor_df, forward_returns)
            
            monotonicity = analyzer.compute_monotonicity()
            
            turnover = analyzer.compute_turnover(factor_df, top_n=10)
            
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
    factor_values: dict,
    price_df: pd.DataFrame,
    method: str = 'spearman',
) -> dict:
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
    
    forward_returns = price_df.pct_change().shift(-1)
    
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
    factor_values: dict,
    ic_results: dict,
    method: str = 'equal_weight',
) -> tuple:
    """
    构建多因子组合
    
    Args:
        factor_values: 因子数据字典
        ic_results: IC分析结果
        method: 加权方法
    
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
) -> dict:
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
    
    forward_returns = price_df.pct_change().shift(-1)
    
    ic_analyzer = ICAnalyzer()
    ic_result = ic_analyzer.compute(portfolio_factor, forward_returns)
    
    layering_analyzer = LayeringAnalyzer(n_groups=5)
    layering_result = layering_analyzer.compute(portfolio_factor, forward_returns)
    
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


def plot_results(
    layering_results: dict,
    correlation_results: dict,
    output_dir: Path,
):
    """
    绘制结果图表
    
    Args:
        layering_results: 分层分析结果
        correlation_results: 相关性分析结果
        output_dir: 输出目录
    """
    print("\n生成可视化图表...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
    ax1.grid(True, alpha=0.3, axis='y')
    
    ax2 = axes[1]
    ic_results = correlation_results['ic_results']
    ic_means = [ic_results[name]['ic_mean'] for name in factor_names]
    
    colors = ['green' if ic > 0.02 else 'orange' if ic > 0 else 'red' for ic in ic_means]
    ax2.bar(range(len(factor_names)), ic_means, color=colors, alpha=0.7)
    ax2.set_xticks(range(len(factor_names)))
    ax2.set_xticklabels(factor_names, rotation=45, ha='right')
    ax2.set_title('因子IC均值对比', fontsize=12, fontweight='bold')
    ax2.set_ylabel('IC均值')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    save_path = output_dir / 'factor_metrics_comparison.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"  保存到: {save_path}")
    plt.close()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    corr_matrix = correlation_results['correlation_matrix']
    
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


def main():
    """主函数"""
    print("=" * 60)
    print("因子分层与相关性分析研究 - 快速测试版本")
    print("=" * 60)
    
    price_df, price_data = create_sample_data(n_dates=252, n_assets=50)
    
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
    
    factor_values = compute_factors(price_data, FACTOR_CONFIGS)
    
    factor_values = preprocess_factors(factor_values, winsorize=True, standardize=True)
    
    layering_results = run_layering_analysis(factor_values, price_df, n_groups=5)
    
    correlation_results = run_correlation_analysis(factor_values, price_df, method='spearman')
    
    portfolio_results = {}
    
    for method in ['equal_weight', 'ic_weight', 'icir_weight']:
        portfolio_factor, weights = construct_factor_portfolio(
            factor_values, correlation_results['ic_results'], method=method
        )
        
        portfolio_name = {
            'equal_weight': '等权组合',
            'ic_weight': 'IC加权组合',
            'icir_weight': 'ICIR加权组合',
        }[method]
        
        result = evaluate_portfolio(portfolio_factor, price_df, portfolio_name)
        portfolio_results[portfolio_name] = result
    
    print("\n" + "=" * 60)
    print("生成可视化图表")
    print("=" * 60)
    
    output_dir = OUTPUT_BASE_DIR / 'figures'
    plot_results(layering_results, correlation_results, output_dir)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print(f"\n结果保存在: {OUTPUT_BASE_DIR}")
    
    print("\n" + "=" * 60)
    print("研究结果总结")
    print("=" * 60)
    
    print("\n1. 因子分层分析结果:")
    for factor_name, result in layering_results.items():
        if result:
            print(f"  {factor_name}:")
            print(f"    单调性: {result['monotonicity']:.4f}")
            print(f"    多空收益: {result['long_short_mean']:.4f}")
            print(f"    多空夏普: {result['long_short_sharpe']:.4f}")
    
    print("\n2. 因子IC表现:")
    for factor_name, ic_result in correlation_results['ic_results'].items():
        print(f"  {factor_name}: IC={ic_result['ic_mean']:.4f}, ICIR={ic_result['icir']:.4f}")
    
    print("\n3. 多因子组合表现:")
    for portfolio_name, result in portfolio_results.items():
        print(f"  {portfolio_name}:")
        print(f"    IC均值: {result['ic_mean']:.4f}")
        print(f"    ICIR: {result['icir']:.4f}")
        print(f"    多空夏普: {result['long_short_sharpe']:.4f}")


if __name__ == "__main__":
    main()
