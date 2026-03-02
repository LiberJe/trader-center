import sqlite3
import json
from datetime import datetime, date
from typing import List, Optional, Tuple
import pandas as pd

from trader_center.data_hub.storage.base import Storage
from trader_center.data_hub.models import (
    SymbolInfo, FinancialReport, BarData,
    MarketFundFlow, StockFundFlow, SectorFundFlow
)
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    type TEXT DEFAULT 'stock',
                    list_date TEXT,
                    delist_date TEXT,
                    industry TEXT
                )
            """
            )

            conn.execute(
                """
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
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_symbols_exchange
                ON symbols(exchange)
            """
            )

            # 资金流向数据表
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS market_fund_flow (
                    date TEXT PRIMARY KEY,
                    market TEXT NOT NULL,
                    main_force_net REAL,
                    super_large_net REAL,
                    large_net REAL,
                    medium_net REAL,
                    small_net REAL,
                    total_amount REAL
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_fund_flow (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT,
                    close_price REAL,
                    change_pct REAL,
                    fund_flow REAL,
                    flow_ratio REAL,
                    main_force_net REAL,
                    UNIQUE(date, symbol)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stock_fund_flow_date
                ON stock_fund_flow(date)
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sector_fund_flow (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    sector_type TEXT NOT NULL,
                    sector_name TEXT NOT NULL,
                    fund_flow REAL,
                    change_pct REAL,
                    leading_stock TEXT,
                    leading_stock_change REAL,
                    UNIQUE(date, sector_type, sector_name)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sector_fund_flow_date
                ON sector_fund_flow(date)
            """
            )

    def save_symbols(self, symbols: List[SymbolInfo]) -> None:
        """保存股票列表"""
        with self._connect() as conn:
            for s in symbols:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO symbols
                    (symbol, name, exchange, type, list_date, delist_date, industry)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        s.symbol,
                        s.name,
                        s.exchange,
                        s.type,
                        s.list_date.isoformat() if s.list_date else None,
                        s.delist_date.isoformat() if s.delist_date else None,
                        s.industry,
                    ),
                )

    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """获取股票列表"""
        with self._connect() as conn:
            if exchange:
                cursor = conn.execute(
                    "SELECT * FROM symbols WHERE exchange = ?", (exchange,)
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
                    industry=row[6],
                )
                for row in rows
            ]

    def save_bars(self, bars: List[BarData]) -> None:
        """SQLite 不存储K线数据，使用 Parquet"""
        raise NotImplementedError("Use ParquetStorage for bars")

    def get_bars(
        self, symbol: str, start: datetime, end: datetime, frequency: str
    ) -> pd.DataFrame:
        """SQLite 不存储K线数据"""
        raise NotImplementedError("Use ParquetStorage for bars")

    def get_data_range(
        self, symbol: str, frequency: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """返回 None，Parquet 存储处理数据范围"""
        return None, None

    # 资金流向数据存储实现
    def save_market_fund_flow(self, data: MarketFundFlow) -> None:
        """保存大盘资金流向数据"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO market_fund_flow
                (date, market, main_force_net, super_large_net, large_net,
                 medium_net, small_net, total_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data.date.isoformat(),
                    data.market,
                    data.main_force_net,
                    data.super_large_net,
                    data.large_net,
                    data.medium_net,
                    data.small_net,
                    data.total_amount,
                ),
            )

    def get_market_fund_flow(self, target_date: date) -> Optional[MarketFundFlow]:
        """获取大盘资金流向数据"""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM market_fund_flow WHERE date = ?",
                (target_date.isoformat(),),
            )
            row = cursor.fetchone()
            if row:
                return MarketFundFlow(
                    date=date.fromisoformat(row[0]),
                    market=row[1],
                    main_force_net=row[2],
                    super_large_net=row[3],
                    large_net=row[4],
                    medium_net=row[5],
                    small_net=row[6],
                    total_amount=row[7],
                )
            return None

    def save_stock_fund_flow(self, data: List[StockFundFlow]) -> None:
        """保存个股资金流向数据"""
        with self._connect() as conn:
            for item in data:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_fund_flow
                    (date, symbol, name, close_price, change_pct,
                     fund_flow, flow_ratio, main_force_net)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item.date.isoformat(),
                        item.symbol,
                        item.name,
                        item.close_price,
                        item.change_pct,
                        item.fund_flow,
                        item.flow_ratio,
                        item.main_force_net,
                    ),
                )

    def get_stock_fund_flow(
        self, target_date: date, limit: int = 100
    ) -> List[StockFundFlow]:
        """获取个股资金流向数据"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM stock_fund_flow
                WHERE date = ?
                ORDER BY fund_flow DESC
                LIMIT ?
            """,
                (target_date.isoformat(), limit),
            )
            rows = cursor.fetchall()
            return [
                StockFundFlow(
                    date=date.fromisoformat(row[1]),
                    symbol=row[2],
                    name=row[3],
                    close_price=row[4],
                    change_pct=row[5],
                    fund_flow=row[6],
                    flow_ratio=row[7],
                    main_force_net=row[8],
                )
                for row in rows
            ]

    def save_sector_fund_flow(self, data: List[SectorFundFlow]) -> None:
        """保存板块资金流向数据"""
        with self._connect() as conn:
            for item in data:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sector_fund_flow
                    (date, sector_type, sector_name, fund_flow, change_pct,
                     leading_stock, leading_stock_change)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item.date.isoformat(),
                        item.sector_type,
                        item.sector_name,
                        item.fund_flow,
                        item.change_pct,
                        item.leading_stock,
                        item.leading_stock_change,
                    ),
                )

    def get_sector_fund_flow(
        self, target_date: date, sector_type: Optional[str] = None
    ) -> List[SectorFundFlow]:
        """获取板块资金流向数据"""
        with self._connect() as conn:
            if sector_type:
                cursor = conn.execute(
                    """
                    SELECT * FROM sector_fund_flow
                    WHERE date = ? AND sector_type = ?
                    ORDER BY fund_flow DESC
                """,
                    (target_date.isoformat(), sector_type),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM sector_fund_flow
                    WHERE date = ?
                    ORDER BY fund_flow DESC
                """,
                    (target_date.isoformat(),),
                )
            rows = cursor.fetchall()
            return [
                SectorFundFlow(
                    date=date.fromisoformat(row[1]),
                    sector_type=row[2],
                    sector_name=row[3],
                    fund_flow=row[4],
                    change_pct=row[5],
                    leading_stock=row[6],
                    leading_stock_change=row[7],
                )
                for row in rows
            ]

    def delete_market_fund_flow(self, target_date: date) -> int:
        """删除指定日期的大盘资金流向数据

        Returns:
            删除的记录数
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM market_fund_flow WHERE date = ?",
                (target_date.isoformat(),),
            )
            return cursor.rowcount

    def delete_stock_fund_flow(self, target_date: date) -> int:
        """删除指定日期的个股资金流向数据

        Returns:
            删除的记录数
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM stock_fund_flow WHERE date = ?",
                (target_date.isoformat(),),
            )
            return cursor.rowcount

    def delete_sector_fund_flow(self, target_date: date, sector_type: Optional[str] = None) -> int:
        """删除指定日期的板块资金流向数据

        Args:
            target_date: 目标日期
            sector_type: 板块类型，为 None 时删除所有类型

        Returns:
            删除的记录数
        """
        with self._connect() as conn:
            if sector_type:
                cursor = conn.execute(
                    "DELETE FROM sector_fund_flow WHERE date = ? AND sector_type = ?",
                    (target_date.isoformat(), sector_type),
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM sector_fund_flow WHERE date = ?",
                    (target_date.isoformat(),),
                )
            return cursor.rowcount

    def delete_all_market_fund_flow(self) -> int:
        """删除所有日期的大盘资金流向数据

        Returns:
            删除的记录数
        """
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM market_fund_flow")
            return cursor.rowcount

    def delete_all_stock_fund_flow(self) -> int:
        """删除所有日期的个股资金流向数据

        Returns:
            删除的记录数
        """
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM stock_fund_flow")
            return cursor.rowcount

    def delete_all_sector_fund_flow(self) -> int:
        """删除所有日期的板块资金流向数据

        Returns:
            删除的记录数
        """
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM sector_fund_flow")
            return cursor.rowcount
