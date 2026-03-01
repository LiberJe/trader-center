import sqlite3
import json
from datetime import datetime, date
from typing import List, Optional, Tuple
import pandas as pd

from trader_center.data_hub.storage.base import Storage
from trader_center.data_hub.models import SymbolInfo, FinancialReport, BarData
from trader_center.data_hub.config import DataHubConfig


class SQLiteStorage(Storage):
    """SQLite 存储实现 - 用于元数据和财务数据"""

    def __init__(self, config: DataHubConfig):
        self.config = config
        self._init_tables()

    def _connect(self):
        return sqlite3.connect(self.config.sqlite_path)

    def _init_tables(self):
        """初始化数据库表"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    type TEXT DEFAULT 'stock',
                    list_date TEXT,
                    delist_date TEXT,
                    industry TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    report_date TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    revenue REAL,
                    net_profit REAL,
                    eps REAL,
                    roe REAL,
                    debt_ratio REAL,
                    raw_data TEXT,
                    UNIQUE(symbol, report_date, report_type)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbols_exchange
                ON symbols(exchange)
            """)

    def save_symbols(self, symbols: List[SymbolInfo]) -> None:
        """保存股票列表"""
        with self._connect() as conn:
            for s in symbols:
                conn.execute("""
                    INSERT OR REPLACE INTO symbols
                    (symbol, name, exchange, type, list_date, delist_date, industry)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    s.symbol, s.name, s.exchange, s.type,
                    s.list_date.isoformat() if s.list_date else None,
                    s.delist_date.isoformat() if s.delist_date else None,
                    s.industry
                ))

    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """获取股票列表"""
        with self._connect() as conn:
            if exchange:
                cursor = conn.execute(
                    "SELECT * FROM symbols WHERE exchange = ?",
                    (exchange,)
                )
            else:
                cursor = conn.execute("SELECT * FROM symbols")

            rows = cursor.fetchall()
            return [
                SymbolInfo(
                    symbol=row[0],
                    name=row[1],
                    exchange=row[2],
                    type=row[3],
                    list_date=date.fromisoformat(row[4]) if row[4] else None,
                    delist_date=date.fromisoformat(row[5]) if row[5] else None,
                    industry=row[6]
                )
                for row in rows
            ]

    def save_bars(self, bars: List[BarData]) -> None:
        """SQLite 不存储K线数据，使用 Parquet"""
        raise NotImplementedError("Use ParquetStorage for bars")

    def get_bars(self, symbol: str, start: datetime, end: datetime, frequency: str) -> pd.DataFrame:
        """SQLite 不存储K线数据"""
        raise NotImplementedError("Use ParquetStorage for bars")

    def get_data_range(self, symbol: str, frequency: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """返回 None，Parquet 存储处理数据范围"""
        return None, None
