# 因子挖掘系统开发计划

## 项目概述

基于现有 trader-center 架构，开发一套完整的因子挖掘系统，为回测系统提供因子计算、分析和选择功能。

## 架构设计

### 模块结构
```
trader_center/
├── factor_library/             # 因子库模块
│   ├── __init__.py
│   ├── base.py                 # 因子基类
│   ├── registry.py             # 因子注册器
│   ├── technical/              # 技术因子
│   │   ├── __init__.py
│   │   ├── momentum.py         # 动量因子
│   │   ├── reversal.py         # 反转因子
│   │   ├── volatility.py       # 波动率因子
│   │   ├── volume.py           # 成交量因子
│   │   └── trend.py            # 趋势因子
│   ├── fundamental/            # 基本面因子
│   │   ├── __init__.py
│   │   ├── valuation.py        # 估值因子
│   │   ├── growth.py           # 成长因子
│   │   ├── profitability.py    # 盈利能力因子
│   │   └── quality.py          # 质量因子
│   └── alternative/            # 另类因子
│       ├── __init__.py
│       ├── fund_flow.py        # 资金流因子
│       ├── sentiment.py        # 情绪因子
│       └── market_structure.py # 市场结构因子
├── factor_mining/              # 因子挖掘模块
│   ├── __init__.py
│   ├── engine.py               # 因子计算引擎
│   ├── preprocessing/          # 因子预处理
│   │   ├── __init__.py
│   │   ├── standardization.py  # 标准化
│   │   ├── winsorization.py    # 去极值
│   │   └── neutralization.py   # 中性化
│   ├── analysis/               # 因子分析
│   │   ├── __init__.py
│   │   ├── ic_analysis.py      # IC分析
│   │   ├── layering.py         # 分层回测
│   │   └── correlation.py      # 相关性分析
│   └── storage/                # 因子存储
│       ├── __init__.py
│       └── factor_store.py     # 因子存储管理
```

### 数据流设计
```
DataHub (原始数据)
    ↓
FactorLibrary (因子定义)
    ↓
FactorMining (因子计算引擎)
    ↓
FactorStore (因子存储)
    ↓
Backtest Strategy (策略使用)
```

## 实施步骤

### Phase 1: 基础框架搭建

#### 步骤 1.1: 创建因子库模块基础结构
- 创建 `trader_center/factor_library/` 目录结构
- 创建所有必要的 `__init__.py` 文件
- 设置模块导入关系

#### 步骤 1.2: 实现因子基类 (factor_library/base.py)
- 定义 `BaseFactor` 抽象基类
- 包含属性: name, category, description, params
- 定义抽象方法: `compute(data: pd.DataFrame) -> pd.Series`
- 实现辅助方法: `validate()`, `get_params()`, `set_params()`
- 添加因子元数据管理

#### 步骤 1.3: 实现因子注册器 (factor_library/registry.py)
- 实现 `FactorRegistry` 单例类
- 提供因子注册功能: `register(factor: BaseFactor)`
- 提供因子获取功能: `get(name: str) -> BaseFactor`
- 提供因子列表功能: `list_factors(category: str = None) -> List[str]`
- 支持因子自动发现和注册

#### 步骤 1.4: 创建因子挖掘模块基础结构
- 创建 `trader_center/factor_mining/` 目录结构
- 创建所有必要的 `__init__.py` 文件
- 设置模块导入关系

#### 步骤 1.5: 实现因子计算引擎 (factor_mining/engine.py)
- 实现 `FactorEngine` 类
- 支持单因子计算: `compute_factor(factor_name, data)`
- 支持多因子批量计算: `compute_factors(factor_names, data)`
- 支持并行计算优化
- 实现计算结果缓存机制

#### 步骤 1.6: 实现因子存储 (factor_mining/storage/factor_store.py)
- 实现 `FactorStore` 类
- 支持因子数据保存: `save(factor_name, data, date)`
- 支持因子数据加载: `load(factor_name, symbols, start, end)`
- 支持因子元数据管理
- 集成现有 DataHub 存储机制

### Phase 2: 核心技术因子实现

#### 步骤 2.1: 实现动量因子 (factor_library/technical/momentum.py)
- **MomentumFactor**: 价格动量因子 (N日收益率)
- **RSIFactor**: 相对强弱指标因子
- **MACDFactor**: MACD因子 (包含MACD、Signal、Histogram)
- **PriceRateOfChangeFactor**: 价格变化率因子

#### 步骤 2.2: 实现反转因子 (factor_library/technical/reversal.py)
- **RSIReversalFactor**: RSI反转因子 (超买超卖)
- **BollingerReversalFactor**: 布林带反转因子
- **KDJReversalFactor**: KDJ反转因子

#### 步骤 2.3: 实现波动率因子 (factor_library/technical/volatility.py)
- **ATRFactor**: 平均真实波幅因子
- **HistoricalVolatilityFactor**: 历史波动率因子
- **ParkinsonVolatilityFactor**: Parkinson波动率因子

#### 步骤 2.4: 实现成交量因子 (factor_library/technical/volume.py)
- **VolumeRatioFactor**: 量比因子
- **OBVFactor**: 能量潮因子
- **VolumePriceTrendFactor**: 量价趋势因子
- **MoneyFlowIndexFactor**: 资金流量指标因子

#### 步骤 2.5: 实现趋势因子 (factor_library/technical/trend.py)
- **MAFactor**: 移动平均线因子
- **EMAFactor**: 指数移动平均线因子
- **MACDTrendFactor**: MACD趋势因子
- **ADXFactor**: 平均趋向指标因子

### Phase 3: 因子预处理功能

#### 步骤 3.1: 实现标准化 (factor_mining/preprocessing/standardization.py)
- **ZScoreStandardizer**: Z-score标准化
- **MinMaxStandardizer**: Min-Max标准化
- **RankStandardizer**: 排名标准化

#### 步骤 3.2: 实现去极值 (factor_mining/preprocessing/winsorization.py)
- **MADWinsorizer**: 中位数绝对偏差去极值
- **PercentileWinsorizer**: 分位数去极值
- **SigmaWinsorizer**: 标准差去极值

#### 步骤 3.3: 实现中性化 (factor_mining/preprocessing/neutralization.py)
- **IndustryNeutralizer**: 行业中性化
- **MarketNeutralizer**: 市场中性化
- **SizeNeutralizer**: 规模中性化

### Phase 4: 因子分析功能

#### 步骤 4.1: 实现IC分析 (factor_mining/analysis/ic_analysis.py)
- **ICAnalyzer**: IC分析器
  - 计算Rank IC
  - 计算Normal IC
  - IC均值、IC标准差、ICIR
  - IC时间序列分析
  - IC衰减分析

#### 步骤 4.2: 实现分层回测 (factor_mining/analysis/layering.py)
- **LayeringAnalyzer**: 分层回测分析器
  - 按因子值分组 (5组/10组)
  - 计算各组收益
  - 多空组合收益
  - 分组换手率
  - 分层收益可视化

#### 步骤 4.3: 实现相关性分析 (factor_mining/analysis/correlation.py)
- **CorrelationAnalyzer**: 相关性分析器
  - 因子间相关性矩阵
  - 因子自相关性
  - 因子与收益相关性

### Phase 5: 另类因子实现

#### 步骤 5.1: 实现资金流因子 (factor_library/alternative/fund_flow.py)
- **MainForceNetFlowFactor**: 主力净流入因子
- **LargeOrderNetFlowFactor**: 大单净流入因子
- **SuperLargeOrderFactor**: 超大单因子
- **SmallOrderFactor**: 小单因子

#### 步骤 5.2: 实现情绪因子 (factor_library/alternative/sentiment.py)
- **TurnoverRateFactor**: 换手率因子
- **AmplitudeFactor**: 振幅因子
- **UpLimitCountFactor**: 涨停板数量因子

#### 步骤 5.3: 实现市场结构因子 (factor_library/alternative/market_structure.py)
- **IndustryMomentumFactor**: 行业动量因子
- **SectorRotationFactor**: 板块轮动因子
- **MarketBreadthFactor**: 市场广度因子

### Phase 6: 基本面因子实现 (可选)

#### 步骤 6.1: 实现估值因子 (factor_library/fundamental/valuation.py)
- **PEFactor**: 市盈率因子
- **PBFactor**: 市净率因子
- **PSFactor**: 市销率因子
- **EVToEBITDAFactor**: EV/EBITDA因子

#### 步骤 6.2: 实现成长因子 (factor_library/fundamental/growth.py)
- **RevenueGrowthFactor**: 营收增长率因子
- **ProfitGrowthFactor**: 净利润增长率因子
- **EPSGrowthFactor**: EPS增长率因子

#### 步骤 6.3: 实现盈利能力因子 (factor_library/fundamental/profitability.py)
- **ROEFactor**: 净资产收益率因子
- **ROAFactor**: 总资产收益率因子
- **GrossMarginFactor**: 毛利率因子
- **NetMarginFactor**: 净利率因子

#### 步骤 6.4: 实现质量因子 (factor_library/fundamental/quality.py)
- **DebtRatioFactor**: 资产负债率因子
- **CurrentRatioFactor**: 流动比率因子
- **CashFlowFactor**: 现金流因子

### Phase 7: 集成与测试

#### 步骤 7.1: 集成到回测系统
- 修改 `BaseStrategy` 支持因子调用
- 创建 `FactorStrategy` 示例策略
- 在 `run_asset_allocation.py` 中添加因子使用示例

#### 步骤 7.2: 编写单元测试
- 创建 `tests/factor_library/` 和 `tests/factor_mining/` 测试目录
- 为每个因子编写测试用例
- 测试因子计算正确性
- 测试因子预处理功能
- 测试因子分析功能

#### 步骤 7.3: 编写集成测试
- 测试因子与DataHub集成
- 测试因子与Backtest集成
- 测试因子存储功能

#### 步骤 7.4: 性能优化
- 实现因子计算并行化
- 优化内存使用
- 实现增量计算

#### 步骤 7.5: 编写文档
- 编写因子系统使用文档
- 编写因子开发指南
- 编写API文档

## 技术细节

### 因子基类设计
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

class BaseFactor(ABC):
    """因子基类"""
    
    def __init__(self, **params):
        self.params = params
        self._validate_params()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """因子名称"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """因子类别"""
        pass
    
    @property
    def description(self) -> str:
        """因子描述"""
        return ""
    
    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        计算因子值
        
        Args:
            data: 包含OHLCV的DataFrame
        
        Returns:
            因子值Series，index为日期
        """
        pass
    
    def _validate_params(self):
        """验证参数"""
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """验证输入数据"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required_cols)
```

### 因子引擎设计
```python
from typing import List, Dict
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from trader_center.factor_library import FactorRegistry

class FactorEngine:
    """因子计算引擎"""
    
    def __init__(self, registry: FactorRegistry, cache_size: int = 100):
        self.registry = registry
        self._cache = {}
        self._cache_size = cache_size
    
    def compute_factor(
        self, 
        factor_name: str, 
        data: pd.DataFrame,
        use_cache: bool = True
    ) -> pd.Series:
        """计算单个因子"""
        factor = self.registry.get(factor_name)
        
        cache_key = self._get_cache_key(factor_name, data)
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        result = factor.compute(data)
        
        if use_cache:
            self._cache[cache_key] = result
        
        return result
    
    def compute_factors(
        self,
        factor_names: List[str],
        data: pd.DataFrame,
        parallel: bool = True
    ) -> pd.DataFrame:
        """批量计算因子"""
        if parallel:
            with ThreadPoolExecutor() as executor:
                results = list(executor.map(
                    lambda name: self.compute_factor(name, data),
                    factor_names
                ))
        else:
            results = [self.compute_factor(name, data) for name in factor_names]
        
        return pd.DataFrame({name: result for name, result in zip(factor_names, results)})
```

### 因子存储设计
```python
from datetime import date
from typing import List, Optional
import pandas as pd
from trader_center.data_hub.storage import HybridStore

class FactorStore:
    """因子存储"""
    
    def __init__(self, storage: HybridStore):
        self.storage = storage
    
    def save(
        self,
        factor_name: str,
        factor_data: pd.Series,
        date: Optional[date] = None
    ):
        """保存因子数据"""
        df = factor_data.to_frame(name='value')
        df['factor_name'] = factor_name
        if date:
            df['date'] = date
        
        self.storage.save(df, table_name=f'factor_{factor_name}')
    
    def load(
        self,
        factor_name: str,
        symbols: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.Series:
        """加载因子数据"""
        df = self.storage.load(
            table_name=f'factor_{factor_name}',
            start_date=start_date,
            end_date=end_date
        )
        
        if symbols:
            df = df[df['symbol'].isin(symbols)]
        
        return df.set_index(['symbol', 'date'])['value']
```

## 架构说明

### 模块职责划分

#### factor_library (因子库)
- **职责**: 存放所有因子定义和因子注册器
- **内容**: 
  - 因子基类 (base.py)
  - 因子注册器 (registry.py)
  - 各类因子实现 (technical/, fundamental/, alternative/)
- **特点**: 纯因子定义，不包含计算逻辑

#### factor_mining (因子挖掘)
- **职责**: 提供因子计算、分析、预处理等工具
- **内容**:
  - 因子计算引擎 (engine.py)
  - 因子预处理 (preprocessing/)
  - 因子分析 (analysis/)
  - 因子存储 (storage/)
- **特点**: 因子工具集，依赖 factor_library

## 测试计划

### 单元测试
- 每个因子类至少3个测试用例
- 测试正常输入、边界条件、异常输入
- 测试因子计算结果的正确性
- 测试因子参数验证

### 集成测试
- 测试因子与DataHub的数据交互
- 测试因子在回测中的使用
- 测试因子存储和加载
- 测试因子分析功能

### 性能测试
- 单因子计算性能
- 多因子并行计算性能
- 因子存储性能
- 内存使用情况

## 集成方案

### 与DataHub集成
```python
# 在 DataHub 中添加因子数据获取方法
class DataHub:
    def get_factor_data(
        self,
        factor_name: str,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取因子数据"""
        pass
```

### 与Backtest集成
```python
# 在 BaseStrategy 中添加因子支持
class BaseStrategy(bt.Strategy):
    def get_factor(self, factor_name: str, data: bt.DataBase) -> float:
        """获取因子值"""
        pass
    
    def get_factor_series(self, factor_name: str, data: bt.DataBase) -> pd.Series:
        """获取因子序列"""
        pass
```

## 预期成果

1. **完整的因子库**: 包含技术、基本面、另类因子共50+个
2. **因子分析工具**: IC分析、分层回测、相关性分析
3. **因子预处理**: 标准化、去极值、中性化
4. **因子存储**: 支持因子数据的持久化存储
5. **文档完善**: 使用文档、开发指南、API文档
6. **测试覆盖**: 单元测试覆盖率>80%

## 风险与挑战

1. **性能问题**: 大量因子计算可能影响性能
   - 解决方案: 并行计算、缓存机制、增量计算

2. **数据依赖**: 部分因子需要额外数据源
   - 解决方案: 分阶段实现，优先实现基于现有数据的因子

3. **因子有效性**: 因子可能随时间失效
   - 解决方案: 因子监控、定期评估、动态调整

4. **存储空间**: 因子数据可能占用大量存储
   - 解决方案: 数据压缩、定期清理、按需加载

## 时间估算

- Phase 1 (基础框架): 2-3天
- Phase 2 (技术因子): 3-4天
- Phase 3 (预处理): 2天
- Phase 4 (分析工具): 3天
- Phase 5 (另类因子): 2天
- Phase 6 (基本面因子): 3天 (可选)
- Phase 7 (集成测试): 2-3天

**总计**: 约15-20天
