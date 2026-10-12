"""Risk budgets are assigned per configured asset leg, without a stock override."""

import backtrader as bt
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from trader_center.backtest.strategy import risk_parity as strategy_module


@pytest.mark.parametrize("n_legs", [2, 3, 4, 5])
def test_strategy_uses_equal_risk_for_configured_legs(n_legs):
    legs = {
        "equity" if i == 0 else f"asset_{i}": {
            "name": f"Asset {i}",
            "members": (f"TEST{i}",),
        }
        for i in range(n_legs)
    }
    assets = {cfg["members"][0]: {"name": cfg["name"], "leg": key, "leg_name": cfg["name"]}
              for key, cfg in legs.items()}

    class ObservedStrategy(strategy_module.RiskParityStrategy4A):
        def __init__(self):
            super().__init__()
            self.observed_risk_contributions = []

        def _compute_leg_weights(self):
            weights, cov, rc = super()._compute_leg_weights()
            self.observed_risk_contributions.append(rc.copy())
            return weights, cov, rc

    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2024-01-02", periods=40)
    returns = rng.standard_normal((len(dates), n_legs)) * np.linspace(
        0.001, 0.02, n_legs
    )
    prices = 10 * np.exp(np.cumsum(returns, axis=0))
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(1_000_000)
    cerebro.addstrategy(ObservedStrategy, cov_window=20, asset_config=assets)
    for i, leg in enumerate(legs.values()):
        frame = pd.DataFrame(
            {column: prices[:, i] for column in ["open", "high", "low", "close"]},
            index=dates,
        )
        frame["volume"] = 1_000_000
        cerebro.adddata(bt.feeds.PandasData(dataname=frame), name=leg["members"][0])

    strategy = cerebro.run()[0]
    assert strategy.observed_risk_contributions
    for rc in strategy.observed_risk_contributions:
        np.testing.assert_allclose(rc, 1 / n_legs, atol=1e-6)
        # In two/three-leg portfolios, the equity leg must also receive 1/N.
        if n_legs < 4:
            assert rc[0] > 0.30


def run_daily_scenario(shock=False, periods=9, preload=True, commission=.0005):
    """Hold ERC targets constant to isolate execution timing and daily drift."""
    symbols = [s for leg in strategy_module.LEG_CONFIG.values() for s in leg["members"]]
    dates = pd.bdate_range("2025-01-06", periods=periods)

    class FixedTargetStrategy(strategy_module.RiskParityStrategy4A):
        def __init__(self):
            super().__init__()
            self.checked_dates, self.fills, self.failures = [], [], []
            self.projected, self.confirmed = {}, {}

        def _compute_leg_weights(self):
            weights = np.full(4, .25)
            return weights, np.eye(4), weights.copy()

        def _decide_rebalance(self, initial):
            if not initial:
                self.checked_dates.append(self.datas[0].datetime.date(0))
            super()._decide_rebalance(initial)

        def _execute_rebalance(self, targets):
            super()._execute_rebalance(targets)
            self.projected[self.datas[0].datetime.date(0)] = self._current_leg_weights().copy()

        def next(self):
            super().next()
            total = self.broker.getvalue()
            self.confirmed[self.datas[0].datetime.date(0)] = np.array([
                sum(self.getposition(self._data_by_symbol[s]).size * self._data_by_symbol[s].close[0]
                    for s in leg["members"]) / total
                for leg in strategy_module.LEG_CONFIG.values()
            ])

        def notify_order(self, order):
            if order.status == order.Completed:
                self.fills.append(bt.num2date(order.executed.dt).date())
            elif order.status in [order.Margin, order.Rejected, order.Canceled]:
                self.failures.append(order.getstatusname())
            super().notify_order(order)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(1_000_000)
    cerebro.addstrategy(FixedTargetStrategy, cov_window=2, commission=commission)
    for i, symbol in enumerate(symbols):
        prices = np.full(periods, 10.0)
        if shock and i == 0:
            prices[5:] = 15
        frame = pd.DataFrame({c: prices for c in ["open", "high", "low", "close"]}, index=dates)
        frame["volume"] = 1_000_000
        cerebro.adddata(bt.feeds.PandasData(dataname=frame), name=symbol)
    # Constant prices deliberately isolate timing; shrinkage is only log metadata
    # here, while the real estimator is exercised by the math and snapshot tests.
    with patch.object(strategy_module, "shrinkage_intensity", return_value=0):
        return cerebro.run(preload=preload, runonce=preload)[0], dates


@pytest.mark.parametrize("preload", [True, False])
def test_daily_drift_triggers_mid_month_without_duplicate_execution_day_signal(preload):
    strategy, dates = run_daily_scenario(shock=True, preload=preload)
    signal_dates = sorted({signal.datetime.date() for signal in strategy.trade_logger.signals})
    assert signal_dates == [dates[3].date(), dates[5].date()]
    assert strategy.checked_dates == [date.date() for date in dates[4:]]
    assert sorted(set(strategy.fills)) == [dates[4].date(), dates[6].date()]
    assert strategy.rebalance_count == 2
    assert not strategy.failures
    assert strategy.p.rebalance_threshold == .05


def test_below_threshold_is_checked_daily_without_new_trades():
    strategy, dates = run_daily_scenario()
    assert strategy.checked_dates == [date.date() for date in dates[4:]]
    assert len({signal.datetime.date() for signal in strategy.trade_logger.signals}) == 1
    assert strategy.rebalance_count == 1
    # The projected weights include the fee in NAV and expire after one bar.
    np.testing.assert_allclose(strategy.projected[dates[4].date()],
                               strategy.confirmed[dates[5].date()], atol=1e-12)


@pytest.mark.parametrize("preload", [True, False])
def test_latest_mid_month_bar_can_produce_next_session_signal(preload):
    strategy, dates = run_daily_scenario(shock=True, periods=6, preload=preload)
    assert strategy._pending_targets is not None
    assert strategy.trade_logger.signals[-1].datetime.date() == dates[-1].date()
    assert sorted(set(strategy.fills)) == [dates[4].date()]


def test_projection_matches_confirmed_positions_with_large_commissions():
    strategy, dates = run_daily_scenario(shock=True, commission=.1)
    assert strategy.failures and set(strategy.failures) == {"Margin"}
    for i, date in enumerate(dates[:-1]):
        if date.date() in strategy.projected and i != 4:
            np.testing.assert_allclose(strategy.projected[date.date()],
                                       strategy.confirmed[dates[i + 1].date()], atol=1e-12)
