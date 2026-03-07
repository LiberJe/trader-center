# Backtest 回测模块

基于 [backtrader](https://www.backtrader.com/) 的 A股量化回测系统，与 DataHub 数据模块深度集成。

## 功能特性

- **A股交易规则支持**: 佣金万2.5、印花税千1、涨跌停限制、T+1交易
- **DataHub 集成**: 自动从 DataHub 获取历史数据
- **策略基类封装**: 简化策略开发，内置日志和交易跟踪
- **多策略并行**: 支持多进程并行回测
- **独立账户管理**: 每个策略独立资金和持仓
- **绩效分析**: 收益率、最大回撤、夏普比率等指标
- **完整交易日志**: 信号日志、资金日志、持仓日志、订单日志
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
        self._log_daily_state()  # 记录每日资金和持仓状态
        
        if not self.position:
            if self.crossover > 0:  # 金叉买入
                # 记录买入信号
                self.log_signal(
                    signal_type='buy',
                    data=self.data,
                    trigger_condition=f'SMA金叉: 快线{self.sma_fast[0]:.2f} > 慢线{self.sma_slow[0]:.2f}',
                    indicator_values={
                        'sma_fast': self.sma_fast[0],
                        'sma_slow': self.sma_slow[0],
                    },
                    confidence=0.8,
                    target_price=self.data.close[0] * 1.1,
                    stop_loss=self.data.close[0] * 0.95,
                )
                self.buy()
        else:
            if self.crossover < 0:  # 死叉卖出
                # 记录卖出信号
                self.log_signal(
                    signal_type='sell',
                    data=self.data,
                    trigger_condition=f'SMA死叉: 快线{self.sma_fast[0]:.2f} < 慢线{self.sma_slow[0]:.2f}',
                    indicator_values={
                        'sma_fast': self.sma_fast[0],
                        'sma_slow': self.sma_slow[0],
                    },
                    confidence=0.8,
                )
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
    │   │   ├── trades.csv           # 交易记录
    │   │   ├── daily_values.csv     # 每日资产价值
    │   │   ├── signals.csv          # 信号日志（新增）
    │   │   ├── capitals.csv         # 资金日志（新增）
    │   │   ├── positions.csv        # 持仓日志（新增）
    │   │   ├── orders.csv           # 订单日志（新增）
    │   │   ├── summary.json         # 回测摘要
    │   │   └── plot.png             # 可视化图表
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

| 文件 | 说明 | 主要字段 |
|------|------|----------|
| `trades.csv` | 交易闭环记录 | date, symbol, pnl, pnlcomm, commission |
| `daily_values.csv` | 每日资产价值 | date, value, cash |
| `signals.csv` | 交易信号日志 | datetime, symbol, signal_type, trigger_condition, confidence, target_price, stop_loss |
| `capitals.csv` | 每日资金状态 | date, cash, position_value, total_value, cash_ratio, daily_pnl, daily_return |
| `positions.csv` | 每日持仓详情 | date, symbol, size, cost_price, current_price, market_value, pnl, pnl_ratio, holding_days |
| `orders.csv` | 订单执行日志 | order_id, datetime, symbol, action, status, expected_price, executed_price, slippage, commission |
| `summary.json` | 回测摘要 | strategy_name, params, return_pct, max_drawdown, sharpe_ratio |
| `plot.png` | 可视化图表 | 资产曲线、回撤曲线、收益分布、绩效摘要 |

### 日志文件字段详解

#### signals.csv - 交易信号日志

记录策略产生的所有交易信号，用于信号分析和策略优化。

| 字段 | 类型 | 说明 |
|------|------|------|
| `datetime` | datetime | 信号产生时间 |
| `symbol` | str | 标的代码 |
| `signal_type` | str | 信号类型: buy / sell |
| `trigger_condition` | str | 触发条件描述 |
| `indicator_values` | dict | 指标值快照 (JSON) |
| `confidence` | float | 信号强度 (0-1) |
| `target_price` | float | 目标价格 |
| `stop_loss` | float | 止损价 |
| `take_profit` | float | 止盈价 |

#### capitals.csv - 每日资金状态

记录每日资金变化，用于资金曲线分析和风险监控。

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | date | 日期 |
| `cash` | float | 可用现金 |
| `position_value` | float | 持仓市值 |
| `total_value` | float | 总资产 |
| `cash_ratio` | float | 现金比例 |
| `position_ratio` | float | 持仓比例 |
| `daily_pnl` | float | 当日盈亏 |
| `daily_return` | float | 当日收益率 |

#### positions.csv - 每日持仓详情

记录每日持仓状态，用于持仓分析和绩效归因。

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | date | 日期 |
| `symbol` | str | 标的代码 |
| `size` | int | 持仓数量 |
| `cost_price` | float | 成本价 |
| `current_price` | float | 当前价 |
| `market_value` | float | 市值 |
| `pnl` | float | 浮动盈亏 |
| `pnl_ratio` | float | 盈亏比例 |
| `holding_days` | int | 持仓天数 |
| `weight` | float | 权重 |

#### orders.csv - 订单执行日志

记录订单提交和执行过程，用于滑点分析和执行效率评估。

| 字段 | 类型 | 说明 |
|------|------|------|
| `order_id` | str | 订单ID |
| `datetime` | datetime | 订单时间 |
| `symbol` | str | 标的代码 |
| `action` | str | 买卖方向: buy / sell |
| `order_type` | str | 订单类型: market / limit |
| `expected_price` | float | 预期价格 |
| `expected_size` | int | 预期数量 |
| `status` | str | 状态: submitted / completed / canceled / rejected |
| `executed_price` | float | 成交价格 |
| `executed_size` | int | 成交数量 |
| `slippage` | float | 滑点 |
| `commission` | float | 手续费 |
| `message` | str | 状态消息 |

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
├── trade_logger.py      # 完整交易日志记录器
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
        # 记录每日资金和持仓状态
        self._log_daily_state()
        
        # 策略逻辑（每根K线执行）
        pass
```

**内置方法:**

| 方法 | 说明 |
|------|------|
| `log(txt)` | 记录日志 |
| `log_signal(...)` | 记录交易信号 |
| `log_daily_capital()` | 记录当日资金状态 |
| `log_daily_positions()` | 记录当日持仓状态 |
| `_log_daily_state()` | 记录每日资金和持仓（推荐在 next() 开头调用） |
| `notify_order(order)` | 订单状态回调 |
| `notify_trade(trade)` | 交易闭环回调 |
| `can_sell_today(data)` | T+1卖出检查 |
| `get_trades_df()` | 获取交易记录 |

**log_signal 参数说明:**

```python
def log_signal(
    signal_type: str,              # 信号类型: 'buy' / 'sell'
    data: bt.DataBase = None,      # 数据对象，默认第一个
    trigger_condition: str = "",   # 触发条件描述
    indicator_values: dict = None, # 指标值快照
    confidence: float = 1.0,       # 信号强度 (0-1)
    target_price: float = None,    # 目标价格
    stop_loss: float = None,       # 止损价
    take_profit: float = None,     # 止盈价
):
    """记录交易信号"""
```

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

# 日志数据（新增）
result.signal_log       # 信号日志列表
result.capital_log      # 资金日志列表
result.position_log     # 持仓日志列表
result.order_log        # 订单日志列表

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
result.save_signal_log(output_dir)      # 保存信号日志
result.save_capital_log(output_dir)     # 保存资金日志
result.save_position_log(output_dir)    # 保存持仓日志
result.save_order_log(output_dir)       # 保存订单日志
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

    # 日志记录开关（新增）
    enable_signal_log=True,                    # 启用信号日志
    enable_capital_log=True,                   # 启用资金日志
    enable_position_log=True,                  # 启用持仓日志
    enable_order_log=True,                     # 启用订单日志

    # 绩效分析配置（新增）
    enable_quantstats=True,                    # 启用 QuantStats 绩效分析
    benchmark_symbol="000300.SH",              # 默认基准（沪深300）
    auto_save_report=True,                     # 自动保存 HTML 报告
    auto_open_report=False,                    # 回测完成后自动打开浏览器展示报告
)
```

## 绩效分析

### QuantStats 集成

回测模块集成了 [QuantStats](https://github.com/ranaroussi/quantstats) 库，提供专业级绩效分析能力。

#### 安装依赖

```bash
pip install trader-center[backtest]
```

#### 使用方式

**方式一：自动生成报告**

回测完成后自动生成 HTML 报告：

```python
from trader_center.backtest import BacktestRunner, BacktestConfig

config = BacktestConfig(
    enable_quantstats=True,
    benchmark_symbol="000300.SH",  # 沪深300作为基准
    auto_save_report=True,
)

runner = BacktestRunner(config=config)
result = runner.run(...)

# 报告自动保存到 logs/backtest/{strategy}/{run_id}/performance_report.html
```

**方式二：手动生成报告**

```python
from trader_center.backtest import PerformanceAnalytics
import pandas as pd

# 从收益率序列创建分析器
returns = pd.Series([0.01, -0.02, 0.03], 
                    index=pd.date_range('2024-01-01', periods=3))
analytics = PerformanceAnalytics(returns)

# 获取绩效指标
metrics = analytics.metrics()
print(f"夏普比率: {metrics['sharpe']:.2f}")
print(f"Sortino比率: {metrics['sortino']:.2f}")

# 生成 HTML 报告
analytics.report('report.html', title='My Strategy')
```

**方式三：从 BacktestResult 生成**

```python
result = runner.run(...)

# 获取扩展绩效指标
metrics = result.get_extended_metrics()

# 生成完整报告
result.generate_performance_report(
    output_dir='./reports',
    benchmark='000300.SH',
    title='策略绩效报告'
)
```

#### 支持的绩效指标

| 类别 | 指标 | 说明 |
|------|------|------|
| **收益指标** | Total Return | 总收益 |
| | CAGR | 年化复合增长率 |
| | Expected Return | 预期收益 |
| **风险指标** | Volatility | 年化波动率 |
| | Max Drawdown | 最大回撤 |
| | VaR (95%) | 风险价值 |
| | CVaR (95%) | 条件风险价值 |
| | Downside Deviation | 下行偏差 |
| **风险调整收益** | Sharpe Ratio | 夏普比率 |
| | Sortino Ratio | 索提诺比率 |
| | Calmar Ratio | 卡尔马比率 |
| | Omega Ratio | 欧米伽比率 |
| | Tail Ratio | 尾部比率 |
| **基准对比** | Alpha | 超额收益 |
| | Beta | 系统性风险暴露 |
| | Information Ratio | 信息比率 |
| | R-Squared | 拟合优度 |

#### HTML 报告内容

QuantStats 生成的 HTML 报告包含：

- 收益曲线与基准对比
- 回撤分析图
- 月度收益热力图
- 年度收益统计
- 滚动夏普比率
- 滚动波动率
- 收益分布直方图
- 完整绩效指标表格

### CLI 参数

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

  绩效分析选项:
  -b, --benchmark     基准指数代码（默认沪深300: 000300.SH）
  --no-quantstats     禁用 QuantStats 绩效分析
  --no-report         禁用自动保存 HTML 绩效报告
  --open-report       回测完成后自动打开浏览器展示绩效报告
```

## 依赖

### 核心依赖
- backtrader
- pandas
- DataHub 模块（自动集成）

### 可选依赖
- matplotlib（可视化）
- quantstats（绩效分析）

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
