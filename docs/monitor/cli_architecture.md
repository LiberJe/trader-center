# Monitor CLI 架构文档

## 概述

Monitor CLI 采用可扩展的任务路由架构，支持动态发现和执行 tasks 目录下的任务。

## 核心组件

### 1. BaseTask (base_task.py)

所有任务必须继承的抽象基类，定义标准接口：
- `name`: 任务唯一标识
- `description`: 任务描述
- `category`: 任务分类
- `run(**kwargs)`: 执行逻辑
- `validate_params(**kwargs)`: 参数验证
- `format_output(result, **options)`: 格式化输出

### 2. TaskRouter (task_router.py)

负责任务注册、发现和执行：
- `register(task_class)`: 注册任务
- `execute(name, **kwargs)`: 执行任务
- `auto_discover()`: 自动发现 tasks/ 下的任务
- `get_task_router()`: 获取单例

### 3. CLI (cli.py)

通用命令行入口：
- `python -m trader_center.monitor --list`: 列出任务
- `python -m trader_center.monitor <task_name>`: 执行任务
- 支持 `--date`, `--top`, `--output` 等通用参数

## 添加新任务

### 方式1: 复制模板 (推荐)

```bash
cp -r trader_center/monitor/tasks/_template_ \
      trader_center/monitor/tasks/my_task
```

修改 `task.py` 中的类属性即可。

### 方式2: 手动创建

1. 创建目录 `tasks/my_task/`
2. 创建 `task.py` 实现 BaseTask 子类
3. (可选) 创建 `formatter.py` 处理输出
4. (可选) 在 `tasks/__init__.py` 中导入

Auto-discover 会自动找到符合规范的类。

## 任务目录结构

```
tasks/
├── __init__.py           # 导出 TASK_REGISTRY
├── fund_flow/            # 资金流向任务
│   ├── __init__.py
│   ├── task.py          # FundFlowTask 实现
│   └── formatter.py     # 专用格式化器
├── market_hotspot/       # 市场热点任务 (示例)
│   ├── __init__.py
│   └── task.py
└── _template_/          # 任务模板
    ├── __init__.py
    ├── task.py
    └── formatter.py
```

## 向后兼容

原有的 API 仍然可用：

```python
from trader_center.monitor import summarize_daily_fund_flow

result = summarize_daily_fund_flow()  # 仍然工作
```
