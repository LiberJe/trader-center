# ETF-Sharp策略单资产止损方案

## 1. 需求分析

### 1.1 当前问题
当前 `ETFSharpStrategy` 没有止损机制，单个ETF可能大幅亏损而无法及时止损。

### 1.2 目标
为策略添加单资产止损功能，在单个ETF亏损达到阈值时自动卖出止损。

## 2. 止损方案设计

### 2.1 止损类型

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| 固定百分比止损 | 亏损超过固定比例时止损 | 简单直接，易于理解 |
| ATR止损 | 根据ATR动态设置止损位 | 适应不同波动率资产 |
| 移动止损 | 盈利后上移止损位保护利润 | 保护盈利，避免回吐 |

### 2.2 推荐方案：固定百分比止损 + 移动止盈

**原因**：
- ETF波动率相对稳定，固定百分比止损足够
- 实现简单，参数少
- 可选移动止盈保护利润

### 2.3 止损逻辑

```
每日检查:
├── 遍历所有持仓
├── 计算当前盈亏比例
│   └── 盈亏比例 = (当前价格 - 买入均价) / 买入均价
├── 检查止损条件
│   ├── 固定止损: 盈亏比例 <= -stop_loss_pct
│   └── 移动止盈: 
│       ├── 更新最高价
│       └── 当前价格 <= 最高价 * (1 - trailing_stop_pct)
├── 触发止损
│   ├── 记录止损信号
│   ├── 卖出该资产
│   └── 标记该资产短期内不再买入（可选）
└── 更新止损状态
```

## 3. 参数设计

### 3.1 新增参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `stop_loss_pct` | float | 0.10 | 止损比例，默认10% |
| `trailing_stop_pct` | float | 0.05 | 移动止盈回撤比例，默认5% |
| `trailing_stop_enabled` | bool | True | 是否启用移动止盈 |
| `stop_loss_cooldown` | int | 5 | 止损后冷却期（交易日），期间不再买入 |

### 3.2 参数说明

- `stop_loss_pct = 0.10`：单个ETF亏损超过10%时止损
- `trailing_stop_pct = 0.05`：盈利后，从最高点回撤超过5%时止盈
- `trailing_stop_enabled = True`：启用移动止盈
- `stop_loss_cooldown = 5`：止损后5个交易日内不再买入该资产

## 4. 数据结构

### 4.1 新增实例变量

```python
# 止损相关
self.entry_prices: Dict[str, float] = {}      # 买入均价 {symbol: price}
self.highest_prices: Dict[str, float] = {}    # 最高价 {symbol: price}
self.stop_loss_dates: Dict[str, int] = {}     # 止损日期 {symbol: day_index}
```

### 4.2 数据更新时机

- **买入时**：记录买入均价，初始化最高价
- **每日**：更新最高价，检查止损条件
- **止损时**：记录止损日期，清除相关数据
- **卖出时**：清除相关数据

## 5. 实现步骤

### Step 1: 添加止损参数
- [ ] 在 `params` 中添加止损相关参数

### Step 2: 初始化止损变量
- [ ] 在 `__init__` 中初始化止损相关变量

### Step 3: 实现止损检查方法
- [ ] 实现 `_check_stop_loss()` 方法
- [ ] 实现 `_update_highest_price()` 方法
- [ ] 实现 `_is_in_cooldown()` 方法

### Step 4: 在 next() 中调用止损检查
- [ ] 在每日执行中调用止损检查
- [ ] 在止损后执行卖出操作

### Step 5: 更新买入均价
- [ ] 在买入时记录买入均价
- [ ] 在加仓时更新加权均价

### Step 6: 更新资产选择逻辑
- [ ] 在 `_select_assets` 中排除冷却期资产

### Step 7: 更新日志输出
- [ ] 添加止损信号日志
- [ ] 添加止损统计信息

## 6. 代码修改清单

### 6.1 params 新增

```python
params = (
    # ... 现有参数 ...
    ('stop_loss_pct', 0.10),           # 止损比例
    ('trailing_stop_pct', 0.05),       # 移动止盈回撤比例
    ('trailing_stop_enabled', True),   # 是否启用移动止盈
    ('stop_loss_cooldown', 5),         # 止损冷却期
)
```

### 6.2 __init__ 新增

```python
# 止损相关
self.entry_prices: Dict[str, float] = {}
self.highest_prices: Dict[str, float] = {}
self.stop_loss_dates: Dict[str, int] = {}
```

### 6.3 新增方法

```python
def _check_stop_loss(self):
    """检查并执行止损"""
    
def _update_highest_price(self, symbol: str, price: float):
    """更新最高价"""
    
def _is_in_cooldown(self, symbol: str) -> bool:
    """检查是否在冷却期"""
    
def _get_entry_price(self, symbol: str) -> float:
    """获取买入均价"""
    
def _update_entry_price(self, symbol: str, price: float, size: int):
    """更新买入均价（加权平均）"""
```

### 6.4 修改方法

```python
def next(self):
    """每日执行"""
    # ... 现有逻辑 ...
    
    # 新增：止损检查
    self._check_stop_loss()
    
    # ... 后续逻辑 ...

def _select_assets(self, scores: Dict[str, float]) -> List[str]:
    """选择资产时排除冷却期资产"""
    # 新增：排除冷却期资产
    available = [s for s in candidates if not self._is_in_cooldown(s)]
    return available
```

## 7. 止损信号记录

```python
self.log_signal(
    signal_type='stop_loss',  # 或 'trailing_stop'
    data=data,
    trigger_condition=f'止损卖出: {asset_name} 亏损 {loss_pct:.2%}',
    indicator_values={
        'entry_price': entry_price,
        'current_price': current_price,
        'loss_pct': loss_pct,
        'highest_price': highest_price,
    },
    confidence=1.0,
)
```

## 8. 回测参数建议

| 参数 | 保守型 | 平衡型 | 激进型 |
|------|--------|--------|--------|
| stop_loss_pct | 0.05 (5%) | 0.10 (10%) | 0.15 (15%) |
| trailing_stop_pct | 0.03 (3%) | 0.05 (5%) | 0.08 (8%) |
| trailing_stop_enabled | True | True | True |
| stop_loss_cooldown | 10 | 5 | 3 |

## 9. 注意事项

1. **止损与再平衡的协调**：止损优先于再平衡执行
2. **冷却期处理**：止损后的资产在冷却期内不再买入
3. **买入均价计算**：多次买入时使用加权平均
4. **日志记录**：详细记录止损触发原因和结果
5. **参数验证**：止损比例应为正数，移动止盈比例应小于止损比例

## 10. 文件修改

| 文件 | 修改内容 |
|------|----------|
| `etf_sharp.py` | 添加止损参数、变量、方法和逻辑 |
| `run_etf_sharp.py` | 更新回测参数配置 |
