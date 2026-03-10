# 大类资产等权持有策略实现计划

## 概述

创建一个大类资产等权持有策略，通过定期再平衡实现资产配置分散化。该策略将等比例配置五种不同类型的大类资产ETF，降低单一资产风险，实现风险分散。

## 策略设计

### 1. 资产配置

| 资产类别 | ETF代码 | ETF名称 | 权重 |
|---------|--------|---------|------|
| 黄金 | 518880 | 华安黄金ETF | 20% |
| 沪深300 | 510300 | 华泰柏瑞沪深300ETF | 20% |
| 纳指100 | 513100 | 国泰纳斯达克100 ETF | 20% |
| 债券 | 511010 | 国泰上证5年期国债ETF | 20% |
| 大宗商品 | 159981 | 能源化工ETF | 20% |

### 2. 策略参数

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| rebalance_freq | 30 | 再平衡频率（交易日） |
| target_weight | 0.19 | 目标权重（保留1%现金） |
| tolerance | 0.05 | 偏离容忍度，超过此值才触发再平衡 |

### 3. 策略逻辑

1. **初始建仓**: 在第一个交易日，等权重买入所有资产
2. **定期再平衡**: 每隔N个交易日检查权重偏离
3. **动态调整**: 当权重偏离超过容忍度时，执行再平衡操作
4. **日志记录**: 记录每次再平衡的信号和持仓变化

## 实现步骤

### Step 1: 创建策略文件

在 `trader_center/backtest/strategy/` 目录下创建 `asset_allocation.py` 文件，实现 `EqualWeightAssetAllocation` 策略类。

**核心实现要点**:
- 继承 `BaseStrategy`
- 支持多数据源（多个ETF）
- 实现权重计算和再平衡逻辑
- 使用 `order_target_percent()` 方法进行仓位调整

### Step 2: 更新策略模块导出

在 `trader_center/backtest/strategy/__init__.py` 中导出新策略。

### Step 3: 创建示例运行脚本

创建一个独立的运行脚本 `run_asset_allocation.py`，演示如何运行该策略。

**脚本内容**:
- 配置回测参数（时间范围、初始资金等）
- 指定五种ETF代码
- 运行回测并输出结果

### Step 4: 验证测试

运行回测验证策略正确性：
- 检查初始建仓是否正确
- 检查再平衡逻辑是否按预期执行
- 检查日志输出是否完整

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|-----|---------|------|
| 新建 | `trader_center/backtest/strategy/asset_allocation.py` | 等权资产配置策略 |
| 修改 | `trader_center/backtest/strategy/__init__.py` | 导出新策略 |
| 新建 | `scripts/run_asset_allocation.py` | 策略运行示例脚本 |

## 策略代码结构

```python
class EqualWeightAssetAllocation(BaseStrategy):
    """大类资产等权持有策略"""
    
    name = "equal_weight_asset_allocation"
    description = "大类资产等权持有策略"
    
    params = (
        ('rebalance_freq', 30),    # 再平衡频率
        ('target_weight', 0.19),   # 目标权重
        ('tolerance', 0.05),       # 偏离容忍度
    )
    
    def __init__(self):
        # 初始化
        pass
    
    def next(self):
        # 策略主逻辑
        pass
    
    def _should_rebalance(self) -> bool:
        # 判断是否需要再平衡
        pass
    
    def _rebalance(self):
        # 执行再平衡
        pass
```

## 注意事项

1. **ETF交易规则**: 部分ETF可能支持T+0交易，需要根据具体ETF类型调整交易限制
2. **数据可用性**: 确保DataHub中有各ETF的历史数据
3. **现金预留**: 预留少量现金应对交易费用和价格波动
4. **滑点影响**: 再平衡时需考虑交易成本对收益的影响
