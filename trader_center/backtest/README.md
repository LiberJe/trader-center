# Backtest 回测模块

基于 [backtrader](https://www.backtrader.com/) 的 A股量化回测系统，与 DataHub 数据模块深度集成。

## 功能特性

- **A股交易规则支持**: 佣金万2.5、印花税千1、涨跌停限制、T+1交易
- **DataHub 集成**: 自动从 DataHub 获取历史数据
- **策略基类封装**: 简化策略开发，内置日志和交易跟踪
- **多策略并行**: 支持多进程并行回测
- **独立账户管理**: 每个策略独立资金和持仓
- **绩效分析**: 收益率、最大回撤、夏普比率等指标

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
from trader_center.backtest import BacktestRunner

runner = BacktestRunner()
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

# 保存结果
result.save("result.json")
```

### 3. 命令行使用

```bash
# 运行示例策略
python -m trader_center.backtest \
    --strategy trader_center.backtest.strategy.examples.SmaCrossStrategy \
    --symbol 000001.SZ \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --cash 100000 \
    --output result.json

# 多股票回测
python -m trader_center.backtest \
    -s trader_center.backtest.strategy.examples.SmaCrossStrategy \
    -sym 000001.SZ -sym 000002.SZ \
    -f 2024-01-01 -t 2024-12-31 \
    -o result.csv
```

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

# 绩效指标
result.calculate_max_drawdown()    # 最大回撤
result.calculate_sharpe_ratio()    # 夏普比率

# 导出
result.to_summary()     # 摘要字典
result.to_dataframe()   # DataFrame
result.save("file.json") # 保存到文件（支持 json/csv/html）
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
from trader_center.backtest.config import BacktestConfig

config = BacktestConfig(
    initial_cash=100000,      # 初始资金
    commission_rate=0.00025,  # 佣金率
    stamp_duty_rate=0.001,    # 印花税率
    min_commission=5.0,       # 最低佣金
    limit_up_pct=0.10,        # 涨停幅度
    limit_down_pct=0.10,      # 跌停幅度
    max_workers=None,         # 并行进程数
    output_dir=Path("~/.trader_center/backtest_results")
)
```

## CLI 参数

```
python -m trader_center.backtest [选项]

选项:
  -s, --strategy    策略模块路径（必需）
  -sym, --symbol    股票代码，可多次指定（必需）
  -f, --start       开始日期 (YYYY-MM-DD)
  -t, --end         结束日期 (YYYY-MM-DD)
  -c, --cash        初始资金（默认10万）
  -w, --workers     并行进程数（默认1）
  -o, --output      输出文件 (.json/.csv/.html)
  -v, --verbose     详细输出
```

## 依赖

- backtrader
- pandas
- DataHub 模块（自动集成）

## 注意事项

1. **数据依赖**: 回测需要 DataHub 模块支持，确保数据已缓存或网络可用
2. **T+1限制**: 策略中需使用 `can_sell_today()` 检查卖出条件
3. **涨跌停**: 极端行情下，backtrader 的市价单可能以涨停/跌停价成交
4. **复权处理**: 数据默认使用前复权，回测结果反映真实收益率

## 测试

```bash
# 运行回测模块测试
pytest tests/backtest/

# 运行特定测试
pytest tests/backtest/test_runner.py
pytest tests/backtest/test_examples.py::test_sma_cross_strategy
```
