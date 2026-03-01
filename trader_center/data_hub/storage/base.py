from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple
import pandas as pd

from trader_center.data_hub.models import BarData, SymbolInfo, FinancialReport


class Storage(ABC):
    """存储层抽象基类"""

    @abstractmethod
    def save_bars(self, bars: List[BarData]) -> None:
        """批量保存K线数据"""
        pass

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> pd.DataFrame:
        """获取K线数据"""
        pass

    @abstractmethod
    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """获取股票列表"""
        pass

    @abstractmethod
    def get_data_range(self, symbol: str, frequency: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取本地已有数据的时间范围"""
        pass

    @abstractmethod
    def save_symbols(self, symbols: List[SymbolInfo]) -> None:
        """保存股票列表"""
        pass
