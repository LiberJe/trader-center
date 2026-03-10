"""
因子计算引擎

提供因子计算、批量计算和缓存功能。
"""

from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial

from trader_center.factor.library import FactorRegistry


logger = logging.getLogger(__name__)


class FactorEngine:
    """
    因子计算引擎
    
    负责因子的计算、缓存和批量处理。
    
    Example:
        engine = FactorEngine()
        
        # 计算单个因子
        factor_values = engine.compute_factor('momentum', data)
        
        # 批量计算因子
        factor_df = engine.compute_factors(['momentum', 'rsi'], data)
    """
    
    def __init__(
        self,
        registry: Optional[FactorRegistry] = None,
        cache_size: int = 100,
        enable_cache: bool = True,
        n_workers: int = 4,
    ):
        """
        初始化因子计算引擎
        
        Args:
            registry: 因子注册器实例，默认使用全局单例
            cache_size: 缓存大小
            enable_cache: 是否启用缓存
            n_workers: 并行计算的worker数量
        """
        self.registry = registry or FactorRegistry()
        self._cache: Dict[str, pd.Series] = {}
        self._cache_size = cache_size
        self._enable_cache = enable_cache
        self._n_workers = n_workers
        self._cache_order: List[str] = []
    
    def compute_factor(
        self,
        factor_name: str,
        data: pd.DataFrame,
        use_cache: bool = True,
        **params,
    ) -> pd.Series:
        """
        计算单个因子
        
        Args:
            factor_name: 因子名称
            data: 包含OHLCV等数据的DataFrame
            use_cache: 是否使用缓存
            **params: 因子参数（会覆盖注册时的参数）
        
        Returns:
            因子值Series，index为日期
        
        Raises:
            KeyError: 如果因子未注册
            ValueError: 如果数据格式不正确
        """
        factor = self.registry.get(factor_name)
        
        if params:
            factor.set_params(**params)
        
        cache_key = self._get_cache_key(factor_name, data, params if params else factor.get_params())
        
        if use_cache and self._enable_cache and cache_key in self._cache:
            logger.debug(f"从缓存获取因子: {factor_name}")
            return self._cache[cache_key].copy()
        
        factor.validate_data(data)
        
        logger.debug(f"计算因子: {factor_name}")
        result = factor.compute(data)
        
        if use_cache and self._enable_cache:
            self._add_to_cache(cache_key, result)
        
        return result
    
    def compute_factors(
        self,
        factor_names: List[str],
        data: pd.DataFrame,
        parallel: bool = False,
        use_cache: bool = True,
        params_dict: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> pd.DataFrame:
        """
        批量计算因子
        
        Args:
            factor_names: 因子名称列表
            data: 包含OHLCV等数据的DataFrame
            parallel: 是否并行计算
            use_cache: 是否使用缓存
            params_dict: 因子参数字典 {factor_name: {param: value}}
        
        Returns:
            因子值DataFrame，每列为一个因子
        
        Example:
            factor_df = engine.compute_factors(
                ['momentum', 'rsi'],
                data,
                parallel=True,
                params_dict={'momentum': {'period': 20}}
            )
        """
        params_dict = params_dict or {}
        
        if parallel and len(factor_names) > 1:
            return self._compute_parallel(factor_names, data, use_cache, params_dict)
        else:
            return self._compute_sequential(factor_names, data, use_cache, params_dict)
    
    def _compute_sequential(
        self,
        factor_names: List[str],
        data: pd.DataFrame,
        use_cache: bool,
        params_dict: Dict[str, Dict[str, Any]],
    ) -> pd.DataFrame:
        """顺序计算因子"""
        results = {}
        for name in factor_names:
            params = params_dict.get(name, {})
            results[name] = self.compute_factor(name, data, use_cache, **params)
        
        return pd.DataFrame(results)
    
    def _compute_parallel(
        self,
        factor_names: List[str],
        data: pd.DataFrame,
        use_cache: bool,
        params_dict: Dict[str, Dict[str, Any]],
    ) -> pd.DataFrame:
        """并行计算因子"""
        compute_func = partial(
            self._compute_single_for_parallel,
            data=data,
            use_cache=use_cache,
            params_dict=params_dict,
        )
        
        with ThreadPoolExecutor(max_workers=self._n_workers) as executor:
            results_list = list(executor.map(compute_func, factor_names))
        
        results = dict(zip(factor_names, results_list))
        return pd.DataFrame(results)
    
    def _compute_single_for_parallel(
        self,
        factor_name: str,
        data: pd.DataFrame,
        use_cache: bool,
        params_dict: Dict[str, Dict[str, Any]],
    ) -> pd.Series:
        """并行计算单个因子的辅助函数"""
        params = params_dict.get(factor_name, {})
        return self.compute_factor(factor_name, data, use_cache, **params)
    
    def compute_for_symbols(
        self,
        factor_name: str,
        data_dict: Dict[str, pd.DataFrame],
        parallel: bool = False,
        use_cache: bool = True,
        **params,
    ) -> pd.DataFrame:
        """
        为多个股票计算因子
        
        Args:
            factor_name: 因子名称
            data_dict: 股票代码到数据的映射 {symbol: DataFrame}
            parallel: 是否并行计算
            use_cache: 是否使用缓存
            **params: 因子参数
        
        Returns:
            因子值DataFrame，index为日期，columns为股票代码
        """
        if parallel and len(data_dict) > 1:
            return self._compute_for_symbols_parallel(
                factor_name, data_dict, use_cache, params
            )
        else:
            return self._compute_for_symbols_sequential(
                factor_name, data_dict, use_cache, params
            )
    
    def _compute_for_symbols_sequential(
        self,
        factor_name: str,
        data_dict: Dict[str, pd.DataFrame],
        use_cache: bool,
        params: Dict[str, Any],
    ) -> pd.DataFrame:
        """顺序为多个股票计算因子"""
        results = {}
        for symbol, data in data_dict.items():
            try:
                results[symbol] = self.compute_factor(
                    factor_name, data, use_cache, **params
                )
            except Exception as e:
                logger.error(f"计算因子 {factor_name} 失败 (symbol={symbol}): {e}")
                results[symbol] = pd.Series(dtype=float)
        
        return pd.DataFrame(results)
    
    def _compute_for_symbols_parallel(
        self,
        factor_name: str,
        data_dict: Dict[str, pd.DataFrame],
        use_cache: bool,
        params: Dict[str, Any],
    ) -> pd.DataFrame:
        """并行为多个股票计算因子"""
        compute_func = partial(
            self.compute_factor,
            factor_name=factor_name,
            use_cache=use_cache,
            **params,
        )
        
        with ThreadPoolExecutor(max_workers=self._n_workers) as executor:
            symbols = list(data_dict.keys())
            data_list = [data_dict[s] for s in symbols]
            results_list = list(executor.map(compute_func, data_list))
        
        results = dict(zip(symbols, results_list))
        return pd.DataFrame(results)
    
    def _get_cache_key(
        self,
        factor_name: str,
        data: pd.DataFrame,
        params: Dict[str, Any],
    ) -> str:
        """
        生成缓存键
        
        Args:
            factor_name: 因子名称
            data: 数据DataFrame
            params: 因子参数
        
        Returns:
            缓存键字符串
        """
        data_hash = self._hash_data(data)
        params_str = str(sorted(params.items()))
        key_str = f"{factor_name}_{data_hash}_{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _hash_data(self, data: pd.DataFrame) -> str:
        """
        计算数据的哈希值
        
        Args:
            data: 数据DataFrame
        
        Returns:
            哈希字符串
        """
        if len(data) == 0:
            return "empty"
        
        data_str = f"{data.index[0]}_{data.index[-1]}_{len(data)}_{data.columns.tolist()}"
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _add_to_cache(self, key: str, value: pd.Series) -> None:
        """
        添加到缓存
        
        Args:
            key: 缓存键
            value: 因子值
        """
        if len(self._cache) >= self._cache_size:
            oldest_key = self._cache_order.pop(0)
            del self._cache[oldest_key]
        
        self._cache[key] = value.copy()
        self._cache_order.append(key)
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._cache_order.clear()
        logger.info("因子缓存已清空")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        return {
            'cache_size': len(self._cache),
            'max_cache_size': self._cache_size,
            'enable_cache': self._enable_cache,
        }
    
    def __repr__(self) -> str:
        return (
            f"FactorEngine("
            f"registry={len(self.registry)}, "
            f"cache={len(self._cache)}/{self._cache_size})"
        )
