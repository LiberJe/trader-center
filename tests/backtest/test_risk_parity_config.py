"""Configuration flows through loading, baskets, orders, reports and exports."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import backtrader as bt
import numpy as np
import pandas as pd
import pytest

from trader_center.backtest import BacktestRunner
from trader_center.backtest.data_feed import PandasDataFeed
from trader_center.backtest.strategy import RiskParityStrategy4A
from trader_center.backtest.strategy.risk_parity_config import (
    DEFAULT_ASSET_CONFIG, DEFAULT_LEG_CONFIG, resolve_risk_parity_config,
)


def replacement_assets():
    return {"513100.SH" if symbol == "510300.SH" else symbol:
            {**info, "name": "纳指ETF" if symbol == "510300.SH" else info["name"]}
            for symbol, info in DEFAULT_ASSET_CONFIG.items()}


def synthetic_frames(symbols, periods=280):
    rng = np.random.default_rng(17)
    dates = pd.bdate_range("2024-01-02", periods=periods)
    returns = rng.normal(0.0001, 0.003, size=(periods, len(symbols)))
    prices = 10 * np.exp(np.cumsum(returns, axis=0))
    return {symbol: pd.DataFrame({**{col: prices[:, i] for col in ["open", "high", "low", "close"]},
                                  "volume": 1_000_000}, index=dates)
            for i, symbol in enumerate(symbols)}


def test_defaults_and_explicit_replacement_are_independent():
    defaults, default_legs = resolve_risk_parity_config()
    supplied = replacement_assets()
    assets, legs = resolve_risk_parity_config(supplied)
    assert "510300.SH" in defaults and "510300.SH" not in assets
    assert legs["equity"]["members"] == ("513100.SH",)
    assert default_legs == DEFAULT_LEG_CONFIG
    supplied["513100.SH"]["leg"] = "gold"
    assets["513100.SH"]["name"] = "modified"
    assert legs["equity"]["members"] == ("513100.SH",)
    assert resolve_risk_parity_config()[0] == defaults


def test_english_and_chinese_leg_names_resolve_identically():
    assets, legs = resolve_risk_parity_config()
    chinese = {symbol: {**info, "leg": legs[info["leg"]]["name"]} for symbol, info in assets.items()}
    assert resolve_risk_parity_config(chinese) == (assets, legs)


@pytest.mark.parametrize("assets, message", [
    ({}, "非空"),
    ([], "非空"),
    ({"A": {}}, "leg"),
    ({"A": "equity"}, "必须是字典"),
    ({" A": {"leg": "equity"}}, "首尾空白"),
    ({"A": {"leg": "equity"}}, "至少需要两条"),
    ({"A": {"leg": "equity", "name": ""}, "B": {"leg": "bond"}}, "name"),
    ({"A": {"leg": "equity", "leg_name": "一条腿"},
      "B": {"leg": "bond", "leg_name": "一条腿"}}, "相同的显示名称"),
    ({"A": {"leg": "equity", "leg_name": "一条腿"},
      "B": {"leg": "equity", "leg_name": "另一条腿"},
      "C": {"leg": "bond"}}, "不一致"),
])
def test_invalid_configuration_fails_at_boundary(assets, message):
    with pytest.raises(ValueError, match=message):
        resolve_risk_parity_config(assets)


def test_multiple_equity_members_affect_covariance_and_split_target():
    assets = {"A": {"leg": "equity"}, "B": {"leg": "股票"}, "C": {"leg": "bond"}}
    _, legs = resolve_risk_parity_config(assets)
    state = SimpleNamespace(leg_names=list(legs), leg_config=legs, p=SimpleNamespace(cov_window=2),
                            _rets={"A": [.01, .02, 99], "B": [.03, .04, -99], "C": [.005, .006, 42]})
    np.testing.assert_allclose(RiskParityStrategy4A._leg_return_matrix(state),
                               [[.02, .005], [.03, .006]])
    assert RiskParityStrategy4A._leg_to_etf_weights(state, np.array([.6, .4])) == {
        "A": .3, "B": .3, "C": .4,
    }


def test_strategy_instances_do_not_share_external_or_default_configuration():
    custom = replacement_assets()
    frames = synthetic_frames([*DEFAULT_ASSET_CONFIG, "513100.SH"], periods=3)
    cerebro = bt.Cerebro()
    cerebro.addstrategy(RiskParityStrategy4A)
    cerebro.addstrategy(RiskParityStrategy4A, asset_config=custom)
    for symbol, frame in frames.items():
        cerebro.adddata(bt.feeds.PandasData(dataname=frame), name=symbol)
    default, alternate = cerebro.run()
    custom["513100.SH"]["leg"] = "gold"
    assert default.leg_config["equity"]["members"] == ("510300.SH",)
    assert alternate.leg_config["equity"]["members"] == ("513100.SH",)
    assert default.symbols != alternate.symbols
    assert "513100.SH" not in DEFAULT_ASSET_CONFIG


def test_missing_feed_error_names_the_external_symbol():
    cerebro = bt.Cerebro()
    cerebro.addstrategy(RiskParityStrategy4A, asset_config=replacement_assets())
    for symbol, frame in synthetic_frames(DEFAULT_ASSET_CONFIG, periods=3).items():
        cerebro.adddata(bt.feeds.PandasData(dataname=frame), name=symbol)
    with pytest.raises(ValueError, match="513100.SH") as exc:
        cerebro.run()
    assert "510300.SH" not in str(exc.value)


@pytest.mark.parametrize("explicit", [False, True])
def test_task_entry_passes_same_configuration_to_strategy_report_and_exports(monkeypatch, tmp_path, explicit):
    from tasks import risk_parity_runner as task

    startup = replacement_assets()
    # Exercise both the module's startup ASSET_CONFIG and a function override,
    # including a new leg key whose display name cannot come from global lists.
    supplied = ({"CUSTOM.A": {"name": "另类ETF", "leg": "alternative", "leg_name": "另类资产"},
                 "CUSTOM.B": {"name": "债券ETF", "leg": "bond"}} if explicit else startup)
    assets, legs = resolve_risk_parity_config(supplied)
    frames = synthetic_frames(assets)
    runs, exports = [], []

    class OfflineRunner(BacktestRunner):
        def __init__(self, config, **kwargs):
            config.auto_save_trades = False
            config.auto_save_plot = False
            config.auto_save_report = False
            config.enable_quantstats = False
            super().__init__(config=config, enable_plot=False)

        def _load_data(self, symbol, start, end):
            assert symbol in assets
            return PandasDataFeed.from_datahub(symbol, frames[symbol])

        def run(self, **kwargs):
            assert kwargs["symbols"] == list(assets)
            assert kwargs["strategy_params"]["asset_config"] == assets
            result = super().run(**kwargs)
            strategy = self._cerebro.runstrats[0][0]
            assert strategy.leg_config == legs
            assert all(s["symbol"] in assets for s in result.signal_log)
            assert all(o["symbol"] in assets for o in result.order_log)
            assert strategy.rebalance_count > 0
            runs.append(result)
            return result

    def capture_export(result, config, output):
        exports.append(deepcopy(config))
        return {}

    monkeypatch.setattr(task, "ASSET_CONFIG", startup)
    monkeypatch.setattr(task, "BacktestRunner", OfflineRunner)
    monkeypatch.setattr(task, "export_leg_analysis", capture_export)
    monkeypatch.setattr(task, "export_symbol_analysis", capture_export)
    monkeypatch.setattr(task, "__file__", str(tmp_path / "tasks/risk_parity_runner.py"))
    result = task.main(asset_config=supplied if explicit else None)
    assert result["status"] == "success"
    assert result["asset_config"] == assets and result["leg_config"] == legs
    assert exports == [legs, legs]
    text = Path(result["report_path"]).read_text(encoding="utf-8")
    for symbol, info in assets.items():
        assert symbol in text and info["name"] in text
    assert "510300.SH" not in text
    assert ("513100.SH" in text) is (not explicit)
    assert len(runs) == 1
    # A separate report call also finds the actual run config in result.params.
    recovered = task.generate_daily_report(runs[0], tmp_path, "20250127", "2025年01月27日")
    assert Path(recovered).read_text(encoding="utf-8").count("510300.SH") == 0


def test_analysis_colors_support_custom_legs():
    from backtest_runner.run_risk_parity import _leg_colors, _symbol_colors

    _, legs = resolve_risk_parity_config({
        "A": {"leg": "equity"}, "B": {"leg": "alternative", "leg_name": "另类资产"},
    })
    assert set(_leg_colors(legs)) == {"equity", "alternative"}
    assert set(_symbol_colors(legs)) == {"A", "B"}


def test_cli_json_configuration_controls_csv_loading_and_exports(monkeypatch, tmp_path):
    from backtest_runner import run_risk_parity as cli

    supplied = replacement_assets()
    assets, legs = resolve_risk_parity_config(supplied)
    config_path = tmp_path / "assets.json"
    config_path.write_text(json.dumps(supplied, ensure_ascii=False), encoding="utf-8")
    for symbol, frame in synthetic_frames(assets).items():
        frame.rename_axis("date").to_csv(tmp_path / f"{symbol}.csv")
    original_runner = cli.CSVDataRunner
    captures, exports = [], []

    class OfflineCSVRunner(original_runner):
        def __init__(self, config, **kwargs):
            config.auto_save_trades = False
            config.enable_quantstats = False
            config.trade_log_dir = tmp_path
            super().__init__(config=config, **kwargs)

        def run(self, **kwargs):
            assert kwargs["symbols"] == list(assets)
            assert kwargs["strategy_params"]["asset_config"] == assets
            result = super().run(**kwargs)
            assert not result.error_message
            assert self._cerebro.runstrats[0][0].leg_config == legs
            captures.append(result)
            return result

    def capture_export(result, config, output):
        exports.append(config)
        return {}

    monkeypatch.setattr(cli, "CSVDataRunner", OfflineCSVRunner)
    monkeypatch.setattr(cli, "export_leg_analysis", capture_export)
    monkeypatch.setattr(cli, "export_symbol_analysis", capture_export)
    monkeypatch.setattr("sys.argv", ["run_risk_parity.py", "--asset-config", str(config_path),
                                     "--source", "csv", "--csv-dir", str(tmp_path),
                                     "--start", "2024-01-01", "--end", "2025-03-01",
                                     "--no-plot", "--no-report"])
    cli.main()
    assert len(captures) == 1 and exports == [legs, legs]
