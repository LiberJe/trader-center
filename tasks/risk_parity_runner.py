"""
四资产风险平价策略任务运行器

基于 ERC（等风险贡献）+ Ledoit-Wolf 收缩协方差的四资产组合策略：
股票 / 利率债10Y / 黄金 / 商品三混合，阈值触发 + 月末强制检查的调仓机制。
生成每日报告，指导次日交易决策。

数据说明：
- 需加载自 2019-11 起的数据以完成 250 日协方差预热
  （商品期货 ETF 于 2019-12 上市，预热完成后首个交易日即 2020-12-18）。
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, datetime, timedelta
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy import RiskParityStrategy4A, LEG_CONFIG

# 复用独立运行器的维度分析导出（腿级 + 标的级 权重/市值/净值曲线与明细）
sys.path.insert(0, str(project_root / "backtest_runner"))
from run_risk_parity import export_leg_analysis, export_symbol_analysis

ASSET_CONFIG = {
    # 股票腿
    '510300.SH': {'name': '沪深300ETF', 'leg': '股票'},
    # 利率债腿
    '511260.SH': {'name': '十年国债ETF', 'leg': '利率债10Y'},
    # 黄金腿
    '518880.SH': {'name': '黄金ETF', 'leg': '黄金'},
    # 商品腿（三等权合成）
    '159981.SZ': {'name': '能源化工ETF', 'leg': '商品三混合'},
    '159985.SZ': {'name': '豆粕ETF', 'leg': '商品三混合'},
    '159980.SZ': {'name': '有色ETF', 'leg': '商品三混合'},
}

# 腿展示顺序（与策略 LEG_CONFIG 一致）
LEG_ORDER = ['股票', '利率债10Y', '黄金', '商品三混合']

# 策略信号中的腿键（英文）-> 中文腿名
LEG_KEY_TO_NAME = {key: cfg['name'] for key, cfg in LEG_CONFIG.items()}


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
            # 获取最新日期的持仓
            df_pos['date'] = pd.to_datetime(df_pos['date']).dt.date
            latest_date = df_pos['date'].max()
            latest_df = df_pos[df_pos['date'] == latest_date]
            # 按 symbol 去重，保留第一条记录
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

    # 提取当日交易（从 order_log 读取实际成交）
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

    # 计算当日收益
    daily_return = latest_capital.get('daily_return', 0)
    data_date = latest_capital.get('date')
    data_display = data_date.strftime("%Y年%m月%d日") if data_date else "无行情数据"

    # 获取交易信号
    today_signals = []
    latest_signals = []
    latest_sig_date = None
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

    # 按腿聚合最新持仓，并关联最新信号中的风险贡献
    total_value = latest_capital.get('total_value', result.final_value)
    leg_stats = {leg: {'market_value': 0.0} for leg in LEG_ORDER}
    for pos in latest_positions:
        leg = ASSET_CONFIG.get(pos.get('symbol', ''), {}).get('leg')
        if leg:
            leg_stats[leg]['market_value'] += pos.get('market_value', 0)
    for sig in latest_signals:
        ind = sig.get('indicator_values', {}) or {}
        leg = ind.get('leg')
        leg_name = LEG_KEY_TO_NAME.get(leg, leg)
        if leg_name in leg_stats:
            leg_stats[leg_name]['target_weight'] = float(ind.get('target_weight', 0) or 0)
            leg_stats[leg_name]['risk_contrib'] = float(ind.get('risk_contrib', 0) or 0)
            leg_stats[leg_name]['lw_shrinkage'] = ind.get('lw_shrinkage')

    # 生成报告
    report = f"""# 四资产风险平价策略日报 - {today_display}

## 回测概览

| 指标 | 数值 |
|------|------|
| 回测区间 | {result.start_date} ~ {result.end_date} |
| 行情截至 | {data_display} |
| 初始资金 | {result.initial_cash:,.0f} 元 |
| 当前总资产 | {result.final_value:,.2f} 元 |
| 累计收益率 | {result.return_pct:+.2%} |
| 最近交易日收益 | {daily_return:+.2%} |
| 最大回撤 | {result.calculate_max_drawdown():.2%} |
| 夏普比率 | {result.calculate_sharpe_ratio():.2f} |
| 总交易次数 | {result.total_trades} |
| 胜率 | {result.win_rate:.1%} |
| 盈亏比 | {result.profit_factor:.2f} |

## 资产配置（腿维度）

| 资产腿 | 市值 | 实际权重 | 最近调仓目标权重 | 目标风险贡献 |
|--------|------|----------|----------|----------|
"""

    for leg in LEG_ORDER:
        mv = leg_stats[leg]['market_value']
        weight = mv / total_value * 100 if total_value > 0 else 0
        target = leg_stats[leg].get('target_weight')
        rc = leg_stats[leg].get('risk_contrib')
        target_str = f"{target*100:.1f}%" if target is not None else "-"
        rc_str = f"{rc*100:.1f}%" if rc is not None else "-"
        report += f"| {leg} | {mv:,.0f} | {weight:.1f}% | {target_str} | {rc_str} |\n"

    if latest_sig_date:
        report += f"\n目标权重和目标风险贡献来自 {latest_sig_date} 的调仓信号，不代表当前持仓的实时风险贡献。\n"

    report += f"""
## 当前持仓 ({data_display})

"""

    # 添加持仓表格
    if latest_positions:
        report += "| 资产 | 代码 | 所属腿 | 持仓数量 | 成本价 | 当前价 | 市值 | 权重 | 盈亏 |\n"
        report += "|------|------|--------|----------|--------|--------|------|------|------|\n"

        for pos in latest_positions:
            symbol = pos.get('symbol', '')
            name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
            leg = ASSET_CONFIG.get(symbol, {}).get('leg', '')
            size = pos.get('size', 0)
            cost = pos.get('cost_price', 0)
            current = pos.get('current_price', 0)
            mv = pos.get('market_value', 0)
            weight = mv / total_value * 100 if total_value > 0 else 0
            pnl = pos.get('pnl_ratio', 0) * 100

            report += f"| {name} | {symbol} | {leg} | {size} | {cost:.2f} | {current:.2f} | {mv:,.0f} | {weight:.1f}% | {pnl:+.2f}% |\n"

        cash = latest_capital.get('cash', 0)
        cash_ratio = cash / total_value * 100 if total_value > 0 else 0
        report += f"\n**现金**: {cash:,.2f} 元 ({cash_ratio:.1f}%)\n"
    else:
        report += "*当前无持仓*\n"

    # 交易信号部分
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

    # 建立 symbol -> orders 映射，用于关联信号与成交
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
                leg_key = ind.get('leg')
                leg_name = (
                    ASSET_CONFIG.get(symbol, {}).get('leg')
                    or LEG_KEY_TO_NAME.get(leg_key, leg_key or symbol)
                )
                current_w = float(ind.get('current_weight', 0) or 0)
                target_w = float(ind.get('target_weight', 0) or 0)
                risk_contrib = float(ind.get('risk_contrib', 0) or 0)
                shrinkage = ind.get('lw_shrinkage')
                delta = target_w - current_w
                if delta > 0:
                    guidance_lines.append(f"建议加仓约 {delta*100:.2f}% (目标权重 {target_w*100:.2f}%)")
                else:
                    guidance_lines.append(f"建议减仓约 {abs(delta)*100:.2f}% (目标权重 {target_w*100:.2f}%)")
                guidance_lines.append(f"腿: {leg_name}, 风险贡献 {risk_contrib*100:.1f}%")
                if shrinkage is not None:
                    guidance_lines.append(f"LW 收缩强度: {float(shrinkage):.4f}")
            elif sig_type == 'buy':
                target_w = float(ind.get('target_weight', 0) or 0)
                guidance_lines.append(f"建议建仓至 {target_w*100:.2f}% 权重")
            elif sig_type in ('stop_loss', 'trailing_stop'):
                pos_size = int(ind.get('position_size', 0) or 0)
                if pos_size:
                    guidance_lines.append(f"建议清仓卖出 {pos_size} 股")

            # 关联实际成交
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
*策略: 四资产风险平价策略（ERC + LW收缩 + 阈值调仓，规格书v3.2）*
"""

    # 保存报告
    report_path = report_dir / "report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return report_path


def main(report_subdir: str = None):
    # 获取当天日期
    today = date.today() - timedelta(days=0)
    today_str = today.strftime("%Y%m%d")
    today_display = today.strftime("%Y年%m月%d日")

    # 数据加载起点：需含 250 日协方差预热（商品 ETF 2019-12 上市，
    # 预热完成后首个交易日为 2020-12-18，此前为数据预热期）
    start_date = "2019-11-01"

    # 创建报告目录 (项目根目录下的 task_reports/)
    report_dir = Path(__file__).parent.parent / "task_reports" / today_str
    if report_subdir:
        report_dir = report_dir / report_subdir
    report_dir.mkdir(parents=True, exist_ok=True)

    # 资产池
    symbols = list(ASSET_CONFIG.keys())
    asset_names = [ASSET_CONFIG[s]['name'] for s in symbols]

    print("=" * 60)
    print("四资产风险平价策略回测")
    print("=" * 60)
    print(f"\n资产池: {', '.join(asset_names)}")
    print(f"数据加载区间: {start_date} ~ {today.strftime('%Y-%m-%d')}（含 250 日预热）")

    # 配置回测
    config = BacktestConfig(
        initial_cash=1000000,
        auto_save_trades=True,
        auto_save_plot=True,
        enable_quantstats=True,
        benchmark_symbol="000300.SH",
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

    # 运行回测，end日期自动设为当天
    result = runner.run(
        strategy=RiskParityStrategy4A,
        symbols=symbols,
        start=start_date,
        end=today.strftime("%Y-%m-%d"),
        initial_cash=config.initial_cash,
        strategy_params={
            'cov_window': 250,            # 协方差滚动估计窗口（交易日）
            'rebalance_threshold': 0.05,  # 调仓触发阈值（Σ|实际-目标|，L1 偏离）
            'commission': 0.0005,         # 单边佣金率（5bp）
            'stamp_duty': 0.0,            # 印花税率（ETF 免印花税）
            'min_commission': 0.0,        # 最低佣金
        }
    )

    print("\n" + "=" * 60)
    print("回测完成")
    print("=" * 60)

    if result.error_message:
        print(f"\n错误: {result.error_message}")
        return {"status": "error", "error_message": result.error_message}

    # 显示核心结果
    print(f"\n总资产: {result.final_value:,.2f} 元")
    print(f"收益率: {result.return_pct:+.2%}")
    print(f"最大回撤: {result.calculate_max_drawdown():.2%}")
    print(f"夏普比率: {result.calculate_sharpe_ratio():.2f}")
    print(f"总交易次数: {result.total_trades}")
    print(f"胜率: {result.win_rate:.1%}")

    # 显示当前持仓（按腿聚合 + 标的明细）
    print("\n资产配置（腿维度）:")
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

            leg_values = {leg: 0.0 for leg in LEG_ORDER}
            for _, pos in latest_pos.iterrows():
                leg = ASSET_CONFIG.get(pos['symbol'], {}).get('leg')
                if leg:
                    leg_values[leg] += pos['market_value']
            for leg in LEG_ORDER:
                mv = leg_values[leg]
                weight = mv / total_value * 100 if total_value > 0 else 0
                print(f"  {leg}: 市值 {mv:,.0f} (权重 {weight:.1f}%)")

            print("\n当前持仓:")
            for _, pos in latest_pos.iterrows():
                symbol = pos['symbol']
                name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
                mv = pos['market_value']
                weight = mv / total_value * 100 if total_value > 0 else 0
                pnl = pos['pnl_ratio'] * 100
                print(f"  {name}: 市值 {mv:,.0f} (权重 {weight:.1f}%, 盈亏 {pnl:+.2f}%)")

    # 生成每日报告
    print("\n生成每日报告...")
    try:
        report_path = generate_daily_report(result, report_dir, today_str, today_display)
        print(f"报告已保存: {report_path}")
    except Exception as e:
        print(f"生成报告失败: {e}")

    # 维度分析：资产类别（腿）级 + 标的（ETF）级，权重/市值/净值曲线 + 明细数据
    print("\n导出维度分析...")
    try:
        result.log_files.update(export_leg_analysis(result, LEG_CONFIG, report_dir))
        result.log_files.update(export_symbol_analysis(result, LEG_CONFIG, report_dir))
        print("维度分析已导出")
    except Exception as e:
        print(f"导出维度分析失败: {e}")

    # 显示日志文件位置
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

    # 持仓摘要（腿维度）
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

                leg_values = {leg: 0.0 for leg in LEG_ORDER}
                for _, pos in latest_pos.iterrows():
                    leg = ASSET_CONFIG.get(pos['symbol'], {}).get('leg')
                    if leg:
                        leg_values[leg] += pos['market_value']

                holdings = []
                for leg in LEG_ORDER:
                    mv = leg_values[leg]
                    if mv > 0:
                        weight = mv / total_value * 100 if total_value > 0 else 0
                        holdings.append(f"{leg} ({weight:.1f}%)")

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
                        ind = sig.get('indicator_values', {}) or {}
                        leg = ind.get('leg')
                        leg_name = ASSET_CONFIG.get(symbol, {}).get('leg', leg or name)
                        sigs.append(f"{leg_name} ({sig['signal_type']})")
                    signals_summary = ", ".join(sigs)
                else:
                    latest_sig_date = df_sig['datetime'].dt.date.max()
                    latest_signals = df_sig[df_sig['datetime'].dt.date == latest_sig_date]
                    if not latest_signals.empty:
                        sig = latest_signals.iloc[-1]
                        symbol = sig['symbol']
                        name = ASSET_CONFIG.get(symbol, {}).get('name', symbol)
                        ind = sig.get('indicator_values', {}) or {}
                        leg = ind.get('leg')
                        leg_name = ASSET_CONFIG.get(symbol, {}).get('leg', leg or name)
                        signals_summary = f"最新信号 ({latest_sig_date}): {leg_name} ({sig['signal_type']})"
        result_dict["signals_summary"] = signals_summary
    except Exception:
        result_dict["signals_summary"] = "获取信号摘要失败"

    return result_dict


if __name__ == "__main__":
    main()
