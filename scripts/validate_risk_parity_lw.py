"""Offline A/B backtest for the constant-correlation Ledoit-Wolf formula fix.

Run from the repository root:
    python scripts/validate_risk_parity_lw.py

Loads both estimators against one in-memory market-data snapshot. The old math
module is read from Git without changing the working tree. No market data is
downloaded. Outputs include input hashes, daily NAV, fills, signals and a report.
"""

import argparse
import hashlib
import io
import json
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch

import backtrader as bt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trader_center.backtest import BacktestConfig, BacktestRunner
from trader_center.backtest.data_feed import PandasDataFeed
from trader_center.backtest.strategy import risk_parity as strategy_module
from trader_center.backtest.strategy import risk_parity_math as fixed_math

ROOT = Path(__file__).resolve().parents[1]
BASELINE_REF = "150f001d40c8705d4fbf8f684cb4d9f3d33ac744"
MATH_PATH = "trader_center/backtest/strategy/risk_parity_math.py"
SYMBOLS = [s for leg in strategy_module.LEG_CONFIG.values() for s in leg["members"]]
PARAMS = dict(
    cov_window=250,
    rebalance_threshold=0.05,
    equity_cap=0.30,
    commission=0.0005,
    stamp_duty=0.0,
    min_commission=0.0,
)


class AuditStrategy(strategy_module.RiskParityStrategy4A):
    """Observe the existing strategy without changing its decisions or orders."""

    def __init__(self):
        super().__init__()
        self.audit_fills = []
        self.audit_failures = []
        self.audit_batches = []
        self.audit_checks = []

    def _compute_leg_weights(self):
        weights, cov, rc = super()._compute_leg_weights()
        assert np.isfinite(cov).all() and np.linalg.eigvalsh(cov).min() > 0
        assert np.isfinite(weights).all() and (weights >= 0).all()
        np.testing.assert_allclose(weights.sum(), 1, atol=1e-10)
        np.testing.assert_allclose(rc, 0.25, atol=1e-6)
        self.audit_checks.append(
            {
                "date": self.datas[0].datetime.date(0).isoformat(),
                "predicted_annual_volatility": float(
                    np.sqrt(weights @ cov @ weights * 252)
                ),
                "max_risk_budget_error": float(np.max(np.abs(rc - 0.25))),
                **dict(zip(strategy_module.LEG_NAMES, weights.tolist())),
            }
        )
        return weights, cov, rc

    def _execute_rebalance(self, targets):
        self.audit_batches.append(self.datas[0].datetime.date(0).isoformat())
        super()._execute_rebalance(targets)

    def notify_order(self, order):
        if order.status == order.Completed:
            self.audit_fills.append(
                {
                    "date": bt.num2date(order.executed.dt).date().isoformat(),
                    "notification_date": self.datas[0].datetime.date(0).isoformat(),
                    "symbol": order.data._name,
                    "size": order.executed.size,
                    "price": order.executed.price,
                    "commission": order.executed.comm,
                }
            )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.audit_failures.append(
                {
                    "date": self.datas[0].datetime.date(0).isoformat(),
                    "symbol": order.data._name,
                    "status": order.getstatusname(),
                }
            )
        super().notify_order(order)


class SnapshotRunner(BacktestRunner):
    def __init__(self, frames, **kwargs):
        super().__init__(**kwargs)
        self.frames = frames

    def _load_data(self, symbol, start, end):
        return PandasDataFeed.from_datahub(
            symbol, self.frames[symbol].loc[start:end].copy()
        )


def metrics(nav, fills, batches, failures):
    returns = nav["value"].pct_change().dropna()
    ratio = nav["value"].iloc[-1] / nav["value"].iloc[0]
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    volatility = returns.std(ddof=1) * np.sqrt(252)
    return {
        "start": nav.index[0].date().isoformat(),
        "end": nav.index[-1].date().isoformat(),
        "return_pct": float(ratio - 1),
        "cagr": float(ratio ** (1 / years) - 1),
        "volatility": float(volatility),
        "sharpe_rf_1_5": float((returns.mean() * 252 - 0.015) / volatility),
        "max_drawdown": float((nav["value"] / nav["value"].cummax() - 1).min()),
        "final_value": float(nav["value"].iloc[-1]),
        "rebalance_batches": len(batches),
        "completed_orders": len(fills),
        "failed_orders": len(failures),
        "fees": float(sum(fill["commission"] for fill in fills)),
    }


def run_variant(label, end, estimator, frames, output):
    run_dir = output / f"{label}_{end}"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = BacktestConfig(
        initial_cash=1_000_000,
        auto_save_trades=False,
        auto_save_plot=False,
        enable_quantstats=False,
        auto_save_report=False,
        output_dir=run_dir,
        trade_log_dir=run_dir,
    )
    runner = SnapshotRunner(frames, config=config, enable_plot=False)
    with patch.multiple(
        strategy_module,
        ledoit_wolf_cov=estimator.ledoit_wolf_cov,
        shrinkage_intensity=estimator.shrinkage_intensity,
    ):
        result = runner.run(
            strategy=AuditStrategy,
            symbols=SYMBOLS,
            start="2019-11-01",
            end=end,
            initial_cash=1_000_000,
            strategy_params=PARAMS,
        )
    if result.error_message:
        raise RuntimeError(result.error_message)
    strategy = runner._cerebro.runstrats[0][0]
    signals = pd.DataFrame(result.signal_log)
    first_signal = pd.to_datetime(signals["datetime"]).min().normalize()
    nav = pd.DataFrame(result.daily_values).set_index("date")
    nav.index = pd.to_datetime(nav.index)
    nav = nav.loc[first_signal:]
    nav.to_csv(run_dir / "daily_values.csv")
    signals.to_csv(run_dir / "signals.csv", index=False)
    pd.DataFrame(strategy.audit_fills).to_csv(run_dir / "fills.csv", index=False)
    pd.DataFrame(strategy.audit_checks).to_csv(run_dir / "risk_checks.csv", index=False)
    (run_dir / "failures.json").write_text(
        json.dumps(strategy.audit_failures, indent=2), encoding="utf-8"
    )
    summary = metrics(
        nav, strategy.audit_fills, strategy.audit_batches, strategy.audit_failures
    )
    summary["pending_target_at_end"] = strategy._pending_targets is not None
    summary["risk_checks"] = len(strategy.audit_checks)
    summary["max_risk_budget_error"] = max(
        row["max_risk_budget_error"] for row in strategy.audit_checks
    )
    summaries = {"frozen" if end == "2024-12-31" else "full": summary}
    if end > "2024-12-31":
        # Include the previous year's final NAV so the first 2025 return is retained.
        anchor = nav.loc[:"2024-12-31"].index[-1]
        summaries["post_2024"] = metrics(
            nav.loc[anchor:],
            [r for r in strategy.audit_fills if r["date"] > "2024-12-31"],
            [d for d in strategy.audit_batches if d > "2024-12-31"],
            [r for r in strategy.audit_failures if r["date"] > "2024-12-31"],
        )
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default=BASELINE_REF)
    parser.add_argument(
        "--data-dir", type=Path, default=Path.home() / ".trader_center/data/bars/daily"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "logs/validation/risk_parity_lw_fix"
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    snapshot_dir = args.output / "input_data"
    snapshot_dir.mkdir(exist_ok=True)
    old_source = subprocess.check_output(
        ["git", "show", f"{args.baseline_ref}:{MATH_PATH}"], cwd=ROOT
    )
    old_math = types.ModuleType("baseline_risk_parity_math")
    exec(compile(old_source, "baseline_risk_parity_math.py", "exec"), old_math.__dict__)
    (args.output / "baseline_risk_parity_math.py").write_bytes(old_source)
    (args.output / "fixed_risk_parity_math.py").write_bytes(
        (ROOT / MATH_PATH).read_bytes()
    )
    frames, inputs = {}, {}
    for symbol in SYMBOLS:
        path = args.data_dir / f"{symbol}.parquet"
        # Hash and parse the same bytes, even if the cache is updated during the run.
        raw = path.read_bytes()
        (snapshot_dir / path.name).write_bytes(raw)
        frame = pd.read_parquet(io.BytesIO(raw)).set_index("timestamp").sort_index()
        assert frame.index.is_unique and np.isfinite(frame["close"]).all()
        assert (frame["close"] > 0).all()
        frames[symbol] = frame
        inputs[symbol] = {
            "path": str(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "start": str(frame.index.min()),
            "end": str(frame.index.max()),
            "rows": len(frame),
        }
    # Preserve per-feed inception dates and require aligned calendars thereafter.
    first_common = max(frame.index.min() for frame in frames.values())
    last_common = min(frame.index.max() for frame in frames.values())
    calendars = [f.loc[first_common:last_common].index for f in frames.values()]
    assert all(calendars[0].equals(c) for c in calendars[1:]), (
        "Unaligned input calendars"
    )
    end = last_common.date().isoformat()
    assert end > "2024-12-31", "Post-2024 validation requires more recent cached data"
    manifest = {
        "baseline_ref": args.baseline_ref,
        "parameters": PARAMS,
        "inputs": inputs,
        "fixed_math_sha256": hashlib.sha256(
            (ROOT / MATH_PATH).read_bytes()
        ).hexdigest(),
        "latest_common_date": end,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    results = {}
    for label, estimator in [("before", old_math), ("after", fixed_math)]:
        results[label] = {}
        for cutoff in ["2024-12-31", end]:
            print(f"Running {label} through {cutoff}", flush=True)
            results[label].update(
                run_variant(label, cutoff, estimator, frames, args.output)
            )
    (args.output / "comparison.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    lines = [
        "# Ledoit–Wolf 公式修复回测验证",
        "",
        f"旧公式基准提交：`{args.baseline_ref}`；最新共同行情日：{end}。",
        "",
        "同一份本地缓存、同一策略与参数；仅切换协方差估计和收缩强度函数。",
        "资金 100 万，窗口 250 日，调仓阈值 5%，股腿风险上限 30%，佣金 5bp。",
        "",
        "| 区间 | 版本 | 累计收益 | CAGR | 年化波动 | 夏普 | 最大回撤 | 调仓批次 | 成交单 | 失败单 | 实际费用（元） |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for period in ["frozen", "post_2024", "full"]:
        for label in ["before", "after"]:
            m = results[label][period]
            lines.append(
                f"| {period}: {m['start']} ~ {m['end']} | {label} | {m['return_pct']:.2%} "
                f"| {m['cagr']:.2%} | {m['volatility']:.2%} | {m['sharpe_rf_1_5']:.3f} "
                f"| {m['max_drawdown']:.2%} | {m['rebalance_batches']} | {m['completed_orders']} "
                f"| {m['failed_orders']} | {m['fees']:.2f} |"
            )
    lines += [
        "",
        "口径与限制：",
        "",
        "- 预热期裁剪至首次信号日；CAGR 使用实际日历跨度 / 365.25。",
        "- 波动为日收益样本标准差 × √252；夏普为 (日均收益 × 252 − 1.5%) / 年化波动。",
        "- post_2024 从完整持仓路径切片，保留 2024 年末净值作为基点，未在 2025 年重新建仓。",
        "- 费用直接汇总 broker 实际成交费用；成交日期取 executed.dt。",
        "- 调仓批次按提交日计数，含首次建仓；失败单单独列出。",
        "- 每次风险估计均核验矩阵有限且正定、权重非负且归一化、ERC 误差 ≤ 1e-6。",
        "- 月末终点判断、持仓漂移、成交撮合和其他既有机制均保持原样；本验证不代表这些问题已修复。",
        "- 最新终点若有待执行目标，则未计为已执行调仓；详情见 comparison.json。",
        "- 本地缓存来源和覆盖范围不同于规格书 Wind 冻结样本，不能直接复现规格书绩效。",
        "",
        "复现命令：`python scripts/validate_risk_parity_lw.py`。",
        "输入快照保存在 input_data，可通过 --data-dir 指向该目录复现；指纹见 manifest.json。",
        "旧版与修复版数学模块均已快照；逐日净值、实际成交、信号与风险检查见各版本子目录。",
    ]
    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Report: {args.output / 'report.md'}")


if __name__ == "__main__":
    main()
