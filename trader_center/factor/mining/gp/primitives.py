"""
因子挖掘基元函数集

定义用于遗传规划的因子计算基元函数。
"""

import numpy as np
import pandas as pd
from typing import Callable, List, Tuple, Union
from functools import wraps


def protected_division(x1: np.ndarray, x2: np.ndarray) -> np.ndarray:
    """
    保护除法，避免除零错误
    
    Args:
        x1: 被除数
        x2: 除数
    
    Returns:
        除法结果，除数为0时返回0
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(np.abs(x2) > 1e-10, x1 / x2, 0.0)
    return result


def protected_sqrt(x: np.ndarray) -> np.ndarray:
    """
    保护平方根，避免负数开方
    
    Args:
        x: 输入值
    
    Returns:
        平方根结果
    """
    return np.sqrt(np.abs(x))


def protected_log(x: np.ndarray) -> np.ndarray:
    """
    保护对数，避免对非正数取对数
    
    Args:
        x: 输入值
    
    Returns:
        对数结果
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(x > 0, np.log(np.abs(x) + 1e-10), 0.0)
    return result


def protected_inverse(x: np.ndarray) -> np.ndarray:
    """
    保护倒数，避免除零
    
    Args:
        x: 输入值
    
    Returns:
        倒数结果
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(np.abs(x) > 1e-10, 1.0 / x, 0.0)
    return result


def TS_MEAN(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序均值
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        滚动均值
    """
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).mean().values
    return pd.Series(x).rolling(window=window, min_periods=1).mean().values


def TS_STD(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序标准差
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        滚动标准差
    """
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).std().values
    return pd.Series(x).rolling(window=window, min_periods=1).std().values


def TS_MAX(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序最大值
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        滚动最大值
    """
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).max().values
    return pd.Series(x).rolling(window=window, min_periods=1).max().values


def TS_MIN(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序最小值
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        滚动最小值
    """
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).min().values
    return pd.Series(x).rolling(window=window, min_periods=1).min().values


def TS_RANK(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序排名
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        滚动排名百分比
    """
    def rolling_rank(series):
        if len(series) == 0:
            return np.nan
        return (series.rank().iloc[-1] - 1) / (len(series) - 1) if len(series) > 1 else 0.5
    
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).apply(rolling_rank, raw=False).values
    return pd.Series(x).rolling(window=window, min_periods=1).apply(rolling_rank, raw=False).values


def TS_DELTA(x: np.ndarray, period: int = 1) -> np.ndarray:
    """
    时序变化量
    
    Args:
        x: 输入序列
        period: 周期
    
    Returns:
        变化量
    """
    if isinstance(x, pd.Series):
        return x.diff(period).fillna(0).values
    return pd.Series(x).diff(period).fillna(0).values


def TS_DECAY(x: np.ndarray, window: int = 10, factor: float = 0.5) -> np.ndarray:
    """
    时序衰减加权平均
    
    Args:
        x: 输入序列
        window: 窗口大小
        factor: 衰减因子
    
    Returns:
        衰减加权平均
    """
    weights = np.array([factor ** i for i in range(window)])[::-1]
    weights = weights / weights.sum()
    
    def weighted_avg(series):
        if len(series) < window:
            w = weights[-len(series):]
            w = w / w.sum()
            return np.sum(series * w)
        return np.sum(series * weights)
    
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).apply(weighted_avg, raw=True).values
    return pd.Series(x).rolling(window=window, min_periods=1).apply(weighted_avg, raw=True).values


def TS_SUM(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序求和
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        滚动求和
    """
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).sum().values
    return pd.Series(x).rolling(window=window, min_periods=1).sum().values


def TS_PRODUCT(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序乘积
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        滚动乘积
    """
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).apply(np.prod, raw=True).values
    return pd.Series(x).rolling(window=window, min_periods=1).apply(np.prod, raw=True).values


def TS_ARGMAX(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序最大值位置
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        最大值位置（归一化）
    """
    def argmax_normalized(series):
        if len(series) == 0:
            return np.nan
        return np.argmax(series) / max(len(series) - 1, 1)
    
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).apply(argmax_normalized, raw=True).values
    return pd.Series(x).rolling(window=window, min_periods=1).apply(argmax_normalized, raw=True).values


def TS_ARGMIN(x: np.ndarray, window: int = 10) -> np.ndarray:
    """
    时序最小值位置
    
    Args:
        x: 输入序列
        window: 窗口大小
    
    Returns:
        最小值位置（归一化）
    """
    def argmin_normalized(series):
        if len(series) == 0:
            return np.nan
        return np.argmin(series) / max(len(series) - 1, 1)
    
    if isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).apply(argmin_normalized, raw=True).values
    return pd.Series(x).rolling(window=window, min_periods=1).apply(argmin_normalized, raw=True).values


def RANK(x: np.ndarray) -> np.ndarray:
    """
    横截面排名
    
    Args:
        x: 输入值
    
    Returns:
        排名百分比
    """
    if isinstance(x, pd.Series):
        return x.rank(pct=True).values
    return pd.Series(x).rank(pct=True).values


def DELAY(x: np.ndarray, period: int = 1) -> np.ndarray:
    """
    滞后值
    
    Args:
        x: 输入序列
        period: 滞后周期
    
    Returns:
        滞后值
    """
    if isinstance(x, pd.Series):
        return x.shift(period).fillna(method='bfill').values
    return pd.Series(x).shift(period).fillna(method='bfill').values


def SIGN(x: np.ndarray) -> np.ndarray:
    """
    符号函数
    
    Args:
        x: 输入值
    
    Returns:
        符号 (-1, 0, 1)
    """
    return np.sign(x)


def LOG(x: np.ndarray) -> np.ndarray:
    """
    对数函数
    
    Args:
        x: 输入值
    
    Returns:
        对数值
    """
    return protected_log(x)


def ABS(x: np.ndarray) -> np.ndarray:
    """
    绝对值
    
    Args:
        x: 输入值
    
    Returns:
        绝对值
    """
    return np.abs(x)


def SQRT(x: np.ndarray) -> np.ndarray:
    """
    平方根
    
    Args:
        x: 输入值
    
    Returns:
        平方根
    """
    return protected_sqrt(x)


def INV(x: np.ndarray) -> np.ndarray:
    """
    倒数
    
    Args:
        x: 输入值
    
    Returns:
        倒数
    """
    return protected_inverse(x)


def SCALE(x: np.ndarray) -> np.ndarray:
    """
    标准化到[-1, 1]
    
    Args:
        x: 输入值
    
    Returns:
        标准化值
    """
    x_min = np.nanmin(x)
    x_max = np.nanmax(x)
    if x_max - x_min < 1e-10:
        return np.zeros_like(x)
    return 2 * (x - x_min) / (x_max - x_min) - 1


def make_function_set(window_sizes: Optional[List[int]] = None) -> List[Tuple[Callable, str, int]]:
    """
    创建GP函数集
    
    Args:
        window_sizes: 窗口大小列表，默认为 [5, 10, 20]
    
    Returns:
        函数列表，每个元素为 (函数, 名称, 参数数量)
    """
    window_sizes = window_sizes or [5, 10, 20]
    functions = [
        (np.add, 'add', 2),
        (np.subtract, 'sub', 2),
        (np.multiply, 'mul', 2),
        (protected_division, 'div', 2),
        (np.maximum, 'max', 2),
        (np.minimum, 'min', 2),
        (ABS, 'abs', 1),
        (SQRT, 'sqrt', 1),
        (LOG, 'log', 1),
        (SIGN, 'sign', 1),
        (INV, 'inv', 1),
        (SCALE, 'scale', 1),
        (RANK, 'rank', 1),
    ]
    
    def make_safe_ts_func(ts_func, window):
        """创建安全的时序函数，处理边界情况"""
        def safe_ts_func(x):
            if x is None or len(x) == 0:
                return np.array([0.0])
            if np.all(x == 0):
                return np.zeros_like(x, dtype=float)
            try:
                result = ts_func(x, window)
                result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
                return result
            except Exception:
                return np.zeros_like(x, dtype=float)
        return safe_ts_func
    
    for w in window_sizes:
        functions.append((make_safe_ts_func(TS_MEAN, w), f'ts_mean_{w}', 1))
        functions.append((make_safe_ts_func(TS_STD, w), f'ts_std_{w}', 1))
        functions.append((make_safe_ts_func(TS_MAX, w), f'ts_max_{w}', 1))
        functions.append((make_safe_ts_func(TS_MIN, w), f'ts_min_{w}', 1))
        functions.append((make_safe_ts_func(TS_RANK, w), f'ts_rank_{w}', 1))
        functions.append((make_safe_ts_func(TS_DELTA, w), f'ts_delta_{w}', 1))
        functions.append((make_safe_ts_func(TS_SUM, w), f'ts_sum_{w}', 1))
    
    return functions


def make_terminal_set() -> List[str]:
    """
    创建GP终端集（数据字段）
    
    Returns:
        终端变量名称列表
    """
    return [
        'open',
        'high',
        'low',
        'close',
        'volume',
        'vwap',
        'returns',
        'turnover',
        'amount',
    ]


def get_window_sizes() -> List[int]:
    """
    获取默认窗口大小列表
    
    Returns:
        窗口大小列表
    """
    return [5, 10, 20, 60, 120]


FUNCTION_MAP = {
    'add': np.add,
    'sub': np.subtract,
    'mul': np.multiply,
    'div': protected_division,
    'max': np.maximum,
    'min': np.minimum,
    'abs': ABS,
    'sqrt': SQRT,
    'log': LOG,
    'sign': SIGN,
    'inv': INV,
    'scale': SCALE,
    'rank': RANK,
    'ts_mean': TS_MEAN,
    'ts_std': TS_STD,
    'ts_max': TS_MAX,
    'ts_min': TS_MIN,
    'ts_rank': TS_RANK,
    'ts_delta': TS_DELTA,
    'ts_sum': TS_SUM,
    'ts_decay': TS_DECAY,
    'ts_product': TS_PRODUCT,
    'ts_argmax': TS_ARGMAX,
    'ts_argmin': TS_ARGMIN,
    'delay': DELAY,
}


def get_function_map_with_windows(window_sizes: Optional[List[int]] = None) -> Dict[str, Callable]:
    """
    获取包含固定窗口函数的函数映射
    
    Args:
        window_sizes: 窗口大小列表
    
    Returns:
        函数名到函数的映射字典
    """
    window_sizes = window_sizes or [5, 10, 20]
    func_map = FUNCTION_MAP.copy()
    
    for w in window_sizes:
        def make_ts_func(ts_func, window):
            def ts_func_fixed(x):
                return ts_func(x, window)
            return ts_func_fixed
        
        func_map[f'ts_mean_{w}'] = make_ts_func(TS_MEAN, w)
        func_map[f'ts_std_{w}'] = make_ts_func(TS_STD, w)
        func_map[f'ts_max_{w}'] = make_ts_func(TS_MAX, w)
        func_map[f'ts_min_{w}'] = make_ts_func(TS_MIN, w)
        func_map[f'ts_rank_{w}'] = make_ts_func(TS_RANK, w)
        func_map[f'ts_delta_{w}'] = make_ts_func(TS_DELTA, w)
        func_map[f'ts_sum_{w}'] = make_ts_func(TS_SUM, w)
    
    return func_map
