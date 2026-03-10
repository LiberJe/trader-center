"""
大类资产等权持有策略运行示例

演示如何运行等权资产配置策略的回测。
"""

from datetime import date
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy import EqualWeightAssetAllocation, ASSET_CONFIG


def main():
    print("=" * 60)
    print("大类资产等权持有策略回测")
    print("=" * 60)
    
    print("\n资产配置:")
    for symbol, info in ASSET_CONFIG.items():
        print(f"  {info['name']} ({symbol}): 20%")
    
    symbols = list(ASSET_CONFIG.keys())
    
    config = BacktestConfig(
        initial_cash=1000000,
        auto_save_trades=True,
        auto_save_plot=True,
        enable_quantstats=True,
        benchmark_symbol="000300.SH",
        auto_save_report=True,
        auto_open_report=False,
    )
    
    runner = BacktestRunner(
        config=config,
        enable_plot=True,
        plot_style="line",
    )
    
    print("\n回测参数:")
    print(f"  初始资金: {config.initial_cash:,.0f} 元")
    print(f"  回测区间: 2023-01-01 ~ 2024-12-31")
    print(f"  再平衡频率: 30个交易日")
    print(f"  目标权重: 19% (每个资产)")
    
    print("\n开始回测...")
    
    result = runner.run(
        strategy=EqualWeightAssetAllocation,
        symbols=symbols,
        start="2020-01-01",
        end="2024-12-31",
        initial_cash=config.initial_cash,
        strategy_params={
            'rebalance_freq': 30,
            'target_weight': 0.19,
            'tolerance': 0.05,
        }
    )
    
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    if result.error_message:
        print(f"\n错误: {result.error_message}")
        return
    
    print(f"\n策略名称: {result.strategy_name}")
    print(f"回测区间: {result.start_date} ~ {result.end_date}")
    print(f"回测时长: {result.duration_seconds:.2f} 秒")
    
    print("\n收益指标:")
    print(f"  初始资金: {result.initial_cash:,.2f} 元")
    print(f"  最终资产: {result.final_value:,.2f} 元")
    print(f"  总收益:   {result.final_value - result.initial_cash:+,.2f} 元")
    print(f"  收益率:   {result.return_pct:+.2%}")
    
    print("\n风险指标:")
    print(f"  最大回撤: {result.calculate_max_drawdown():.2%}")
    print(f"  夏普比率: {result.calculate_sharpe_ratio():.2f}")
    
    print("\n交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  胜率:       {result.win_rate:.1%}")
    print(f"  盈亏比:     {result.profit_factor:.2f}")
    
    if result.analyzer_results:
        print("\n分析器结果:")
        print(f"  SQN:         {result.analyzer_results.get('sqn', 0):.2f}")
        print(f"  BT夏普比率:  {result.analyzer_results.get('sharpe_ratio', 0):.2f}")
    
    if result.log_files:
        print("\n输出文件:")
        for name, path in result.log_files.items():
            print(f"  {name}: {path}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
