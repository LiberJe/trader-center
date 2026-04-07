# 因子库与 FactorAnalysisPipeline 集成优化方案

## 问题分析

### 当前架构

1. **BaseFactor** - 因子基类
   - `compute(data: pd.DataFrame)` - 处理单只股票数据
   - 期望数据格式：长表格式，包含 `close`、`open`、`high`、`low`、`volume` 等列

2. **FactorEngine** - 因子计算引擎
   - `compute_for_symbols(factor_name, data_dict)` - 为多个股票计算因子
   - 输入：`data_dict: {symbol: DataFrame}` 格式
   - 输出：宽表格式 DataFrame（index=日期，columns=股票代码）

3. **FactorAnalysisPipeline** - 因子分析流水线
   - `run(factor_df, price_df)` - 接收已计算好的因子值
   - 期望数据格式：宽表格式（index=日期，columns=资产代码）

### 核心问题

1. **数据格式断层**：
   - `momentum.py` 中的 `price_df` 是宽表格式
   - `BaseFactor.compute()` 期望长表格式
   - 缺少格式转换层

2. **基础设施未利用**：
   - `FactorEngine.compute_for_symbols()` 已提供多股票因子计算能力
   - 但需要 `data_dict` 格式输入，而非宽表格式

3. **因子未自动注册**：
   - Library 中的因子类未自动注册到 `FactorRegistry`

## 优化方案

### 方案设计

在 `FactorAnalysisPipeline` 中添加新方法 `run_with_factor()`，支持：
- 直接传入 `BaseFactor` 实例
- 通过因子名称获取已注册的因子
- 自动处理数据格式转换

### 实现步骤

#### 步骤 1：创建数据格式转换工具

**文件**：`trader_center/factor/mining/data_adapter.py`

**功能**：
- `wide_to_dict(price_df, columns=None)` - 宽表转字典
- `dict_to_wide(data_dict)` - 字典转宽表
- `prepare_ohlcv_data(price_df, volume_df=None)` - 准备 OHLCV 数据

#### 步骤 2：扩展 FactorAnalysisPipeline

**文件**：`trader_center/factor/mining/pipeline.py`

**新增方法**：
```python
def run_with_factor(
    self,
    factor: Union[str, BaseFactor],
    price_df: pd.DataFrame,
    volume_df: pd.DataFrame = None,
    factor_params: Dict = None,
    **kwargs,
) -> Dict:
    """
    使用 BaseFactor 实例运行因子分析
    
    Args:
        factor: 因子名称或 BaseFactor 实例
        price_df: 价格数据（宽表格式）
        volume_df: 成交量数据（可选）
        factor_params: 因子参数
        **kwargs: 传递给 run() 的参数
    """
```

#### 步骤 3：创建因子自动注册机制

**文件**：`trader_center/factor/library/auto_register.py`

**功能**：
- 自动发现并注册所有因子类
- 支持延迟加载

#### 步骤 4：重构 momentum.py 示例

**文件**：`factor_research/momentum.py`

**改造内容**：
1. 使用 `MomentumFactor` 替代自定义 `calculate_momentum_factor`
2. 利用 `FactorAnalysisPipeline.run_with_factor()` 方法
3. 支持多周期参数批量分析

### 详细实现

#### 1. data_adapter.py

```python
"""
因子数据适配器

处理不同数据格式之间的转换。
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np


def wide_to_dict(
    price_df: pd.DataFrame,
    include_ohlcv: bool = False,
    open_df: pd.DataFrame = None,
    high_df: pd.DataFrame = None,
    low_df: pd.DataFrame = None,
    volume_df: pd.DataFrame = None,
) -> Dict[str, pd.DataFrame]:
    """
    将宽表格式价格数据转换为字典格式
    
    Args:
        price_df: 收盘价数据（index=日期，columns=股票代码）
        include_ohlcv: 是否包含完整 OHLCV 数据
        open_df, high_df, low_df, volume_df: 可选的 OHLCV 数据
    
    Returns:
        {symbol: DataFrame} 格式的字典
    """
    data_dict = {}
    
    for symbol in price_df.columns:
        data = pd.DataFrame({'close': price_df[symbol]})
        
        if include_ohlcv:
            if open_df is not None and symbol in open_df.columns:
                data['open'] = open_df[symbol]
            else:
                data['open'] = price_df[symbol]
            
            if high_df is not None and symbol in high_df.columns:
                data['high'] = high_df[symbol]
            else:
                data['high'] = price_df[symbol]
            
            if low_df is not None and symbol in low_df.columns:
                data['low'] = low_df[symbol]
            else:
                data['low'] = price_df[symbol]
            
            if volume_df is not None and symbol in volume_df.columns:
                data['volume'] = volume_df[symbol]
            else:
                data['volume'] = 0
        
        data_dict[symbol] = data
    
    return data_dict


def dict_to_wide(data_dict: Dict[str, pd.Series]) -> pd.DataFrame:
    """
    将字典格式数据转换为宽表格式
    
    Args:
        data_dict: {symbol: Series} 格式的字典
    
    Returns:
        宽表格式 DataFrame
    """
    return pd.DataFrame(data_dict)
```

#### 2. pipeline.py 扩展

```python
def run_with_factor(
    self,
    factor: Union[str, BaseFactor],
    price_df: pd.DataFrame,
    volume_df: pd.DataFrame = None,
    factor_params: Dict = None,
    preprocessing: bool = True,
    scoring: bool = True,
    visualize: bool = True,
    generate_report: bool = False,
    metadata: Dict = None,
    **kwargs,
) -> Dict:
    """
    使用 BaseFactor 实例运行因子分析
    
    Args:
        factor: 因子名称（字符串）或 BaseFactor 实例
        price_df: 价格数据（宽表格式，index=日期，columns=股票代码）
        volume_df: 成交量数据（可选）
        factor_params: 因子参数（当 factor 为字符串时使用）
        preprocessing: 是否进行预处理
        scoring: 是否进行评分
        visualize: 是否生成可视化
        generate_report: 是否生成报告
        metadata: 因子元数据
        **kwargs: 其他参数
    
    Returns:
        分析结果字典
    """
    from trader_center.factor.mining.data_adapter import wide_to_dict
    
    # 获取因子实例
    if isinstance(factor, str):
        factor_instance = self.registry.get(factor)
        if factor_params:
            factor_instance.set_params(**factor_params)
    else:
        factor_instance = factor
    
    # 转换数据格式
    include_volume = 'volume' in factor_instance.required_data
    data_dict = wide_to_dict(
        price_df,
        include_ohlcv=True,
        volume_df=volume_df if include_volume else None,
    )
    
    # 计算因子值
    factor_df = self.engine.compute_for_symbols(
        factor_instance.name,
        data_dict,
        parallel=True,
        **(factor_params or {}),
    )
    
    # 生成因子名称
    params_str = '_'.join(f"{k}{v}" for k, v in factor_instance.params.items())
    factor_name = f"{factor_instance.name}_{params_str}" if params_str else factor_instance.name
    
    # 合并元数据
    full_metadata = factor_instance.get_metadata()
    if metadata:
        full_metadata.update(metadata)
    
    # 调用原有的 run 方法
    return self.run(
        factor_name=factor_name,
        factor_df=factor_df,
        price_df=price_df,
        preprocessing=preprocessing,
        scoring=scoring,
        visualize=visualize,
        generate_report=generate_report,
        metadata=full_metadata,
        **kwargs,
    )
```

#### 3. auto_register.py

```python
"""
因子自动注册

自动发现并注册所有因子类。
"""

import logging
from typing import List, Type
from trader_center.factor.library.base import BaseFactor
from trader_center.factor.library.registry import FactorRegistry

logger = logging.getLogger(__name__)


def auto_register_factors(
    registry: FactorRegistry = None,
    default_params: dict = None,
) -> List[str]:
    """
    自动注册所有因子
    
    Args:
        registry: 因子注册器，默认使用全局单例
        default_params: 默认参数
    
    Returns:
        注册的因子名称列表
    """
    registry = registry or FactorRegistry()
    default_params = default_params or {}
    registered = []
    
    # 导入所有因子模块
    from trader_center.factor.library.technical import (
        MomentumFactor, RSIFactor, MACDFactor,
        PriceRateOfChangeFactor, MomentumQualityFactor,
        VolumeAdjustedMomentumFactor,
        ATRFactor, HistoricalVolatilityFactor,
        TrendStrengthFactor,
        SharpeRatioFactor, SortinoRatioFactor,
        MaxDrawdownFactor, AverageDrawdownFactor,
        # ... 其他因子
    )
    
    # 因子类列表
    factor_classes = [
        MomentumFactor, RSIFactor, MACDFactor,
        PriceRateOfChangeFactor, MomentumQualityFactor,
        VolumeAdjustedMomentumFactor,
        ATRFactor, HistoricalVolatilityFactor,
        TrendStrengthFactor,
        SharpeRatioFactor, SortinoRatioFactor,
        MaxDrawdownFactor, AverageDrawdownFactor,
    ]
    
    for factor_class in factor_classes:
        try:
            factor = factor_class(**default_params.get(factor_class.name, {}))
            registry.register(factor)
            registered.append(factor.name)
        except Exception as e:
            logger.warning(f"注册因子 {factor_class.__name__} 失败: {e}")
    
    logger.info(f"自动注册了 {len(registered)} 个因子")
    return registered
```

#### 4. 重构后的 momentum.py

```python
"""
单因子复现研究 - 价格动量因子

使用 library 中的 MomentumFactor 进行因子研究。
"""

import pandas as pd
import numpy as np
from pathlib import Path

from trader_center.factor.mining import FactorAnalysisPipeline
from trader_center.factor.library.technical.momentum import MomentumFactor
from trader_center.factor.library.registry import FactorRegistry


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_BASE_DIR = PROJECT_ROOT / 'factor_research_results'


def get_stock_data(symbols: list, start_date: str, end_date: str) -> pd.DataFrame:
    """获取股票数据（同原实现）"""
    # ... 保持原有实现
    pass


def create_sample_data() -> pd.DataFrame:
    """创建示例数据（同原实现）"""
    # ... 保持原有实现
    pass


def run_factor_research(
    price_df: pd.DataFrame,
    factor_class: type = MomentumFactor,
    periods: list = [5, 10, 20, 60],
    volume_df: pd.DataFrame = None,
):
    """
    运行因子研究
    
    使用 library 中的因子类进行分析。
    
    Args:
        price_df: 价格数据（宽表格式）
        factor_class: 因子类
        periods: 因子参数列表
        volume_df: 成交量数据（可选）
    """
    print("=" * 60)
    print(f"因子研究: {factor_class.name}")
    print("=" * 60)
    
    output_dir = OUTPUT_BASE_DIR / factor_class.name
    
    # 注册因子
    registry = FactorRegistry()
    
    pipeline = FactorAnalysisPipeline(
        registry=registry,
        output_dir=str(output_dir),
        use_alphalens=False,
    )
    
    results = {}
    
    for period in periods:
        print(f"\n--- 参数: period={period} ---")
        
        # 创建因子实例
        factor = factor_class(period=period)
        
        # 使用 run_with_factor 方法
        result = pipeline.run_with_factor(
            factor=factor,
            price_df=price_df,
            volume_df=volume_df,
            preprocessing=True,
            scoring=True,
            visualize=True,
            generate_report=True,
            metadata={
                'factor_type': factor_class.name,
                'period': period,
                'n_assets': len(price_df.columns),
                'n_dates': len(price_df),
            }
        )
        
        results[f'{factor_class.name}_{period}'] = result
        
        print(f"IC均值: {result['summary'].get('ic_mean', 0):.4f}")
        print(f"ICIR: {result['summary'].get('icir', 0):.4f}")
        if 'score' in result:
            print(f"评分: {result['score']['total_score']:.2f} ({result['score']['grade']})")
    
    print("\n" + "=" * 60)
    print("所有参数分析完成")
    print("=" * 60)
    
    ranking = pipeline.get_ranking()
    print("\n--- 因子排名 ---")
    print(ranking)
    
    return results, pipeline


def main():
    """主函数"""
    print("因子复现研究 - 价格动量因子")
    print("=" * 60)
    
    USE_REAL_DATA = False
    
    if USE_REAL_DATA:
        print("使用真实数据...")
        symbols = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ']
        try:
            price_df = get_stock_data(
                symbols=symbols,
                start_date='2023-01-01',
                end_date='2024-12-31',
            )
            print(f"获取到 {len(price_df)} 天的数据，{len(price_df.columns)} 只股票")
        except Exception as e:
            print(f"获取数据失败: {e}，使用示例数据")
            price_df = create_sample_data()
    else:
        print("使用示例数据...")
        price_df = create_sample_data()
        print(f"生成数据: {len(price_df)} 天，{len(price_df.columns)} 只股票")
    
    results, pipeline = run_factor_research(
        price_df=price_df,
        factor_class=MomentumFactor,
        periods=[5, 10, 20, 60],
    )
    
    print("\n研究完成！")
    print(f"结果保存在: {OUTPUT_BASE_DIR / 'momentum'}")


if __name__ == "__main__":
    main()
```

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `trader_center/factor/mining/data_adapter.py` | 新建 | 数据格式转换工具 |
| `trader_center/factor/mining/pipeline.py` | 修改 | 添加 `run_with_factor` 方法 |
| `trader_center/factor/library/auto_register.py` | 新建 | 因子自动注册机制 |
| `trader_center/factor/mining/__init__.py` | 修改 | 导出新模块 |
| `factor_research/momentum.py` | 修改 | 重构为使用 library 因子 |

## 优势

1. **统一接口**：所有 library 中的因子都可以通过 `run_with_factor` 方法使用
2. **代码复用**：避免重复实现因子计算逻辑
3. **易于扩展**：新增因子只需继承 `BaseFactor`，无需修改研究脚本
4. **向后兼容**：保留原有的 `run` 方法，不影响现有代码

## 测试计划

1. 单元测试 `data_adapter.py` 的格式转换功能
2. 集成测试 `run_with_factor` 方法
3. 验证 `momentum.py` 重构后的功能一致性
