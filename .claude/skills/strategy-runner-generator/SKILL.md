---
name: strategy-runner-generator
description: |
  为 trader_center 回测系统生成策略运行器（Strategy Runner）可执行组件。
  当用户想要创建一个可以直接运行的策略执行脚本、将策略封装成独立可执行文件、或生成完整的策略回测运行器时使用此技能。
  适用于需要生成 run_*.py 形式的策略运行器、创建可执行的交易策略回测脚本、或封装策略为命令行工具的场景。
---

# 策略运行器生成器 (Strategy Runner Generator)

此技能帮助用户生成完整的策略运行器可执行组件。生成的 runner 是一个独立的 Python 脚本，可以直接运行执行策略回测。

## 使用场景

当用户想要以下操作时，使用此技能：
- 创建一个可执行的策略运行脚本
- 将策略封装为独立的 runner 组件
- 生成完整的策略回测执行器
- 创建命令行可运行的策略测试脚本
- 为现有策略生成对应的运行器

## 输出格式

生成的 runner 文件是一个完整的 Python 脚本，包含：
1. **文件头**：模块文档字符串和路径设置
2. **导入区**：必要的模块导入
3. **main() 函数**：完整的回测配置和执行逻辑
4. **输出展示**：结构化的回测结果打印
5. **策略说明**：详细的策略逻辑说明和扩展建议

## 文件命名规范

- 保存到 `backtest_runner/` 目录
- 命名格式：`run_{strategy_name_snake_case}.py`
- 例如：`run_sma_cross.py`, `run_multi_factor_rotation.py`

## 生成步骤

### 步骤 1：理解策略

从用户输入中提取：
- **策略名称**：中文名称和英文标识
- **策略类路径**：完整的模块导入路径
- **策略参数**：需要的配置参数及其默认值
- **股票池**：回测使用的标的列表
- **回测区间**：开始和结束日期
- **资金配置**：初始资金、仓位管理等
- **特殊需求**：如再平衡频率、止盈止损等

### 步骤 2：生成 Runner 代码

使用以下模板结构生成代码：

```python
"""
{策略中文名称}运行示例

{策略描述}
"""

import sys
from pathlib import Path
# 添加项目根目录到路径，确保使用当前开发代码而非已安装包
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date
from trader_center.backtest import BacktestRunner, BacktestConfig
from {strategy_module} import {strategy_class}


def main():
    print("=" * 60)
    print("{策略中文名称}回测")
    print("=" * 60)

    # 策略配置展示
    print("\n策略配置:")
    # ... 配置详情

    symbols = {symbols_list}

    config = BacktestConfig(
        initial_cash={initial_cash},
        auto_save_trades=True,
        auto_save_plot=True,
        enable_quantstats=True,
        benchmark_symbol="{benchmark}",
        auto_save_report=True,
        auto_open_report=False,
    )

    runner = BacktestRunner(
        config=config,
        enable_plot=True,
        plot_style="{plot_style}",
    )

    print("\n回测参数:")
    # ... 参数详情

    print("\n开始回测...")

    result = runner.run(
        strategy={strategy_class},
        symbols=symbols,
        start="{start_date}",
        end="{end_date}",
        initial_cash=config.initial_cash,
        strategy_params={strategy_params_dict}
    )

    # 结果展示
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    # ... 结果详情

    print("\n" + "=" * 60)
    print("策略说明")
    print("=" * 60)
    print("""
{策略详细说明}
""")


if __name__ == "__main__":
    main()
```

### 步骤 3：结果展示格式

生成的 runner 必须包含以下结果展示：

```python
# 基本结果
print(f"\n策略名称: {result.strategy_name}")
print(f"回测区间: {result.start_date} ~ {result.end_date}")
print(f"回测时长: {result.duration_seconds:.2f} 秒")

# 收益指标
print("\n收益指标:")
print(f"  初始资金: {result.initial_cash:,.2f} 元")
print(f"  最终资产: {result.final_value:,.2f} 元")
print(f"  总收益:   {result.final_value - result.initial_cash:+,.2f} 元")
print(f"  收益率:   {result.return_pct:+.2%}")

# 风险指标
print("\n风险指标:")
print(f"  最大回撤: {result.calculate_max_drawdown():.2%}")
print(f"  夏普比率: {result.calculate_sharpe_ratio():.2f}")

# 交易统计
print("\n交易统计:")
print(f"  总交易次数: {result.total_trades}")
print(f"  胜率:       {result.win_rate:.1%}")
print(f"  盈亏比:     {result.profit_factor:.2f}")

# 分析器结果
if result.analyzer_results:
    print("\n分析器结果:")
    print(f"  SQN:         {result.analyzer_results.get('sqn', 0):.2f}")
    print(f"  BT夏普比率:  {result.analyzer_results.get('sharpe_ratio', 0):.2f}")

# 输出文件
if result.log_files:
    print("\n输出文件:")
    for name, path in result.log_files.items():
        print(f"  {name}: {path}")
```

## 完整示例

用户输入：
> 为双均线交叉策略生成一个 runner，使用平安银行和万科，回测 2024 年数据，初始资金 50 万

生成的 runner (`run_sma_cross.py`)：

```python
"""
双均线交叉策略运行示例

演示如何运行 SMA 双均线交叉策略的回测。
短期均线上穿长期均线买入，下穿卖出。
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date
from trader_center.backtest import BacktestRunner, BacktestConfig
from trader_center.backtest.strategy.examples import SmaCrossStrategy


def main():
    print("=" * 60)
    print("双均线交叉策略回测")
    print("=" * 60)

    print("\n策略配置:")
    print("  快线周期: 5日")
    print("  慢线周期: 20日")

    symbols = ["000001.SZ", "000002.SZ"]

    config = BacktestConfig(
        initial_cash=500000,
        auto_save_trades=True,
        auto_save_plot=True,
        enable_quantstats=True,
        benchmark_symbol="000300.SH",
        auto_save_report=True,
        auto_open_report=False,
    )

    runner = BacktestRunner(
        config=config,
        enable_plot=True,
        plot_style="line",
    )

    print("\n回测参数:")
    print(f"  初始资金: {config.initial_cash:,.0f} 元")
    print(f"  回测区间: 2024-01-01 ~ 2024-12-31")
    print(f"  股票池: 平安银行(000001.SZ), 万科A(000002.SZ)")

    print("\n开始回测...")

    result = runner.run(
        strategy=SmaCrossStrategy,
        symbols=symbols,
        start="2024-01-01",
        end="2024-12-31",
        initial_cash=config.initial_cash,
        strategy_params={'fast': 5, 'slow': 20}
    )

    # ... 结果展示代码 ...


if __name__ == "__main__":
    main()
```

## 策略说明部分

每个生成的 runner 必须包含详细的策略说明，格式如下：

```
策略说明
============================================================

该策略实现了{策略名称}：

1. 策略逻辑
   - {逻辑点 1}
   - {逻辑点 2}
   - {逻辑点 3}

2. 交易规则
   - 买入条件：{条件描述}
   - 卖出条件：{条件描述}
   - 仓位管理：{管理方式}

3. 参数说明
   - {参数1}: {说明} (默认: {值})
   - {参数2}: {说明} (默认: {值})

扩展建议:
- {建议 1}
- {建议 2}
- {建议 3}
```

## 使用方式

生成 runner 后，用户可以：

1. **直接运行**：
   ```bash
   python backtest_runner/run_sma_cross.py
   ```

2. **修改参数**：编辑文件中的配置部分

3. **扩展功能**：基于生成的模板添加自定义逻辑

## 注意事项

1. 所有生成的 runner 必须包含 `sys.path.insert` 以确保使用当前开发代码
2. 配置参数必须明确展示给用户
3. 结果输出必须包含收益、风险、交易统计三个维度
4. 策略说明必须包含逻辑描述、交易规则、参数说明
5. 必须提供扩展建议帮助用户后续优化
