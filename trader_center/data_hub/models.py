"""Database models for the data hub."""

from datetime import date
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), nullable=False, unique=True, index=True)
    name = Column(String(128), nullable=False)
    market = Column(String(16), nullable=False, index=True)  # CN, US, HK, CRYPTO
    exchange = Column(String(16), nullable=False)
    category = Column(String(16), default="stock")  # stock, index, etf, crypto
    status = Column(String(16), default="active")  # active, delisted
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    daily_bars = relationship("DailyBar", back_populates="symbol", cascade="all, delete-orphan")
    watchlist_entries = relationship("Watchlist", back_populates="symbol", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Symbol(code='{self.code}', name='{self.name}')>"


class DailyBar(Base):
    __tablename__ = "daily_bars"

    id = Column(Integer, primary_key=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    amount = Column(Float, nullable=True)
    adj_factor = Column(Float, default=1.0)
    is_suspended = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    symbol = relationship("Symbol", back_populates="daily_bars")

    __table_args__ = (
        UniqueConstraint("symbol_id", "date", name="uix_daily_bar_symbol_date"),
        Index("ix_daily_bars_symbol_date", "symbol_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<DailyBar(symbol='{self.symbol.code}', date='{self.date}', close={self.close})>"


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    group_name = Column(String(32), default="default", nullable=False)
    notes = Column(String(256), nullable=True)
    added_at = Column(DateTime, server_default=func.now())

    symbol = relationship("Symbol", back_populates="watchlist_entries")

    __table_args__ = (
        UniqueConstraint("symbol_id", "group_name", name="uix_watchlist_symbol_group"),
    )

    def __repr__(self) -> str:
        return f"<Watchlist(symbol='{self.symbol.code}', group='{self.group_name}')>"
