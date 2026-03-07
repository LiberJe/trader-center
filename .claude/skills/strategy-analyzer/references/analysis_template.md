# 策略分析模板参考

此文件提供策略分析的详细模板和检查清单。

## 代码审查检查清单

### 基础结构
- [ ] 策略继承自 BaseStrategy
- [ ] 正确设置了 name 和 description 类属性
- [ ] params 参数定义清晰

### 指标定义
- [ ] 指标选择符合策略逻辑
- [ ] 指标参数可配置
- [ ] 避免指标冗余计算

### 交易逻辑
- [ ] 入场条件明确
- [ ] 出场条件完整
- [ ] 仓位计算合理
- [ ] 避免信号冲突

### 日志记录
- [ ] 使用 log_signal 记录交易信号
- [ ] 包含触发条件描述
- [ ] 记录关键指标值
- [ ] 调用 _log_daily_state() 记录每日状态

## 绩效评估标准

### 收益类指标
| 指标 | 优秀 | 良好 | 一般 | 较差 |
|------|------|------|------|------|
| 年化收益率 | >20% | 10-20% | 5-10% | <5% |
| 超额收益 | >10% | 5-10% | 0-5% | <0% |

### 风险类指标
| 指标 | 优秀 | 良好 | 一般 | 较差 |
|------|------|------|------|------|
| 最大回撤 | <10% | 10-20% | 20-30% | >30% |
| 夏普比率 | >1.5 | 1-1.5 | 0.5-1 | <0.5 |
| 胜率 | >55% | 45-55% | 35-45% | <35% |
| 盈亏比 | >2 | 1.5-2 | 1-1.5 | <1 |

## 常见问题诊断

### 问题：交易过于频繁
**症状**：
- 日交易次数 > 1
- 平均持仓时间 < 5天
- 手续费占比 > 5%

**可能原因**：
1. 指标周期过短
2. 缺乏信号过滤
3. 震荡市中频繁触发

**解决方案**：
1. 增加指标周期
2. 添加趋势过滤器
3. 设置最小持仓时间
4. 添加信号确认机制

### 问题：胜率过低
**症状**：
- 胜率 < 40%
- 连续亏损次数 > 5次

**可能原因**：
1. 信号质量差
2. 趋势判断错误
3. 参数设置不当

**解决方案**：
1. 增加确认条件
2. 调整超买超卖阈值
3. 添加市场环境判断

### 问题：回撤过大
**症状**：
- 最大回撤 > 20%
- 回撤恢复时间 > 3个月

**可能原因**：
1. 缺乏止损机制
2. 仓位过重
3. 单票持仓比例过高

**解决方案**：
1. 添加硬止损（如 -8%）
2. 实施 trailing stop
3. 限制单票仓位比例
4. 添加市场风控（如大盘跌破均线清仓）

### 问题：收益不稳定
**症状**：
- 月度收益波动大
- 依赖特定行情

**可能原因**：
1. 策略适应性差
2. 只在特定市场有效
3. 过度拟合历史数据

**解决方案**：
1. 添加市场环境判断
2. 实施策略切换机制
3. 进行样本外测试

## 改进建议优先级

### P0 - 必须修复
- 逻辑错误
- 风控缺失
- 明显的过度拟合

### P1 - 强烈建议
- 添加止损
- 优化参数
- 改进信号过滤

### P2 - 建议优化
- 仓位管理优化
- 增加市场环境判断
- 多因子结合

### P3 - 可选增强
- 增加可视化
- 优化日志输出
- 性能优化

## Python 分析代码片段

### 读取回测日志
```python
import pandas as pd
import json
from pathlib import Path

def load_backtest_logs(log_dir: Path):
    """加载回测日志文件"""
    logs = {}

    # 加载摘要
    summary_path = log_dir / "summary.json"
    if summary_path.exists():
        with open(summary_path, 'r', encoding='utf-8') as f:
            logs['summary'] = json.load(f)

    # 加载交易记录
    trades_path = log_dir / "trades.csv"
    if trades_path.exists():
        logs['trades'] = pd.read_csv(trades_path)

    # 加载信号日志
    signals_path = log_dir / "signals.csv"
    if signals_path.exists():
        logs['signals'] = pd.read_csv(signals_path)

    # 加载资金日志
    capitals_path = log_dir / "capitals.csv"
    if capitals_path.exists():
        logs['capitals'] = pd.read_csv(capitals_path)
        logs['capitals']['date'] = pd.to_datetime(logs['capitals']['date'])

    # 加载持仓日志
    positions_path = log_dir / "positions.csv"
    if positions_path.exists():
        logs['positions'] = pd.read_csv(positions_path)
        logs['positions']['date'] = pd.to_datetime(logs['positions']['date'])

    # 加载订单日志
    orders_path = log_dir / "orders.csv"
    if orders_path.exists():
        logs['orders'] = pd.read_csv(orders_path)

    return logs
```

### 分析交易统计
```python
def analyze_trades(trades_df: pd.DataFrame):
    """分析交易统计"""
    if trades_df.empty:
        return {}

    winning_trades = trades_df[trades_df['pnl'] > 0]
    losing_trades = trades_df[trades_df['pnl'] < 0]

    return {
        'total_trades': len(trades_df),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0,
        'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
        'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
        'max_win': winning_trades['pnl'].max() if len(winning_trades) > 0 else 0,
        'max_loss': losing_trades['pnl'].min() if len(losing_trades) > 0 else 0,
        'profit_factor': (
            winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum())
            if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0
            else float('inf')
        ),
    }
```

### 分析回撤
```python
def analyze_drawdown(capitals_df: pd.DataFrame):
    """分析回撤情况"""
    if capitals_df.empty or 'total_value' not in capitals_df.columns:
        return {}

    df = capitals_df.sort_values('date').copy()
    df['peak'] = df['total_value'].cummax()
    df['drawdown'] = (df['total_value'] - df['peak']) / df['peak']

    max_dd_idx = df['drawdown'].idxmin()
    max_dd_date = df.loc[max_dd_idx, 'date']
    max_dd_value = df.loc[max_dd_idx, 'drawdown']

    # 找到回撤开始日期
    peak_before_dd = df.loc[:max_dd_idx, 'peak'].iloc[-2] if max_dd_idx > 0 else df['peak'].iloc[0]
    dd_start_idx = df[df['total_value'] == peak_before_dd].index[0] if any(df['total_value'] == peak_before_dd) else 0
    dd_start_date = df.loc[dd_start_idx, 'date']

    return {
        'max_drawdown': max_dd_value,
        'max_drawdown_date': max_dd_date,
        'drawdown_start_date': dd_start_date,
        'drawdown_duration': (max_dd_date - dd_start_date).days,
        'avg_drawdown': df['drawdown'].mean(),
    }
```

### 分析信号质量
```python
def analyze_signal_quality(signals_df: pd.DataFrame, trades_df: pd.DataFrame):
    """分析信号质量"""
    if signals_df.empty:
        return {}

    # 按信号类型分组
    buy_signals = signals_df[signals_df['signal_type'] == 'buy']
    sell_signals = signals_df[signals_df['signal_type'] == 'sell']

    # 置信度分布
    confidence_stats = {
        'avg_confidence': signals_df['confidence'].mean() if 'confidence' in signals_df.columns else None,
        'high_confidence_count': len(signals_df[signals_df['confidence'] > 0.8]) if 'confidence' in signals_df.columns else 0,
    }

    return {
        'total_signals': len(signals_df),
        'buy_signals': len(buy_signals),
        'sell_signals': len(sell_signals),
        **confidence_stats,
    }
```
