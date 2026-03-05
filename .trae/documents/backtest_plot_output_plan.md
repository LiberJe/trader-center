# 可视化图表输出到指定目录

## 目标
将回测可视化图表默认输出到当前工程的指定目录下，而不是需要手动指定路径或仅在屏幕显示。

## 当前问题
1. `enable_plot=True` 时默认只调用 `plt.show()` 显示图表，不保存文件
2. 需要手动指定 `--plot-file` 参数才能保存图表
3. 没有默认的图表输出目录配置
4. 图表文件命名不规范

## 解决方案

### 1. 扩展 BacktestConfig (config.py)
添加图表输出相关配置：
- `plot_output_dir`: 图表输出目录（默认 `logs/backtest/plots`）
- `auto_save_plot`: 是否自动保存图表（默认 True，当启用可视化时）

### 2. 修改 BacktestRunner (runner.py)
在 `_plot_result()` 方法中：
- 当 `enable_plot=True` 且未指定 `plot_file` 时，自动生成文件名并保存到配置目录
- 文件名格式：`{strategy_name}_{start_date}_{end_date}.png`

### 3. 更新 CLI (cli.py)
- 添加 `--auto-save-plot` / `--no-auto-save-plot` 参数控制

## 文件命名规范

图表文件命名格式：
```
{strategy_name}/{start_date}_{end_date}.png
```

示例目录结构：
```
c:\workspace\trader-center\
└── logs\
    └── backtest\
        ├── plots\
        │   ├── sma_cross\
        │   │   ├── 2024-01-01_2024-12-31.png
        │   │   └── 2024-01-01_2024-06-30.png
        │   └── rsi_strategy\
        │       └── 2024-06-01_2024-12-31.png
        ├── sma_cross\
        │   ├── 2024-01-01_2024-12-31_trades.csv
        │   └── ...
        └── ...
```

## 实现步骤

### Step 1: 更新配置类 (config.py)
- 添加 `plot_output_dir` 属性，默认 `Path.cwd() / "logs" / "backtest" / "plots"`
- 添加 `auto_save_plot` 属性，默认 True

### Step 2: 修改 BacktestRunner (runner.py)
- 在 `__init__` 中使用配置
- 在 `_plot_result()` 方法中实现自动保存逻辑
- 当 `enable_plot=True` 且 `plot_file` 为 None 时，自动生成路径并保存

### Step 3: 更新 CLI (cli.py)
- 添加 `--no-auto-save-plot` 参数

### Step 4: 更新模块导出 (__init__.py)
- 确保新配置可导出

## 兼容性
- 保持现有 API 不变
- 如果用户指定了 `--plot-file`，则使用用户指定的路径
- 新功能通过配置项控制
