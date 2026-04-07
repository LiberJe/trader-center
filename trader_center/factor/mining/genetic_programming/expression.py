"""
因子表达式树

定义因子表达式的树形结构，支持求值和序列化。
"""

from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
import copy
from dataclasses import dataclass

from .primitives import Primitive, PrimitiveSet, PrimitiveType


class ExpressionNode:
    """
    表达式树节点
    
    表示因子表达式中的一个元素（函数或终端）。
    """
    
    def __init__(
        self,
        primitive: Primitive,
        children: List['ExpressionNode'] = None,
    ):
        """
        初始化节点
        
        Args:
            primitive: 基元（函数或终端）
            children: 子节点列表
        """
        self.primitive = primitive
        self.children = children or []
        self.parent: Optional['ExpressionNode'] = None
        
        for child in self.children:
            child.parent = self
    
    @property
    def name(self) -> str:
        """节点名称"""
        return self.primitive.name
    
    @property
    def arity(self) -> int:
        """参数个数"""
        return self.primitive.arity
    
    @property
    def is_terminal(self) -> bool:
        """是否为终端节点"""
        return self.primitive.ptype == PrimitiveType.TERMINAL
    
    @property
    def is_function(self) -> bool:
        """是否为函数节点"""
        return self.primitive.ptype == PrimitiveType.FUNCTION
    
    def evaluate(self, data: Dict[str, pd.DataFrame]) -> Union[pd.DataFrame, pd.Series]:
        """
        递归求值
        
        Args:
            data: 数据字典，包含 open, close, volume 等
        
        Returns:
            计算结果
        """
        if self.is_terminal:
            return data.get(self.name, pd.DataFrame())
        
        args = [child.evaluate(data) for child in self.children]
        
        if self.primitive.function is None:
            raise ValueError(f"函数 {self.name} 没有实现")
        
        return self.primitive.function(*args)
    
    def depth(self) -> int:
        """计算树的深度"""
        if self.is_terminal:
            return 0
        return 1 + max(child.depth() for child in self.children) if self.children else 1
    
    def size(self) -> int:
        """计算树的节点数"""
        return 1 + sum(child.size() for child in self.children)
    
    def get_all_nodes(self) -> List['ExpressionNode']:
        """获取所有节点（包括自己）"""
        nodes = [self]
        for child in self.children:
            nodes.extend(child.get_all_nodes())
        return nodes
    
    def get_function_nodes(self) -> List['ExpressionNode']:
        """获取所有函数节点"""
        nodes = []
        if self.is_function:
            nodes.append(self)
        for child in self.children:
            nodes.extend(child.get_function_nodes())
        return nodes
    
    def get_terminal_nodes(self) -> List['ExpressionNode']:
        """获取所有终端节点"""
        nodes = []
        if self.is_terminal:
            nodes.append(self)
        for child in self.children:
            nodes.extend(child.get_terminal_nodes())
        return nodes
    
    def copy(self) -> 'ExpressionNode':
        """深拷贝"""
        return copy.deepcopy(self)
    
    def __repr__(self) -> str:
        if self.is_terminal:
            return self.name
        args = ', '.join(repr(child) for child in self.children)
        return f"{self.name}({args})"
    
    def to_string(self) -> str:
        """转换为字符串表达式"""
        return repr(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'type': self.primitive.ptype.value,
            'children': [child.to_dict() for child in self.children],
        }
    
    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        pset: PrimitiveSet,
    ) -> 'ExpressionNode':
        """从字典创建"""
        if data['type'] == 'terminal':
            primitive = pset.get_terminal(data['name'])
        else:
            primitive = pset.get_function(data['name'])
        
        children = [
            cls.from_dict(child_data, pset)
            for child_data in data['children']
        ]
        
        return cls(primitive, children)


class FactorExpression:
    """
    因子表达式
    
    封装表达式树，提供便捷的操作接口。
    
    Example:
        expr = FactorExpression(pset)
        expr.random_generate(max_depth=5)
        factor_values = expr.evaluate(data)
        print(expr)  # rank(ts_mean(close, 20))
    """
    
    def __init__(
        self,
        pset: PrimitiveSet,
        root: ExpressionNode = None,
    ):
        """
        初始化因子表达式
        
        Args:
            pset: 基元集合
            root: 根节点
        """
        self.pset = pset
        self.root = root
        self._fitness: Optional[float] = None
        self._metadata: Dict[str, Any] = {}
    
    def random_generate(
        self,
        max_depth: int = 5,
        method: str = 'grow',
    ) -> 'FactorExpression':
        """
        随机生成表达式
        
        Args:
            max_depth: 最大深度
            method: 生成方法 ('grow' 或 'full')
                - grow: 每个节点随机选择函数或终端
                - full: 非叶节点必须是函数
        
        Returns:
            self（支持链式调用）
        """
        self.root = self._generate_tree(max_depth, method)
        return self
    
    def _generate_tree(
        self,
        max_depth: int,
        method: str,
    ) -> ExpressionNode:
        """递归生成表达式树"""
        if max_depth == 0:
            terminal = self.pset.get_random_terminal()
            return ExpressionNode(terminal)
        
        if method == 'full':
            primitive = self.pset.get_random_function()
        else:
            if np.random.random() < 0.3:
                primitive = self.pset.get_random_terminal()
            else:
                primitive = self.pset.get_random_function()
        
        if primitive.ptype == PrimitiveType.TERMINAL:
            return ExpressionNode(primitive)
        
        children = []
        for _ in range(primitive.arity):
            child = self._generate_tree(max_depth - 1, method)
            children.append(child)
        
        return ExpressionNode(primitive, children)
    
    def evaluate(self, data: Dict[str, pd.DataFrame]) -> Union[pd.DataFrame, pd.Series]:
        """
        计算因子值
        
        Args:
            data: 数据字典
        
        Returns:
            因子值
        """
        if self.root is None:
            raise ValueError("表达式未初始化")
        return self.root.evaluate(data)
    
    def depth(self) -> int:
        """获取表达式深度"""
        return self.root.depth() if self.root else 0
    
    def size(self) -> int:
        """获取表达式节点数"""
        return self.root.size() if self.root else 0
    
    def get_all_nodes(self) -> List[ExpressionNode]:
        """获取所有节点"""
        return self.root.get_all_nodes() if self.root else []
    
    def get_function_nodes(self) -> List[ExpressionNode]:
        """获取所有函数节点"""
        return self.root.get_function_nodes() if self.root else []
    
    def get_terminal_nodes(self) -> List[ExpressionNode]:
        """获取所有终端节点"""
        return self.root.get_terminal_nodes() if self.root else []
    
    def copy(self) -> 'FactorExpression':
        """深拷贝"""
        new_expr = FactorExpression(self.pset)
        new_expr.root = self.root.copy() if self.root else None
        new_expr._fitness = self._fitness
        new_expr._metadata = copy.deepcopy(self._metadata)
        return new_expr
    
    @property
    def fitness(self) -> Optional[float]:
        """获取适应度"""
        return self._fitness
    
    @fitness.setter
    def fitness(self, value: float):
        """设置适应度"""
        self._fitness = value
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """获取元数据"""
        return self._metadata
    
    def __repr__(self) -> str:
        if self.root is None:
            return "FactorExpression(empty)"
        return f"FactorExpression({self.root})"
    
    def __str__(self) -> str:
        if self.root is None:
            return ""
        return self.root.to_string()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'expression': str(self),
            'depth': self.depth(),
            'size': self.size(),
            'fitness': self._fitness,
            'metadata': self._metadata,
            'tree': self.root.to_dict() if self.root else None,
        }
    
    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        pset: PrimitiveSet,
    ) -> 'FactorExpression':
        """从字典创建"""
        expr = cls(pset)
        if data.get('tree'):
            expr.root = ExpressionNode.from_dict(data['tree'], pset)
        expr._fitness = data.get('fitness')
        expr._metadata = data.get('metadata', {})
        return expr
    
    def __lt__(self, other: 'FactorExpression') -> bool:
        """比较适应度（用于排序）"""
        if self._fitness is None:
            return False
        if other._fitness is None:
            return True
        return self._fitness < other._fitness
    
    def __eq__(self, other: object) -> bool:
        """判断相等"""
        if not isinstance(other, FactorExpression):
            return False
        return str(self) == str(other)
    
    def __hash__(self) -> int:
        """哈希值"""
        return hash(str(self))


def create_random_expression(
    pset: PrimitiveSet,
    max_depth: int = 5,
    method: str = 'grow',
) -> FactorExpression:
    """
    创建随机因子表达式
    
    Args:
        pset: 基元集合
        max_depth: 最大深度
        method: 生成方法
    
    Returns:
        因子表达式
    """
    expr = FactorExpression(pset)
    expr.random_generate(max_depth, method)
    return expr
