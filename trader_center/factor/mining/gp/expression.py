"""
因子表达式处理

将GP生成的表达式树转换为可执行的因子类。
"""

import re
import hashlib
from typing import Dict, Any, Optional, List, Callable
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor
from .primitives import FUNCTION_MAP, get_function_map_with_windows


class FactorExpression:
    """
    因子表达式
    
    封装GP生成的因子表达式，提供转换和执行功能。
    """
    
    def __init__(
        self,
        expression_str: str,
        expression_tree: Optional[Any] = None,
        fitness: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化因子表达式
        
        Args:
            expression_str: 表达式字符串
            expression_tree: 原始表达式树（gplearn格式）
            fitness: 适应度值
            metadata: 元数据
        """
        self.expression_str = expression_str
        self.expression_tree = expression_tree
        self.fitness = fitness
        self.metadata = metadata or {}
        self._factor_instance: Optional[BaseFactor] = None
        self._factor_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成因子唯一ID"""
        hash_str = hashlib.md5(self.expression_str.encode()).hexdigest()[:8]
        return f"gp_factor_{hash_str}"
    
    @property
    def name(self) -> str:
        """因子名称"""
        return self._factor_id
    
    def to_factor(self) -> BaseFactor:
        """
        转换为BaseFactor实例
        
        Returns:
            BaseFactor实例
        """
        if self._factor_instance is not None:
            return self._factor_instance
        
        expression_str = self.expression_str
        fitness = self.fitness
        factor_id = self._factor_id
        
        class GPGeneratedFactor(BaseFactor):
            """GP生成的因子"""
            
            @property
            def name(self) -> str:
                return factor_id
            
            @property
            def category(self) -> str:
                return "gp_generated"
            
            @property
            def description(self) -> str:
                return f"GP generated factor: {expression_str}"
            
            def compute(self, data: pd.DataFrame) -> pd.Series:
                return evaluate_expression(expression_str, data)
        
        self._factor_instance = GPGeneratedFactor()
        return self._factor_instance
    
    def to_code(self) -> str:
        """
        生成Python代码
        
        Returns:
            Python代码字符串
        """
        code = f'''
class {self._factor_id.capitalize()}(BaseFactor):
    """自动生成的因子: {self.expression_str}"""
    
    name = "{self._factor_id}"
    category = "gp_generated"
    description = "{self.expression_str}"
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        return evaluate_expression("{self.expression_str}", data)
'''
        return code
    
    def to_latex(self) -> str:
        """
        生成LaTeX公式
        
        Returns:
            LaTeX公式字符串
        """
        latex_expr = self._convert_to_latex(self.expression_str)
        return f"${latex_expr}$"
    
    def _convert_to_latex(self, expr: str) -> str:
        """将表达式转换为LaTeX格式"""
        replacements = {
            'add': '+',
            'sub': '-',
            'mul': r'\\times',
            'div': r'\\div',
            'sqrt': r'\\sqrt',
            'log': r'\\log',
            'abs': r'|',
            'sign': r'\\text{sign}',
            'ts_mean': r'\\text{ts\_mean}',
            'ts_std': r'\\text{ts\_std}',
            'ts_max': r'\\text{ts\_max}',
            'ts_min': r'\\text{ts\_min}',
            'ts_rank': r'\\text{ts\_rank}',
            'ts_delta': r'\\text{ts\_delta}',
            'ts_sum': r'\\text{ts\_sum}',
            'rank': r'\\text{rank}',
        }
        
        result = expr
        for old, new in replacements.items():
            result = result.replace(old, new)
        
        return result
    
    def __repr__(self) -> str:
        return f"FactorExpression('{self.expression_str}', fitness={self.fitness})"
    
    def __str__(self) -> str:
        return self.expression_str


class ExpressionConverter:
    """
    表达式转换器
    
    将gplearn的表达式树转换为可执行代码。
    """
    
    @staticmethod
    def from_gplearn(program) -> FactorExpression:
        """
        从gplearn程序创建因子表达式
        
        Args:
            program: gplearn的program对象
        
        Returns:
            FactorExpression实例
        """
        expression_str = str(program)
        
        fitness = None
        if hasattr(program, 'fitness_') and program.fitness_ is not None:
            fitness = program.fitness_.wvalues[0] if hasattr(program.fitness_, 'wvalues') else float(program.fitness_)
        
        metadata = {
            'raw_program': program,
            'length': len(program) if hasattr(program, '__len__') else 0,
        }
        
        return FactorExpression(
            expression_str=expression_str,
            expression_tree=program,
            fitness=fitness,
            metadata=metadata,
        )
    
    @staticmethod
    def batch_from_gplearn(programs: List) -> List[FactorExpression]:
        """
        批量转换gplearn程序
        
        Args:
            programs: gplearn程序列表
        
        Returns:
            FactorExpression列表
        """
        return [ExpressionConverter.from_gplearn(p) for p in programs]


def evaluate_expression(expression: str, data: pd.DataFrame, window_sizes: Optional[List[int]] = None) -> pd.Series:
    """
    执行因子表达式
    
    Args:
        expression: 表达式字符串
        data: 包含OHLCV等数据的DataFrame
        window_sizes: 窗口大小列表
    
    Returns:
        因子值Series
    """
    local_vars = {}
    
    for col in data.columns:
        local_vars[col] = data[col].values
    
    local_vars['vwap'] = data.get('vwap', (data['high'] + data['low'] + data['close']) / 3).values if 'vwap' not in data.columns else data['vwap'].values
    local_vars['returns'] = data['close'].pct_change().fillna(0).values if 'returns' not in data.columns else data['returns'].values
    local_vars['turnover'] = data.get('turnover', data['volume'] / data['volume'].rolling(20).mean().replace(0, 1)).values if 'turnover' not in data.columns else data['turnover'].values
    local_vars['amount'] = data.get('amount', data['close'] * data['volume']).values if 'amount' not in data.columns else data['amount'].values
    
    func_map = get_function_map_with_windows(window_sizes)
    for func_name, func in func_map.items():
        local_vars[func_name] = func
    
    local_vars['np'] = np
    local_vars['pd'] = pd
    
    safe_builtins = {
        'abs': np.abs,
        'max': np.maximum,
        'min': np.minimum,
        'sum': np.sum,
        'mean': np.mean,
        'std': np.std,
    }
    local_vars['__builtins__'] = safe_builtins
    
    try:
        result = eval(expression, {"__builtins__": {}}, local_vars)
        
        if isinstance(result, np.ndarray):
            return pd.Series(result, index=data.index)
        elif isinstance(result, pd.Series):
            return result
        else:
            return pd.Series(result, index=data.index)
    
    except Exception as e:
        return pd.Series(np.nan, index=data.index)


def simplify_expression(expression: str) -> str:
    """
    简化表达式
    
    Args:
        expression: 原始表达式
    
    Returns:
        简化后的表达式
    """
    expr = expression
    
    expr = re.sub(r'add\(([^,]+),\s*0\)', r'\1', expr)
    expr = re.sub(r'add\(0,\s*([^,]+)\)', r'\1', expr)
    expr = re.sub(r'sub\(([^,]+),\s*0\)', r'\1', expr)
    expr = re.sub(r'mul\(([^,]+),\s*1\)', r'\1', expr)
    expr = re.sub(r'mul\(1,\s*([^,]+)\)', r'\1', expr)
    expr = re.sub(r'div\(([^,]+),\s*1\)', r'\1', expr)
    
    return expr


def expression_complexity(expression: str) -> int:
    """
    计算表达式复杂度
    
    Args:
        expression: 表达式字符串
    
    Returns:
        复杂度值
    """
    operators = ['add', 'sub', 'mul', 'div', 'max', 'min', 'abs', 'sqrt', 'log', 
                 'sign', 'inv', 'scale', 'rank', 'ts_mean', 'ts_std', 'ts_max', 
                 'ts_min', 'ts_rank', 'ts_delta', 'ts_sum']
    
    complexity = 0
    for op in operators:
        complexity += expression.count(op)
    
    return complexity
