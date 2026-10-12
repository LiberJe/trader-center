"""Tie production daily 5% decisions/fills to the previously saved experiment.

python scripts/validate_risk_parity_daily.py

Uses the immutable 2026-10-13 study snapshot, normal BacktestRunner and production
decision/position logic. Does not override schedules, weights or order sizing.
"""

import hashlib
import json
import sys
from pathlib import Path

import backtrader as bt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trader_center.backtest import BacktestConfig, BacktestRunner  # noqa: E402
from trader_center.backtest.data_feed import PandasDataFeed  # noqa: E402
from trader_center.backtest.strategy import risk_parity as production  # noqa: E402


class ProductionAudit(production.RiskParityStrategy4A):
    def __init__(self):
        super().__init__()
        self.audit_fills, self.audit_failures, self.audit_signals, self.audit_batches = [], [], [], []
        self.audit_check_dates = []

    def _compute_leg_weights(self):
        weights, cov, rc = super()._compute_leg_weights()
        np.testing.assert_allclose(rc, 1 / len(production.LEG_NAMES), atol=1e-6)
        self.audit_check_dates.append(self.datas[0].datetime.date(0))
        return weights, cov, rc

    def _log_decision(self, *args, **kwargs):
        self.audit_signals.append(self.datas[0].datetime.date(0))
        super()._log_decision(*args, **kwargs)

    def _execute_rebalance(self, targets):
        self.audit_batches.append(self.datas[0].datetime.date(0))
        super()._execute_rebalance(targets)

    def notify_order(self, order):
        if order.status == order.Completed:
            self.audit_fills.append(dict(date=pd.Timestamp(bt.num2date(order.executed.dt).date()),
                                         symbol=order.data._name, size=order.executed.size,
                                         price=order.executed.price, commission=order.executed.comm))
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.audit_failures.append(order.getstatusname())
        super().notify_order(order)


class SnapshotRunner(BacktestRunner):
    def __init__(self, frames, **kwargs):
        super().__init__(**kwargs)
        self.frames = frames

    def _load_data(self, symbol, start, end):
        return PandasDataFeed.from_datahub(symbol, self.frames[symbol].loc[start:end].copy())


def main():
    reference = ROOT / "logs/research/risk_parity_rebalance_20261013"
    output = ROOT / "logs/validation/risk_parity_daily_20261013"
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    frames = {}
    for symbol, details in manifest["inputs"].items():
        path = reference / "input_data" / f"{symbol}.parquet"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == details["sha256"]
        frames[symbol] = pd.read_parquet(path).set_index("timestamp").sort_index()
    config = BacktestConfig(initial_cash=1_000_000, auto_save_trades=False,
                            auto_save_plot=False, auto_save_report=False,
                            enable_quantstats=False, output_dir=output, trade_log_dir=output)
    runner = SnapshotRunner(frames, config=config, enable_plot=False)
    print("Running unchanged production decision/position methods through BacktestRunner", flush=True)
    result = runner.run(strategy=ProductionAudit, symbols=list(frames), start="2019-11-01",
                        end=manifest["latest_common_date"], initial_cash=1_000_000)
    assert not result.error_message, result.error_message
    strategy = runner._cerebro.runstrats[0][0]
    assert strategy.p.rebalance_threshold == .05
    actual = pd.DataFrame(strategy.audit_fills)
    expected_dir = reference / "variants/daily_5pct_5bp"
    expected = pd.read_csv(expected_dir / "fills.csv", parse_dates=["date"])
    assert len(actual) == len(expected)
    for column in ["date", "symbol", "size"]:
        assert actual[column].tolist() == expected[column].tolist(), column
    for column in ["price", "commission"]:
        np.testing.assert_allclose(actual[column], expected[column], atol=1e-8, rtol=1e-12)
    checks = pd.read_csv(expected_dir / "checks.csv", parse_dates=["date"])
    assert strategy.audit_signals == checks[checks.triggered].date.dt.date.tolist()
    assert strategy.audit_check_dates == checks.date.dt.date.tolist()
    batches = pd.read_csv(expected_dir / "batches.csv", parse_dates=["date"])
    assert strategy.audit_batches == batches.date.dt.date.tolist()
    assert not strategy.audit_failures
    expected_nav = pd.read_csv(expected_dir / "nav.csv", parse_dates=["date"])
    np.testing.assert_allclose(result.final_value, expected_nav.value.iloc[-1], atol=1e-8)
    actual.to_csv(output / "fills.csv", index=False)
    pd.DataFrame(result.signal_log).to_csv(output / "signals.csv", index=False)
    pd.DataFrame(result.daily_values).to_csv(output / "broker_daily_values.csv", index=False)
    expected_nav.to_csv(output / "matched_economic_daily_values.csv", index=False)
    strategy.trade_logger.save_all(output / "trade_logs")
    # Exercise the same reporting function used by the daily task, without
    # invoking task orchestration, downloading market data, or sending messages.
    from tasks.risk_parity_runner import generate_daily_report
    end = pd.Timestamp(manifest["latest_common_date"])
    generate_daily_report(result, output, end.strftime("%Y%m%d"), end.strftime("%Y年%m月%d日"))
    summary = dict(matched=True, start=str(checks.date.iloc[0].date()), end=str(end.date()),
                   threshold=strategy.p.rebalance_threshold, daily_checks=len(strategy.audit_check_dates),
                   signal_batches=len(strategy.audit_signals), executed_batches=len(strategy.audit_batches),
                   completed_orders=len(actual), failed_orders=len(strategy.audit_failures),
                   final_value=result.final_value, fees=float(actual.commission.sum()),
                   production_sha256=hashlib.sha256(Path(production.__file__).read_bytes()).hexdigest(),
                   reference_manifest=str(reference / "manifest.json"),
                   reference_production_sha256=manifest["production_sha256"])
    (output / "validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
