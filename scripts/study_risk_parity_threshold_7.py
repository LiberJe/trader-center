"""Supplement the frequency study with 7%, using its saved input snapshot.

python scripts/study_risk_parity_threshold_7.py
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import study_risk_parity_rebalance as study


def main():
    parent = study.ROOT / "logs/research/risk_parity_rebalance_20261013"
    output = parent / "supplement_7pct"
    original = json.loads((parent / "manifest.json").read_text(encoding="utf-8"))
    # The research audit explicitly selects its schedule; changing production's
    # default from monthly to daily must not alter historical control variants.
    assert json.loads(json.dumps(study.production.LEG_CONFIG)) == original["legs"]
    assert study.production.RiskParityStrategy4A.params.cov_window == original["window"]
    math_path = study.ROOT / "trader_center/backtest/strategy/risk_parity_math.py"
    assert hashlib.sha256(math_path.read_bytes()).hexdigest() == original["math_sha256"]
    print("Loading original immutable snapshot; supplement thresholds 5 / 6 / 7 / 7.5 percent", flush=True)
    market, inputs = study.load_market(parent / "input_data", output)
    for symbol, details in inputs.items():
        assert details["sha256"] == original["inputs"][symbol]["sha256"]
    thresholds = [.05, .06, .07, .075]
    sims, rows, annual = {}, [], []
    for cost in [0, .0005, .001, .002]:
        for mode in ["monthly", "daily"]:
            for threshold in thresholds:
                sim = study.simulate(market, mode, threshold, cost)
                if cost == .0005:
                    assert not sim.failures
                    study.save_sim(sim, output / "variants" / sim.label)
                sims[sim.label] = sim
                for period, start, end in [("train", None, study.TRAIN_END),
                                           ("oos", "2025-01-01", None), ("full", None, None)]:
                    rows.append(dict(period=period, **study.metrics(sim, start, end)))
                if cost == .0005:
                    for year in range(2021, market.dates[-1].year + 1):
                        annual.append(dict(year=year, **study.metrics(sim, f"{year}-01-01", f"{year}-12-31")))
    table = pd.DataFrame(rows)
    # The unchanged 5/6/7.5 controls must exactly reproduce the previous study.
    control = pd.read_csv(parent / "summary.csv")
    for row in table[table.threshold != .07].itertuples():
        prior = control[(control.label == row.label) & (control.period == row.period)].iloc[0]
        for metric in ["cagr", "sharpe", "mdd", "batches", "fees", "mean_rc_error"]:
            np.testing.assert_allclose(getattr(row, metric), prior[metric], atol=1e-12, rtol=1e-12)
    validations = []
    for mode in ["monthly", "daily"]:
        label = f"{mode}_7pct_5bp"
        print(f"Independent Backtrader tie-out: {label}", flush=True)
        validations.append(study.framework_validate(market, sims[label], output))
    bootstrap = []
    for mode in ["monthly", "daily"]:
        candidate = sims[f"{mode}_7pct_5bp"]
        for threshold in [.05, .06, .075]:
            reference = sims[f"{mode}_{threshold * 100:g}pct_5bp"]
            for period, start, end in [("train", None, study.TRAIN_END),
                                       ("oos", "2025-01-01", None), ("full", None, None)]:
                for block in [21, 63]:
                    bootstrap.append(dict(period=period, **study.paired_bootstrap(candidate, reference, start, end, block)))
    manifest = dict(parent_manifest=str(parent / "manifest.json"), inputs=inputs,
                    thresholds=thresholds, commissions=[0, .0005, .001, .002],
                    first_signal=original["first_signal"], latest_common_date=original["latest_common_date"],
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    shared_engine_sha256=hashlib.sha256(Path(study.__file__).read_bytes()).hexdigest(),
                    production_sha256=hashlib.sha256(Path(study.production.__file__).read_bytes()).hexdigest(),
                    reference_production_sha256=original["production_sha256"], math_sha256=original["math_sha256"],
                    selection="User-requested exploratory 7% supplement after the original grid was observed")
    table.to_csv(output / "summary.csv", index=False)
    pd.DataFrame(annual).to_csv(output / "annual.csv", index=False)
    for name, value in [("manifest", manifest), ("framework_validation", validations), ("bootstrap", bootstrap)]:
        (output / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    report(output, table, bootstrap)
    print(table[table.commission == .0005][["period", "mode", "threshold", "cagr", "sharpe", "mdd", "batches", "fees", "mean_rc_error"]].to_string(index=False))
    print(f"Report: {output / 'report.html'}", flush=True)


def report(output, table, bootstrap):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    plt.rcParams.update({"font.family": "Microsoft YaHei", "axes.unicode_minus": False,
                         "figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False})
    main = table[table.commission == .0005]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for period, style, title in [("full", "-", "全区间"), ("oos", "--", "2025 年起")]:
        for mode, color, mode_name in [("monthly", "#245b9b", "月末"), ("daily", "#df6a35", "每日")]:
            data = main[(main.period == period) & (main['mode'] == mode)].sort_values("threshold")
            for ax, metric, metric_name in zip(axes, ["cagr", "sharpe", "mdd"], ["年化收益", "夏普", "最大回撤"]):
                ax.plot(data.threshold * 100, data[metric], style, color=color, marker="o", label=f"{mode_name} · {title}")
                ax.set_title(metric_name)
                ax.set_xlabel("阈值（%）")
                ax.axvline(7, color="#7c8996", alpha=.4)
                ax.grid(alpha=.2)
    for ax in [axes[0], axes[2]]:
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    axes[1].legend(fontsize=8)
    fig.suptitle("7% 阈值补充实验 · 同一数据快照与单边 5bp 成本")
    fig.tight_layout()
    fig.savefig(output / "comparison.png", bbox_inches="tight")
    plt.close(fig)
    columns = ["mode", "threshold", "cagr", "sharpe", "mdd", "batches", "fees", "mean_rc_error"]

    def formatted(frame):
        f = frame[columns].copy()
        f['mode'] = f['mode'].map({"monthly": "月末", "daily": "每日"})
        for c in ["threshold", "cagr", "mdd", "mean_rc_error"]:
            f[c] = f[c].map(lambda x: f"{x:.2%}")
        f.sharpe = f.sharpe.map(lambda x: f"{x:.3f}")
        f.fees = f.fees.map(lambda x: f"{x:,.2f}")
        return f.rename(columns={"mode": "检查频率", "threshold": "阈值", "cagr": "年化收益", "sharpe": "夏普",
                                 "mdd": "最大回撤", "batches": "实际调仓次数", "fees": "费用（元）",
                                 "mean_rc_error": "平均最大单腿风险预算偏离"}).to_html(index=False)

    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>7% 调仓阈值补充验证</title>",
             "<style>body{font:16px/1.65 'Microsoft YaHei',sans-serif;max-width:1200px;margin:40px auto;padding:0 24px;color:#183044}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:right;padding:8px;border-bottom:1px solid #dce3ea}th{background:#edf2f7}img{width:100%}a{color:#245b9b}</style>",
             "<h1>7% 调仓阈值补充验证</h1>",
             "<p>2021-01-29—2026-10-12；沿用原研究保存的六只 ETF 行情快照，逐个校验输入哈希。资金 100 万，100 股整手，250 日 LW/ERC，" 
             "估计窗口截至 T-1，触发后 T+1 收盘成交。主比较单边成本 5bp，夏普无风险利率 1.5%。调仓次数包含首次建仓。</p>",
             "<p>7% 为看过原研究结果后追加的假设；2025 年起数据用于分段比较，不视为未接触的未来样本。" 
             "5%、6%、7.5% 控制组逐项复现原结果；月末 7% 和每日 7% 均通过生产交易框架信号、股数、价格与佣金对拍。</p>",
             "<img src='comparison.png'>"]
    for period, title in [("full", "全区间"), ("train", "2024 年及以前"), ("oos", "2025 年起")]:
        parts.extend([f"<h2>{title}</h2>", formatted(main[main.period == period])])
    b = pd.DataFrame(bootstrap)[["a", "b", "period", "block", "sharpe_difference", "sharpe_ci_95", "annual_log_return_difference", "annual_log_return_ci_95"]].copy()
    b.sharpe_difference = b.sharpe_difference.map(lambda x: f"{x:+.3f}")
    b.sharpe_ci_95 = b.sharpe_ci_95.map(lambda x: f"[{x[0]:+.3f}, {x[1]:+.3f}]")
    b.annual_log_return_difference = b.annual_log_return_difference.map(lambda x: f"{x:+.2%}")
    b.annual_log_return_ci_95 = b.annual_log_return_ci_95.map(lambda x: f"[{x[0]:+.2%}, {x[1]:+.2%}]")
    parts.extend(["<h2>成对块自助比较</h2><p>7% 对同频率的 5%、6%、7.5%，21 / 63 日块长，各 2000 次，seed=42；" 
                  "收益差为年化对数收益差。仅为给定参数差异的置信区间，未作全组多重比较校正。</p>", b.to_html(index=False),
                  "<h2>成本压力测试</h2><p>按每档成本重新交易，取整可能改变后续持仓；失败单非零时，结果也包含拒单影响。</p>",
                  table[(table.period == "full") & (table.threshold == .07)][["mode", "commission", "cagr", "sharpe", "mdd", "failed_orders"]].round(6).to_html(index=False),
                  "<p>前复权行情与整手规则继承原回测；未模拟额外滑点、成交冲击和现金利息。风险预算偏离为每日各腿风险贡献相对 25% 的" 
                  "最大绝对偏离，再对日期取平均，单位为百分点。</p>",
                  "<p><a href='../report.html'>原完整研究</a> · <a href='summary.csv'>结果明细</a> · <a href='annual.csv'>分年表现</a> · <a href='manifest.json'>快照与复现信息</a></p></html>"])
    (output / "report.html").write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
