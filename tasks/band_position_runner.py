"""
分仓波段策略运行器

底仓持有+波段定投+移动止盈的组合策略回测。
生成每日报告，指导次日交易决策。
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, datetime, timedelta
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy.band_position import BandPositionStrategy

ASSET_CONFIG = {
    '512890.SH': {'name': '红利低波ETF', 'category': 'equity_cn'},
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

    report = f"""# 分仓波段策略日报 - {today_display}

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
*策略: 分仓波段策略*
"""

    report_path = report_dir / "report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return report_path


def main(report_subdir: str = None):
    today = date.today() - timedelta(days=0)
    today_str = today.strftime("%Y%m%d")
    today_display = today.strftime("%Y年%m月%d日")

    start_date = "2019-01-01"

    report_dir = Path(__file__).parent.parent / "task_reports" / today_str
    if report_subdir:
        report_dir = report_dir / report_subdir
    report_dir.mkdir(parents=True, exist_ok=True)

    symbols = list(ASSET_CONFIG.keys())
    asset_names = [ASSET_CONFIG[s]['name'] for s in symbols]

    print("=" * 60)
    print("分仓波段策略回测")
    print("=" * 60)
    print(f"\n资产池: {', '.join(asset_names)}")
    print(f"回测区间: {start_date} ~ {today.strftime('%Y-%m-%d')}")

    config = BacktestConfig(
        initial_cash=100000,
        auto_save_trades=True,
        auto_save_plot=True,
        enable_quantstats=True,
        benchmark_symbol="512890.SH",
        auto_save_report=True,
        auto_open_report=False,
        trade_log_dir=report_dir,
    )

    runner = BacktestRunner(
        config=config,
        enable_plot=True,
        plot_style="line",
    )

    print("\n开始回测...")

    result = runner.run(
        strategy=BandPositionStrategy,
        symbols=symbols,
        start=start_date,
        end=today.strftime("%Y-%m-%d"),
        initial_cash=config.initial_cash,
        strategy_params={
            'base_position_pct': 50,
            'ma_period': 60,
            'dca_batches': 5,
            'dca_interval': 5,
            'dca_trigger_bias': 0,
            'trailing_stop_pct': 3,
            'use_bias_weighting': True,
            'min_dca_weight': 1.0,
            'max_dca_weight': 3.0,
            'time_decay_days': 30,
            'time_factor_ratio': 0.4,
            'drop_factor_ratio': 0.6,
            'max_bias_ref': 20,
            'max_leverage_pct': 0,
            'leverage_interest_rate': 3.0,
            'use_dynamic_trailing_stop': True,
            'trailing_tighten_bias_1': 8.0,
            'trailing_tighten_stop_1': 2.0,
            'trailing_tighten_bias_2': 10.0,
            'trailing_tighten_stop_2': 1.5,
            'trailing_tighten_bias_3': 12.0,
            'trailing_tighten_stop_3': 1.0,
            'trailing_activation_bars': 3,
            'enable_base_reduce': True,
            'base_reduce_bias_threshold': 15.0,
            'base_reduce_ratio': 0.5,
            'base_reduce_min_hold': 0.5,
            'base_restore_bias_threshold': 0,
        }
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
            latest_pos = df_pos[df_pos['date'] == latest_date].drop_duplicates(subset=['symbol'], keep='first')

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

    # 构造返回结果
    result_dict = {
        "status": "error" if result.error_message else "success",
        "report_path": str(report_path) if 'report_path' in locals() else None,
        "error_message": result.error_message,
        "metrics": {
            "return_pct": result.return_pct,
            "max_drawdown": result.calculate_max_drawdown(),
            "sharpe_ratio": result.calculate_sharpe_ratio(),
            "final_value": result.final_value,
            "initial_cash": result.initial_cash,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
        },
    }

    # 持仓摘要
    try:
        holdings_summary = ""
        if result.position_log:
            import pandas as pd
            df_pos = pd.DataFrame(result.position_log)
            if not df_pos.empty:
                df_pos['date'] = pd.to_datetime(df_pos['date']).dt.date
                latest_date = df_pos['date'].max()
                latest_pos = df_pos[df_pos['date'] == latest_date].drop_duplicates(subset=['symbol'], keep='first')

                df_cap = pd.DataFrame(result.capital_log)
                total_value = result.final_value
                if not df_cap.empty:
                    df_cap['date'] = pd.to_datetime(df_cap['date']).dt.date
                    latest_cap = df_cap[df_cap['date'] == latest_date]
                    if not latest_cap.empty:
                        total_value = latest_cap.iloc[0]['total_value']

                holdings = []
                for _, pos in latest_pos.iterrows():
                    symbol = pos['symbol']
                    name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
                    mv = pos['market_value']
                    weight = mv / total_value * 100 if total_value > 0 else 0
                    holdings.append(f"{name} ({weight:.1f}%)")

                cash = 0
                if not df_cap.empty:
                    latest_cap = df_cap[df_cap['date'] == latest_date]
                    if not latest_cap.empty:
                        cash = latest_cap.iloc[0]['cash']
                cash_ratio = cash / total_value * 100 if total_value > 0 else 0
                if cash_ratio > 1:
                    holdings.append(f"现金 ({cash_ratio:.1f}%)")

                holdings_summary = ", ".join(holdings) if holdings else "无持仓"
        result_dict["holdings_summary"] = holdings_summary or "无持仓"
    except Exception:
        result_dict["holdings_summary"] = "获取持仓摘要失败"

    # 信号摘要
    try:
        signals_summary = "今日无交易"
        if result.signal_log:
            import pandas as pd
            df_sig = pd.DataFrame(result.signal_log)
            if not df_sig.empty:
                df_sig['datetime'] = pd.to_datetime(df_sig['datetime'])
                signal_types = ['buy', 'rebalance', 'stop_loss', 'trailing_stop']
                df_sig = df_sig[df_sig['signal_type'].isin(signal_types)]
                today = datetime.strptime(today_str, "%Y%m%d").date()
                today_signals = df_sig[df_sig['datetime'].dt.date == today]
                if not today_signals.empty:
                    sigs = []
                    for _, sig in today_signals.iterrows():
                        symbol = sig['symbol']
                        name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
                        sig_type = sig['signal_type']
                        sigs.append(f"{name} ({sig_type})")
                    signals_summary = ", ".join(sigs)
                else:
                    latest_sig_date = df_sig['datetime'].dt.date.max()
                    latest_signals = df_sig[df_sig['datetime'].dt.date == latest_sig_date]
                    if not latest_signals.empty:
                        sig = latest_signals.iloc[-1]
                        symbol = sig['symbol']
                        name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
                        signals_summary = f"最新信号 ({latest_sig_date}): {name} ({sig['signal_type']})"
        result_dict["signals_summary"] = signals_summary
    except Exception:
        result_dict["signals_summary"] = "获取信号摘要失败"

    return result_dict


if __name__ == "__main__":
    main()
