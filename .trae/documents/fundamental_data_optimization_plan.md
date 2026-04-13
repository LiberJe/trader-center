# 基本面数据获取优化计划

## 一、问题分析

### 当前问题
1. **API接口问题**: 
   - `stock_a_lg_indicator` 不存在
   - `stock_financial_analysis_indicator` 返回空数据

2. **字段映射不完整**: 数据字段未正确映射到因子所需字段

3. **数据源单一**: 只使用了一个数据源，缺少备选

### 发现的可用接口
akshare 1.18.9 版本中可用的财务数据接口：

| 接口名称 | 功能 | 数据内容 |
|----------|------|----------|
| `stock_balance_sheet_by_report_em` | 资产负债表 | 总资产、总负债、流动资产、流动负债、货币资金等 |
| `stock_profit_sheet_by_report_em` | 利润表 | 营业收入、净利润、毛利率、净利率、PE、PB、PS等 |
| `stock_cash_flow_sheet_by_report_em` | 现金流量表 | 经营现金流、投资现金流、筹资现金流等 |
| `stock_financial_report_sina` | 财务报表(新浪) | 资产负债表、利润表、现金流量表 |

### 利润表接口返回的关键字段
```
营业收入, 营业成本, 营业利润, 利润总额, 净利润,
基本每股收益, 市盈率, 市净率, 市销率, 市现率,
毛利率, 净利率, 总资产周转率
```

### 资产负债表接口返回的关键字段
```
资产, 货币资金, 应收账款, 存货, 流动资产, 非流动资产,
总负债, 流动负债, 非流动负债, 所有者权益
```

## 二、优化方案

### 步骤1: 重写 DataHub 基本面数据获取函数

更新 `trader_center/data_hub/__init__.py` 中的函数：

1. **get_balance_sheet(symbol)** - 获取资产负债表
   - 使用 `stock_balance_sheet_by_report_em`
   - 映射字段: 总资产、总负债、流动资产、流动负债、货币资金、存货等

2. **get_profit_sheet(symbol)** - 获取利润表
   - 使用 `stock_profit_sheet_by_report_em`
   - 映射字段: 营业收入、净利润、PE、PB、PS、毛利率、净利率等

3. **get_cashflow_sheet(symbol)** - 获取现金流量表
   - 使用 `stock_cash_flow_sheet_by_report_em`
   - 映射字段: 经营现金流、投资现金流、自由现金流等

4. **get_fundamental_data(symbol)** - 综合获取基本面数据
   - 合并三张报表数据
   - 标准化字段名称
   - 返回完整的因子计算所需数据

### 步骤2: 创建字段映射表

```python
FIELD_MAPPING = {
    # 利润表字段
    '日期': 'date',
    '营业收入': 'revenue',
    '营业成本': 'cost_of_goods',
    '净利润': 'net_income',
    '基本每股收益': 'eps',
    '市盈率': 'pe_ratio',
    '市净率': 'pb_ratio',
    '市销率': 'ps_ratio',
    '毛利率': 'gross_margin',
    '净利率': 'net_margin',
    
    # 资产负债表字段
    '资产': 'total_assets',
    '总负债': 'total_liabilities',
    '流动资产': 'current_assets',
    '流动负债': 'current_liabilities',
    '货币资金': 'cash',
    '存货': 'inventory',
    '所有者权益': 'total_equity',
    
    # 现金流量表字段
    '经营活动产生的现金流量净额': 'operating_cash_flow',
}
```

### 步骤3: 更新回测数据合并逻辑

更新 `examples/fundamental_factor_real_backtest.py` 中的数据合并函数

### 步骤4: 预期产出

1. 完整的基本面数据字段
2. 正确的因子计算结果（不同股票有不同得分）
3. 可用的多因子策略回测

### 步骤5: 验证方法

运行回测验证脚本，检查：
1. 数据字段完整性
2. 因子得分差异性
3. 策略执行正确性
