# 多因子轮动策略实施计划

## 1. 项目背景

基于当前因子库，创建一个多因子轮动策略示例，演示如何使用因子库进行资产配置和轮动。

## 2. 当前代码库分析

### 2.1 因子库结构
- **位置**: `trader_center/factor/library/`
- **基类**: `BaseFactor` - 所有因子的抽象基类
- **注册器**: `FactorRegistry` - 单例模式管理因子
- **引擎**: `FactorEngine` - 因子计算、缓存、批量处理

### 2.2 可用因子
| 类别 | 因子名称 | 描述 |
|------|----------|------|
| 动量 | `momentum` | 价格动量因子（N日收益率） |
| 动量 | `rsi` | 相对强弱指标因子 |
| 动量 | `macd` | MACD因子 |
| 趋势 | `trend_strength` | 趋势强度因子 |
| 趋势 | `adx` | 平均趋向指标因子 |
| 波动率 | `historical_volatility` | 历史波动率因子 |
| 波动率 | `atr` | 平均真实波幅因子 |

### 2.3 策略框架
- **基类**: `BaseStrategy` (继承自 `bt.Strategy`)
- **运行器**: `BacktestRunner`
- **示例策略**: `EqualWeightAssetAllocation` (大类资产等权持有)

### 2.4 资产池
```python
ASSET_CONFIG = {
    '518880.SH': {'name': '黄金ETF', 'category': 'commodity'},
    '510300.SH': {'name': '沪深300ETF', 'category': 'equity_cn'},
    '513100.SH': {'name': '纳指ETF', 'category': 'equity_us'},
    '511010.SH': {'name': '国债ETF', 'category': 'bond'},
    '159981.SZ': {'name': '能源化工ETF', 'category': 'commodity'},
}
```

## 3. 策略设计

### 3.1 策略名称
`MultiFactorRotationStrategy` - 多因子轮动策略

### 3.2 策略逻辑
1. **因子选择**: 选择多个因子（动量、趋势、波动率）
2. **因子打分**: 对每个资产计算因子值，标准化后加权合成综合得分
3. **排名选股**: 根据综合得分排名，选择得分最高的N个资产
4. **权重分配**: 按排名分配权重（等权或按得分加权）
5. **定期调仓**: 按固定频率进行再平衡

### 3.3 因子配置
| 因子 | 权重 | 方向 | 说明 |
|------|------|------|------|
| `momentum` (20日) | 30% | 正向 | 动量因子，高动量得分高 |
| `trend_strength` (20日) | 25% | 正向 | 趋势强度，强趋势得分高 |
| `rsi` (14日) | 15% | 反向 | RSI因子，超卖得分高 |
| `historical_volatility` (20日) | 15% | 反向 | 波动率因子，低波动得分高 |
| `atr` (14日) | 15% | 反向 | ATR因子，低波动得分高 |

### 3.4 策略参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `rebalance_freq` | 20 | 再平衡频率（交易日） |
| `top_n` | 3 | 持仓资产数量 |
| `factor_weights` | 见上表 | 因子权重字典 |
| `min_score` | 0.3 | 最低得分阈值，低于此值不持有 |

## 4. 实施步骤

### 步骤 1: 创建因子打分器类
**文件**: `trader_center/backtest/strategy/factor_scorer.py`

创建 `FactorScorer` 类，负责：
- 管理多个因子
- 计算因子值
- 标准化因子值（Z-score）
- 加权合成综合得分

```python
class FactorScorer:
    """多因子打分器"""
    
    def __init__(self, factor_configs: Dict[str, Dict]):
        """
        Args:
            factor_configs: 因子配置字典
                {
                    'momentum': {'weight': 0.3, 'direction': 'positive'},
                    'rsi': {'weight': 0.15, 'direction': 'negative'},
                }
        """
        
    def compute_scores(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """计算所有资产的综合得分"""
        
    def _standardize(self, values: pd.Series) -> pd.Series:
        """Z-score标准化"""
        
    def _apply_direction(self, values: pd.Series, direction: str) -> pd.Series:
        """应用因子方向"""
```

### 步骤 2: 创建多因子轮动策略类
**文件**: `trader_center/backtest/strategy/multi_factor_rotation.py`

创建 `MultiFactorRotationStrategy` 类：

```python
class MultiFactorRotationStrategy(BaseStrategy):
    """多因子轮动策略"""
    
    name = "multi_factor_rotation"
    description = "基于多因子打分的资产轮动策略"
    
    params = (
        ('rebalance_freq', 20),
        ('top_n', 3),
        ('factor_configs', DEFAULT_FACTOR_CONFIGS),
        ('min_score', 0.3),
    )
    
    def __init__(self):
        super().__init__()
        self.scorer = FactorScorer(self.p.factor_configs)
        self.data_cache = {}  # 缓存历史数据
        
    def nextstart(self):
        """初始建仓"""
        
    def next(self):
        """每日执行"""
        
    def _should_rebalance(self) -> bool:
        """判断是否需要再平衡"""
        
    def _compute_scores(self) -> Dict[str, float]:
        """计算所有资产的因子得分"""
        
    def _select_assets(self, scores: Dict[str, float]) -> List[str]:
        """选择得分最高的N个资产"""
        
    def _rebalance(self, selected_assets: List[str], scores: Dict[str, float]):
        """执行再平衡"""
```

### 步骤 3: 创建策略运行脚本
**文件**: `backtest_runner/run_multi_factor_rotation.py`

创建运行脚本，演示如何使用多因子轮动策略：

```python
def main():
    # 配置因子
    factor_configs = {
        'momentum': {'weight': 0.30, 'direction': 'positive', 'params': {'period': 20}},
        'trend_strength': {'weight': 0.25, 'direction': 'positive', 'params': {'period': 20}},
        'rsi': {'weight': 0.15, 'direction': 'negative', 'params': {'period': 14}},
        'historical_volatility': {'weight': 0.15, 'direction': 'negative', 'params': {'period': 20}},
        'atr': {'weight': 0.15, 'direction': 'negative', 'params': {'period': 14}},
    }
    
    # 运行回测
    result = runner.run(
        strategy=MultiFactorRotationStrategy,
        symbols=symbols,
        start="2020-01-01",
        end="2024-12-31",
        strategy_params={
            'rebalance_freq': 20,
            'top_n': 3,
            'factor_configs': factor_configs,
            'min_score': 0.3,
        }
    )
```

### 步骤 4: 更新策略模块导出
**文件**: `trader_center/backtest/strategy/__init__.py`

添加新策略的导出。

## 5. 文件清单

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `trader_center/backtest/strategy/factor_scorer.py` | 新建 | 因子打分器 |
| `trader_center/backtest/strategy/multi_factor_rotation.py` | 新建 | 多因子轮动策略 |
| `backtest_runner/run_multi_factor_rotation.py` | 新建 | 运行脚本 |
| `trader_center/backtest/strategy/__init__.py` | 修改 | 添加导出 |

## 6. 关键设计决策

### 6.1 数据缓存机制
由于 backtrader 的数据访问方式是逐 bar 的，需要在策略中缓存历史数据用于因子计算：
- 使用 `data_cache` 字典缓存每个资产的 DataFrame
- 每次调用 `next()` 时更新缓存

### 6.2 因子计算时机
- 在每个再平衡日计算因子
- 使用过去 N 天的数据计算因子值
- 避免未来函数（look-ahead bias）

### 6.3 标准化方法
- 使用 Z-score 标准化（横截面）
- 对每个因子，在所有资产间进行标准化
- 处理 NaN 值（填充为 0 或排除）

### 6.4 权重分配
- 等权分配：选中的资产平均分配权重
- 可选：按得分加权分配

## 7. 预期效果

### 7.1 策略特点
- **因子驱动**: 基于多个因子综合评分进行资产选择
- **动态轮动**: 根据因子得分动态调整持仓
- **风险分散**: 持有多只资产，降低单一资产风险
- **可扩展**: 易于添加新因子或调整因子权重

### 7.2 示例输出
```
================================================================================
多因子轮动策略回测
================================================================================

因子配置:
  momentum (20日): 权重 30%, 方向 正向
  trend_strength (20日): 权重 25%, 方向 正向
  rsi (14日): 权重 15%, 方向 反向
  historical_volatility (20日): 权重 15%, 方向 反向
  atr (14日): 权重 15%, 方向 反向

资产池:
  黄金ETF (518880.SH)
  沪深300ETF (510300.SH)
  纳指ETF (513100.SH)
  国债ETF (511010.SH)
  能源化工ETF (159981.SZ)

回测参数:
  初始资金: 1,000,000 元
  回测区间: 2020-01-01 ~ 2024-12-31
  再平衡频率: 20个交易日
  持仓数量: 3

================================================================================
回测结果
================================================================================

策略名称: multi_factor_rotation
回测区间: 2020-01-01 ~ 2024-12-31

收益指标:
  初始资金: 1,000,000.00 元
  最终资产: 1,xxx,xxx.xx 元
  总收益:   +xxx,xxx.xx 元
  收益率:   +xx.xx%

风险指标:
  最大回撤: xx.xx%
  夏普比率: x.xx
  卡玛比率: x.xx

交易统计:
  总交易次数: xx
  胜率:       xx.x%
  盈亏比:     x.xx
```

## 8. 后续优化方向

1. **因子优化**: 添加更多因子类型（基本面、另类数据）
2. **动态权重**: 根据因子 IC 动态调整因子权重
3. **风险控制**: 添加波动率目标、最大回撤控制
4. **择时模块**: 添加市场择时，在不利市场环境下降低仓位
5. **因子正交化**: 消除因子间的相关性
