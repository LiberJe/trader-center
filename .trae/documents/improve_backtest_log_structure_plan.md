# 改进回测日志输出结构

## 目标

1. 解决重复运行策略时日志被覆盖的问题
2. 将策略日志、结果和图表统一放在同一目录下

## 当前问题

### 问题1: 重复运行会覆盖

当前文件名格式：`{start_date}_{end_date}_{log_type}.csv`

* 相同策略、相同日期范围重复运行会覆盖之前的日志

* 无法追溯历史回测结果

### 问题2: 日志和图表分离

当前目录结构：

```
logs/backtest/
├── plots/
│   └── {strategy_name}/
│       └── {start}_{end}.png
└── {strategy_name}/
    ├── {start}_{end}_trades.csv
    ├── {start}_{end}_daily_values.csv
    └── {start}_{end}_summary.json
```

问题：

* 图表和日志分散在不同位置

* 不便于管理和归档

## 解决方案

### 新的目录结构
每次回测生成一个独立目录，包含所有输出文件：
```
logs/backtest/
├── sma_cross/
│   ├── 20240306_143052_a1b2c3/
│   │   ├── trades.csv
│   │   ├── daily_values.csv
│   │   ├── summary.json
│   │   └── plot.png
│   └── 20240306_150123_d4e5f6/
│       └── ...
└── rsi_strategy/
    └── 20240305_091234_g7h8i9/
        └── ...
```

目录命名格式：`{strategy_name}/{timestamp}_{hash}`
- `strategy_name`: 策略名称（一级目录）
- `timestamp`: 运行时间 (YYYYMMDD_HHMMSS)
- `hash`: 短哈希值 (6位)，进一步避免冲突

### 文件命名简化

目录内文件名简化，不再包含日期范围：

* `trades.csv` - 交易记录

* `daily_values.csv` - 每日资产

* `summary.json` - 回测摘要（包含日期范围信息）

* `plot.png` - 可视化图表

## 实现步骤

### Step 1: 修改 BacktestConfig (config.py)

* 移除 `plot_output_dir`，统一使用 `output_dir`

* 保留 `trade_log_dir` 作为基础输出目录

### Step 2: 修改 BacktestResult (results.py)

* 添加 `generate_run_id()` 方法生成唯一运行ID

* 修改 `generate_log_filename()` 简化文件名

* 修改 `save_trades()`, `save_daily_values()`, `save_summary()` 使用新目录结构

* 添加 `run_id` 属性存储运行ID

### Step 3: 修改 BacktestRunner (runner.py)

* 在创建结果时生成运行ID

* 统一输出目录路径

* 修改图表保存逻辑

### Step 4: 更新 CLI (cli.py)

* 移除 `--plot-file` 相关逻辑（自动管理）

* 更新输出路径显示

### Step 5: 更新 README.md

* 更新目录结构说明

* 更新使用示例

## 代码变更

### generate\_run\_id 实现

```python
import hashlib
from datetime import datetime

def generate_run_id(self) -> str:
    """生成唯一运行ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 使用策略名+时间戳+参数生成短哈希
    content = f"{self.strategy_name}_{timestamp}_{self.params}"
    hash_val = hashlib.md5(content.encode()).hexdigest()[:6]
    return f"{self.strategy_name}_{timestamp}_{hash_val}"
```

### 新的目录路径生成

```python
def get_output_dir(self, base_dir: Path) -> Path:
    """获取本次回测的输出目录"""
    run_id = self.generate_run_id()
    return base_dir / run_id
```

## 兼容性

* 保持现有 API 不变

* `result.save()` 方法仍然可用

* 用户仍可通过 `--log-dir` 指定基础输出目录

