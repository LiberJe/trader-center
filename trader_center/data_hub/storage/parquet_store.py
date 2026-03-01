from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa

from trader_center.data_hub.storage.base import Storage
from trader_center.data_hub.models import (
    BarData, Frequency,
    MarketFundFlow, StockFundFlow, SectorFundFlow
)
from trader_center.data_hub.config import DataHubConfig


class ParquetStorage(Storage):
    """Parquet 存储实现 - 用于大规模K线数据"""

    def __init__(self, config: DataHubConfig):
        self.config = config

    def _get_bar_path(self, symbol: str, frequency: str) -> Path:
        """获取 Parquet 文件路径"""
        freq_dir = self.config.bars_dir / frequency.replace("1d", "daily").replace(
            "1min", "min1"
        )
        freq_dir.mkdir(exist_ok=True)
        return freq_dir / f"{symbol}.parquet"

    def save_bars(self, bars: List[BarData]) -> None:
        """保存K线数据到 Parquet"""
        if not bars:
            return

        # 按 symbol 和 frequency 分组
        grouped = {}
        for bar in bars:
            key = (bar.symbol, bar.frequency.value)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(bar)

        for (symbol, frequency), bar_list in grouped.items():
            self._save_symbol_bars(symbol, frequency, bar_list)

    def _save_symbol_bars(self, symbol: str, frequency: str, bars: List[BarData]):
        """保存单个股票的K线数据"""
        file_path = self._get_bar_path(symbol, frequency)

        # 新数据转换为 DataFrame
        new_df = pd.DataFrame(
            [
                {
                    "timestamp": bar.timestamp,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "amount": bar.amount,
                    "adj_factor": bar.adj_factor,
                    "is_suspended": bar.is_suspended,
                }
                for bar in bars
            ]
        )

        if file_path.exists():
            # 读取现有数据
            existing_df = pq.read_table(file_path).to_pandas()
            # 合并并去重
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["timestamp"], keep="first")
            combined = combined.sort_values("timestamp")
        else:
            combined = new_df.sort_values("timestamp")

        # 写入 Parquet
        table = pa.Table.from_pandas(combined)
        pq.write_table(table, file_path)

    def get_bars(
        self, symbol: str, start: datetime, end: datetime, frequency: str
    ) -> pd.DataFrame:
        """获取K线数据"""
        file_path = self._get_bar_path(symbol, frequency)

        if not file_path.exists():
            return pd.DataFrame()

        df = pq.read_table(file_path).to_pandas()
        mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
        return df[mask].copy()

    def get_data_range(
        self, symbol: str, frequency: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取本地已有数据的时间范围"""
        file_path = self._get_bar_path(symbol, frequency)

        if not file_path.exists():
            return None, None

        df = pq.read_table(file_path).to_pandas()
        if df.empty:
            return None, None

        return df["timestamp"].min(), df["timestamp"].max()

    def get_symbols(self, exchange: Optional[str] = None) -> List:
        """Parquet 不存储股票列表"""
        raise NotImplementedError("Use SQLiteStorage for symbols")

    def save_symbols(self, symbols: List) -> None:
        """Parquet 不存储股票列表"""
        raise NotImplementedError("Use SQLiteStorage for symbols")

    # 资金流向数据 - Parquet 不存储，使用 SQLite
    def save_market_fund_flow(self, data: MarketFundFlow) -> None:
        """Parquet 不存储资金流向数据"""
        raise NotImplementedError("Use SQLiteStorage for fund flow data")

    def get_market_fund_flow(self, target_date: date) -> Optional[MarketFundFlow]:
        """Parquet 不存储资金流向数据"""
        raise NotImplementedError("Use SQLiteStorage for fund flow data")

    def save_stock_fund_flow(self, data: List[StockFundFlow]) -> None:
        """Parquet 不存储资金流向数据"""
        raise NotImplementedError("Use SQLiteStorage for fund flow data")

    def get_stock_fund_flow(
        self, target_date: date, limit: int = 100
    ) -> List[StockFundFlow]:
        """Parquet 不存储资金流向数据"""
        raise NotImplementedError("Use SQLiteStorage for fund flow data")

    def save_sector_fund_flow(self, data: List[SectorFundFlow]) -> None:
        """Parquet 不存储资金流向数据"""
        raise NotImplementedError("Use SQLiteStorage for fund flow data")

    def get_sector_fund_flow(
        self, target_date: date, sector_type: Optional[str] = None
    ) -> List[SectorFundFlow]:
        """Parquet 不存储资金流向数据"""
        raise NotImplementedError("Use SQLiteStorage for fund flow data")
