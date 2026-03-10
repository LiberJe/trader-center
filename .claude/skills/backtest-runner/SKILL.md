---
name: backtest-runner
description: |
  使用 trader_center 回测系统执行 A 股量化回测。
  当用户想要运行回测、测试交易策略、分析策略绩效或评估中国股票市场数据的投资策略时使用此技能。
  包括回测、策略测试、绩效分析、交易模拟，或当用户想要运行示例策略（如 SMA 交叉、RSI、买入持有）等场景。
---

# 回测执行器 (Backtest Runner)

此技能帮助用户使用 trader_center 回测模块执行量化回测，该模块基于 backtrader 构建，专为 A 股（中国股票市场）交易设计。

## 使用场景

当用户想要以下操作时，使用此技能：
- 运行交易策略回测
- 在特定股票或时间段上测试策略
- 分析策略绩效指标
- 对比不同策略
- 生成交易日志和绩效报告
- 可视化回测结果

## 可用策略

系统包含以下内置示例策略：

1. **SmaCrossStrategy** (`trader_center.backtest.strategy.examples.SmaCrossStrategy`)
   - 双均线交叉策略
   - 参数：`fast` (默认 5), `slow` (默认 20)
   - 金叉买入，死叉卖出

2. **RsiStrategy** (`trader_center.backtest.strategy.examples.RsiStrategy`)
   - RSI 超买超卖策略
   - 参数：`period` (默认 14), `oversold` (默认 30), `overbought` (默认 70)
   - RSI < 30 买入，RSI > 70 卖出

3. **BuyAndHoldStrategy** (`trader_center.backtest.strategy.examples.BuyAndHoldStrategy`)
   - 买入持有基准策略
   - 首日买入 99% 仓位并持有到期

## 快速开始

### 方法 1：命令行执行（快速测试推荐）

通过命令行运行回测：

```bash
# SMA 交叉策略基础用法
python -m trader_center.backtest \
    --strategy trader_center.backtest.strategy.examples.SmaCrossStrategy \
    --symbol 000001.SZ \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --cash 100000

# 启用可视化和自动保存
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ \
    -f 2024-01-01 -t 2024-12-31 \
    --plot

# 多股票回测
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.RsiStrategy \
    -sym 000001.SZ -sym 000002.SZ \
    -f 2024-01-01 -t 2024-12-31

# 保存结果到文件
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ \
    -f 2024-01-01 -t 2024-12-31 \
    -o result.json

# 自动在浏览器中打开绩效报告
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ \
    -f 2024-01-01 -t 2024-12-31 \
    --open-report
```

### 方法 2：Python API（自定义推荐）

```python
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy.examples import SmaCrossStrategy

# 自定义配置
config = BacktestConfig(
    initial_cash=100000,
    auto_save_trades=True,
    auto_save_plot=True,
    enable_quantstats=True,
    benchmark_symbol="000300.SH",  # 沪深 300 作为基准
    auto_save_report=True,
    auto_open_report=True,
)

# 创建运行器
runner = BacktestRunner(
    max_workers=1,
    enable_plot=True,
    config=config
)

# 运行回测
result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params={'fast': 5, 'slow': 20}
)

# 打印结果
print(f"收益率: {result.return_pct:.2%}")
print(f"交易次数: {result.total_trades}")
print(f"最大回撤: {result.calculate_max_drawdown():.2%}")
print(f"夏普比率: {result.calculate_sharpe_ratio():.2f}")

# 访问日志文件
print(f"日志文件: {result.log_files}")
```

## 命令行参数参考

| 参数 | 简写 | 说明 | 默认值 |
|-----------|-------|-------------|---------|
| `--strategy` | `-s` | 策略模块路径（必填） | - |
| `--symbol` | `-sym` | 股票代码，可多次指定（必填） | - |
| `--start` | `-f` | 开始日期 (YYYY-MM-DD) | 一年前 |
| `--end` | `-t` | 结束日期 (YYYY-MM-DD) | 今天 |
| `--cash` | `-c` | 初始资金 | 100000 |
| `--workers` | `-w` | 并行进程数 | 1 |
| `--output` | `-o` | 输出文件 (.json/.csv/.html) | - |
| `--verbose` | `-v` | 详细输出 | False |
| `--plot` | `-p` | 显示可视化图表 | False |
| `--plot-style` | - | 图表样式 (candle/line/bar) | candle |
| `--plot-file` | - | 保存图表到指定文件 | - |
| `--log-dir` | - | 日志输出目录 | logs/backtest/ |
| `--no-auto-save` | - | 禁用自动保存日志 | False |
| `--log-format` | - | 日志格式 (csv/json) | csv |
| `--benchmark` | `-b` | 基准指数代码 | 000300.SH |
| `--no-quantstats` | - | 禁用 QuantStats | False |
| `--open-report` | - | 自动在浏览器中打开报告 | False |

## 输出文件

回测结果保存到 `logs/backtest/{strategy_name}/{timestamp}_{hash}/`：

- `trades.csv` - 交易记录
- `daily_values.csv` - 每日资产价值
- `signals.csv` - 交易信号日志
- `capitals.csv` - 每日资金状态
- `positions.csv` - 每日持仓明细
- `orders.csv` - 订单执行日志
- `summary.json` - 回测摘要
- `plot.png` - 可视化图表
- `performance_report.html` - QuantStats HTML 报告

## 绩效指标

系统计算以下指标：

**基础指标：**
- 总收益率
- 总交易次数
- 胜率
- 盈亏比

**风险指标：**
- 最大回撤
- 夏普比率
- 波动率

**扩展指标（通过 QuantStats）：**
- Sortino 比率
- Calmar 比率
- Omega 比率
- VaR (95%)
- Alpha / Beta（相对于基准）
- CAGR（年化复合增长率）

## A 股交易规则

系统自动应用 A 股市场规则：
- 佣金：万 2.5（最低 5 元）
- 印花税：千 1（仅卖出收取）
- 涨跌停限制：10%（ST 股 5%，创业板/科创板 20%）
- T+1 交收（当日买入次日才能卖出）

## 示例工作流

### 1. 单股票快速回测

```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.examples import SmaCrossStrategy

runner = BacktestRunner()
result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=["000001.SZ"],  # 平安银行
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000
)
print(f"收益率: {result.return_pct:.2%}")
```

### 2. 多策略对比

```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.examples import SmaCrossStrategy, RsiStrategy

runner = BacktestRunner(max_workers=2)
strategies = [
    {'class': SmaCrossStrategy, 'params': {'fast': 5, 'slow': 20}},
    {'class': RsiStrategy, 'params': {'period': 14}},
]

results = runner.run_multiple(
    strategies=strategies,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000
)

for result in results:
    print(f"{result.strategy_name}: {result.return_pct:.2%}")
```

### 3. 生成完整绩效报告

```python
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy.examples import SmaCrossStrategy

config = BacktestConfig(
    enable_quantstats=True,
    auto_save_report=True,
    auto_open_report=True,
    benchmark_symbol="000300.SH"
)

runner = BacktestRunner(config=config)
result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000
)

# 报告将自动保存并在浏览器中打开
```

## 故障排除

**问题：没有加载到数据**
- 检查股票代码是否正确（深圳：`000001.SZ`，上海：`600000.SH`）
- 确认 DataHub 在该日期范围内有数据
- 如需获取数据，检查网络连接

**问题：找不到策略**
- 使用完整模块路径：`trader_center.backtest.strategy.examples.SmaCrossStrategy`
- 确保策略类继承自 `BaseStrategy`

**问题：导入错误**
- 安装回测依赖：`pip install trader-center[backtest]`
- 安装可视化库：`pip install matplotlib`
- 安装绩效分析库：`pip install quantstats`

## 依赖项

核心依赖：
- backtrader
- pandas
- numpy

可选依赖（完整功能）：
- matplotlib（可视化）
- quantstats（绩效分析）
