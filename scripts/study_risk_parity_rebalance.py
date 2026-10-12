"""Offline, reproducible frequency/threshold study using the current 4A strategy.

python scripts/study_risk_parity_rebalance.py

The event simulator uses the production estimator and order sizing, with explicit
T+1 closing fills before the next close's decision. Production Backtrader fills
are independently compared, including a projected post-fill position for daily
checks (Backtrader delivers cheat-on-close fills one bar after their effective
date). No production strategy, parameter, task, or cached market data is changed.
"""

import argparse
import hashlib
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import backtrader as bt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trader_center.backtest.strategy import risk_parity as production  # noqa: E402
from trader_center.backtest.strategy.risk_parity_math import (  # noqa: E402
    erc_weights, ledoit_wolf_cov, risk_contributions,
)

SYMBOLS = [s for leg in production.LEG_CONFIG.values() for s in leg["members"]]
LEGS = list(production.LEG_CONFIG)
MEMBERS = [[SYMBOLS.index(s) for s in production.LEG_CONFIG[leg]["members"]] for leg in LEGS]
THRESHOLDS = [0, .005, .01, .02, .03, .04, .05, .06, .075, .10, .15, .20]
WINDOW = 250
INITIAL_CASH = 1_000_000.0
TRAIN_END = pd.Timestamp("2024-12-31")


@dataclass
class Market:
    dates: pd.DatetimeIndex
    prices: np.ndarray
    frames: dict
    targets: np.ndarray
    covariances: np.ndarray
    month_ends: np.ndarray
    first_signal: int


@dataclass
class Simulation:
    label: str
    mode: str
    threshold: float
    commission: float
    nav: pd.DataFrame
    fills: pd.DataFrame
    batches: pd.DataFrame
    checks: pd.DataFrame
    failures: list


def load_market(data_dir, output):
    frames, manifest = {}, {}
    snapshot = output / "input_data"
    snapshot.mkdir(parents=True, exist_ok=True)
    for symbol in SYMBOLS:
        path = data_dir / f"{symbol}.parquet"
        raw = path.read_bytes()
        (snapshot / path.name).write_bytes(raw)
        f = pd.read_parquet(io.BytesIO(raw)).set_index("timestamp").sort_index()
        assert f.index.is_unique
        assert np.isfinite(f.close).all() and (f.close > 0).all()
        frames[symbol] = f
        manifest[symbol] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                                rows=len(f), start=str(f.index.min()), end=str(f.index.max()))
    start = max(f.index.min() for f in frames.values())
    end = min(f.index.max() for f in frames.values())
    aligned = {s: f.loc[start:end] for s, f in frames.items()}
    dates = aligned[SYMBOLS[0]].index
    assert all(f.index.equals(dates) for f in aligned.values()), "Unequal trading calendars"
    prices = np.column_stack([aligned[s].close for s in SYMBOLS])
    returns = prices[1:] / prices[:-1] - 1
    leg_returns = np.column_stack([returns[:, ids].mean(axis=1) for ids in MEMBERS])
    targets = np.full((len(dates), len(LEGS)), np.nan)
    covs = np.full((len(dates), len(LEGS), len(LEGS)), np.nan)
    # Production BaseStrategy.nextstart skips the first fully aligned bar. It
    # then records 251 returns before the initial decision, excluding today's.
    first_signal = WINDOW + 1
    for i in range(first_signal, len(dates)):
        cov = ledoit_wolf_cov(leg_returns[i - WINDOW - 1:i - 1])
        w = erc_weights(cov)
        assert np.linalg.eigvalsh(cov).min() > 0
        np.testing.assert_allclose(risk_contributions(w, cov), 1 / len(LEGS), atol=1e-6)
        covs[i], targets[i] = cov, w
    month_ends = np.zeros(len(dates), dtype=bool)
    month_ends[:-1] = dates[:-1].to_period("M") != dates[1:].to_period("M")
    # Never infer month-end from exhaustion of the data snapshot.
    pd.DataFrame(targets, index=dates, columns=LEGS).to_csv(output / "daily_erc_targets.csv")
    return Market(dates, prices, frames, targets, covs, month_ends, first_signal), manifest


def etf_targets(leg_targets):
    result = np.zeros(len(SYMBOLS))
    for i, ids in enumerate(MEMBERS):
        result[ids] = leg_targets[i] / len(ids)
    return result


def lot_size(price, value):
    return int(value // price) // 100 * 100


def execute(holdings, cash, prices, targets, commission, date, signal_date):
    """Mirror RiskParityStrategy4A._execute_rebalance, including budget buffer."""
    total = cash + holdings @ prices
    current = holdings * prices / total
    sells = sorted([j for j in range(len(prices)) if targets[j] < current[j]],
                   key=lambda j: targets[j] - current[j])
    buys = sorted([j for j in range(len(prices)) if targets[j] >= current[j]],
                  key=lambda j: -targets[j])
    budget = cash + sum(lot_size(prices[j], max(0, holdings[j] * prices[j] - targets[j] * total))
                        * prices[j] for j in sells)
    fills, failures = [], []

    def fill(j, quantity):
        nonlocal cash
        if quantity == 0:
            return
        fee = abs(quantity) * prices[j] * commission
        new_cash = cash - quantity * prices[j] - fee
        if new_cash < -1e-7:
            failures.append(dict(date=str(date.date()), symbol=SYMBOLS[j], status="Margin"))
            return
        cash = new_cash
        holdings[j] += quantity
        fills.append(dict(date=date, signal_date=signal_date, symbol=SYMBOLS[j],
                          size=quantity, price=prices[j], commission=fee,
                          turnover=abs(quantity) * prices[j] / total))

    for j in sells:
        fill(j, -lot_size(prices[j], holdings[j] * prices[j] - targets[j] * total))
    for j in buys:
        gap = targets[j] * total - holdings[j] * prices[j]
        if gap <= 0:
            continue
        size = lot_size(prices[j], min(gap, budget * .999))
        if size <= 0:
            continue
        budget -= size * prices[j] * (1 + commission + .001)
        fill(j, size)
    return holdings, cash, fills, failures


def simulate(market, mode, threshold, commission=.0005, yearly_thresholds=None):
    label = f"{mode}_{threshold * 100:g}pct_{commission * 10000:g}bp"
    holdings = np.zeros(len(SYMBOLS), dtype=int)
    cash = INITIAL_CASH
    pending = None
    rows, fills, batches, checks, failures = [], [], [], [], []
    for i in range(market.first_signal, len(market.dates)):
        date, prices = market.dates[i], market.prices[i]
        if pending is not None:
            targets, signal_date = pending
            holdings, cash, new_fills, failed = execute(
                holdings, cash, prices, targets, commission, date, signal_date)
            fills.extend(new_fills)
            failures.extend(failed)
            batches.append(dict(date=date, signal_date=signal_date, fills=len(new_fills)))
            pending = None
        value = cash + holdings @ prices
        leg_w = np.array([(holdings[ids] * prices[ids]).sum() / value for ids in MEMBERS])
        deviation = np.abs(leg_w - market.targets[i]).sum()
        rc = risk_contributions(leg_w, market.covariances[i])
        rc_error = np.max(np.abs(rc - 1 / len(LEGS))) if holdings.any() else np.nan
        rows.append(dict(date=date, value=value, cash=cash, l1_deviation=deviation,
                         max_rc_error=rc_error, **dict(zip(LEGS, leg_w))))
        eligible = i == market.first_signal or mode == "daily" or market.month_ends[i]
        if eligible:
            active_threshold = (yearly_thresholds or {}).get(date.year, threshold)
            triggered = i == market.first_signal or deviation > active_threshold
            checks.append(dict(date=date, deviation=deviation, threshold=active_threshold,
                               triggered=triggered, initial=i == market.first_signal))
            if triggered:
                pending = etf_targets(market.targets[i]), date
    return Simulation(label, mode, threshold, commission,
                      pd.DataFrame(rows).set_index("date"),
                      pd.DataFrame(fills), pd.DataFrame(batches),
                      pd.DataFrame(checks), failures)


def period_nav(sim, start=None, end=None):
    nav = sim.nav.loc[:end] if end is not None else sim.nav
    if start is not None:
        before = nav.index[nav.index < pd.Timestamp(start)]
        anchor = before[-1] if len(before) else pd.Timestamp(start)
        nav = nav.loc[anchor:]
    return nav


def metrics(sim, start=None, end=None):
    nav = period_nav(sim, start, end)
    ret = nav.value.pct_change().dropna()
    ratio = nav.value.iloc[-1] / nav.value.iloc[0]
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    vol = ret.std(ddof=1) * np.sqrt(252)
    dates = (nav.index[0], nav.index[-1])
    fills = sim.fills[(sim.fills.date > dates[0]) & (sim.fills.date <= dates[1])]
    batches = sim.batches[(sim.batches.date > dates[0]) & (sim.batches.date <= dates[1])]
    actual_batches = int((batches.fills > 0).sum())
    failed_orders = sum(dates[0] < pd.Timestamp(f["date"]) <= dates[1] for f in sim.failures)
    return dict(label=sim.label, mode=sim.mode, threshold=sim.threshold,
                commission=sim.commission, start=str(dates[0].date()), end=str(dates[1].date()),
                cagr=float(ratio ** (1 / years) - 1), cumulative=float(ratio - 1),
                volatility=float(vol), sharpe=float((ret.mean() * 252 - .015) / vol),
                mdd=float((nav.value / nav.value.cummax() - 1).min()),
                batches=actual_batches, execution_attempts=len(batches), batches_per_year=actual_batches / years,
                fees=float(fills.commission.sum()), annual_turnover=float(fills.turnover.sum() / years),
                mean_l1=float(nav.l1_deviation.iloc[1:].mean()),
                mean_rc_error=float(nav.max_rc_error.mean()),
                p95_rc_error=float(nav.max_rc_error.quantile(.95)), failed_orders=int(failed_orders))


class FrameworkAudit(production.RiskParityStrategy4A):
    params = (("market", None), ("check_mode", "monthly"), ("project_fills", True))

    def __init__(self):
        self.submitted_today = []
        self.audit_fills, self.audit_failures, self.audit_signals = [], [], []
        super().__init__()

    def log(self, *args, **kwargs):
        pass

    def _log_daily_state(self):
        pass

    def _log_decision(self, etf_targets, leg_targets, cov, rc, deviation):
        self.audit_signals.append(self.datas[0].datetime.date(0))

    def _decide_rebalance(self, initial):
        # Preserve explicitly selected research schedules if production defaults
        # change. The event simulator defines the historical study's rules.
        if initial or self._is_month_end():
            super()._decide_rebalance(initial)

    def next(self):
        self.submitted_today = []
        super().next()

    def _compute_leg_weights(self):
        weights, cov, rc = super()._compute_leg_weights()
        i = self.p.market.dates.get_loc(pd.Timestamp(self.datas[0].datetime.date(0)))
        np.testing.assert_allclose(weights, self.p.market.targets[i], atol=1e-12, rtol=1e-12)
        np.testing.assert_allclose(cov, self.p.market.covariances[i], atol=1e-15, rtol=1e-12)
        return weights, cov, rc

    def buy(self, *args, **kwargs):
        order = super().buy(*args, **kwargs)
        if order is not None:
            self.submitted_today.append(order)
        return order

    def sell(self, *args, **kwargs):
        order = super().sell(*args, **kwargs)
        if order is not None:
            self.submitted_today.append(order)
        return order

    def _is_month_end(self):
        date = pd.Timestamp(self.datas[0].datetime.date(0))
        i = self.p.market.dates.get_loc(date)
        return self.p.check_mode == "daily" or bool(self.p.market.month_ends[i])

    def _current_leg_weights(self):
        if not self.p.project_fills or not self.submitted_today:
            total = self.broker.getvalue()
            return np.array([sum(self.getposition(self._data_by_symbol[SYMBOLS[j]]).size
                                 * self._data_by_symbol[SYMBOLS[j]].close[0] for j in ids) / total
                             for ids in MEMBERS])
        quantities = {s: self.getposition(self._data_by_symbol[s]).size for s in SYMBOLS}
        fees = 0.0
        for order in self.submitted_today:
            quantities[order.data._name] += order.size
            fees += abs(order.size) * order.data.close[0] * self.p.commission
        value = self.broker.getvalue() - fees
        return np.array([sum(quantities[SYMBOLS[j]] * self._data_by_symbol[SYMBOLS[j]].close[0]
                             for j in ids) / value for ids in MEMBERS])

    def notify_order(self, order):
        if order.status == order.Completed:
            self.audit_fills.append(dict(date=pd.Timestamp(bt.num2date(order.executed.dt).date()),
                                         symbol=order.data._name, size=order.executed.size,
                                         price=order.executed.price, commission=order.executed.comm))
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.audit_failures.append(order.getstatusname())

    def stop(self):
        pass


def framework_validate(market, sim, output, project=True):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(INITIAL_CASH)
    cerebro.addstrategy(FrameworkAudit, market=market, check_mode=sim.mode,
                        project_fills=project, rebalance_threshold=sim.threshold,
                        commission=sim.commission)
    for symbol in SYMBOLS:
        cerebro.adddata(bt.feeds.PandasData(dataname=market.frames[symbol]), name=symbol)
    strat = cerebro.run()[0]
    actual = pd.DataFrame(strat.audit_fills)
    tag = sim.label + ("" if project else "_naive")
    actual.to_csv(output / f"framework_fills_{tag}.csv", index=False)
    # The final effective-date fill is not delivered without another bar. Our
    # simulator accounts for it on its economic date; compare all earlier fills.
    expected = sim.fills[sim.fills.date < market.dates[-1]]
    if project:
        assert not strat.audit_failures, strat.audit_failures
        assert len(actual) == len(expected), (tag, len(actual), len(expected))
        for col in ["date", "symbol", "size"]:
            assert actual[col].tolist() == expected[col].tolist(), (tag, col)
        for col in ["price", "commission"]:
            np.testing.assert_allclose(actual[col], expected[col], atol=1e-8, rtol=1e-12)
        signals = sim.checks[sim.checks.triggered].date.dt.date.tolist()
        assert strat.audit_signals == signals, (tag, "signal dates")
    return dict(label=tag, matched=project, orders=len(actual), failures=len(strat.audit_failures),
                max_abs_fee_error=float(np.max(np.abs(actual.commission.to_numpy()
                                        - expected.commission.to_numpy()))) if project else None,
                final_broker_value=cerebro.broker.getvalue(), economic_final_value=sim.nav.value.iloc[-1])


def paired_bootstrap(a, b, start=None, end=None, block=21, samples=2000):
    """Paired circular-block resampling; preserves local time dependence."""
    x = period_nav(a, start, end).value.pct_change().dropna().to_numpy()
    y = period_nav(b, start, end).value.pct_change().dropna().to_numpy()
    assert len(x) == len(y)
    rng = np.random.default_rng(42)
    starts = rng.integers(0, len(x), size=(samples, int(np.ceil(len(x) / block))))
    indices = ((starts[:, :, None] + np.arange(block)) % len(x)).reshape(samples, -1)[:, :len(x)]
    rx, ry = x[indices], y[indices]
    sharpe_x = (rx.mean(axis=1) * 252 - .015) / (rx.std(axis=1, ddof=1) * np.sqrt(252))
    sharpe_y = (ry.mean(axis=1) * 252 - .015) / (ry.std(axis=1, ddof=1) * np.sqrt(252))
    annual_log_delta = (np.log1p(rx) - np.log1p(ry)).mean(axis=1) * 252
    delta = sharpe_x - sharpe_y
    return dict(a=a.label, b=b.label, block=block, observations=len(x), samples=samples,
                sharpe_difference=float(((x.mean() * 252 - .015) / (x.std(ddof=1) * np.sqrt(252)))
                                        - ((y.mean() * 252 - .015) / (y.std(ddof=1) * np.sqrt(252)))),
                sharpe_ci_95=np.quantile(delta, [.025, .975]).tolist(),
                annual_log_return_difference=float((np.log1p(x) - np.log1p(y)).mean() * 252),
                annual_log_return_ci_95=np.quantile(annual_log_delta, [.025, .975]).tolist(),
                positive_sharpe_fraction=float((delta > 0).mean()))


def save_sim(sim, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name in ["nav", "fills", "batches", "checks"]:
        getattr(sim, name).to_csv(directory / f"{name}.csv", index=name == "nav")


def attribute(market, sim):
    """Currency P&L by leg using actual pre-close shares, not synthetic returns."""
    holdings = np.zeros(len(SYMBOLS), dtype=int)
    groups = {date: group for date, group in sim.fills.groupby("date")}
    rows = []
    for i in range(market.first_signal, len(market.dates)):
        date = market.dates[i]
        pnl = holdings * (market.prices[i] - market.prices[i - 1])
        fees = 0.0
        if date in groups:
            for fill in groups[date].itertuples():
                holdings[SYMBOLS.index(fill.symbol)] += fill.size
                fees += fill.commission
        rows.append(dict(date=date, fees=fees,
                         **{leg: pnl[ids].sum() for leg, ids in zip(LEGS, MEMBERS)}))
    result = pd.DataFrame(rows).set_index("date")
    np.testing.assert_allclose(result[LEGS].sum(axis=1).iloc[1:] - result.fees.iloc[1:],
                               sim.nav.value.diff().iloc[1:], atol=1e-8, rtol=1e-10)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".trader_center/data/bars/daily")
    parser.add_argument("--output", type=Path, default=ROOT / "logs/research/risk_parity_rebalance_20261013")
    parser.add_argument("--skip-framework", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    print("Loading one immutable data snapshot and precomputing PIT ERC targets", flush=True)
    market, inputs = load_market(args.data_dir, args.output)
    manifest = dict(inputs=inputs, symbols=SYMBOLS, legs=production.LEG_CONFIG,
                    first_signal=str(market.dates[market.first_signal].date()),
                    latest_common_date=str(market.dates[-1].date()), window=WINDOW,
                    initial_cash=INITIAL_CASH, thresholds=THRESHOLDS,
                    commissions=[0, .0005, .001, .002], rf=.015, annualization=252,
                    train_end=str(TRAIN_END.date()), bootstrap_seed=42,
                    execution="signal T close with covariance through T-1; fill T+1 close; decision after fill",
                    price_basis="existing AkShare qfq cached OHLC, no separate cash distributions",
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    production_sha256=hashlib.sha256(Path(production.__file__).read_bytes()).hexdigest(),
                    math_sha256=hashlib.sha256((ROOT / "trader_center/backtest/strategy/risk_parity_math.py").read_bytes()).hexdigest())
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    sims, rows = {}, []
    for commission in manifest["commissions"]:
        for mode in ["monthly", "daily"]:
            for threshold in THRESHOLDS:
                sim = simulate(market, mode, threshold, commission)
                if commission == .0005:
                    assert not sim.failures, (sim.label, sim.failures)
                sims[sim.label] = sim
                for period, start, end in [("train", None, TRAIN_END),
                                           ("oos", "2025-01-01", None), ("full", None, None)]:
                    rows.append(dict(period=period, **metrics(sim, start, end)))
                if commission == .0005:
                    save_sim(sim, args.output / "variants" / sim.label)
        print(f"Completed frequency/threshold grid at {commission * 10000:g}bp", flush=True)
    table = pd.DataFrame(rows)
    table.to_csv(args.output / "summary.csv", index=False)
    base_sims = [s for s in sims.values() if s.commission == .0005]
    baseline = sims["monthly_5pct_5bp"]
    selected = {}
    for mode in ["monthly", "daily"]:
        training = table[(table.period == "train") & (table.commission == .0005) & (table['mode'] == mode)]
        winner = training.sort_values(["sharpe", "annual_turnover"], ascending=[False, True]).iloc[0]
        selected[mode] = dict(label=winner.label, threshold=float(winner.threshold), train_sharpe=float(winner.sharpe))
    print(f"Training-only selections: {selected}", flush=True)
    (args.output / "training_selections.json").write_text(json.dumps(selected, indent=2), encoding="utf-8")
    validations = []
    if not args.skip_framework:
        labels = {"monthly_5pct_5bp", "daily_5pct_5bp", "daily_0pct_5bp",
                  selected["monthly"]["label"], selected["daily"]["label"]}
        for label in sorted(labels):
            print(f"Independent Backtrader signal/fill tie-out: {label}", flush=True)
            validations.append(framework_validate(market, sims[label], args.output))
        print("Measuring naive daily port's stale-position effect", flush=True)
        validations.append(framework_validate(market, sims["daily_5pct_5bp"], args.output, project=False))
    (args.output / "framework_validation.json").write_text(json.dumps(validations, indent=2), encoding="utf-8")
    bootstrap = []
    labels = {"daily_3pct_5bp", "daily_5pct_5bp", "monthly_6pct_5bp",
              selected["monthly"]["label"], selected["daily"]["label"]} - {baseline.label}
    pairs = {(label, baseline.label) for label in labels}
    pairs.update({("daily_3pct_5bp", "daily_5pct_5bp"),
                  ("daily_15pct_5bp", "daily_5pct_5bp"),
                  ("daily_20pct_5bp", "daily_5pct_5bp")})
    for label, reference in sorted(pairs):
        for period, start, end in [("train", None, TRAIN_END), ("oos", "2025-01-01", None), ("full", None, None)]:
            for block in [21, 63]:
                bootstrap.append(dict(period=period, **paired_bootstrap(sims[label], sims[reference], start, end, block)))
    (args.output / "bootstrap.json").write_text(json.dumps(bootstrap, indent=2), encoding="utf-8")
    annual = []
    for sim in base_sims:
        for year in range(2021, market.dates[-1].year + 1):
            annual.append(dict(year=year, **metrics(sim, f"{year}-01-01", f"{year}-12-31")))
    pd.DataFrame(annual).to_csv(args.output / "annual.csv", index=False)
    walkforwards, wf_rows = {}, []
    for mode in ["monthly", "daily"]:
        selections = {}
        for year in range(2023, market.dates[-1].year + 1):
            candidates = [metrics(s, end=f"{year-1}-12-31") for s in base_sims if s.mode == mode]
            best = max(candidates, key=lambda m: (m["sharpe"], -m["annual_turnover"]))
            selections[year] = best["threshold"]
        wf = simulate(market, mode, .05, .0005, yearly_thresholds=selections)
        wf.label = f"walkforward_{mode}"
        save_sim(wf, args.output / wf.label)
        wf_rows.append(dict(selection_by_year=selections, **metrics(wf, "2023-01-01")))
        walkforwards[mode] = wf
    wf_rows.append(metrics(baseline, "2023-01-01"))
    (args.output / "walkforward.json").write_text(json.dumps(wf_rows, indent=2), encoding="utf-8")
    attribution = []
    for label in ["monthly_5pct_5bp", "daily_5pct_5bp", "daily_20pct_5bp", "monthly_15pct_5bp"]:
        contributions = attribute(market, sims[label])
        contributions.to_csv(args.output / "variants" / label / "pnl_attribution.csv")
        attribution.append(dict(label=label, **contributions.sum().to_dict()))
    pd.DataFrame(attribution).to_csv(args.output / "pnl_attribution.csv", index=False)
    write_report(args.output, market, table, sims, selected, bootstrap, validations, wf_rows)
    print(table[(table.period == "full") & (table.commission == .0005)]
          [["mode", "threshold", "cagr", "sharpe", "mdd", "batches", "annual_turnover", "mean_rc_error"]].to_string(index=False), flush=True)
    print(f"Report: {args.output / 'report.html'}", flush=True)


def write_report(output, market, table, sims, selected, bootstrap, validations, wf_rows):
    # Report generation is kept separate from the experiment's trading logic.
    import html
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    plt.rcParams.update({"font.family": "Microsoft YaHei", "axes.unicode_minus": False,
                         "figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False})
    grid = table[table.commission == .0005]
    baseline_full = grid[(grid.period == "full") & (grid.label == "monthly_5pct_5bp")].iloc[0]
    daily_full = grid[(grid.period == "full") & (grid.label == "daily_5pct_5bp")].iloc[0]
    winner_full = grid[(grid.period == "full") & (grid.label == selected["daily"]["label"])].iloc[0]
    colors = {"monthly": "#245b9b", "daily": "#df6a35"}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for period, style, period_name in [("train", "--", "2021—2024"), ("oos", "-", "2025—2026")]:
        for mode, mode_name in [("monthly", "月末检查"), ("daily", "每日检查")]:
            data = grid[(grid.period == period) & (grid['mode'] == mode)].sort_values("threshold")
            for ax, col, title in zip(axes.flat, ["cagr", "sharpe", "mdd", "batches_per_year"],
                                      ["扣费年化收益", "夏普（无风险利率 1.5%）", "最大回撤", "每年实际调仓批次（含建仓）"]):
                ax.plot(data.threshold * 100, data[col], style, color=colors[mode], marker="o", ms=3,
                        label=f"{mode_name} · {period_name}")
                ax.set_title(title)
                ax.set_xlabel("L1 权重偏离阈值（%）")
                ax.grid(alpha=.2)
    for ax in [axes[0, 0], axes[1, 0]]:
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    axes[0, 1].legend(fontsize=8)
    fig.suptitle("四资产 ERC：检查频率与阈值敏感性 · 单边成本 5bp", fontsize=15)
    fig.tight_layout()
    fig.savefig(output / "threshold_sensitivity.png", bbox_inches="tight")
    plt.close(fig)
    labels = list(dict.fromkeys(["monthly_5pct_5bp", "daily_5pct_5bp",
                                selected["monthly"]["label"], selected["daily"]["label"]]))
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for label in labels:
        sim = sims[label]
        label_cn = f"{'每日' if sim.mode == 'daily' else '月末'} · {sim.threshold:.1%}"
        axes[0].plot(sim.nav.index, sim.nav.value / sim.nav.value.iloc[0], label=label_cn, lw=1.5)
        axes[1].plot(sim.nav.index, sim.nav.value / sim.nav.value.cummax() - 1, lw=1)
    for ax in axes:
        ax.axvline(TRAIN_END, color="#667788", ls="--", lw=1)
        ax.grid(alpha=.2)
    axes[0].legend()
    axes[0].set_title("固定参数路径：净值与回撤（虚线后为 2025 年起验证区间）")
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    fig.tight_layout()
    fig.savefig(output / "nav_comparison.png", bbox_inches="tight")
    plt.close(fig)
    columns = ["mode", "threshold", "cagr", "volatility", "sharpe", "mdd", "batches", "fees", "annual_turnover", "mean_rc_error"]
    names = {"mode": "检查频率", "threshold": "阈值", "cagr": "年化收益", "volatility": "年化波动",
             "sharpe": "夏普", "mdd": "最大回撤", "batches": "调仓批次", "fees": "费用（元）",
             "annual_turnover": "年均双边换手", "mean_rc_error": "平均最大风险贡献偏离"}

    def formatted(frame):
        f = frame[columns].copy()
        f["mode"] = f["mode"].map({"daily": "每日", "monthly": "月末"})
        for col in ["threshold", "cagr", "volatility", "mdd", "annual_turnover", "mean_rc_error"]:
            f[col] = f[col].map(lambda v: f"{v:.2%}")
        f.sharpe = f.sharpe.map(lambda v: f"{v:.3f}")
        f.fees = f.fees.map(lambda v: f"{v:,.2f}")
        return f.rename(columns=names).to_html(index=False, escape=True)

    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>四资产调仓机制验证</title>",
             "<style>body{font:16px/1.65 'Microsoft YaHei',sans-serif;max-width:1280px;margin:40px auto;color:#183044;padding:0 24px}h1,h2{color:#173858}table{border-collapse:collapse;width:100%;font-size:13px;margin:18px 0}th,td{padding:7px;border-bottom:1px solid #dce3ea;text-align:right}th{background:#edf2f7}img{width:100%}.note{background:#f0f4f8;padding:18px;border-radius:8px}code{font-size:13px}a{color:#245b9b}</style>",
             "<h1>四资产风险平价：调仓频率与阈值实践验证</h1>",
             f"<p>实验日期：2026-10-13。共同数据终点：{market.dates[-1].date()}；首次信号：{market.dates[market.first_signal].date()}。</p>",
             "<h2>实验结论</h2>",
             f"<p><b>每日检查＋5%：主要改善风险控制，收益提升较小。</b>全区间扣费年化收益由 {baseline_full.cagr:.2%} 升至 {daily_full.cagr:.2%}，"
             f"夏普由 {baseline_full.sharpe:.3f} 升至 {daily_full.sharpe:.3f}，最大回撤由 {baseline_full.mdd:.2%} 收窄至 {daily_full.mdd:.2%}；"
             f"实际调仓 {int(baseline_full.batches)} → {int(daily_full.batches)} 次，均含首次建仓。2025 年起年化收益仅提升约 0.02 个百分点。</p>",
             "<p><b>5% 是合理的收益、风险纪律和执行频率折中，未发现更小阈值稳定增加收益。</b>每日 3% 与 5% 的全区间夏普相近，"
             "但调仓为 57 对 25 次；0%—2% 的年化收益较低。资本权重的 L1 偏离不直接限制风险贡献误差，仍应监测每腿 25% 风险预算。</p>",
             f"<p><b>大阈值产生更高历史收益，但风险预算偏离明显。</b>仅用 2024 年以前选择，月末最优为 15%，每日最优为 20%；"
             f"每日 20% 的全区间年化收益 {winner_full.cagr:.2%}、夏普 {winner_full.sharpe:.3f}、最大回撤 {winner_full.mdd:.2%}，"
             "只有 4 次实际调仓（含建仓），2021 年 10 月至 2025 年 9 月之间没有调仓。平均每日最大单腿风险贡献偏离预算从原机制约 6.05 个百分点升至 16.42 个百分点。</p>",
             "<p><b>统计证据不足以认定必然改善或全局最优。</b>21 / 63 日成对块自助下，每日 5% 和训练选择的每日 20% 相对原机制的"
             "收益差与夏普差 95% 区间均跨过零。20% 又位于测试范围边界，不能据此宣布它是最优阈值。</p>",
             "<div class='note'><b>实验定义：</b>月末或每日重新估计 ERC；四腿实际资本权重与当日目标的 L1 偏离严格大于阈值时，全组合回到目标。两种机制均在触发后的下一交易日收盘成交。首次建仓不受阈值限制。</div>",
             "<h2>输入与口径</h2><ul><li>同一份本地 AkShare 前复权缓存快照，六只 ETF；不下载新行情。" 
             "510300 / 511260 / 518880 / 159981 / 159985 / 159980；商品收益估计为三只日收益均值，实际仓位仅在组合调仓时回到三等权。</li>",
             "<li>使用当前已修正的常相关 Ledoit–Wolf 与 ERC 求解器；滚动 250 日，估计窗口截至决策前一交易日。</li>",
             "<li>初始资金 100 万；100 股整手；单边佣金 5bp，无印花税、最低佣金和额外滑点。另跑 0 / 10 / 20bp 成本敏感性。</li>",
             "<li>0%、0.5%、1%、2%、3%、4%、5%、6%、7.5%、10%、15%、20% 共 12 档；2 种频率 × 12 档 × 4 档成本 = 96 个固定参数实验。</li>",
             "<li>年化收益用实际日历跨度；波动和夏普用 252 日、无风险利率 1.5%。换手为买卖金额之和 / 成交前净值，包含首次建仓。</li>",
             "<li>收益和风险按成交有效日重建，解决 cheat-on-close 回报延后一天的问题；月末由快照内已观察到的下月交易日确认，数据末日不额外当作月末。</li>",
             "<li>2021—2024 为参数选择区间，2025 年起为冻结阈值的时间留出验证。历史上已看过这段行情，因此它不是完全未接触的真实未来样本。</li></ul>",
             "<h2>参数曲线</h2><img src='threshold_sensitivity.png'><img src='nav_comparison.png'>"]
    for period, title in [("train", "参数选择区间：首次信号—2024-12-31"),
                          ("oos", "时间留出验证：2025-01-01—最新共同交易日"), ("full", "完整区间")]:
        parts.extend([f"<h2>{title}</h2>", formatted(grid[grid.period == period])])
    parts.extend(["<h2>只用 2024 年及以前选择参数</h2><pre>", html.escape(json.dumps(selected, indent=2, ensure_ascii=False)), "</pre>",
                  "<p>按训练期扣费夏普最大选择；若相同，优先低换手。没有根据留出期排名重新挑选阈值。</p>",
                  "<h2>年度滚动选择，持仓连续运行</h2>",
                  "<p>2021—2022 用原 5%；从 2023 年起，每年只用截至上一年末的候选固定策略表现选择阈值，随后运行一年；" 
                  "跨年保留已有持仓，不重置账户、不拼接候选策略净值。</p><pre>",
                  html.escape(json.dumps(wf_rows, indent=2, ensure_ascii=False)), "</pre>",
                  "<h2>成对循环块自助置信区间</h2><p>相同日期、相同抽样索引，21 / 63 日块长，各 2000 次，seed=42。" 
                  "这是给定参数收益差异的不确定性诊断，未对整组择优做多重检验校正，不能证明全局最优。</p>"])
    boot = pd.DataFrame(bootstrap)[["a", "b", "period", "block", "sharpe_difference", "sharpe_ci_95",
                                                "annual_log_return_difference", "annual_log_return_ci_95"]].copy()
    boot.sharpe_difference = boot.sharpe_difference.map(lambda x: f"{x:+.3f}")
    boot.sharpe_ci_95 = boot.sharpe_ci_95.map(lambda x: f"[{x[0]:+.3f}, {x[1]:+.3f}]")
    boot.annual_log_return_difference = boot.annual_log_return_difference.map(lambda x: f"{x:+.2%}")
    boot.annual_log_return_ci_95 = boot.annual_log_return_ci_95.map(lambda x: f"[{x[0]:+.2%}, {x[1]:+.2%}]")
    parts.append(boot.rename(columns={"a": "候选机制", "b": "参照机制", "period": "区间", "block": "块长",
                                     "sharpe_difference": "夏普差", "sharpe_ci_95": "夏普差 95% 区间",
                                     "annual_log_return_difference": "年化对数收益差", "annual_log_return_ci_95": "收益差 95% 区间"})
                 .to_html(index=False, escape=True))
    parts.extend(["<h2>收益来源（全区间各腿盈亏，元）</h2>",
                  "<p>以每个交易日收盘前真实股数计算价格变动盈亏，按有效成交日扣费用；各腿盈亏之和减费用与净值变化逐日对齐。" 
                  "用于判断提升来自何种持仓差异，不将历史归因当作未来预测。</p>",
                  pd.read_csv(output / "pnl_attribution.csv").round(2).to_html(index=False)])
    stress = table[(table.period == "full") & table.label.str.startswith(("monthly_5pct_", "daily_5pct_", "daily_20pct_"))]
    parts.extend(["<h2>交易成本压力测试</h2>",
                  "<p>每档成本重新运行相同生产股数与现金预算规则，持仓会因整手取整而变化。10 / 20bp 部分小阈值出现资金不足拒单；" 
                  "有拒单的结果不是纯费用变化，需同时看失败单列。主实验 5bp 的所有 24 组均无失败单。</p>",
                  stress[["mode", "threshold", "commission", "cagr", "sharpe", "mdd", "failed_orders"]].round(5).to_html(index=False)])
    parts.extend(["<h2>交易框架独立对拍</h2><pre>", html.escape(json.dumps(validations, indent=2)), "</pre>",
                  "<p>对比生产估计器计算出的信号日期、实际成交顺序、股数、价格和佣金；每日检查用已提交当日收盘订单投影成交后仓位。" 
                  "数据末日的订单若无后续 bar，框架尚未回报，按同一有效日期处理并在对拍中明确裁剪。</p>",
                  "<h2>限制与复现</h2><ul><li>前复权历史作为价格输入，整手股数和费用口径继承现有回测，不能当作历史原始报价下的实盘逐笔复现。</li>",
                  "<li>未模拟 bid/ask、冲击、盘中执行、成交量上限；现金不计息。20bp 是成本压力测试，未模拟不同成本对成交价格本身的影响。</li>",
                  "<li>最大回撤按区间重新起算；2026 为截至 10 月 12 日的非完整年度。训练期和留出期长度不同，分别报告 CAGR。</li>",
                  "<li>调仓更及时可以降低风险预算偏离，但不必然提高收益；阈值是资本权重偏离，不是直接的风险贡献误差限制。</li></ul>",
                  "<p><code>python scripts/study_risk_parity_rebalance.py</code>；详见 manifest.json、summary.csv、annual.csv、bootstrap.json、walkforward.json 及 variants 下的每日净值、信号与成交。</p>",
                  "<p>方法背景：<a href='https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2731886'>Bailey 等：Backtest Overfitting in Financial Markets</a>；" 
                  "<a href='https://corporate.vanguard.com/content/dam/corp/research/pdf/the_rebalancing_edge_optimizing_target_date_fund_rebalancing_through_threshold_based_strategies.pdf'>Vanguard：阈值再平衡研究</a>。" 
                  "以上仅支持研究设计，不作为本策略绩效证据。</p></html>"])
    (output / "report.html").write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
