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

## 文件结构

```
{strategy_name}/
├── __init__.py        # 导出策略类
├── index.py           # 策略主代码
├── config.py          # 策略配置
└── README.md          # 策略说明（本文件）
```

## 使用示例

### 基本回测

```python
from trader_center.backtest import BacktestRunner
from trader_center.backtest.strategy.{strategy_name} import {StrategyClass}
from trader_center.backtest.strategy.{strategy_name}.config import DEFAULT_CONFIG

runner = BacktestRunner()
result = runner.run(
    strategy={StrategyClass},
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=100000,
    strategy_params=DEFAULT_CONFIG.to_params()
)
print(f"收益率: {result.return_pct:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
```

### 自定义参数

```python
from trader_center.backtest.strategy.{strategy_name}.config import TemplateConfig

config = TemplateConfig(
    param1=20,
    param2=0.3,
    initial_cash=200000
)

result = runner.run(
    strategy={StrategyClass},
    symbols=["000001.SZ"],
    start="2024-01-01",
    end="2024-12-31",
    initial_cash=config.initial_cash,
    strategy_params=config.to_params()
)
```

## 注意事项

- 注意事项1
- 注意事项2

## 参考

- 相关文档链接
- 参考资料
