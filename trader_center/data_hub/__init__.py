"""
DataHub - Multi-source financial data access layer

Example:
    >>> import trader_center.data_hub as dh
    >>> df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
"""

from datetime import datetime, date
from typing import Optional, Union, List
import pandas as pd
import logging

from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.router import DataRouter
from trader_center.data_hub.cache.manager import CacheManager
from trader_center.data_hub.cache.key_builder import CacheKeyBuilder

# 全局实例
_router: Optional[DataRouter] = None
_cache: Optional[CacheManager] = None
_config: Optional[DataHubConfig] = None

logger = logging.getLogger(__name__)


def _get_router() -> DataRouter:
    """获取或初始化全局 Router"""
    global _router
    if _router is None:
        _init_default()
    return _router


def _get_cache() -> CacheManager:
    """获取或初始化全局 Cache"""
    global _cache
    if _cache is None:
        _cache = CacheManager(max_size=1000)
    return _cache


def _init_default():
    """初始化默认配置"""
    global _router, _config

    _config = DataHubConfig()
    _router = DataRouter(_config)

    # 尝试注册 akshare
    try:
        from trader_center.data_hub.fetchers.akshare_fetcher import AkshareFetcher

        _router.register_fetcher(AkshareFetcher())
        logger.info("Akshare fetcher registered automatically")
    except ImportError:
        logger.warning("akshare not installed, skipping auto-registration")


def configure(
    data_dir: Optional[str] = None,
    cache_size: int = 1000,
):
    """
    配置 DataHub

    Parameters
    ----------
    data_dir : str, optional
        数据存储目录，默认 ~/.trader_center/data/
    cache_size : int
        内存缓存大小
    """
    global _router, _cache, _config

    _config = DataHubConfig(data_dir=data_dir)
    _router = DataRouter(_config)
    _cache = CacheManager(max_size=cache_size)

    # 重新注册默认 fetcher
    try:
        from trader_center.data_hub.fetchers.akshare_fetcher import AkshareFetcher

        _router.register_fetcher(AkshareFetcher())
    except ImportError:
        pass


def get_daily_bars(
    symbol: str,
    start: Union[str, datetime, date],
    end: Union[str, datetime, date],
    adjust: str = "qfq",
) -> pd.DataFrame:
    """
    获取日线数据

    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ", "600000.SH"
    start : str or datetime
        开始日期，格式 "YYYY-MM-DD"
    end : str or datetime
        结束日期
    adjust : str
        复权方式: "qfq"(前复权), "hfq"(后复权), None(不复权)

    Returns
    -------
    pd.DataFrame
        columns: [timestamp, open, high, low, close, volume, amount]

    Examples
    --------
    >>> df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
    """
    router = _get_router()
    cache = _get_cache()

    # 解析日期
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)

    # 构建缓存键
    cache_key = CacheKeyBuilder.for_bars(symbol, start_dt, end_dt, "1d")

    # 尝试读取缓存
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 从 router 获取
    df = router.get_bars(symbol, start_dt, end_dt, "1d")

    # 写入缓存（5分钟 TTL）
    if not df.empty:
        cache.set(cache_key, df, ttl=300)

    return df


def get_stock_list(exchange: Optional[str] = None) -> pd.DataFrame:
    """
    获取股票列表

    Parameters
    ----------
    exchange : str, optional
        交易所过滤: "SZ", "SH", "BJ"

    Returns
    -------
    pd.DataFrame
        columns: [symbol, name, exchange, type, list_date, industry]
    """
    router = _get_router()
    cache = _get_cache()

    cache_key = CacheKeyBuilder.for_symbols(exchange)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    symbols = router.get_symbols(exchange)
    df = pd.DataFrame([s.model_dump() for s in symbols])

    if not df.empty:
        cache.set(cache_key, df, ttl=86400)  # 1天 TTL

    return df


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    cache = _get_cache()
    return cache.get_stats()


def clear_cache():
    """清空内存缓存"""
    cache = _get_cache()
    cache.clear()


__all__ = [
    "configure",
    "get_daily_bars",
    "get_stock_list",
    "get_cache_stats",
    "clear_cache",
]
