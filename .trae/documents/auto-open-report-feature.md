# 增加自动打开绩效报告功能

## 需求

在存在 QuantStats 分析的情况下，回测完成后自动打开浏览器展示绩效分析报告。

## 实现步骤

### Step 1: 扩展 BacktestConfig

**文件**: `trader_center/backtest/config.py`

新增配置项：
```python
auto_open_report: bool = False  # 回测完成后自动打开浏览器展示报告
```

同时更新 `to_dict()` 方法。

### Step 2: 更新 BacktestRunner

**文件**: `trader_center/backtest/runner.py`

在报告生成成功后，检查 `auto_open_report` 配置，使用 Python 标准库 `webbrowser` 打开报告：

```python
if report_path and self.config.auto_open_report:
    import webbrowser
    webbrowser.open(f'file://{Path(report_path).absolute()}')
    self.logger.info(f"已在浏览器中打开绩效报告")
```

### Step 3: 更新 CLI

**文件**: `trader_center/backtest/cli.py`

新增参数：
```
--open-report      回测完成后自动打开浏览器展示绩效报告
```

### Step 4: 更新 README

**文件**: `trader_center/backtest/README.md`

- 在配置选项中添加 `auto_open_report` 说明
- 在 CLI 参数中添加 `--open-report` 说明

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `config.py` | 新增 `auto_open_report` 配置项 |
| `runner.py` | 报告生成后调用 `webbrowser.open()` |
| `cli.py` | 新增 `--open-report` 参数 |
| `README.md` | 更新文档 |

## 使用示例

**Python API:**
```python
from trader_center.backtest import BacktestRunner, BacktestConfig

config = BacktestConfig(
    enable_quantstats=True,
    auto_save_report=True,
    auto_open_report=True,  # 新增配置
)

runner = BacktestRunner(config=config)
result = runner.run(...)  # 完成后自动打开浏览器
```

**CLI:**
```bash
python -m trader_center.backtest \
    -s my_strategy \
    -sym 000001.SZ \
    --open-report
```
