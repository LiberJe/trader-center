"""Offline smoke run of the task's actual configurable universe and reports.

python scripts/validate_risk_parity_universe.py

Loads the selected task ASSET_CONFIG from local Parquet caches, saves a snapshot,
and calls the real task entry, strategy, daily report, and dimension exporters.
Performance benchmark downloads and orchestration/messaging are not invoked.
"""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tasks import risk_parity_runner as task  # noqa: E402
from trader_center.backtest import BacktestRunner  # noqa: E402
from trader_center.backtest.data_feed import PandasDataFeed  # noqa: E402
from trader_center.backtest.strategy import resolve_risk_parity_config  # noqa: E402


def main():
    output = ROOT / "logs/validation/risk_parity_universe_20261013"
    snapshot = output / "input_data"
    snapshot.mkdir(parents=True, exist_ok=True)
    assets, legs = resolve_risk_parity_config(task.ASSET_CONFIG)
    frames, inputs = {}, {}
    for symbol in assets:
        path = Path.home() / ".trader_center/data/bars/daily" / f"{symbol}.parquet"
        raw = path.read_bytes()
        (snapshot / path.name).write_bytes(raw)
        frame = pd.read_parquet(io.BytesIO(raw)).set_index("timestamp").sort_index()
        frames[symbol] = frame
        inputs[symbol] = {"sha256": hashlib.sha256(raw).hexdigest(), "rows": len(frame),
                          "start": str(frame.index.min()), "end": str(frame.index.max())}
    first = max(f.index.min() for f in frames.values())
    last = min(f.index.max() for f in frames.values())
    calendars = [f.loc[first:last].index for f in frames.values()]
    union = sorted(set().union(*(set(calendar) for calendar in calendars)))
    missing_dates = {symbol: [str(date.date()) for date in union if date not in calendar]
                     for symbol, calendar in zip(frames, calendars)}
    captures = []

    class OfflineRunner(BacktestRunner):
        def __init__(self, config, **kwargs):
            config.auto_save_report = False
            config.enable_quantstats = False
            config.auto_save_plot = False
            super().__init__(config=config, enable_plot=False)

        def _load_data(self, symbol, start, end):
            return PandasDataFeed.from_datahub(symbol, frames[symbol].loc[start:min(pd.Timestamp(end), last)])

        def run(self, **kwargs):
            assert kwargs["symbols"] == list(assets)
            assert kwargs["strategy_params"]["asset_config"] == assets
            result = super().run(**kwargs)
            strategy = self._cerebro.runstrats[0][0]
            assert strategy.asset_config == assets and strategy.leg_config == legs
            assert not result.error_message, result.error_message
            failures = [row for row in result.order_log if row["status"] in ["margin", "rejected", "canceled"]]
            assert not failures, failures
            assert all(row["symbol"] in assets for row in result.signal_log)
            assert all(row["symbol"] in assets for row in result.order_log)
            captures.append((result, strategy))
            return result

    print(f"Running real task with {list(assets)}", flush=True)
    with patch.object(task, "BacktestRunner", OfflineRunner), (output / "task_run.log").open("w", encoding="utf-8") as log:
        with redirect_stdout(log):
            returned = task.main(report_subdir="risk_parity_config_validation")
    assert returned["status"] == "success", returned
    result, strategy = captures[0]
    report = Path(returned["report_path"]).read_text(encoding="utf-8")
    for symbol, info in assets.items():
        assert symbol in report and info["name"] in report
    symbol_table = pd.read_csv(result.log_files["symbol_weights"])
    for symbol in assets:
        assert any(symbol in column for column in symbol_table.columns)
    absent_defaults = {"510300.SH", "513100.SH"} - set(assets)
    assert all(symbol not in report for symbol in absent_defaults)
    assert all(not any(symbol in column for column in symbol_table.columns) for symbol in absent_defaults)
    # Preserve the task loader's existing feed calendars. This smoke run checks
    # configuration propagation; recording gaps does not certify data quality.
    summary = dict(matched=True, asset_config=assets, leg_config=legs, inputs=inputs,
                   missing_common_dates=missing_dates,
                   latest_common_date=str(last.date()), rebalance_threshold=strategy.p.rebalance_threshold,
                   rebalance_batches=strategy.rebalance_count, final_value=result.final_value,
                   completed_orders=sum(row["status"] == "completed" for row in result.order_log),
                   failed_orders=0, report_path=returned["report_path"], exports=result.log_files)
    (output / "validation.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["matched", "latest_common_date", "rebalance_threshold",
                                            "rebalance_batches", "completed_orders", "failed_orders", "report_path"]},
                     indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
