# Backtest 绩效分析优化计划

## 背景

当前 `trader_center.backtest` 模块的绩效分析功能较为简单，主要包括：
- 基础指标：收益率、最大回撤、夏普比率
- backtrader 内置分析器：Returns, DrawDown, TradeAnalyzer, SQN, SharpeRatio
- 简单的 matplotlib 可视化图表

## 优化目标

集成 **QuantStats** 库，提供专业级的绩效分析能力。

### QuantStats 优势

| 功能 | 当前实现 | QuantStats |
|------|---------|------------|
| 风险指标 | 夏普比率、最大回撤 | Sortino、Calmar、Omega、VaR、CVaR 等 20+ 指标 |
| 可视化 | 简单 matplotlib 图表 | 专业 HTML 交互报告 |
| 基准对比 | 无 | 支持任意基准对比 |
| 滚动分析 | 无 | 滚动夏普、滚动波动率等 |
| 回撤分析 | 仅最大回撤 | 完整回撤周期分析 |
| 月度/年度收益 | 无 | 热力图、表格展示 |

## 实现步骤

### Step 1: 添加 QuantStats 依赖

**文件**: `pyproject.toml`

```toml
[project.optional-dependencies]
backtest = [
    "quantstats>=0.0.62",
]
```

### Step 2: 创建绩效分析模块

**新建文件**: `trader_center/backtest/analytics.py`

核心功能：
1. `PerformanceAnalytics` 类 - 绩效分析核心
2. 支持从 `BacktestResult` 或 DataFrame 生成分析
3. 生成 QuantStats HTML 报告
4. 提供丰富的绩效指标计算

```python
class PerformanceAnalytics:
    """绩效分析器"""
    
    def __init__(self, returns: pd.Series, benchmark: pd.Series = None):
        self.returns = returns
        self.benchmark = benchmark
    
    def metrics(self) -> Dict[str, float]:
        """计算完整绩效指标"""
        
    def report(self, output_path: str = None, title: str = None) -> str:
        """生成 HTML 报告"""
        
    def plot_snapshot(self, output_path: str = None):
        """生成快照图表"""
        
    def plot_earnings(self, output_path: str = None):
        """生成收益图表"""
```

### Step 3: 扩展 BacktestResult

**修改文件**: `trader_center/backtest/results.py`

新增方法：
```python
class BacktestResult:
    # 新增方法
    def get_returns_series(self) -> pd.Series:
        """获取日收益率序列（QuantStats 兼容格式）"""
    
    def generate_performance_report(
        self, 
        output_dir: Path = None,
        benchmark: str = None,  # 如 "000300.SH" 沪深300
        title: str = None
    ) -> str:
        """生成完整绩效分析报告"""
    
    def get_extended_metrics(self) -> Dict[str, float]:
        """获取扩展绩效指标（Sortino, Calmar, Omega 等）"""
```

### Step 4: 扩展 BacktestConfig

**修改文件**: `trader_center/backtest/config.py`

新增配置项：
```python
@dataclass
class BacktestConfig:
    # ... 现有配置 ...
    
    # 绩效分析配置
    enable_quantstats: bool = True          # 启用 QuantStats 分析
    benchmark_symbol: str = "000300.SH"     # 默认基准（沪深300）
    auto_save_report: bool = True           # 自动保存 HTML 报告
```

### Step 5: 更新 BacktestRunner

**修改文件**: `trader_center/backtest/runner.py`

修改点：
1. 回测完成后自动调用绩效分析
2. 加载基准数据用于对比
3. 保存 QuantStats HTML 报告

```python
def run(self, ...):
    # ... 现有逻辑 ...
    
    # 生成 QuantStats 报告
    if self.config.enable_quantstats:
        report_path = result.generate_performance_report(
            output_dir=self.config.trade_log_dir,
            benchmark=self.config.benchmark_symbol
        )
```

### Step 6: 更新 CLI

**修改文件**: `trader_center/backtest/cli.py`

新增参数：
```
--benchmark       基准指数代码（默认沪深300）
--no-quantstats   禁用 QuantStats 分析
--report-only     仅生成报告（不显示图表）
```

### Step 7: 更新文档

**修改文件**: `trader_center/backtest/README.md`

添加 QuantStats 相关说明：
- 新增绩效指标列表
- HTML 报告示例
- 使用方法说明

## 新增绩效指标

集成 QuantStats 后将支持以下指标：

### 收益指标
- Total Return (总收益)
- CAGR (年化复合增长率)
- Expected Return (预期收益)

### 风险指标
- Volatility (年化波动率)
- Max Drawdown (最大回撤)
- VaR (风险价值)
- CVaR (条件风险价值)
- Downside Deviation (下行偏差)

### 风险调整收益
- Sharpe Ratio (夏普比率)
- Sortino Ratio (索提诺比率)
- Calmar Ratio (卡尔马比率)
- Omega Ratio (欧米伽比率)
- Tail Ratio (尾部比率)

### 交易指标
- Win Rate (胜率)
- Profit Factor (盈亏比)
- Expected Return per Trade (单笔预期收益)
- Kelly Criterion (凯利准则)

## 输出文件变更

```
logs/backtest/{strategy_name}/{run_id}/
├── trades.csv           # 交易记录
├── daily_values.csv     # 每日资产价值
├── signals.csv          # 信号日志
├── capitals.csv         # 资金日志
├── positions.csv        # 持仓日志
├── orders.csv           # 订单日志
├── summary.json         # 回测摘要
├── plot.png             # 可视化图表
├── performance_report.html    # [新增] QuantStats HTML 报告
└── metrics.json               # [新增] 完整绩效指标
```

## 兼容性考虑

1. **可选依赖**: QuantStats 作为可选依赖，未安装时降级到现有实现
2. **向后兼容**: 现有 API 不变，新增方法为可选功能
3. **性能影响**: HTML 报告生成可选，不影响核心回测性能

## 测试计划

1. 单元测试：`tests/backtest/test_analytics.py`
   - 测试绩效指标计算准确性
   - 测试报告生成

2. 集成测试：
   - 测试完整回测流程
   - 测试基准数据加载

3. 边界测试：
   - 无交易情况
   - 空数据情况
   - QuantStats 未安装情况

## 预估工作量

| 任务 | 文件 | 复杂度 |
|-----|------|--------|
| 添加依赖 | pyproject.toml | 低 |
| 创建分析模块 | analytics.py (新建) | 高 |
| 扩展结果类 | results.py | 中 |
| 扩展配置类 | config.py | 低 |
| 更新运行器 | runner.py | 中 |
| 更新 CLI | cli.py | 低 |
| 更新文档 | README.md | 低 |
| 编写测试 | test_analytics.py | 中 |

## 执行顺序

1. ✅ 分析现有代码结构
2. ⬜ 添加 QuantStats 依赖
3. ⬜ 创建 `analytics.py` 绩效分析模块
4. ⬜ 扩展 `BacktestResult` 类
5. ⬜ 扩展 `BacktestConfig` 配置
6. ⬜ 更新 `BacktestRunner`
7. ⬜ 更新 CLI 参数
8. ⬜ 更新 README 文档
9. ⬜ 编写单元测试
10. ⬜ 集成测试验证
