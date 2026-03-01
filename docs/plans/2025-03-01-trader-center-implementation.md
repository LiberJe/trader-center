# Trader Center Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal financial market research framework with data hub, dual backtest engines, and daily market monitoring.

**Architecture:** Modular monolith with clear separation between data_hub (unified data access), backtest (vectorized + event-driven), and monitor (market overview, watchlist, alerts). SQLite for storage, Click for CLI.

**Tech Stack:** Python 3.11+, SQLite, SQLAlchemy 2.0, Pydantic 2.0, Click, Pandas, NumPy, AkShare, yfinance, python-binance, rich (optional), pytest

---

## Phase 1: Project Foundation

### Task 1: Create Project Structure

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.gitignore`
- Create: `trader_center/__init__.py`
- Create: `trader_center/data_hub/__init__.py`
- Create: `trader_center/backtest/__init__.py`
- Create: `trader_center/monitor/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "trader-center"
version = "0.1.0"
description = "Personal financial market research framework"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "sqlalchemy>=2.0",
    "pandas>=2.0",
    "numpy>=1.24",
    "akshare>=1.11",
    "yfinance>=0.2",
    "python-binance>=1.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]

[project.scripts]
tc = "trader_center.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

**Step 2: Write .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Data
data/*.db
data/*.sqlite
data/*.sqlite3
*.csv
*.parquet

# Logs
*.log
logs/

# Config with secrets
config.yaml
!config.yaml.example

# OS
.DS_Store
Thumbs.db
```

**Step 3: Create directory structure**

```bash
mkdir -p trader_center/data_hub/fetchers
mkdir -p trader_center/backtest/vectorized
mkdir -p trader_center/backtest/event_driven
mkdir -p trader_center/monitor/templates
mkdir -p tests/data_hub
mkdir -p tests/backtest
mkdir -p tests/monitor
mkdir -p data
mkdir -p examples
```

**Step 4: Write README.md**

```markdown
# Trader Center

Personal financial market research framework.

## Features

- **Data Hub**: Unified data access for A-share (AkShare), US/HK stocks (Yahoo), Crypto (Binance)
- **Backtest**: Vectorized and event-driven backtest engines
- **Monitor**: Daily market overview, watchlist, alerts

## Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Initialize database
tc init

# Fetch data
tc data sync

# Run backtest
examples/backtest_demo.py

# Market overview
tc monitor overview
```
```

**Step 5: Commit**

```bash
git add .
git commit -m "chore: initialize project structure

- Add pyproject.toml with dependencies
- Create package structure
- Add README and .gitignore

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: Data Hub - Database Models

### Task 2: Create Database Models

**Files:**
- Create: `trader_center/data_hub/models.py`
- Test: `tests/data_hub/test_models.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from trader_center.data_hub.models import Base, Symbol, DailyBar, Watchlist


class TestModels:
    @pytest.fixture
    def session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    def test_create_symbol(self, session):
        symbol = Symbol(
            code="000001.SZ",
            name="平安银行",
            market="CN",
            exchange="SZSE",
            category="stock"
        )
        session.add(symbol)
        session.commit()

        result = session.query(Symbol).first()
        assert result.code == "000001.SZ"
        assert result.name == "平安银行"

    def test_create_daily_bar(self, session):
        symbol = Symbol(code="000001.SZ", name="平安银行", market="CN", exchange="SZSE")
        session.add(symbol)
        session.commit()

        bar = DailyBar(
            symbol_id=symbol.id,
            date=date(2024, 1, 15),
            open=10.5,
            high=10.8,
            low=10.3,
            close=10.6,
            volume=1000000,
            amount=10500000.0
        )
        session.add(bar)
        session.commit()

        result = session.query(DailyBar).first()
        assert result.close == 10.6
        assert result.symbol.code == "000001.SZ"

    def test_watchlist(self, session):
        symbol = Symbol(code="000001.SZ", name="平安银行", market="CN", exchange="SZSE")
        session.add(symbol)
        session.commit()

        watch = Watchlist(symbol_id=symbol.id, group_name="tech")
        session.add(watch)
        session.commit()

        result = session.query(Watchlist).first()
        assert result.group_name == "tech"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/data_hub/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'trader_center.data_hub.models'`

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/test_models.py -v
```

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add database models for data hub

- Symbol, DailyBar, Watchlist models
- SQLAlchemy 2.0 declarative base
- Relationships and indexes

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Database Connection Manager

**Files:**
- Create: `trader_center/data_hub/database.py`
- Test: `tests/data_hub/test_database.py`

**Step 1: Write failing test**

```python
import pytest
import os
import tempfile

from trader_center.data_hub.database import DatabaseManager


class TestDatabaseManager:
    def test_singleton_instance(self):
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        assert db1 is db2

    def test_init_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseManager()
            db.init_database(db_path)
            assert os.path.exists(db_path)

    def test_get_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseManager()
            db.init_database(db_path)
            session = db.get_session()
            assert session is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/data_hub/test_database.py -v
```

Expected: `ModuleNotFoundError`

**Step 3: Write implementation**

```python
import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from trader_center.data_hub.models import Base


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None
    _engine = None
    _session_factory = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init_database(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = Path.home() / ".trader_center" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "trader_center.db"

        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def get_session(self) -> Session:
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call init_database() first.")
        return self._session_factory()

    def get_engine(self):
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call init_database() first.")
        return self._engine

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


def get_db() -> DatabaseManager:
    return DatabaseManager()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/test_database.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add database manager with singleton pattern

- DatabaseManager singleton for connection management
- Auto-create tables on init
- Default path in ~/.trader_center/data/

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: Data Hub - Fetchers

### Task 4: Create Base Fetcher

**Files:**
- Create: `trader_center/data_hub/fetchers/base.py`
- Test: `tests/data_hub/fetchers/test_base.py`

**Step 1: Write failing test**

```python
import pytest
import pandas as pd
from datetime import date

from trader_center.data_hub.fetchers.base import BaseFetcher, FetcherError


class TestBaseFetcher:
    def test_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseFetcher()

    def test_fetcher_error(self):
        error = FetcherError("test error", source="test")
        assert str(error) == "[test] test error"


class ConcreteFetcher(BaseFetcher):
    @property
    def source_name(self) -> str:
        return "test"

    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame({
            "date": [date(2024, 1, 1)],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000000],
        })

    def fetch_symbols(self) -> pd.DataFrame:
        return pd.DataFrame({
            "code": ["TEST001"],
            "name": ["Test Stock"],
            "market": ["CN"],
            "exchange": ["TEST"],
        })


class TestConcreteFetcher:
    def test_source_name(self):
        fetcher = ConcreteFetcher()
        assert fetcher.source_name == "test"

    def test_fetch_daily_bars(self):
        fetcher = ConcreteFetcher()
        df = fetcher.fetch_daily_bars("TEST001", date(2024, 1, 1), date(2024, 1, 31))
        assert not df.empty
        assert "date" in df.columns
        assert "close" in df.columns
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/data_hub/fetchers/test_base.py -v
```

**Step 3: Write implementation**

```python
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

import pandas as pd


class FetcherError(Exception):
    """Exception raised when data fetching fails."""

    def __init__(self, message: str, source: Optional[str] = None):
        self.source = source
        self.message = message
        super().__init__(f"[{source}] {message}" if source else message)


class BaseFetcher(ABC):
    """Abstract base class for data fetchers."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the data source."""
        pass

    @abstractmethod
    def fetch_daily_bars(
        self, symbol: str, start: date, end: date
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV bars for a symbol.

        Args:
            symbol: Symbol code (e.g., "000001.SZ")
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        pass

    @abstractmethod
    def fetch_symbols(self) -> pd.DataFrame:
        """
        Fetch all available symbols.

        Returns:
            DataFrame with columns: code, name, market, exchange, category
        """
        pass

    def validate_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize OHLCV data."""
        required_cols = ["date", "open", "high", "low", "close", "volume"]

        for col in required_cols:
            if col not in df.columns:
                raise FetcherError(f"Missing required column: {col}", self.source_name)

        # Ensure date column is datetime
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # Sort by date
        df = df.sort_values("date").reset_index(drop=True)

        return df
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/fetchers/test_base.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add base fetcher abstract class

- BaseFetcher with abstract methods
- FetcherError exception class
- OHLCV validation helper

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Implement AkShare Fetcher (A-Share)

**Files:**
- Create: `trader_center/data_hub/fetchers/akshare_fetcher.py`
- Test: `tests/data_hub/fetchers/test_akshare_fetcher.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd

from trader_center.data_hub.fetchers.akshare_fetcher import AkShareFetcher


class TestAkShareFetcher:
    def test_source_name(self):
        fetcher = AkShareFetcher()
        assert fetcher.source_name == "akshare"

    @patch("trader_center.data_hub.fetchers.akshare_fetcher.ak")
    def test_fetch_daily_bars(self, mock_ak):
        # Mock the akshare response
        mock_df = pd.DataFrame({
            "日期": ["2024-01-15", "2024-01-16"],
            "开盘": [10.0, 10.2],
            "最高": [10.5, 10.6],
            "最低": [9.8, 10.0],
            "收盘": [10.3, 10.4],
            "成交量": [100000, 120000],
            "成交额": [1000000, 1200000],
        })
        mock_ak.stock_zh_a_hist.return_value = mock_df

        fetcher = AkShareFetcher()
        result = fetcher.fetch_daily_bars("000001", date(2024, 1, 1), date(2024, 1, 31))

        assert len(result) == 2
        assert "date" in result.columns
        assert "close" in result.columns
        assert result["close"].iloc[0] == 10.3

    @patch("trader_center.data_hub.fetchers.akshare_fetcher.ak")
    def test_fetch_symbols(self, mock_ak):
        mock_df = pd.DataFrame({
            "代码": ["000001", "000002"],
            "名称": ["平安银行", "万科A"],
        })
        mock_ak.stock_zh_a_spot_em.return_value = mock_df

        fetcher = AkShareFetcher()
        result = fetcher.fetch_symbols()

        assert len(result) == 2
        assert "code" in result.columns
        assert result["code"].iloc[0] == "000001.SZ"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/data_hub/fetchers/test_akshare_fetcher.py -v
```

**Step 3: Write implementation**

```python
from datetime import date
from typing import Optional

import akshare as ak
import pandas as pd

from trader_center.data_hub.fetchers.base import BaseFetcher, FetcherError


class AkShareFetcher(BaseFetcher):
    """Fetcher for A-share market data using AkShare."""

    @property
    def source_name(self) -> str:
        return "akshare"

    def _normalize_symbol(self, symbol: str) -> tuple[str, str]:
        """
        Normalize symbol to AkShare format.

        Args:
            symbol: Symbol like "000001.SZ" or "600000.SH"

        Returns:
            Tuple of (code, exchange) like ("000001", "SZ")
        """
        if "." in symbol:
            code, exchange = symbol.split(".")
            return code, exchange
        return symbol, ""

    def _add_exchange_suffix(self, code: str, exchange: str) -> str:
        """Add exchange suffix to code."""
        exchange_map = {
            "SZ": "SZ",
            "SH": "SH",
            "BJ": "BJ",
        }
        suffix = exchange_map.get(exchange, "")
        return f"{code}.{suffix}" if suffix else code

    def fetch_daily_bars(
        self, symbol: str, start: date, end: date
    ) -> pd.DataFrame:
        """
        Fetch daily bars for A-share stock.

        Args:
            symbol: Stock code like "000001.SZ"
            start: Start date
            end: End date

        Returns:
            DataFrame with OHLCV data
        """
        try:
            code, exchange = self._normalize_symbol(symbol)

            # Determine start and end adjustment mode
            start_date = start.strftime("%Y%m%d")
            end_date = end.strftime("%Y%m%d")

            # Fetch data from AkShare
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",  # Forward adjusted
            )

            if df.empty:
                return pd.DataFrame(
                    columns=["date", "open", "high", "low", "close", "volume", "amount"]
                )

            # Rename columns to standard format
            column_map = {
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
            }
            df = df.rename(columns=column_map)

            # Select only needed columns
            df = df[["date", "open", "high", "low", "close", "volume", "amount"]]

            return self.validate_ohlcv(df)

        except Exception as e:
            raise FetcherError(f"Failed to fetch {symbol}: {e}", self.source_name)

    def fetch_symbols(self) -> pd.DataFrame:
        """
        Fetch all A-share stock symbols.

        Returns:
            DataFrame with symbol info
        """
        try:
            df = ak.stock_zh_a_spot_em()

            # Rename columns
            column_map = {
                "代码": "code",
                "名称": "name",
            }
            df = df.rename(columns=column_map)

            # Extract exchange from code pattern
            def get_exchange(code: str) -> str:
                if code.startswith("6"):
                    return "SH"
                elif code.startswith("0") or code.startswith("3"):
                    return "SZ"
                elif code.startswith("4") or code.startswith("8"):
                    return "BJ"
                return ""

            df["exchange"] = df["code"].apply(get_exchange)
            df["market"] = "CN"
            df["category"] = "stock"

            # Add exchange suffix to code
            df["code"] = df["code"] + "." + df["exchange"]

            return df[["code", "name", "market", "exchange", "category"]]

        except Exception as e:
            raise FetcherError(f"Failed to fetch symbols: {e}", self.source_name)

    def fetch_index_bars(
        self, index_code: str, start: date, end: date
    ) -> pd.DataFrame:
        """
        Fetch index daily bars.

        Args:
            index_code: Index code like "000001.SH" (上证指数)
            start: Start date
            end: End date

        Returns:
            DataFrame with OHLCV data
        """
        try:
            code, exchange = self._normalize_symbol(index_code)
            start_date = start.strftime("%Y%m%d")
            end_date = end.strftime("%Y%m%d")

            # Map index codes to AkShare format
            # "000001.SH" -> "sh000001"
            ak_symbol = f"{exchange.lower()}{code}"

            df = ak.index_zh_a_hist(
                symbol=ak_symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
            )

            if df.empty:
                return pd.DataFrame(
                    columns=["date", "open", "high", "low", "close", "volume", "amount"]
                )

            # Rename columns
            column_map = {
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
            }
            df = df.rename(columns=column_map)
            df = df[["date", "open", "high", "low", "close", "volume", "amount"]]

            return self.validate_ohlcv(df)

        except Exception as e:
            raise FetcherError(f"Failed to fetch index {index_code}: {e}", self.source_name)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/fetchers/test_akshare_fetcher.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add AkShare fetcher for A-share data

- Fetch daily bars for stocks
- Fetch all A-share symbols
- Support for index data
- Forward adjusted prices

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Implement Yahoo Finance Fetcher

**Files:**
- Create: `trader_center/data_hub/fetchers/yahoo_fetcher.py`
- Test: `tests/data_hub/fetchers/test_yahoo_fetcher.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd

from trader_center.data_hub.fetchers.yahoo_fetcher import YahooFetcher


class TestYahooFetcher:
    def test_source_name(self):
        fetcher = YahooFetcher()
        assert fetcher.source_name == "yahoo"

    @patch("trader_center.data_hub.fetchers.yahoo_fetcher.yf")
    def test_fetch_daily_bars(self, mock_yf):
        mock_ticker = Mock()
        mock_df = pd.DataFrame({
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000000, 1200000],
        }, index=pd.to_datetime(["2024-01-15", "2024-01-16"]))
        mock_ticker.history.return_value = mock_df
        mock_yf.Ticker.return_value = mock_ticker

        fetcher = YahooFetcher()
        result = fetcher.fetch_daily_bars("AAPL", date(2024, 1, 1), date(2024, 1, 31))

        assert len(result) == 2
        assert "date" in result.columns
        assert "close" in result.columns
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from trader_center.data_hub.fetchers.base import BaseFetcher, FetcherError


class YahooFetcher(BaseFetcher):
    """Fetcher for US/HK stock data using Yahoo Finance."""

    @property
    def source_name(self) -> str:
        return "yahoo"

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Yahoo Finance format.

        Args:
            symbol: Symbol like "AAPL" or "0700.HK"

        Returns:
            Yahoo Finance symbol
        """
        # Handle HK stocks: 0700.HK -> 0700.HK (already correct)
        # Handle Chinese A-shares via Yahoo: 000001.SZ -> 000001.SZ
        return symbol

    def fetch_daily_bars(
        self, symbol: str, start: date, end: date
    ) -> pd.DataFrame:
        """
        Fetch daily bars from Yahoo Finance.

        Args:
            symbol: Stock symbol
            start: Start date
            end: End date

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)

            df = ticker.history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=True,  # Use adjusted prices
            )

            if df.empty:
                return pd.DataFrame(
                    columns=["date", "open", "high", "low", "close", "volume", "amount"]
                )

            # Reset index to get date as column
            df = df.reset_index()

            # Rename columns
            column_map = {
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
            df = df.rename(columns=column_map)

            # Yahoo doesn't provide amount, calculate from close * volume
            df["amount"] = df["close"] * df["volume"]

            # Select only needed columns
            df = df[["date", "open", "high", "low", "close", "volume", "amount"]]

            return self.validate_ohlcv(df)

        except Exception as e:
            raise FetcherError(f"Failed to fetch {symbol}: {e}", self.source_name)

    def fetch_symbols(self) -> pd.DataFrame:
        """
        Yahoo Finance doesn't provide a symbols list API.
        Return empty DataFrame with correct schema.
        """
        return pd.DataFrame(
            columns=["code", "name", "market", "exchange", "category"]
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/fetchers/test_yahoo_fetcher.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Yahoo Finance fetcher

- Fetch daily bars for US/HK stocks
- Auto-adjusted prices
- Note: No symbol list API available

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Implement Binance Fetcher

**Files:**
- Create: `trader_center/data_hub/fetchers/binance_fetcher.py`
- Test: `tests/data_hub/fetchers/test_binance_fetcher.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd

from trader_center.data_hub.fetchers.binance_fetcher import BinanceFetcher


class TestBinanceFetcher:
    def test_source_name(self):
        fetcher = BinanceFetcher()
        assert fetcher.source_name == "binance"

    @patch("trader_center.data_hub.fetchers.binance_fetcher.Client")
    def test_fetch_daily_bars(self, mock_client_class):
        mock_client = Mock()
        mock_client.get_klines.return_value = [
            [1705276800000, "40000", "41000", "39000", "40500", "100", 1705363199999, "4050000", 100, "50", "2025000", "0"],
            [1705363200000, "40500", "41500", "40000", "41000", "120", 1705449599999, "4920000", 120, "60", "2460000", "0"],
        ]
        mock_client_class.return_value = mock_client

        fetcher = BinanceFetcher()
        result = fetcher.fetch_daily_bars("BTCUSDT", date(2024, 1, 15), date(2024, 1, 16))

        assert len(result) == 2
        assert "date" in result.columns
        assert result["close"].iloc[0] == 40500.0
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
from datetime import date, datetime
from typing import Optional

import pandas as pd
from binance.client import Client

from trader_center.data_hub.fetchers.base import BaseFetcher, FetcherError


class BinanceFetcher(BaseFetcher):
    """Fetcher for cryptocurrency data using Binance."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self._client: Optional[Client] = None

    @property
    def source_name(self) -> str:
        return "binance"

    @property
    def client(self) -> Client:
        """Lazy initialization of Binance client."""
        if self._client is None:
            # Client works without API key for public data
            self._client = Client(self.api_key, self.api_secret)
        return self._client

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Binance format.

        Args:
            symbol: Symbol like "BTCUSDT" or "BTC-USDT"

        Returns:
            Binance format symbol
        """
        return symbol.replace("-", "").upper()

    def fetch_daily_bars(
        self, symbol: str, start: date, end: date
    ) -> pd.DataFrame:
        """
        Fetch daily klines from Binance.

        Args:
            symbol: Trading pair like "BTCUSDT"
            start: Start date
            end: End date

        Returns:
            DataFrame with OHLCV data
        """
        try:
            symbol = self._normalize_symbol(symbol)

            # Convert dates to timestamps (milliseconds)
            start_ts = int(datetime.combine(start, datetime.min.time()).timestamp() * 1000)
            end_ts = int(datetime.combine(end, datetime.max.time()).timestamp() * 1000)

            # Fetch klines (candlestick data)
            klines = self.client.get_klines(
                symbol=symbol,
                interval=Client.KLINE_INTERVAL_1DAY,
                startTime=start_ts,
                endTime=end_ts,
            )

            if not klines:
                return pd.DataFrame(
                    columns=["date", "open", "high", "low", "close", "volume", "amount"]
                )

            # Parse klines data
            # [timestamp, open, high, low, close, volume, close_time, quote_volume, trades, ...]
            data = []
            for k in klines:
                data.append({
                    "date": datetime.fromtimestamp(k[0] / 1000).date(),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "amount": float(k[7]),  # Quote volume
                })

            df = pd.DataFrame(data)
            return self.validate_ohlcv(df)

        except Exception as e:
            raise FetcherError(f"Failed to fetch {symbol}: {e}", self.source_name)

    def fetch_symbols(self) -> pd.DataFrame:
        """
        Fetch all available trading pairs from Binance.

        Returns:
            DataFrame with symbol info
        """
        try:
            exchange_info = self.client.get_exchange_info()

            symbols = []
            for s in exchange_info["symbols"]:
                if s["status"] == "TRADING" and s["isSpotTradingAllowed"]:
                    symbols.append({
                        "code": s["symbol"],
                        "name": s["symbol"],
                        "market": "CRYPTO",
                        "exchange": "BINANCE",
                        "category": "crypto",
                    })

            return pd.DataFrame(symbols)

        except Exception as e:
            raise FetcherError(f"Failed to fetch symbols: {e}", self.source_name)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/fetchers/test_binance_fetcher.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Binance fetcher for crypto data

- Fetch daily klines for trading pairs
- Fetch all available symbols
- Support for spot trading pairs

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 4: Data Hub - Unified API

### Task 8: Create Data Sync Engine

**Files:**
- Create: `trader_center/data_hub/sync.py`
- Test: `tests/data_hub/test_sync.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd

from trader_center.data_hub.sync import DataSync
from trader_center.data_hub.models import Symbol, DailyBar


class TestDataSync:
    @pytest.fixture
    def mock_fetcher(self):
        fetcher = Mock()
        fetcher.source_name = "mock"
        fetcher.fetch_daily_bars.return_value = pd.DataFrame({
            "date": [date(2024, 1, 15), date(2024, 1, 16)],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000000, 1200000],
            "amount": [101000000, 122400000],
        })
        return fetcher

    @patch("trader_center.data_hub.sync.get_db")
    def test_sync_symbol_bars(self, mock_get_db, mock_fetcher):
        mock_session = Mock()
        mock_get_db.return_value.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_get_db.return_value.get_session.return_value.__exit__ = Mock(return_value=False)

        # Mock symbol query
        mock_symbol = Mock()
        mock_symbol.id = 1
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_symbol

        sync = DataSync()
        sync.register_fetcher("mock", mock_fetcher)
        sync.sync_symbol_bars("000001.SZ", date(2024, 1, 1), date(2024, 1, 31), source="mock")

        mock_fetcher.fetch_daily_bars.assert_called_once()
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
from datetime import date, timedelta
from typing import Optional, Callable

import pandas as pd
from sqlalchemy.orm import Session

from trader_center.data_hub.database import get_db
from trader_center.data_hub.fetchers.base import BaseFetcher
from trader_center.data_hub.models import Symbol, DailyBar


class DataSync:
    """Data synchronization engine."""

    def __init__(self):
        self._fetchers: dict[str, BaseFetcher] = {}
        self._db = get_db()

    def register_fetcher(self, name: str, fetcher: BaseFetcher) -> None:
        """Register a data fetcher."""
        self._fetchers[name] = fetcher

    def get_fetcher(self, source: str) -> BaseFetcher:
        """Get a registered fetcher by name."""
        if source not in self._fetchers:
            raise ValueError(f"Unknown data source: {source}")
        return self._fetchers[source]

    def sync_symbols(self, source: str) -> int:
        """
        Sync symbol list from a data source.

        Returns:
            Number of symbols synced
        """
        fetcher = self.get_fetcher(source)
        df = fetcher.fetch_symbols()

        if df.empty:
            return 0

        with self._db.get_session() as session:
            count = 0
            for _, row in df.iterrows():
                symbol = session.query(Symbol).filter_by(code=row["code"]).first()
                if symbol is None:
                    symbol = Symbol(
                        code=row["code"],
                        name=row["name"],
                        market=row.get("market", ""),
                        exchange=row.get("exchange", ""),
                        category=row.get("category", "stock"),
                    )
                    session.add(symbol)
                    count += 1

            session.commit()
            return count

    def sync_symbol_bars(
        self,
        symbol_code: str,
        start: date,
        end: date,
        source: Optional[str] = None,
    ) -> int:
        """
        Sync daily bars for a symbol.

        Args:
            symbol_code: Symbol code
            start: Start date
            end: End date
            source: Data source name (auto-detected if not provided)

        Returns:
            Number of bars synced
        """
        # Auto-detect source from symbol code
        if source is None:
            source = self._detect_source(symbol_code)

        fetcher = self.get_fetcher(source)
        df = fetcher.fetch_daily_bars(symbol_code, start, end)

        if df.empty:
            return 0

        with self._db.get_session() as session:
            # Get or create symbol
            symbol = session.query(Symbol).filter_by(code=symbol_code).first()
            if symbol is None:
                symbol = Symbol(
                    code=symbol_code,
                    name=symbol_code,
                    market=self._get_market_from_source(source),
                    exchange="",
                    category="stock",
                )
                session.add(symbol)
                session.flush()

            # Get existing dates to avoid duplicates
            existing_dates = {
                r[0]
                for r in session.query(DailyBar.date)
                .filter_by(symbol_id=symbol.id)
                .filter(DailyBar.date >= start, DailyBar.date <= end)
                .all()
            }

            count = 0
            for _, row in df.iterrows():
                if row["date"] in existing_dates:
                    continue

                bar = DailyBar(
                    symbol_id=symbol.id,
                    date=row["date"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    amount=row.get("amount"),
                )
                session.add(bar)
                count += 1

            session.commit()
            return count

    def sync_watchlist(self, group: str = "default") -> None:
        """
        Sync data for all symbols in watchlist group.
        """
        with self._db.get_session() as session:
            from trader_center.data_hub.models import Watchlist

            watchlist = session.query(Watchlist).filter_by(group_name=group).all()

            end = date.today()
            start = end - timedelta(days=365)  # Last year

            for entry in watchlist:
                try:
                    self.sync_symbol_bars(entry.symbol.code, start, end)
                except Exception as e:
                    print(f"Failed to sync {entry.symbol.code}: {e}")

    def _detect_source(self, symbol_code: str) -> str:
        """Auto-detect data source from symbol code."""
        if symbol_code.endswith(".SZ") or symbol_code.endswith(".SH") or symbol_code.endswith(".BJ"):
            return "akshare"
        elif symbol_code.endswith(".HK") or symbol_code.isalpha():
            return "yahoo"
        elif "USDT" in symbol_code or "BTC" in symbol_code or "ETH" in symbol_code:
            return "binance"
        else:
            raise ValueError(f"Cannot auto-detect source for symbol: {symbol_code}")

    def _get_market_from_source(self, source: str) -> str:
        """Get market name from source."""
        mapping = {
            "akshare": "CN",
            "yahoo": "US",
            "binance": "CRYPTO",
        }
        return mapping.get(source, "UNKNOWN")

    def get_last_update(self, symbol_code: str) -> Optional[date]:
        """Get the last update date for a symbol."""
        with self._db.get_session() as session:
            symbol = session.query(Symbol).filter_by(code=symbol_code).first()
            if symbol is None:
                return None

            result = (
                session.query(DailyBar.date)
                .filter_by(symbol_id=symbol.id)
                .order_by(DailyBar.date.desc())
                .first()
            )
            return result[0] if result else None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/test_sync.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add data sync engine

- Register and manage multiple fetchers
- Sync symbol lists and daily bars
- Auto-detect data source from symbol
- Watchlist batch sync
- Duplicate detection and prevention

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Create Unified Data API

**Files:**
- Create: `trader_center/data_hub/api.py`
- Test: `tests/data_hub/test_api.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd

from trader_center.data_hub import api


class TestDataAPI:
    @patch("trader_center.data_hub.api.get_db")
    def test_get_daily_bars(self, mock_get_db):
        mock_session = Mock()
        mock_get_db.return_value.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_get_db.return_value.get_session.return_value.__exit__ = Mock(return_value=False)

        # Mock symbol and bars query
        mock_symbol = Mock()
        mock_symbol.id = 1
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_symbol

        mock_bars = [
            Mock(date=date(2024, 1, 15), open=100.0, high=102.0, low=99.0, close=101.0, volume=1000000),
            Mock(date=date(2024, 1, 16), open=101.0, high=103.0, low=100.0, close=102.0, volume=1200000),
        ]
        mock_session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_bars

        result = api.get_daily_bars("000001.SZ", date(2024, 1, 1), date(2024, 1, 31))

        assert len(result) == 2
        assert "close" in result.columns
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

from trader_center.data_hub.database import get_db
from trader_center.data_hub.models import Symbol, DailyBar, Watchlist
from trader_center.data_hub.sync import DataSync


def get_daily_bars(
    symbol: str,
    start: str | date | datetime,
    end: str | date | datetime,
    adjust: bool = True,
    fields: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Get daily OHLCV bars for a symbol.

    Args:
        symbol: Symbol code (e.g., "000001.SZ")
        start: Start date
        end: End date
        adjust: Whether to apply forward adjustment
        fields: Optional list of columns to return

    Returns:
        DataFrame with OHLCV data
    """
    # Convert string dates to date objects
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d").date()
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d").date()

    db = get_db()
    with db.get_session() as session:
        sym = session.query(Symbol).filter_by(code=symbol).first()
        if sym is None:
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "volume", "amount"]
            )

        query = (
            session.query(DailyBar)
            .filter_by(symbol_id=sym.id)
            .filter(DailyBar.date >= start, DailyBar.date <= end)
            .order_by(DailyBar.date)
        )

        bars = query.all()

        if not bars:
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "volume", "amount"]
            )

        data = []
        for bar in bars:
            data.append({
                "date": bar.date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "amount": bar.amount,
            })

        df = pd.DataFrame(data)

        if fields:
            df = df[["date"] + [f for f in fields if f in df.columns]]

        return df


def get_symbols(market: Optional[str] = None) -> pd.DataFrame:
    """
    Get all symbols.

    Args:
        market: Optional market filter (CN, US, CRYPTO)

    Returns:
        DataFrame with symbol info
    """
    db = get_db()
    with db.get_session() as session:
        query = session.query(Symbol)

        if market:
            query = query.filter_by(market=market)

        symbols = query.all()

        data = []
        for s in symbols:
            data.append({
                "code": s.code,
                "name": s.name,
                "market": s.market,
                "exchange": s.exchange,
                "category": s.category,
            })

        return pd.DataFrame(data)


def get_watchlist(group: str = "default") -> pd.DataFrame:
    """
    Get watchlist symbols.

    Args:
        group: Watchlist group name

    Returns:
        DataFrame with watchlist entries
    """
    db = get_db()
    with db.get_session() as session:
        entries = (
            session.query(Watchlist)
            .filter_by(group_name=group)
            .all()
        )

        data = []
        for e in entries:
            data.append({
                "code": e.symbol.code,
                "name": e.symbol.name,
                "group": e.group_name,
                "notes": e.notes,
                "added_at": e.added_at,
            })

        return pd.DataFrame(data)


def add_to_watchlist(
    symbol_code: str,
    group: str = "default",
    notes: Optional[str] = None,
) -> bool:
    """
    Add a symbol to watchlist.

    Args:
        symbol_code: Symbol code
        group: Watchlist group
        notes: Optional notes

    Returns:
        True if added, False if already exists
    """
    db = get_db()
    with db.get_session() as session:
        symbol = session.query(Symbol).filter_by(code=symbol_code).first()
        if symbol is None:
            raise ValueError(f"Symbol not found: {symbol_code}")

        existing = (
            session.query(Watchlist)
            .filter_by(symbol_id=symbol.id, group_name=group)
            .first()
        )

        if existing:
            return False

        watch = Watchlist(symbol_id=symbol.id, group_name=group, notes=notes)
        session.add(watch)
        session.commit()
        return True


def remove_from_watchlist(symbol_code: str, group: str = "default") -> bool:
    """
    Remove a symbol from watchlist.

    Args:
        symbol_code: Symbol code
        group: Watchlist group

    Returns:
        True if removed, False if not found
    """
    db = get_db()
    with db.get_session() as session:
        symbol = session.query(Symbol).filter_by(code=symbol_code).first()
        if symbol is None:
            return False

        watch = (
            session.query(Watchlist)
            .filter_by(symbol_id=symbol.id, group_name=group)
            .first()
        )

        if watch is None:
            return False

        session.delete(watch)
        session.commit()
        return True


def ensure_data(
    symbol: str,
    days: int = 365,
    source: Optional[str] = None,
) -> None:
    """
    Ensure data exists for a symbol, fetching if necessary.

    Args:
        symbol: Symbol code
        days: Number of days of data to ensure
        source: Data source (auto-detected if not provided)
    """
    db = get_db()
    sync = DataSync()

    # Register default fetchers if needed
    try:
        from trader_center.data_hub.fetchers.akshare_fetcher import AkShareFetcher
        from trader_center.data_hub.fetchers.yahoo_fetcher import YahooFetcher
        from trader_center.data_hub.fetchers.binance_fetcher import BinanceFetcher

        sync.register_fetcher("akshare", AkShareFetcher())
        sync.register_fetcher("yahoo", YahooFetcher())
        sync.register_fetcher("binance", BinanceFetcher())
    except ImportError:
        pass

    end = date.today()
    start = end - timedelta(days=days)

    with db.get_session() as session:
        sym = session.query(Symbol).filter_by(code=symbol).first()

        if sym is None:
            # Need to fetch data
            sync.sync_symbol_bars(symbol, start, end, source=source)
            return

        # Check if we have recent data
        latest = (
            session.query(DailyBar)
            .filter_by(symbol_id=sym.id)
            .order_by(DailyBar.date.desc())
            .first()
        )

        if latest is None or latest.date < end - timedelta(days=7):
            # Data is stale, sync
            sync.sync_symbol_bars(symbol, start, end, source=source)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/data_hub/test_api.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add unified data API

- get_daily_bars() for historical data
- get_symbols() for symbol list
- get_watchlist() / add_to_watchlist() / remove_from_watchlist()
- ensure_data() for on-demand data fetching
- Date range filtering and column selection

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 5: Backtest Engine

### Task 10: Implement Vectorized Backtest

**Files:**
- Create: `trader_center/backtest/vectorized/engine.py`
- Create: `trader_center/backtest/metrics.py`
- Test: `tests/backtest/test_vectorized.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
import pandas as pd
import numpy as np

from trader_center.backtest.vectorized import Engine, BacktestResult


class TestVectorizedBacktest:
    def test_simple_buy_and_hold(self):
        # Create sample data
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            "date": dates.date,
            "open": [100.0] * 10,
            "high": [105.0] * 10,
            "low": [95.0] * 10,
            "close": [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0],
            "volume": [1000000] * 10,
        })

        # Buy and hold signal (1 = buy/hold, 0 = flat, -1 = short)
        signals = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

        engine = Engine(initial_cash=100000, commission=0.001)
        result = engine.run(df, signals)

        assert isinstance(result, BacktestResult)
        assert result.total_return > 0  # Price went up
        assert len(result.trades) == 1  # One entry, hold to end

    def test_empty_signals(self):
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            "date": dates.date,
            "open": [100.0] * 5,
            "high": [105.0] * 5,
            "low": [95.0] * 5,
            "close": [100.0, 101.0, 102.0, 103.0, 104.0],
            "volume": [1000000] * 5,
        })

        signals = pd.Series([0, 0, 0, 0, 0])

        engine = Engine(initial_cash=100000)
        result = engine.run(df, signals)

        assert result.total_return == 0
        assert len(result.trades) == 0
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
# trader_center/backtest/vectorized/engine.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd
import numpy as np


@dataclass
class Trade:
    """Represents a completed trade."""
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    return_pct: float
    side: str  # "long" or "short"


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    initial_cash: float
    final_equity: float
    total_return: float
    total_return_pct: float
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: dict


class Engine:
    """Vectorized backtest engine for rapid strategy testing."""

    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        slippage: float = 0.0,
    ):
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage

    def run(
        self,
        data: pd.DataFrame,
        signals: pd.Series,
    ) -> BacktestResult:
        """
        Run vectorized backtest.

        Args:
            data: DataFrame with OHLCV data
            signals: Series with signals (1=buy, -1=sell, 0=hold/flat)

        Returns:
            BacktestResult with performance metrics
        """
        df = data.copy()
        df["signal"] = signals.values

        # Calculate position changes
        df["position"] = df["signal"].shift(1).fillna(0)  # Lag by 1 to avoid lookahead

        # Calculate returns
        df["returns"] = df["close"].pct_change()
        df["strategy_returns"] = df["position"] * df["returns"]

        # Apply commission on position changes
        position_changes = df["position"].diff().abs()
        df["commission_cost"] = position_changes * self.commission
        df["strategy_returns"] -= df["commission_cost"]

        # Calculate equity curve
        df["cumulative_returns"] = (1 + df["strategy_returns"].fillna(0)).cumprod()
        df["equity"] = self.initial_cash * df["cumulative_returns"]

        # Generate trades
        trades = self._extract_trades(df)

        # Calculate metrics
        metrics = self._calculate_metrics(df, trades)

        final_equity = df["equity"].iloc[-1]
        total_return = final_equity - self.initial_cash
        total_return_pct = total_return / self.initial_cash

        return BacktestResult(
            initial_cash=self.initial_cash,
            final_equity=final_equity,
            total_return=total_return,
            total_return_pct=total_return_pct,
            trades=trades,
            equity_curve=df[["date", "equity", "close"]].copy(),
            metrics=metrics,
        )

    def _extract_trades(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract individual trades from position data."""
        trades = []
        position = 0
        entry_date = None
        entry_price = None

        for _, row in df.iterrows():
            new_position = row["position"]

            # Entry
            if position == 0 and new_position != 0:
                position = new_position
                entry_date = row["date"]
                entry_price = row["close"]

            # Exit
            elif position != 0 and new_position == 0:
                exit_price = row["close"]
                pnl = (exit_price - entry_price) * position
                return_pct = (exit_price - entry_price) / entry_price * position

                trades.append({
                    "entry_date": entry_date,
                    "exit_date": row["date"],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "side": "long" if position > 0 else "short",
                    "pnl": pnl,
                    "return_pct": return_pct,
                })

                position = 0
                entry_date = None
                entry_price = None

            # Position flip
            elif position != 0 and new_position != 0 and position != new_position:
                # Close current position
                exit_price = row["close"]
                pnl = (exit_price - entry_price) * position
                return_pct = (exit_price - entry_price) / entry_price * position

                trades.append({
                    "entry_date": entry_date,
                    "exit_date": row["date"],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "side": "long" if position > 0 else "short",
                    "pnl": pnl,
                    "return_pct": return_pct,
                })

                # Open new position
                position = new_position
                entry_date = row["date"]
                entry_price = row["close"]

        # Close open position at end
        if position != 0:
            last_row = df.iloc[-1]
            exit_price = last_row["close"]
            pnl = (exit_price - entry_price) * position
            return_pct = (exit_price - entry_price) / entry_price * position

            trades.append({
                "entry_date": entry_date,
                "exit_date": last_row["date"],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "side": "long" if position > 0 else "short",
                "pnl": pnl,
                "return_pct": return_pct,
            })

        return pd.DataFrame(trades)

    def _calculate_metrics(self, df: pd.DataFrame, trades: pd.DataFrame) -> dict:
        """Calculate performance metrics."""
        equity = df["equity"]
        returns = df["strategy_returns"].dropna()

        # Total return
        total_return = (equity.iloc[-1] - self.initial_cash) / self.initial_cash

        # Annualized return (assuming 252 trading days)
        n_days = len(df)
        annualized_return = (1 + total_return) ** (252 / n_days) - 1 if n_days > 0 else 0

        # Volatility
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0

        # Sharpe ratio (assuming 0 risk-free rate)
        sharpe = annualized_return / volatility if volatility > 0 else 0

        # Max drawdown
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_drawdown = drawdown.min()

        # Trade metrics
        if len(trades) > 0:
            win_rate = (trades["pnl"] > 0).mean()
            avg_win = trades[trades["pnl"] > 0]["pnl"].mean() if (trades["pnl"] > 0).any() else 0
            avg_loss = trades[trades["pnl"] < 0]["pnl"].mean() if (trades["pnl"] < 0).any() else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "num_trades": len(trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
        }
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/backtest/test_vectorized.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add vectorized backtest engine

- Fast vectorized backtesting with pandas
- Trade extraction and tracking
- Performance metrics (return, sharpe, drawdown)
- Commission and slippage support

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 11: Implement Event-Driven Backtest

**Files:**
- Create: `trader_center/backtest/event_driven/events.py`
- Create: `trader_center/backtest/event_driven/broker.py`
- Create: `trader_center/backtest/event_driven/portfolio.py`
- Create: `trader_center/backtest/event_driven/strategy.py`
- Create: `trader_center/backtest/event_driven/engine.py`
- Test: `tests/backtest/test_event_driven.py`

**Step 1: Write failing test**

```python
import pytest
from datetime import date
import pandas as pd

from trader_center.backtest.event_driven import (
    EventEngine, Strategy, Broker, Portfolio
)


class TestEventDrivenBacktest:
    def test_event_engine_initialization(self):
        engine = EventEngine()
        assert engine is not None

    def test_portfolio(self):
        portfolio = Portfolio(initial_cash=100000)
        assert portfolio.cash == 100000
        assert portfolio.total_value == 100000

    def test_broker(self):
        broker = Broker(commission=0.001)
        assert broker.commission == 0.001
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
# trader_center/backtest/event_driven/events.py
from dataclasses import dataclass
from datetime import date
from typing import Optional
from enum import Enum


class EventType(Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"


@dataclass
class Event:
    """Base event class."""
    event_type: EventType
    timestamp: date


@dataclass
class MarketEvent(Event):
    """New market data event."""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __init__(self, timestamp: date, symbol: str, open: float, high: float,
                 low: float, close: float, volume: float):
        super().__init__(EventType.MARKET, timestamp)
        self.symbol = symbol
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


@dataclass
class SignalEvent(Event):
    """Strategy signal event."""
    symbol: str
    signal: str  # "BUY", "SELL", "EXIT"
    strength: float = 1.0

    def __init__(self, timestamp: date, symbol: str, signal: str, strength: float = 1.0):
        super().__init__(EventType.SIGNAL, timestamp)
        self.symbol = symbol
        self.signal = signal
        self.strength = strength


@dataclass
class OrderEvent(Event):
    """Order request event."""
    symbol: str
    order_type: str  # "MARKET", "LIMIT"
    direction: str  # "BUY", "SELL"
    quantity: float
    price: Optional[float] = None

    def __init__(self, timestamp: date, symbol: str, order_type: str,
                 direction: str, quantity: float, price: Optional[float] = None):
        super().__init__(EventType.ORDER, timestamp)
        self.symbol = symbol
        self.order_type = order_type
        self.direction = direction
        self.quantity = quantity
        self.price = price


@dataclass
class FillEvent(Event):
    """Order fill event."""
    symbol: str
    direction: str
    quantity: float
    fill_price: float
    commission: float

    def __init__(self, timestamp: date, symbol: str, direction: str,
                 quantity: float, fill_price: float, commission: float):
        super().__init__(EventType.FILL, timestamp)
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity
        self.fill_price = fill_price
        self.commission = commission
```

```python
# trader_center/backtest/event_driven/broker.py
from datetime import date
from typing import Optional

from trader_center.backtest.event_driven.events import (
    OrderEvent, FillEvent, MarketEvent
)


class Broker:
    """Simulated broker execution."""

    def __init__(
        self,
        commission: float = 0.001,
        slippage: float = 0.0,
    ):
        self.commission = commission
        self.slippage = slippage

    def execute_order(
        self,
        order: OrderEvent,
        market_data: dict[str, MarketEvent],
    ) -> Optional[FillEvent]:
        """
        Execute an order and return fill event.

        Args:
            order: Order to execute
            market_data: Current market data for all symbols

        Returns:
            FillEvent if order filled, None otherwise
        """
        if order.symbol not in market_data:
            return None

        market = market_data[order.symbol]

        # Determine fill price
        if order.order_type == "MARKET":
            if order.direction == "BUY":
                fill_price = market.close * (1 + self.slippage)
            else:
                fill_price = market.close * (1 - self.slippage)
        elif order.order_type == "LIMIT" and order.price:
            # Simple limit order logic
            if order.direction == "BUY" and market.low <= order.price:
                fill_price = order.price
            elif order.direction == "SELL" and market.high >= order.price:
                fill_price = order.price
            else:
                return None
        else:
            return None

        # Calculate commission
        trade_value = fill_price * order.quantity
        commission = trade_value * self.commission

        return FillEvent(
            timestamp=market.timestamp,
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            fill_price=fill_price,
            commission=commission,
        )
```

```python
# trader_center/backtest/event_driven/portfolio.py
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from trader_center.backtest.event_driven.events import FillEvent


@dataclass
class Position:
    """Position in a symbol."""
    symbol: str
    quantity: float
    avg_cost: float

    @property
    def market_value(self, price: float) -> float:
        return self.quantity * price

    @property
    def unrealized_pnl(self, price: float) -> float:
        return self.quantity * (price - self.avg_cost)


class Portfolio:
    """Portfolio tracking positions and cash."""

    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.trade_history: list[dict] = []
        self.equity_curve: list[dict] = []

    @property
    def total_value(self) -> float:
        """Total portfolio value (cash + positions)."""
        position_value = sum(
            pos.quantity * pos.avg_cost for pos in self.positions.values()
        )
        return self.cash + position_value

    def update_fill(self, fill: FillEvent) -> None:
        """Update portfolio with a fill event."""
        trade_value = fill.fill_price * fill.quantity
        commission = fill.commission
        total_cost = trade_value + commission

        if fill.direction == "BUY":
            self.cash -= total_cost

            if fill.symbol in self.positions:
                # Update existing position
                pos = self.positions[fill.symbol]
                total_quantity = pos.quantity + fill.quantity
                total_cost_basis = (pos.quantity * pos.avg_cost) + trade_value
                pos.quantity = total_quantity
                pos.avg_cost = total_cost_basis / total_quantity
            else:
                # New position
                self.positions[fill.symbol] = Position(
                    symbol=fill.symbol,
                    quantity=fill.quantity,
                    avg_cost=fill.fill_price,
                )
        else:  # SELL
            self.cash += trade_value - commission

            if fill.symbol in self.positions:
                pos = self.positions[fill.symbol]
                pos.quantity -= fill.quantity

                # Calculate realized PnL
                realized_pnl = (fill.fill_price - pos.avg_cost) * fill.quantity

                if pos.quantity == 0:
                    del self.positions[fill.symbol]

                # Record trade
                self.trade_history.append({
                    "date": fill.timestamp,
                    "symbol": fill.symbol,
                    "direction": fill.direction,
                    "quantity": fill.quantity,
                    "price": fill.fill_price,
                    "commission": fill.commission,
                    "realized_pnl": realized_pnl,
                })

    def record_equity(self, timestamp: date, prices: dict[str, float]) -> None:
        """Record equity at a point in time."""
        position_value = sum(
            pos.quantity * prices.get(sym, pos.avg_cost)
            for sym, pos in self.positions.items()
        )

        self.equity_curve.append({
            "date": timestamp,
            "cash": self.cash,
            "position_value": position_value,
            "total": self.cash + position_value,
        })
```

```python
# trader_center/backtest/event_driven/strategy.py
from abc import ABC, abstractmethod
from typing import Optional

from trader_center.backtest.event_driven.events import (
    MarketEvent, SignalEvent
)


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    @abstractmethod
    def on_bar(self, event: MarketEvent) -> Optional[SignalEvent]:
        """
        Process a market bar and generate signal.

        Args:
            event: Market data event

        Returns:
            SignalEvent if signal generated, None otherwise
        """
        pass

    def on_start(self) -> None:
        """Called at the start of backtest."""
        pass

    def on_end(self) -> None:
        """Called at the end of backtest."""
        pass
```

```python
# trader_center/backtest/event_driven/engine.py
from collections import deque
from datetime import date
from typing import Optional
import pandas as pd

from trader_center.backtest.event_driven.events import (
    Event, EventType, MarketEvent, SignalEvent, OrderEvent, FillEvent
)
from trader_center.backtest.event_driven.broker import Broker
from trader_center.backtest.event_driven.portfolio import Portfolio
from trader_center.backtest.event_driven.strategy import Strategy


class EventEngine:
    """Event-driven backtest engine."""

    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        slippage: float = 0.0,
    ):
        self.initial_cash = initial_cash
        self.broker = Broker(commission=commission, slippage=slippage)
        self.portfolio = Portfolio(initial_cash=initial_cash)

        self._events: deque[Event] = deque()
        self._strategy: Optional[Strategy] = None
        self._current_data: dict[str, MarketEvent] = {}

    def set_strategy(self, strategy: Strategy) -> None:
        """Set the trading strategy."""
        self._strategy = strategy

    def run(self, data: pd.DataFrame) -> dict:
        """
        Run backtest on historical data.

        Args:
            data: DataFrame with OHLCV data, must have 'date' column

        Returns:
            Dictionary with backtest results
        """
        if self._strategy is None:
            raise ValueError("Strategy must be set before running backtest")

        self._strategy.on_start()

        for _, row in data.iterrows():
            # Create market event
            market_event = MarketEvent(
                timestamp=row["date"],
                symbol=row.get("symbol", "UNKNOWN"),
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )

            # Update current market data
            self._current_data[market_event.symbol] = market_event

            # Process market event through strategy
            signal = self._strategy.on_bar(market_event)

            if signal:
                # Convert signal to order
                direction = "BUY" if signal.signal == "BUY" else "SELL"
                order = OrderEvent(
                    timestamp=market_event.timestamp,
                    symbol=signal.symbol,
                    order_type="MARKET",
                    direction=direction,
                    quantity=100,  # Fixed size for simplicity
                )

                # Execute order
                fill = self.broker.execute_order(order, self._current_data)

                if fill:
                    self.portfolio.update_fill(fill)

            # Record equity
            prices = {sym: evt.close for sym, evt in self._current_data.items()}
            self.portfolio.record_equity(market_event.timestamp, prices)

        self._strategy.on_end()

        return self._generate_results()

    def _generate_results(self) -> dict:
        """Generate backtest results."""
        equity_df = pd.DataFrame(self.portfolio.equity_curve)

        if len(equity_df) == 0:
            return {
                "total_return": 0,
                "trades": pd.DataFrame(),
                "equity_curve": equity_df,
            }

        final_equity = equity_df["total"].iloc[-1]
        total_return = (final_equity - self.initial_cash) / self.initial_cash

        trades_df = pd.DataFrame(self.portfolio.trade_history)

        return {
            "initial_cash": self.initial_cash,
            "final_equity": final_equity,
            "total_return": total_return,
            "trades": trades_df,
            "equity_curve": equity_df,
        }
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/backtest/test_event_driven.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add event-driven backtest engine

- Event system (Market, Signal, Order, Fill)
- Broker simulation with commission/slippage
- Portfolio tracking positions and PnL
- Strategy base class
- EventEngine for running backtests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 6: Market Monitor

### Task 12: Implement Watchlist Management

**Files:**
- Create: `trader_center/monitor/watchlist.py`
- Test: `tests/monitor/test_watchlist.py`

**Step 1: Write failing test**

```python
import pytest
from unittest.mock import Mock, patch

from trader_center.monitor.watchlist import WatchlistManager


class TestWatchlistManager:
    @patch("trader_center.monitor.watchlist.get_db")
    def test_list_groups(self, mock_get_db):
        mock_session = Mock()
        mock_result = [Mock(group_name="default"), Mock(group_name="tech")]
        mock_session.query.return_value.distinct.return_value.all.return_value = mock_result
        mock_get_db.return_value.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_get_db.return_value.get_session.return_value.__exit__ = Mock(return_value=False)

        manager = WatchlistManager()
        groups = manager.list_groups()
        assert "default" in groups
        assert "tech" in groups
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
from typing import Optional

import pandas as pd

from trader_center.data_hub.database import get_db
from trader_center.data_hub.models import Symbol, Watchlist


class WatchlistManager:
    """Manage watchlist groups and entries."""

    def __init__(self):
        self._db = get_db()

    def list_groups(self) -> list[str]:
        """Get all watchlist group names."""
        with self._db.get_session() as session:
            groups = (
                session.query(Watchlist.group_name)
                .distinct()
                .all()
            )
            return [g[0] for g in groups]

    def get_group(self, group_name: str = "default") -> pd.DataFrame:
        """Get all symbols in a watchlist group."""
        from trader_center.data_hub.api import get_watchlist
        return get_watchlist(group_name)

    def add(
        self,
        symbol_code: str,
        group: str = "default",
        notes: Optional[str] = None,
    ) -> bool:
        """Add a symbol to a watchlist group."""
        from trader_center.data_hub.api import add_to_watchlist, ensure_data

        # Ensure we have the symbol in database
        ensure_data(symbol_code, days=30)

        return add_to_watchlist(symbol_code, group, notes)

    def remove(self, symbol_code: str, group: str = "default") -> bool:
        """Remove a symbol from a watchlist group."""
        from trader_center.data_hub.api import remove_from_watchlist
        return remove_from_watchlist(symbol_code, group)

    def get_prices(self, group: str = "default") -> pd.DataFrame:
        """Get current prices for all symbols in a group."""
        from trader_center.data_hub.api import get_daily_bars, ensure_data
        from datetime import date, timedelta

        symbols = self.get_group(group)

        if symbols.empty:
            return pd.DataFrame()

        end = date.today()
        start = end - timedelta(days=5)

        data = []
        for _, row in symbols.iterrows():
            code = row["code"]
            try:
                ensure_data(code, days=5)
                bars = get_daily_bars(code, start, end)
                if not bars.empty:
                    latest = bars.iloc[-1]
                    prev = bars.iloc[-2] if len(bars) > 1 else latest
                    change = latest["close"] - prev["close"]
                    change_pct = change / prev["close"] * 100

                    data.append({
                        "code": code,
                        "name": row["name"],
                        "price": latest["close"],
                        "change": change,
                        "change_pct": change_pct,
                        "volume": latest["volume"],
                    })
            except Exception as e:
                # Skip symbols that fail to load
                continue

        return pd.DataFrame(data)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/monitor/test_watchlist.py -v
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add watchlist manager

- List and manage watchlist groups
- Add/remove symbols from watchlist
- Get current prices for watchlist symbols
- Auto-fetch missing data

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 13: Implement Market Overview

**Files:**
- Create: `trader_center/monitor/market_overview.py`
- Test: `tests/monitor/test_market_overview.py`

**Step 1: Write implementation**

```python
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from trader_center.data_hub.api import get_daily_bars


# Major indices to track
INDICES = {
    "CN": [
        ("000001.SH", "上证指数"),
        ("399001.SZ", "深证成指"),
        ("399006.SZ", "创业板指"),
        ("000300.SH", "沪深300"),
        ("000905.SH", "中证500"),
    ],
    "US": [
        ("^GSPC", "S\u0026P 500"),
        ("^DJI", "道琼斯"),
        ("^IXIC", "纳斯达克"),
    ],
    "HK": [
        ("^HSI", "恒生指数"),
        ("^HSTECH", "恒生科技"),
    ],
}


class MarketOverview:
    """Generate market overview reports."""

    def __init__(self):
        pass

    def get_index_data(self, market: str = "CN") -> pd.DataFrame:
        """Get major indices data for a market."""
        indices = INDICES.get(market, [])

        end = date.today()
        start = end - timedelta(days=5)

        data = []
        for code, name in indices:
            try:
                bars = get_daily_bars(code, start, end)
                if not bars.empty:
                    latest = bars.iloc[-1]
                    prev = bars.iloc[-2] if len(bars) > 1 else latest
                    change = latest["close"] - prev["close"]
                    change_pct = change / prev["close"] * 100

                    data.append({
                        "code": code,
                        "name": name,
                        "price": latest["close"],
                        "change": change,
                        "change_pct": change_pct,
                        "volume": latest.get("volume", 0),
                    })
            except Exception:
                continue

        return pd.DataFrame(data)

    def get_market_summary(self, market: str = "CN") -> dict:
        """Get market summary statistics."""
        # This would need market breadth data which requires
        # fetching all stocks in the market
        # For now, return basic index info
        indices = self.get_index_data(market)

        if indices.empty:
            return {}

        return {
            "market": market,
            "indices": indices.to_dict("records"),
            "avg_change": indices["change_pct"].mean(),
        }
```

**Step 2: Commit**

```bash
git add .
git commit -m "feat: add market overview

- Track major indices (CN/US/HK)
- Calculate price changes and percentages
- Market summary statistics

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 14: Create Daily Report Generator

**Files:**
- Create: `trader_center/monitor/report.py`
- Create: `trader_center/monitor/templates/daily_report.md`

**Step 1: Write implementation**

```python
from datetime import date
from pathlib import Path
from typing import Optional

from jinja2 import Template

from trader_center.monitor.market_overview import MarketOverview, INDICES
from trader_center.monitor.watchlist import WatchlistManager


DEFAULT_TEMPLATE = """# 监测报告 - {{ date }}

## 市场概览

### 主要指数

{% for idx in indices %}
- **{{ idx.name }}** ({{ idx.code }}): {{ "%.2f"|format(idx.price) }} ({{ "%.2f"|format(idx.change_pct) }}%)
{%- endfor %}

### 自选股监控

{% if watchlist.empty %}
暂无自选股
{% else %}
| 代码 | 名称 | 价格 | 涨跌 | 涨跌幅 |
|------|------|------|------|--------|
{% for _, row in watchlist.iterrows() %}
| {{ row.code }} | {{ row.name }} | {{ "%.2f"|format(row.price) }} | {{ "%.2f"|format(row.change) }} | {{ "%.2f"|format(row.change_pct) }}% |
{%- endfor %}
{% endif %}

---
*生成时间: {{ timestamp }}*
"""


class ReportGenerator:
    """Generate daily market reports."""

    def __init__(self, template_path: Optional[Path] = None):
        if template_path and template_path.exists():
            with open(template_path) as f:
                self.template = Template(f.read())
        else:
            self.template = Template(DEFAULT_TEMPLATE)

        self.overview = MarketOverview()
        self.watchlist = WatchlistManager()

    def generate(self, market: str = "CN", group: str = "default") -> str:
        """Generate daily report as markdown."""
        from datetime import datetime

        indices = self.overview.get_index_data(market)
        watchlist = self.watchlist.get_prices(group)

        return self.template.render(
            date=date.today().strftime("%Y-%m-%d"),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            indices=indices.to_dict("records") if not indices.empty else [],
            watchlist=watchlist,
        )

    def save(self, output_path: Path, market: str = "CN", group: str = "default") -> Path:
        """Generate and save report to file."""
        report = self.generate(market, group)
        output_path.write_text(report, encoding="utf-8")
        return output_path
```

**Step 2: Commit**

```bash
git add .
git commit -m "feat: add daily report generator

- Markdown report with indices and watchlist
- Jinja2 templating support
- Default template in Chinese

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 7: CLI Interface

### Task 15: Create CLI Entry Point

**Files:**
- Create: `trader_center/cli.py`
- Create: `trader_center/config.py`

**Step 1: Write implementation**

```python
# trader_center/config.py
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="",
        description="SQLite database URL (empty = use default path)",
    )

    # Data sources
    tushare_token: str = Field(default="", description="Tushare API token")
    binance_api_key: str = Field(default="", description="Binance API key")
    binance_api_secret: str = Field(default="", description="Binance API secret")

    # Paths
    data_dir: Path = Field(
        default=Path.home() / ".trader_center" / "data",
        description="Data directory path",
    )

    @property
    def db_path(self) -> Path:
        """Get database file path."""
        if self.database_url:
            # Extract path from sqlite URL
            if self.database_url.startswith("sqlite:///"):
                return Path(self.database_url[10:])
        return self.data_dir / "trader_center.db"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
```

```python
# trader_center/cli.py
import sys
from pathlib import Path
from typing import Optional

import click

from trader_center.config import get_settings
from trader_center.data_hub.database import DatabaseManager
from trader_center.data_hub.sync import DataSync
from trader_center.data_hub.fetchers.akshare_fetcher import AkShareFetcher
from trader_center.data_hub.fetchers.yahoo_fetcher import YahooFetcher
from trader_center.data_hub.fetchers.binance_fetcher import BinanceFetcher
from trader_center.monitor.watchlist import WatchlistManager
from trader_center.monitor.market_overview import MarketOverview
from trader_center.monitor.report import ReportGenerator


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Trader Center - Personal financial market research framework."""
    pass


@cli.command()
def init():
    """Initialize database and configuration."""
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager()
    db.init_database(str(settings.db_path))

    click.echo(f"✓ Database initialized at {settings.db_path}")


@cli.group()
def data():
    """Data management commands."""
    pass


@data.command("sync")
@click.option("--source", default="akshare", help="Data source to sync")
@click.option("--symbol", help="Sync specific symbol")
def sync_data(source: str, symbol: Optional[str]):
    """Sync data from external sources."""
    db = DatabaseManager()
    db.init_database()

    sync = DataSync()

    # Register fetchers
    if source == "akshare":
        sync.register_fetcher("akshare", AkShareFetcher())
    elif source == "yahoo":
        sync.register_fetcher("yahoo", YahooFetcher())
    elif source == "binance":
        settings = get_settings()
        sync.register_fetcher(
            "binance",
            BinanceFetcher(settings.binance_api_key, settings.binance_api_secret)
        )
    else:
        click.echo(f"Unknown source: {source}", err=True)
        sys.exit(1)

    if symbol:
        from datetime import date, timedelta
        count = sync.sync_symbol_bars(symbol, date.today() - timedelta(days=365), date.today())
        click.echo(f"✓ Synced {count} bars for {symbol}")
    else:
        count = sync.sync_symbols(source)
        click.echo(f"✓ Synced {count} symbols from {source}")


@cli.group()
def watchlist():
    """Watchlist management commands."""
    pass


@watchlist.command("list")
@click.option("--group", default="default", help="Watchlist group")
def list_watchlist(group: str):
    """List symbols in watchlist."""
    db = DatabaseManager()
    db.init_database()

    manager = WatchlistManager()
    symbols = manager.get_group(group)

    if symbols.empty:
        click.echo(f"No symbols in group '{group}'")
        return

    click.echo(f"\nWatchlist: {group}\n")
    for _, row in symbols.iterrows():
        click.echo(f"  {row['code']} - {row['name']}")


@watchlist.command("add")
@click.argument("symbol")
@click.option("--group", default="default", help="Watchlist group")
@click.option("--notes", help="Optional notes")
def add_to_watchlist(symbol: str, group: str, notes: Optional[str]):
    """Add a symbol to watchlist."""
    db = DatabaseManager()
    db.init_database()

    manager = WatchlistManager()
    success = manager.add(symbol, group, notes)

    if success:
        click.echo(f"✓ Added {symbol} to {group}")
    else:
        click.echo(f"! {symbol} already in {group}")


@watchlist.command("remove")
@click.argument("symbol")
@click.option("--group", default="default", help="Watchlist group")
def remove_from_watchlist(symbol: str, group: str):
    """Remove a symbol from watchlist."""
    db = DatabaseManager()
    db.init_database()

    manager = WatchlistManager()
    success = manager.remove(symbol, group)

    if success:
        click.echo(f"✓ Removed {symbol} from {group}")
    else:
        click.echo(f"! {symbol} not found in {group}")


@cli.group()
def monitor():
    """Market monitoring commands."""
    pass


@monitor.command("overview")
@click.option("--market", default="CN", help="Market (CN/US/HK)")
def market_overview(market: str):
    """Show market overview."""
    db = DatabaseManager()
    db.init_database()

    overview = MarketOverview()
    indices = overview.get_index_data(market)

    if indices.empty:
        click.echo("No data available")
        return

    click.echo(f"\n📊 {market} Market Overview\n")
    for _, row in indices.iterrows():
        change_emoji = "🔺" if row["change"] >= 0 else "🔻"
        click.echo(
            f"  {row['name']}: {row['price']:.2f} "
            f"({row['change']:.2f} / {row['change_pct']:+.2f}%) {change_emoji}"
        )


@monitor.command("report")
@click.option("--market", default="CN", help="Market")
@click.option("--group", default="default", help="Watchlist group")
@click.option("--output", "-o", help="Output file path")
def generate_report(market: str, group: str, output: Optional[str]):
    """Generate daily market report."""
    db = DatabaseManager()
    db.init_database()

    generator = ReportGenerator()

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generator.save(output_path, market, group)
        click.echo(f"✓ Report saved to {output_path}")
    else:
        report = generator.generate(market, group)
        click.echo(report)


def main():
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add .
git commit -m "feat: add CLI interface

- tc init - Initialize database
- tc data sync - Sync data from sources
- tc watchlist add/remove/list - Manage watchlist
- tc monitor overview - Show market overview
- tc monitor report - Generate daily report

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 8: Final Integration

### Task 16: Create Example Scripts

**Files:**
- Create: `examples/quickstart.py`
- Create: `examples/backtest_demo.py`

**Step 1: Write examples**

```python
# examples/quickstart.py
"""Quick start example for Trader Center."""

from datetime import date, timedelta

from trader_center.data_hub.database import DatabaseManager
from trader_center.data_hub.api import get_daily_bars, add_to_watchlist


def main():
    # Initialize database
    db = DatabaseManager()
    db.init_database()
    print("✓ Database initialized")

    # Fetch data for a stock
    symbol = "000001.SZ"  # 平安银行
    end = date.today()
    start = end - timedelta(days=30)

    print(f"\nFetching data for {symbol}...")

    # Ensure data exists (will fetch if needed)
    from trader_center.data_hub.api import ensure_data
    ensure_data(symbol, days=30)

    # Get daily bars
    df = get_daily_bars(symbol, start, end)
    print(f"✓ Got {len(df)} bars")
    print(df.tail())

    # Add to watchlist
    add_to_watchlist(symbol, group="demo", notes="Quick start example")
    print(f"\n✓ Added {symbol} to watchlist")


if __name__ == "__main__":
    main()
```

```python
# examples/backtest_demo.py
"""Backtest demo using Trader Center."""

from datetime import date, timedelta

import pandas as pd
import numpy as np

from trader_center.data_hub.database import DatabaseManager
from trader_center.data_hub.api import get_daily_bars, ensure_data
from trader_center.backtest.vectorized import Engine


def ma_crossover_strategy(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> pd.Series:
    """
    Simple moving average crossover strategy.

    Buy when fast MA crosses above slow MA.
    Sell when fast MA crosses below slow MA.
    """
    df["ma_fast"] = df["close"].rolling(fast).mean()
    df["ma_slow"] = df["close"].rolling(slow).mean()

    # Generate signals
    df["signal"] = 0
    df.loc[df["ma_fast"] > df["ma_slow"], "signal"] = 1
    df.loc[df["ma_fast"] < df["ma_slow"], "signal"] = -1

    return df["signal"]


def main():
    # Initialize
    db = DatabaseManager()
    db.init_database()

    # Get data
    symbol = "000001.SZ"
    end = date.today()
    start = end - timedelta(days=365)

    print(f"Fetching data for {symbol}...")
    ensure_data(symbol, days=365)
    df = get_daily_bars(symbol, start, end)

    if df.empty:
        print("No data available")
        return

    print(f"Got {len(df)} bars")

    # Generate signals
    signals = ma_crossover_strategy(df)

    # Run backtest
    engine = Engine(
        initial_cash=100000,
        commission=0.001,
        slippage=0.001,
    )
    result = engine.run(df, signals)

    # Print results
    print("\n" + "=" * 50)
    print("回测结果")
    print("=" * 50)
    print(f"初始资金: ¥{result.initial_cash:,.2f}")
    print(f"最终权益: ¥{result.final_equity:,.2f}")
    print(f"总收益: {result.total_return_pct:.2%}")
    print(f"\n交易次数: {result.metrics['num_trades']}")
    print(f"胜率: {result.metrics['win_rate']:.2%}")
    print(f"夏普比率: {result.metrics['sharpe_ratio']:.2f}")
    print(f"最大回撤: {result.metrics['max_drawdown']:.2%}")


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add .
git commit -m "feat: add example scripts

- quickstart.py - Basic usage example
- backtest_demo.py - MA crossover backtest

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Summary

This implementation plan creates a complete personal financial market research framework with:

1. **Data Hub**: Multi-source data fetching (AkShare, Yahoo, Binance), unified API, SQLite storage
2. **Backtest Engine**: Vectorized and event-driven engines with performance metrics
3. **Market Monitor**: Watchlist management, market overview, daily reports
4. **CLI**: `tc` command with init, data, watchlist, monitor subcommands

**Execution Options:**

1. **Subagent-Driven (this session)** - Fresh subagent per task, review between tasks
2. **Parallel Session** - New session with executing-plans for batch execution

**Prerequisites:**
```bash
# Install dependencies
pip install -e ".[dev]"

# Or install manually
pip install click pydantic pydantic-settings sqlalchemy pandas numpy akshare yfinance python-binance rich pytest
```

**First command to run:**
```bash
tc init  # Initialize database
```
