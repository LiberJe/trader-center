# Bias因子研究计划

## 1. 仓库研究结论

通过分析代码库结构，发现：

- **因子系统架构**：采用模块化设计，所有因子继承自 `BaseFactor` 基类
- **技术因子组织**：位于 `trader_center/factor/library/technical/` 目录，按功能分类
- **因子实现规范**：每个因子需要实现 `name`、`category` 属性和 `compute` 方法
- **因子注册机制**：通过 `__init__.py` 导出因子，自动注册到因子系统

## 2. Bias因子概述

Bias因子（乖离率）是一种技术分析指标，用于衡量价格与移动平均线之间的偏离程度。它可以帮助识别超买超卖状态和潜在的反转信号。

### 计算方法

Bias = (当前价格 - N日移动平均线) / N日移动平均线 × 100%

## 3. 实施计划

### 3.1 创建Bias因子实现

**文件**：`trader_center/factor/library/technical/reversal.py`

**内容**：
- 实现 `BiasFactor` 类，继承自 `BaseFactor`
- 支持自定义移动平均线周期和类型（简单/指数/加权）
- 实现 `compute` 方法计算乖离率

### 3.2 更新技术因子导出

**文件**：`trader_center/factor/library/technical/__init__.py`

**内容**：
- 导入 `BiasFactor`
- 在 `__all__` 列表中添加 `BiasFactor`

### 3.3 编写测试用例

**文件**：`tests/factor/test_technical_factors.py`

**内容**：
- 测试 `BiasFactor` 的基本计算
- 测试不同参数配置
- 测试数据验证

### 3.4 因子分析与评估

**文件**：`factor_research/bias_factor_analysis.py`

**内容**：
- 使用 `factor_research` 模块分析Bias因子
- 计算IC值和分层收益率
- 评估因子的有效性和稳定性
- 与其他技术因子进行相关性分析
- 生成详细的因子分析报告

## 4. 技术实现细节

### 4.1 BiasFactor 类设计

```python
class BiasFactor(BaseFactor):
    name = "bias"
    category = "technical"
    description = "价格乖离率因子"
    
    def __init__(self, period=20, ma_type="sma"):
        super().__init__(period=period, ma_type=ma_type)
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # 计算移动平均线
        if self.params['ma_type'] == "sma":
            ma = data['close'].rolling(self.params['period']).mean()
        elif self.params['ma_type'] == "ema":
            ma = data['close'].ewm(span=self.params['period']).mean()
        elif self.params['ma_type'] == "wma":
            weights = np.arange(1, self.params['period'] + 1)
            ma = data['close'].rolling(self.params['period']).apply(
                lambda x: np.dot(x, weights) / weights.sum()
            )
        else:
            raise ValueError(f"不支持的移动平均线类型: {self.params['ma_type']}")
        
        # 计算乖离率
        bias = (data['close'] - ma) / ma * 100
        return bias
```

### 4.2 参数验证

- `period`：必须为正整数
- `ma_type`：必须为 "sma"、"ema" 或 "wma"

## 5. 风险处理

- **数据质量**：处理缺失值和异常值
- **参数敏感性**：测试不同周期参数的表现
- **过度拟合**：使用不同时间窗口进行验证
- **计算效率**：优化大样本数据的计算性能

## 6. 预期成果

- 完成 Bias 因子的实现和集成
- 提供详细的因子分析报告
- 评估 Bias 因子在不同市场环境下的表现
- 为策略开发提供有效的技术分析工具

## 7. 后续扩展

- 实现多周期 Bias 因子组合
- 开发 Bias 因子的衍生指标
- 与其他技术因子构建复合策略
- 优化因子参数以适应不同市场特性