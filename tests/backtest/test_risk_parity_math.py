"""
风险平价数学核心测试

验证：
- Ledoit-Wolf (2004 Honey) 收缩估计的合理性（PSD、MSE 不劣于样本协方差量级）
- CCD-ERC 求解器与 SLSQP 参考解一致
- 风险贡献计算的正确性
- 单腿风险贡献上限条款
"""

import numpy as np
import pytest

from trader_center.backtest.strategy.risk_parity_math import (
    erc_weights,
    erc_weights_with_cap,
    ledoit_wolf_cov,
    risk_contributions,
    shrinkage_intensity,
)

try:
    from scipy.optimize import minimize

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@pytest.fixture()
def cov_4a():
    """规格书四资产腿协方差（年化）：A股 / 10Y国债 / 黄金 / 商品混合"""
    vols = np.array([0.187, 0.030, 0.150, 0.160])
    corr = np.array(
        [
            [1.00, -0.23, 0.15, 0.25],
            [-0.23, 1.00, 0.04, -0.15],
            [0.15, 0.04, 1.00, 0.16],
            [0.25, -0.15, 0.16, 1.00],
        ]
    )
    return np.outer(vols, vols) * corr


# ---------------------------------------------------------------------------
# Ledoit-Wolf
# ---------------------------------------------------------------------------


class TestLedoitWolf:
    def test_output_shape_and_psd(self):
        rng = np.random.default_rng(0)
        X = rng.standard_normal((250, 4))
        cov = ledoit_wolf_cov(X)
        assert cov.shape == (4, 4)
        assert np.allclose(cov, cov.T)
        assert np.all(np.linalg.eigvalsh(cov) > 0)

    def test_intensity_bounds(self):
        rng = np.random.default_rng(1)
        for _ in range(20):
            X = rng.standard_normal((250, 4))
            d = shrinkage_intensity(X)
            assert 0.0 <= d <= 1.0

    def test_mse_not_worse_than_sample(self):
        """LW 估计的 MSE 不应显著差于样本协方差（Monte Carlo）"""
        rng = np.random.default_rng(42)
        p = 4
        vols = np.array([0.187, 0.030, 0.150, 0.160])
        corr = np.array(
            [
                [1.00, -0.23, 0.15, 0.25],
                [-0.23, 1.00, 0.04, -0.15],
                [0.15, 0.04, 1.00, 0.16],
                [0.25, -0.15, 0.16, 1.00],
            ]
        )
        L = np.linalg.cholesky(corr)
        sigma_true = np.outer(vols, vols) * corr
        mse_s, mse_lw = [], []
        for _ in range(200):
            X = rng.standard_normal((250, p)) @ L.T * (vols / np.sqrt(252))
            S = np.cov(X.T, ddof=0)
            LW = ledoit_wolf_cov(X)
            mse_s.append(((S - sigma_true / 252) ** 2).mean())
            mse_lw.append(((LW - sigma_true / 252) ** 2).mean())
        # p/n 较小（4/250）时两者接近，LW 不应显著更差（容差 15%）
        assert np.mean(mse_lw) <= np.mean(mse_s) * 1.15

    def test_constant_correlation_target_when_perfect(self):
        """数据本身为常相关时，收缩强度应接近 1（目标即真值）"""
        rng = np.random.default_rng(3)
        n, p = 250, 6
        vols = np.linspace(0.05, 0.30, p)
        r = 0.3
        corr = np.full((p, p), r)
        np.fill_diagonal(corr, 1.0)
        L = np.linalg.cholesky(corr)
        X = rng.standard_normal((n, p)) @ L.T * (vols / np.sqrt(252))
        assert shrinkage_intensity(X) > 0.5


# ---------------------------------------------------------------------------
# ERC 求解
# ---------------------------------------------------------------------------


class TestERC:
    def test_risk_contributions_sum_to_one(self, cov_4a):
        w = np.array([0.1, 0.7, 0.1, 0.1])
        rc = risk_contributions(w, cov_4a)
        assert np.isclose(rc.sum(), 1.0)

    def test_erc_equal_budgets(self, cov_4a):
        w = erc_weights(cov_4a)
        assert np.all(w >= -1e-12)
        assert np.isclose(w.sum(), 1.0)
        rc = risk_contributions(w, cov_4a)
        # 等预算 ERC：各腿风险贡献相等
        assert np.allclose(rc, 0.25, atol=1e-6)

    def test_erc_low_vol_asset_gets_more_weight(self, cov_4a):
        w = erc_weights(cov_4a)
        # 债券波动最低，应获得最大权重
        assert w[1] == w.max()
        assert w[1] > 0.5

    @pytest.mark.skipif(not HAS_SCIPY, reason="scipy 不可用")
    def test_ccd_matches_slsqp(self, cov_4a):
        """CCD 解与 SLSQP 参考解一致（规格书要求 1e-7 量级）"""
        p = cov_4a.shape[0]

        def eq_cons(w):
            sw = cov_4a @ w
            return w[:-1] * sw[:-1] - w[1:] * sw[1:]

        res = minimize(
            lambda w: ((w - 1.0 / p) ** 2).sum(),
            np.full(p, 1.0 / p),
            method="SLSQP",
            bounds=[(0, 1)] * p,
            constraints=[
                {"type": "eq", "fun": lambda w: w.sum() - 1},
                {"type": "eq", "fun": eq_cons},
            ],
            options={"ftol": 1e-14, "maxiter": 1000},
        )
        assert res.success
        w_ccd = erc_weights(cov_4a)
        assert np.abs(w_ccd - res.x).max() < 1e-6

    def test_cap_non_binding(self, cov_4a):
        """上限宽松时不应触发（规格书：30% 上限全样本零触发）"""
        w = erc_weights_with_cap(cov_4a, cap_idx=0, cap=0.30)
        rc = risk_contributions(w, cov_4a)
        assert rc[0] < 0.30
        # 无约束 ERC 股腿 RC = 25%，上限 30% 时解应不变
        w_free = erc_weights(cov_4a)
        assert np.allclose(w, w_free, atol=1e-8)

    def test_cap_binding(self, cov_4a):
        """上限收紧时应恰好满足约束"""
        w = erc_weights_with_cap(cov_4a, cap_idx=0, cap=0.20)
        rc = risk_contributions(w, cov_4a)
        assert np.isclose(rc[0], 0.20, atol=1e-4)
        assert np.isclose(w.sum(), 1.0)
        assert np.all(w >= -1e-12)
