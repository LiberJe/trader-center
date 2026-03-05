# 回测交易日志输出到指定目录的实现计划

## 目标
将所有回测的交易日志自动输出到指定的目录中，便于后续分析和管理。

## 当前状态分析

### 现有交易日志处理
1. **BaseStrategy** ([strategy/base.py](file:///c:/workspace/trader-center/trader_center/backtest/strategy/base.py))
   - `trades`: 记录订单级别的交易（买入/卖出）
   - `closed_trades`: 记录交易闭环（包含 pnl）
   - `log()`: 日志记录方法

2. **BacktestResult** ([results.py](file:///c:/workspace/trader-center/trader_center/backtest/results.py))
   - `trades`: 交易记录列表
   - `logs`: 日志记录
   - `save()`: 保存结果到文件（支持 json/csv/html）

3. **BacktestRunner** ([runner.py](file:///c:/workspace/trader-center/trader_center/backtest/runner.py))
   - 提取交易记录到 `result.trades`
   - 需要显式调用 `result.save()` 才保存

4. **BacktestConfig** ([config.py](file:///c:/workspace/trader-center/trader_center/backtest/config.py))
   - 已有 `output_dir` 配置项

### 问题
- 交易日志不会自动保存，需要手动调用 `save()`
- 没有统一的交易日志目录管理
- 文件命名不够规范

## 实现方案

### 1. 扩展配置类 (config.py)
添加交易日志相关配置：
- `trade_log_dir`: 交易日志输出目录（默认 `~/.trader_center/backtest_logs`）
- `auto_save_trades`: 是否自动保存交易日志（默认 True）
- `trade_log_format`: 日志格式（csv/json，默认 csv）

### 2. 扩展 BacktestResult (results.py)
添加方法：
- `save_trades()`: 专门保存交易日志
- `save_logs()`: 专门保存运行日志
- 生成规范文件名：`{strategy_name}_{start_date}_{end_date}_trades.csv`

### 3. 修改 BacktestRunner (runner.py)
在 `run()` 方法结束时：
- 自动调用交易日志保存
- 使用配置中的目录
- 生成唯一且有意义的文件名

### 4. 更新 CLI (cli.py)
添加命令行参数：
- `--log-dir`: 指定日志输出目录
- `--no-auto-save`: 禁用自动保存

### 5. 更新 BaseStrategy (strategy/base.py)
- 收集更详细的交易日志信息
- 包含订单状态、执行时间等

## 实现步骤

### Step 1: 更新配置类
文件: `trader_center/backtest/config.py`
- 添加 `trade_log_dir` 属性
- 添加 `auto_save_trades` 属性
- 添加 `trade_log_format` 属性
- 在 `__post_init__` 中创建日志目录

### Step 2: 扩展 BacktestResult
文件: `trader_center/backtest/results.py`
- 添加 `save_trades()` 方法
- 添加 `save_logs()` 方法
- 添加 `generate_log_filename()` 方法
- 支持追加模式（同一策略多次运行）

### Step 3: 修改 BacktestRunner
文件: `trader_center/backtest/runner.py`
- 在 `__init__` 中接受 `config` 参数
- 在 `run()` 方法结束时自动保存交易日志
- 记录保存路径到结果中

### Step 4: 更新 CLI
文件: `trader_center/backtest/cli.py`
- 添加 `--log-dir` 参数
- 添加 `--no-auto-save` 参数
- 添加 `--log-format` 参数
- 在输出中显示日志保存路径

### Step 5: 更新模块导出
文件: `trader_center/backtest/__init__.py`
- 导出新的配置选项

## 文件命名规范

交易日志文件命名格式：
```
{strategy_name}/{start_date}_{end_date}_trades.csv
{strategy_name}/{start_date}_{end_date}_summary.json
```

示例：
```
~/.trader_center/backtest_logs/
├── sma_cross/
│   ├── 2024-01-01_2024-12-31_trades.csv
│   ├── 2024-01-01_2024-12-31_summary.json
│   └── 2024-01-01_2024-12-31_daily_values.csv
└── rsi_strategy/
    └── 2024-06-01_2024-12-31_trades.csv
```

## 输出内容

### trades.csv 包含字段
- date: 交易日期
- symbol: 股票代码
- action: 买入/卖出
- price: 成交价格
- size: 成交数量
- value: 成交金额
- commission: 手续费
- pnl: 盈亏（闭环交易）
- pnlcomm: 净盈亏

### summary.json 包含
- 策略名称和参数
- 回测周期
- 收益率、最大回撤、夏普比率
- 交易统计

## 兼容性
- 保持现有 API 不变
- 新功能通过配置项控制
- 默认启用自动保存
