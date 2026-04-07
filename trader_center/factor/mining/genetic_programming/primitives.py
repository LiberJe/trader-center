"""
遗传规划基元定义

定义因子表达式的操作符、函数和终端符号。
"""

from typing import Callable, List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum


class PrimitiveType(Enum):
    TERMINAL = "terminal"
    FUNCTION = "function"


@dataclass
class Primitive:
    name: str
    ptype: PrimitiveType
    arity: int = 0
    function: Optional[Callable] = None
    description: str = ""
    
    def __repr__(self):
        if self.ptype == PrimitiveType.TERMINAL:
            return f"Terminal({self.name})"
        return f"Function({self.name}, arity={self.arity})"


class PrimitiveSet:
    """
    基元集合
    
    管理因子表达式可用的操作符和终端符号。
    
    Example:
        pset = PrimitiveSet()
        pset.add_terminal('close', '收盘价')
        pset.add_function('rank', rank_func, 1, '横截面排名')
    """
    
    def __init__(self):
        self.terminals: Dict[str, Primitive] = {}
        self.functions: Dict[str, Primitive] = {}
        self.context: Dict[str, Any] = {}
    
    def add_terminal(
        self,
        name: str,
        description: str = "",
        data_key: str = None,
    ) -> None:
        """
        添加终端符号
        
        Args:
            name: 终端名称
            description: 描述
            data_key: 数据键名（如果与name不同）
        """
        terminal = Primitive(
            name=name,
            ptype=PrimitiveType.TERMINAL,
            description=description,
        )
        self.terminals[name] = terminal
        self.context[name] = data_key or name
    
    def add_function(
        self,
        name: str,
        function: Callable,
        arity: int,
        description: str = "",
    ) -> None:
        """
        添加函数
        
        Args:
            name: 函数名称
            function: 函数实现
            arity: 参数个数
            description: 描述
        """
        func = Primitive(
            name=name,
            ptype=PrimitiveType.FUNCTION,
            arity=arity,
            function=function,
            description=description,
        )
        self.functions[name] = func
    
    def get_terminal(self, name: str) -> Primitive:
        """获取终端符号"""
        return self.terminals.get(name)
    
    def get_function(self, name: str) -> Primitive:
        """获取函数"""
        return self.functions.get(name)
    
    def get_random_terminal(self) -> Primitive:
        """随机获取一个终端符号"""
        return np.random.choice(list(self.terminals.values()))
    
    def get_random_function(self) -> Primitive:
        """随机获取一个函数"""
        return np.random.choice(list(self.functions.values()))
    
    def get_terminals_by_arity(self, arity: int) -> List[Primitive]:
        """获取指定参数个数的函数列表"""
        return [f for f in self.functions.values() if f.arity == arity]


def create_default_pset() -> PrimitiveSet:
    """
    创建默认的基元集合
    
    包含常用的技术指标操作符和数据字段。
    
    Returns:
        配置好的PrimitiveSet实例
    """
    pset = PrimitiveSet()
    
    pset.add_terminal('open', '开盘价')
    pset.add_terminal('high', '最高价')
    pset.add_terminal('low', '最低价')
    pset.add_terminal('close', '收盘价')
    pset.add_terminal('volume', '成交量')
    pset.add_terminal('vwap', '成交量加权平均价')
    
    pset.add_terminal('returns', '收益率')
    pset.add_terminal('log_returns', '对数收益率')
    
    pset.add_function('add', _add, 2, '加法')
    pset.add_function('sub', _sub, 2, '减法')
    pset.add_function('mul', _mul, 2, '乘法')
    pset.add_function('div', _div, 2, '除法（安全）')
    
    pset.add_function('abs', _abs, 1, '绝对值')
    pset.add_function('neg', _neg, 1, '取负')
    pset.add_function('sqrt', _sqrt, 1, '平方根（安全）')
    pset.add_function('log', _log, 1, '对数（安全）')
    pset.add_function('sign', _sign, 1, '符号')
    
    pset.add_function('rank', _rank, 1, '横截面排名')
    pset.add_function('zscore', _zscore, 1, '横截面标准化')
    pset.add_function('scale', _scale, 1, '缩放到[-1,1]')
    
    pset.add_function('ts_mean', _ts_mean, 2, '时间序列均值')
    pset.add_function('ts_std', _ts_std, 2, '时间序列标准差')
    pset.add_function('ts_max', _ts_max, 2, '时间序列最大值')
    pset.add_function('ts_min', _ts_min, 2, '时间序列最小值')
    pset.add_function('ts_sum', _ts_sum, 2, '时间序列求和')
    pset.add_function('ts_delay', _ts_delay, 2, '时间序列滞后')
    pset.add_function('ts_delta', _ts_delta, 2, '时间序列差分')
    pset.add_function('ts_rank', _ts_rank, 2, '时间序列排名')
    
    pset.add_function('ts_corr', _ts_corr, 3, '时间序列相关性')
    pset.add_function('ts_cov', _ts_cov, 3, '时间序列协方差')
    
    pset.add_function('decay_linear', _decay_linear, 2, '线性衰减')
    
    return pset


def _add(x, y):
    return x + y

def _sub(x, y):
    return x - y

def _mul(x, y):
    return x * y

def _div(x, y):
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(np.abs(y) > 1e-10, x / y, 0.0)
    return result

def _abs(x):
    return np.abs(x)

def _neg(x):
    return -x

def _sqrt(x):
    return np.sqrt(np.abs(x))

def _log(x):
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(x > 0, np.log(np.abs(x) + 1e-10), 0.0)
    return result

def _sign(x):
    return np.sign(x)

def _rank(x):
    if isinstance(x, pd.DataFrame):
        return x.rank(axis=1, pct=True)
    elif isinstance(x, pd.Series):
        return x.rank(pct=True)
    else:
        return pd.Series(x).rank(pct=True).values

def _zscore(x):
    if isinstance(x, pd.DataFrame):
        mean = x.mean(axis=1)
        std = x.std(axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            result = (x.sub(mean, axis=0)).div(std.replace(0, np.nan), axis=0)
        return result.fillna(0)
    elif isinstance(x, pd.Series):
        mean = x.mean()
        std = x.std()
        if std == 0:
            return pd.Series(0, index=x.index)
        return (x - mean) / std
    else:
        x_arr = np.array(x)
        mean = np.mean(x_arr)
        std = np.std(x_arr)
        if std == 0:
            return np.zeros_like(x_arr)
        return (x_arr - mean) / std

def _scale(x):
    if isinstance(x, pd.DataFrame):
        max_val = x.abs().max(axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            result = x.div(max_val.replace(0, np.nan), axis=0)
        return result.fillna(0)
    elif isinstance(x, pd.Series):
        max_val = x.abs().max()
        if max_val == 0:
            return pd.Series(0, index=x.index)
        return x / max_val
    else:
        x_arr = np.array(x)
        max_val = np.max(np.abs(x_arr))
        if max_val == 0:
            return np.zeros_like(x_arr)
        return x_arr / max_val

def _ts_mean(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.rolling(window=window, min_periods=1).mean()
    elif isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).mean()
    else:
        return pd.Series(x).rolling(window=window, min_periods=1).mean().values

def _ts_std(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.rolling(window=window, min_periods=1).std()
    elif isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).std()
    else:
        return pd.Series(x).rolling(window=window, min_periods=1).std().values

def _ts_max(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.rolling(window=window, min_periods=1).max()
    elif isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).max()
    else:
        return pd.Series(x).rolling(window=window, min_periods=1).max().values

def _ts_min(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.rolling(window=window, min_periods=1).min()
    elif isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).min()
    else:
        return pd.Series(x).rolling(window=window, min_periods=1).min().values

def _ts_sum(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.rolling(window=window, min_periods=1).sum()
    elif isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).sum()
    else:
        return pd.Series(x).rolling(window=window, min_periods=1).sum().values

def _ts_delay(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.shift(window)
    elif isinstance(x, pd.Series):
        return x.shift(window)
    else:
        return pd.Series(x).shift(window).values

def _ts_delta(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.diff(window)
    elif isinstance(x, pd.Series):
        return x.diff(window)
    else:
        return pd.Series(x).diff(window).values

def _ts_rank(x, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame):
        return x.rolling(window=window, min_periods=1).apply(
            lambda s: pd.Series(s).rank(pct=True).iloc[-1] if len(s) > 0 else np.nan
        )
    elif isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).apply(
            lambda s: pd.Series(s).rank(pct=True).iloc[-1] if len(s) > 0 else np.nan
        )
    else:
        return pd.Series(x).rolling(window=window, min_periods=1).apply(
            lambda s: pd.Series(s).rank(pct=True).iloc[-1] if len(s) > 0 else np.nan
        ).values

def _ts_corr(x, y, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame) and isinstance(y, pd.DataFrame):
        def rolling_corr(s1, s2):
            if len(s1) < 2:
                return np.nan
            return pd.Series(s1).corr(pd.Series(s2))
        
        result = pd.DataFrame(index=x.index, columns=x.columns)
        for col in x.columns:
            result[col] = x[col].rolling(window=window, min_periods=2).corr(y[col])
        return result
    else:
        x_s = pd.Series(x) if not isinstance(x, pd.Series) else x
        y_s = pd.Series(y) if not isinstance(y, pd.Series) else y
        return x_s.rolling(window=window, min_periods=2).corr(y_s)

def _ts_cov(x, y, window):
    window = int(max(1, abs(window)))
    if isinstance(x, pd.DataFrame) and isinstance(y, pd.DataFrame):
        result = pd.DataFrame(index=x.index, columns=x.columns)
        for col in x.columns:
            result[col] = x[col].rolling(window=window, min_periods=2).cov(y[col])
        return result
    else:
        x_s = pd.Series(x) if not isinstance(x, pd.Series) else x
        y_s = pd.Series(y) if not isinstance(y, pd.Series) else y
        return x_s.rolling(window=window, min_periods=2).cov(y_s)

def _decay_linear(x, window):
    window = int(max(1, abs(window)))
    weights = np.arange(1, window + 1)
    weights = weights / weights.sum()
    
    if isinstance(x, pd.DataFrame):
        result = pd.DataFrame(index=x.index, columns=x.columns)
        for col in x.columns:
            result[col] = x[col].rolling(window=window, min_periods=1).apply(
                lambda s: np.dot(s[-window:], weights[-len(s):]) if len(s) > 0 else np.nan
            )
        return result
    elif isinstance(x, pd.Series):
        return x.rolling(window=window, min_periods=1).apply(
            lambda s: np.dot(s[-window:], weights[-len(s):]) if len(s) > 0 else np.nan
        )
    else:
        return pd.Series(x).rolling(window=window, min_periods=1).apply(
            lambda s: np.dot(s[-window:], weights[-len(s):]) if len(s) > 0 else np.nan
        ).values
