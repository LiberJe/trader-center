# Trader Center - A股量化交易框架

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Trader Center 是一个专为 A 股市场设计的量化交易框架，提供数据获取、策略回测和市场监控的一站式解决方案。

## 核心特性

- **DataHub 数据中枢** - 多数据源接入（akshare）、智能缓存、增量更新、资金流向数据
- **Backtest 回测引擎** - 基于 backtrader、支持 A 股交易规则（T+1、涨跌停、印花税）
- **Monitor 市场监控** - CLI 任务系统、资金流向追踪、可扩展的任务架构
- **智能策略生成** - AI 驱动的量化策略自动生成与优化

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/trader-center.git
cd trader-center

# 安装依赖（基础）
pip install -e .

# 安装依赖（开发模式）
pip install -e ".[dev]"

# 安装回测扩展（可选，用于性能分析）
pip install -e ".[backtest]"
```

### 1. 数据获取

```python
import trader_center.data_hub as dh

# 获取股票日线数据
df = dh.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
print(df.head())

# 获取股票列表
stocks = dh.get_stock_list()
print(stocks.head())

# 获取大盘资金流向
fund_flow = dh.get_market_fund_flow()
print(fund_flow)
```

### 2. 策略回测

```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.examples import SmaCrossStrategy

# 创建回测运行器
runner = BacktestRunner()

# 运行 SMA 交叉策略
result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000
)

# 查看结果
print(f"总收益率: {result.return_pct:.2%}")
print(f"最大回撤: {result.max_drawdown:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")

# 打开详细报告
result.open_report()
```

### 3. 市场监控

```bash
# 列出所有可用任务
python -m trader_center.monitor --list

# 查看资金流向
python -m trader_center.monitor fund_flow

# 查看特定日期的资金流向
python -m trader_center.monitor fund_flow -d 2025-08-26

# 导出到文件
python -m trader_center.monitor fund_flow -o report.txt
```

## 模块详解

### DataHub 数据中枢

DataHub 提供统一的数据访问接口，支持自动缓存和增量更新。

#### 股票数据

```python
import trader_center.data_hub as dh

# 获取日线数据（支持复权）
df = dh.get_daily_bars(
    symbol="600519.SH",
    start="2024-01-01",
    end="2024-12-31",
    adjust="qfq"  # 前复权
)

# 获取股票列表
stocks = dh.get_stock_list(exchange="SH")  # 过滤上交所
```

#### 资金流向数据

```python
from datetime import date

# 大盘资金流向
market_flow = dh.get_market_fund_flow(target_date=date.today())

# 个股资金流向排名
stock_flow = dh.get_stock_fund_flow_rank(top_n=50)

# 板块资金流向
sector_flow = dh.get_sector_fund_flow(sector_type="industry")
```

#### 配置

```python
# 自定义配置
dh.configure(
    data_dir="/path/to/data",
    cache_size=2000
)

# 查看缓存统计
print(dh.get_cache_stats())

# 清空缓存
dh.clear_cache()
```

### Backtest 回测引擎

基于 backtrader 构建，针对 A 股市场进行了专门优化。

#### 内置策略

```python
from trader_center.backtest.strategy.examples import (
    SmaCrossStrategy,  # SMA 均线交叉
    RsiStrategy,       # RSI 策略
    BuyAndHoldStrategy # 买入持有
)
```

#### 自定义策略

```python
from trader_center.backtest import BaseStrategy

class MyStrategy(BaseStrategy):
    params = {
        ('period', 20),
    }

    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.period
        )

    def next(self):
        if not self.position:
            if self.data.close > self.sma:
                self.buy(size=100)
        else:
            if self.data.close < self.sma:
                self.sell(size=100)
```

#### 高级配置

```python
from trader_center.backtest import BacktestRunner, BacktestConfig

config = BacktestConfig(
    auto_save_trades=True,      # 自动保存交易记录
    enable_quantstats=True,     # 启用 QuantStats 分析
    auto_save_report=True       # 自动保存 HTML 报告
)

runner = BacktestRunner(config=config)
```

### Monitor 市场监控

可扩展的任务系统，用于执行各类市场观察任务。

#### CLI 使用

```bash
# 基础命令
python -m trader_center.monitor <task_name> [options]

# 可用选项
-d, --date     指定日期 (YYYY-MM-DD 或 YYYYMMDD)
-t, --top      显示前 N 条记录 (默认: 10)
-o, --output   导出到文件
-v, --verbose  详细输出
--list         列出所有任务

# 数据清理
python -m trader_center.monitor clean --fund-flow -d 2025-08-26
python -m trader_center.monitor clean --fund-flow --all
```

#### 自定义任务

1. 复制模板目录：
```bash
cp -r trader_center/monitor/tasks/_template_ trader_center/monitor/tasks/my_task
```

2. 实现任务类：
```python
from trader_center.monitor.base_task import BaseTask

class MyTask(BaseTask):
    name = "my_task"
    description = "我的自定义任务"

    def run(self, **kwargs):
        # 实现任务逻辑
        return {
            "status": "success",
            "data": {...}
        }
```

3. 任务将自动被发现并注册

## 项目架构

```
trader_center/
├── data_hub/           # 数据中枢模块
│   ├── fetchers/       # 数据获取器
│   ├── storage/        # 数据存储
│   ├── cache/          # 缓存管理
│   └── models.py       # 数据模型
├── backtest/           # 回测引擎
│   ├── strategy/       # 策略目录
│   ├── runner.py       # 回测运行器
│   ├── broker.py       # A股经纪商模拟
│   └── analytics.py    # 绩效分析
├── monitor/            # 市场监控
│   ├── tasks/          # 任务目录
│   ├── cli.py          # 命令行接口
│   └── task_router.py  # 任务路由
└── ...
```

## 回测策略案例

### 案例 1：双均线策略

```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.examples import SmaCrossStrategy

runner = BacktestRunner()
result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params={"fast": 10, "slow": 30}
)

print(f"收益率: {result.return_pct:.2%}")
result.plot()  # 绘制收益曲线
```

### 案例 2：多股票回测

```python
# 回测多只股票
symbols = ["000001.SZ", "600000.SH", "600519.SH"]

result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=symbols,
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=300000
)
```

### 案例 3：生成策略

```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.generated import GeneratedStrategy

# 使用 AI 生成的策略
runner = BacktestRunner()
result = runner.run(
    strategy=GeneratedStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000
)
```

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/data_hub/
pytest tests/backtest/
pytest tests/monitor/

# 带覆盖率报告
pytest --cov=trader_center
```

### 代码规范

```bash
# 格式化代码
black trader_center tests

# 代码检查
ruff check trader_center tests
```

### 项目配置

数据默认存储位置：`~/.trader_center/data/`

- `metadata.db` - SQLite 元数据数据库
- `bars/` - Parquet 格式的 K 线数据
- `logs/` - 交易日志和报告

## A股交易规则说明

本框架已针对 A 股市场进行专门优化：

| 规则 | 实现 |
|------|------|
| T+1 交易 | 当日买入不可卖出 |
| 涨跌停限制 | ±10%（ST 股票 ±5%，创业板 ±20%） |
| 佣金 | 默认 0.025%，最低 5 元 |
| 印花税 | 卖出时 0.1% |
| 过户费 | 沪市 0.001%（双向） |

## 技术栈

- **Python 3.10+** - 编程语言
- **pandas / pyarrow** - 数据处理与存储
- **akshare** - A股数据源
- **backtrader** - 回测引擎
- **pydantic** - 数据验证
- **QuantStats** - 绩效分析

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件

## 致谢

- [akshare](https://www.akshare.xyz/) - 提供 A 股数据接口
- [backtrader](https://www.backtrader.com/) - 强大的回测引擎
- [QuantStats](https://github.com/ranaroussi/quantstats) - 专业的绩效分析

---

**免责声明**：本框架仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。
