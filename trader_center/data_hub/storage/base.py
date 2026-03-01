from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Tuple
import pandas as pd

from trader_center.data_hub.models import (
    BarData, SymbolInfo, FinancialReport,
    MarketFundFlow, StockFundFlow, SectorFundFlow
)


class Storage(ABC):
    """存储层抽象基类"""

    @abstractmethod
    def save_bars(self, bars: List[BarData]) -> None:
        """批量保存K线数据"""
        pass

    @abstractmethod
    def get_bars(
        self, symbol: str, start: datetime, end: datetime, frequency: str
    ) -> pd.DataFrame:
        """获取K线数据"""
        pass

    @abstractmethod
    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """获取股票列表"""
        pass

    @abstractmethod
    def get_data_range(
        self, symbol: str, frequency: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取本地已有数据的时间范围"""
        pass

    @abstractmethod
    def save_symbols(self, symbols: List[SymbolInfo]) -> None:
        """保存股票列表"""
        pass

    # 资金流向数据存储接口
    @abstractmethod
    def save_market_fund_flow(self, data: MarketFundFlow) -> None:
        """保存大盘资金流向数据"""
        pass

    @abstractmethod
    def get_market_fund_flow(self, target_date: date) -> Optional[MarketFundFlow]:
        """获取大盘资金流向数据"""
        pass

    @abstractmethod
    def save_stock_fund_flow(self, data: List[StockFundFlow]) -> None:
        """保存个股资金流向数据"""
        pass

    @abstractmethod
    def get_stock_fund_flow(
        self, target_date: date, limit: int = 100
    ) -> List[StockFundFlow]:
        """获取个股资金流向数据"""
        pass

    @abstractmethod
    def save_sector_fund_flow(self, data: List[SectorFundFlow]) -> None:
        """保存板块资金流向数据"""
        pass

    @abstractmethod
    def get_sector_fund_flow(
        self, target_date: date, sector_type: Optional[str] = None
    ) -> List[SectorFundFlow]:
        """获取板块资金流向数据"""
        pass
