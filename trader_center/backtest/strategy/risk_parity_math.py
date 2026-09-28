"""
风险平价数学核心

纯 numpy 实现（无 sklearn/scipy 依赖）：
- Ledoit-Wolf (2004) "Simple" 收缩协方差估计（常相关收缩目标）
- 等风险贡献（ERC）权重求解：循环坐标下降（CCD）
- 单腿风险贡献上限的保险条款（bisection 兜底）

参考：
- Ledoit, O. & Wolf, M. (2004). "Honey, I Shrunk the Sample Covariance
  Matrix." Journal of Portfolio Management（常相关收缩目标版本）
- Spinu, F. (2013). "An Algorithm for Computing Risk Parity Weights."
- Roncalli, T. (2013). "Introduction to Risk Parity and Budgeting."
"""

from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Ledoit-Wolf (2004) Simple 收缩协方差
# ---------------------------------------------------------------------------


def ledoit_wolf_cov(returns: np.ndarray) -> np.ndarray:
    """
    Ledoit-Wolf (2004) "Simple" 收缩协方差估计。

    将样本协方差向"常相关矩阵"收缩：
        Σ̂ = δ·F + (1−δ)·S
    其中 S 为样本协方差（MLE，1/n），F 与 S 对角相同、非对角为平均相关
    乘以对应标准差乘积，δ 为收缩强度（由数据驱动，∈ [0, 1]）。

    Args:
        returns: 收益率矩阵，shape (n, p)，n 个观测、 p 个资产

    Returns:
        收缩后的协方差矩阵，shape (p, p)，对称；退化数据下不保证严格正定
    """
    cov, _ = _ledoit_wolf_estimate(returns)
    return cov


def shrinkage_intensity(returns: np.ndarray) -> float:
    """返回协方差估计实际采用的 LW 收缩强度 δ；S == F 时约定为 1。"""
    _, intensity = _ledoit_wolf_estimate(returns)
    return intensity


def _ledoit_wolf_estimate(returns: np.ndarray) -> tuple[np.ndarray, float]:
    """共用常相关目标估计，避免协方差与诊断强度的公式或边界处理分叉。"""
    X = np.asarray(returns, dtype=np.float64)
    if X.ndim != 2:
        raise ValueError("returns 必须是二维矩阵 (n, p)")
    n, p = X.shape
    if n < 2 or p < 2:
        raise ValueError("观测数与资产数必须 >= 2")

    X = X - X.mean(axis=0)
    S = (X.T @ X) / n

    # --- 收缩目标 F：常相关，对角与 S 一致 ---
    d = np.sqrt(np.diag(S))
    outer_d = np.outer(d, d)
    # 避免除零（某资产零波动时相关无定义，按 0 处理）
    with np.errstate(divide="ignore", invalid="ignore"):
        R = np.where(outer_d > 0, S / np.where(outer_d > 0, outer_d, 1.0), 0.0)
    np.fill_diagonal(R, 0.0)
    if p > 1:
        rbar = R.sum() / (p * (p - 1))
    else:
        rbar = 0.0
    F = rbar * outer_d
    np.fill_diagonal(F, np.diag(S))

    # --- π̂_ij：√T·s_ij 渐近方差的估计 ---
    # π̂_ij = (1/T) Σ_t (x_ti·x_tj − s_ij)² = (X²)'(X²)/T − s_ij²
    X2 = X * X
    pi_mat = (X2.T @ X2) / n - S * S

    # --- ρ̂：收缩目标 F 与样本协方差的渐近协方差之和（LW 2004 JoPF, eq. (12)）---
    # ρ̂ = Σ_i π̂_ii + Σ_{i≠j} (r̄/2)·( √(s_jj/s_ii)·ϑ̂_{ii,ij} + √(s_ii/s_jj)·ϑ̂_{jj,ij} )
    # ϑ̂_{ii,ij} = (1/T) Σ_t (x_ti² − s_ii)(x_ti·x_tj − s_ij)
    idx = np.arange(p)
    d_i = d[idx]  # √s_ii
    ratio_ij = np.outer(d_i, 1.0 / d_i)  # √(s_ii/s_jj)，[i,j] 元素
    # 展开中心化乘积得到 E[x_i³ x_j] - s_ii·s_ij，必须是四阶矩。
    theta_ii_ij = ((X2 * X).T @ X) / n - S * np.diag(S)[:, None]
    rho_off = (rbar / 2.0) * (
        np.swapaxes(ratio_ij, 0, 1) * theta_ii_ij  # √(s_jj/s_ii)·ϑ̂_{ii,ij}
        + ratio_ij * theta_ii_ij.T  # √(s_ii/s_jj)·ϑ̂_{jj,ij}
    )
    np.fill_diagonal(rho_off, 0.0)
    rho = float(np.sum(pi_mat[idx, idx]) + np.sum(rho_off))

    # --- γ̂²：样本协方差与收缩目标的距离 ---
    gamma2 = float(np.sum((F - S) ** 2))

    # 最优收缩强度 δ* = clip( κ̂ / T, 0, 1 )，κ̂ = (π̂ − ρ̂)/γ̂
    if gamma2 <= 0:
        shrinkage = 1.0
    else:
        shrinkage = (float(np.sum(pi_mat)) - rho) / (n * gamma2)
    shrinkage = min(1.0, max(0.0, shrinkage))

    cov = shrinkage * F + (1.0 - shrinkage) * S

    # 数值保护：对称化 + 对角下限（不等价于严格正定修复）
    cov = (cov + cov.T) / 2.0
    diag = np.diag(cov).copy()
    diag[diag <= 0] = 1e-12
    np.fill_diagonal(cov, diag)
    return cov, shrinkage


# ---------------------------------------------------------------------------
# 等风险贡献（ERC）权重
# ---------------------------------------------------------------------------


def risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """
    计算各资产的风险贡献占比 RC_i = w_i·(Σw)_i / (w'Σw)。

    Args:
        weights: 权重向量，shape (p,)
        cov: 协方差矩阵，shape (p, p)

    Returns:
        风险贡献占比向量，shape (p,)，求和为 1
    """
    w = np.asarray(weights, dtype=np.float64)
    sigma_w = cov @ w
    var_p = float(w @ sigma_w)
    if var_p <= 0:
        return np.full_like(w, 1.0 / len(w))
    return w * sigma_w / var_p


def erc_weights(
    cov: np.ndarray,
    budgets: Optional[np.ndarray] = None,
    tol: float = 1e-10,
    max_sweeps: int = 500,
) -> np.ndarray:
    """
    循环坐标下降（CCD）求解等风险贡献权重。

    求解 w ≥ 0, Σw = 1，使得各资产风险贡献 RC_i 等于给定预算 b_i。
    单资产坐标更新为二次方程正根（Roncalli, 2013）：
        σ_ii·w_i² + c_i·w_i = b_i·σ_p²
        w_i ← max(0, [−c_i + √(c_i² + 4·σ_ii·b_i·σ_p²)] / (2·σ_ii))
    其中 c_i = Σ_{j≠i} σ_ij·w_j，σ_p² = w'Σw 每轮扫描后更新。

    Args:
        cov: 协方差矩阵，shape (p, p)，需正定
        budgets: 风险预算向量，shape (p,)；None 表示等预算（1/p）
        tol: 收敛容差（单轮最大权重变化）
        max_sweeps: 最大扫描轮数

    Returns:
        权重向量，shape (p,)，非负且和为 1
    """
    cov = np.asarray(cov, dtype=np.float64)
    p = cov.shape[0]
    if budgets is None:
        budgets = np.full(p, 1.0 / p)
    else:
        budgets = np.asarray(budgets, dtype=np.float64)
        if budgets.shape != (p,):
            raise ValueError("budgets 维度必须与协方差矩阵一致")
        total = budgets.sum()
        if total <= 0:
            raise ValueError("风险预算必须为正")
        budgets = budgets / total

    # 初始化：等权
    w = np.full(p, 1.0 / p)
    var_p = float(w @ cov @ w)

    for _ in range(max_sweeps):
        max_diff = 0.0
        for i in range(p):
            c_i = float(cov[i] @ w - cov[i, i] * w[i])
            disc = c_i * c_i + 4.0 * cov[i, i] * budgets[i] * var_p
            new_wi = max(0.0, (-c_i + np.sqrt(max(disc, 0.0))) / (2.0 * cov[i, i]))
            max_diff = max(max_diff, abs(new_wi - w[i]))
            w[i] = new_wi
        s = w.sum()
        if s <= 0:
            w = np.full(p, 1.0 / p)
        else:
            w = w / s
        var_p = float(w @ cov @ w)
        if max_diff < tol:
            break

    return w


def erc_weights_with_cap(
    cov: np.ndarray,
    budgets: Optional[np.ndarray] = None,
    cap_idx: int = 0,
    cap: float = 0.30,
    tol: float = 1e-10,
    max_sweeps: int = 500,
) -> np.ndarray:
    """
    带单腿风险贡献上限的 ERC 权重（保险条款）。

    先求解无约束 ERC；若 cap_idx 资产的风险贡献未超上限则直接返回，
    否则对该资产权重做 bisection：固定 w_cap，剩余资产在子协方差上
    按归一化预算求解 ERC，直至该资产风险贡献恰好等于上限。

    说明：上限在全样本内零触发，本函数仅作为 regime 突变兜底。

    Args:
        cov: 协方差矩阵，shape (p, p)
        budgets: 风险预算向量；None 表示等预算
        cap_idx: 施加风险贡献上限的资产下标
        cap: 风险贡献上限（占比，如 0.30）
        tol/max_sweeps: 传递至 erc_weights

    Returns:
        权重向量，shape (p,)，非负且和为 1
    """
    cov = np.asarray(cov, dtype=np.float64)
    p = cov.shape[0]
    if budgets is None:
        budgets = np.full(p, 1.0 / p)
    else:
        budgets = np.asarray(budgets, dtype=np.float64)
        budgets = budgets / budgets.sum()

    w = erc_weights(cov, budgets, tol=tol, max_sweeps=max_sweeps)
    rc = risk_contributions(w, cov)
    if rc[cap_idx] <= cap + 1e-12:
        return w

    others = [i for i in range(p) if i != cap_idx]
    sub_cov = cov[np.ix_(others, others)]
    sub_budgets = budgets[others]
    sub_budgets = sub_budgets / sub_budgets.sum()

    def _compose(w_cap: float) -> np.ndarray:
        w_full = np.zeros(p)
        w_full[cap_idx] = w_cap
        w_full[others] = erc_weights(
            sub_cov, sub_budgets, tol=tol, max_sweeps=max_sweeps
        ) * (1.0 - w_cap)
        return w_full

    # bisection：RC_cap 随 w_cap 单调（近似假设）， bracket [0, 无约束权重]
    lo, hi = 0.0, w[cap_idx]
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        rc_mid = risk_contributions(_compose(mid), cov)[cap_idx]
        if rc_mid > cap:
            hi = mid
        else:
            lo = mid
    return _compose(lo)
