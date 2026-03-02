# Monitor CLI - A股市场观察任务执行工具

Monitor CLI 是一个可扩展的命令行工具，用于执行 A 股市场数据观察任务。采用任务路由架构，支持动态发现和执行自定义任务。

## 功能特性

- **任务路由架构** - 自动发现并执行 `tasks/` 目录下的任务
- **内置资金流向任务** - 汇总每日 A 股市场资金流向数据
- **灵活的日期支持** - 支持指定任意交易日进行数据查询
- **多种输出格式** - 支持终端输出和文件导出
- **易于扩展** - 提供任务模板，快速开发新任务

## 安装要求

```bash
# Python 3.10+
pip install akshare pandas
```

## 基本用法

### 查看可用任务

```bash
python -m trader_center.monitor --list
```

### 执行资金流向任务

```bash
# 查询今日数据
python -m trader_center.monitor fund_flow

# 查询指定日期
python -m trader_center.monitor fund_flow --date 2025-08-26
python -m trader_center.monitor fund_flow -d 20250826

# 显示前20条记录
python -m trader_center.monitor fund_flow -t 20

# 导出到文件
python -m trader_center.monitor fund_flow -o report.txt
```

### 清理资金流向数据

```bash
# 清理指定日期的所有资金流向数据
python -m trader_center.monitor clean -d 2025-08-26

# 只清理大盘资金流向数据
python -m trader_center.monitor clean -d 2025-08-26 --type market

# 只清理个股资金流向数据
python -m trader_center.monitor clean -d 2025-08-26 --type stock

# 只清理板块资金流向数据
python -m trader_center.monitor clean -d 2025-08-26 --type sector

# 清理所有日期的所有资金流向数据
python -m trader_center.monitor clean --all

# 清理所有日期的个股资金流向数据
python -m trader_center.monitor clean --all --type stock
```

**说明：**
- `clean` 命令用于删除本地存储的资金流向数据
- 清理后会自动清除相关内存缓存
- 使用 `-d` 指定日期，或使用 `--all` 清理所有日期
- 数据类型选项：`all` (默认), `market`, `stock`, `sector`
- `--all` 和 `-d` 参数必须且只能指定一个

## 命令行参数

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--list` | `-l` | 列出所有可用任务 | `--list` |
| `--date` | `-d` | 目标日期 (YYYY-MM-DD 或 YYYYMMDD) | `-d 2025-08-26` |
| `--top` | `-t` | 显示前 N 条记录 (默认: 10) | `-t 20` |
| `--output` | `-o` | 导出结果到文件 | `-o report.txt` |
| `--verbose` | `-v` | 显示详细输出 | `-v` |
| `--type` | | 数据类型 (仅用于 clean 命令) | `--type market` |
| `--all` | | 清理所有日期的数据 (仅用于 clean) | `--all` |

## 内置任务

### fund_flow - 资金流向观察任务

自动汇总当日 A 股市场资金流向数据，包括：

- **大盘资金流向** - 主力、超大单、大单、中单、小单净流入
- **个股资金流向排名** - 按净流入金额排序
- **行业板块资金流向** - 各行业板块资金流入流出情况
- **概念板块资金流向** - 各概念板块资金流入流出情况

#### 任务特性

- 自动检测非交易日，跳过非交易日查询
- 数据获取失败自动重试（最多3次）
- 支持自定义显示条数

#### 示例输出

```
============================================================
 [REPORT] A股资金流向日报 - 2025-08-26
============================================================
============================================================
 [MARKET] 大盘资金流向
============================================================

  [DATA] 主力净流入:     -125.50亿
     超大单净流入:   -45.30亿
     大单净流入:     -80.20亿
     中单净流入:     +35.80亿
     小单净流入:     +89.70亿

  [WARN]  主力资金净流出，市场情绪偏空

============================================================
 [DATA] 个股资金流向 TOP 10
============================================================

  排名   代码         名称         净流入        涨跌幅
  --------------------------------------------------
  1      000001       平安银行      +5.20亿     +2.35%
  2      000002       万科A         +3.80亿     +1.92%
  ...

============================================================
 [DONE] 执行完成
============================================================
```

## 扩展开发

### 添加新任务

#### 方式1: 复制模板（推荐）

```bash
# 复制模板目录
cp -r trader_center/monitor/tasks/_template_ \
      trader_center/monitor/tasks/my_task

# 修改 task.py 中的类属性
# - name: 任务唯一标识
# - description: 任务描述
# - category: 任务分类
# - 实现 run() 方法
```

#### 方式2: 手动创建

1. 创建目录 `tasks/my_task/`
2. 创建 `task.py` 实现 `BaseTask` 子类
3. (可选) 创建 `formatter.py` 处理输出
4. Auto-discover 会自动发现符合规范的类

#### 任务基类接口

```python
from trader_center.monitor.base_task import BaseTask
from typing import Any, Dict, Optional
from datetime import date

class MyTask(BaseTask):
    """我的自定义任务"""

    name = "my_task"                    # 必须：任务唯一标识
    description = "任务描述"             # 必须：任务描述
    category = "market_data"            # 可选：任务分类

    def run(self, target_date: Optional[date] = None, **kwargs) -> Dict[str, Any]:
        """执行任务核心逻辑

        Returns:
            {
                "status": "success" | "skipped" | "error",
                "date": date,
                # 其他任务特定数据...
            }
        """
        target_date = target_date or date.today()
        # 实现任务逻辑
        return {
            "status": "success",
            "date": target_date,
            "data": [...]
        }

    def format_output(self, result: Dict[str, Any], **options) -> str:
        """格式化输出（可选）"""
        return f"任务结果: {result}"
```

### 任务目录结构

```
tasks/
├── __init__.py              # 任务包初始化
├── fund_flow/               # 资金流向任务
│   ├── __init__.py
│   ├── task.py             # FundFlowTask 实现
│   └── formatter.py        # 专用格式化器
├── my_task/                 # 你的自定义任务
│   ├── __init__.py
│   ├── task.py
│   └── formatter.py
└── _template_/             # 任务开发模板
    ├── __init__.py
    ├── task.py
    └── formatter.py
```

## 架构说明

### 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| BaseTask | `base_task.py` | 任务抽象基类，定义标准接口 |
| TaskRouter | `task_router.py` | 任务注册、发现和执行 |
| CLI | `cli.py` | 命令行入口，参数解析 |

### 任务执行流程

```
CLI (cli.py)
    ↓
TaskRouter (task_router.py)
    ↓
Task Class (tasks/*/task.py)
    ↓
Formatter (tasks/*/formatter.py) [可选]
    ↓
Output (终端/文件)
```

## Python API 使用

除了命令行，也可以直接在 Python 代码中使用：

```python
from datetime import date
from trader_center.monitor.task_router import get_task_router

# 获取路由器（自动发现所有任务）
router = get_task_router()

# 列出可用任务
print(router.list_tasks())  # ['fund_flow', ...]

# 获取任务信息
info = router.get_task_info('fund_flow')
print(info)  # {'name': 'fund_flow', 'description': '...', 'category': '...'}

# 执行任务
result = router.execute('fund_flow', target_date=date(2025, 8, 26))
print(result['status'])  # 'success' | 'skipped' | 'error'

# 直接使用任务类
from trader_center.monitor.tasks.fund_flow import FundFlowTask

task = FundFlowTask()
result = task.run(target_date=date.today())
output = task.format_output(result, top_n=20)
print(output)
```

## 向后兼容

原有的 API 仍然可用：

```python
from trader_center.monitor import summarize_daily_fund_flow

result = summarize_daily_fund_flow()  # 仍然工作
```

## 常见问题

**Q: 如何查看任务的详细日志？**
A: 使用 `-v` 参数启用详细输出模式。

**Q: 非交易日会如何处理？**
A: 任务会自动检测非交易日并跳过，输出 `[SKIP]` 状态。

**Q: 如何添加新的输出格式？**
A: 在任务类中重写 `format_output()` 方法，或使用独立的 formatter 模块。

**Q: 任务执行失败如何排查？**
A: 使用 `-v` 参数查看详细日志，检查网络连接和数据源可用性。

**Q: 如何清理错误或过期的资金流向数据？**
A: 使用 `clean` 命令清理本地存储的数据。可以指定日期 `-d 2025-08-26` 清理该日期的数据，或使用 `--all` 清理所有日期的数据。使用 `--type` 参数可指定清理特定类型的数据（market/stock/sector）。

## 许可证

MIT License
