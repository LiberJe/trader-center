from datetime import datetime
from typing import List, Optional, Tuple
import pandas as pd

from trader_center.data_hub.storage.base import Storage
from trader_center.data_hub.storage.sqlite_store import SQLiteStorage
from trader_center.data_hub.storage.parquet_store import ParquetStorage
from trader_center.data_hub.models import BarData, SymbolInfo
from trader_center.data_hub.config import DataHubConfig


class HybridStorage(Storage):
    """
    混合存储：SQLite 用于元数据，Parquet 用于K线数据
    """

    def __init__(self, config: DataHubConfig):
        self.sqlite = SQLiteStorage(config)
        self.parquet = ParquetStorage(config)

    def save_bars(self, bars: List[BarData]) -> None:
        """K线数据保存到 Parquet"""
        self.parquet.save_bars(bars)

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> pd.DataFrame:
        """从 Parquet 获取K线数据"""
        return self.parquet.get_bars(symbol, start, end, frequency)

    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """从 SQLite 获取股票列表"""
        return self.sqlite.get_symbols(exchange)

    def save_symbols(self, symbols: List[SymbolInfo]) -> None:
        """保存股票列表到 SQLite"""
        self.sqlite.save_symbols(symbols)

    def get_data_range(self, symbol: str, frequency: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取K线数据范围"""
        return self.parquet.get_data_range(symbol, frequency)
