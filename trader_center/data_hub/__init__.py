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


def get_financial_indicator(
    symbol: str,
) -> pd.DataFrame:
    """
    获取个股财务指标数据
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ", "600000.SH"
    
    Returns
    -------
    pd.DataFrame
        财务指标数据，包含:
        - date: 报告日期
        - pe_ratio: 市盈率
        - pb_ratio: 市净率
        - ps_ratio: 市销率
        - market_cap: 总市值
        - revenue: 营业收入
        - net_income: 净利润
        - total_assets: 总资产
        - total_equity: 净资产
        - roe: 净资产收益率
        - debt_ratio: 资产负债率
        等字段
    
    Examples
    --------
    >>> df = dh.get_financial_indicator("000001.SZ")
    """
    cache = _get_cache()
    
    cache_key = f"financial_indicator:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df = ak.stock_financial_analysis_indicator(symbol=code)
        
        if df.empty:
            df = get_profit_sheet(symbol)
        
        if df.empty:
            return pd.DataFrame()
        
        df = _normalize_financial_df(df, symbol)
        
        cache.set(cache_key, df, ttl=3600)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取财务指标失败 {symbol}: {e}")
        return pd.DataFrame()


def get_balance_sheet(
    symbol: str,
) -> pd.DataFrame:
    """
    获取个股资产负债表数据
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ"
    
    Returns
    -------
    pd.DataFrame
        资产负债表数据，包含:
        - date: 报告日期
        - total_assets: 总资产
        - total_liabilities: 总负债
        - total_equity: 所有者权益
        - current_assets: 流动资产
        - current_liabilities: 流动负债
        - cash: 货币资金
        - inventory: 存货
    
    Examples
    --------
    >>> df = dh.get_balance_sheet("000001.SZ")
    """
    cache = _get_cache()
    
    cache_key = f"balance_sheet:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df = ak.stock_financial_report_sina(stock=code, symbol='资产负债表')
        
        if df.empty:
            return pd.DataFrame()
        
        df = _normalize_financial_df(df, symbol)
        
        cache.set(cache_key, df, ttl=3600)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取资产负债表失败 {symbol}: {e}")
        return pd.DataFrame()


def get_profit_sheet(
    symbol: str,
) -> pd.DataFrame:
    """
    获取个股利润表数据
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ"
    
    Returns
    -------
    pd.DataFrame
        利润表数据，包含:
        - date: 报告日期
        - revenue: 营业收入
        - cost_of_goods: 营业成本
        - net_income: 净利润
        - eps: 每股收益
        - pe_ratio: 市盈率
        - pb_ratio: 市净率
        - ps_ratio: 市销率
        - gross_margin: 毛利率
        - net_margin: 净利率
    
    Examples
    --------
    >>> df = dh.get_profit_sheet("000001.SZ")
    """
    cache = _get_cache()
    
    cache_key = f"profit_sheet:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df = ak.stock_financial_report_sina(stock=code, symbol='利润表')
        
        if df.empty:
            return pd.DataFrame()
        
        df = _normalize_financial_df(df, symbol)
        
        cache.set(cache_key, df, ttl=3600)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取利润表失败 {symbol}: {e}")
        return pd.DataFrame()


def get_cashflow_sheet(
    symbol: str,
) -> pd.DataFrame:
    """
    获取个股现金流量表数据
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ"
    
    Returns
    -------
    pd.DataFrame
        现金流量表数据，包含:
        - date: 报告日期
        - operating_cash_flow: 经营活动现金流量净额
        - investing_cash_flow: 投资活动现金流量净额
        - financing_cash_flow: 筹资活动现金流量净额
        - free_cash_flow: 自由现金流
    
    Examples
    --------
    >>> df = dh.get_cashflow_sheet("000001.SZ")
    """
    cache = _get_cache()
    
    cache_key = f"cashflow_sheet:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df = ak.stock_financial_report_sina(stock=code, symbol='现金流量表')
        
        if df.empty:
            return pd.DataFrame()
        
        df = _normalize_financial_df(df, symbol)
        
        cache.set(cache_key, df, ttl=3600)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取现金流量表失败 {symbol}: {e}")
        return pd.DataFrame()


def get_fundamental_data(
    symbol: str,
) -> pd.DataFrame:
    """
    综合获取个股基本面数据
    
    合并资产负债表、利润表、现金流量表数据，返回完整的因子计算所需数据。
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ"
    
    Returns
    -------
    pd.DataFrame
        综合基本面数据，包含:
        - date: 报告日期
        - pe_ratio: 市盈率
        - pb_ratio: 市净率
        - ps_ratio: 市销率
        - revenue: 营业收入
        - net_income: 净利润
        - total_assets: 总资产
        - total_equity: 所有者权益
        - total_liabilities: 总负债
        - current_assets: 流动资产
        - current_liabilities: 流动负债
        - operating_cash_flow: 经营现金流
        - cash: 货币资金
        - inventory: 存货
        - eps: 每股收益
        - gross_margin: 毛利率
        - net_margin: 净利率
        等字段
    
    Examples
    --------
    >>> df = dh.get_fundamental_data("000001.SZ")
    """
    cache = _get_cache()
    
    cache_key = f"fundamental_data:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df_ths = ak.stock_financial_abstract_ths(symbol=code, indicator='按报告期')
        
        if df_ths.empty:
            return pd.DataFrame()
        
        column_mapping = {
            '报告期': 'date',
            '净利润同比增长率': 'net_income_growth',
            '营业总收入同比增长率': 'revenue_growth',
            '净利润': 'net_income',
            '扣非净利润': 'net_income_deducted',
            '营业总收入': 'revenue',
            '基本每股收益': 'eps',
            '每股净资产': 'book_value_per_share',
            '每股资本公积金': 'capital_reserve_per_share',
            '每股未分配利润': 'retained_earnings_per_share',
            '每股经营现金流': 'ocf_per_share',
            '销售净利率': 'net_margin',
            '净资产收益率': 'roe',
            '净资产收益率-摊薄': 'roe_diluted',
            '营业周期': 'operating_cycle',
            '应收账款周转天数': 'ar_turnover_days',
            '流动比率': 'current_ratio',
            '速动比率': 'quick_ratio',
            '产权比率': 'equity_ratio',
            '资产负债率': 'debt_ratio',
            '销售毛利率': 'gross_margin',
        }
        
        rename_cols = {}
        used_targets = set()
        for col in df_ths.columns:
            col_str = str(col).strip()
            for cn_name, en_name in column_mapping.items():
                if cn_name == col_str or cn_name in col_str:
                    if en_name not in used_targets:
                        rename_cols[col] = en_name
                        used_targets.add(en_name)
                    break
        
        df = df_ths.rename(columns=rename_cols)
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()
        
        numeric_cols = ['net_income', 'revenue', 'eps', 'book_value_per_share', 
                        'ocf_per_share', 'net_margin', 'roe', 'current_ratio', 
                        'quick_ratio', 'debt_ratio', 'revenue_growth', 'net_income_growth']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('%', '').str.replace('万', 'e4').str.replace('亿', 'e8'), errors='coerce')
        
        try:
            df_balance = ak.stock_financial_report_sina(stock=code, symbol='资产负债表')
            if not df_balance.empty:
                balance_mapping = {
                    '报告日': 'date',
                    '资产总计': 'total_assets',
                    '负债合计': 'total_liabilities',
                    '所有者权益(或股东权益)合计': 'total_equity',
                    '流动资产合计': 'current_assets',
                    '流动负债合计': 'current_liabilities',
                    '货币资金': 'cash',
                    '存货': 'inventory',
                }
                
                balance_rename = {}
                for col in df_balance.columns:
                    col_str = str(col).strip()
                    for cn_name, en_name in balance_mapping.items():
                        if cn_name == col_str:
                            balance_rename[col] = en_name
                            break
                
                for col in df_balance.columns:
                    if col in balance_rename:
                        continue
                    col_str = str(col).strip()
                    for cn_name, en_name in balance_mapping.items():
                        if cn_name in col_str and en_name not in balance_rename.values():
                            balance_rename[col] = en_name
                            break
                
                df_balance = df_balance.rename(columns=balance_rename)
                
                if 'date' in df_balance.columns:
                    df_balance['date'] = pd.to_datetime(df_balance['date'], format='%Y%m%d')
                    df_balance = df_balance.set_index('date')
                    df_balance = df_balance.sort_index()
                    
                    for col in ['total_assets', 'total_liabilities', 'total_equity', 
                                'current_assets', 'current_liabilities', 'cash', 'inventory']:
                        if col in df_balance.columns:
                            df_balance[col] = pd.to_numeric(df_balance[col], errors='coerce')
                    
                    cols_to_merge = [c for c in ['total_assets', 'total_liabilities', 'total_equity',
                                                  'current_assets', 'current_liabilities', 'cash', 'inventory']
                                     if c in df_balance.columns]
                    if cols_to_merge:
                        df_balance_subset = df_balance[cols_to_merge].dropna(axis=1, how='all')
                        if not df_balance_subset.empty:
                            df = df.combine_first(df_balance_subset)
        except Exception as e:
            logger.debug(f"获取资产负债表数据失败 {symbol}: {e}")
        
        try:
            df_income = ak.stock_financial_report_sina(stock=code, symbol='利润表')
            if not df_income.empty:
                income_mapping = {
                    '报告日': 'date',
                    '营业成本': 'cost_of_goods',
                    '营业总成本': 'total_operating_cost',
                    '营业利润': 'operating_profit',
                    '利润总额': 'total_profit',
                }
                
                income_rename = {}
                for col in df_income.columns:
                    col_str = str(col).strip()
                    for cn_name, en_name in income_mapping.items():
                        if cn_name == col_str:
                            income_rename[col] = en_name
                            break
                
                for col in df_income.columns:
                    if col in income_rename:
                        continue
                    col_str = str(col).strip()
                    for cn_name, en_name in income_mapping.items():
                        if cn_name in col_str and en_name not in income_rename.values():
                            income_rename[col] = en_name
                            break
                
                df_income = df_income.rename(columns=income_rename)
                
                if 'date' in df_income.columns:
                    df_income['date'] = pd.to_datetime(df_income['date'], format='%Y%m%d')
                    df_income = df_income.set_index('date')
                    df_income = df_income.sort_index()
                    
                    for col in ['cost_of_goods', 'total_operating_cost', 'operating_profit', 'total_profit']:
                        if col in df_income.columns:
                            df_income[col] = pd.to_numeric(df_income[col], errors='coerce')
                    
                    cols_to_merge = [c for c in ['cost_of_goods', 'total_operating_cost', 
                                                  'operating_profit', 'total_profit']
                                     if c in df_income.columns]
                    if cols_to_merge:
                        df_income_subset = df_income[cols_to_merge].dropna(axis=1, how='all')
                        if not df_income_subset.empty:
                            df = df.combine_first(df_income_subset)
        except Exception as e:
            logger.debug(f"获取利润表数据失败 {symbol}: {e}")
        
        df['symbol'] = symbol
        
        cache.set(cache_key, df, ttl=3600)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取综合基本面数据失败 {symbol}: {e}")
        return pd.DataFrame()


def get_financial_report(
    symbol: str,
    report_type: str = "资产负债表",
) -> pd.DataFrame:
    """
    获取个股财务报表数据
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ"
    report_type : str
        报表类型: "资产负债表", "利润表", "现金流量表"
    
    Returns
    -------
    pd.DataFrame
        财务报表数据
    
    Examples
    --------
    >>> df = dh.get_financial_report("000001.SZ", "利润表")
    """
    router = _get_router()
    cache = _get_cache()
    
    cache_key = f"financial_report:{symbol}:{report_type}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df = ak.stock_financial_report_sina(stock=code, symbol=report_type)
        
        if df.empty:
            return pd.DataFrame()
        
        cache.set(cache_key, df, ttl=3600)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取财务报表失败 {symbol}: {e}")
        return pd.DataFrame()


def get_valuation_data(
    symbol: str,
) -> pd.DataFrame:
    """
    获取个股估值数据（PE、PB、PS等历史数据）
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ"
    
    Returns
    -------
    pd.DataFrame
        估值数据，包含:
        - date: 日期
        - pe_ratio: 市盈率
        - pb_ratio: 市净率
        - ps_ratio: 市销率
        - market_cap: 总市值
        - circulation_market_cap: 流通市值
    
    Examples
    --------
    >>> df = dh.get_valuation_data("000001.SZ")
    """
    cache = _get_cache()
    
    cache_key = f"valuation_data:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df = ak.stock_zh_valuation_baidu(symbol=code, indicator='总市值')
        
        if df.empty:
            return pd.DataFrame()
        
        df = df.rename(columns={
            'date': 'date',
            'value': 'market_cap',
        })
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        cache.set(cache_key, df, ttl=3600)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取估值数据失败 {symbol}: {e}")
        return pd.DataFrame()


def get_main_business(
    symbol: str,
) -> pd.DataFrame:
    """
    获取主营业务构成数据
    
    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ"
    
    Returns
    -------
    pd.DataFrame
        主营业务构成数据
    
    Examples
    --------
    >>> df = dh.get_main_business("000001.SZ")
    """
    cache = _get_cache()
    
    cache_key = f"main_business:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    code, exchange = _parse_symbol(symbol)
    
    try:
        import akshare as ak
        
        df = ak.stock_zygc_em(symbol=code)
        
        if df.empty:
            return pd.DataFrame()
        
        cache.set(cache_key, df, ttl=86400)
        
        return df
        
    except Exception as e:
        logger.warning(f"获取主营业务数据失败 {symbol}: {e}")
        return pd.DataFrame()


def _parse_symbol(symbol: str) -> tuple:
    """解析股票代码"""
    parts = symbol.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid symbol format: {symbol}, expected 'code.exchange'")
    return parts[0], parts[1]


def _normalize_financial_df(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """标准化财务数据DataFrame"""
    df = df.loc[:, ~df.columns.duplicated()]
    
    column_mapping = {
        '报告日': 'date',
        '日期': 'date',
        '报告期': 'date',
        '营业收入': 'revenue',
        '营业总收入': 'revenue',
        '利息收入': 'interest_income',
        '利息支出': 'interest_expense',
        '手续费及佣金净收入': 'commission_income',
        '营业支出': 'operating_expense',
        '营业成本': 'cost_of_goods',
        '营业利润': 'operating_profit',
        '利润总额': 'total_profit',
        '净利润': 'net_income',
        '归属于母公司的净利润': 'net_income',
        '归属于母公司所有者的净利润': 'net_income',
        '基本每股收益': 'eps',
        '稀释每股收益': 'eps_diluted',
        '资产总计': 'total_assets',
        '资产': 'total_assets',
        '总资产': 'total_assets',
        '负债合计': 'total_liabilities',
        '总负债': 'total_liabilities',
        '负债': 'total_liabilities',
        '所有者权益合计': 'total_equity',
        '净资产': 'total_equity',
        '所有者权益': 'total_equity',
        '归属于母公司股东的权益': 'total_equity',
        '股东权益': 'total_equity',
        '流动资产合计': 'current_assets',
        '流动资产': 'current_assets',
        '流动负债合计': 'current_liabilities',
        '流动负债': 'current_liabilities',
        '货币资金': 'cash',
        '现金及存放中央银行款项': 'cash',
        '存货': 'inventory',
        '应收账款': 'receivables',
        '应付账款': 'accounts_payable',
        '经营活动产生的现金流量净额': 'operating_cash_flow',
        '投资活动产生的现金流量净额': 'investing_cash_flow',
        '筹资活动产生的现金流量净额': 'financing_cash_flow',
        '净资产收益率': 'roe',
        'ROE': 'roe',
        '资产负债率': 'debt_ratio',
        '毛利率': 'gross_margin',
        '净利率': 'net_margin',
        '股本': 'shares_outstanding',
        '实收资本（或股本）': 'shares_outstanding',
    }
    
    rename_cols = {}
    used_targets = set()
    for col in df.columns:
        for cn_name, en_name in column_mapping.items():
            if cn_name == str(col) or cn_name in str(col):
                if en_name not in used_targets:
                    rename_cols[col] = en_name
                    used_targets.add(en_name)
                break
    
    df = df.rename(columns=rename_cols)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    
    df['symbol'] = symbol
    
    return df


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
    "get_financial_indicator",
    "get_financial_report",
    "get_valuation_data",
    "get_main_business",
    "get_balance_sheet",
    "get_profit_sheet",
    "get_cashflow_sheet",
    "get_fundamental_data",
]
