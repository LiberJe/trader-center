# ETF-Sharp 策略实现计划

## 1. 策略概述

### 1.1 策略思想

基于多因子综合评分的ETF轮动策略，核心因子包括：

* **夏普比率因子**：衡量风险调整后的收益，核心选股因子

* **波动率因子**：衡量资产风险水平，低波动率得分更高

* **动量因子**：捕捉价格趋势，正向动量得分更高

* **最大回撤因子**：衡量历史最大亏损，低回撤得分更高

### 1.2 策略特点

* **多因子综合评分**：四个因子加权合成综合得分

* **风险调整收益导向**：夏普比率为核心，平衡收益与风险

* **动态轮动**：定期根据因子得分变化调整持仓

* **风险控制**：波动率和最大回撤因子提供风险约束

## 2. 因子体系

### 2.1 因子列表

| 因子名称 | 因子类                          | 方向 | 说明            | 状态     |
| ---- | ---------------------------- | -- | ------------- | ------ |
| 夏普比率 | `SharpeRatioFactor`          | 正向 | 滚动夏普比率，风险调整收益 | **新增** |
| 波动率  | `HistoricalVolatilityFactor` | 反向 | 历史波动率，低波动更优   | 已有     |
| 动量   | `MomentumFactor`             | 正向 | N日收益率，捕捉趋势    | 已有     |
| 最大回撤 | `MaxDrawdownFactor`          | 反向 | 滚动最大回撤，低回撤更优  | **新增** |

### 2.2 夏普比率因子（新增）

**文件**: `trader_center/factor/library/technical/sharpe.py`

```python
class SharpeRatioFactor(BaseFactor):
    """
    滚动夏普比率因子
    
    计算N日滚动夏普比率，用于衡量风险调整后的收益。
    
    公式: Sharpe = (年化收益率 - 无风险利率) / 年化波动率
    
    Params:
        period: 计算周期，默认60个交易日
        risk_free_rate: 无风险利率（年化），默认0.03
        annualization_factor: 年化因子，默认252（交易日）
    """
    
    name = "sharpe_ratio"
    category = "technical"
    description = "滚动夏普比率因子"
```

**计算逻辑**：

1. 计算period日收益率序列
2. 计算年化收益率 = mean(returns) \* 252
3. 计算年化波动率 = std(returns) \* sqrt(252)
4. 夏普比率 = (年化收益率 - 无风险利率) / 年化波动率

### 2.3 最大回撤因子（新增）

**文件**: `trader_center/factor/library/technical/drawdown.py`

```python
class MaxDrawdownFactor(BaseFactor):
    """
    滚动最大回撤因子
    
    计算N日滚动窗口内的最大回撤，用于衡量历史风险。
    
    公式: MaxDD = max((peak - price) / peak)
    
    Params:
        period: 计算周期，默认60个交易日
    """
    
    name = "max_drawdown"
    category = "technical"
    description = "滚动最大回撤因子"
```

**计算逻辑**：

1. 在period日窗口内计算累计最高点
2. 计算每个时点的回撤 = (peak - close) / peak
3. 取窗口内最大回撤值

### 2.4 已有因子

**波动率因子** (`HistoricalVolatilityFactor`)：

* 位置：`trader_center/factor/library/technical/volatility.py`

* 方向：反向（低波动率得分更高）

* 参数：period=20, annualize=True

**动量因子** (`MomentumFactor`)：

* 位置：`trader_center/factor/library/technical/momentum.py`

* 方向：正向（高动量得分更高）

* 参数：period=20

## 3. 因子归一化处理

### 3.1 归一化流程

```
原始因子值 → 极端值处理 → 横截面标准化 → 方向调整 → 加权合成
```

### 3.2 归一化步骤详解

#### Step 1: 极端值处理 (Winsorize)

**目的**：去除极端值对因子得分的干扰

**方法**：分位数截断

```python
def winsorize(values, lower=0.025, upper=0.975):
    """
    极端值处理
    
    将低于 lower 分位数的值设为 lower 分位数值
    将高于 upper 分位数的值设为 upper 分位数值
    
    Args:
        values: 因子值序列
        lower: 下分位数，默认2.5%
        upper: 上分位数，默认97.5%
    """
    lower_bound = np.quantile(values, lower)
    upper_bound = np.quantile(values, upper)
    return np.clip(values, lower_bound, upper_bound)
```

#### Step 2: 横截面标准化 (Z-score)

**目的**：消除不同因子量纲差异，使因子可比

**方法**：Z-score 标准化

```python
def zscore_standardize(values):
    """
    横截面 Z-score 标准化
    
    公式: z = (x - mean) / std
    
    将因子值转换为均值为0、标准差为1的分布
    """
    mean = np.mean(values)
    std = np.std(values)
    if std == 0 or np.isnan(std):
        return np.zeros_like(values)
    return (values - mean) / std
```

#### Step 3: 方向调整

**目的**：统一因子方向，正向因子保持不变，反向因子取负

```python
def adjust_direction(zscore_values, direction):
    """
    方向调整
    
    Args:
        zscore_values: 标准化后的因子值
        direction: 'positive' 或 'negative'
    
    Returns:
        调整方向后的因子值
    """
    if direction == 'negative':
        return -zscore_values
    return zscore_values
```

#### Step 4: 加权合成

**目的**：将多个因子加权合成为综合得分

```python
def aggregate_scores(factor_scores, weights):
    """
    加权合成综合得分
    
    Args:
        factor_scores: {factor_name: adjusted_value}
        weights: {factor_name: weight}
    
    Returns:
        综合得分
    """
    score = 0.0
    for factor_name, value in factor_scores.items():
        score += weights[factor_name] * value
    return score
```

### 3.3 归一化参数配置

```python
NORMALIZATION_CONFIG = {
    'winsorize': {
        'enabled': True,
        'lower': 0.025,  # 下2.5%分位数
        'upper': 0.975,  # 上97.5%分位数
    },
    'standardize': {
        'method': 'zscore',  # 可选: 'zscore', 'minmax', 'rank'
    },
}
```

### 3.4 可选归一化方法

| 方法             | 公式                | 特点        | 适用场景   |
| -------------- | ----------------- | --------- | ------ |
| Z-score        | (x-μ)/σ           | 均值0，标准差1  | 正态分布数据 |
| Min-Max        | (x-min)/(max-min) | 映射到\[0,1] | 有界数据   |
| Rank           | rank(x)/n         | 排名百分位     | 非正态分布  |
| Robust Z-score | (x-median)/MAD    | 抗极端值      | 有极端值数据 |

### 3.5 归一化实现位置

归一化处理将在 `FactorScorer` 类中实现：

```python
class FactorScorer:
    """
    多因子打分器
    
    支持多种归一化方法：
    - winsorize: 极端值处理
    - zscore: Z-score标准化
    - minmax: Min-Max归一化
    - rank: 排名归一化
    """
    
    def __init__(
        self,
        factor_configs: Dict[str, Dict],
        normalization_config: Optional[Dict] = None,
    ):
        self.factor_configs = factor_configs
        self.normalization_config = normalization_config or NORMALIZATION_CONFIG
        
    def _winsorize_values(self, values: np.ndarray) -> np.ndarray:
        """极端值处理"""
        ...
    
    def _standardize_values(self, values: np.ndarray) -> np.ndarray:
        """标准化处理"""
        method = self.normalization_config['standardize']['method']
        if method == 'zscore':
            return self._zscore_standardize(values)
        elif method == 'minmax':
            return self._minmax_standardize(values)
        elif method == 'rank':
            return self._rank_standardize(values)
        ...
```

## 4. 策略实现

### 4.1 新增文件

| 文件路径                                                 | 说明             |
| ---------------------------------------------------- | -------------- |
| `trader_center/factor/library/technical/sharpe.py`   | 夏普比率因子实现       |
| `trader_center/factor/library/technical/drawdown.py` | 最大回撤因子实现       |
| `trader_center/backtest/strategy/etf_sharp.py`       | ETF-Sharp策略主文件 |
| `backtest_runner/run_etf_sharp.py`                   | 策略运行脚本         |

### 4.2 ETF-Sharp策略实现

**文件**: `trader_center/backtest/strategy/etf_sharp.py`

```python
class ETFSharpStrategy(BaseStrategy):
    """
    ETF夏普比率轮动策略
    
    基于四因子综合评分进行ETF资产选择和轮动：
    1. 计算每个ETF的四个因子值
    2. 极端值处理 (Winsorize)
    3. 横截面标准化 (Z-score)
    4. 方向调整
    5. 加权合成综合得分
    6. 选择得分最高的N个ETF
    7. 定期再平衡
    
    因子配置:
    - sharpe_ratio: 权重 0.40, 方向 positive
    - momentum: 权重 0.25, 方向 positive
    - historical_volatility: 权重 0.20, 方向 negative
    - max_drawdown: 权重 0.15, 方向 negative
    
    Params:
        rebalance_freq: 再平衡频率（交易日），默认20天
        top_n: 持仓ETF数量，默认3
        lookback: 因子计算窗口，默认60天
        factor_configs: 因子配置字典
        normalization_config: 归一化配置
        min_score: 最低综合得分阈值
        weighting_method: 权重分配方法，'equal'或'score_weighted'
        exec_type: 订单执行类型，'open'或'close'
    """
```

### 4.3 策略核心逻辑

```
初始化阶段:
├── 设置参数和因子配置
├── 设置归一化配置
├── 初始化因子打分器 (FactorScorer)
├── 初始化数据缓存
└── 预热数据

每日执行:
├── 更新数据缓存
├── 检查是否需要再平衡
│   └── 达到再平衡频率
├── 计算所有ETF的四个因子值
│   ├── 夏普比率因子
│   ├── 动量因子
│   ├── 波动率因子
│   └── 最大回撤因子
├── 因子归一化处理
│   ├── Step 1: 极端值处理 (Winsorize 2.5%-97.5%)
│   ├── Step 2: 横截面标准化 (Z-score)
│   ├── Step 3: 方向调整 (正向保持, 反向取负)
│   └── Step 4: 加权合成综合得分
├── 选择得分最高的top_n个ETF
├── 根据weighting_method分配权重
│   ├── equal: 等权分配
│   └── score_weighted: 按得分加权
└── 执行调仓
```

### 4.4 因子权重配置

默认因子权重配置：

```python
ETF_SHARP_FACTOR_CONFIGS = {
    'sharpe_ratio': {
        'weight': 0.40,
        'direction': 'positive',
        'params': {'period': 60, 'risk_free_rate': 0.03},
    },
    'momentum': {
        'weight': 0.25,
        'direction': 'positive',
        'params': {'period': 20},
    },
    'historical_volatility': {
        'weight': 0.20,
        'direction': 'negative',
        'params': {'period': 20, 'annualize': True},
    },
    'max_drawdown': {
        'weight': 0.15,
        'direction': 'negative',
        'params': {'period': 60},
    },
}
```

**权重设计理由**：

* **夏普比率 (40%)**：核心因子，直接衡量风险调整收益

* **动量 (25%)**：捕捉趋势，辅助判断方向

* **波动率 (20%)**：风险约束，惩罚高波动资产

* **最大回撤 (15%)**：尾部风险约束，惩罚高回撤资产

### 4.5 权重分配方法

**等权分配 (equal)**：

* 每个选中的ETF分配相同权重

* 简单直观，易于实现

**得分加权 (score\_weighted)**：

* 根据综合得分大小分配权重

* 得分越高，权重越大

* 公式：weight\_i = max(score\_i, 0) / sum(max(score\_j, 0) for j in selected)

## 5. 实现步骤

### Step 1: 创建夏普比率因子

* [ ] 创建 `trader_center/factor/library/technical/sharpe.py`

* [ ] 实现 `SharpeRatioFactor` 类

* [ ] 添加必要的参数验证

### Step 2: 创建最大回撤因子

* [ ] 创建 `trader_center/factor/library/technical/drawdown.py`

* [ ] 实现 `MaxDrawdownFactor` 类

* [ ] 添加必要的参数验证

### Step 3: 增强FactorScorer归一化功能

* [ ] 在 `factor_scorer.py` 中添加极端值处理 (Winsorize)

* [ ] 添加多种标准化方法支持 (Z-score, Min-Max, Rank)

* [ ] 添加归一化配置参数

### Step 4: 创建ETF-Sharp策略

* [ ] 创建 `trader_center/backtest/strategy/etf_sharp.py`

* [ ] 实现 `ETFSharpStrategy` 类

* [ ] 继承 `BaseStrategy`

* [ ] 实现数据缓存和因子计算

* [ ] 实现归一化处理

* [ ] 实现综合得分计算

* [ ] 实现资产选择和权重分配

* [ ] 实现再平衡逻辑

### Step 5: 创建运行脚本

* [ ] 创建 `backtest_runner/run_etf_sharp.py`

* [ ] 配置回测参数

* [ ] 配置ETF资产池

* [ ] 添加结果输出和可视化

### Step 6: 更新模块导出

* [ ] 更新 `trader_center/factor/library/technical/__init__.py`

* [ ] 更新 `trader_center/backtest/strategy/__init__.py`

### Step 7: 测试验证

* [ ] 运行回测验证策略正确性

* [ ] 检查日志输出

* [ ] 验证绩效指标

## 6. ETF资产池配置

使用现有的 `ASSET_CONFIG`，包含：

* `518880.SH`: 黄金ETF (商品)

* `510300.SH`: 沪深300ETF (A股)

* `513100.SH`: 纳指ETF (美股)

* `511010.SH`: 国债ETF (债券)

* `159981.SZ`: 能源化工ETF (商品)

## 7. 回测参数建议

| 参数     | 建议值                      | 说明        |
| ------ | ------------------------ | --------- |
| 初始资金   | 1,000,000                | 100万      |
| 回测区间 | 2020-01-01 ~ 2024-12-31 | 5年 |       |
| 再平衡频率  | 20个交易日                   | 约每月一次     |
| 持仓数量   | 3                        | 选择得分最高的3个 |
| 因子计算窗口 | 60天                      | 约3个月      |
| 无风险利率  | 3%                       | 年化        |
| 权重方法   | equal                    | 等权分配      |
| 订单执行   | close                    | 次日收盘价     |
| 极端值处理  | 2.5%-97.5%               | Winsorize |
| 标准化方法  | Z-score                  | 横截面标准化    |

## 8. 预期效果

基于四因子轮动策略的预期特点：

* **收益稳定性**：多因子综合评分，避免单一因子偏差

* **风险控制**：波动率和最大回撤因子提供双重风险约束

* **趋势捕捉**：动量因子捕捉市场趋势

* **夏普比率优化**：以夏普比率为核心，预期策略夏普比率较高

* **极端值鲁棒性**：Winsorize处理提高策略对极端值的鲁棒性

## 9. 扩展方向

1. **因子权重优化**：根据历史IC动态调整因子权重
2. **因子正交化**：消除因子间相关性，提高信息比率
3. **动态阈值**：根据市场环境调整最低得分阈值
4. **波动率目标**：设定目标波动率，动态调整仓位
5. **市场择时**：结合大盘择时信号，在熊市降低仓位
6. **自适应归一化**：根据因子分布特征自动选择归一化方法

## 10. 文件依赖关系

```
etf_sharp.py
├── base.py (BaseStrategy)
├── asset_allocation.py (ASSET_CONFIG)
├── factor_scorer.py (FactorScorer) [增强归一化功能]
└── factor/library/technical/
    ├── sharpe.py (SharpeRatioFactor) [新增]
    ├── drawdown.py (MaxDrawdownFactor) [新增]
    ├── volatility.py (HistoricalVolatilityFactor)
    └── momentum.py (MomentumFactor)

run_etf_sharp.py
├── BacktestRunner
├── BacktestConfig
├── ETFSharpStrategy
└── ASSET_CONFIG
```

## 11. 与现有策略的对比

| 特性    | ETF-Sharp策略 | 多因子轮动策略   |
| ----- | ----------- | --------- |
| 核心因子  | 夏普比率        | 动量        |
| 因子数量  | 4个          | 5个        |
| 风险因子  | 波动率 + 最大回撤  | 波动率 + ATR |
| 反转因子  | 无           | RSI       |
| 极端值处理 | Winsorize   | 无         |
| 标准化方法 | Z-score     | Z-score   |
| 适用场景  | 风险调整收益优化    | 趋势跟踪      |

