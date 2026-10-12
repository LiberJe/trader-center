"""Economic timing, frequency isolation, fees, and prefix independence."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

path = Path(__file__).resolve().parents[2] / "scripts/study_risk_parity_rebalance.py"
spec = importlib.util.spec_from_file_location("rebalance_study", path)
study = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = study
spec.loader.exec_module(study)


def market(prices):
    dates = pd.bdate_range("2025-01-06", periods=len(prices))
    return study.Market(dates, np.asarray(prices, dtype=float), {},
                        np.full((len(dates), 4), .25),
                        np.tile(np.eye(4) * .0001, (len(dates), 1, 1)),
                        np.zeros(len(dates), dtype=bool), 0)


def test_initial_signal_fills_next_close_and_earns_only_later_returns():
    prices = np.array([[10] * 6, [20] * 6, [22] * 6], dtype=float)
    data = market(prices)
    result = study.simulate(data, "monthly", .05, commission=0)
    assert result.nav.value.iloc[0] == study.INITIAL_CASH
    assert result.nav.value.iloc[1] == study.INITIAL_CASH
    assert result.batches.date.tolist() == [data.dates[1]]
    assert set(result.fills.price) == {20}
    assert set(result.fills.signal_date) == {data.dates[0]}
    invested = sum(result.fills['size'] * result.fills.price)
    assert np.isclose(result.nav.value.iloc[2], study.INITIAL_CASH + invested * .1)


def test_daily_threshold_reacts_within_month_monthly_does_not():
    prices = np.full((5, 6), 10.0)
    prices[2:, 0] = 15
    data = market(prices)
    daily = study.simulate(data, "daily", .05, commission=0)
    monthly = study.simulate(data, "monthly", .05, commission=0)
    assert daily.batches.date.tolist() == [data.dates[1], data.dates[3]]
    assert monthly.batches.date.tolist() == [data.dates[1]]
    # Checking after the prior target's fill avoids duplicate stale-position
    # signals on the initial execution day and on the shock's execution day.
    assert daily.checks[daily.checks.triggered].date.tolist() == [data.dates[0], data.dates[2]]


def test_fees_reduce_nav_on_effective_fill_date_and_shares_are_lots():
    data = market(np.full((3, 6), 10.0))
    result = study.simulate(data, "daily", .05, commission=.0005)
    assert (result.fills['size'] % 100 == 0).all()
    assert np.isclose(result.nav.value.iloc[1], study.INITIAL_CASH - result.fills.commission.sum())
    assert (result.nav.cash >= 0).all()


def test_no_future_data_changes_earlier_decisions_or_nav():
    prices = np.full((8, 6), 10.0)
    prices[2:5, 0] = 15
    prices[5:, 1] = 30
    full = study.simulate(market(prices), "daily", .05, commission=.0005)
    short = study.simulate(market(prices[:5]), "daily", .05, commission=.0005)
    pd.testing.assert_frame_equal(full.nav.iloc[:5], short.nav)
    pd.testing.assert_frame_equal(full.checks.iloc[:5], short.checks)
