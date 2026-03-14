# Agent 代码生成目录规范

本文件定义所有 Agent 在生成代码时必须遵守的目录结构规则。

## 策略生成规则

**强制路径**: `trader_center/backtest/strategy/{strategy-name}/`

**目录结构**:
```
{strategy-name}/
├── __init__.py        # 导出策略类
├── index.py           # 策略主代码（必须）
├── config.py          # 策略配置（必须）
└── README.md          # 策略说明（必须）
```

**命名规范**:
- 目录名: snake_case，如 `macd_strategy`
- 策略类名: PascalCase + Strategy，如 `MacdStrategy`
- name 属性: snake_case，如 `name = "macd_strategy"`

**必需操作**:
1. 创建策略目录
2. 创建 `index.py` 包含策略类
3. 创建 `config.py` 包含参数配置
4. 创建 `README.md` 说明策略逻辑
5. 创建 `__init__.py` 导出策略
6. 在 `trader_center/backtest/strategy/__init__.py` 中导入新策略

## Runner 生成规则

**强制路径**: `./backtest_runner/`（项目根目录）

**目录结构**:
```
backtest_runner/
├── __init__.py
├── runner.py
├── config.py
└── README.md
```

**用途**: 存放自定义回测运行器实现
