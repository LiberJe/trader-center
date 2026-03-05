# 更新 backtest README.md

## 目标
更新 `trader_center/backtest/README.md` 文档，反映新增的交易日志和可视化图表自动输出功能。

## 需要更新的内容

### 1. 功能特性部分
添加新功能：
- **自动日志输出**: 交易日志自动保存到工程目录
- **可视化图表保存**: 回测图表自动保存到指定目录

### 2. 配置选项部分
更新 `BacktestConfig` 示例，添加新配置项：
- `trade_log_dir`: 交易日志输出目录
- `auto_save_trades`: 是否自动保存交易日志
- `trade_log_format`: 交易日志格式
- `plot_output_dir`: 图表输出目录
- `auto_save_plot`: 是否自动保存图表

### 3. CLI 参数部分
添加新的命令行参数：
- `--log-dir`: 交易日志输出目录
- `--no-auto-save`: 禁用自动保存交易日志
- `--log-format`: 交易日志格式
- `--plot`: 显示可视化图表
- `--plot-style`: 图表样式
- `--plot-file`: 保存图表到指定文件
- `--no-auto-save-plot`: 禁用自动保存图表

### 4. 新增输出目录结构说明
添加日志输出目录结构示例：
```
logs/
└── backtest/
    ├── plots/                    # 可视化图表
    │   └── {strategy_name}/
    │       └── {start}_{end}.png
    └── {strategy_name}/          # 交易日志
        ├── {start}_{end}_trades.csv
        ├── {start}_{end}_daily_values.csv
        └── {start}_{end}_summary.json
```

### 5. 更新命令行示例
更新 CLI 使用示例，展示新功能

## 实现步骤

### Step 1: 更新功能特性
在"功能特性"部分添加自动日志输出和图表保存功能

### Step 2: 更新配置选项
更新 `BacktestConfig` 示例代码

### Step 3: 更新 CLI 参数
添加所有新的命令行参数说明

### Step 4: 添加输出目录结构
新增"输出目录结构"章节

### Step 5: 更新命令行示例
更新示例命令展示新功能
