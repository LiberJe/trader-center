# 动量因子研究数据集改造计划

## 问题分析

### 当前问题

当前 `momentum.py` 中的数据集配置存在以下问题：

1. **样本量不足**：仅使用 4 只 ETF，样本量太小
2. **资产类型不当**：使用 ETF 而非股票
3. **数据获取方式不规范**：直接使用 `AkshareFetcher`，而非 `trader_center.data_hub` 统一接口
4. **未利用现有缓存机制**：`data_hub` 已有缓存功能，但未使用

### data\_hub 现有能力

`trader_center.data_hub` 已提供：

* `get_daily_bars(symbol, start, end)` - 获取日线数据（带缓存，TTL=300秒）

* `get_stock_list(exchange)` - 获取股票列表（带缓存，TTL=86400秒）

* `CacheManager` - 内存缓存管理器

## 改造方案

### 核心改动

1. **使用 data\_hub 统一接口**：替换直接使用 AkshareFetcher
2. **新增指数成分股获取函数**：利用 akshare 获取沪深300/中证500成分股
3. **批量获取数据**：使用 data\_hub 的缓存机制提高效率

### 实施步骤

#### 步骤 1：新增股票池获取函数

```python
def get_index_constituents(index_code: str) -> list:
    """
    获取指数成分股
    
    Args:
        index_code: 指数代码
            - '000300': 沪深300
            - '000905': 中证500
            - '000852': 中证1000
    
    Returns:
        股票代码列表，格式如 ['000001.SZ', '600000.SH']
    """
    import akshare as ak
    
    df = ak.index_stock_cons(symbol=index_code)
    symbols = []
    
    for _, row in df.iterrows():
        code = str(row['成分券代码'])
        # 根据代码判断交易所
        if code.startswith(('60', '68', '88', '89')):
            exchange = 'SH'
        elif code.startswith(('00', '30', '82', '83')):
            exchange = 'SZ'
        else:
            exchange = 'SH'
        symbols.append(f"{code}.{exchange}")
    
    return symbols
```

#### 步骤 2：修改数据获取函数

```python
import trader_center.data_hub as dh

def get_stock_data(symbols: list, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取股票数据（使用 data_hub 统一接口）
    
    Args:
        symbols: 股票代码列表
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
    
    Returns:
        价格DataFrame，index为日期，columns为股票代码
    """
    price_data = {}
    
    for symbol in symbols:
        try:
            df = dh.get_daily_bars(symbol, start_date, end_date)
            if df is not None and not df.empty:
                price_data[symbol] = df['close']
        except Exception as e:
            print(f"获取 {symbol} 数据失败: {e}")
    
    if not price_data:
        raise ValueError("未获取到任何股票数据")
    
    price_df = pd.DataFrame(price_data)
    price_df.index = pd.to_datetime(price_df.index)
    price_df = price_df.sort_index()
    
    return price_df
```

#### 步骤 3：修改 main() 函数

```python
def main():
    """主函数"""
    print("因子复现研究 - 价格动量因子")
    print("=" * 60)
    
    # 配置参数
    POOL_TYPE = 'hs300_zz500'  # 沪深300 + 中证500
    START_DATE = '2019-01-01'
    END_DATE = '2024-12-31'
    
    # 获取股票池
    print(f"获取股票池: {POOL_TYPE}")
    symbols = []
    
    if POOL_TYPE in ['hs300', 'hs300_zz500']:
        hs300 = get_index_constituents('000300')
        symbols.extend(hs300)
        print(f"  沪深300: {len(hs300)} 只")
    
    if POOL_TYPE in ['zz500', 'hs300_zz500']:
        zz500 = get_index_constituents('000905')
        symbols.extend(zz500)
        print(f"  中证500: {len(zz500)} 只")
    
    # 去重
    symbols = list(set(symbols))
    print(f"股票池总计: {len(symbols)} 只")
    
    # 获取数据
    print(f"\n获取数据: {START_DATE} 至 {END_DATE}")
    print("(首次获取可能需要较长时间，后续会使用缓存)")
    
    try:
        price_df = get_stock_data(symbols, START_DATE, END_DATE)
        print(f"获取到 {len(price_df)} 天的数据，{len(price_df.columns)} 只股票")
    except Exception as e:
        print(f"获取数据失败: {e}")
        return
    
    # 运行因子研究
    results, pipeline = run_factor_research(
        price_df=price_df,
        factor_class=MomentumFactor,
        periods=[5, 10, 20, 60],
    )
    
    compare_different_periods(results)
    
    print("\n研究完成！")
    print(f"结果保存在: {OUTPUT_BASE_DIR / 'momentum'}")
```

## 文件变更清单

| 文件                            | 变更内容                                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------- |
| `factor_research/momentum.py` | 1. 新增 `get_index_constituents()` 函数2. 修改 `get_stock_data()` 使用 data\_hub 接口3. 修改 `main()` 函数使用新股票池 |

## 推荐配置

| 参数   | 推荐值                     | 说明          |
| ---- | ----------------------- | ----------- |
| 股票池  | 沪深300 + 中证500           | 约800只，样本量充足 |
| 时间跨度 | 2019-01-01 至 2024-12-31 | 5年，覆盖不同市场周期 |
| 因子周期 | \[5, 10, 20, 60]        | 短中长期动量      |

## 优势

1. **统一接口**：使用 `trader_center.data_hub` 统一数据访问层
2. **自动缓存**：利用 data\_hub 内置缓存机制，避免重复请求
3. **样本量充足**：约800只股票，统计显著性大幅提升
4. **代码规范**：符合项目架构设计

