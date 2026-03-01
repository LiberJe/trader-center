from datetime import datetime, date
from typing import List, Optional, Tuple
import pandas as pd

from trader_center.data_hub.storage.base import Storage
from trader_center.data_hub.storage.sqlite_store import SQLiteStorage
from trader_center.data_hub.storage.parquet_store import ParquetStorage
from trader_center.data_hub.models import (
    BarData, SymbolInfo,
    MarketFundFlow, StockFundFlow, SectorFundFlow
)
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
        self, symbol: str, start: datetime, end: datetime, frequency: str
    ) -> pd.DataFrame:
        """从 Parquet 获取K线数据"""
        return self.parquet.get_bars(symbol, start, end, frequency)

    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """从 SQLite 获取股票列表"""
        return self.sqlite.get_symbols(exchange)

    def save_symbols(self, symbols: List[SymbolInfo]) -> None:
        """保存股票列表到 SQLite"""
        self.sqlite.save_symbols(symbols)

    def get_data_range(
        self, symbol: str, frequency: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取K线数据范围"""
        return self.parquet.get_data_range(symbol, frequency)

    # 资金流向数据存储 - 转发到 SQLite
    def save_market_fund_flow(self, data: MarketFundFlow) -> None:
        """保存大盘资金流向数据"""
        self.sqlite.save_market_fund_flow(data)

    def get_market_fund_flow(self, target_date: date) -> Optional[MarketFundFlow]:
        """获取大盘资金流向数据"""
        return self.sqlite.get_market_fund_flow(target_date)

    def save_stock_fund_flow(self, data: List[StockFundFlow]) -> None:
        """保存个股资金流向数据"""
        self.sqlite.save_stock_fund_flow(data)

    def get_stock_fund_flow(
        self, target_date: date, limit: int = 100
    ) -> List[StockFundFlow]:
        """获取个股资金流向数据"""
        return self.sqlite.get_stock_fund_flow(target_date, limit)

    def save_sector_fund_flow(self, data: List[SectorFundFlow]) -> None:
        """保存板块资金流向数据"""
        self.sqlite.save_sector_fund_flow(data)

    def get_sector_fund_flow(
        self, target_date: date, sector_type: Optional[str] = None
    ) -> List[SectorFundFlow]:
        """获取板块资金流向数据"""
        return self.sqlite.get_sector_fund_flow(target_date, sector_type)
