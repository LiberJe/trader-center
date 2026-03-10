"""
因子基类

定义因子的基本接口和通用功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


class BaseFactor(ABC):
    """
    因子基类
    
    所有因子必须继承此类并实现 compute 方法。
    
    Attributes:
        name: 因子名称（唯一标识）
        category: 因子类别（technical/fundamental/alternative）
        description: 因子描述
        params: 因子参数
        
    Example:
        class MomentumFactor(BaseFactor):
            name = "momentum"
            category = "technical"
            description = "价格动量因子"
            
            def __init__(self, period=20):
                super().__init__(period=period)
            
            def compute(self, data: pd.DataFrame) -> pd.Series:
                return data['close'].pct_change(self.params['period'])
    """
    
    def __init__(self, **params):
        """
        初始化因子
        
        Args:
            **params: 因子参数
        """
        self.params = params
        self._validate_params()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """因子名称（必须唯一）"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """因子类别: technical/fundamental/alternative"""
        pass
    
    @property
    def description(self) -> str:
        """因子描述"""
        return ""
    
    @property
    def author(self) -> str:
        """因子作者"""
        return ""
    
    @property
    def version(self) -> str:
        """因子版本"""
        return "1.0.0"
    
    @property
    def required_data(self) -> List[str]:
        """
        所需数据字段
        
        Returns:
            所需的数据字段列表，如 ['open', 'high', 'low', 'close', 'volume']
        """
        return ['open', 'high', 'low', 'close', 'volume']
    
    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算因子值
        
        Args:
            data: 包含OHLCV等数据的DataFrame，index为日期
        
        Returns:
            因子值Series，index为日期
        
        Raises:
            ValueError: 如果数据格式不正确
        """
        pass
    
    def _validate_params(self):
        """
        验证参数
        
        子类可以重写此方法实现参数验证逻辑。
        
        Raises:
            ValueError: 如果参数不合法
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证输入数据
        
        Args:
            data: 输入数据DataFrame
        
        Returns:
            True 如果数据包含所有必需字段
        
        Raises:
            ValueError: 如果缺少必需字段
        """
        missing = set(self.required_data) - set(data.columns)
        if missing:
            raise ValueError(
                f"数据缺少必需字段: {missing}. "
                f"当前字段: {list(data.columns)}"
            )
        return True
    
    def get_params(self) -> Dict[str, Any]:
        """
        获取因子参数
        
        Returns:
            因子参数字典
        """
        return self.params.copy()
    
    def set_params(self, **params):
        """
        设置因子参数
        
        Args:
            **params: 新的参数
        """
        self.params.update(params)
        self._validate_params()
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取因子元数据
        
        Returns:
            包含因子所有元数据的字典
        """
        return {
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'author': self.author,
            'version': self.version,
            'params': self.get_params(),
            'required_data': self.required_data,
        }
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"category='{self.category}', "
            f"params={self.params})"
        )
    
    def __str__(self) -> str:
        return f"{self.name} ({self.category})"
