import hashlib
from datetime import datetime
from typing import Optional


class CacheKeyBuilder:
    """缓存键生成器"""

    @staticmethod
    def for_bars(symbol: str, start: datetime, end: datetime, frequency: str) -> str:
        """K线数据缓存键"""
        params = f"{symbol}:{start.isoformat()}:{end.isoformat()}:{frequency}"
        hash_val = hashlib.md5(params.encode()).hexdigest()[:12]
        return f"bars:{symbol}:{frequency}:{hash_val}"

    @staticmethod
    def for_symbols(exchange: Optional[str] = None) -> str:
        """股票列表缓存键"""
        return f"symbols:{exchange or 'all'}"

    @staticmethod
    def for_data_range(symbol: str, frequency: str) -> str:
        """数据范围缓存键"""
        return f"range:{symbol}:{frequency}"
