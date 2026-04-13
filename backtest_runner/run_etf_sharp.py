"""
ETF夏普比率轮动策略运行示例

演示如何使用四因子综合评分进行ETF轮动策略回测。
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy import ETFSharpStrategy
from trader_center.backtest.strategy.factor_scorer import ETF_SHARP_FACTOR_CONFIGS, DEFAULT_NORMALIZATION_CONFIG

ASSET_CONFIG = {
    # 宽基指数
    '510300.SH': {'name': '沪深300ETF', 'category': 'equity_cn'},
    '159915.SZ': {'name': '创业板ETF', 'category': 'equity_cn'},

    # 海外
    '513100.SH': {'name': '纳指ETF', 'category': 'equity_us'},

    # 策略
    # '512890.SH': {'name': '红利低波ETF', 'category': 'equity_cn'},

    # 行业指数


    # 债券
    '511010.SH': {'name': '国债ETF', 'category': 'bond'},  # 5年期国债
    # '511260.SH': {'name': '十年国债ETF', 'category': 'bond', 'theme': '长债'},          # 10年期国债

    # 商品
    '518880.SH': {'name': '黄金ETF', 'category': 'commodity'},
    '159981.SZ': {'name': '能源化工ETF', 'category': 'commodity'},
    # '159985.SZ': {'name': '豆粕ETF', 'category': 'commodity'},
    # '159980.SZ': {'name': '有色ETF', 'category': 'commodity'},
}

def main():
    print("=" * 60)
    print("ETF夏普比率轮动策略回测")
    print("=" * 60)
    
    print("\n因子配置:")
    for name, cfg in ETF_SHARP_FACTOR_CONFIGS.items():
        direction_str = "正向" if cfg['direction'] == 'positive' else "反向"
        params_str = ", ".join(f"{k}={v}" for k, v in cfg['params'].items())
        print(f"  {name} ({params_str}): 权重 {cfg['weight']:.0%}, 方向 {direction_str}")
    
    print("\n归一化配置:")
    print(f"  极端值处理: Winsorize {DEFAULT_NORMALIZATION_CONFIG['winsorize']['lower']:.1%}-{DEFAULT_NORMALIZATION_CONFIG['winsorize']['upper']:.1%}")
    print(f"  标准化方法: {DEFAULT_NORMALIZATION_CONFIG['standardize']['method']}")
    
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
    print(f"  再平衡频率: 5个交易日")
    print(f"  持仓数量: 3")
    print(f"  因子计算窗口: 60天")
    print(f"  权重分配方法: equal (等权)")
    print(f"  订单执行: 次日收盘价 (exec_type='close')")
    print(f"  止损比例: 10%")
    print(f"  移动止盈: 5%")
    print(f"  止损冷却期: 5个交易日")
    
    print("\n开始回测...")
    
    result = runner.run(
        strategy=ETFSharpStrategy,
        symbols=symbols,
        start="2019-01-01",
        end="2026-03-29",
        initial_cash=config.initial_cash,
        strategy_params={
            'rebalance_freq': 5,
            'top_n': 3,
            'lookback': 60,
            'factor_configs': ETF_SHARP_FACTOR_CONFIGS,
            'normalization_config': DEFAULT_NORMALIZATION_CONFIG,
            'weighting_method': 'equal',
            'exec_type': 'close',
            'stop_loss_pct': 0.10,
            'trailing_stop_pct': 0.05,
            'trailing_stop_enabled': True,
            'stop_loss_cooldown': 5,
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
该策略使用四因子综合评分进行ETF轮动:

1. 因子选择
   - 夏普比率因子 (sharpe_ratio): 核心因子，衡量风险调整收益
   - 动量因子 (momentum): 捕捉价格趋势
   - 波动率因子 (historical_volatility): 风险约束
   - 最大回撤因子 (max_drawdown): 尾部风险约束

2. 因子权重
   - 夏普比率: 40% (核心因子)
   - 动量: 30%
   - 波动率: 20%
   - 最大回撤: 10%

3. 归一化处理
   - Step 1: 极端值处理 (Winsorize 2.5%-97.5%)
   - Step 2: 横截面标准化 (Z-score)
   - Step 3: 方向调整 (正向保持，反向取负)
   - Step 4: 加权合成综合得分

4. 资产选择
   - 选择得分最高的3个ETF
   - 等权分配 (每个约31.7%)
   - 排除止损冷却期内的资产

5. 定期轮动
   - 每5个交易日再平衡一次
   - 根据最新因子得分调整持仓

6. 风控机制
   - 单资产止损: 亏损超过10%时止损卖出
   - 移动止盈: 盈利后从最高点回撤超过5%时止盈
   - 止损冷却期: 止损后5个交易日内不再买入该资产

策略特点:
- 风险调整收益导向: 以夏普比率为核心
- 多因子综合评分: 避免单一因子偏差
- 归一化处理: 提高策略鲁棒性
- 动态轮动: 适应市场变化
- 止损保护: 控制单资产最大亏损

扩展建议:
- 添加更多因子类型 (基本面、另类数据)
- 根据因子IC动态调整权重
- 添加波动率目标控制
- 添加市场择时模块
""")


if __name__ == "__main__":
    main()
