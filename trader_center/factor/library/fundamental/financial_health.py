"""
财务健康因子

包含偿债能力、破产预警等财务健康相关因子。

学术出处:
    Altman, E. I. (1968). "Financial Ratios, Discriminant Analysis and the Prediction 
    of Corporate Bankruptcy". Journal of Finance, 23(4), 589-609.
    Piotroski, J. D. (2000). "Value Investing: The Use of Historical Financial Statement 
    Information to Separate Winners from Losers". Journal of Accounting Research.
"""

from typing import List
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class DebtRatioFactor(BaseFactor):
    """
    资产负债率因子 (Debt Ratio)
    
    计算公式: 资产负债率 = 总负债 / 总资产
    
    理论依据:
        衡量公司的财务杠杆水平，是财务风险的核心指标。
        高负债率增加财务困境风险，但也可能提高股东回报。
    
    学术出处:
        Altman (1968) "Financial Ratios, Discriminant Analysis and the Prediction 
        of Corporate Bankruptcy"
    
    使用说明:
        - 方向: negative (低负债率更稳健)
        - 适用: 所有公司
        - 注意: 不同行业负债率差异大，需行业中性化
    """
    
    name = "debt_ratio"
    category = "fundamental"
    description = "资产负债率因子（总负债/总资产）"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['total_liabilities', 'total_assets']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        total_liabilities = data['total_liabilities']
        total_assets = data['total_assets']
        
        debt_ratio = total_liabilities / total_assets.replace(0, np.nan)
        
        return debt_ratio


class CurrentRatioFactor(BaseFactor):
    """
    流动比率因子 (Current Ratio)
    
    计算公式: 流动比率 = 流动资产 / 流动负债
    
    理论依据:
        衡量公司的短期偿债能力。
        流动比率 > 1 表示流动资产足以覆盖流动负债。
    
    学术出处:
        Altman (1968) "Financial Ratios, Discriminant Analysis and the Prediction 
        of Corporate Bankruptcy"
        Ohlson (1980) "Financial Ratios and the Probabilistic Prediction of Bankruptcy"
    
    使用说明:
        - 方向: positive (高流动比率更稳健)
        - 适用: 所有公司
        - 注意: 过高可能表示资金利用效率低
    """
    
    name = "current_ratio"
    category = "fundamental"
    description = "流动比率因子（流动资产/流动负债）"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['current_assets', 'current_liabilities']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        current_assets = data['current_assets']
        current_liabilities = data['current_liabilities']
        
        current_ratio = current_assets / current_liabilities.replace(0, np.nan)
        
        return current_ratio


class QuickRatioFactor(BaseFactor):
    """
    速动比率因子 (Quick Ratio / Acid Test Ratio)
    
    计算公式: 速动比率 = (流动资产 - 存货) / 流动负债
    
    理论依据:
        比流动比率更严格的短期偿债能力指标。
        排除存货后，更准确反映即时偿债能力。
    
    学术出处:
        Altman (1968) "Financial Ratios, Discriminant Analysis and the Prediction 
        of Corporate Bankruptcy"
        Ohlson (1980) "Financial Ratios and the Probabilistic Prediction of Bankruptcy"
    
    使用说明:
        - 方向: positive (高速动比率更稳健)
        - 适用: 所有公司
        - 注意: 速动比率 > 1 通常被认为健康
    """
    
    name = "quick_ratio"
    category = "fundamental"
    description = "速动比率因子（(流动资产-存货)/流动负债）"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['current_assets', 'inventory', 'current_liabilities']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        current_assets = data['current_assets']
        inventory = data.get('inventory', pd.Series(0, index=data.index))
        current_liabilities = data['current_liabilities']
        
        quick_assets = current_assets - inventory
        quick_ratio = quick_assets / current_liabilities.replace(0, np.nan)
        
        return quick_ratio


class InterestCoverageFactor(BaseFactor):
    """
    利息保障倍数因子 (Interest Coverage Ratio)
    
    计算公式: 利息保障倍数 = EBIT / 利息支出
    
    理论依据:
        衡量公司支付利息的能力。
        高利息保障倍数表示公司有足够的利润支付利息。
    
    学术出处:
        Ohlson (1980) "Financial Ratios and the Probabilistic Prediction of Bankruptcy"
        Altman (1968) "Financial Ratios, Discriminant Analysis and the Prediction 
        of Corporate Bankruptcy"
    
    使用说明:
        - 方向: positive (高保障倍数更稳健)
        - 适用: 有负债的公司
        - 注意: 利息保障倍数 < 1.5 表示财务风险较高
    """
    
    name = "interest_coverage"
    category = "fundamental"
    description = "利息保障倍数因子（EBIT/利息支出）"
    
    def __init__(self, min_coverage: float = 0.1):
        """
        Args:
            min_coverage: 最小保障倍数，用于处理极端值
        """
        super().__init__(min_coverage=min_coverage)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['ebit', 'interest_expense']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        ebit = data['ebit']
        interest_expense = data['interest_expense']
        
        coverage = ebit / interest_expense.replace(0, np.nan)
        
        min_coverage = self.params.get('min_coverage', 0.1)
        coverage = coverage.clip(lower=min_coverage)
        
        return coverage


class AltmanZScoreFactor(BaseFactor):
    """
    Altman Z-Score因子
    
    计算公式: 
        Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
        X1 = 营运资本/总资产
        X2 = 留存收益/总资产
        X3 = EBIT/总资产
        X4 = 股票市值/总负债
        X5 = 营业收入/总资产
    
    理论依据:
        Altman (1968) 提出的破产预警模型，综合多个财务比率预测破产风险。
        Z < 1.81 表示高破产风险，Z > 2.99 表示低风险。
    
    学术出处:
        Altman, E. I. (1968). "Financial Ratios, Discriminant Analysis and the 
        Prediction of Corporate Bankruptcy". Journal of Finance, 23(4), 589-609.
    
    使用说明:
        - 方向: positive (高Z-Score更稳健)
        - 适用: 上市公司
        - 注意: Z < 1.81 为高风险区，Z > 2.99 为安全区
    """
    
    name = "altman_z_score"
    category = "fundamental"
    description = "Altman Z-Score破产预警因子"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return [
            'current_assets', 'current_liabilities', 'total_assets',
            'retained_earnings', 'ebit', 'market_cap', 'total_liabilities', 'revenue'
        ]
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        total_assets = data['total_assets'].replace(0, np.nan)
        total_liabilities = data['total_liabilities'].replace(0, np.nan)
        
        x1 = (data['current_assets'] - data['current_liabilities']) / total_assets
        x2 = data.get('retained_earnings', pd.Series(0, index=data.index)) / total_assets
        x3 = data['ebit'] / total_assets
        x4 = data['market_cap'] / total_liabilities
        x5 = data['revenue'] / total_assets
        
        z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        
        return z_score


class PiotroskiFScoreFactor(BaseFactor):
    """
    Piotroski F-Score因子
    
    计算公式: 9项指标得分之和（0-9分）
        盈利能力（4分）:
            1. ROA > 0
            2. 经营现金流 > 0
            3. ROA同比增长
            4. 经营现金流 > 净利润（盈利质量）
        杠杆/流动性（3分）:
            5. 杠杆同比下降
            6. 流动比率同比上升
            7. 未发行新股
        运营效率（2分）:
            8. 毛利率同比上升
            9. 资产周转率同比上升
    
    理论依据:
        Piotroski (2000) 发现高F-Score的价值股表现显著更好。
        F-Score综合评估公司的财务健康状况。
    
    学术出处:
        Piotroski, J. D. (2000). "Value Investing: The Use of Historical Financial 
        Statement Information to Separate Winners from Losers". 
        Journal of Accounting Research, 38, 1-41.
    
    使用说明:
        - 方向: positive (高F-Score更优)
        - 适用: 所有公司，特别是价值股
        - 注意: 需要历史数据进行同比计算
    """
    
    name = "piotroski_f_score"
    category = "fundamental"
    description = "Piotroski F-Score财务健康评分因子"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return [
            'net_income', 'total_assets', 'operating_cash_flow',
            'total_liabilities', 'current_assets', 'current_liabilities',
            'revenue', 'cost_of_goods', 'shares_outstanding'
        ]
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        f_score = pd.Series(0, index=data.index, dtype=float)
        
        roa = data['net_income'] / data['total_assets'].replace(0, np.nan)
        f_score = f_score + (roa > 0).astype(float)
        
        f_score = f_score + (data['operating_cash_flow'] > 0).astype(float)
        
        roa_prev = roa.shift(4)
        f_score = f_score + (roa > roa_prev).astype(float)
        
        f_score = f_score + (data['operating_cash_flow'] > data['net_income']).astype(float)
        
        leverage = data['total_liabilities'] / data['total_assets'].replace(0, np.nan)
        leverage_prev = leverage.shift(4)
        f_score = f_score + (leverage < leverage_prev).astype(float)
        
        current_ratio = data['current_assets'] / data['current_liabilities'].replace(0, np.nan)
        current_ratio_prev = current_ratio.shift(4)
        f_score = f_score + (current_ratio > current_ratio_prev).astype(float)
        
        shares = data['shares_outstanding']
        shares_prev = shares.shift(4)
        f_score = f_score + (shares <= shares_prev).astype(float)
        
        gross_margin = (data['revenue'] - data['cost_of_goods']) / data['revenue'].replace(0, np.nan)
        gross_margin_prev = gross_margin.shift(4)
        f_score = f_score + (gross_margin > gross_margin_prev).astype(float)
        
        asset_turnover = data['revenue'] / data['total_assets'].replace(0, np.nan)
        asset_turnover_prev = asset_turnover.shift(4)
        f_score = f_score + (asset_turnover > asset_turnover_prev).astype(float)
        
        return f_score


class CashRatioFactor(BaseFactor):
    """
    现金比率因子 (Cash Ratio)
    
    计算公式: 现金比率 = 现金及现金等价物 / 流动负债
    
    理论依据:
        最严格的流动性指标，衡量公司用现金偿还短期债务的能力。
        高现金比率表示公司具有较强的即时偿债能力。
    
    学术出处:
        Ohlson (1980) "Financial Ratios and the Probabilistic Prediction of Bankruptcy"
    
    使用说明:
        - 方向: positive (高现金比率更稳健)
        - 适用: 所有公司
        - 注意: 过高可能表示资金利用效率低
    """
    
    name = "cash_ratio"
    category = "fundamental"
    description = "现金比率因子（现金/流动负债）"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['cash', 'current_liabilities']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        cash = data['cash']
        current_liabilities = data['current_liabilities']
        
        cash_ratio = cash / current_liabilities.replace(0, np.nan)
        
        return cash_ratio
