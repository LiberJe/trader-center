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
    print("  底仓比例: 50% (一次性买入并长期持有)")
    print("  波段比例: 50% (用于波段操作)")
    print("  均线周期: 60日")
    print("  定投批次: 5次 (跌破均线后分5批投入)")
    print("  移动止盈: 动态收紧 (基础3%，BIAS≥8%→2%，≥10%→1.5%，≥12%→1%，确认期3bar)")
    print("  BIAS加权: 启用 (时间+跌幅双重衰减)")
    print("  杠杆系统: 0% (最大杠杆资金占总资金0%，年化利率3%)")

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
        'base_position_pct': 50,       # 底仓50%
        'ma_period': 60,               # 60日均线
        'dca_batches': 5,              # 分5批定投
        'dca_interval': 5,             # 定投间隔天
        'dca_trigger_bias': 0,         # 定投触发阈值，BIAS60 <= -3%才开始定投
        'trailing_stop_pct': 3,        # 基础移动止盈3%
        # 动态止盈参数
        'use_dynamic_trailing_stop': True,  # 启用动态止盈
        'trailing_tighten_bias_1': 8.0,     # BIAS≥8% 止盈收紧到2%
        'trailing_tighten_stop_1': 2.0,
        'trailing_tighten_bias_2': 10.0,    # BIAS≥10% 止盈收紧到1.5%
        'trailing_tighten_stop_2': 1.5,
        'trailing_tighten_bias_3': 12.0,    # BIAS≥12% 止盈收紧到1%
        'trailing_tighten_stop_3': 1.0,
        # 移动止盈激活参数
        'trailing_activation_bars': 3,  # 突破均线后需站稳3个交易bar才启用移动止盈
        # BIAS智能加权参数
        'use_bias_weighting': True,    # 启用BIAS加权
        'min_dca_weight': 1.0,         # 最小加仓权重1.0x
        'max_dca_weight': 3.0,         # 最大加仓权重3.0x
        'time_decay_days': 30,         # 时间衰减周期30个交易日
        'time_factor_ratio': 0.4,      # 时间因子占比40%
        'drop_factor_ratio': 0.6,      # 跌幅因子占比60%
        'max_bias_ref': 20,            # 最大参考跌幅20%
        # 杠杆系统参数
        'max_leverage_pct': 0,         # 最大杠杆资金占总资金0%（关闭杠杆）
        'leverage_interest_rate': 3.0, # 杠杆年化利率3%
        # === 底仓动态减持参数（方案A）===
        'enable_base_reduce': True,           # 是否启用底仓动态减持
        'base_reduce_bias_threshold': 15.0,   # BIAS60 >= 此值触发减持（%）
        'base_reduce_ratio': 0.5,             # 减持比例（相对初始底仓市值）
        'base_reduce_min_hold': 0.5,          # 减持后最少保留比例（相对初始底仓市值）
        'base_restore_bias_threshold': 0,   # BIAS60 <= 此值触发回补（%）
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
        end="2026-04-10",
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
    print(f"  最大回撤: {result.calculate_max_drawdown():.2%}")
    print(f"  夏普比率: {result.calculate_sharpe_ratio():.2f}")

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
    report_path = result.log_files.get('performance_report')
    if report_path:
        print(f"\n正在打开报告: {report_path}")
        import webbrowser
        webbrowser.open(report_path)

    print("\n" + "=" * 60)
    print("策略说明")
    print("=" * 60)
    print("""
该策略实现了分仓波段交易逻辑（BIAS智能加权 + 动态收紧回撤版）：

1. 仓位分配
   - 底仓 (base_position_pct%): 回测开始时一次性买入并长期持有
   - 波段仓 (100% - base_position_pct%): 用于波段操作，高抛低吸

2. 买入逻辑（波段仓）- BIAS智能加权定投
   - 当价格跌破60日均线，且BIAS60 <= -dca_trigger_bias%时，触发定投买入信号
   - 加仓权重 = min_weight + (max_weight - min_weight) × (time_factor × time_ratio + drop_factor × drop_ratio)
   - 时间因子: 跌破均线时间越长，加仓权重越高（基于交易bar数，按time_decay_days线性增长）
   - 跌幅因子: BIAS60（乖离率）绝对值越大，加仓权重越高（基于当前跌幅/max_bias_ref计算）
   - 单次加仓不超过剩余波段资金的50%，防止过早打光资金

3. 卖出逻辑（波段仓）- 动态移动止盈
   - 当价格回到60日均线以上后，进入“突破确认期”（trailing_activation_bars，默认3bar）
   - 确认期内只追踪最高价，但不真正触发移动止盈，防止暴跌后的假突破被立刻洗出
   - 确认期结束后，若价格从突破后的最高价回撤超过阈值，才执行卖出
   - 基础回撤比例: trailing_stop_pct%（默认3%）
   - 动态收紧: BIAS越高，止盈线越紧，避免大幅回吐利润
     * BIAS >= 8%  → 止盈收紧到 2%
     * BIAS >= 10% → 止盈收紧到 1.5%
     * BIAS >= 12% → 止盈收紧到 1%
   - 当价格从最高点回撤超过当前动态止盈比例时卖出
   - 卖出后重置波段仓状态和BIAS计时，等待下一次波段机会

4. BIAS加权参数说明
   - use_bias_weighting: 是否启用BIAS加权，默认True
   - min_dca_weight: 最小加仓权重，默认1.0x
   - max_dca_weight: 最大加仓权重，默认3.0x
   - time_decay_days: 时间衰减周期（交易bar数），默认30
   - time_factor_ratio: 时间因子占比，默认40%
   - drop_factor_ratio: 跌幅因子占比，默认60%
   - max_bias_ref: 最大参考跌幅，默认20%

5. 定投触发阈值
   - dca_trigger_bias: 默认3.0%，即BIAS60跌破-3%才开始定投
   - 作用: 避免小幅回踩均线就过早建仓，过滤无效震荡

6. 杠杆系统说明
   - max_leverage_pct: 最大杠杆资金占初始总资金百分比，默认20%
   - leverage_interest_rate: 杠杆年化利率，默认3%
   - 触发条件: 5份自有资金定投用完后，若价格仍在60日均线下方，启用杠杆加仓
   - 还款条件: 波段仓移动止盈清仓时，从卖出回款中扣除杠杆本金+利息
   - 计息方式: 杠杆启用日至清仓日之间的自然日天数 × 年化利率 / 365

7. 特殊模式
   - 当 base_position_pct 设为 100% 时，策略退化为买入持有策略
   - 当 use_bias_weighting 设为 False 时，退化为等额定投模式
   - 当 use_dynamic_trailing_stop 设为 False 时，退化为固定比例移动止盈

扩展建议:
- 可以尝试调整底仓比例，对比50%、80%、100%的表现差异
- 可以调整max_dca_weight和因子占比，测试不同激进程度的效果
- 可以修改动态止盈档位阈值，对比不同收紧速度的绩效差异
- 可以对比加权定投 vs 等额定投的绩效差异
""")


if __name__ == "__main__":
    main()
