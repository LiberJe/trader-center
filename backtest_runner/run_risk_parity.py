"""
四资产风险平价策略运行器（策略规格书 v3.2）

用法：
    # 冻结样本（默认）：2020-12-18（250日预热完成后首个交易日）~ 2024-12-31
    python backtest_runner/run_risk_parity.py

    # 含样本外验证
    python backtest_runner/run_risk_parity.py --end 2026-09-21

    # 关闭图表或绩效报告
    python backtest_runner/run_risk_parity.py --no-plot
    python backtest_runner/run_risk_parity.py --no-report

    # 从本地 CSV 加载数据（文件名为 {code}.csv，如 510300.SH.csv）
    python backtest_runner/run_risk_parity.py --source csv --csv-dir research/etf4_rp/data

    # 外部完整标的配置（与任务运行器 ASSET_CONFIG 同结构）
    python backtest_runner/run_risk_parity.py --asset-config my_assets.json

产出（logs/backtest/risk_parity_4a/{run_id}/）：
- kline*.png：backtrader K线图（6 只 ETF）
- plot.png：资产曲线/回撤/收益分布/绩效摘要四联图
- performance_report.html：QuantStats 绩效报告（基准沪深300）
- leg_analysis.png + leg_values/leg_weights/leg_nav.csv：各资产类别权重/市值/净值曲线与明细
- symbol_analysis.png + symbol_values/symbol_weights/symbol_nav.csv：每只 ETF 权重/市值/净值曲线与明细
- trades/orders/signals/positions/capitals/daily_values：交易日志

数据说明：
- akshare 数据源经由 DataHub，需加载自 2019-11 起的数据以完成 250 日协方差预热
  （商品期货 ETF 于 2019-12 上市，预热完成后首个交易日即 2020-12-18）。
- CSV 格式要求列：date/open/high/low/close/volume（date 列或 datetime index）。
- 绩效指标在策略首个交易日（预热完成日）之后计算，与研究引擎口径一致。
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.data_feed import PandasDataFeed
from trader_center.backtest.strategy import RiskParityStrategy4A, resolve_risk_parity_config

# ---------------------------------------------------------------------------
# 默认配置（命令行未提供参数时使用）
# ---------------------------------------------------------------------------
# 运行级默认配置（规格书 v3.2 冻结口径）
DEFAULTS = {
    # 数据加载起点（含 250 日预热）：商品期货 ETF 2019-12 上市，向前多取无妨
    "start": "2019-11-01",
    # 回测终点（冻结样本）
    "end": "2024-12-31",
    # "end": "2026-09-27",
    # 初始资金
    "cash": 1_000_000.0,
    # 产出开关
    "plot": True,  # K线图+绩效图
    "report": True,  # QuantStats HTML 绩效报告
}

# 策略参数默认值直接取自策略类 params（单一事实来源，与
# trader_center/backtest/strategy/risk_parity.py 中的定义保持一致），
# 命令行提供对应参数时覆盖
_STRATEGY_DEFAULTS = dict(RiskParityStrategy4A.params()._getkwargs())

# CLI 参数名 -> 策略 params 名
_STRATEGY_ARG_MAP = {
    "threshold": "rebalance_threshold",
    "cov_window": "cov_window",
    "commission": "commission",
    "stamp_duty": "stamp_duty",
    "min_commission": "min_commission",
}


class CSVDataRunner(BacktestRunner):
    """从本地 CSV 目录加载数据的运行器（用于离线数据/与研究引擎对拍）"""

    def __init__(self, csv_dir: str, **kwargs):
        super().__init__(**kwargs)
        self.csv_dir = Path(csv_dir)

    def _load_data(self, symbol, start, end):
        path = self.csv_dir / f"{symbol}.csv"
        if not path.exists():
            # 兼容 510300.SH -> 510300_SH.csv 的命名
            alt = self.csv_dir / f"{symbol.replace('.', '_')}.csv"
            if alt.exists():
                path = alt
            else:
                self.logger.error(f"CSV 不存在: {path}")
                return None
        df = pd.read_csv(path)
        df.columns = [c.lower() for c in df.columns]
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        elif not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.loc[pd.Timestamp(start) : pd.Timestamp(end)]
        if df.empty:
            self.logger.warning(f"CSV 无数据: {symbol} [{start} ~ {end}]")
            return None
        return PandasDataFeed.from_datahub(symbol, df)


def trim_to_strategy_start(result, signal_log):
    """剔除预热期（策略首个信号之前）的净值记录，使指标口径与研究引擎一致"""
    if not signal_log:
        return result
    dt_col = None
    for key in ("datetime", "dt", "date"):
        if key in signal_log[0]:
            dt_col = key
            break
    if dt_col is None:
        return result
    first_dt = min(pd.Timestamp(s[dt_col]).date() for s in signal_log)
    n_before = len(result.daily_values)
    result.daily_values = [r for r in result.daily_values if r["date"] >= first_dt]
    trimmed = n_before - len(result.daily_values)
    if trimmed > 0:
        result.log_files["trim_note"] = (
            f"预热期剔除 {trimmed} 个交易日净值（自 {first_dt} 起计）"
        )
    return result


def _setup_chinese_font():
    """配置 matplotlib 中文字体（与框架 _plot_result 同一逻辑）"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    for font_name in [
        "SimHei",
        "Microsoft YaHei",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
    ]:
        try:
            font_path = fm.findfont(font_name)
            if "generic" not in font_path.lower():
                plt.rcParams["font.sans-serif"] = [font_name]
                break
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False
    return plt


# 腿配色（标的级图表在同族色内取深浅变体）
LEG_COLORS = {
    "equity": "#d62728",
    "bond": "#1f77b4",
    "gold": "#d4a017",
    "commodity": "#2ca02c",
}


def _leg_colors(leg_config):
    """Default leg colors plus deterministic colors for externally added legs."""
    fallback = ["#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#17becf", "#bcbd22"]
    return {leg: LEG_COLORS.get(leg, fallback[i % len(fallback)])
            for i, leg in enumerate(leg_config)}


def _symbol_colors(leg_config):
    """为每只 ETF 生成颜色：按所属腿取基色，同腿内按深浅区分"""
    import matplotlib.colors as mcolors

    colors = {}
    leg_colors = _leg_colors(leg_config)
    for leg, cfg in leg_config.items():
        base = mcolors.to_rgb(leg_colors[leg])
        members = cfg["members"]
        n = len(members)
        shades = (
            [0.45, 0.72, 1.0][-n:]
            if n <= 3
            else [0.4 + 0.6 * i / (n - 1) for i in range(n)]
        )
        for member, s in zip(members, shades):
            colors[member] = tuple(1.0 - (1.0 - c) * s for c in base)
    return colors


def _build_group_value(result, symbol_to_group: dict, groups: list) -> pd.DataFrame:
    """把逐日持仓日志按分组聚合为 date x group 的市值表

    - BaseStrategy.stop() 会再记一次当日持仓，末日常有重复记录，去重取最后一条
    - 对齐到组合净值日历（裁剪后口径），无持仓日补 0、中间缺失前值填充
    """
    if not result.position_log or not result.daily_values:
        return pd.DataFrame()

    pos = pd.DataFrame(result.position_log)
    date_col = "log_date" if "log_date" in pos.columns else "date"
    pos[date_col] = pd.to_datetime(pos[date_col])
    if "market_value" not in pos.columns:
        pos["market_value"] = pos["size"] * pos["current_price"]
    pos["group"] = pos["symbol"].map(symbol_to_group)
    pos = pos.dropna(subset=["group"])
    pos = pos.sort_values(date_col).drop_duplicates(
        subset=[date_col, "symbol"], keep="last"
    )

    value = (
        pos.pivot_table(
            index=date_col, columns="group", values="market_value", aggfunc="sum"
        )
        .reindex(columns=groups)
        .fillna(0.0)
        .sort_index()
    )

    daily = pd.DataFrame(result.daily_values)
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.set_index("date").sort_index()
    return value.reindex(daily.index).ffill().fillna(0.0)


def _compute_nav(value: pd.DataFrame) -> pd.DataFrame:
    """归一化净值：以每组首次建仓执行日为基准 1，未建仓日为 NaN"""
    nav = pd.DataFrame(index=value.index)
    for col in value.columns:
        series = value[col]
        base_date = series.where(series > 0).first_valid_index()
        if base_date is None:
            nav[col] = np.nan
            continue
        nav[col] = series.where(series > 0) / series.loc[base_date]
    return nav


def _plot_group_analysis(
    value: pd.DataFrame,
    total_value: pd.Series,
    weights: pd.DataFrame,
    nav: pd.DataFrame,
    title: str,
    png_path: Path,
    colors: dict,
):
    """绘制分组分析三联图：权重曲线 / 归一化净值 / 市值堆叠面积"""
    plt = _setup_chinese_font()
    fig, axes = plt.subplots(3, 1, figsize=(13, 12), sharex=True)
    x = value.index
    cols = list(value.columns)
    # 序列多（标的级 6 条）时图例放轴下方并分两行，避免溢出挤压绘图区
    ncols = min(len(cols), 4)
    legend_below = len(cols) > 4

    def _legend(ax, loc):
        if legend_below:
            ax.legend(
                loc="upper center",
                bbox_to_anchor=(0.5, -0.08),
                ncol=ncols,
                fontsize=9,
                frameon=False,
            )
        else:
            ax.legend(loc=loc, ncol=ncols, fontsize=9)

    ax = axes[0]
    for c in cols:
        ax.plot(x, weights[c] * 100, label=str(c), color=colors.get(c), linewidth=1.2)
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_title("权重（%）")
    ax.set_ylabel("权重 (%)")
    _legend(ax, "upper right")
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    for c in cols:
        ax.plot(x, nav[c], label=str(c), color=colors.get(c), linewidth=1.2)
    ax.axhline(1, color="gray", linewidth=0.5, linestyle="--")
    ax.set_title("归一化净值（建仓执行日 = 1）")
    ax.set_ylabel("净值")
    _legend(ax, "upper left")
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    ax.stackplot(
        x,
        [value[c] for c in cols],
        labels=[str(c) for c in cols],
        colors=[colors.get(c) for c in cols],
        alpha=0.75,
    )
    ax.plot(x, total_value, color="black", linewidth=1.0, label="组合总值")
    ax.set_title("市值（元）")
    ax.set_ylabel("市值")
    _legend(ax, "upper left")
    ax.grid(True, alpha=0.3)

    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _export_group(
    result,
    groups: dict,
    display: dict,
    colors: dict,
    title: str,
    prefix: str,
    output_dir: Path,
) -> dict:
    """通用分组导出：市值/权重/净值 CSV + 三联图

    Args:
        groups: {组键: 成员列表}
        display: {组键: 显示名}
        colors: {显示名: 颜色}
        prefix: 输出文件前缀（leg / symbol）
    """
    keys = list(groups.keys())
    symbol_to_group = {m: k for k in keys for m in groups[k]}
    value = _build_group_value(result, symbol_to_group, keys)
    if value.empty:
        return {}

    daily = pd.DataFrame(result.daily_values)
    daily["date"] = pd.to_datetime(daily["date"])
    total_value = daily.set_index("date").sort_index()["value"]

    value = value.rename(columns=display)
    weights = value.div(total_value, axis=0)
    cash_weight = 1.0 - weights.sum(axis=1)
    nav = _compute_nav(value)

    run_dir = result.get_run_dir(output_dir)
    saved = {}

    values_df = value.copy()
    values_df["组合总值"] = total_value
    values_df.index.name = "date"
    values_df.round(2).to_csv(run_dir / f"{prefix}_values.csv", encoding="utf-8-sig")
    saved[f"{prefix}_values"] = str(run_dir / f"{prefix}_values.csv")

    weights_df = weights.copy()
    weights_df["现金"] = cash_weight
    weights_df.index.name = "date"
    weights_df.round(6).to_csv(run_dir / f"{prefix}_weights.csv", encoding="utf-8-sig")
    saved[f"{prefix}_weights"] = str(run_dir / f"{prefix}_weights.csv")

    nav.index.name = "date"
    nav.round(6).to_csv(run_dir / f"{prefix}_nav.csv", encoding="utf-8-sig")
    saved[f"{prefix}_nav"] = str(run_dir / f"{prefix}_nav.csv")

    try:
        _plot_group_analysis(
            value,
            total_value,
            weights,
            nav,
            title,
            run_dir / f"{prefix}_analysis.png",
            colors,
        )
        saved[f"{prefix}_analysis"] = str(run_dir / f"{prefix}_analysis.png")
    except Exception as e:
        print(f"生成{title}图表失败: {e}")

    return saved


def export_leg_analysis(result, leg_config, output_dir: Path) -> dict:
    """导出各资产类别（腿）级别的权重/市值/归一化净值曲线与明细数据

    基于逐日持仓日志聚合到 4 条腿（商品腿为 3 只 ETF 之和），产出：
    - leg_values.csv / leg_weights.csv / leg_nav.csv
    - leg_analysis.png：权重 / 归一化净值 / 市值堆叠面积 三联图
    """
    groups = {leg: leg_config[leg]["members"] for leg in leg_config}
    display = {leg: leg_config[leg]["name"] for leg in leg_config}
    colors = {display[leg]: color for leg, color in _leg_colors(leg_config).items()}
    return _export_group(
        result,
        groups,
        display,
        colors,
        "四资产风险平价 — 资产类别维度分析",
        "leg",
        output_dir,
    )


def export_symbol_analysis(result, leg_config, output_dir: Path) -> dict:
    """导出每只 ETF 的权重/市值/归一化净值曲线与明细数据（标的级，下钻）"""
    groups = {}
    display = {}
    for leg, cfg in leg_config.items():
        for member in cfg["members"]:
            groups[member] = [member]
            display[member] = f"{member}（{cfg['name']}）"
    colors = {display[m]: c for m, c in _symbol_colors(leg_config).items()}
    return _export_group(
        result,
        groups,
        display,
        colors,
        "四资产风险平价 — 标的维度分析",
        "symbol",
        output_dir,
    )


def main(asset_config=None):
    parser = argparse.ArgumentParser(
        description="四资产风险平价策略回测（规格书 v3.2）",
        epilog="所有参数均有默认配置（help 中标注），命令行提供时覆盖。",
    )
    parser.add_argument(
        "--asset-config", type=Path,
        help="完整标的配置 JSON 文件：{代码: {name, leg}}；未提供时使用内置默认值",
    )
    parser.add_argument(
        "--start",
        default=None,
        help=f"数据加载起点（含预热），默认 {DEFAULTS['start']}",
    )
    parser.add_argument(
        "--end",
        default=None,
        help=f"回测终点，默认 {DEFAULTS['end']}（冻结样本）",
    )
    parser.add_argument(
        "--cash",
        type=float,
        default=None,
        help=f"初始资金，默认 {DEFAULTS['cash']:,.0f} 元",
    )
    parser.add_argument(
        "--source",
        choices=["akshare", "csv"],
        default="akshare",
        help="数据源，默认 akshare（经 DataHub）",
    )
    parser.add_argument(
        "--csv-dir", default="research/etf4_rp/data", help="--source csv 时的数据目录"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=f"调仓触发阈值（Σ|实际-目标|），默认 {_STRATEGY_DEFAULTS['rebalance_threshold']}",
    )
    parser.add_argument(
        "--cov-window",
        type=int,
        default=None,
        help=f"协方差估计窗口，默认 {_STRATEGY_DEFAULTS['cov_window']}",
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=None,
        help=f"单边佣金率，默认 {_STRATEGY_DEFAULTS['commission']}",
    )
    parser.add_argument(
        "--stamp-duty",
        type=float,
        default=None,
        help=f"印花税率（ETF 为 0），默认 {_STRATEGY_DEFAULTS['stamp_duty']}",
    )
    parser.add_argument(
        "--min-commission",
        type=float,
        default=None,
        help=f"最低佣金（元），默认 {_STRATEGY_DEFAULTS['min_commission']}",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        default=None,
        help=f"关闭图表产出（默认 {'开启' if DEFAULTS['plot'] else '关闭'}）",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        default=None,
        help=f"关闭 QuantStats 绩效报告（默认 {'开启' if DEFAULTS['report'] else '关闭'}）",
    )
    args = parser.parse_args()

    try:
        if args.asset_config is not None:
            asset_config = json.loads(args.asset_config.read_text(encoding="utf-8-sig"))
        asset_config, leg_config = resolve_risk_parity_config(asset_config)
    except (OSError, ValueError) as exc:
        parser.error(f"资产配置无效: {exc}")
    symbols = list(asset_config)

    # 解析有效配置：命令行优先，回落到默认配置
    start = args.start or DEFAULTS["start"]
    end = args.end or DEFAULTS["end"]
    cash = args.cash if args.cash is not None else DEFAULTS["cash"]
    enable_plot = DEFAULTS["plot"] if args.no_plot is None else not args.no_plot
    enable_report = DEFAULTS["report"] if args.no_report is None else not args.no_report

    strategy_params = {"asset_config": asset_config}
    for arg_name, param_name in _STRATEGY_ARG_MAP.items():
        value = getattr(args, arg_name)
        strategy_params[param_name] = (
            value if value is not None else _STRATEGY_DEFAULTS[param_name]
        )

    print("=" * 64)
    print("四资产风险平价策略（规格书 v3.2）")
    print("=" * 64)
    print("\n资产标的:")
    for leg, cfg in leg_config.items():
        print(f"  [{cfg['name']}] {' + '.join(cfg['members'])}")
    print("\n回测参数（默认值可被命令行覆盖）:")
    print(
        f"  数据加载区间: {start} ~ {end}（含 {strategy_params['cov_window']} 日预热）"
    )
    print(f"  初始资金: {cash:,.0f} 元")
    print(f"  权重方法: ERC（LW收缩, 窗口 {strategy_params['cov_window']}）")
    print(
        f"  调仓阈值: Σ|实际-目标| > {strategy_params['rebalance_threshold']:.2%}，"
        "每日收盘检查"
    )
    print(
        f"  每腿风险预算: 1/{len(leg_config)} = {1 / len(leg_config):.2%}，"
        f"佣金: {strategy_params['commission']:.4%}/单边，"
        f"印花税: {strategy_params['stamp_duty']:.4%}，"
        f"最低佣金: {strategy_params['min_commission']:g} 元"
    )
    print("  执行: T+1 收盘生效")
    print(
        f"  产出: K线图+绩效图{'（关闭）' if not enable_plot else ''}，"
        f"QuantStats 报告{'（关闭）' if not enable_report else ''}，交易日志"
    )

    # 绩效报告在预热期裁剪后由本脚本生成（口径与研究引擎一致），
    # 故关闭 run() 内部的报告生成，避免双份
    config = BacktestConfig(
        initial_cash=cash,
        auto_save_trades=True,
        enable_quantstats=True,
        auto_save_report=False,
        benchmark_symbol="000300.SH",
    )

    common = dict(config=config, enable_plot=enable_plot, plot_style="line")
    if args.source == "csv":
        runner = CSVDataRunner(csv_dir=args.csv_dir, **common)
    else:
        runner = BacktestRunner(**common)

    result = runner.run(
        strategy=RiskParityStrategy4A,
        symbols=symbols,
        start=start,
        end=end,
        initial_cash=cash,
        strategy_params=strategy_params,
    )

    result = trim_to_strategy_start(result, result.signal_log)

    if result.error_message:
        print("\n" + "=" * 64)
        print("回测结果")
        print("=" * 64)
        print(f"\n错误: {result.error_message}")
        sys.exit(1)

    # 预热期裁剪后重新落盘净值/摘要，并生成 QuantStats 绩效报告（基准：沪深300）
    result.save_daily_values(config.trade_log_dir)
    result.save_summary(config.trade_log_dir)
    if enable_report:
        try:
            report_path = result.generate_performance_report(
                output_dir=config.trade_log_dir,
                benchmark=config.benchmark_symbol,
                title=f"{result.strategy_name} Performance Report",
            )
            if report_path:
                result.log_files["performance_report"] = str(report_path)
        except Exception as e:
            print(f"生成绩效报告失败: {e}")

    # 维度分析：资产类别（腿）级 + 标的（ETF）级，权重/市值/净值曲线 + 明细数据
    try:
        result.log_files.update(
            export_leg_analysis(result, leg_config, config.trade_log_dir)
        )
        result.log_files.update(
            export_symbol_analysis(result, leg_config, config.trade_log_dir)
        )
    except Exception as e:
        print(f"导出维度分析失败: {e}")

    print("\n" + "=" * 64)
    print("回测结果")
    print("=" * 64)

    print(f"\n策略名称: {result.strategy_name}")
    print(
        f"净值计值区间: {result.daily_values[0]['date']} ~ {result.daily_values[-1]['date']}"
        if result.daily_values
        else "无净值数据"
    )

    print("\n收益指标:")
    print(f"  初始资金: {result.initial_cash:,.2f} 元")
    print(f"  最终资产: {result.final_value:,.2f} 元")
    print(f"  收益率:   {result.return_pct:+.2%}")

    print("\n风险指标:")
    print(f"  最大回撤: {result.calculate_max_drawdown():.2%}")
    print(
        f"  夏普比率: {result.calculate_sharpe_ratio(risk_free_rate=0.015):.2f} (rf=1.5%)"
    )

    print("\n交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    orders = pd.DataFrame(result.order_log) if result.order_log else pd.DataFrame()
    if not orders.empty and "status" in orders.columns:
        completed = orders[orders["status"] == "completed"]
        print(f"  成交订单数: {len(completed)}")
        if "commission" in completed.columns:
            print(f"  总佣金:   {completed['commission'].sum():,.2f} 元")

    if result.log_files:
        print("\n输出文件:")
        for name, path in result.log_files.items():
            print(f"  {name}: {path}")

    print("\n对拍基准（规格书附录，冻结样本 2020-12-18 ~ 2024-12-31）:")
    print("  框架版:  年化 6.37% / 夏普 1.18 / 回撤 -3.17% / 调仓 24 次")
    print("  研究版:  年化 6.80% / 夏普 1.23 / 回撤 -3.32% / 调仓 23 次")
    print("=" * 64)


if __name__ == "__main__":
    main()
