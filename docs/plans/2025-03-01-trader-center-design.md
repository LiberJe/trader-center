# Trader Center 设计文档

## 项目概述

个人金融市场研究框架，采用模块化单体架构，提供统一数据出口，支持量化回测、每日市场监测和市场分析功能。

## 技术栈

- **语言**: Python 3.11+
- **数据存储**: SQLite (SQLAlchemy ORM)
- **CLI 框架**: Click
- **数据验证**: Pydantic v2
- **数据分析**: Pandas, NumPy
- **数据源**: AkShare (A股), yfinance (美股/港股), python-binance (加密货币)

## 架构设计

### 整体结构

```
trader-center/
├── trader_center/           # 主包
│   ├── cli.py              # 统一 CLI 入口
│   ├── config.py           # 配置管理
│   ├── data_hub/           # 数据中台
│   ├── backtest/           # 回测引擎
│   ├── monitor/            # 市场监测
│   └── analysis/           # 分析工具
├── tests/                  # 测试目录
├── data/                   # SQLite 数据目录
└── examples/               # 使用示例
```

### 数据中台 (data_hub)

负责从多数据源获取数据，提供统一查询接口。

#### 数据模型

| 表名 | 用途 | 主键 |
|------|------|------|
| `symbols` | 标的元数据 | id |
| `daily_bars` | 日线行情 | (symbol_id, date) |
| `adj_factors` | 复权因子 | (symbol_id, date) |
| `indices` | 指数/板块 | id |
| `watchlist` | 用户自选股 | (symbol_id, group_name) |

#### 数据源适配器

- `akshare_fetcher.py` - A股市场数据
- `yahoo_fetcher.py` - 美股/港股市场数据
- `binance_fetcher.py` - 加密货币数据

每个适配器继承 `BaseFetcher`，实现统一的 `fetch_daily_bars()` 接口。

#### 统一数据 API

```python
# api.py 核心接口
def get_daily_bars(
    symbol: str,
    start: str | datetime,
    end: str | datetime,
    adjust: bool = True,
    fields: list[str] | None = None
) -> pd.DataFrame

def get_symbols(market: str | None = None) -> pd.DataFrame
def get_watchlist(group: str = "default") -> list[str]
```

### 回测引擎 (backtest)

#### 向量化回测

适合快速策略验证，基于 Pandas 向量化运算。

```python
from trader_center.backtest.vectorized import Engine

engine = Engine(
    initial_cash=100000,
    commission=0.0003,
    slippage=0.001
)
result = engine.run(data=df, signals=signal_series)
```

#### 事件驱动回测

适合精细模拟真实交易流程。

```
BarEvent → Strategy → Signal → Broker → 执行
              ↓
         Portfolio (持仓/资金)
```

组件：
- `engine.py` - 事件循环主引擎
- `broker.py` - 模拟交易执行（费用、滑点）
- `portfolio.py` - 资金和持仓管理
- `strategy.py` - 策略基类

#### 绩效指标

- 年化收益率 (CAGR)
- 最大回撤 (Max Drawdown)
- 夏普比率 (Sharpe Ratio)
- 胜率、盈亏比
- 交易明细

### 每日市场监测 (monitor)

#### CLI 命令

```bash
tc monitor overview              # 市场全景
tc watchlist add <code>          # 添加自选股
tc watchlist list                # 查看自选股
tc monitor check                 # 运行监测检查
tc monitor report                # 生成日报
```

#### 监测功能

- **市场概览**: 大盘指数、涨跌分布、成交额
- **自选股监控**: 价格、涨跌幅、关键价位
- **预警系统**: 技术指标预警（金叉、突破等）

## 配置管理

### 配置文件路径

- 项目配置: `./config.yaml`
- 用户配置: `~/.trader_center/config.yaml`

### 配置示例

```yaml
data_sources:
  akshare:
    enabled: true
  yahoo:
    enabled: true
  binance:
    enabled: true

sync:
  daily_update: "20:00"
  keep_days: 3650

alerts:
  rules:
    - name: "突破MA20"
      condition: "close > MA(close, 20)"
```

## 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                         数据中台                             │
│  ┌────────────┐    ┌────────────┐    ┌──────────────────┐  │
│  │ 数据源    │───▶│ 标准化转换 │───▶│ SQLite 存储      │  │
│  │ (多市场)  │    │ (OHLCV)    │    │ (日线数据)       │  │
│  └────────────┘    └────────────┘    └──────────────────┘  │
│                                              │              │
│  ┌───────────────────────────────────────────┘              │
│  │                                                         │
│  ▼                                                         │
│  ┌────────────┐                                            │
│  │ 统一 API  │                                            │
│  │ (api.py)  │                                            │
│  └─────┬──────┘                                            │
└────────┼────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                        应用层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ 回测引擎 │  │ 市场监测 │  │ 分析工具 │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 扩展规划

1. **技术指标库** - 在 `analysis/` 模块实现常用技术指标
2. **策略模板** - 提供常见策略的参考实现
3. **可视化** - 使用 `rich` 或 `plotext` 进行终端可视化
4. **数据导出** - 支持导出 CSV/Excel 用于外部分析

## 设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 架构风格 | 模块化单体 | 简单直接，适合个人项目 |
| 数据存储 | SQLite | 零部署，个人使用足够 |
| A股数据源 | AkShare | 免费、开源、数据丰富 |
| 交互方式 | CLI | 技术用户友好，易于自动化 |
| 数据频率 | 日线 | 中长期策略，数据量可控 |
| 回测模式 | 双模式 | 快速验证 + 精细模拟 |

## 验收标准

- [ ] 数据中台可从三个数据源获取日线数据
- [ ] 提供统一 API 查询历史行情
- [ ] 向量化回测可运行并输出绩效指标
- [ ] 每日市场监测可生成报告
- [ ] 自选股管理功能完整
- [ ] CLI 命令统一、文档清晰
