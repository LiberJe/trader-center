"""
因子注册器

管理所有因子的注册、获取和发现。
"""

from typing import Dict, List, Optional, Type
import logging
from .base import BaseFactor


logger = logging.getLogger(__name__)


class FactorRegistry:
    """
    因子注册器
    
    单例模式，管理所有注册的因子。
    
    Example:
        registry = FactorRegistry()
        
        # 注册因子
        registry.register(MomentumFactor())
        
        # 获取因子
        factor = registry.get('momentum')
        
        # 列出所有因子
        factors = registry.list_factors()
    """
    
    _instance: Optional['FactorRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factors: Dict[str, BaseFactor] = {}
            cls._instance._factor_classes: Dict[str, Type[BaseFactor]] = {}
        return cls._instance
    
    def register(self, factor: BaseFactor) -> None:
        """
        注册因子实例
        
        Args:
            factor: 因子实例
        
        Raises:
            ValueError: 如果因子名称已存在
        """
        if factor.name in self._factors:
            logger.warning(
                f"因子 '{factor.name}' 已存在，将被覆盖。"
                f"旧因子: {self._factors[factor.name]}, "
                f"新因子: {factor}"
            )
        
        self._factors[factor.name] = factor
        logger.info(f"注册因子: {factor.name} ({factor.category})")
    
    def register_class(self, factor_class: Type[BaseFactor], **params) -> None:
        """
        注册因子类
        
        Args:
            factor_class: 因子类
            **params: 因子参数
        """
        factor = factor_class(**params)
        self.register(factor)
        self._factor_classes[factor.name] = factor_class
    
    def get(self, name: str) -> BaseFactor:
        """
        获取因子
        
        Args:
            name: 因子名称
        
        Returns:
            因子实例
        
        Raises:
            KeyError: 如果因子不存在
        """
        if name not in self._factors:
            raise KeyError(
                f"因子 '{name}' 未注册。"
                f"可用因子: {list(self._factors.keys())}"
            )
        return self._factors[name]
    
    def get_class(self, name: str) -> Type[BaseFactor]:
        """
        获取因子类
        
        Args:
            name: 因子名称
        
        Returns:
            因子类
        
        Raises:
            KeyError: 如果因子不存在
        """
        if name not in self._factor_classes:
            raise KeyError(f"因子类 '{name}' 未注册。")
        return self._factor_classes[name]
    
    def list_factors(self, category: Optional[str] = None) -> List[str]:
        """
        列出所有因子
        
        Args:
            category: 可选，按类别筛选 (technical/fundamental/alternative)
        
        Returns:
            因子名称列表
        """
        if category is None:
            return list(self._factors.keys())
        
        return [
            name for name, factor in self._factors.items()
            if factor.category == category
        ]
    
    def list_factors_by_category(self) -> Dict[str, List[str]]:
        """
        按类别列出所有因子
        
        Returns:
            类别到因子列表的映射
        """
        result = {}
        for name, factor in self._factors.items():
            if factor.category not in result:
                result[factor.category] = []
            result[factor.category].append(name)
        return result
    
    def get_metadata(self, name: str) -> dict:
        """
        获取因子元数据
        
        Args:
            name: 因子名称
        
        Returns:
            因子元数据字典
        """
        factor = self.get(name)
        return factor.get_metadata()
    
    def get_all_metadata(self) -> List[dict]:
        """
        获取所有因子的元数据
        
        Returns:
            所有因子元数据列表
        """
        return [factor.get_metadata() for factor in self._factors.values()]
    
    def exists(self, name: str) -> bool:
        """
        检查因子是否存在
        
        Args:
            name: 因子名称
        
        Returns:
            True 如果因子已注册
        """
        return name in self._factors
    
    def unregister(self, name: str) -> None:
        """
        注销因子
        
        Args:
            name: 因子名称
        
        Raises:
            KeyError: 如果因子不存在
        """
        if name not in self._factors:
            raise KeyError(f"因子 '{name}' 未注册。")
        
        del self._factors[name]
        if name in self._factor_classes:
            del self._factor_classes[name]
        
        logger.info(f"注销因子: {name}")
    
    def clear(self) -> None:
        """清空所有注册的因子"""
        self._factors.clear()
        self._factor_classes.clear()
        logger.info("清空所有因子注册")
    
    def __len__(self) -> int:
        return len(self._factors)
    
    def __contains__(self, name: str) -> bool:
        return self.exists(name)
    
    def __repr__(self) -> str:
        return f"FactorRegistry(factors={len(self._factors)})"


def register_factor(factor: BaseFactor) -> None:
    """
    注册因子（便捷函数）
    
    Args:
        factor: 因子实例
    """
    registry = FactorRegistry()
    registry.register(factor)


def get_factor(name: str) -> BaseFactor:
    """
    获取因子（便捷函数）
    
    Args:
        name: 因子名称
    
    Returns:
        因子实例
    """
    registry = FactorRegistry()
    return registry.get(name)


def list_factors(category: Optional[str] = None) -> List[str]:
    """
    列出所有因子（便捷函数）
    
    Args:
        category: 可选，按类别筛选
    
    Returns:
        因子名称列表
    """
    registry = FactorRegistry()
    return registry.list_factors(category)
