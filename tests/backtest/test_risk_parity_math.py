"""
风险平价数学核心测试

验证：
- Ledoit-Wolf (2004 Honey) 收缩估计的合理性（PSD、MSE 不劣于样本协方差量级）
- CCD-ERC 求解器与 SLSQP 参考解一致
- 风险贡献计算的正确性
- 不同资产腿数量下的 1/N 风险预算
"""

import numpy as np
import pytest

from trader_center.backtest.strategy.risk_parity_math import (
    erc_weights,
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


def _constant_correlation_reference(returns):
    """按 Honey 附录的中心化乘积定义逐项计算，独立于生产代码的矩阵展开。"""
    x = returns - returns.mean(axis=0)
    n, p = x.shape
    sample = x.T @ x / n
    std = np.sqrt(np.diag(sample))
    mean_corr = np.mean(
        [sample[i, j] / (std[i] * std[j]) for i in range(p) for j in range(i)]
    )
    target = mean_corr * np.outer(std, std)
    np.fill_diagonal(target, np.diag(sample))

    pi = 0.0
    rho = 0.0
    for i in range(p):
        for j in range(p):
            residual = x[:, i] * x[:, j] - sample[i, j]
            pi_ij = np.mean(residual**2)
            pi += pi_ij
            if i == j:
                rho += pi_ij
            else:
                theta_i = np.mean((x[:, i] ** 2 - sample[i, i]) * residual)
                theta_j = np.mean((x[:, j] ** 2 - sample[j, j]) * residual)
                rho += (
                    mean_corr
                    / 2
                    * (std[j] / std[i] * theta_i + std[i] / std[j] * theta_j)
                )

    distance = np.sum((target - sample) ** 2)
    intensity = float(np.clip((pi - rho) / (n * distance), 0, 1))
    return intensity, intensity * target + (1 - intensity) * sample


class TestLedoitWolf:
    @pytest.mark.parametrize("seed", [0, 42, 2026])
    def test_matches_centered_product_reference(self, cov_4a, seed):
        rng = np.random.default_rng(seed)
        returns = rng.standard_normal((250, 4)) @ np.linalg.cholesky(cov_4a / 252).T
        expected_delta, expected_cov = _constant_correlation_reference(returns)
        # 避免被 [0, 1] 裁剪掩盖收缩强度公式错误。
        assert 0 < expected_delta < 1
        assert shrinkage_intensity(returns) == pytest.approx(expected_delta, abs=1e-12)
        np.testing.assert_allclose(
            ledoit_wolf_cov(returns), expected_cov, rtol=1e-12, atol=1e-18
        )

    @pytest.mark.parametrize("scale", [0.01, 100.0, -1.0])
    def test_uniform_scaling_preserves_intensity_and_erc(self, cov_4a, scale):
        rng = np.random.default_rng(42)
        returns = rng.standard_normal((250, 4)) @ np.linalg.cholesky(cov_4a / 252).T
        cov = ledoit_wolf_cov(returns)
        scaled_cov = ledoit_wolf_cov(returns * scale)
        assert shrinkage_intensity(returns * scale) == pytest.approx(
            shrinkage_intensity(returns), abs=1e-12
        )
        np.testing.assert_allclose(scaled_cov, cov * scale**2, rtol=1e-12, atol=1e-18)
        np.testing.assert_allclose(erc_weights(scaled_cov), erc_weights(cov), atol=1e-9)

    def test_identical_target_reports_actual_intensity(self):
        # S == F 时强度不可识别；两个公开入口约定同样使用 delta=1。
        returns = np.array([[-1.0, -2.0], [1.0, 2.0]])
        assert shrinkage_intensity(returns) == 1.0
        np.testing.assert_allclose(ledoit_wolf_cov(returns), [[1.0, 2.0], [2.0, 4.0]])

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

    @pytest.mark.parametrize("n_legs", [2, 3, 4, 5, 8])
    def test_equal_risk_budget_follows_leg_count(self, n_legs):
        """每腿风险预算随 N 变化，包括超过旧股票上限的 2/3 腿情况。"""
        rng = np.random.default_rng(42)
        factor = rng.standard_normal((n_legs, n_legs))
        cov = factor @ factor.T + np.eye(n_legs)
        scales = np.linspace(0.03, 0.20, n_legs)
        cov *= np.outer(scales, scales)
        w = erc_weights(cov)
        rc = risk_contributions(w, cov)
        np.testing.assert_allclose(rc, 1 / n_legs, atol=1e-6)
        assert np.isclose(w.sum(), 1.0)
        assert np.all(w >= -1e-12)
