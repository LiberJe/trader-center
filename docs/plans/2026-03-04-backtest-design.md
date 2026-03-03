# Backtrader 回测系统设计文档

## 概述

基于 backtrader 框架，为 trader_center 构建支持多策略组合和资金管理的完整回测系统。

## 需求确认

| 需求项 | 选择 |
|--------|------|
| 使用场景 | B - 完整策略研发（多策略组合、资金管理） |
| 多策略架构 | A - 独立账户模式 |
| 策略定义 | A - 类继承模式（继承 BaseStrategy） |
| 执行方式 | C - 混合模式（事件驱动 + 向量化 API） |
| 并行能力 | D - 支持多进程并行 |
| 架构方案 | 方案1 - Backtrader 原生集成 |

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      Backtest Module                            │
│                 (trader_center/backtest/)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Strategy   │  │   Cerebro    │  │   Analyzer   │          │
│  │    Layer     │  │   Engine     │  │    Layer     │          │
│  │              │  │              │  │              │          │
│  │ BaseStrategy │  │  Backtrader  │  │  Performance │          │
│  │   (封装)      │  │   Cerebro    │  │   Metrics    │          │
│  │              │  │              │  │              │          │
│  │ MultiStrategy│  │  DataFeeds   │  │  Trade Log   │          │
│  │   (组合)      │  │   (Pandas)   │  │   Export     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐        │
│  │              DataHub Integration Layer              │        │
│  │         (PandasData feed adapter)                  │        │
│  └────────────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐        │
│  │                   DataHub                          │        │
│  │         (已有的数据获取和存储模块)                   │        │
│  └────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## 组件设计

### 核心组件

| 组件 | 职责 | 文件位置 |
|------|------|----------|
| `BaseStrategy` | 策略基类，封装 backtrader 原生 Strategy，添加 A股特性 | `backtest/strategy/base.py` |
| `StrategyAccount` | 独立账户封装，管理单个策略的资金和持仓 | `backtest/account.py` |
| `MultiStrategyRunner` | 多策略并行执行器，多进程调度 | `backtest/runner.py` |
| `PandasDataFeed` | DataHub → Backtrader 数据适配器 | `backtest/data_feed.py` |
| `AStockCommission` | A股手续费/印花税计算 | `backtest/broker.py` |
| `PerformanceAnalyzer` | 绩效分析器封装 | `backtest/analyzers.py` |
| `BacktestCLI` | 回测 CLI 入口 | `backtest/cli.py` |

### 目录结构

```
trader_center/backtest/
├── __init__.py           # 导出公共API
├── cli.py                # 命令行入口
├── config.py             # 回测配置
├── strategy/
│   ├── __init__.py
│   ├── base.py           # BaseStrategy
│   └── template.py       # 策略模板
├── account.py            # StrategyAccount
├── runner.py             # MultiStrategyRunner
├── data_feed.py          # PandasDataFeed
├── broker.py             # A股手续费/滑点
├── analyzers.py          # 绩效分析器
├── results.py            # 回测结果封装
└── utils.py              # 辅助函数
```

## 数据流设计

### 单策略回测流程

1. **数据加载**
   - 用户指定股票代码和日期范围
   - `DataFeed` 调用 `data_hub.get_daily_bars()` 获取数据
   - 数据转换为 backtrader 的 `PandasData` 格式
   - Cerebro 加载数据并开始回测

2. **交易执行**
   - 策略在 `next()` 中发出买卖指令 `self.buy()/self.sell()`
   - Broker 处理订单，考虑 A股特性（涨跌停、T+1、手续费）
   - `notify_order()` 回调通知订单成交状态

3. **独立账户**
   - 每个策略实例有独立的 `StrategyAccount`
   - 资金、持仓、交易记录互不影响
   - 回测结束后各自生成独立的绩效报告

### 多策略并行流程

- `MultiStrategyRunner` 接收多个策略配置
- `ProcessPoolExecutor` 分配多个 Worker 进程
- 每个 Worker 独立运行一个 Cerebro 实例
- 主进程汇总所有策略结果

## A股特性处理

| 特性 | 实现方式 |
|------|---------|
| 涨跌停限制 | Broker 中检查价格，涨停不能买入，跌停不能卖出 |
| T+1 交易 | 持仓对象记录买入日期，`next()` 中检查 |
| 手续费 | 买入万2.5，卖出万2.5+千1印花税，最低5元 |
| 除权除息 | DataHub 已处理前复权，回测直接使用 |

## 日志设计

### 日志级别

| 级别 | 场景 |
|------|------|
| `DEBUG` | 详细的执行细节 |
| `INFO` | 重要里程碑事件 |
| `WARNING` | 异常但可继续（如数据缺失） |
| `ERROR` | 严重错误，策略失败 |
| `CRITICAL` | 系统级故障 |

### 输出方式

1. **控制台** - 实时显示进度（INFO及以上）
2. **文件** - 完整记录（DEBUG及以上），按策略分文件
3. **结果对象** - 关键事件存入 `BacktestResult.logs`

### 多进程日志

- 各进程独立写入临时日志文件
- 主进程合并并按时间排序
- 避免多进程写同一文件的锁竞争

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 数据缺失 | 警告日志，跳过该日期 |
| 策略异常 | 捕获异常，标记 `status="error"` |
| 内存不足 | 分批加载，流式处理 |
| 多进程崩溃 | 捕获异常，其他进程继续 |
| 参数无效 | 前置校验，抛出 `ValueError` |

## 测试策略

| 测试类型 | 覆盖范围 |
|---------|---------|
| 单元测试 | 账户计算、手续费、数据适配 |
| 集成测试 | 完整回测流程（DataHub → Backtrader → Result） |
| 性能测试 | 大数据量、多进程并行 |
| 策略示例 | 提供 SMA/RSI 示例策略作为测试用例 |

## 使用示例

```python
# 定义策略
class SmaCrossStrategy(BaseStrategy):
    name = "sma_cross"
    params = (('fast', 10), ('slow', 30))

    def __init__(self):
        self.sma_fast = bt.indicators.SMA(period=self.p.fast)
        self.sma_slow = bt.indicators.SMA(period=self.p.slow)

    def next(self):
        if not self.position:
            if self.sma_fast > self.sma_slow:
                self.buy()
        else:
            if self.sma_fast < self.sma_slow:
                self.sell()

# 运行回测
runner = MultiStrategyRunner(max_workers=4)
results = runner.run(
    strategies=[SmaCrossStrategy(fast=5, slow=20),
                SmaCrossStrategy(fast=10, slow=30)],
    symbols=["000001.SZ", "600000.SH"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000
)

# 查看结果
for r in results:
    print(f"{r.strategy_name}: 收益率 {r.return_pct:.2%}")
```

## CLI 使用示例

```bash
# 运行单个策略
python -m trader_center.backtest --strategy examples.sma --symbol 000001.SZ

# 多策略并行回测
python -m trader_center.backtest --config strategies.yaml --workers 4

# 导出结果
python -m trader_center.backtest --strategy examples.sma -o result.html
```

---

设计确认日期: 2026-03-04
