"""
多因子轮动策略运行示例

演示如何使用因子库构建多因子轮动策略并运行回测。
"""

from datetime import date
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy import MultiFactorRotationStrategy, ASSET_CONFIG
from trader_center.backtest.strategy.factor_scorer import DEFAULT_FACTOR_CONFIGS


def main():
    print("=" * 60)
    print("多因子轮动策略回测")
    print("=" * 60)
    
    factor_configs = {
        'momentum': {
            'weight': 0.30,
            'direction': 'positive',
            'params': {'period': 20},
        },
        'trend_strength': {
            'weight': 0.25,
            'direction': 'positive',
            'params': {'period': 20},
        },
        'rsi': {
            'weight': 0.15,
            'direction': 'negative',
            'params': {'period': 14},
        },
        'historical_volatility': {
            'weight': 0.15,
            'direction': 'negative',
            'params': {'period': 20},
        },
        'atr': {
            'weight': 0.15,
            'direction': 'negative',
            'params': {'period': 14},
        },
    }
    
    print("\n因子配置:")
    for name, cfg in factor_configs.items():
        direction_str = "正向" if cfg['direction'] == 'positive' else "反向"
        params_str = ", ".join(f"{k}={v}" for k, v in cfg['params'].items())
        print(f"  {name} ({params_str}): 权重 {cfg['weight']:.0%}, 方向 {direction_str}")
    
    print("\n资产池:")
    for symbol, info in ASSET_CONFIG.items():
        print(f"  {info['name']} ({symbol})")
    
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
    print(f"  回测区间: 2020-01-01 ~ 2024-12-31")
    print(f"  再平衡频率: 20个交易日")
    print(f"  持仓数量: 3")
    print(f"  因子计算窗口: 60天")
    
    print("\n开始回测...")
    
    result = runner.run(
        strategy=MultiFactorRotationStrategy,
        symbols=symbols,
        start="2019-01-01",
        end="2026-03-10",
        initial_cash=config.initial_cash,
        strategy_params={
            'rebalance_freq': 20,
            'top_n': 3,
            'factor_configs': factor_configs,
            'lookback': 60,
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
    print("策略说明")
    print("=" * 60)
    print("""
该策略演示了如何使用因子库构建多因子轮动策略:

1. 因子选择
   - 动量因子 (momentum): 捕捉价格趋势
   - 趋势强度因子 (trend_strength): 衡量趋势的可靠性
   - RSI因子 (rsi): 反转信号，超卖时得分高
   - 历史波动率因子 (historical_volatility): 低波动得分高
   - ATR因子 (atr): 低波动得分高

2. 因子打分
   - 计算每个资产的因子值
   - 横截面标准化 (Z-score)
   - 加权合成综合得分

3. 资产选择
   - 选择得分最高的3个资产
   - 等权分配 (每个约33%)

4. 定期轮动
   - 每20个交易日再平衡一次
   - 根据最新因子得分调整持仓

扩展建议:
- 添加更多因子类型 (基本面、另类数据)
- 根据因子IC动态调整权重
- 添加风险控制 (波动率目标、最大回撤控制)
- 添加市场择时模块
""")


if __name__ == "__main__":
    main()
