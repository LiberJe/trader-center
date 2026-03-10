# 因子模块目录结构重构计划

## 问题说明

当前架构中，`factor_library` 和 `factor_mining` 是两个独立的顶级模块。根据用户需求，应该将它们作为平行的子模块，统一放在一个 `factor` 大文件夹下。

## 目标架构

```
trader_center/
├── factor/                     # 因子大模块
│   ├── __init__.py
│   ├── library/                # 因子库（因子定义）
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── technical/
│   │   ├── fundamental/
│   │   └── alternative/
│   └── mining/                 # 因子挖掘（工具集）
│       ├── __init__.py
│       ├── engine.py
│       ├── preprocessing/
│       ├── analysis/
│       └── storage/
```

## 实施步骤

### Phase 1: 创建新的目录结构

#### 步骤 1.1: 创建 factor 顶级目录
- 创建 `trader_center/factor/` 目录
- 创建 `trader_center/factor/__init__.py`

#### 步骤 1.2: 移动因子库模块
- 将 `trader_center/factor_library/` 重命名为 `trader_center/factor/library/`
- 更新 `library/__init__.py` 的导入路径

#### 步骤 1.3: 移动因子挖掘模块
- 将 `trader_center/factor_mining/` 重命名为 `trader_center/factor/mining/`
- 更新 `mining/__init__.py` 的导入路径

### Phase 2: 更新导入路径

#### 步骤 2.1: 更新因子库内部导入
- 更新 `library/base.py` 中的导入（如有）
- 更新 `library/registry.py` 中的导入
- 更新 `library/technical/*.py` 中的导入
- 更新 `library/fundamental/*.py` 中的导入
- 更新 `library/alternative/*.py` 中的导入

#### 步骤 2.2: 更新因子挖掘内部导入
- 更新 `mining/engine.py` 中的导入
  - `from trader_center.factor_library import FactorRegistry` 
  - 改为 `from trader_center.factor.library import FactorRegistry`
- 更新 `mining/storage/factor_store.py` 中的导入
- 更新 `mining/preprocessing/*.py` 中的导入
- 更新 `mining/analysis/*.py` 中的导入

#### 步骤 2.3: 更新 factor 顶级 __init__.py
- 导出常用接口：
  ```python
  from trader_center.factor.library import BaseFactor, FactorRegistry
  from trader_center.factor.mining import FactorEngine
  ```

### Phase 3: 更新测试和示例

#### 步骤 3.1: 更新测试文件
- 更新 `tests/test_factor_system.py` 中的所有导入路径
  - `from trader_center.factor_library` → `from trader_center.factor.library`
  - `from trader_center.factor_mining` → `from trader_center.factor.mining`

#### 步骤 3.2: 更新示例文件
- 更新 `examples/factor_system_example.py` 中的所有导入路径

### Phase 4: 更新文档

#### 步骤 4.1: 更新 README
- 更新 `trader_center/factor/library/README.md` 中的模块结构说明
- 更新所有示例代码中的导入路径

#### 步骤 4.2: 更新计划文档
- 更新 `.trae/documents/factor_mining_system_plan.md` 中的架构说明

### Phase 5: 清理工作

#### 步骤 5.1: 删除旧目录
- 确认所有文件已正确移动后，删除旧的空目录

#### 步骤 5.2: 验证功能
- 运行测试确保所有功能正常
- 运行示例确保代码可执行

## 导入路径变更对照表

| 旧路径 | 新路径 |
|--------|--------|
| `trader_center.factor_library` | `trader_center.factor.library` |
| `trader_center.factor_library.base` | `trader_center.factor.library.base` |
| `trader_center.factor_library.registry` | `trader_center.factor.library.registry` |
| `trader_center.factor_library.technical.momentum` | `trader_center.factor.library.technical.momentum` |
| `trader_center.factor_mining` | `trader_center.factor.mining` |
| `trader_center.factor_mining.engine` | `trader_center.factor.mining.engine` |
| `trader_center.factor_mining.storage` | `trader_center.factor.mining.storage` |
| `trader_center.factor_mining.preprocessing` | `trader_center.factor.mining.preprocessing` |
| `trader_center.factor_mining.analysis` | `trader_center.factor.mining.analysis` |

## 新的 __init__.py 内容

### factor/__init__.py
```python
"""
因子模块

提供因子定义、计算、分析和存储功能。
"""

from trader_center.factor.library import (
    BaseFactor,
    FactorRegistry,
    register_factor,
    get_factor,
    list_factors,
)
from trader_center.factor.mining import FactorEngine

__all__ = [
    'BaseFactor',
    'FactorRegistry',
    'register_factor',
    'get_factor',
    'list_factors',
    'FactorEngine',
]
```

### factor/library/__init__.py
```python
"""
因子库

提供各类因子的定义和注册功能。
"""

from .base import BaseFactor
from .registry import FactorRegistry, register_factor, get_factor, list_factors

__all__ = [
    'BaseFactor',
    'FactorRegistry',
    'register_factor',
    'get_factor',
    'list_factors',
]
```

### factor/mining/__init__.py
```python
"""
因子挖掘

提供因子计算、分析、预处理和存储功能。
"""

from .engine import FactorEngine

__all__ = ['FactorEngine']
```

## 风险评估

1. **导入路径变更**: 所有使用旧路径的代码都需要更新
2. **测试覆盖**: 需要确保所有测试在新路径下通过
3. **向后兼容**: 如果有外部代码依赖旧路径，会受到影响

## 验证清单

- [ ] 所有文件已正确移动到新目录
- [ ] 所有导入路径已更新
- [ ] 所有测试通过
- [ ] 示例代码可执行
- [ ] 文档已更新
- [ ] 旧目录已清理

## 时间估算

- Phase 1 (目录结构): 10分钟
- Phase 2 (更新导入): 15分钟
- Phase 3 (测试示例): 10分钟
- Phase 4 (文档更新): 5分钟
- Phase 5 (清理验证): 10分钟

**总计**: 约50分钟
