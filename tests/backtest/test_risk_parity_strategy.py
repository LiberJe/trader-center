"""Risk budgets are assigned per configured asset leg, without a stock override."""

import backtrader as bt
import numpy as np
import pandas as pd
import pytest

from trader_center.backtest.strategy import risk_parity as strategy_module


@pytest.mark.parametrize("n_legs", [2, 3, 4, 5])
def test_strategy_uses_equal_risk_for_configured_legs(monkeypatch, n_legs):
    legs = {
        "equity" if i == 0 else f"asset_{i}": {
            "name": f"Asset {i}",
            "members": (f"TEST{i}",),
        }
        for i in range(n_legs)
    }
    monkeypatch.setattr(strategy_module, "LEG_CONFIG", legs)
    monkeypatch.setattr(strategy_module, "LEG_NAMES", list(legs))

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
    cerebro.addstrategy(ObservedStrategy, cov_window=20)
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
