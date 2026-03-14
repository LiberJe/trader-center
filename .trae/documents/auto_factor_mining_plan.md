# 自动因子挖掘实现计划

## 一、现状分析

### 当前框架已有的能力

| 模块 | 功能 | 状态 |
|-----|------|------|
| `factor/library/base.py` | 因子基类定义 | ✅ 已实现 |
| `factor/library/registry.py` | 因子注册管理 | ✅ 已实现 |
| `factor/mining/engine.py` | 因子计算引擎 | ✅ 已实现 |
| `factor/mining/ic_analysis.py` | IC分析 | ✅ 已实现 |
| `factor/mining/layering.py` | 分层回测 | ✅ 已实现 |
| `factor/mining/preprocessing/` | 因子预处理 | ✅ 已实现 |
| `factor/library/technical/` | 技术因子库 | ✅ 已实现 |

### 缺失的自动因子挖掘能力

| 功能 | 描述 | 优先级 |
|-----|------|--------|
| 遗传规划因子生成 | 使用GP自动生成新因子表达式 | 高 |
| 因子自动筛选流程 | 批量评估、筛选、排序因子 | 高 |
| 因子组合优化 | 多因子权重优化、正交化 | 中 |
| 因子评估报告生成 | 自动生成因子评估报告 | 中 |
| 因子存储和版本管理 | 持久化挖掘结果 | 低 |

---

## 二、实现方案

### 方案概述

采用**遗传规划（Genetic Programming）**方法自动挖掘因子，结合现有的IC分析和分层回测进行因子评估。

### 技术选型

- **gplearn**: Python遗传规划库，适合因子表达式挖掘
- **DEAP**: 灵活的进化计算框架（备选）

---

## 三、实现步骤

### Step 1: 创建因子表达式基元集

**文件**: `trader_center/factor/mining/gp/primitives.py`

定义因子计算的基础运算符和函数：
- 算术运算: `add`, `sub`, `mul`, `div`, `max`, `min`
- 时序函数: `ts_mean`, `ts_std`, `ts_max`, `ts_min`, `ts_rank`, `ts_delta`, `ts_decay`
- 技术指标: `rsi`, `macd`, `atr`, `momentum`
- 数据字段: `open`, `high`, `low`, `close`, `volume`, `vwap`

### Step 2: 实现遗传规划因子生成器

**文件**: `trader_center/factor/mining/gp/factor_generator.py`

核心类 `GPFactorGenerator`:
```python
class GPFactorGenerator:
    """基于遗传规划的因子生成器"""
    
    def __init__(self, 
                 population_size=1000,
                 generations=20,
                 tournament_size=20,
                 p_crossover=0.7,
                 p_mutation=0.1):
        ...
    
    def generate(self, data: pd.DataFrame, 
                 forward_returns: pd.Series,
                 n_factors: int = 10) -> List[FactorExpression]:
        """生成因子表达式"""
        ...
    
    def evaluate_factor(self, factor_expr, data, forward_returns) -> Dict:
        """评估单个因子"""
        ...
```

### Step 3: 实现因子表达式转换器

**文件**: `trader_center/factor/mining/gp/expression.py`

将GP生成的表达式树转换为可执行的因子类：
```python
class FactorExpression:
    """因子表达式"""
    
    def to_factor(self) -> BaseFactor:
        """转换为BaseFactor实例"""
        ...
    
    def to_code(self) -> str:
        """生成Python代码"""
        ...
    
    def to_latex(self) -> str:
        """生成LaTeX公式"""
        ...
```

### Step 4: 实现自动化因子筛选流程

**文件**: `trader_center/factor/mining/pipeline.py`

```python
class FactorMiningPipeline:
    """因子挖掘流水线"""
    
    def __init__(self, 
                 data_loader,
                 generator,
                 evaluator,
                 selector):
        ...
    
    def run(self, 
            start_date: str,
            end_date: str,
            universe: List[str]) -> MiningResult:
        """运行完整的因子挖掘流程"""
        # 1. 数据准备
        # 2. 因子生成
        # 3. 因子预处理
        # 4. IC分析
        # 5. 分层回测
        # 6. 因子筛选
        # 7. 结果输出
        ...
```

### Step 5: 实现因子评估器

**文件**: `trader_center/factor/mining/evaluator.py`

```python
class FactorEvaluator:
    """因子评估器"""
    
    def evaluate(self, 
                 factor_data: pd.DataFrame,
                 forward_returns: pd.DataFrame) -> FactorReport:
        """综合评估因子"""
        # IC分析
        # 分层回测
        # 相关性分析
        # 换手率分析
        # 单调性检验
        ...
    
    def rank_factors(self, factors: List, metric: str = 'icir') -> pd.DataFrame:
        """因子排名"""
        ...
```

### Step 6: 实现因子组合优化

**文件**: `trader_center/factor/mining/combination.py`

```python
class FactorCombiner:
    """因子组合优化器"""
    
    def orthogonalize(self, factors: pd.DataFrame) -> pd.DataFrame:
        """因子正交化（施密特正交化）"""
        ...
    
    def optimize_weights(self, 
                         factors: pd.DataFrame,
                         forward_returns: pd.Series,
                         method: str = 'icir') -> pd.Series:
        """优化因子权重"""
        ...
    
    def combine(self, 
                factors: pd.DataFrame,
                weights: pd.Series) -> pd.Series:
        """合成复合因子"""
        ...
```

### Step 7: 创建运行脚本和示例

**文件**: `backtest_runner/run_factor_mining.py`

提供完整的因子挖掘运行示例。

---

## 四、文件结构

```
trader_center/factor/mining/
├── __init__.py
├── engine.py              # 已有
├── ic_analysis.py         # 已有
├── layering.py            # 已有
├── correlation.py         # 已有
├── preprocessing/         # 已有
├── storage/               # 已有
├── gp/                    # 新增：遗传规划模块
│   ├── __init__.py
│   ├── primitives.py      # 基元函数集
│   ├── factor_generator.py # 因子生成器
│   └── expression.py      # 表达式处理
├── pipeline.py            # 新增：挖掘流水线
├── evaluator.py           # 新增：因子评估器
└── combination.py         # 新增：因子组合

backtest_runner/
└── run_factor_mining.py   # 新增：运行脚本
```

---

## 五、使用示例

```python
from trader_center.factor.mining.pipeline import FactorMiningPipeline
from trader_center.factor.mining.gp import GPFactorGenerator

# 创建因子生成器
generator = GPFactorGenerator(
    population_size=1000,
    generations=20,
    tournament_size=20
)

# 创建挖掘流水线
pipeline = FactorMiningPipeline(
    generator=generator,
    n_factors_to_generate=50,
    selection_criteria={
        'min_ic': 0.02,
        'min_icir': 0.5,
        'max_correlation': 0.7
    }
)

# 运行因子挖掘
result = pipeline.run(
    start_date='2020-01-01',
    end_date='2024-12-31',
    universe=['000001.SZ', '000002.SZ', ...]
)

# 查看挖掘结果
print(result.top_factors)
print(result.factor_report)

# 将挖掘的因子注册到因子库
result.register_factors()
```

---

## 六、依赖项

需要添加到 `requirements.txt`:
```
gplearn>=0.4.2
DEAP>=1.4.1  # 可选
```

---

## 七、任务清单

| 序号 | 任务 | 文件 | 优先级 |
|-----|------|------|--------|
| 1 | 创建GP基元函数集 | `gp/primitives.py` | 高 |
| 2 | 实现因子表达式类 | `gp/expression.py` | 高 |
| 3 | 实现GP因子生成器 | `gp/factor_generator.py` | 高 |
| 4 | 实现因子评估器 | `evaluator.py` | 高 |
| 5 | 实现因子挖掘流水线 | `pipeline.py` | 高 |
| 6 | 实现因子组合优化 | `combination.py` | 中 |
| 7 | 创建运行脚本 | `run_factor_mining.py` | 中 |
| 8 | 编写单元测试 | `tests/test_factor_mining.py` | 中 |
| 9 | 更新模块导出 | `__init__.py` | 低 |

---

## 八、预期成果

1. **自动化因子生成**: 通过遗传规划自动生成有效的因子表达式
2. **批量因子评估**: 自动计算IC、ICIR、分层收益等指标
3. **智能因子筛选**: 根据多维度指标筛选优质因子
4. **因子组合优化**: 生成低相关性的因子组合
5. **可复现的挖掘流程**: 完整的流水线支持参数化配置
