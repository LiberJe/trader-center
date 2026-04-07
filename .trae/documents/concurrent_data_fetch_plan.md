# 数据获取并发优化计划

## 问题分析

### 当前实现

`momentum.py` 中的 `get_stock_data` 函数使用串行方式获取数据：

```python
for i, symbol in enumerate(symbols):
    df = dh.get_daily_bars(symbol, start_date, end_date)
    ...
```

### 性能问题

- **串行获取**：每只股票依次获取，总耗时 = 单只股票耗时 × 股票数量
- **IO 密集型**：数据获取主要等待网络响应，CPU 利用率低
- **效率低下**：获取 300 只股票可能需要数分钟

### 优化目标

使用并发方式获取数据，充分利用网络 IO 等待时间，大幅减少总耗时。

## 优化方案

### 方案选择

| 方案 | 优点 | 缺点 | 适用性 |
|------|------|------|--------|
| `ThreadPoolExecutor` | 简单易用、适合 IO 密集型 | GIL 限制 | ✅ 推荐 |
| `asyncio` | 高效、无 GIL 限制 | 需要异步库支持 | ❌ akshare 不支持 |
| `ProcessPoolExecutor` | 绕过 GIL | 进程开销大、数据序列化复杂 | ❌ 不适合 |

**选择**：使用 `concurrent.futures.ThreadPoolExecutor`

### 实现方案

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def get_stock_data(symbols: list, start_date: str, end_date: str, max_workers: int = 10) -> pd.DataFrame:
    """
    并发获取股票数据
    """
    price_data = {}
    failed_symbols = []
    lock = threading.Lock()
    
    total = len(symbols)
    start_time = datetime.now()
    completed_count = [0]  # 使用列表以便在闭包中修改
    
    def fetch_single(symbol: str) -> tuple:
        """获取单只股票数据"""
        try:
            df = dh.get_daily_bars(symbol, start_date, end_date)
            return (symbol, df['close'] if df is not None and not df.empty else None, None)
        except Exception as e:
            return (symbol, None, str(e))
    
    # 使用线程池并发获取
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single, symbol): symbol for symbol in symbols}
        
        for future in as_completed(futures):
            symbol, close_series, error = future.result()
            completed_count[0] += 1
            
            if close_series is not None:
                with lock:
                    price_data[symbol] = close_series
            else:
                failed_symbols.append(symbol)
            
            # 更新进度
            progress = completed_count[0] / total
            elapsed = (datetime.now() - start_time).total_seconds()
            if completed_count[0] > 0 and elapsed > 0:
                avg_time = elapsed / completed_count[0]
                remaining = avg_time * (total - completed_count[0])
                eta_str = f"ETA: {int(remaining)}s"
            else:
                eta_str = "ETA: --"
            
            status = f"\r  进度: {completed_count[0]}/{total} ({progress*100:.1f}%) | 成功: {len(price_data)} | 失败: {len(failed_symbols)} | {eta_str}    "
            sys.stdout.write(status)
            sys.stdout.flush()
    
    print()
    ...
```

## 实施步骤

### 步骤 1：修改 `get_stock_data` 函数

**文件**：`factor_research/momentum.py`

**修改内容**：
1. 导入 `concurrent.futures` 和 `threading`
2. 添加 `max_workers` 参数
3. 使用 `ThreadPoolExecutor` 并发获取数据
4. 添加线程安全的进度更新

### 步骤 2：添加配置参数

在 `main()` 函数中添加并发配置：

```python
# 配置参数
MAX_WORKERS = 20  # 并发线程数，建议 10-30
```

### 步骤 3：错误处理优化

- 捕获单个股票获取失败，不影响其他股票
- 记录失败原因，便于排查

## 文件变更清单

| 文件 | 变更内容 |
|------|----------|
| `factor_research/momentum.py` | 1. 导入 `concurrent.futures`<br>2. 修改 `get_stock_data` 为并发实现<br>3. 添加 `max_workers` 参数 |

## 性能预期

| 场景 | 串行耗时 | 并发耗时（预期） | 提升比例 |
|------|----------|------------------|----------|
| 300 只股票 | ~5 分钟 | ~30 秒 | 10x |
| 800 只股票 | ~15 分钟 | ~2 分钟 | 7x |

实际提升取决于：
- 网络延迟
- API 限速
- 服务器响应速度

## 注意事项

1. **API 限速**：akshare 可能有请求频率限制，需要适当调整 `max_workers`
2. **内存使用**：并发获取会增加内存占用
3. **错误处理**：单个股票失败不应影响整体流程

## 测试计划

1. 测试少量股票（10只）验证功能正确性
2. 测试大量股票（300只）验证性能提升
3. 测试错误处理（故意使用无效股票代码）
