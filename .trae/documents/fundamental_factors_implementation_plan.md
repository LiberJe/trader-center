# 基本面因子补充实现计划

## 一、背景与目标

当前因子库技术因子覆盖全面（90+个），但基本面因子完全缺失。本计划旨在补充完整的基本面因子体系，支持多因子策略构建。

## 二、因子分类与实现清单

### 2.1 估值因子 (valuation.py)

| 因子名称 | 英文名 | 计算公式 | 理论依据 | 学术出处 |
|----------|--------|----------|----------|----------|
| 市盈率因子 | PEFactor | 股价/每股收益 | 价值异象 | Fama & French (1992) |
| 市净率因子 | PBFactor | 股价/每股净资产 | 价值异象 | Fama & French (1992) |
| 市销率因子 | PSFactor | 股价/每股销售额 | 成长估值 | Lakonishok et al. (1994) |
| 企业价值倍数 | EVEBITDAFactor | EV/EBITDA | 企业价值评估 | Damodaran (2006) |
| PEG因子 | PEGFactor | PE/盈利增长率 | 成长价值平衡 | Peter Lynch |
| 股价现金流比 | PCFFactor | 股价/每股现金流 | 现金流估值 | Sloan (1996) |

### 2.2 质量因子 (quality.py)

| 因子名称 | 英文名 | 计算公式 | 理论依据 | 学术出处 |
|----------|--------|----------|----------|----------|
| 净资产收益率 | ROEFactor | 净利润/净资产 | 盈利能力 | Novy-Marx (2013) |
| 总资产收益率 | ROAFactor | 净利润/总资产 | 盈利能力 | Novy-Marx (2013) |
| 毛利率因子 | GrossMarginFactor | (营收-成本)/营收 | 盈利质量 | Novy-Marx (2013) |
| 净利率因子 | NetMarginFactor | 净利润/营收 | 盈利质量 | Novy-Marx (2013) |
| 资产周转率 | AssetTurnoverFactor | 营收/总资产 | 运营效率 | Soliman (2008) |
| 毛利润率 | GrossProfitabilityFactor | (营收-COGS)/总资产 | 质量因子 | Novy-Marx (2013) |

### 2.3 成长因子 (growth.py)

| 因子名称 | 英文名 | 计算公式 | 理论依据 | 学术出处 |
|----------|--------|----------|----------|----------|
| 营收增长率 | RevenueGrowthFactor | (本期营收-上期营收)/上期营收 | 成长投资 | Lakonishok et al. (1994) |
| 净利润增长率 | EarningsGrowthFactor | (本期净利润-上期净利润)/上期净利润 | 成长投资 | Chan et al. (2003) |
| EPS增长率 | EPSGrowthFactor | (本期EPS-上期EPS)/上期EPS | 成长投资 | Chan et al. (2003) |
| 资产增长率 | AssetGrowthFactor | (本期资产-上期资产)/上期资产 | 资产增长效应 | Cooper et al. (2008) |
| 经营现金流增长率 | OCFGrowthFactor | (本期OCF-上期OCF)/上期OCF | 现金流增长 | Sloan (1996) |

### 2.4 财务健康因子 (financial_health.py)

| 因子名称 | 英文名 | 计算公式 | 理论依据 | 学术出处 |
|----------|--------|----------|----------|----------|
| 资产负债率 | DebtRatioFactor | 总负债/总资产 | 财务风险 | Altman (1968) |
| 流动比率 | CurrentRatioFactor | 流动资产/流动负债 | 短期偿债能力 | Altman (1968) |
| 速动比率 | QuickRatioFactor | (流动资产-存货)/流动负债 | 短期偿债能力 | Altman (1968) |
| 利息保障倍数 | InterestCoverageFactor | EBIT/利息支出 | 偿债能力 | Ohlson (1980) |
| Altman Z-Score | AltmanZScoreFactor | 综合评分模型 | 破产预警 | Altman (1968) |
| Piotroski F-Score | PiotroskiFScoreFactor | 9项指标综合评分 | 价值投资 | Piotroski (2000) |
| 现金比率 | CashRatioFactor | 现金/流动负债 | 流动性 | Ohlson (1980) |

### 2.5 现金流因子 (cashflow.py)

| 因子名称 | 英文名 | 计算公式 | 理论依据 | 学术出处 |
|----------|--------|----------|----------|----------|
| 自由现金流收益率 | FCFYieldFactor | FCF/市值 | 现金流价值 | Sloan (1996) |
| 经营现金流/净利润 | OCFToNetIncomeFactor | OCF/净利润 | 盈利质量 | Sloan (1996) |
| 现金循环周期 | CashConversionCycleFactor | 应收周转天数+存货周转天数-应付周转天数 | 运营效率 | Richards & Laughlin (1980) |
| 资本支出比率 | CapExRatioFactor | 资本支出/总资产 | 投资强度 | Titman et al. (2004) |

### 2.6 分红因子 (dividend.py)

| 因子名称 | 英文名 | 计算公式 | 理论依据 | 学术出处 |
|----------|--------|----------|----------|----------|
| 股息率 | DividendYieldFactor | 每股股息/股价 | 分红溢价 | Litzenberger & Ramaswamy (1979) |
| 分红率 | PayoutRatioFactor | 每股股息/每股收益 | 分红政策 | Fama & French (2001) |
| 股息增长率 | DividendGrowthFactor | (本期股息-上期股息)/上期股息 | 分红成长 | Grullon et al. (2002) |

## 三、实现步骤

### 步骤1：创建基本面因子目录结构

```
trader_center/factor/library/fundamental/
├── __init__.py          # 导出所有基本面因子
├── valuation.py         # 估值因子（6个）
├── quality.py           # 质量因子（6个）
├── growth.py            # 成长因子（5个）
├── financial_health.py  # 财务健康因子（7个）
├── cashflow.py          # 现金流因子（4个）
└── dividend.py          # 分红因子（3个）
```

### 步骤2：实现估值因子 (valuation.py)

- PEFactor：市盈率因子
- PBFactor：市净率因子
- PSFactor：市销率因子
- EVEBITDAFactor：企业价值倍数因子
- PEGFactor：PEG因子
- PCFFactor：股价现金流比因子

### 步骤3：实现质量因子 (quality.py)

- ROEFactor：净资产收益率因子
- ROAFactor：总资产收益率因子
- GrossMarginFactor：毛利率因子
- NetMarginFactor：净利率因子
- AssetTurnoverFactor：资产周转率因子
- GrossProfitabilityFactor：毛利润率因子

### 步骤4：实现成长因子 (growth.py)

- RevenueGrowthFactor：营收增长率因子
- EarningsGrowthFactor：净利润增长率因子
- EPSGrowthFactor：EPS增长率因子
- AssetGrowthFactor：资产增长率因子
- OCFGrowthFactor：经营现金流增长率因子

### 步骤5：实现财务健康因子 (financial_health.py)

- DebtRatioFactor：资产负债率因子
- CurrentRatioFactor：流动比率因子
- QuickRatioFactor：速动比率因子
- InterestCoverageFactor：利息保障倍数因子
- AltmanZScoreFactor：Altman Z-Score因子
- PiotroskiFScoreFactor：Piotroski F-Score因子
- CashRatioFactor：现金比率因子

### 步骤6：实现现金流因子 (cashflow.py)

- FCFYieldFactor：自由现金流收益率因子
- OCFToNetIncomeFactor：经营现金流/净利润因子
- CashConversionCycleFactor：现金循环周期因子
- CapExRatioFactor：资本支出比率因子

### 步骤7：实现分红因子 (dividend.py)

- DividendYieldFactor：股息率因子
- PayoutRatioFactor：分红率因子
- DividendGrowthFactor：股息增长率因子

### 步骤8：更新 __init__.py 导出

更新 `fundamental/__init__.py` 导出所有因子类。

### 步骤9：编写单元测试

创建 `tests/test_fundamental_factors.py` 测试所有基本面因子。

### 步骤10：更新因子库文档

更新 README.md 添加基本面因子说明。

## 四、数据字段要求

基本面因子需要以下数据字段支持：

```python
# 估值数据
'market_cap',        # 总市值
'pe_ratio',          # 市盈率
'pb_ratio',          # 市净率
'ps_ratio',          # 市销率
'ev',                # 企业价值
'ebitda',            # EBITDA
'eps',               # 每股收益
'eps_growth',        # EPS增长率
'price',             # 股价
'shares_outstanding', # 流通股数

# 财务数据
'revenue',           # 营业收入
'cost_of_goods',     # 营业成本
'net_income',        # 净利润
'total_assets',      # 总资产
'total_equity',      # 净资产
'total_liabilities', # 总负债
'current_assets',    # 流动资产
'current_liabilities', # 流动负债
'cash',              # 现金
'inventory',         # 存货
'interest_expense',  # 利息支出
'ebit',              # 息税前利润

# 现金流数据
'operating_cash_flow', # 经营现金流
'capital_expenditure', # 资本支出
'free_cash_flow',      # 自由现金流

# 分红数据
'dividend_per_share',  # 每股股息
'dividend_yield',      # 股息率

# 周转数据
'receivables',         # 应收账款
'accounts_payable',    # 应付账款
```

## 五、因子设计规范

### 5.1 基类继承

所有因子继承 `BaseFactor`，设置 `category = "fundamental"`。

### 5.2 数据验证

```python
@property
def required_data(self) -> List[str]:
    return ['field1', 'field2', ...]
```

### 5.3 参数设计

- 支持多周期比较（如同比、环比）
- 支持行业中性化选项
- 支持极端值处理

### 5.4 文档规范

每个因子包含：
- 因子名称和描述
- 计算公式
- 理论依据
- 学术出处
- 使用示例

## 六、预期产出

1. **31个基本面因子**：覆盖估值、质量、成长、财务健康、现金流、分红六大类
2. **完整测试覆盖**：单元测试验证计算正确性
3. **文档更新**：README和代码注释完善
4. **因子注册支持**：可通过 FactorRegistry 统一管理

## 七、学术参考文献

1. Fama, E. F., & French, K. R. (1992). The Cross-Section of Expected Stock Returns. Journal of Finance.
2. Novy-Marx, R. (2013). The Other Side of Value: The Gross Profitability Premium. Journal of Financial Economics.
3. Sloan, R. G. (1996). Do Stock Prices Reflect Information in Accruals and Cash Flows?. Accounting Review.
4. Piotroski, J. D. (2000). Value Investing: The Use of Historical Financial Statement Information. Journal of Accounting Research.
5. Altman, E. I. (1968). Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy. Journal of Finance.
6. Cooper, M. J., Gulen, H., & Schill, M. J. (2008). Asset Growth and the Cross-Section of Stock Returns. Journal of Finance.
7. Lakonishok, J., Shleifer, A., & Vishny, R. W. (1994). Contrarian Investment, Extrapolation, and Risk. Journal of Finance.
8. Litzenberger, R. H., & Ramaswamy, K. (1979). The Effect of Personal Taxes and Dividends on Capital Asset Prices. Journal of Financial Economics.

## 八、实施时间线

| 阶段 | 任务 | 文件 |
|------|------|------|
| 1 | 创建目录结构和 __init__.py | fundamental/__init__.py |
| 2 | 实现估值因子 | valuation.py |
| 3 | 实现质量因子 | quality.py |
| 4 | 实现成长因子 | growth.py |
| 5 | 实现财务健康因子 | financial_health.py |
| 6 | 实现现金流因子 | cashflow.py |
| 7 | 实现分红因子 | dividend.py |
| 8 | 编写单元测试 | tests/test_fundamental_factors.py |
| 9 | 更新文档 | README.md |
