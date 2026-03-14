# 多因子轮动策略 (Multi-Factor Rotation Strategy)

基于多因子综合评分的资产轮动策略，支持灵活配置资产池和策略参数。

## 策略原理

1. **因子计算**: 为每个资产计算多个因子值（动量、趋势强度、RSI、波动率等）
2. **标准化**: 对因子值进行横截面标准化（Z-score）
3. **加权评分**: 根据因子权重合成综合得分
4. **资产选择**: 选择得分最高的N个资产
5. **定期轮动**: 按设定频率再平衡，动态调整持仓

## 配置方式

### 方式一：使用默认配置

```python
from trader_center.backtest.strategy import MultiFactorRotationStrategy

# 使用默认资产配置
strategy = MultiFactorRotationStrategy
```

### 方式二：通过参数传入配置

```python
from trader_center.backtest.strategy import MultiFactorRotationStrategy

custom_assets = {
    '518880.SH': {'name': '黄金ETF', 'category': 'commodity'},
    '510300.SH': {'name': '沪深300ETF', 'category': 'equity_cn'},
    # ... 更多资产
}

strategy_params = {
    'asset_config': custom_assets,  # 自定义资产配置
    'rebalance_freq': 20,           # 每20个交易日再平衡
    'top_n': 3,                     # 持仓3个资产
    'lookback': 60,                 # 回看60天计算因子
    'exec_type': 'close',           # 次日收盘价执行
}
```

### 方式三：使用配置类

```python
from trader_center.backtest.strategy.multi_factor_rotation import (
    MultiFactorRotationConfig, MultiFactorRotationStrategy
)

# 创建配置
config = MultiFactorRotationConfig(
    assets={
        '518880.SH': {'name': '黄金ETF', 'category': 'commodity'},
        '510300.SH': {'name': '沪深300ETF', 'category': 'equity_cn'},
    },
    rebalance_freq=20,
    top_n=2,
    lookback=60,
    exec_type='close',
)

# 保存配置到JSON
config.to_json('my_config.json')

# 从JSON加载配置
config = MultiFactorRotationConfig.load_from_json('my_config.json')

# 使用配置运行策略
strategy_params = {
    'asset_config': config.assets,
    'rebalance_freq': config.rebalance_freq,
    'top_n': config.top_n,
    'lookback': config.lookback,
    'exec_type': config.exec_type,
}
```

## 默认资产配置

| 代码 | 名称 | 类别 |
|------|------|------|
| 518880.SH | 黄金ETF | commodity |
| 510300.SH | 沪深300ETF | equity_cn |
| 513100.SH | 纳指ETF | equity_us |
| 511010.SH | 国债ETF | bond |
| 159981.SZ | 能源化工ETF | commodity |

## 策略参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| rebalance_freq | int | 20 | 再平衡频率（交易日） |
| top_n | int | 3 | 持仓资产数量 |
| factor_configs | dict | None | 因子配置字典 |
| min_score | float | -inf | 最低得分阈值 |
| lookback | int | 60 | 因子计算回看周期 |
| exec_type | str | 'open' | 执行类型：'open'/'close' |
| asset_config | dict | None | 外部传入的资产配置 |

## 运行示例

```bash
python backtest_runner/run_multi_factor_rotation.py
```

## 文件结构

```
multi_factor_rotation/
├── __init__.py        # 导出策略类和配置
├── index.py           # 策略主代码
├── config.py          # 配置类和默认资产配置
├── config.json        # JSON格式默认配置
└── README.md          # 策略说明文档
```
