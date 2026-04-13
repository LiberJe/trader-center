# 因子挖掘系统

基于 trader-center 架构的完整因子挖掘系统，提供因子计算、分析和预处理功能。

## 📁 模块结构

```
trader_center/
├── factor_library/             # 因子库模块
│   ├── base.py                 # 因子基类
│   ├── registry.py             # 因子注册器
│   ├── technical/              # 技术因子
│   │   ├── momentum.py         # 动量因子
│   │   ├── reversal.py         # 反转因子
│   │   ├── volatility.py       # 波动率因子
│   │   ├── volume.py           # 成交量因子
│   │   └── trend.py            # 趋势因子
│   ├── fundamental/            # 基本面因子
│   └── alternative/            # 另类因子
├── factor_mining/              # 因子挖掘模块
│   ├── engine.py               # 因子计算引擎
│   ├── preprocessing/          # 因子预处理
│   │   ├── standardization.py  # 标准化
│   │   ├── winsorization.py    # 去极值
│   │   └── neutralization.py   # 中性化
│   ├── analysis/               # 因子分析
│   │   ├── ic_analysis.py      # IC分析
│   │   ├── layering.py         # 分层回测
│   │   └── correlation.py      # 相关性分析
│   └── storage/                # 因子存储
│       └── factor_store.py     # 因子存储管理
```

## 🚀 快速开始

### 1. 基础因子使用

```python
from trader_center.factor_library.technical.momentum import MomentumFactor, RSIFactor
import pandas as pd

# 创建数据
data = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})

# 使用动量因子
momentum = MomentumFactor(period=20)
momentum_values = momentum.compute(data)

# 使用RSI因子
rsi = RSIFactor(period=14)
rsi_values = rsi.compute(data)
```

### 2. 因子注册器

```python
from trader_center.factor_library import FactorRegistry, register_factor

# 创建注册器
registry = FactorRegistry()

# 注册因子
registry.register(MomentumFactor(period=20))
registry.register(RSIFactor(period=14))

# 获取因子
factor = registry.get('momentum')

# 列出所有因子
factors = registry.list_factors()
```

### 3. 因子计算引擎

```python
from trader_center.factor_mining import FactorEngine

# 创建引擎
engine = FactorEngine(registry=registry)

# 计算单个因子
momentum = engine.compute_factor('momentum', data)

# 批量计算因子
factors_df = engine.compute_factors(
    ['momentum', 'rsi', 'atr'],
    data,
    parallel=True
)
```

### 4. 因子预处理

```python
from trader_center.factor_mining.preprocessing.standardization import ZScoreStandardizer
from trader_center.factor_mining.preprocessing.winsorization import MADWinsorizer

# 标准化
standardizer = ZScoreStandardizer()
standardized = standardizer.fit_transform(factor_values)

# 去极值
winsorizer = MADWinsorizer(threshold=3.0)
winsorized = winsorizer.fit_transform(factor_values)
```

### 5. 因子分析

```python
from trader_center.factor_mining.analysis.ic_analysis import ICAnalyzer
from trader_center.factor_mining.analysis.layering import LayeringAnalyzer

# IC分析
ic_analyzer = ICAnalyzer()
ic_result = ic_analyzer.compute(factor_data, forward_returns)
print(f"IC均值: {ic_result['ic_mean']}")
print(f"ICIR: {ic_result['icir']}")

# 分层回测
layering_analyzer = LayeringAnalyzer(n_groups=5)
layering_result = layering_analyzer.compute(factor_data, forward_returns)
print(f"多空收益: {layering_result['long_short_mean']}")
```

## 📊 已实现的因子

### 技术因子

#### 动量因子
- **MomentumFactor**: 价格动量因子（N日收益率）
- **RSIFactor**: 相对强弱指标因子
- **MACDFactor**: MACD因子
- **PriceRateOfChangeFactor**: 价格变化率因子
- **MomentumQualityFactor**: 动量质量因子
- **VolumeAdjustedMomentumFactor**: 成交量调整动量因子

#### 反转因子
- **RSIReversalFactor**: RSI反转因子
- **BollingerReversalFactor**: 布林带反转因子
- **KDJReversalFactor**: KDJ反转因子
- **WilliamsReversalFactor**: 威廉指标反转因子
- **CCIFactor**: 顺势指标因子

#### 波动率因子
- **ATRFactor**: 平均真实波幅因子
- **HistoricalVolatilityFactor**: 历史波动率因子
- **ParkinsonVolatilityFactor**: Parkinson波动率因子
- **GarmanKlassVolatilityFactor**: Garman-Klass波动率因子
- **VolatilityRatioFactor**: 波动率比率因子
- **TrueRangeFactor**: 真实波幅因子
- **VolatilityRegimeFactor**: 波动率状态因子

#### 成交量因子
- **VolumeRatioFactor**: 量比因子
- **OBVFactor**: 能量潮因子
- **VolumePriceTrendFactor**: 量价趋势因子
- **MoneyFlowIndexFactor**: 资金流量指标因子
- **AccumulationDistributionFactor**: 累积/派发线因子
- **VolumeOscillatorFactor**: 成交量震荡因子
- **VolumeWeightedPriceFactor**: 成交量加权价格因子
- **VolumeTrendFactor**: 成交量趋势因子
- **VolumeSpikeFactor**: 成交量异常因子

#### 趋势因子
- **MAFactor**: 移动平均线因子
- **EMAFactor**: 指数移动平均线因子
- **MACDTrendFactor**: MACD趋势因子
- **ADXFactor**: 平均趋向指标因子
- **TrendStrengthFactor**: 趋势强度因子
- **GoldenCrossFactor**: 金叉死叉因子
- **TrendDirectionFactor**: 趋势方向因子
- **PricePositionFactor**: 价格位置因子
- **SupertrendFactor**: 超级趋势因子

### 基本面因子

#### 估值因子
| 因子名称 | 描述 | 方向 | 学术出处 |
|----------|------|------|----------|
| **PEFactor** | 市盈率因子（股价/每股收益） | negative | Fama & French (1992) |
| **PBFactor** | 市净率因子（股价/每股净资产） | negative | Fama & French (1992) |
| **PSFactor** | 市销率因子（股价/每股销售额） | negative | Lakonishok et al. (1994) |
| **EVEBITDAFactor** | 企业价值倍数因子（EV/EBITDA） | negative | Damodaran (2006) |
| **PEGFactor** | PEG因子（PE/盈利增长率） | negative | Peter Lynch |
| **PCFFactor** | 股价现金流比因子 | negative | Sloan (1996) |

#### 质量因子
| 因子名称 | 描述 | 方向 | 学术出处 |
|----------|------|------|----------|
| **ROEFactor** | 净资产收益率因子（净利润/净资产） | positive | Novy-Marx (2013) |
| **ROAFactor** | 总资产收益率因子（净利润/总资产） | positive | Novy-Marx (2013) |
| **GrossMarginFactor** | 毛利率因子 | positive | Novy-Marx (2013) |
| **NetMarginFactor** | 净利率因子 | positive | Novy-Marx (2013) |
| **AssetTurnoverFactor** | 资产周转率因子 | positive | Soliman (2008) |
| **GrossProfitabilityFactor** | 毛利润率因子（最强质量因子） | positive | Novy-Marx (2013) |

#### 成长因子
| 因子名称 | 描述 | 方向 | 学术出处 |
|----------|------|------|----------|
| **RevenueGrowthFactor** | 营收增长率因子 | positive | Lakonishok et al. (1994) |
| **EarningsGrowthFactor** | 净利润增长率因子 | positive | Chan et al. (2003) |
| **EPSGrowthFactor** | EPS增长率因子 | positive | Chan et al. (2003) |
| **AssetGrowthFactor** | 资产增长率因子（负向因子） | negative | Cooper et al. (2008) |
| **OCFGrowthFactor** | 经营现金流增长率因子 | positive | Sloan (1996) |

#### 财务健康因子
| 因子名称 | 描述 | 方向 | 学术出处 |
|----------|------|------|----------|
| **DebtRatioFactor** | 资产负债率因子 | negative | Altman (1968) |
| **CurrentRatioFactor** | 流动比率因子 | positive | Altman (1968) |
| **QuickRatioFactor** | 速动比率因子 | positive | Altman (1968) |
| **InterestCoverageFactor** | 利息保障倍数因子 | positive | Ohlson (1980) |
| **AltmanZScoreFactor** | Altman Z-Score破产预警因子 | positive | Altman (1968) |
| **CashRatioFactor** | 现金比率因子 | positive | Ohlson (1980) |

#### 现金流因子
| 因子名称 | 描述 | 方向 | 学术出处 |
|----------|------|------|----------|
| **FCFYieldFactor** | 自由现金流收益率因子 | positive | Sloan (1996) |
| **OCFToNetIncomeFactor** | 经营现金流/净利润因子（盈利质量） | positive | Sloan (1996) |
| **CashConversionCycleFactor** | 现金循环周期因子 | negative | Richards & Laughlin (1980) |
| **CapExRatioFactor** | 资本支出比率因子 | negative | Titman et al. (2004) |

#### 分红因子
| 因子名称 | 描述 | 方向 | 学术出处 |
|----------|------|------|----------|
| **DividendYieldFactor** | 股息率因子 | positive | Litzenberger & Ramaswamy (1979) |
| **PayoutRatioFactor** | 分红率因子 | moderate | Fama & French (2001) |
| **DividendGrowthFactor** | 股息增长率因子 | positive | Grullon et al. (2002) |

## 🔧 自定义因子

创建自定义因子非常简单：

```python
from trader_center.factor_library.base import BaseFactor
import pandas as pd

class CustomFactor(BaseFactor):
    """自定义因子"""
    
    name = "custom_factor"
    category = "technical"
    description = "我的自定义因子"
    
    def __init__(self, period: int = 20):
        super().__init__(period=period)
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # 实现因子计算逻辑
        return data['close'].rolling(self.params['period']).mean()

# 注册自定义因子
from trader_center.factor_library import register_factor
register_factor(CustomFactor(period=20))
```

## 📈 因子预处理

### 标准化方法

1. **Z-score标准化**: 转换为标准正态分布
2. **Min-Max标准化**: 缩放到指定范围
3. **排名标准化**: 转换为排名百分比
4. **鲁棒标准化**: 基于中位数和四分位距

### 去极值方法

1. **MAD去极值**: 中位数绝对偏差方法
2. **分位数去极值**: 基于分位数截断
3. **标准差去极值**: 基于均值±N倍标准差
4. **IQR去极值**: 基于四分位距

### 中性化方法

1. **行业中性化**: 消除行业差异
2. **市场中性化**: 消除市场影响
3. **规模中性化**: 消除市值影响
4. **多因子中性化**: 同时对多个风险因子中性化

## 📊 因子分析

### IC分析

- IC均值、IC标准差、ICIR
- IC时间序列分析
- IC衰减分析
- IC显著性检验

### 分层回测

- 按因子值分组（5组/10组）
- 各组收益统计
- 多空组合收益
- 单调性检验
- 换手率分析

### 相关性分析

- 因子间相关性矩阵
- 因子自相关性
- 因子与收益相关性
- 高相关性因子对识别

## 💾 因子存储

```python
from trader_center.factor_mining.storage import FactorStore

# 创建存储
store = FactorStore()

# 保存因子数据
store.save('momentum', '000001.SZ', factor_data)

# 批量保存
store.save_batch('momentum', factor_df)

# 加载因子数据
data = store.load('momentum', ['000001.SZ', '000002.SZ'])
```

## 🧪 测试

运行测试：

```bash
python tests/test_factor_system.py
```

运行示例：

```bash
python examples/factor_system_example.py
```

## 📝 开发指南

### 因子开发规范

1. 继承 `BaseFactor` 基类
2. 设置 `name`、`category`、`description` 属性
3. 实现 `compute` 方法
4. 添加参数验证 `_validate_params`
5. 编写单元测试

### 代码风格

- 遵循 PEP 8 规范
- 使用类型注解
- 添加文档字符串
- 编写清晰的注释

## 📚 参考资料

- [因子投资方法](https://www.factorinvesting.org/)
- [量化投资策略](https://www.quantopian.com/)
- [技术分析指标](https://www.investopedia.com/)

## 🤝 贡献

欢迎贡献新的因子和功能改进！

## 📄 许可证

MIT License
