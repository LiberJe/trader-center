from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from trader_center.data_hub.models import BarData, SymbolInfo


class DataFetcher(ABC):
    """数据源获取器基类"""

    name: str = "base"
    priority: int = 100  # 数字越小优先级越高

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> List[BarData]:
        """获取K线数据"""
        pass

    @abstractmethod
    def get_symbols(self) -> List[SymbolInfo]:
        """获取股票列表"""
        pass

    @abstractmethod
    def check_available(self) -> bool:
        """检查数据源是否可用"""
        pass
