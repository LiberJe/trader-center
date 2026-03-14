# 因子评价报告生成计划

## 一、现状分析

### 已有的评价能力

| 模块 | 功能 | 状态 |
|-----|------|------|
| `FactorMetrics` | 因子指标数据类 | ✅ 已实现 |
| `FactorReport` | 因子评估报告数据结构 | ✅ 已实现 |
| `summary()` | 文本摘要生成 | ✅ 已实现 |
| `plot_ic_series()` | IC时间序列图 | ✅ 已实现（仅显示） |
| `plot_layering_results()` | 分层回测图 | ✅ 已实现（仅显示） |
| `plot_correlation_matrix()` | 相关性热力图 | ✅ 已实现（仅显示） |
| `to_dataframe()` | 导出DataFrame | ✅ 已实现 |

### 缺失的评价能力

| 功能 | 描述 | 优先级 |
|-----|------|--------|
| 专业因子分析库集成 | 接入alphalens-reloaded | 高 |
| 完整评价报告生成 | HTML/PDF格式报告 | 高 |
| 图表保存功能 | 保存图表到文件 | 高 |
| 评价报告模板 | 标准化的报告模板 | 高 |

---

## 二、实现方案

### 方案概述

**接入 alphalens-reloaded 库**，这是一个专业的因子分析库，提供：

| 分析类型 | 内容 |
|---------|------|
| Returns Analysis | 收益分析（分组收益、多空收益、累积收益） |
| Information Coefficient Analysis | IC分析（IC时间序列、IC分布、IC衰减） |
| Turnover Analysis | 换手率分析 |
| Grouped Analysis | 分组分析（按行业/板块） |

### alphalens-reloaded 核心功能

```python
import alphalens

# 数据准备
factor_data = alphalens.utils.get_clean_factor_and_forward_returns(
    factor,           # 因子值
    pricing,          # 价格数据
    quantiles=5,      # 分组数量
    groupby=sector,   # 行业分组
)

# 生成完整报告
alphalens.tears.create_full_tear_sheet(factor_data)
```

### 技术选型

- **alphalens-reloaded** - 专业因子分析库（核心）
- **Jinja2** - HTML模板引擎（报告生成）
- **Matplotlib** - 图表生成（alphalens依赖）

---

## 三、实现步骤

### Step 1: 创建Alphalens适配器

**文件**: `trader_center/factor/mining/report/alphalens_adapter.py`

```python
class AlphalensAdapter:
    """Alphalens适配器 - 将框架数据转换为alphalens格式"""
    
    def __init__(self):
        self._check_availability()
    
    def _check_availability(self) -> bool:
        """检查alphalens是否可用"""
        
    def prepare_factor_data(
        self,
        factor_values: pd.DataFrame,  # index=日期, columns=股票代码
        prices: pd.DataFrame,         # index=日期, columns=股票代码
        quantiles: int = 5,
        periods: Tuple[int, ...] = (1, 5, 10, 20),
        groupby: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """准备alphalens格式的因子数据"""
        
    def create_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        long_short: bool = True,
        group_neutral: bool = False,
        by_group: bool = False,
    ) -> None:
        """创建完整的因子分析报告"""
        
    def create_returns_tear_sheet(
        self,
        factor_data: pd.DataFrame,
    ) -> None:
        """创建收益分析报告"""
        
    def create_information_tear_sheet(
        self,
        factor_data: pd.DataFrame,
    ) -> None:
        """创建IC分析报告"""
        
    def create_turnover_tear_sheet(
        self,
        factor_data: pd.DataFrame,
    ) -> None:
        """创建换手率分析报告"""
        
    def create_event_study_tear_sheet(
        self,
        factor_data: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> None:
        """创建事件研究报告"""
```

### Step 2: 创建报告生成器

**文件**: `trader_center/factor/mining/report/generator.py`

```python
class FactorReportGenerator:
    """因子评价报告生成器"""
    
    def __init__(self, output_dir: str = './reports'):
        self.output_dir = output_dir
        self.alphalens = AlphalensAdapter()
    
    def analyze_with_alphalens(
        self,
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
        quantiles: int = 5,
        periods: Tuple[int, ...] = (1, 5, 10, 20),
    ) -> Dict[str, Any]:
        """使用alphalens进行因子分析"""
        
    def generate_full_report(
        self,
        factor_values: pd.DataFrame,
        prices: pd.DataFrame,
        title: str = "因子评价报告",
        save_charts: bool = True,
    ) -> str:
        """生成完整报告（包含所有图表）"""
        
    def save_tear_sheet_to_html(
        self,
        factor_data: pd.DataFrame,
        filename: str = "factor_report.html",
    ) -> str:
        """保存tear sheet到HTML文件"""
```

### Step 3: 创建数据转换工具

**文件**: `trader_center/factor/mining/report/data_converter.py`

```python
class DataConverter:
    """数据格式转换器"""
    
    @staticmethod
    def factor_expression_to_panel(
        expressions: List[FactorExpression],
        data_dict: Dict[str, pd.DataFrame],
    ) -> Dict[str, pd.DataFrame]:
        """将因子表达式转换为面板数据"""
        
    @staticmethod
    def mining_result_to_alphalens_format(
        result: MiningResult,
        data_dict: Dict[str, pd.DataFrame],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """将挖掘结果转换为alphalens格式"""
        
    @staticmethod
    def get_pricing_data(
        data_dict: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """提取价格数据"""
```

### Step 4: 更新运行脚本

**文件**: `backtest_runner/run_factor_mining.py`

```python
from trader_center.factor.mining.report import FactorReportGenerator

# 因子挖掘完成后
generator = FactorReportGenerator(output_dir='./reports')

# 使用alphalens进行专业分析
factor_values = convert_to_panel(result.selected_factors, data_dict)
prices = extract_prices(data_dict)

# 生成完整报告
report_path = generator.generate_full_report(
    factor_values,
    prices,
    title="因子挖掘评价报告"
)
print(f"报告已生成: {report_path}")
```

---

## 四、文件结构

```
trader_center/factor/mining/report/
├── __init__.py
├── generator.py           # 报告生成器
├── alphalens_adapter.py   # Alphalens适配器
├── data_converter.py      # 数据转换工具
└── templates/             # HTML模板目录
    └── report.html
```

---

## 五、使用示例

### 示例1: 基础使用

```python
from trader_center.factor.mining import FactorMiningPipeline, MiningConfig
from trader_center.factor.mining.report import FactorReportGenerator

# 运行因子挖掘
pipeline = FactorMiningPipeline(config=MiningConfig())
result = pipeline.run(data, forward_returns)

# 生成评价报告
generator = FactorReportGenerator(output_dir='./reports')
report_path = generator.generate_full_report(
    factor_values,
    prices,
    title="因子挖掘评价报告"
)
```

### 示例2: 直接使用Alphalens

```python
from trader_center.factor.mining.report import AlphalensAdapter

adapter = AlphalensAdapter()

# 准备数据
factor_data = adapter.prepare_factor_data(
    factor_values=factor_df,
    prices=price_df,
    quantiles=5,
    periods=(1, 5, 10, 20),
)

# 生成完整报告
adapter.create_tear_sheet(factor_data)

# 或分别生成各类报告
adapter.create_returns_tear_sheet(factor_data)
adapter.create_information_tear_sheet(factor_data)
adapter.create_turnover_tear_sheet(factor_data)
```

### 示例3: 批量分析多个因子

```python
# 批量分析
for factor_name, factor_values in factors_dict.items():
    factor_data = adapter.prepare_factor_data(
        factor_values,
        prices,
        quantiles=5,
    )
    
    print(f"\n=== {factor_name} ===")
    adapter.create_tear_sheet(factor_data)
```

---

## 六、Alphalens报告内容

### 1. Returns Analysis（收益分析）
- 分组平均收益
- 分组累积收益
- 多空收益曲线
- 最佳/最差组收益对比

### 2. Information Coefficient Analysis（IC分析）
- IC时间序列
- IC分布直方图
- IC衰减曲线
- IC热力图（按时间）

### 3. Turnover Analysis（换手率分析）
- 各组换手率
- 因子自相关性
- 换手率与收益关系

### 4. Grouped Analysis（分组分析）
- 按行业/板块分组
- 各组因子表现对比

---

## 七、任务清单

| 序号 | 任务 | 文件 | 优先级 |
|-----|------|------|--------|
| 1 | 创建Alphalens适配器 | `report/alphalens_adapter.py` | 高 |
| 2 | 创建数据转换工具 | `report/data_converter.py` | 高 |
| 3 | 实现报告生成器 | `report/generator.py` | 高 |
| 4 | 更新运行脚本 | `run_factor_mining.py` | 中 |
| 5 | 更新模块导出 | `report/__init__.py` | 低 |

---

## 八、依赖项

需要添加到 `requirements.txt`:
```
alphalens-reloaded>=0.4.0
```

安装命令：
```bash
pip install alphalens-reloaded
```

---

## 九、预期成果

1. **专业因子分析**: 使用alphalens进行标准化因子评价
2. **完整Tear Sheet**: 包含收益、IC、换手率等完整分析
3. **可视化图表**: 自动生成十多张专业分析图表
4. **HTML报告**: 可保存为HTML格式报告文件
