# 因子研究结果输出格式优化计划

## 问题分析

### 当前输出结构

```
factor_research_results/
  momentum/
    figures/
      momentum_5_distribution.png
      momentum_10_distribution.png
      ...
    reports/
      momentum_5_report_20260406_234628.html
      momentum_10_report_20260406_234629.html
      ...
```

### 问题

1. **多次运行结果混杂**：不同时间运行的结果混在同一目录下
2. **难以区分**：只能通过文件名中的时间戳区分，不直观
3. **清理困难**：无法快速删除某次运行的所有结果

### 目标输出结构

```
factor_research_results/
  momentum/
    20260407_222250/           # 运行时间戳
      figures/
        momentum_5_distribution.png
        momentum_10_distribution.png
        ...
      reports/
        momentum_5_report.html
        momentum_10_report.html
        ...
    20260407_234500/           # 另一次运行
      figures/
        ...
      reports/
        ...
```

### 优势

1. **结果隔离**：每次运行的结果存储在独立的时间戳目录中
2. **易于管理**：可以快速定位、删除或归档某次运行的结果
3. **结构清晰**：`figures/` 和 `reports/` 目录分离，便于查找

## 实施步骤

### 步骤 1：修改 FactorAnalysisPipeline 初始化

**文件**：`trader_center/factor/mining/pipeline.py`

**修改内容**：
1. 在 `__init__` 中添加 `run_timestamp` 参数
2. 自动创建带时间戳的子目录
3. 更新 `figures` 和 `reports` 目录路径

```python
def __init__(
    self,
    registry: FactorRegistry = None,
    preprocessing_config: Dict = None,
    analysis_config: Dict = None,
    output_dir: str = './factor_analysis_output',
    use_alphalens: bool = True,
    use_timestamp_subdir: bool = True,  # 新增参数
):
    """
    初始化因子分析流水线
    
    Args:
        ...
        use_timestamp_subdir: 是否使用时间戳子目录
    """
    ...
    
    self.output_dir = Path(output_dir)
    
    if use_timestamp_subdir:
        # 创建时间戳子目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.run_dir = self.output_dir / timestamp
    else:
        self.run_dir = self.output_dir
    
    self.run_dir.mkdir(parents=True, exist_ok=True)
    
    # 更新 figures 和 reports 目录
    self.visualizer = FactorVisualizer()
    self.reporter = FactorReport(str(self.run_dir / 'reports'))
```

### 步骤 2：更新图表保存路径

**文件**：`trader_center/factor/mining/pipeline.py`

**修改 `_generate_visualizations` 方法**：

```python
def _generate_visualizations(self, ...):
    ...
    figure_dir = self.run_dir / 'figures'  # 使用 run_dir 替代 output_dir
    ...
```

### 步骤 3：简化报告文件名

**文件**：`trader_center/factor/mining/report.py`

由于目录已包含时间戳，报告文件名可以简化：

```python
# 之前：momentum_5_report_20260406_234628.html
# 之后：momentum_5_report.html
```

### 步骤 4：更新 momentum.py 调用方式

**文件**：`factor_research/momentum.py`

无需修改，`FactorAnalysisPipeline` 会自动处理时间戳目录。

## 文件变更清单

| 文件 | 变更内容 |
|------|----------|
| `trader_center/factor/mining/pipeline.py` | 1. 添加 `use_timestamp_subdir` 参数<br>2. 创建 `run_dir` 属性<br>3. 更新 figures/reports 目录路径 |
| `trader_center/factor/mining/report.py` | 简化报告文件名（可选） |

## 向后兼容

- 添加 `use_timestamp_subdir` 参数，默认为 `True`
- 设置为 `False` 时使用原有输出格式
- 不影响现有代码的行为（除非显式设置）

## 使用示例

```python
# 使用时间戳子目录（默认）
pipeline = FactorAnalysisPipeline(
    output_dir='./factor_research_results/momentum',
)
# 输出：./factor_research_results/momentum/20260407_222250/

# 不使用时间戳子目录（兼容旧模式）
pipeline = FactorAnalysisPipeline(
    output_dir='./factor_research_results/momentum',
    use_timestamp_subdir=False,
)
# 输出：./factor_research_results/momentum/
```

## 测试计划

1. 验证时间戳目录正确创建
2. 验证 figures 和 reports 目录在时间戳目录下
3. 验证 `use_timestamp_subdir=False` 时使用原有格式
