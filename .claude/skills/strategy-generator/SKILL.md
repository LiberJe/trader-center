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

## 代码生成目录规则

**重要**: 所有策略必须按照 [AGENT.md](../../../../AGENT.md) 中定义的目录结构生成。

### 策略目录结构（强制）

**路径**: `trader_center/backtest/strategy/{strategy-name}/`

```
{strategy-name}/
├── __init__.py        # 导出策略类
├── index.py           # 策略主代码（必须）
├── config.py          # 策略配置（必须）
└── README.md          # 策略说明（必须）
```

### 命名规范

- **目录名**: snake_case，如 `macd_strategy`
- **策略类名**: PascalCase + Strategy，如 `MacdStrategy`
- **name 属性**: snake_case，如 `name = "macd_strategy"`

### 必需操作

生成策略后必须完成以下步骤：

1. ✅ 创建策略目录 `trader_center/backtest/strategy/{strategy-name}/`
2. ✅ 创建 `index.py` 包含策略类
3. ✅ 创建 `config.py` 包含参数配置
4. ✅ 创建 `README.md` 说明策略逻辑
5. ✅ 创建 `__init__.py` 导出策略类
6. ✅ 在 `trader_center/backtest/strategy/__init__.py` 中导入新策略

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

### index.py 模板

```python
"""
策略描述
"""

import backtrader as bt
from trader_center.backtest.strategy.base import BaseStrategy


class StrategyNameStrategy(BaseStrategy):
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

### config.py 模板

```python
"""
策略配置
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class StrategyNameConfig:
    """策略配置类"""

    # 策略参数
    param1: int = 10
    param2: float = 0.5

    # 回测参数
    initial_cash: float = 100000.0
    commission: float = 0.00025  # 万2.5
    stake: int = 100  # 每次交易股数

    def to_params(self) -> Dict[str, Any]:
        """转换为 backtrader params 格式"""
        return {
            'param1': self.param1,
            'param2': self.param2,
        }


# 默认配置
DEFAULT_CONFIG = StrategyNameConfig()

# 优化参数范围（用于参数优化）
PARAM_RANGES = {
    'param1': range(5, 50, 5),
    'param2': [0.1, 0.2, 0.3, 0.5, 0.8],
}
```

### README.md 模板

```markdown
# 策略名称

## 描述

策略中文描述...

## 策略逻辑

### 买入条件

1. 条件1描述
2. 条件2描述

### 卖出条件

1. 条件1描述
2. 条件2描述

## 参数说明

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| param1 | int | 10 | 参数1说明 |
| param2 | float | 0.5 | 参数2说明 |

## 回测示例

```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.strategy_name import StrategyNameStrategy
from trader_center.backtest.strategy.strategy_name.config import DEFAULT_CONFIG

runner = BacktestRunner()
result = runner.run(
    strategy=StrategyNameStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params=DEFAULT_CONFIG.to_params()
)
print(f"收益率: {result.return_pct:.2%}")
```

## 注意事项

- 注意事项1
- 注意事项2
```

### __init__.py 模板

```python
"""策略模块"""
from .index import StrategyNameStrategy
from .config import StrategyNameConfig, DEFAULT_CONFIG

__all__ = [
    "StrategyNameStrategy",
    "StrategyNameConfig",
    "DEFAULT_CONFIG",
]
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
4. **生成目录结构**：
   - 创建策略目录
   - 创建 `index.py`（策略代码）
   - 创建 `config.py`（配置）
   - 创建 `README.md`（说明）
   - 创建 `__init__.py`（导出）
5. **更新父级导入**：在 `trader_center/backtest/strategy/__init__.py` 中添加导入
6. **提供示例**：给出回测运行示例

## 输出要求

- 代码必须是有效的 Python 代码
- 所有注释和文档字符串使用中文
- 包含完整的 `__init__` 和 `next()` 方法
- 提供参数说明和策略逻辑说明
- 给出回测使用示例
- **必须创建完整的目录结构（4个文件）**
- **必须更新父级 `__init__.py` 导入**

## 示例

**用户输入**：
> 帮我写一个MACD策略，MACD金叉买入，死叉卖出

**生成的目录结构**：
```
trader_center/backtest/strategy/macd_strategy/
├── __init__.py
├── index.py
├── config.py
└── README.md
```

**index.py**:
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

    name = "macd_strategy"
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

**父级 __init__.py 更新**：
在 `trader_center/backtest/strategy/__init__.py` 中添加：
```python
from .macd_strategy import MacdStrategy

__all__ = [
    # ... existing exports ...
    "MacdStrategy",
]
```

**回测示例**：
```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.macd_strategy import MacdStrategy
from trader_center.backtest.strategy.macd_strategy.config import DEFAULT_CONFIG

runner = BacktestRunner()
result = runner.run(
    strategy=MacdStrategy,
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params=DEFAULT_CONFIG.to_params()
)
print(f"收益率: {result.return_pct:.2%}")
```
