# 回测系统问题分析报告

## 概述

对 `trader_center/backtest` 模块进行全面审查，发现以下问题，按严重程度分类。

**更新日期: 2026-03-05** - 已修复的问题标记为 ✅

---

## 🔴 严重问题（影响核心功能）

### 1. 手续费计算参数错误 ✅ 已修复

**位置**: [broker.py:27](file:///c:/workspace/trader-center/trader_center/backtest/broker.py#L27)

**问题描述**:
```python
params = (
    ('commission', 0.025),   # 注释说是万2.5，但实际值是 2.5%
    ...
)
```

- 注释说是"万2.5"，即 0.00025
- 实际代码值是 0.025，即 2.5%
- **这会导致手续费被放大100倍！**

**修复方案**:
- 将 `commission` 参数改为 `0.00025`
- 将 `stamp_duty` 参数改为 `0.001`
- 将 `commtype` 改为 `COMM_FIXED` 以避免 backtrader 的百分比转换

---

### 2. daily_values 从未被填充 ✅ 已修复

**位置**: [results.py:39](file:///c:/workspace/trader-center/trader_center/backtest/results.py#L39), [runner.py:137](file:///c:/workspace/trader-center/trader_center/backtest/runner.py#L137)

**问题描述**:
- `BacktestResult.daily_values` 定义了但从未被填充
- 导致 `calculate_max_drawdown()` 永远返回 0.0
- 导致 `calculate_sharpe_ratio()` 永远返回 0.0

**修复方案**: 
- 添加 `DailyValueObserver` 观察器记录每日资产价值
- 在 `BacktestRunner.run()` 中提取观察器数据填充 `daily_values`

---

### 3. 交易记录缺少 pnl 字段 ✅ 已修复

**位置**: [base.py:96-103](file:///c:/workspace/trader-center/trader_center/backtest/strategy/base.py#L96-L103)

**问题描述**:
```python
self.trades.append({
    'date': ...,
    'action': ...,
    'price': ...,
    'size': ...,
    'value': ...,
    'commission': ...,
    # 缺少 'pnl' 字段！
})
```

**修复方案**: 
- 添加 `closed_trades` 列表专门记录交易闭环
- 在 `notify_trade()` 回调中记录完整的交易闭环信息，包括 `pnl`
- `get_trades_df()` 返回 `closed_trades` 而非 `trades`

---

### 4. StrategyAccount 类未被使用

**位置**: [account.py](file:///c:/workspace/trader-center/trader_center/backtest/account.py)

**问题描述**:
- 设计文档要求使用独立账户模式
- `StrategyAccount` 类已实现但从未在 `runner.py` 中集成
- 多策略回测时无法实现资金隔离

**影响**: 多策略并行时，所有策略共享同一个 broker 账户，无法实现独立账户模式。

---

## 🟠 中等问题（影响功能完整性）

### 5. 分析器结果未被提取 ✅ 已修复

**位置**: [runner.py:118-124](file:///c:/workspace/trader-center/trader_center/backtest/runner.py#L118-L124)

**问题描述**:
```python
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
# ... 但结果从未被提取使用！
```

**修复方案**: 
- 在 `BacktestRunner.run()` 中提取分析器结果
- 添加 `analyzer_results` 字段到 `BacktestResult`

---

### 6. 多进程序列化问题 ✅ 已修复

**位置**: [runner.py:232-249](file:///c:/workspace/trader-center/trader_center/backtest/runner.py#L232-L249)

**问题描述**:
```python
def _run_single_worker(self, config: Dict[str, Any], ...):
    """工作进程执行的函数（必须是静态方法或模块函数）"""
    ...
```

- 注释说"必须是静态方法或模块函数"，但实际是实例方法
- 实例方法无法被 pickle 序列化

**修复方案**: 
- 将 `_run_single_worker` 改为模块级函数
- 直接传递策略类和参数，而非配置字典

---

### 7. 涨跌停检查不完善

**位置**: [broker.py:97-143](file:///c:/workspace/trader-center/trader_center/backtest/broker.py#L97-L143)

**问题描述**:
- 只支持 10% 涨跌停
- 未考虑 ST 股票（5% 涨跌停）
- 未考虑创业板/科创板（20% 涨跌停）
- 未考虑新股上市首日（44% 涨停）

**修复方案**: 根据股票代码自动识别板块类型，设置不同的涨跌停幅度。

---

### 8. T+1 检查未强制执行

**位置**: [base.py:132-149](file:///c:/workspace/trader-center/trader_center/backtest/strategy/base.py#L132-L149)

**问题描述**:
- `can_sell_today()` 方法已实现
- 但策略中需要手动调用检查
- 没有在 Broker 层面强制阻止 T+0 卖出

**风险**: 策略开发者可能忘记调用检查，导致回测结果与实际情况不符。

---

### 9. BacktestConfig 未被使用

**位置**: [config.py](file:///c:/workspace/trader-center/trader_center/backtest/config.py)

**问题描述**:
- `BacktestConfig` 类定义了完整的配置项
- 但 `runner.py` 中直接使用硬编码参数
- 配置参数分散在多处，难以统一管理

---

### 10. 数据验证缺失

**位置**: [data_feed.py:45-70](file:///c:/workspace/trader-center/trader_center/backtest/data_feed.py#L45-L70)

**问题描述**:
- 只检查列是否存在
- 未验证数据质量：
  - high >= low
  - close 在 [low, high] 范围内
  - volume >= 0
  - 价格无异常值（如 0 或负数）

---

## 🟡 轻微问题（代码质量）

### 11. 缺少 analyzers.py

**位置**: 设计文档提到但未实现

**问题描述**:
- 设计文档要求实现 `analyzers.py`
- 实际未创建该文件
- 无法扩展自定义绩效分析器

---

### 12. 缺少 utils.py

**位置**: 设计文档提到但未实现

**问题描述**:
- 设计文档要求实现 `utils.py`
- 实际未创建该文件
- 辅助函数分散在各模块中

---

### 13. CLI 功能不完整

**位置**: [cli.py](file:///c:/workspace/trader-center/trader_center/backtest/cli.py)

**问题描述**:
- 不支持多策略配置文件（YAML/JSON）
- 不支持参数优化
- 不支持结果对比

---

### 14. 测试覆盖不足

**位置**: [tests/backtest/](file:///c:/workspace/trader-center/tests/backtest/)

**问题描述**:
- `test_runner.py` 只有创建测试，没有运行测试
- 没有测试多进程并行
- 没有测试绩效指标计算
- 没有测试错误处理边界情况

---

### 15. 缺少风险控制模块

**问题描述**:
- 无止损/止盈功能
- 无仓位管理功能
- 无风险敞口限制

---

### 16. 缺少回测报告生成

**问题描述**:
- `results.py` 的 `save()` 方法只支持简单的 HTML
- 缺少专业的回测报告模板
- 缺少可视化图表生成

---

### 17. 缺少参数优化功能

**问题描述**:
- 不支持参数网格搜索
- 不支持参数优化结果分析
- 设计文档提到的"参数优化"功能未实现

---

## 📊 问题统计

| 严重程度 | 数量 | 占比 |
|---------|------|------|
| 🔴 严重 | 4 | 23.5% |
| 🟠 中等 | 6 | 35.3% |
| 🟡 轻微 | 7 | 41.2% |
| **总计** | **17** | **100%** |

---

## 🎯 修复优先级建议

### 第一优先级（必须立即修复）
1. 手续费参数错误（问题 #1）
2. daily_values 未填充（问题 #2）
3. 交易记录缺少 pnl（问题 #3）

### 第二优先级（影响核心功能）
4. 分析器结果提取（问题 #5）
5. StrategyAccount 集成（问题 #4）
6. 涨跌停检查完善（问题 #7）

### 第三优先级（功能完善）
7. 多进程序列化修复（问题 #6）
8. T+1 强制执行（问题 #8）
9. BacktestConfig 集成（问题 #9）
10. 数据验证（问题 #10）

### 第四优先级（代码质量）
11-17. 其他轻微问题

---

## 📝 总结

当前回测系统存在 **4 个严重问题**，其中最关键的是：

1. **手续费计算错误** - 直接影响回测收益率的准确性
2. **绩效指标失效** - 最大回撤和夏普比率无法计算
3. **独立账户未实现** - 多策略回测功能不完整

建议按照优先级顺序逐步修复，首先解决严重问题，确保回测结果的准确性和可靠性。

---

分析日期: 2026-03-05
