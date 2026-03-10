---
name: strategy-generator
description: |
  基于 trader_center 回测框架生成量化交易策略代码。
  当用户要求创建、编写、生成量化策略时使用此技能。
  适用于各种交易策略需求：技术指标策略（均线、MACD、RSI、KDJ等）、
  趋势跟踪策略、均值回归策略、突破策略、多因子策略等。
  只要用户提到策略、量化、交易、回测、指标等关键词，立即使用此技能。
---

# 量化策略生成器

根据用户需求，基于 trader_center 回测框架生成完整的量化交易策略代码。

## 框架概述

 trader_center 使用 backtrader 作为回测引擎，策略需要：

1. **继承 `BaseStrategy`**（位于 `trader_center.backtest.strategy.base`）
2. **设置类属性**：`name`（策略标识）和 `description`（策略描述）
3. **定义参数**：使用 `params` 元组定义可配置参数
4. **实现 `next()` 方法**：核心的交易逻辑

### BaseStrategy 提供的方法

- `log_signal()` - 记录交易信号（推荐在买卖时调用）
- `_log_daily_state()` - 记录每日资金和持仓状态（建议在 next() 开头调用）
- `can_sell_today(data)` - T+1 卖出检查

## 策略代码模板

```python
"""
策略描述
"""

import backtrader as bt
from trader_center.backtest.strategy.base import BaseStrategy


class 策略名Strategy(BaseStrategy):
    """
    策略中文描述

    策略逻辑说明...

    Params:
        param1: 参数1说明（默认值）
        param2: 参数2说明（默认值）
    """

    name = "策略英文标识"
    description = "策略简短描述"

    params = (
        ('param1', 默认值1),
        ('param2', 默认值2),
    )

    def __init__(self):
        super().__init__()
        # 初始化指标
        self.indicator = bt.indicators.XXX()

    def next(self):
        self._log_daily_state()

        # 没有持仓时的逻辑
        if not self.position:
            if 买入条件:
                self.log_signal(
                    signal_type='buy',
                    data=self.data,
                    trigger_condition='买入触发条件描述',
                    indicator_values={
                        '指标名': self.indicator[0],
                        'close': self.data.close[0],
                    },
                    confidence=0.8,  # 信号置信度 0-1
                    target_price=self.data.close[0] * 1.1,  # 目标价
                    stop_loss=self.data.close[0] * 0.95,    # 止损价
                )
                self.buy()
        else:
            # 有持仓时的逻辑
            if 卖出条件:
                self.log_signal(
                    signal_type='sell',
                    data=self.data,
                    trigger_condition='卖出触发条件描述',
                    indicator_values={
                        '指标名': self.indicator[0],
                        'close': self.data.close[0],
                    },
                    confidence=0.8,
                )
                self.sell()
```

## 常用 backtrader 指标

| 指标 | 类名 | 常用参数 |
|------|------|----------|
| 简单均线 | `bt.indicators.SMA` | `period` |
| 指数均线 | `bt.indicators.EMA` | `period` |
| MACD | `bt.indicators.MACD` | `period_me1`, `period_me2`, `period_signal` |
| RSI | `bt.indicators.RSI` | `period` |
| 布林带 | `bt.indicators.BollingerBands` | `period`, `devfactor` |
| ATR | `bt.indicators.ATR` | `period` |
| 交叉检测 | `bt.indicators.CrossOver` | 两个指标/数据线 |

## A股交易规则

- **T+1 制度**：当天买入的股票次日才能卖出，使用 `can_sell_today(data)` 检查
- **涨跌停限制**：普通股票 ±10%，ST股票 ±5%
- **交易费用**：佣金万2.5（最低5元），印花税千1（卖出时）
- **代码格式**：股票代码.交易所（如 `000001.SZ`、`600519.SH`）

## 工作流程

1. **理解需求**：分析用户想要的策略类型和逻辑
2. **选择指标**：根据策略类型选择合适的技术指标
3. **设计参数**：提取可配置的参数（周期、阈值等）
4. **编写代码**：生成完整的策略类代码
5. **提供示例**：给出回测运行示例

## 输出要求

- 代码必须是有效的 Python 代码
- 所有注释和文档字符串使用中文
- 包含完整的 `__init__` 和 `next()` 方法
- 提供参数说明和策略逻辑说明
- 给出回测使用示例

## 示例

**用户输入**：
> 帮我写一个MACD策略，MACD金叉买入，死叉卖出

**生成的策略**：
```python
"""
MACD策略

MACD金叉买入，死叉卖出
"""

import backtrader as bt
from trader_center.backtest.strategy.base import BaseStrategy


class MacdStrategy(BaseStrategy):
    """
    MACD金叉死叉策略

    当MACD柱状线由负转正（金叉）时买入，
    由正转负（死叉）时卖出。

    Params:
        fast: 快线周期（默认12）
        slow: 慢线周期（默认26）
        signal: 信号线周期（默认9）
    """

    name = "macd"
    description = "MACD金叉死叉策略"

    params = (
        ('fast', 12),
        ('slow', 26),
        ('signal', 9),
    )

    def __init__(self):
        super().__init__()
        self.macd = bt.indicators.MACD(
            period_me1=self.p.fast,
            period_me2=self.p.slow,
            period_signal=self.p.signal
        )
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        self._log_daily_state()

        if not self.position:
            if self.crossover > 0:
                self.log_signal(
                    signal_type='buy',
                    data=self.data,
                    trigger_condition=f'MACD金叉: DIF={self.macd.macd[0]:.3f} > DEA={self.macd.signal[0]:.3f}',
                    indicator_values={
                        'macd': self.macd.macd[0],
                        'signal': self.macd.signal[0],
                        'histogram': self.macd.histo[0],
                        'close': self.data.close[0],
                    },
                    confidence=0.75,
                    target_price=self.data.close[0] * 1.08,
                    stop_loss=self.data.close[0] * 0.96,
                )
                self.buy()
        else:
            if self.crossover < 0:
                self.log_signal(
                    signal_type='sell',
                    data=self.data,
                    trigger_condition=f'MACD死叉: DIF={self.macd.macd[0]:.3f} < DEA={self.macd.signal[0]:.3f}',
                    indicator_values={
                        'macd': self.macd.macd[0],
                        'signal': self.macd.signal[0],
                        'histogram': self.macd.histo[0],
                        'close': self.data.close[0],
                    },
                    confidence=0.75,
                )
                self.sell()
```

**回测示例**：
```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.examples import MacdStrategy

runner = BacktestRunner()
result = runner.run(
    strategy=MacdStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params={'fast': 12, 'slow': 26, 'signal': 9}
)
print(f"收益率: {result.return_pct:.2%}")
```
