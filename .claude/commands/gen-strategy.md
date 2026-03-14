# 量化策略生成

根据用户需求自动生成量化交易策略，并执行回测验证。

## 代码生成目录规则

**重要**: 所有策略必须按照 [AGENT.md](../../AGENT.md) 中定义的目录结构生成。

- **策略路径**: `trader_center/backtest/strategy/{strategy-name}/`
- **必须包含**: `index.py`、`config.py`、`README.md`、`__init__.py`
- **必须更新**: `trader_center/backtest/strategy/__init__.py`

## 使用方式

/gen-strategy 帮我写一个MACD策略，要求夏普比率>1.2，最大回撤<15%，回测平安银行2024年数据

## 执行步骤

1. **解析目标**：提取优化目标（sharpe、max_drawdown、total_return）和回测参数
2. **生成配置**：在 `.claude/tmp/strategy-loop/` 创建 `strategy-goals.json`
3. **生成策略**：触发 strategy-generator skill 创建策略目录结构
4. **执行回测**：使用 backtest-runner 验证策略表现
5. **结果对比**：检查是否达到优化目标

## 参数解析规则

### 策略类型识别
- 双均线/均线交叉/SMA → `SmaCrossStrategy`
- RSI → `RsiStrategy`
- MACD → `MacdStrategy`
- KDJ → `KdjStrategy`
- 布林带/Bollinger → `BollingerStrategy`
- 买入持有/基准 → `BuyAndHoldStrategy`

### 优化目标解析
- **夏普比率**："夏普>X"、"sharpe>X"、"夏普比率>X"
- **最大回撤**："回撤<X%"、"max_drawdown<X%"、"最大回撤<X%"
  - 注意：回撤存储为负数（15% → -0.15）
- **收益率**："收益>X%"、"return>X%"、"收益率>X%"
  - 百分比转换为小数（30% → 0.30）

### 回测参数解析
- **股票代码**：
  - 自动识别格式如 `000001.SZ`、`600000.SH`
  - 中文名称如 "平安银行"、"贵州茅台" 需映射为代码
- **时间范围**：
  - 年份格式：`2024年` → `2024-01-01` 到 `2024-12-31`
  - 日期范围：`2024-01-01到2024-12-31`

## Workflow

当用户执行 `/gen-strategy` 命令时，按以下步骤处理：

### Step 1: 解析用户输入

从用户输入中提取以下信息：

```python
# 示例输入：写一个双均线策略，夏普>1.0，回撤<20%，测试000001.SZ从2024-01-01到2024-12-31

parsed = {
    "strategy_type": "SmaCrossStrategy",  # 从"双均线"识别
    "strategy_name": "sma_cross_strategy",  # snake_case
    "goals": {
        "sharpe": {"min": 1.0, "max": None},
        "max_drawdown": {"min": None, "max": -0.20},  # 20%回撤转为-0.20
        "total_return": {"min": None, "max": None}
    },
    "backtest_params": {
        "symbol": "000001.SZ",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "initial_cash": 100000
    }
}
```

### Step 2: 生成 strategy-goals.json

创建 `.claude/tmp/strategy-loop/strategy-goals.json`：

```json
{
  "target_strategy": "sma_cross_strategy",
  "goals": {
    "total_return": {"min": null, "max": null},
    "max_drawdown": {"min": null, "max": -0.20},
    "sharpe": {"min": 1.0, "max": null}
  },
  "check_latest_n": 1,
  "open_report_on_success": true,
  "prompt_on_fail": "当前策略 '{strategy}' 未达到目标：\n{failures}\n\n请分析并优化策略：\n1. 查看回测结果和交易日志\n2. 识别问题根源\n3. 调整策略参数或逻辑\n4. 重新运行回测验证改进效果",
  "prompt_on_success": "策略 '{strategy}' 已达标！\n\n最终结果：\n{results}\n\n正在打开报告文件..."
}
```

### Step 3: 触发策略生成

根据解析的策略类型，构造请求触发 `strategy-generator` skill：

- 如果用户请求"MACD策略" → 生成 MACD 金叉死叉策略
- 如果用户请求"双均线策略" → 生成 SMA 交叉策略
- 如果用户请求"RSI策略" → 生成 RSI 超买超卖策略

**生成目标**: `trader_center/backtest/strategy/{strategy-name}/` 目录

**必须生成的文件**:
- `index.py` - 策略主代码
- `config.py` - 策略配置
- `README.md` - 策略说明
- `__init__.py` - 导出策略类

**必须更新**: `trader_center/backtest/strategy/__init__.py` 添加新策略导入

### Step 4: 执行回测

使用 `backtest-runner` skill 执行回测：

```bash
python -m trader_center.backtest \
    --strategy trader_center.backtest.strategy.{strategy_name}.{StrategyClass} \
    --symbol {symbol} \
    --start {start} \
    --end {end} \
    --cash 100000 \
    --open-report
```

### Step 5: 对比结果与目标

读取回测结果，与 `strategy-goals.json` 中的目标对比：

```python
def check_goals(results, goals):
    failures = []
    for metric, bounds in goals.items():
        value = results.get(metric)
        if bounds["min"] is not None and value < bounds["min"]:
            failures.append(f"{metric}: {value:.2%} < 目标 {bounds['min']:.2%}")
        if bounds["max"] is not None and value > bounds["max"]:
            failures.append(f"{metric}: {value:.2%} > 目标 {bounds['max']:.2%}")
    return failures
```

输出结论：
- **达标**：显示成功消息，打开报告
- **未达标**：显示失败原因，提示优化建议

## 示例

### 示例 1：MACD 策略

用户输入：
```
/gen-strategy 写一个MACD策略，夏普>1.5，最大回撤<10%，测试000001.SZ 2024年数据
```

执行流程：
1. 解析：strategy_type="MacdStrategy", strategy_name="macd_strategy", sharpe>1.5, max_drawdown<-0.10
2. 生成 strategy-goals.json
3. 调用 strategy-generator 生成目录 `trader_center/backtest/strategy/macd_strategy/`
4. 生成 4 个文件（index.py, config.py, README.md, __init__.py）
5. 更新父级 `__init__.py` 导入
6. 调用 backtest-runner 执行回测
7. 对比结果：输出是否达标

### 示例 2：双均线策略

用户输入：
```
/gen-strategy 双均线策略，收益率>20%，回撤<15%，回测600519.SH从2024-01-01到2024-12-31
```

执行流程：
1. 解析：strategy_type="SmaCrossStrategy", strategy_name="sma_cross_strategy", total_return>0.20, max_drawdown<-0.15
2. 生成 strategy-goals.json
3. 调用 strategy-generator 生成目录 `trader_center/backtest/strategy/sma_cross_strategy/`
4. 生成 4 个文件（index.py, config.py, README.md, __init__.py）
5. 更新父级 `__init__.py` 导入
6. 调用 backtest-runner 执行回测
7. 对比结果：输出是否达标

## 实现代码

```python
import json
import os
import re
from datetime import datetime
from pathlib import Path

# 确保目录存在
STRATEGY_LOOP_DIR = Path(".claude/tmp/strategy-loop")
STRATEGY_LOOP_DIR.mkdir(parents=True, exist_ok=True)

# 策略类型映射
STRATEGY_MAP = {
    "双均线": "SmaCrossStrategy",
    "均线": "SmaCrossStrategy",
    "sma": "SmaCrossStrategy",
    "均线交叉": "SmaCrossStrategy",
    "rsi": "RsiStrategy",
    "RSI": "RsiStrategy",
    "macd": "MacdStrategy",
    "MACD": "MacdStrategy",
    "kdj": "KdjStrategy",
    "KDJ": "KdjStrategy",
    "布林带": "BollingerStrategy",
    "bollinger": "BollingerStrategy",
    "买入持有": "BuyAndHoldStrategy",
    "基准": "BuyAndHoldStrategy",
}

# 股票名称映射（常见股票）
STOCK_MAP = {
    "平安银行": "000001.SZ",
    "万科": "000002.SZ",
    "贵州茅台": "600519.SH",
    "五粮液": "000858.SZ",
    "招商银行": "600036.SH",
    "中国平安": "601318.SH",
    "宁德时代": "300750.SZ",
    "比亚迪": "002594.SZ",
    "中信证券": "600030.SH",
    "东方财富": "300059.SZ",
}

def to_snake_case(name: str) -> str:
    """将策略类名转换为 snake_case 目录名"""
    # 移除 Strategy 后缀
    name = name.replace("Strategy", "")
    # PascalCase 转 snake_case
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result) + "_strategy"

def parse_strategy_input(user_input: str) -> dict:
    """解析用户输入，提取策略类型、目标和回测参数"""
    result = {
        "strategy_type": None,
        "strategy_name": None,
        "goals": {
            "total_return": {"min": None, "max": None},
            "max_drawdown": {"min": None, "max": None},
            "sharpe": {"min": None, "max": None},
        },
        "backtest_params": {
            "symbol": "000001.SZ",  # 默认平安银行
            "start": "2024-01-01",
            "end": "2024-12-31",
            "initial_cash": 100000,
        }
    }

    # 解析策略类型
    for key, strategy in STRATEGY_MAP.items():
        if key in user_input:
            result["strategy_type"] = strategy
            result["strategy_name"] = to_snake_case(strategy)
            break

    # 默认策略
    if not result["strategy_type"]:
        result["strategy_type"] = "SmaCrossStrategy"
        result["strategy_name"] = "sma_cross_strategy"

    # 解析夏普比率目标
    sharpe_match = re.search(r'夏普(?:比率)?[>≥](\d+(?:\.\d+)?)', user_input)
    if sharpe_match:
        result["goals"]["sharpe"]["min"] = float(sharpe_match.group(1))

    sharpe_match2 = re.search(r'sharpe[>≥](\d+(?:\.\d+)?)', user_input, re.IGNORECASE)
    if sharpe_match2:
        result["goals"]["sharpe"]["min"] = float(sharpe_match2.group(1))

    # 解析最大回撤目标
    dd_match = re.search(r'(?:最大)?回撤[<≤](\d+(?:\.\d+)?)%?', user_input)
    if dd_match:
        result["goals"]["max_drawdown"]["max"] = -float(dd_match.group(1)) / 100

    dd_match2 = re.search(r'max_drawdown[<≤](\d+(?:\.\d+)?)%?', user_input, re.IGNORECASE)
    if dd_match2:
        result["goals"]["max_drawdown"]["max"] = -float(dd_match2.group(1)) / 100

    # 解析收益率目标
    ret_match = re.search(r'(?:总)?收益(?:率)?[>≥](\d+(?:\.\d+)?)%?', user_input)
    if ret_match:
        result["goals"]["total_return"]["min"] = float(ret_match.group(1)) / 100

    ret_match2 = re.search(r'return[>≥](\d+(?:\.\d+)?)%?', user_input, re.IGNORECASE)
    if ret_match2:
        result["goals"]["total_return"]["min"] = float(ret_match2.group(1)) / 100

    # 解析股票代码
    symbol_match = re.search(r'(\d{6}\.(?:SZ|SH|sz|sh))', user_input)
    if symbol_match:
        result["backtest_params"]["symbol"] = symbol_match.group(1).upper()
    else:
        # 检查股票名称
        for name, code in STOCK_MAP.items():
            if name in user_input:
                result["backtest_params"]["symbol"] = code
                break

    # 解析时间范围
    # 年份格式：2024年
    year_match = re.search(r'(\d{4})年', user_input)
    if year_match:
        year = year_match.group(1)
        result["backtest_params"]["start"] = f"{year}-01-01"
        result["backtest_params"]["end"] = f"{year}-12-31"

    # 日期范围格式：2024-01-01到2024-12-31
    date_range_match = re.search(r'(\d{4}-\d{2}-\d{2})[到~-](\d{4}-\d{2}-\d{2})', user_input)
    if date_range_match:
        result["backtest_params"]["start"] = date_range_match.group(1)
        result["backtest_params"]["end"] = date_range_match.group(2)

    return result

def generate_strategy_goals(parsed: dict) -> Path:
    """生成 strategy-goals.json 文件"""
    goals_file = STRATEGY_LOOP_DIR / "strategy-goals.json"

    # 过滤掉未设置的目标
    filtered_goals = {}
    for metric, bounds in parsed["goals"].items():
        if bounds["min"] is not None or bounds["max"] is not None:
            filtered_goals[metric] = bounds

    goals_data = {
        "target_strategy": parsed["strategy_name"],
        "goals": filtered_goals,
        "check_latest_n": 1,
        "open_report_on_success": True,
        "prompt_on_fail": "当前策略 '{strategy}' 未达到目标：\n{failures}\n\n请分析并优化策略：\n1. 查看回测结果和交易日志\n2. 识别问题根源\n3. 调整策略参数或逻辑\n4. 重新运行回测验证改进效果",
        "prompt_on_success": "策略 '{strategy}' 已达标！\n\n最终结果：\n{results}\n\n正在打开报告文件..."
    }

    with open(goals_file, 'w', encoding='utf-8') as f:
        json.dump(goals_data, f, indent=2, ensure_ascii=False)

    return goals_file

def check_goals_against_results(results: dict, goals: dict) -> list:
    """检查回测结果是否达到目标"""
    failures = []

    metric_map = {
        "total_return": "return_pct",
        "max_drawdown": "max_drawdown",
        "sharpe": "sharpe_ratio"
    }

    for metric, bounds in goals.items():
        result_key = metric_map.get(metric, metric)
        value = results.get(result_key)

        if value is None:
            continue

        if bounds["min"] is not None and value < bounds["min"]:
            failures.append(f"{metric}: {value:.2%} < 目标 {bounds['min']:.2%}")
        if bounds["max"] is not None and value > bounds["max"]:
            failures.append(f"{metric}: {value:.2%} > 目标 {bounds['max']:.2%}")

    return failures

# 主执行流程
user_input = ""  # 用户输入将由 Claude 填充

# 1. 解析输入
parsed = parse_strategy_input(user_input)
print(f"解析结果：策略={parsed['strategy_type']}, 目录={parsed['strategy_name']}, 股票={parsed['backtest_params']['symbol']}")
print(f"目标：{json.dumps(parsed['goals'], indent=2, ensure_ascii=False)}")

# 2. 生成 goals 文件
goals_file = generate_strategy_goals(parsed)
print(f"已生成配置：{goals_file}")

# 3. 触发策略生成（Claude 将使用 strategy-generator skill）
strategy_request = f"""请生成一个{parsed['strategy_type']}策略代码，基于 trader_center 框架。

必须遵守 AGENT.md 中的目录结构规则：
1. 创建目录：trader_center/backtest/strategy/{parsed['strategy_name']}/
2. 创建 index.py（策略主代码）
3. 创建 config.py（策略配置）
4. 创建 README.md（策略说明）
5. 创建 __init__.py（导出策略类）
6. 在 trader_center/backtest/strategy/__init__.py 中添加导入

要求：
- 继承 BaseStrategy
- 包含完整的策略逻辑
- 使用中文注释
- 命名规范：目录={parsed['strategy_name']}, 类名={parsed['strategy_type']}"""

# 4. 触发回测（Claude 将使用 backtest-runner skill）
backtest_request = f"""请使用 backtest-runner 执行回测：
- 策略：{parsed['strategy_type']}
- 目录：trader_center.backtest.strategy.{parsed['strategy_name']}
- 股票：{parsed['backtest_params']['symbol']}
- 开始：{parsed['backtest_params']['start']}
- 结束：{parsed['backtest_params']['end']}
- 初始资金：100000
- 打开报告查看结果"""

print("\n=== 执行流程 ===")
print("1. 已解析用户输入")
print("2. 已生成 strategy-goals.json")
print("3. 请使用 strategy-generator 生成策略目录结构")
print("4. 请使用 backtest-runner 执行回测验证")
```

## Claude 执行指令

当用户执行 `/gen-strategy` 时，Claude 应该：

1. **解析阶段**：运行解析代码，提取所有参数
2. **生成配置**：创建 `.claude/tmp/strategy-loop/strategy-goals.json`
3. **生成策略**：使用 `Skill: strategy-generator` 生成完整策略目录结构（4个文件）
4. **更新导入**：在 `trader_center/backtest/strategy/__init__.py` 中添加新策略导入
5. **执行回测**：使用 `Skill: backtest-runner` 运行回测
6. **结果验证**：读取回测结果，与目标对比，输出结论

注意：
- 策略必须生成在独立目录中，不能放在 `generated/` 下
- 必须创建完整的 4 个文件（index.py, config.py, README.md, __init__.py）
- 必须更新父级 `__init__.py` 导入
- 如果策略目录已存在，询问用户是否覆盖
- 回测完成后，根据 strategy-goals.json 中的目标检查结果
- 达标时显示成功消息并可选择打开报告
- 未达标时显示失败原因并建议优化方向
