# trader_center/backtest/metrics.py
"""Performance metrics calculation for backtest results."""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


def calculate_cagr(start_value: float, end_value: float, days: int) -> float:
    """计算年化复合增长率 (CAGR).

    Args:
        start_value: 初始资金
        end_value: 结束资金
        days: 交易日天数

    Returns:
        年化收益率
    """
    if days <= 0 or start_value <= 0:
        return 0.0
    years = days / 365.25  # 使用日历年份
    return (end_value / start_value) ** (1 / years) - 1


def calculate_max_drawdown(values: pd.Series) -> Tuple[float, int, int]:
    """计算最大回撤.

    Args:
        values: 资金曲线序列

    Returns:
        (最大回撤比例, 峰值索引, 谷值索引)
    """
    if len(values) < 2:
        return 0.0, 0, 0

    # 计算累计最大值 (历史峰值)
    running_max = values.cummax()

    # 计算回撤
    drawdown = (values - running_max) / running_max

    # 找到最大回撤
    max_dd_idx = drawdown.idxmin()
    max_dd = drawdown.min()

    # 找到对应的峰值位置
    peak_idx = values.loc[:max_dd_idx].idxmax()

    return abs(max_dd), values.index.get_loc(peak_idx), values.index.get_loc(max_dd_idx)


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
    """计算夏普比率.

    Args:
        returns: 每日收益率序列
        risk_free_rate: 年化无风险利率

    Returns:
        夏普比率
    """
    if len(returns) < 2:
        return 0.0

    # 将年化无风险利率转为日利率
    daily_risk_free = risk_free_rate / 252

    # 超额收益
    excess_returns = returns - daily_risk_free

    # 夏普比率 = 超额收益均值 / 超额收益标准差 * sqrt(252)
    if excess_returns.std() == 0:
        return 0.0

    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)


def calculate_metrics(daily_values: pd.DataFrame) -> Dict[str, float]:
    """计算完整的绩效指标.

    Args:
        daily_values: DataFrame with 'value' column

    Returns:
        指标字典
    """
    values = daily_values['value']
    returns = values.pct_change().dropna()

    total_return = values.iloc[-1] / values.iloc[0] - 1
    days = len(values)

    cagr = calculate_cagr(values.iloc[0], values.iloc[-1], days)
    max_dd, _, _ = calculate_max_drawdown(values)
    sharpe = calculate_sharpe_ratio(returns)

    # 计算波动率 (年化)
    volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0.0

    # 计算 Calmar 比率 (年化收益 / 最大回撤)
    calmar = cagr / max_dd if max_dd > 0 else 0.0

    return {
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'cagr': cagr,
        'cagr_pct': cagr * 100,
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd * 100,
        'sharpe_ratio': sharpe,
        'volatility': volatility,
        'volatility_pct': volatility * 100,
        'calmar_ratio': calmar,
        'trading_days': days,
    }
