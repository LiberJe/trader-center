# 修改交易日志输出到当前工程目录

## 目标
将回测交易日志从全局目录 (`~/.trader_center/backtest_logs`) 改为输出到当前工程目录下 (`./logs/backtest/`)。

## 当前问题
- 日志输出到 `Path.home() / ".trader_center" / "backtest_logs"`，即用户主目录下的全局位置
- 不便于项目管理和版本控制
- 日志与项目代码分离，难以追踪

## 解决方案

### 修改文件
**文件**: `trader_center/backtest/config.py`

### 修改内容
将 `trade_log_dir` 的默认值从：
```python
trade_log_dir: Path = field(default_factory=lambda: Path.home() / ".trader_center" / "backtest_logs")
```

改为：
```python
trade_log_dir: Path = field(default_factory=lambda: Path.cwd() / "logs" / "backtest")
```

### 目录结构
修改后，日志将输出到：
```
c:\workspace\trader-center\
└── logs\
    └── backtest\
        ├── sma_cross\
        │   ├── 2024-01-01_2024-12-31_trades.csv
        │   ├── 2024-01-01_2024-12-31_daily_values.csv
        │   └── 2024-01-01_2024-12-31_summary.json
        └── rsi_strategy\
            └── ...
```

### 注意事项
1. `Path.cwd()` 返回当前工作目录，在命令行运行时通常是项目根目录
2. 需要更新 `.gitignore` 忽略 `logs/` 目录
3. 保持向后兼容，用户仍可通过 `--log-dir` 参数指定其他目录

## 实现步骤

### Step 1: 修改 config.py
将 `trade_log_dir` 默认值改为 `Path.cwd() / "logs" / "backtest"`

### Step 2: 更新 .gitignore
添加 `logs/` 目录到忽略列表

## 影响范围
- 仅影响默认日志输出位置
- 用户通过 `--log-dir` 指定的路径不受影响
- 现有测试无需修改（测试不依赖具体路径）
