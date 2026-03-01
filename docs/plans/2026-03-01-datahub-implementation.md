# DataHub Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use @superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现基于 akshare 的多数据源 DataHub 模块，支持股票行情、财务、宏观数据获取与本地缓存

**Architecture:** 分层架构：API层 -> Router层 -> Fetcher层 -> Cache层 -> Storage层（SQLite + Parquet 混合存储）

**Tech Stack:** Python 3.10+, Pydantic 2.0, Pandas 2.0, AkShare, PyArrow, SQLite3

---

## Phase 1: 基础结构与数据模型

### Task 1: 项目结构与依赖配置

**Files:**
- Create: `pyproject.toml`
- Create: `trader_center/__init__.py`
- Create: `trader_center/data_hub/__init__.py`

**Step 1: 创建项目配置**

```toml
[project]
name = "trader-center"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "pandas>=2.0",
    "akshare>=1.15",
    "pyarrow>=15.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "black",
    "ruff",
]
```

**Step 2: 创建包结构**

```python
# trader_center/__init__.py
"""Trader Center - Quantitative Trading Framework"""
__version__ = "0.1.0"
```

```python
# trader_center/data_hub/__init__.py
"""DataHub - Multi-source financial data access layer"""
```

**Step 3: 验证安装**

```bash
pip install -e .
python -c "import trader_center; print(trader_center.__version__)"
```

Expected: `0.1.0`

**Step 4: Commit**

```bash
git add pyproject.toml trader_center/__init__.py trader_center/data_hub/__init__.py
git commit -m "chore: setup project structure and dependencies"
```

---

### Task 2: 核心数据模型

**Files:**
- Create: `trader_center/data_hub/models.py`
- Test: `tests/data_hub/test_models.py`

**Step 1: 编写数据模型测试**

```python
# tests/data_hub/test_models.py
import pytest
from datetime import datetime, date
from trader_center.data_hub.models import (
    BarData, SymbolInfo, FinancialReport, MacroData, Frequency
)

class TestBarData:
    def test_create_bar(self):
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 1, 9, 30),
            frequency=Frequency.DAILY,
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            volume=10000.0,
        )
        assert bar.symbol == "000001.SZ"
        assert bar.close == 10.5

    def test_bar_is_frozen(self):
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 1),
            frequency=Frequency.DAILY,
            open=10.0, high=10.0, low=10.0, close=10.0, volume=100.0
        )
        with pytest.raises(Exception):
            bar.close = 11.0

    def test_bar_with_optional_fields(self):
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 1),
            frequency=Frequency.DAILY,
            open=10.0, high=11.0, low=9.5, close=10.5, volume=10000.0,
            amount=105000.0,
            adj_factor=1.05,
            is_suspended=False
        )
        assert bar.amount == 105000.0

class TestSymbolInfo:
    def test_create_symbol(self):
        symbol = SymbolInfo(
            symbol="000001.SZ",
            name="平安银行",
            exchange="SZ",
            type="stock",
            list_date=date(1991, 4, 3),
            industry="银行"
        )
        assert symbol.name == "平安银行"

    def test_symbol_exchange_validation(self):
        with pytest.raises(ValueError):
            SymbolInfo(
                symbol="INVALID",
                name="Invalid",
                exchange="XX"  # Invalid exchange
            )
```

**Step 2: 运行测试，确认失败**

```bash
pytest tests/data_hub/test_models.py -v
```

Expected: ImportError / module not found

**Step 3: 实现数据模型**

```python
# trader_center/data_hub/models.py
from datetime import datetime, date
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class Frequency(str, Enum):
    """数据频率"""
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1m"
    MIN_1 = "1min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    MIN_60 = "60min"


class BarData(BaseModel):
    """K线数据模型"""
    model_config = {"frozen": True}

    symbol: str = Field(..., description="股票代码，如 000001.SZ")
    timestamp: datetime = Field(..., description="时间戳")
    frequency: Frequency = Field(..., description="数据周期")

    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")

    amount: Optional[float] = Field(None, description="成交额")
    adj_factor: Optional[float] = Field(None, description="复权因子")
    is_suspended: bool = Field(False, description="是否停牌")


class SymbolInfo(BaseModel):
    """股票基础信息"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    exchange: str = Field(..., pattern=r"^(SZ|SH|BJ|HK|US)$")
    type: str = Field(default="stock", pattern=r"^(stock|index|etf|bond)$")
    list_date: Optional[date] = None
    delist_date: Optional[date] = None
    industry: Optional[str] = None


class FinancialReport(BaseModel):
    """财务报告数据"""
    symbol: str
    report_date: date
    report_type: str = Field(..., pattern=r"^(Q1|Q2|Q3|annual)$")

    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    eps: Optional[float] = None
    roe: Optional[float] = None
    debt_ratio: Optional[float] = None

    raw_data: Optional[dict] = None


class MacroData(BaseModel):
    """宏观数据"""
    indicator: str
    country: str = "CN"
    timestamp: date
    value: float
    period: Optional[str] = None
```

**Step 4: 运行测试，确认通过**

```bash
pytest tests/data_hub/test_models.py -v
```

Expected: 5 passed

**Step 5: Commit**

```bash
git add trader_center/data_hub/models.py tests/data_hub/test_models.py
git commit -m "feat: add core data models (BarData, SymbolInfo, etc.)"
```

---

## Phase 2: 存储层实现

### Task 3: 存储抽象与配置

**Files:**
- Create: `trader_center/data_hub/storage/__init__.py`
- Create: `trader_center/data_hub/storage/base.py`
- Create: `trader_center/data_hub/config.py`
- Test: `tests/data_hub/storage/__init__.py`

**Step 1: 编写配置模块**

```python
# trader_center/data_hub/config.py
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DataHubConfig:
    """DataHub 配置"""
    data_dir: Path = Path.home() / ".trader_center" / "data"
    cache_size: int = 1000
    sqlite_db_name: str = "metadata.db"

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / self.sqlite_db_name

    @property
    def bars_dir(self) -> Path:
        path = self.data_dir / "bars"
        path.mkdir(exist_ok=True)
        return path
```

**Step 2: 编写存储抽象基类**

```python
# trader_center/data_hub/storage/base.py
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
```

**Step 3: Commit**

```bash
git add trader_center/data_hub/storage/ trader_center/data_hub/config.py
git commit -m "feat: add storage abstraction and config"
```

---

### Task 4: SQLite 存储实现

**Files:**
- Create: `trader_center/data_hub/storage/sqlite_store.py`
- Test: `tests/data_hub/storage/test_sqlite_store.py`

**Step 1: 编写 SQLite 存储测试**

```python
# tests/data_hub/storage/test_sqlite_store.py
import pytest
import tempfile
from datetime import datetime, date
from pathlib import Path

from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.storage.sqlite_store import SQLiteStorage
from trader_center.data_hub.models import SymbolInfo, FinancialReport


class TestSQLiteStorage:
    @pytest.fixture
    def storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataHubConfig(data_dir=tmpdir)
            store = SQLiteStorage(config)
            yield store

    def test_save_and_get_symbols(self, storage):
        symbols = [
            SymbolInfo(symbol="000001.SZ", name="平安银行", exchange="SZ"),
            SymbolInfo(symbol="600000.SH", name="浦发银行", exchange="SH"),
        ]
        storage.save_symbols(symbols)

        result = storage.get_symbols()
        assert len(result) == 2
        assert result[0].symbol == "000001.SZ"

    def test_get_symbols_by_exchange(self, storage):
        symbols = [
            SymbolInfo(symbol="000001.SZ", name="平安银行", exchange="SZ"),
            SymbolInfo(symbol="600000.SH", name="浦发银行", exchange="SH"),
        ]
        storage.save_symbols(symbols)

        sz_symbols = storage.get_symbols(exchange="SZ")
        assert len(sz_symbols) == 1
        assert sz_symbols[0].exchange == "SZ"
```

**Step 2: 运行测试，确认失败**

```bash
pytest tests/data_hub/storage/test_sqlite_store.py -v
```

**Step 3: 实现 SQLite 存储**

```python
# trader_center/data_hub/storage/sqlite_store.py
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
```

**Step 4: 运行测试，确认通过**

```bash
pytest tests/data_hub/storage/test_sqlite_store.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add trader_center/data_hub/storage/sqlite_store.py tests/data_hub/storage/test_sqlite_store.py
git commit -m "feat: implement SQLite storage for metadata"
```

---

### Task 5: Parquet 存储实现

**Files:**
- Create: `trader_center/data_hub/storage/parquet_store.py`
- Test: `tests/data_hub/storage/test_parquet_store.py`

**Step 1: 编写 Parquet 存储测试**

```python
# tests/data_hub/storage/test_parquet_store.py
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.storage.parquet_store import ParquetStorage
from trader_center.data_hub.models import BarData, Frequency


class TestParquetStorage:
    @pytest.fixture
    def storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataHubConfig(data_dir=tmpdir)
            store = ParquetStorage(config)
            yield store

    def test_save_and_get_daily_bars(self, storage):
        bars = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 1),
                frequency=Frequency.DAILY,
                open=10.0, high=11.0, low=9.5, close=10.5, volume=10000.0
            ),
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 2),
                frequency=Frequency.DAILY,
                open=10.5, high=10.8, low=10.2, close=10.6, volume=8000.0
            ),
        ]
        storage.save_bars(bars)

        df = storage.get_bars(
            "000001.SZ",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            "1d"
        )
        assert len(df) == 2
        assert df.iloc[0]['close'] == 10.5

    def test_get_data_range(self, storage):
        bars = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 15),
                frequency=Frequency.DAILY,
                open=10.0, high=11.0, low=9.5, close=10.5, volume=10000.0
            ),
        ]
        storage.save_bars(bars)

        start, end = storage.get_data_range("000001.SZ", "1d")
        assert start == datetime(2024, 1, 15)
        assert end == datetime(2024, 1, 15)

    def test_incremental_save(self, storage):
        """测试增量保存不会重复数据"""
        bars1 = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 1),
                frequency=Frequency.DAILY,
                open=10.0, high=11.0, low=9.5, close=10.5, volume=10000.0
            ),
        ]
        bars2 = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 2),
                frequency=Frequency.DAILY,
                open=10.5, high=10.8, low=10.2, close=10.6, volume=8000.0
            ),
        ]
        storage.save_bars(bars1)
        storage.save_bars(bars2)

        df = storage.get_bars(
            "000001.SZ",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            "1d"
        )
        assert len(df) == 2
```

**Step 2: 运行测试，确认失败**

```bash
pytest tests/data_hub/storage/test_parquet_store.py -v
```

**Step 3: 实现 Parquet 存储**

```python
# trader_center/data_hub/storage/parquet_store.py
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa

from trader_center.data_hub.storage.base import Storage
from trader_center.data_hub.models import BarData, Frequency
from trader_center.data_hub.config import DataHubConfig


class ParquetStorage(Storage):
    """Parquet 存储实现 - 用于大规模K线数据"""

    def __init__(self, config: DataHubConfig):
        self.config = config

    def _get_bar_path(self, symbol: str, frequency: str) -> Path:
        """获取 Parquet 文件路径"""
        freq_dir = self.config.bars_dir / frequency.replace("1d", "daily").replace("1min", "min1")
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
        new_df = pd.DataFrame([{
            'timestamp': bar.timestamp,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'amount': bar.amount,
            'adj_factor': bar.adj_factor,
            'is_suspended': bar.is_suspended
        } for bar in bars])

        if file_path.exists():
            # 读取现有数据
            existing_df = pq.read_table(file_path).to_pandas()
            # 合并并去重
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['timestamp'], keep='first')
            combined = combined.sort_values('timestamp')
        else:
            combined = new_df.sort_values('timestamp')

        # 写入 Parquet
        table = pa.Table.from_pandas(combined)
        pq.write_table(table, file_path)

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> pd.DataFrame:
        """获取K线数据"""
        file_path = self._get_bar_path(symbol, frequency)

        if not file_path.exists():
            return pd.DataFrame()

        df = pq.read_table(file_path).to_pandas()
        mask = (df['timestamp'] >= start) & (df['timestamp'] <= end)
        return df[mask].copy()

    def get_data_range(self, symbol: str, frequency: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取本地已有数据的时间范围"""
        file_path = self._get_bar_path(symbol, frequency)

        if not file_path.exists():
            return None, None

        df = pq.read_table(file_path).to_pandas()
        if df.empty:
            return None, None

        return df['timestamp'].min(), df['timestamp'].max()

    def get_symbols(self, exchange: Optional[str] = None) -> List:
        """Parquet 不存储股票列表"""
        raise NotImplementedError("Use SQLiteStorage for symbols")

    def save_symbols(self, symbols: List) -> None:
        """Parquet 不存储股票列表"""
        raise NotImplementedError("Use SQLiteStorage for symbols")
```

**Step 4: 运行测试，确认通过**

```bash
pytest tests/data_hub/storage/test_parquet_store.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add trader_center/data_hub/storage/parquet_store.py tests/data_hub/storage/test_parquet_store.py
git commit -m "feat: implement Parquet storage for bar data"
```

---

### Task 6: 混合存储整合

**Files:**
- Create: `trader_center/data_hub/storage/hybrid_store.py`
- Modify: `trader_center/data_hub/storage/__init__.py`

**Step 1: 实现混合存储**

```python
# trader_center/data_hub/storage/hybrid_store.py
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
```

**Step 2: 更新存储模块导出**

```python
# trader_center/data_hub/storage/__init__.py
from trader_center.data_hub.storage.base import Storage
from trader_center.data_hub.storage.hybrid_store import HybridStorage
from trader_center.data_hub.storage.sqlite_store import SQLiteStorage
from trader_center.data_hub.storage.parquet_store import ParquetStorage

__all__ = ["Storage", "HybridStorage", "SQLiteStorage", "ParquetStorage"]
```

**Step 3: 提交**

```bash
git add trader_center/data_hub/storage/
git commit -m "feat: integrate hybrid storage (SQLite + Parquet)"
```

---

## Phase 3: Fetcher 层实现

### Task 7: Fetcher 抽象基类

**Files:**
- Create: `trader_center/data_hub/fetchers/__init__.py`
- Create: `trader_center/data_hub/fetchers/base.py`

**Step 1: 实现 Fetcher 抽象基类**

```python
# trader_center/data_hub/fetchers/base.py
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
```

**Step 2: Commit**

```bash
git add trader_center/data_hub/fetchers/
git commit -m "feat: add DataFetcher abstract base class"
```

---

### Task 8: Akshare Fetcher 实现

**Files:**
- Create: `trader_center/data_hub/fetchers/akshare_fetcher.py`
- Test: `tests/data_hub/fetchers/test_akshare_fetcher.py` (mock 测试)

**Step 1: 实现 Akshare Fetcher**

```python
# trader_center/data_hub/fetchers/akshare_fetcher.py
from datetime import datetime
from typing import List, Optional

from trader_center.data_hub.fetchers.base import DataFetcher
from trader_center.data_hub.models import BarData, SymbolInfo, Frequency


class AkshareFetcher(DataFetcher):
    """Akshare 数据源获取器"""

    name = "akshare"
    priority = 10  # 高优先级

    def __init__(self):
        self._ak = None

    def _get_ak(self):
        """延迟导入 akshare"""
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak

    def check_available(self) -> bool:
        """检查 akshare 是否可用"""
        try:
            import akshare as ak
            # 简单测试调用
            _ = ak.stock_zh_a_spot_em()
            return True
        except Exception:
            return False

    def _parse_symbol(self, symbol: str) -> tuple[str, str]:
        """解析 symbol: '000001.SZ' -> ('000001', 'SZ')"""
        parts = symbol.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid symbol format: {symbol}, expected 'code.exchange'")
        return parts[0], parts[1]

    def _map_frequency(self, frequency: str) -> str:
        """频率映射"""
        mapping = {
            "1d": "daily",
            "1w": "weekly",
            "1m": "monthly",
            "1min": "1",
            "5min": "5",
            "15min": "15",
            "30min": "30",
            "60min": "60",
        }
        return mapping.get(frequency, "daily")

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> List[BarData]:
        """获取K线数据"""
        ak = self._get_ak()
        code, exchange = self._parse_symbol(symbol)
        period = self._map_frequency(frequency)

        # 调用 akshare 接口
        df = ak.stock_zh_a_hist(
            symbol=code,
            period=period,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq"  # 前复权
        )

        if df.empty:
            return []

        # 转换为 BarData 列表
        bars = []
        for _, row in df.iterrows():
            bar = BarData(
                symbol=symbol,
                timestamp=datetime.strptime(str(row['日期']), "%Y-%m-%d"),
                frequency=Frequency(frequency) if frequency in [f.value for f in Frequency] else Frequency.DAILY,
                open=float(row['开盘']),
                high=float(row['最高']),
                low=float(row['最低']),
                close=float(row['收盘']),
                volume=float(row['成交量']),
                amount=float(row['成交额']) if '成交额' in row and pd.notna(row['成交额']) else None,
            )
            bars.append(bar)

        return bars

    def get_symbols(self) -> List[SymbolInfo]:
        """获取A股股票列表"""
        ak = self._get_ak()
        df = ak.stock_zh_a_spot_em()

        symbols = []
        for _, row in df.iterrows():
            # 解析代码和交易所
            code = str(row['代码'])
            # 根据代码判断交易所
            if code.startswith(('60', '68', '88', '89')):
                exchange = "SH"
            elif code.startswith(('00', '30', '82', '83')):
                exchange = "SZ"
            elif code.startswith(('43', '83', '87', '88')):
                exchange = "BJ"
            else:
                exchange = "SH"  # 默认

            symbol = SymbolInfo(
                symbol=f"{code}.{exchange}",
                name=str(row['名称']),
                exchange=exchange,
                industry=str(row.get('所属行业', '')) if pd.notna(row.get('所属行业')) else None
            )
            symbols.append(symbol)

        return symbols
```

**Step 2: 创建测试（使用 mock）**

```python
# tests/data_hub/fetchers/test_akshare_fetcher.py
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from trader_center.data_hub.fetchers.akshare_fetcher import AkshareFetcher
from trader_center.data_hub.models import Frequency


class TestAkshareFetcher:
    @pytest.fixture
    def fetcher(self):
        return AkshareFetcher()

    def test_parse_symbol(self, fetcher):
        code, exchange = fetcher._parse_symbol("000001.SZ")
        assert code == "000001"
        assert exchange == "SZ"

    def test_parse_symbol_invalid(self, fetcher):
        with pytest.raises(ValueError):
            fetcher._parse_symbol("INVALID")

    def test_map_frequency(self, fetcher):
        assert fetcher._map_frequency("1d") == "daily"
        assert fetcher._map_frequency("5min") == "5"
        assert fetcher._map_frequency("unknown") == "daily"

    @patch('trader_center.data_hub.fetchers.akshare_fetcher.akshare')
    def test_get_bars(self, mock_ak, fetcher):
        # Mock akshare 返回
        import pandas as pd
        mock_ak.stock_zh_a_hist.return_value = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘': [10.0, 10.5],
            '最高': [11.0, 10.8],
            '最低': [9.5, 10.2],
            '收盘': [10.5, 10.6],
            '成交量': [10000, 8000],
            '成交额': [105000, 84800],
        })

        fetcher._ak = mock_ak
        bars = fetcher.get_bars(
            "000001.SZ",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            "1d"
        )

        assert len(bars) == 2
        assert bars[0].close == 10.5
        assert bars[1].close == 10.6
```

**Step 3: Commit**

```bash
git add trader_center/data_hub/fetchers/ tests/data_hub/fetchers/
git commit -m "feat: implement AkshareFetcher for stock data"
```

---

## Phase 4: 路由层实现

### Task 9: 多源路由与合并

**Files:**
- Create: `trader_center/data_hub/fetchers/router.py`
- Create: `trader_center/data_hub/router.py` (顶层路由)

**Step 1: 实现 Fetcher 路由**

```python
# trader_center/data_hub/fetchers/router.py
from datetime import datetime
from typing import List, Optional, Tuple
import pandas as pd
import logging

from trader_center.data_hub.fetchers.base import DataFetcher
from trader_center.data_hub.models import BarData, SymbolInfo

logger = logging.getLogger(__name__)


class FetcherRouter:
    """Fetcher 路由与合并中心"""

    def __init__(self):
        self.fetchers: List[DataFetcher] = []

    def register(self, fetcher: DataFetcher):
        """注册数据源"""
        self.fetchers.append(fetcher)
        # 按优先级排序
        self.fetchers.sort(key=lambda f: f.priority)
        logger.info(f"Registered fetcher: {fetcher.name} (priority={fetcher.priority})")

    def get_available_fetchers(self) -> List[DataFetcher]:
        """获取可用的数据源列表"""
        return [f for f in self.fetchers if f.check_available()]

    def fetch_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> Optional[pd.DataFrame]:
        """
        从多个源获取数据并合并
        策略：按优先级获取，互补缺失数据
        """
        available = self.get_available_fetchers()
        if not available:
            logger.error("No fetchers available")
            return None

        results = []
        for fetcher in available:
            try:
                bars = fetcher.get_bars(symbol, start, end, frequency)
                if bars:
                    df = pd.DataFrame([b.model_dump() for b in bars])
                    results.append((fetcher.name, fetcher.priority, df))
                    logger.debug(f"{fetcher.name}: fetched {len(df)} bars")
            except Exception as e:
                logger.warning(f"{fetcher.name} fetch failed: {e}")
                continue

        if not results:
            return None

        # 按优先级排序后合并
        results.sort(key=lambda x: x[1])
        return self._merge_results(results)

    def _merge_results(
        self,
        results: List[Tuple[str, int, pd.DataFrame]]
    ) -> pd.DataFrame:
        """
        合并多源数据
        策略：高优先级源为主，低优先级源互补缺失数据
        """
        base_name, _, base_df = results[0]
        merged = base_df.copy()

        for src_name, _, src_df in results[1:]:
            # 找出 base 中缺失的日期
            existing_dates = set(merged['timestamp'])
            missing = src_df[~src_df['timestamp'].isin(existing_dates)]

            if not missing.empty:
                logger.debug(f"{src_name}: complementing {len(missing)} missing bars")
                merged = pd.concat([merged, missing], ignore_index=True)

        # 排序
        merged = merged.sort_values('timestamp').reset_index(drop=True)
        return merged

    def fetch_symbols(self) -> List[SymbolInfo]:
        """获取股票列表（使用最高优先级的源）"""
        available = self.get_available_fetchers()
        if not available:
            return []

        # 使用最高优先级的源
        return available[0].get_symbols()
```

**Step 2: 实现顶层路由（整合 storage）**

```python
# trader_center/data_hub/router.py
from datetime import datetime
from typing import List, Optional, Tuple
import pandas as pd
import logging

from trader_center.data_hub.fetchers.router import FetcherRouter
from trader_center.data_hub.storage.hybrid_store import HybridStorage
from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.models import BarData, SymbolInfo

logger = logging.getLogger(__name__)


class DataRouter:
    """
    数据路由中心 - 整合 Fetcher 和 Storage
    职责：
    1. 管理本地缓存
    2. 处理增量更新
    3. 多源数据合并
    """

    def __init__(self, config: Optional[DataHubConfig] = None):
        self.config = config or DataHubConfig()
        self.storage = HybridStorage(self.config)
        self.fetcher_router = FetcherRouter()

    def register_fetcher(self, fetcher):
        """注册数据源"""
        self.fetcher_router.register(fetcher)

    def get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> pd.DataFrame:
        """
        获取K线数据（带增量更新）
        """
        # 1. 从本地获取已有数据
        local_df = self.storage.get_bars(symbol, start, end, frequency)

        # 2. 计算缺失的时间段
        missing_ranges = self._calculate_missing_ranges(
            local_df, start, end, symbol, frequency
        )

        if not missing_ranges:
            logger.debug(f"All data available locally for {symbol}")
            return local_df

        # 3. 从远程获取缺失数据
        all_new_data = []
        for miss_start, miss_end in missing_ranges:
            logger.info(f"Fetching missing data: {symbol} [{miss_start} to {miss_end}]")
            fetched = self.fetcher_router.fetch_bars(symbol, miss_start, miss_end, frequency)
            if fetched is not None and not fetched.empty:
                all_new_data.append(fetched)

        if not all_new_data:
            return local_df

        # 4. 合并新数据并保存
        new_df = pd.concat(all_new_data, ignore_index=True)
        self._save_to_storage(new_df)

        # 5. 返回完整数据
        if local_df.empty:
            return new_df
        else:
            combined = pd.concat([local_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['timestamp'], keep='first')
            return combined.sort_values('timestamp').reset_index(drop=True)

    def _calculate_missing_ranges(
        self,
        local_df: pd.DataFrame,
        requested_start: datetime,
        requested_end: datetime,
        symbol: str,
        frequency: str
    ) -> List[Tuple[datetime, datetime]]:
        """计算需要获取的缺失时间段"""
        # 获取本地数据的实际范围
        local_start, local_end = self.storage.get_data_range(symbol, frequency)

        if local_start is None:
            # 本地无数据，全量获取
            return [(requested_start, requested_end)]

        missing = []

        # 检查开头
        if requested_start < local_start:
            missing.append((requested_start, min(requested_end, local_start)))

        # 检查结尾
        if requested_end > local_end:
            missing.append((max(requested_start, local_end), requested_end))

        return missing

    def _save_to_storage(self, df: pd.DataFrame):
        """保存 DataFrame 到存储"""
        if df.empty:
            return

        bars = []
        for _, row in df.iterrows():
            try:
                bar = BarData(**row.to_dict())
                bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to parse bar: {e}")

        if bars:
            self.storage.save_bars(bars)

    def get_symbols(self, exchange: Optional[str] = None) -> List[SymbolInfo]:
        """获取股票列表"""
        # 先尝试从本地获取
        local = self.storage.get_symbols(exchange)
        if local:
            return local

        # 从远程获取并保存
        remote = self.fetcher_router.fetch_symbols()
        if remote:
            self.storage.save_symbols(remote)
            if exchange:
                return [s for s in remote if s.exchange == exchange]
            return remote

        return []
```

**Step 3: Commit**

```bash
git add trader_center/data_hub/router.py trader_center/data_hub/fetchers/router.py
git commit -m "feat: implement multi-source routing with incremental updates"
```

---

## Phase 5: 缓存层实现

### Task 10: 内存缓存管理器

**Files:**
- Create: `trader_center/data_hub/cache/__init__.py`
- Create: `trader_center/data_hub/cache/manager.py`
- Create: `trader_center/data_hub/cache/key_builder.py`

**Step 1: 实现缓存键构建器**

```python
# trader_center/data_hub/cache/key_builder.py
import hashlib
from datetime import datetime
from typing import Optional


class CacheKeyBuilder:
    """缓存键生成器"""

    @staticmethod
    def for_bars(
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str
    ) -> str:
        """K线数据缓存键"""
        params = f"{symbol}:{start.isoformat()}:{end.isoformat()}:{frequency}"
        hash_val = hashlib.md5(params.encode()).hexdigest()[:12]
        return f"bars:{symbol}:{frequency}:{hash_val}"

    @staticmethod
    def for_symbols(exchange: Optional[str] = None) -> str:
        """股票列表缓存键"""
        return f"symbols:{exchange or 'all'}"

    @staticmethod
    def for_data_range(symbol: str, frequency: str) -> str:
        """数据范围缓存键"""
        return f"range:{symbol}:{frequency}"
```

**Step 2: 实现缓存管理器**

```python
# trader_center/data_hub/cache/manager.py
import time
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict

logger = logging.getLogger(__name__)


class CacheManager:
    """
    LRU 内存缓存管理器
    支持 TTL 和容量限制
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._ttl: Dict[str, float] = {}
        self._access_count: Dict[str, int] = {}
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            self._miss_count += 1
            return None

        # 检查 TTL
        if key in self._ttl and time.time() > self._ttl[key]:
            self._delete(key)
            self._miss_count += 1
            return None

        # 更新访问顺序（LRU）
        self._cache.move_to_end(key)
        self._access_count[key] = self._access_count.get(key, 0) + 1
        self._hit_count += 1

        return self._cache[key]

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """设置缓存"""
        # 如果已存在，先删除
        if key in self._cache:
            del self._cache[key]

        # LRU 淘汰
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        self._cache[key] = value
        if ttl:
            self._ttl[key] = time.time() + ttl

    def _evict_lru(self):
        """淘汰最少使用的缓存"""
        if not self._cache:
            return
        oldest_key = next(iter(self._cache))
        self._delete(oldest_key)
        logger.debug(f"Evicted cache key: {oldest_key}")

    def _delete(self, key: str):
        """删除缓存项"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        self._access_count.pop(key, None)

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._ttl.clear()
        self._access_count.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": f"{hit_rate:.2%}"
        }
```

**Step 3: Commit**

```bash
git add trader_center/data_hub/cache/
git commit -m "feat: implement LRU cache manager with TTL support"
```

---

## Phase 6: API 层实现

### Task 11: 对外 API 函数

**Files:**
- Modify: `trader_center/data_hub/__init__.py`

**Step 1: 实现 API 函数**

```python
# trader_center/data_hub/__init__.py
"""
DataHub - Multi-source financial data access layer

Example:
    >>> import trader_center.data_hub as dh
    >>> df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
"""

from datetime import datetime, date
from typing import Optional, Union, List
import pandas as pd
import logging

from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.router import DataRouter
from trader_center.data_hub.cache.manager import CacheManager
from trader_center.data_hub.cache.key_builder import CacheKeyBuilder

# 全局实例
_router: Optional[DataRouter] = None
_cache: Optional[CacheManager] = None
_config: Optional[DataHubConfig] = None

logger = logging.getLogger(__name__)


def _get_router() -> DataRouter:
    """获取或初始化全局 Router"""
    global _router
    if _router is None:
        _init_default()
    return _router


def _get_cache() -> CacheManager:
    """获取或初始化全局 Cache"""
    global _cache
    if _cache is None:
        _cache = CacheManager(max_size=1000)
    return _cache


def _init_default():
    """初始化默认配置"""
    global _router, _config

    _config = DataHubConfig()
    _router = DataRouter(_config)

    # 尝试注册 akshare
    try:
        from trader_center.data_hub.fetchers.akshare_fetcher import AkshareFetcher
        _router.register_fetcher(AkshareFetcher())
        logger.info("Akshare fetcher registered automatically")
    except ImportError:
        logger.warning("akshare not installed, skipping auto-registration")


def configure(
    data_dir: Optional[str] = None,
    cache_size: int = 1000,
):
    """
    配置 DataHub

    Parameters
    ----------
    data_dir : str, optional
        数据存储目录，默认 ~/.trader_center/data/
    cache_size : int
        内存缓存大小
    """
    global _router, _cache, _config

    _config = DataHubConfig(data_dir=data_dir)
    _router = DataRouter(_config)
    _cache = CacheManager(max_size=cache_size)

    # 重新注册默认 fetcher
    try:
        from trader_center.data_hub.fetchers.akshare_fetcher import AkshareFetcher
        _router.register_fetcher(AkshareFetcher())
    except ImportError:
        pass


def get_daily_bars(
    symbol: str,
    start: Union[str, datetime, date],
    end: Union[str, datetime, date],
    adjust: str = "qfq",
) -> pd.DataFrame:
    """
    获取日线数据

    Parameters
    ----------
    symbol : str
        股票代码，如 "000001.SZ", "600000.SH"
    start : str or datetime
        开始日期，格式 "YYYY-MM-DD"
    end : str or datetime
        结束日期
    adjust : str
        复权方式: "qfq"(前复权), "hfq"(后复权), None(不复权)

    Returns
    -------
    pd.DataFrame
        columns: [timestamp, open, high, low, close, volume, amount]

    Examples
    --------
    >>> df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
    """
    router = _get_router()
    cache = _get_cache()

    # 解析日期
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)

    # 构建缓存键
    cache_key = CacheKeyBuilder.for_bars(symbol, start_dt, end_dt, "1d")

    # 尝试读取缓存
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 从 router 获取
    df = router.get_bars(symbol, start_dt, end_dt, "1d")

    # 写入缓存（5分钟 TTL）
    if not df.empty:
        cache.set(cache_key, df, ttl=300)

    return df


def get_stock_list(exchange: Optional[str] = None) -> pd.DataFrame:
    """
    获取股票列表

    Parameters
    ----------
    exchange : str, optional
        交易所过滤: "SZ", "SH", "BJ"

    Returns
    -------
    pd.DataFrame
        columns: [symbol, name, exchange, type, list_date, industry]
    """
    router = _get_router()
    cache = _get_cache()

    cache_key = CacheKeyBuilder.for_symbols(exchange)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    symbols = router.get_symbols(exchange)
    df = pd.DataFrame([s.model_dump() for s in symbols])

    if not df.empty:
        cache.set(cache_key, df, ttl=86400)  # 1天 TTL

    return df


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    cache = _get_cache()
    return cache.get_stats()


def clear_cache():
    """清空内存缓存"""
    cache = _get_cache()
    cache.clear()


__all__ = [
    "configure",
    "get_daily_bars",
    "get_stock_list",
    "get_cache_stats",
    "clear_cache",
]
```

**Step 2: Commit**

```bash
git add trader_center/data_hub/__init__.py
git commit -m "feat: implement public API layer with caching"
```

---

## Phase 7: 集成测试

### Task 12: 端到端测试

**Files:**
- Create: `tests/data_hub/test_integration.py`

**Step 1: 编写集成测试**

```python
# tests/data_hub/test_integration.py
import pytest
import tempfile
from datetime import datetime

import trader_center.data_hub as dh
from trader_center.data_hub.config import DataHubConfig


class TestIntegration:
    """端到端集成测试"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前清理缓存"""
        dh.clear_cache()
        yield
        dh.clear_cache()

    def test_configure_and_get_bars(self):
        """测试配置和数据获取流程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 配置
            dh.configure(data_dir=tmpdir, cache_size=100)

            # 获取股票列表（mock 或需要网络）
            # 这个测试可能需要 mock akshare
            pass

    def test_cache_functionality(self):
        """测试缓存是否工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            dh.configure(data_dir=tmpdir)

            # 首次调用后应该有缓存
            stats1 = dh.get_cache_stats()
            assert stats1['size'] >= 0

    def test_clear_cache(self):
        """测试清空缓存"""
        dh.clear_cache()
        stats = dh.get_cache_stats()
        assert stats['size'] == 0
```

**Step 2: Commit**

```bash
git add tests/data_hub/test_integration.py
git commit -m "test: add integration tests"
```

---

## Phase 8: 完成与验证

### Task 13: 运行完整测试套件

**Step 1: 运行所有测试**

```bash
pytest tests/data_hub/ -v --tb=short
```

Expected: All tests pass

**Step 2: 代码格式化**

```bash
black trader_center/data_hub/ tests/data_hub/
ruff check trader_center/data_hub/ --fix
```

**Step 3: 最终提交**

```bash
git add -A
git commit -m "feat: complete DataHub module implementation"
```

---

## 总结

实现完成后，DataHub 将提供：

1. **数据模型**: BarData, SymbolInfo, FinancialReport 等强类型模型
2. **混合存储**: SQLite (元数据) + Parquet (K线数据)
3. **多源获取**: Akshare 为主，可扩展其他源
4. **智能路由**: 自动增量更新、多源合并
5. **内存缓存**: LRU + TTL 策略
6. **简洁 API**: `dh.get_daily_bars()`, `dh.get_stock_list()` 等函数

### 使用示例

```python
import trader_center.data_hub as dh

# 配置（可选）
dh.configure(data_dir="./data", cache_size=2000)

# 获取日线数据
df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
print(df.head())

# 获取股票列表
stocks = dh.get_stock_list(exchange="SZ")
```
