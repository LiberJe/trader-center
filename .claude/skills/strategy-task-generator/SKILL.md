---
name: strategy-task-generator
description: |
  生成 trader_center 项目 `tasks/` 目录下的策略日报任务运行器。
  当用户提到"创建一个xx策略的任务"、"生成策略日报任务"、"给xx策略写个runner"、"创建任务运行器"等时触发。
  生成的文件格式必须参考 `tasks/etf_sharp_runner.py`，包含资产配置、回测执行、Markdown日报生成等完整逻辑。
---

# 策略日报任务运行器生成器

此技能用于自动生成策略日报任务运行器脚本，保存到项目根目录的 `tasks/` 下。

生成的运行器参考 `tasks/etf_sharp_runner.py` 的结构，具备以下能力：
- 定义资产池和配置
- 运行策略回测
- 生成结构化的 Markdown 日报
- 保存报告到 `task_reports/{日期}/` 目录

## 触发条件

用户输入中出现以下意图时立即使用此技能：
- "创建一个XX策略的任务"
- "给XX策略生成一个任务runner"
- "写一个策略日报运行器"
- "生成一个可执行的任务脚本"
- "为XX策略添加每日报告任务"

## 输出要求

1. **文件路径**：`tasks/{strategy_name_snake}_runner.py`
2. **文件内容**：参考 `tasks/etf_sharp_runner.py` 的完整结构
3. **直接写入文件**：不需要与用户确认，直接生成并保存

## 文件结构模板

```python
"""
{策略中文名}任务运行器

{一句话描述策略功能}
生成每日报告，指导次日交易决策。
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, datetime
from trader_center.backtest import BacktestRunner, BacktestConfig
from {strategy_module} import {strategy_class}

ASSET_CONFIG = {
    # 在此定义资产池
    {asset_entries}
}


def generate_daily_report(result, report_dir: Path, today_str: str, today_display: str):
    """
    生成每日Markdown报告

    Args:
        result: BacktestResult 回测结果
        report_dir: 报告目录
        today_str: 日期字符串 (YYYYMMDD)
        today_display: 显示日期 (YYYY年MM月DD日)
    """
    # 提取最新持仓数据
    latest_positions = []
    if result.position_log:
        import pandas as pd
        df_pos = pd.DataFrame(result.position_log)
        if not df_pos.empty:
            df_pos['date'] = pd.to_datetime(df_pos['date']).dt.date
            latest_date = df_pos['date'].max()
            latest_df = df_pos[df_pos['date'] == latest_date]
            latest_positions = latest_df.drop_duplicates(subset=['symbol'], keep='first').to_dict('records')

    # 提取最新资金数据
    latest_capital = {}
    if result.capital_log:
        import pandas as pd
        df_cap = pd.DataFrame(result.capital_log)
        if not df_cap.empty:
            df_cap['date'] = pd.to_datetime(df_cap['date']).dt.date
            latest_date = df_cap['date'].max()
            latest_capital = df_cap[df_cap['date'] == latest_date].iloc[0].to_dict()

    today = datetime.strptime(today_str, "%Y%m%d").date()

    # 提取当日成交
    today_orders = []
    if result.order_log:
        import pandas as pd
        df_orders = pd.DataFrame(result.order_log)
        if not df_orders.empty:
            df_orders['datetime'] = pd.to_datetime(df_orders['datetime'])
            today_orders = df_orders[
                (df_orders['datetime'].dt.date == today) &
                (df_orders['status'] == 'completed')
            ].to_dict('records')

    daily_return = latest_capital.get('daily_return', 0) * 100

    # 获取交易信号
    today_signals = []
    latest_signals = []
    if result.signal_log:
        import pandas as pd
        df_sig = pd.DataFrame(result.signal_log)
        if not df_sig.empty:
            df_sig['datetime'] = pd.to_datetime(df_sig['datetime'])
            signal_types = ['buy', 'rebalance', 'stop_loss', 'trailing_stop']
            df_sig = df_sig[df_sig['signal_type'].isin(signal_types)]
            today_signals = df_sig[df_sig['datetime'].dt.date == today].to_dict('records')
            latest_sig_date = df_sig['datetime'].dt.date.max()
            latest_signals = df_sig[df_sig['datetime'].dt.date == latest_sig_date].to_dict('records')

    report = f"""# {策略中文名}日报 - {today_display}

## 回测概览

| 指标 | 数值 |
|------|------|
| 回测区间 | {result.start_date} ~ {result.end_date} |
| 初始资金 | {result.initial_cash:,.0f} 元 |
| 当前总资产 | {result.final_value:,.2f} 元 |
| 累计收益率 | {result.return_pct:+.2%} |
| 当日收益 | {daily_return:+.2%} |
| 最大回撤 | {result.calculate_max_drawdown():.2%} |
| 夏普比率 | {result.calculate_sharpe_ratio():.2f} |
| 总交易次数 | {result.total_trades} |
| 胜率 | {result.win_rate:.1%} |
| 盈亏比 | {result.profit_factor:.2f} |

## 当前持仓 ({today_display})

"""

    if latest_positions:
        total_value = latest_capital.get('total_value', result.final_value)
        report += "| 资产 | 代码 | 持仓数量 | 成本价 | 当前价 | 市值 | 权重 | 盈亏 |\n"
        report += "|------|------|----------|--------|--------|------|------|------|\n"

        for pos in latest_positions:
            symbol = pos.get('symbol', '')
            name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
            size = pos.get('size', 0)
            cost = pos.get('cost_price', 0)
            current = pos.get('current_price', 0)
            mv = pos.get('market_value', 0)
            weight = mv / total_value * 100 if total_value > 0 else 0
            pnl = pos.get('pnl_ratio', 0) * 100

            report += f"| {name} | {symbol} | {size} | {cost:.2f} | {current:.2f} | {mv:,.0f} | {weight:.1f}% | {pnl:+.2f}% |\n"

        cash = latest_capital.get('cash', 0)
        cash_ratio = cash / total_value * 100 if total_value > 0 else 0
        report += f"\n**现金**: {cash:,.2f} 元 ({cash_ratio:.1f}%)\n"
    else:
        report += "*当前无持仓*\n"

    report += f"\n## 交易信号\n\n"

    if today_orders:
        report += "### 今日成交\n\n"
        report += "| 时间 | 类型 | 资产 | 数量 | 价格 | 金额 | 费用 |\n"
        report += "|------|------|------|------|------|------|------|\n"

        for order in today_orders:
            order_time = order.get('datetime', '')
            action = order.get('action', '')
            symbol = order.get('symbol', '')
            name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
            size = order.get('executed_size', 0) or 0
            price = order.get('executed_price', 0) or 0
            value = size * price
            commission = order.get('commission', 0) or 0

            report += f"| {order_time} | {action} | {name} | {size} | {price:.3f} | {value:,.0f} | {commission:.2f} |\n"
    else:
        report += "### 今日成交\n\n*今日无交易*\n"

    symbol_orders_map = {}
    for order in today_orders:
        symbol_orders_map.setdefault(order.get('symbol'), []).append(order)

    def _render_signals(signals, title):
        nonlocal report
        report += f"\n### {title}\n\n"
        for sig in signals:
            sig_type = sig.get('signal_type', '')
            symbol = sig.get('symbol', '')
            name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
            trigger = sig.get('trigger_condition', '')
            ind = sig.get('indicator_values', {}) or {}

            guidance_lines = []
            if sig_type == 'rebalance':
                current_w = float(ind.get('current_weight', 0))
                target_w = float(ind.get('target_weight', 0))
                delta = target_w - current_w
                if delta > 0:
                    guidance_lines.append(f"建议加仓约 {delta*100:.2f}% (目标权重 {target_w*100:.2f}%)")
                else:
                    guidance_lines.append(f"建议减仓约 {abs(delta)*100:.2f}% (目标权重 {target_w*100:.2f}%)")
            elif sig_type == 'buy':
                target_w = float(ind.get('target_weight', 0))
                guidance_lines.append(f"建议建仓至 {target_w*100:.2f}% 权重")
            elif sig_type in ('stop_loss', 'trailing_stop'):
                pos_size = int(ind.get('position_size', 0))
                if pos_size:
                    guidance_lines.append(f"建议清仓卖出 {pos_size} 股")

            for order in symbol_orders_map.get(symbol, []):
                action = order.get('action', '')
                size = int(order.get('executed_size', 0) or 0)
                price = float(order.get('executed_price', 0) or 0)
                if size and price:
                    value = size * price
                    guidance_lines.append(
                        f"实际成交: {action} {size} 股 @ {price:.3f} (金额 {value:,.0f} 元)"
                    )

            report += f"- **{name}** (`{sig_type}`): {trigger}"
            if guidance_lines:
                report += "\n  - " + "\n  - ".join(guidance_lines)
            report += "\n"

    if today_signals:
        _render_signals(today_signals, "今日交易信号")
    elif latest_signals:
        _render_signals(latest_signals[-5:], f"最新交易信号 ({latest_sig_date})")

    report += f"""

---
*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
*策略: {策略中文名}*
"""

    report_path = report_dir / "report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return report_path


def main():
    today = date.today()
    today_str = today.strftime("%Y%m%d")
    today_display = today.strftime("%Y年%m月%d日")

    start_date = "{default_start_date}"

    report_dir = Path(__file__).parent.parent / "task_reports" / today_str
    report_dir.mkdir(parents=True, exist_ok=True)

    symbols = list(ASSET_CONFIG.keys())
    asset_names = [ASSET_CONFIG[s]['name'] for s in symbols]

    print("=" * 60)
    print("{策略中文名}回测")
    print("=" * 60)
    print(f"\n资产池: {', '.join(asset_names)}")
    print(f"回测区间: {start_date} ~ {today.strftime('%Y-%m-%d')}")

    config = BacktestConfig(
        initial_cash={initial_cash},
        auto_save_trades=True,
        auto_save_plot=True,
        enable_quantstats={enable_quantstats},
        benchmark_symbol="{benchmark_symbol}",
        auto_save_report=True,
        auto_open_report=False,
        trade_log_dir=report_dir,
    )

    runner = BacktestRunner(
        config=config,
        enable_plot={enable_plot},
        plot_style="{plot_style}",
    )

    print("\n开始回测...")

    result = runner.run(
        strategy={strategy_class},
        symbols=symbols,
        start=start_date,
        end=today.strftime("%Y-%m-%d"),
        initial_cash=config.initial_cash,
        strategy_params={strategy_params}
    )

    print("\n" + "=" * 60)
    print("回测完成")
    print("=" * 60)

    if result.error_message:
        print(f"\n错误: {result.error_message}")
        return

    print(f"\n总资产: {result.final_value:,.2f} 元")
    print(f"收益率: {result.return_pct:+.2%}")
    print(f"最大回撤: {result.calculate_max_drawdown():.2%}")
    print(f"夏普比率: {result.calculate_sharpe_ratio():.2f}")
    print(f"总交易次数: {result.total_trades}")
    print(f"胜率: {result.win_rate:.1%}")

    print("\n当前持仓:")
    if result.position_log:
        import pandas as pd
        df_pos = pd.DataFrame(result.position_log)
        if not df_pos.empty:
            df_pos['date'] = pd.to_datetime(df_pos['date']).dt.date
            latest_date = df_pos['date'].max()
            latest_pos = df_pos[df_pos['date'] == latest_date]

            df_cap = pd.DataFrame(result.capital_log)
            total_value = result.final_value
            if not df_cap.empty:
                df_cap['date'] = pd.to_datetime(df_cap['date']).dt.date
                latest_cap = df_cap[df_cap['date'] == latest_date]
                if not latest_cap.empty:
                    total_value = latest_cap.iloc[0]['total_value']

            for _, pos in latest_pos.iterrows():
                symbol = pos['symbol']
                name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
                mv = pos['market_value']
                weight = mv / total_value * 100 if total_value > 0 else 0
                pnl = pos['pnl_ratio'] * 100
                print(f"  {name}: 市值 {mv:,.0f} (权重 {weight:.1f}%, 盈亏 {pnl:+.2f}%)")

    print("\n生成每日报告...")
    try:
        report_path = generate_daily_report(result, report_dir, today_str, today_display)
        print(f"报告已保存: {report_path}")
    except Exception as e:
        print(f"生成报告失败: {e}")

    if result.log_files:
        print(f"\n所有文件已保存到: {report_dir}")
        for name, path in result.log_files.items():
            print(f"  - {name}: {Path(path).name}")


if __name__ == "__main__":
    main()
```

## 参数提取规则

从用户输入中提取以下信息，缺失时使用默认值：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| 策略中文名 | 用户提到的名称 | 用于文件注释和报告标题 |
| strategy_class | 用户指定的类名 | 必须大驼峰命名 |
| strategy_module | 根据类名推断 | 如 `trader_center.backtest.strategy.examples` |
| initial_cash | 1,000,000 | 初始资金 |
| benchmark_symbol | 000300.SH | 基准指数 |
| enable_quantstats | True | 是否启用 QuantStats |
| enable_plot | True | 是否生成图表 |
| plot_style | line | 图表样式 |
| default_start_date | 2019-01-01 | 默认回测开始日期 |
| asset_config | 根据策略类型推断 | 资产池字典 |
| strategy_params | 根据策略推断 | 参数字典，直接写入 |

## 资产池推断规则

- **ETF轮动/资产配置策略**：提供多类资产（宽基、海外、债券、商品）
- **股票策略**：提供具体股票代码（如 000001.SZ, 600519.SH）
- **用户已指定**：直接使用用户给出的列表

## 执行步骤

1. 解析用户意图，确定策略类型和名称
2. 推断或确认策略类路径、资产池、参数
3. 按上述模板生成完整的 Python 脚本
4. 写入 `tasks/{strategy_name_snake}_runner.py`
5. 向用户报告生成的文件路径和关键配置
