# DataHub 模块设计文档

**日期**: 2026-03-01
**目标**: 实现基于多数据源（akshare为主）的数据模块，支持回测系统的数据需求

---

## 1. 设计目标

为量化回测系统提供统一、可靠、高效的数据访问层：

- **多数据源聚合**: 以 akshare 为主，支持多源互补合并
- **全类型数据**: 股票行情、财务数据、宏观数据、另类数据
- **混合存储**: SQLite 存储元数据，Parquet 存储大规模价格数据
- **智能缓存**: 内存 LRU + 磁盘持久化，支持增量更新
- **简洁 API**: 类似 akshare/pandas-datareader 的函数式接口

---

## 2. 整体架构

```
┌─────────────────────────────────────────┐
│  API Layer (函数式接口)                  │
│  get_daily_bars(), get_stock_list()     │
├─────────────────────────────────────────┤
│  Data Router (多源路由与合并)             │
│  source selection, conflict resolution  │
├─────────────────────────────────────────┤
│  Fetcher Layer (数据源适配器)            │
│  AkshareFetcher, TushareFetcher...      │
├─────────────────────────────────────────┤
│  Cache Layer (智能缓存)                  │
│  memory LRU, TTL, incremental update    │
├─────────────────────────────────────────┤
│  Storage Layer (混合存储)               │
│  SQLite(meta) + Parquet(bulk data)      │
└─────────────────────────────────────────┘
```

### 模块结构

```
trader_center/
└── data_hub/
    ├── __init__.py          # 对外暴露的函数式API
    ├── config.py            # 配置管理
    ├── cache/               # 缓存层
    │   ├── __init__.py
    │   ├── manager.py       # 缓存管理器
    │   └── key_builder.py   # 缓存键生成
    ├── storage/             # 存储层
    │   ├── __init__.py
    │   ├── base.py          # 存储抽象接口
    │   ├── sqlite_store.py  # SQLite元数据存储
    │   └── parquet_store.py # Parquet大数据存储
    ├── fetchers/            # 数据获取层
    │   ├── __init__.py
    │   ├── base.py          # Fetcher抽象基类
    │   ├── akshare_fetcher.py
    │   ├── tushare_fetcher.py
    │   └── router.py        # 多源路由与合并
    └── models.py            # 核心数据模型
```

---

## 3. 核心数据模型

使用 Pydantic 定义强类型数据模型：

```python
class Frequency(str, Enum):
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
    symbol: str
    timestamp: datetime
    frequency: Frequency
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: Optional[float] = None
    adj_factor: Optional[float] = None
    is_suspended: bool = False

    class Config:
        frozen = True

class SymbolInfo(BaseModel):
    """股票元数据"""
    symbol: str
    name: str
    exchange: Literal["SZ", "SH", "BJ", "HK", "US"]
    type: Literal["stock", "index", "etf", "bond"]
    list_date: Optional[date]
    delist_date: Optional[date]
    industry: Optional[str]

class FinancialReport(BaseModel):
    """财务数据模型"""
    symbol: str
    report_date: date
    report_type: Literal["Q1", "Q2", "Q3", "annual"]
    revenue: Optional[float]
    net_profit: Optional[float]
    eps: Optional[float]
    roe: Optional[float]
    debt_ratio: Optional[float]

class MacroData(BaseModel):
    """宏观数据模型"""
    indicator: str
    country: str = "CN"
    timestamp: date
    value: float
    period: Optional[str]
```

---

## 4. 存储层设计

### 存储策略

| 数据类型 | 存储方式 | 理由 |
|---------|---------|------|
| 股票代码列表 | SQLite | 查询频繁、数据量小 |
| K线数据（日线+） | Parquet + 按symbol分区 | 列式压缩高效 |
| 分钟线数据 | Parquet + 按日期分区 | 避免单文件过大 |
| 财务数据 | SQLite | 结构化、关联查询 |
| 宏观数据 | SQLite | 低频更新 |

### 目录结构

```
data/
├── metadata.db               # SQLite 数据库
├── bars/
│   ├── daily/               # 日线数据
│   │   ├── 000001.SZ.parquet
│   │   └── ...
│   └── min_5/               # 分钟线
│       ├── 2024-01.parquet
│       └── ...
└── cache/                   # 临时缓存
```

### 存储接口

```python
class Storage(ABC):
    @abstractmethod
    def save_bars(self, bars: List[BarData]) -> None: ...

    @abstractmethod
    def get_bars(self, symbol, start, end, frequency) -> pd.DataFrame: ...

    @abstractmethod
    def get_symbols(self, exchange=None) -> List[SymbolInfo]: ...

    @abstractmethod
    def get_data_range(self, symbol, frequency) -> tuple[datetime, datetime]: ...
```

---

## 5. Fetcher 与路由层设计

### Fetcher 抽象

```python
class DataFetcher(ABC):
    name: str
    priority: int = 100

    @abstractmethod
    def get_bars(self, symbol, start, end, frequency) -> List[BarData]: ...

    @abstractmethod
    def get_symbols(self) -> List[SymbolInfo]: ...

    @abstractmethod
    def check_available(self) -> bool: ...
```

### 多源合并策略

1. **优先级机制**: akshare 优先（priority=10），其他源互补
2. **增量更新**: 检测本地已有数据，只拉取缺失部分
3. **冲突解决**: 同日期数据以高优先级源为准
4. **失败容错**: 单源失败自动切换，不影响整体

```python
class DataRouter:
    def get_bars(self, symbol, start, end, frequency):
        # 1. 查本地缓存
        # 2. 计算缺失时间段
        # 3. 按优先级从多源获取
        # 4. 合并去重（高优先级优先）
        # 5. 保存到本地
        pass
```

---

## 6. 缓存层设计

### 缓存策略

| 数据类型 | 位置 | TTL | 说明 |
|---------|-----|-----|------|
| 股票列表 | 内存+SQLite | 1天 | 低频变化 |
| K线数据 | 磁盘(Parquet) | 永久 | 增量补充 |
| 热点行情 | 内存 LRU | 5分钟 | 回测热点 |
| 财务数据 | 内存+SQLite | 7天 | 季报频率 |

### 核心组件

```python
class CacheManager:
    """LRU 内存缓存 + TTL"""
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl: Optional[int]): ...

class CacheKeyBuilder:
    """缓存键生成"""
    @staticmethod
    def for_bars(symbol, start, end, freq) -> str: ...
```

---

## 7. 对外 API 设计

### 主要接口

```python
import trader_center.data_hub as dh

# 股票行情
df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31", adjust="qfq")
df_5min = dh.get_minute_bars("000001.SZ", "2024-01-01", "2024-01-31", freq="5min")

# 股票列表
stocks = dh.get_stock_list(exchange="SZ")

# 财务数据
reports = dh.get_financial_report("000001.SZ", report_type="annual", years=5)

# 宏观数据
cpi = dh.get_macro_data("CPI", "2020-01-01", "2024-12-31")

# 配置
dh.configure(data_dir="./my_data", cache_size=2000)
```

---

## 8. 依赖项

```
pydantic >= 2.0
pandas >= 2.0
akshare >= 1.15
pyarrow >= 15.0  # Parquet 支持
```

---

## 9. 验收标准

- [ ] 成功获取股票日线数据并保存到本地
- [ ] 支持增量更新，避免重复拉取
- [ ] 多源合并逻辑正常工作
- [ ] 内存缓存命中率达到 80%+
- [ ] API 接口符合设计文档
- [ ] 支持常见频率：日线、周线、月线、分钟线
