# Backtest 回测模块

基于 [backtrader](https://www.backtrader.com/) 的 A股量化回测系统，与 DataHub 数据模块深度集成。

## 功能特性

- **A股交易规则支持**: 佣金万2.5、印花税千1、涨跌停限制、T+1交易
- **DataHub 集成**: 自动从 DataHub 获取历史数据
- **策略基类封装**: 简化策略开发，内置日志和交易跟踪
- **多策略并行**: 支持多进程并行回测
- **独立账户管理**: 每个策略独立资金和持仓
- **绩效分析**: 收益率、最大回撤、夏普比率等指标
- **自动日志输出**: 交易日志自动保存到工程目录
- **可视化图表保存**: 回测图表自动保存到指定目录

## 快速开始

### 1. 编写策略

```python
from trader_center.backtest import BaseStrategy
import backtrader as bt

class SmaCrossStrategy(BaseStrategy):
    """双均线交叉策略"""
    name = "sma_cross"
    description = "双均线交叉策略"

    params = (
        ('fast', 5),
        ('slow', 20),
    )

    def __init__(self):
        super().__init__()
        self.sma_fast = bt.indicators.SMA(period=self.p.fast)
        self.sma_slow = bt.indicators.SMA(period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        if not self.position:
            if self.crossover > 0:  # 金叉买入
                self.buy()
        else:
            if self.crossover < 0:  # 死叉卖出
                self.sell()
```

### 2. 运行回测

```python
from trader_center.backtest import BacktestRunner, BacktestConfig

# 使用自定义配置
config = BacktestConfig(
    initial_cash=100000,
    auto_save_trades=True,
    auto_save_plot=True,
)

runner = BacktestRunner(config=config)
result = runner.run(
    strategy=SmaCrossStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params={'fast': 5, 'slow': 20}
)

# 查看结果
print(f"收益率: {result.return_pct:.2%}")
print(f"交易次数: {result.total_trades}")
print(f"最大回撤: {result.calculate_max_drawdown():.2%}")

# 查看保存的日志文件
print(f"日志文件: {result.log_files}")
```

### 3. 命令行使用

```bash
# 运行示例策略（自动保存交易日志到 logs/backtest/）
python -m trader_center.backtest \
    --strategy trader_center.backtest.strategy.examples.SmaCrossStrategy \
    --symbol 000001.SZ \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --cash 100000

# 启用可视化并自动保存图表
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ \
    -f 2024-01-01 -t 2024-12-31 \
    --plot

# 多股票回测
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ -sym 000002.SZ \
    -f 2024-01-01 -t 2024-12-31 \
    -o result.csv

# 指定日志输出目录
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ \
    --log-dir ./my_logs

# 使用 JSON 格式保存交易日志
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ \
    --log-format json
```

## 输出目录结构

每次回测生成一个独立目录，包含所有输出文件，避免重复运行覆盖：

```
logs/
└── backtest/
    ├── sma_cross/
    │   ├── 20240306_143052_a1b2c3/
    │   │   ├── trades.csv
    │   │   ├── daily_values.csv
    │   │   ├── summary.json
    │   │   └── plot.png
    │   └── 20240306_150123_d4e5f6/
    │       └── ...
    └── rsi_strategy/
        └── 20240305_091234_g7h8i9/
            └── ...
```

目录命名格式：`{strategy_name}/{timestamp}_{hash}`
- `strategy_name`: 策略名称（一级目录）
- `timestamp`: 运行时间 (YYYYMMDD_HHMMSS)
- `hash`: 短哈希值 (6位)，避免冲突

### 输出文件说明

| 文件 | 说明 |
|------|------|
| `trades.csv` | 交易记录（日期、股票、买卖、价格、数量、盈亏等） |
| `daily_values.csv` | 每日资产价值（日期、资产、现金） |
| `summary.json` | 回测摘要（策略名称、参数、收益率、风险指标等） |
| `plot.png` | 可视化图表（资产曲线、回撤、收益分布） |

## 模块结构

```
backtest/
├── __init__.py          # 模块入口，导出主要类
├── __main__.py          # python -m 入口
├── cli.py               # 命令行接口
├── config.py            # 回测配置
├── runner.py            # 回测运行器（核心）
├── data_feed.py         # DataHub 数据适配器
├── broker.py            # A股 Broker 配置
├── account.py           # 独立账户封装
├── results.py           # 回测结果和绩效指标
└── strategy/
    ├── __init__.py
    ├── base.py          # 策略基类
    └── examples.py      # 示例策略
```

## 核心组件

### BaseStrategy - 策略基类

所有策略必须继承的基类，封装了 backtrader 的 `bt.Strategy`。

```python
class MyStrategy(BaseStrategy):
    name = "my_strategy"          # 必须设置
    description = "策略描述"       # 可选
    params = (('period', 20),)    # 策略参数

    def __init__(self):
        super().__init__()
        # 初始化指标

    def next(self):
        # 策略逻辑（每根K线执行）
        pass
```

**内置方法:**

| 方法 | 说明 |
|------|------|
| `log(txt)` | 记录日志 |
| `notify_order(order)` | 订单状态回调 |
| `notify_trade(trade)` | 交易闭环回调 |
| `can_sell_today(data)` | T+1卖出检查 |
| `get_trades_df()` | 获取交易记录 |

### BacktestRunner - 回测运行器

```python
runner = BacktestRunner(max_workers=4)

# 单策略回测
result = runner.run(
    strategy=MyStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params={'period': 20}
)

# 多策略并行回测
results = runner.run_multiple(
    strategies=[
        {'class': StrategyA, 'params': {'p1': 5}},
        {'class': StrategyB, 'params': {'p2': 10}},
    ],
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
)
```

### BacktestResult - 回测结果

```python
# 基础属性
result.strategy_name    # 策略名称
result.initial_cash     # 初始资金
result.final_value      # 最终资产
result.return_pct       # 总收益率
result.total_trades     # 交易次数
result.win_rate         # 胜率
result.profit_factor    # 盈亏比
result.log_files        # 保存的日志文件路径

# 绩效指标
result.calculate_max_drawdown()    # 最大回撤
result.calculate_sharpe_ratio()    # 夏普比率

# 导出
result.to_summary()     # 摘要字典
result.to_dataframe()   # DataFrame
result.save("file.json") # 保存到文件（支持 json/csv/html）

# 手动保存日志
result.save_trades(output_dir, format="csv")
result.save_daily_values(output_dir)
result.save_summary(output_dir)
result.save_all_logs(output_dir, format="csv")
```

### A股 Broker 配置

自动配置 A股交易规则:

- **佣金**: 万2.5 (0.025%), 最低5元
- **印花税**: 千1 (0.1%), 仅卖出收取
- **涨跌停**: 默认10%（ST股5%，创业板/科创板20%）
- **T+1**: 当日买入次日才能卖出

```python
from trader_center.backtest.broker import configure_astock_broker, AStockConstraints

# 配置 Broker
configure_astock_broker(cerebro, cash=100000, slip_perc=0.001)

# 交易限制检查
constraints = AStockConstraints(limit_up_pct=0.10, limit_down_pct=0.10)
if constraints.can_buy(data, last_close):
    self.buy()
```

## 示例策略

模块内置了三个示例策略:

### 1. SmaCrossStrategy - 双均线交叉

```python
from trader_center.backtest.strategy.examples import SmaCrossStrategy

# 参数: fast=5, slow=20
# 金叉买入，死叉卖出
```

### 2. RsiStrategy - RSI超买超卖

```python
from trader_center.backtest.strategy.examples import RsiStrategy

# 参数: period=14, oversold=30, overbought=70
# RSI<30买入，RSI>70卖出
```

### 3. BuyAndHoldStrategy - 买入持有

```python
from trader_center.backtest.strategy.examples import BuyAndHoldStrategy

# 首日买入99%仓位，持有到期末
# 用于作为基准对比
```

## 配置选项

```python
from trader_center.backtest import BacktestConfig

config = BacktestConfig(
    # 资金配置
    initial_cash=100000,      # 初始资金
    commission_rate=0.00025,  # 佣金率（万2.5）
    stamp_duty_rate=0.001,    # 印花税率（千1）
    min_commission=5.0,       # 最低佣金

    # 交易限制
    limit_up_pct=0.10,        # 涨停幅度
    limit_down_pct=0.10,      # 跌停幅度

    # 执行配置
    max_workers=None,         # 并行进程数

    # 日志输出配置
    trade_log_dir=Path("logs/backtest"),      # 日志输出目录
    auto_save_trades=True,                     # 自动保存交易日志
    trade_log_format="csv",                    # 日志格式（csv/json）
    auto_save_plot=True,                       # 自动保存图表
)
```

## CLI 参数

```
python -m trader_center.backtest [选项]

选项:
  -s, --strategy      策略模块路径（必需）
  -sym, --symbol      股票代码，可多次指定（必需）
  -f, --start         开始日期 (YYYY-MM-DD)
  -t, --end           结束日期 (YYYY-MM-DD)
  -c, --cash          初始资金（默认10万）
  -w, --workers       并行进程数（默认1）
  -o, --output        输出文件 (.json/.csv/.html)
  -v, --verbose       详细输出

  日志选项:
  --log-dir           日志输出目录（默认 logs/backtest/）
  --no-auto-save      禁用自动保存日志
  --log-format        日志格式（csv/json，默认csv）

  可视化选项:
  -p, --plot          显示可视化图表
  --plot-style        图表样式（candle/line/bar，默认candle）
  --plot-file         保存图表到指定文件（覆盖自动保存）
  --no-auto-save-plot 禁用自动保存图表
```

## 依赖

- backtrader
- pandas
- matplotlib（可视化）
- DataHub 模块（自动集成）

## 注意事项

1. **数据依赖**: 回测需要 DataHub 模块支持，确保数据已缓存或网络可用
2. **T+1限制**: 策略中需使用 `can_sell_today()` 检查卖出条件
3. **涨跌停**: 极端行情下，backtrader 的市价单可能以涨停/跌停价成交
4. **复权处理**: 数据默认使用前复权，回测结果反映真实收益率
5. **日志目录**: 默认输出到 `logs/backtest/`，可通过 `--log-dir` 指定其他目录

## 测试

```bash
# 运行回测模块测试
pytest tests/backtest/

# 运行特定测试
pytest tests/backtest/test_runner.py
pytest tests/backtest/test_examples.py::test_sma_cross_strategy
```
