"""
分仓波段策略运行示例

演示如何运行分仓波段策略的回测。
将仓位分为底仓和波段仓两部分，底仓长期持有，波段仓围绕60日均线进行高抛低吸。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径，确保使用当前开发代码而非已安装包
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy.band_position import BandPositionStrategy


def main():
    print("=" * 60)
    print("分仓波段策略回测")
    print("=" * 60)

    # 策略配置展示
    print("\n策略配置:")
    print("  底仓比例: 80% (一次性买入并长期持有)")
    print("  波段比例: 20% (用于波段操作)")
    print("  均线周期: 60日")
    print("  定投批次: 5次 (跌破均线后分5批投入)")
    print("  移动止盈: 5% (从最高点回撤5%触发卖出)")

    # 股票池 - 红利低波ETF
    symbols = ["512890.SH"]

    # 回测配置
    config = BacktestConfig(
        initial_cash=100000,
        auto_save_trades=True,
        auto_save_plot=True,
        enable_quantstats=True,
        benchmark_symbol="512890.SH",  # 沪深300作为基准
        auto_save_report=True,
        auto_open_report=False,
    )

    # 创建回测运行器
    runner = BacktestRunner(
        config=config,
        enable_plot=True,
        plot_style="line",
    )

    # 策略参数
    strategy_params = {
        'base_position_pct': 50,      # 底仓80%
        'ma_period': 60,               # 60日均线
        'dca_batches': 5,              # 分5批定投
        'trailing_stop_pct': 5,        # 5%移动止盈
        'dca_interval': 5,             # 定投间隔天
    }

    print("\n回测参数:")
    print(f"  初始资金: {config.initial_cash:,.0f} 元")
    print(f"  回测区间: 2020-01-01 ~ 2024-12-31")
    print(f"  标的: 红利低波ETF (512890.SH)")
    print(f"  基准: 沪深300指数 (000300.SH)")

    print("\n开始回测...")
    print("-" * 60)

    # 执行回测
    result = runner.run(
        strategy=BandPositionStrategy,
        symbols=symbols,
        start="2020-01-01",
        end="2024-12-31",
        initial_cash=config.initial_cash,
        strategy_params=strategy_params
    )

    # 结果展示
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)

    # 基本结果
    print(f"\n策略名称: {result.strategy_name}")
    print(f"回测区间: {result.start_date} ~ {result.end_date}")
    print(f"回测时长: {result.duration_seconds:.2f} 秒")

    # 收益指标
    print("\n收益指标:")
    print(f"  初始资金: {result.initial_cash:,.2f} 元")
    print(f"  最终资产: {result.final_value:,.2f} 元")
    print(f"  总收益:   {result.final_value - result.initial_cash:+,.2f} 元")
    print(f"  收益率:   {result.return_pct:+.2%}")

    # 风险指标
    print("\n风险指标:")
    print(f"  最大回撤: {result.max_drawdown:.2%}")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  索提诺比率: {result.sortino_ratio:.2f}")

    # 交易统计
    print("\n交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  胜率:       {result.win_rate:.1%}")
    print(f"  盈亏比:     {result.profit_factor:.2f}")

    # 分析器结果
    if result.analyzer_results:
        print("\n分析器结果:")
        print(f"  SQN:         {result.analyzer_results.get('sqn', 0):.2f}")
        print(f"  BT夏普比率:  {result.analyzer_results.get('sharpe_ratio', 0):.2f}")

    # 输出文件
    if result.log_files:
        print("\n输出文件:")
        for name, path in result.log_files.items():
            print(f"  {name}: {path}")

    # 打开报告
    if result.report_path:
        print(f"\n正在打开报告: {result.report_path}")
        result.open_report()

    print("\n" + "=" * 60)
    print("策略说明")
    print("=" * 60)
    print("""
该策略实现了分仓波段交易逻辑：

1. 仓位分配
   - 底仓 (base_position_pct%): 回测开始时一次性买入并长期持有
   - 波段仓 (100% - base_position_pct%): 用于波段操作，高抛低吸

2. 买入逻辑（波段仓）
   - 当价格跌破60日均线时，触发定投买入信号
   - 将波段资金分为多批(dca_batches)投入，降低择时风险
   - 每批投入等额资金，买入股数为100的整数倍(A股规则)

3. 卖出逻辑（波段仓）
   - 当价格回到60日均线以上后，启用移动止盈机制
   - 追踪持仓期间的最高价，记录最高点
   - 当价格从最高点回撤超过设定比例(trailing_stop_pct%)时卖出
   - 卖出后重置波段仓状态，等待下一次波段机会

4. 特殊模式
   - 当 base_position_pct 设为 100% 时，策略退化为买入持有策略
   - 此时所有资金一次性买入，不再进行波段操作
   - 适用于长期看好标的、不希望频繁交易的场景

5. 参数说明
   - base_position_pct: 底仓比例，默认80% (范围: 0-100)
   - ma_period: 移动平均线周期，默认60日 (范围: 5-250)
   - dca_batches: 定投批次，默认5次 (范围: 1-20)
   - trailing_stop_pct: 移动止盈比例，默认5% (范围: 1-20)

扩展建议:
- 可以尝试调整底仓比例，对比80%、90%、100%的表现差异
- 可以修改均线周期(如30日、90日)，测试不同周期的效果
- 可以增加止损逻辑，在跌破均线一定比例后止损而非定投
- 可以尝试多标的组合，每只标的独立执行分仓策略
- 可以加入择时过滤器，如大盘MACD为正时才开启波段操作
""")


if __name__ == "__main__":
    main()
