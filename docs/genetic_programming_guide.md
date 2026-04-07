# 遗传规划因子挖掘系统使用指南

## 概述

本系统实现了基于遗传规划（Genetic Programming）的自动因子挖掘功能，能够自动发现有效的量化因子。

## 核心组件

### 1. 基元集合 (PrimitiveSet)

定义因子表达式可用的操作符和数据字段。

**默认包含的操作符：**
- **算术运算**：add, sub, mul, div
- **数学函数**：abs, neg, sqrt, log, sign
- **横截面操作**：rank, zscore, scale
- **时间序列操作**：ts_mean, ts_std, ts_max, ts_min, ts_sum, ts_delay, ts_delta, ts_rank
- **相关性操作**：ts_corr, ts_cov
- **衰减加权**：decay_linear

**默认包含的数据字段：**
- open, high, low, close, volume, vwap
- returns, log_returns

### 2. 因子表达式 (FactorExpression)

表示一个因子公式，支持：
- 树形结构存储
- 表达式求值
- 序列化和反序列化

### 3. 适应度评估 (FitnessEvaluator)

评估因子优劣的指标：
- `ic_mean`: IC均值
- `icir`: ICIR
- `sharpe`: 因子夏普比率
- `combined`: 综合得分

### 4. 遗传操作 (GeneticOperators)

- **交叉**：交换两个个体的子树
- **变异**：
  - subtree: 子树变异
  - point: 点变异
  - hoist: 提升变异
  - shrink: 收缩变异
- **选择**：
  - tournament: 锦标赛选择
  - roulette: 轮盘赌选择
  - rank: 排名选择

### 5. 进化引擎 (GeneticProgrammingEngine)

主控制流程，管理整个进化过程。

## 快速开始

### 最简单的用法

```python
from trader_center.factor.mining import run_factor_mining

# 准备数据
price_df = ...  # 价格数据，index为日期，columns为资产代码
data_dict = {
    'close': close_prices,
    'volume': volumes,
    'returns': returns,
}

# 运行因子挖掘
factors = run_factor_mining(
    price_df=price_df,
    data_dict=data_dict,
    population_size=50,      # 种群大小
    n_generations=30,        # 进化代数
    max_depth=8,             # 最大深度
    fitness_metric='ic_mean', # 优化目标
    seed=42,                 # 随机种子
    verbose=1,               # 日志级别
)

# 查看最佳因子
for factor in factors[:5]:
    print(f"{factor}: fitness={factor.fitness:.4f}")
```

### 完整配置示例

```python
from trader_center.factor.mining import GeneticProgrammingEngine

engine = GeneticProgrammingEngine(
    price_df=price_df,
    data_dict=data_dict,
    
    # 种群配置
    population_size=100,      # 种群大小
    n_generations=50,         # 进化代数
    max_depth=10,             # 表达式最大深度
    init_depth=4,             # 初始深度
    
    # 适应度配置
    fitness_metric='icir',    # 优化目标
    
    # 遗传操作配置
    crossover_prob=0.8,       # 交叉概率
    mutation_prob=0.2,        # 变异概率
    elitism_size=5,           # 精英保留数量
    tournament_size=3,        # 锦标赛大小
    selection_method='tournament', # 选择方法
    
    # 其他配置
    seed=42,
    verbose=1,
    output_dir='./gp_results',
)

# 运行进化
factors = engine.run()

# 获取最佳因子
best_factors = engine.get_best_factors(top_n=10)

# 获取不重复的因子
unique_factors = engine.get_unique_factors(top_n=10)

# 查看进化历史
history_df = engine.get_evolution_history()
```

### 自定义基元

```python
from trader_center.factor.mining.genetic_programming import PrimitiveSet

# 创建自定义基元集合
pset = PrimitiveSet()

# 添加数据字段
pset.add_terminal('close', '收盘价')
pset.add_terminal('volume', '成交量')

# 添加自定义函数
def my_custom_func(x):
    """自定义均线差"""
    return x.rolling(10).mean() - x.rolling(20).mean()

pset.add_function('my_ma_diff', my_custom_func, 1, '自定义均线差')

# 使用自定义基元
engine = GeneticProgrammingEngine(
    price_df=price_df,
    data_dict=data_dict,
    pset=pset,
    ...
)
```

### 验证挖掘结果

```python
from trader_center.factor.mining import FactorAnalysisPipeline

# 获取最佳因子
best_factor = factors[0]

# 计算因子值
factor_values = best_factor.evaluate(data_dict)

# 使用因子评价流水线验证
pipeline = FactorAnalysisPipeline(use_alphalens=False)
result = pipeline.run(
    factor_name='gp_factor',
    factor_df=factor_values,
    price_df=price_df,
    preprocessing=True,
    scoring=True,
    visualize=True,
    generate_report=True,
)

print(f"IC均值: {result['summary']['ic_mean']:.4f}")
print(f"评级: {result['score']['grade']}")
```

## 参数调优建议

### 种群大小和进化代数

| 数据规模 | 种群大小 | 进化代数 | 预计时间 |
|---------|---------|---------|---------|
| 小（<50只股票） | 50-100 | 20-30 | 几分钟 |
| 中（50-200只股票） | 100-200 | 30-50 | 十几分钟 |
| 大（>200只股票） | 200-500 | 50-100 | 半小时以上 |

### 深度控制

- **max_depth**: 建议设置在6-10之间
  - 太小：表达式过于简单，可能无法捕捉复杂模式
  - 太大：容易过拟合，计算时间长

- **init_depth**: 建议设置在3-5之间
  - 影响初始种群的多样性

### 遗传操作参数

- **crossover_prob**: 0.7-0.9（推荐0.8）
- **mutation_prob**: 0.1-0.3（推荐0.2）
- **elitism_size**: 种群大小的5-10%
- **tournament_size**: 3-7（推荐3）

### 适应度指标选择

| 指标 | 适用场景 | 特点 |
|-----|---------|------|
| ic_mean | 通用 | 关注因子预测能力 |
| icir | 稳定性优先 | 关注因子稳定性 |
| sharpe | 收益优先 | 关注实际收益 |
| combined | 综合评估 | 平衡多个维度 |

## 最佳实践

### 1. 数据准备

```python
# 确保数据质量
data_dict = {
    'close': close_df.dropna(),      # 去除缺失值
    'volume': volume_df.dropna(),
    'returns': returns_df.dropna(),
}

# 数据对齐
common_dates = close_df.index
for key in data_dict:
    data_dict[key] = data_dict[key].reindex(common_dates)
```

### 2. 避免过拟合

- 使用样本外数据验证
- 限制表达式复杂度
- 多次运行取稳定结果

```python
# 多次运行
results = []
for seed in [42, 123, 456]:
    factors = run_factor_mining(
        price_df=price_df,
        data_dict=data_dict,
        seed=seed,
        ...
    )
    results.append(factors[0])

# 选择稳定出现的因子
```

### 3. 因子筛选

```python
# 获取不重复的因子
unique_factors = engine.get_unique_factors(top_n=20)

# 验证每个因子
validated = []
for factor in unique_factors:
    try:
        factor_values = factor.evaluate(data_dict)
        result = pipeline.run(
            factor_name=str(factor)[:20],
            factor_df=factor_values,
            price_df=price_df,
            scoring=True,
        )
        
        if result['score']['grade'] in ['A', 'B']:
            validated.append({
                'expression': str(factor),
                'fitness': factor.fitness,
                'grade': result['score']['grade'],
            })
    except:
        continue

# 排序
validated.sort(key=lambda x: x['fitness'], reverse=True)
```

### 4. 结果保存

```python
import json

# 保存最佳因子
best_factors = engine.get_best_factors(top_n=10)
factors_data = [
    {
        'expression': str(f),
        'fitness': f.fitness,
        'depth': f.depth(),
        'size': f.size(),
    }
    for f in best_factors
]

with open('best_factors.json', 'w') as f:
    json.dump(factors_data, f, indent=2)

# 保存进化历史
history_df = engine.get_evolution_history()
history_df.to_csv('evolution_history.csv')
```

## 常见问题

### Q1: 为什么因子适应度很低？

可能原因：
1. 数据质量问题（缺失值、异常值）
2. 数据量不足（建议至少1年数据）
3. 市场环境不适合该类型因子
4. 参数设置不当（尝试增加种群大小和进化代数）

### Q2: 如何提高挖掘效率？

1. 减少数据维度（选择代表性股票）
2. 降低种群大小和进化代数
3. 使用更简单的基元集合
4. 启用缓存（默认已启用）

### Q3: 如何解释挖掘到的因子？

1. 查看表达式字符串
2. 分析因子逻辑
3. 对照已知因子库
4. 使用因子评价报告

### Q4: 如何避免挖掘到已知因子？

1. 检查与现有因子的相关性
2. 使用独立性评分
3. 人工筛选和验证

## 示例项目结构

```
factor_research/
├── gp_quickstart.py           # 快速入门示例
├── genetic_programming_example.py  # 完整示例
├── custom_primitives.py       # 自定义基元示例
└── results/                   # 结果输出
    ├── generation_*.json      # 每代结果
    ├── final_results.json     # 最终结果
    └── evolution_history.csv  # 进化历史
```

## 进阶主题

### 多目标优化

```python
from trader_center.factor.mining.genetic_programming import MultiObjectiveFitness

# 同时优化多个目标
multi_fitness = MultiObjectiveFitness(
    price_df=price_df,
    objectives=['ic_mean', 'icir', 'sharpe'],
    weights=[0.4, 0.4, 0.2],
)

# 评估因子
scores = multi_fitness.evaluate(factor, data_dict)
weighted_score = multi_fitness.get_weighted_fitness(scores)
```

### 与机器学习结合

```python
# 使用遗传规划生成特征
from sklearn.ensemble import RandomForestClassifier

# 生成因子特征
factor_features = []
for factor in best_factors[:10]:
    factor_values = factor.evaluate(data_dict)
    factor_features.append(factor_values)

# 构建特征矩阵
X = pd.concat(factor_features, axis=1)

# 训练模型
model = RandomForestClassifier()
model.fit(X_train, y_train)
```

## 参考资料

- [遗传规划算法原理](https://en.wikipedia.org/wiki/Genetic_programming)
- [因子投资方法论](https://www.sciencedirect.com/science/article/pii/S0304405X16301456)
- [Alpha因子挖掘实践](https://arxiv.org/abs/1601.00991)
