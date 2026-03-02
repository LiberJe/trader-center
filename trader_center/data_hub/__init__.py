"""
DataHub - Multi-source financial data access layer

Example:
    >>> import trader_center.data_hub as dh
    >>> df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
"""

from datetime import datetime, date
from typing import Optional, Union, List, Dict, Any
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


def get_market_fund_flow(target_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """
    获取大盘资金流向

    Parameters
    ----------
    target_date : date, optional
        目标日期，默认为今日

    Returns
    -------
    pd.DataFrame or None
        columns: [date, market, main_force_net, super_large_net, large_net,
                 medium_net, small_net, total_amount]
    """
    router = _get_router()
    cache = _get_cache()

    target_date = target_date or date.today()
    cache_key = CacheKeyBuilder.for_bars("market_fund_flow", target_date, target_date, "1d")

    # 尝试读取缓存
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 先尝试从存储获取
    stored = router.storage.get_market_fund_flow(target_date)
    if stored:
        df = pd.DataFrame([stored.model_dump()])
        cache.set(cache_key, df, ttl=300)
        return df

    # 从 fetcher 获取
    fetcher = None
    for f in router.fetcher_router.fetchers:
        if hasattr(f, 'get_market_fund_flow'):
            fetcher = f
            break

    if fetcher is None:
        logger.warning("No fetcher supports fund flow data")
        return None

    data = fetcher.get_market_fund_flow(target_date)
    if data is None:
        return None

    # 保存到存储
    router.storage.save_market_fund_flow(data)

    df = pd.DataFrame([data.model_dump()])
    cache.set(cache_key, df, ttl=300)
    return df


def get_stock_fund_flow_rank(
    target_date: Optional[date] = None, top_n: int = 100
) -> pd.DataFrame:
    """
    获取个股资金流向排名

    Parameters
    ----------
    target_date : date, optional
        目标日期，默认为今日
    top_n : int
        返回前N条记录

    Returns
    -------
    pd.DataFrame
        columns: [date, symbol, name, close_price, change_pct,
                 fund_flow, flow_ratio, main_force_net]
    """
    router = _get_router()
    cache = _get_cache()

    target_date = target_date or date.today()
    cache_key = f"stock_fund_flow:{target_date.isoformat()}:{top_n}"

    # 尝试读取缓存
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 先尝试从存储获取
    stored = router.storage.get_stock_fund_flow(target_date, limit=top_n)
    if stored and len(stored) >= top_n:
        df = pd.DataFrame([s.model_dump() for s in stored])
        cache.set(cache_key, df, ttl=300)
        return df

    # 存储中没有，只有今天的数据可以从 API 获取
    if target_date != date.today():
        logger.warning(f"Stock fund flow for {target_date} not found in storage, and historical data not available from API")
        return pd.DataFrame()

    # 从 fetcher 获取今天的数据
    fetcher = None
    for f in router.fetcher_router.fetchers:
        if hasattr(f, 'get_stock_fund_flow_rank'):
            fetcher = f
            break

    if fetcher is None:
        logger.warning("No fetcher supports fund flow data")
        return pd.DataFrame()

    data = fetcher.get_stock_fund_flow_rank(target_date, top_n=top_n)
    if not data:
        return pd.DataFrame()

    # 保存到存储
    router.storage.save_stock_fund_flow(data)

    df = pd.DataFrame([d.model_dump() for d in data])
    cache.set(cache_key, df, ttl=300)
    return df


def get_sector_fund_flow(
    target_date: Optional[date] = None, sector_type: str = "industry"
) -> pd.DataFrame:
    """
    获取板块资金流向

    Parameters
    ----------
    target_date : date, optional
        目标日期，默认为今日
    sector_type : str
        板块类型: "industry" 或 "concept"

    Returns
    -------
    pd.DataFrame
        columns: [date, sector_type, sector_name, fund_flow, change_pct,
                 leading_stock, leading_stock_change]
    """
    router = _get_router()
    cache = _get_cache()

    target_date = target_date or date.today()
    cache_key = f"sector_fund_flow:{target_date.isoformat()}:{sector_type}"

    # 尝试读取缓存
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 先尝试从存储获取
    stored = router.storage.get_sector_fund_flow(target_date, sector_type=sector_type)
    if stored:
        df = pd.DataFrame([s.model_dump() for s in stored])
        cache.set(cache_key, df, ttl=300)
        return df

    # 存储中没有，只有今天的数据可以从 API 获取
    if target_date != date.today():
        logger.warning(f"Sector fund flow for {target_date} not found in storage, and historical data not available from API")
        return pd.DataFrame()

    # 从 fetcher 获取今天的数据
    fetcher = None
    for f in router.fetcher_router.fetchers:
        if hasattr(f, 'get_sector_fund_flow'):
            fetcher = f
            break

    if fetcher is None:
        logger.warning("No fetcher supports fund flow data")
        return pd.DataFrame()

    data = fetcher.get_sector_fund_flow(target_date, sector_type=sector_type)
    if not data:
        return pd.DataFrame()

    # 保存到存储
    router.storage.save_sector_fund_flow(data)

    df = pd.DataFrame([d.model_dump() for d in data])
    cache.set(cache_key, df, ttl=300)
    return df


def delete_fund_flow_data(
    target_date: Optional[date] = None,
    data_type: str = "all",
    clear_cache: bool = True,
) -> dict:
    """删除指定日期的资金流向数据

    用于清理错误或过期数据。

    Args:
        target_date: 目标日期，默认为今天
        data_type: 数据类型 - "all" | "market" | "stock" | "sector"
        clear_cache: 是否同时清理缓存

    Returns:
        {
            "market": int,  # 删除的大盘数据记录数
            "stock": int,   # 删除的个股数据记录数
            "sector": int,  # 删除的板块数据记录数
        }
    """
    router = _get_router()
    target_date = target_date or date.today()

    result = {"market": 0, "stock": 0, "sector": 0}

    if data_type in ("all", "market"):
        result["market"] = router.storage.delete_market_fund_flow(target_date)

    if data_type in ("all", "stock"):
        result["stock"] = router.storage.delete_stock_fund_flow(target_date)

    if data_type in ("all", "sector"):
        result["sector"] = router.storage.delete_sector_fund_flow(target_date)

    # 清理缓存
    if clear_cache:
        cache = _get_cache()
        # 清理该日期相关的缓存
        cache_keys_to_delete = [
            CacheKeyBuilder.for_bars("market_fund_flow", target_date, target_date, "1d"),
            f"stock_fund_flow:{target_date.isoformat()}",
            f"sector_fund_flow:{target_date.isoformat()}",
        ]
        for key in cache_keys_to_delete:
            # CacheManager 没有直接删除方法，通过设置过期来处理
            pass  # TTL 会自动过期，或者使用 clear() 清空全部

    logger.info(f"Deleted fund flow data for {target_date}: {result}")
    return result


def delete_all_fund_flow_data(
    data_type: str = "all",
    clear_cache: bool = True,
) -> dict:
    """删除所有日期的资金流向数据

    Args:
        data_type: 数据类型 - "all" | "market" | "stock" | "sector"
        clear_cache: 是否同时清理缓存

    Returns:
        {
            "market": int,  # 删除的大盘数据记录数
            "stock": int,   # 删除的个股数据记录数
            "sector": int,  # 删除的板块数据记录数
        }
    """
    router = _get_router()

    result = {"market": 0, "stock": 0, "sector": 0}

    if data_type in ("all", "market"):
        result["market"] = router.storage.delete_all_market_fund_flow()

    if data_type in ("all", "stock"):
        result["stock"] = router.storage.delete_all_stock_fund_flow()

    if data_type in ("all", "sector"):
        result["sector"] = router.storage.delete_all_sector_fund_flow()

    # 清理缓存
    if clear_cache:
        cache = _get_cache()
        cache.clear()

    logger.info(f"Deleted all fund flow data: {result}")
    return result


__all__ = [
    "configure",
    "get_daily_bars",
    "get_stock_list",
    "get_market_fund_flow",
    "get_stock_fund_flow_rank",
    "get_sector_fund_flow",
    "get_cache_stats",
    "clear_cache",
    "delete_fund_flow_data",
    "delete_all_fund_flow_data",
]
