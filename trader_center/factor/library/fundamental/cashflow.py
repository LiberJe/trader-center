"""
现金流因子

包含自由现金流收益率、现金流质量等现金流相关因子。

学术出处:
    Sloan, R. G. (1996). "Do Stock Prices Reflect Information in Accruals and Cash Flows?"
    Accounting Review, 71(3), 289-315.
"""

from typing import List
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class FCFYieldFactor(BaseFactor):
    """
    自由现金流收益率因子 (Free Cash Flow Yield)
    
    计算公式: FCF收益率 = 自由现金流 / 市值
    
    理论依据:
        自由现金流是公司可自由支配的现金，是股东价值的真实来源。
        高FCF收益率表示公司被低估或现金流强劲。
    
    学术出处:
        Sloan, R. G. (1996). "Do Stock Prices Reflect Information in Accruals and Cash Flows?"
        Accounting Review, 71(3), 289-315.
        Hackel, Livnat & Rai (1994) "The Free Cash Flow/Small-Cap Anomaly"
    
    使用说明:
        - 方向: positive (高FCF收益率更优)
        - 适用: 所有公司
        - 注意: FCF波动大的公司需谨慎
    """
    
    name = "fcf_yield"
    category = "fundamental"
    description = "自由现金流收益率因子（FCF/市值）"
    
    def __init__(self, annualize: bool = True):
        super().__init__(annualize=annualize)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['free_cash_flow', 'market_cap']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        fcf = data['free_cash_flow']
        market_cap = data['market_cap']
        
        fcf_yield = fcf / market_cap.replace(0, np.nan)
        
        if self.params.get('annualize', True):
            fcf_yield = fcf_yield * 4
        
        return fcf_yield


class OCFToNetIncomeFactor(BaseFactor):
    """
    经营现金流/净利润因子 (OCF to Net Income Ratio)
    
    计算公式: OCF/净利润 = 经营现金流 / 净利润
    
    理论依据:
        Sloan (1996) 发现应计项目（净利润与现金流的差异）高的公司未来收益低。
        OCF/净利润 > 1 表示盈利质量高，利润有现金流支撑。
        OCF/净利润 < 1 可能表示利润被操纵或应收账款过多。
    
    学术出处:
        Sloan, R. G. (1996). "Do Stock Prices Reflect Information in Accruals and Cash Flows?"
        Accounting Review, 71(3), 289-315.
    
    使用说明:
        - 方向: positive (高比率表示盈利质量高)
        - 适用: 盈利公司
        - 注意: 比率 < 0.5 需警惕盈利质量
    """
    
    name = "ocf_to_net_income"
    category = "fundamental"
    description = "经营现金流/净利润因子（盈利质量）"
    
    def __init__(self, handle_negative: str = 'abs'):
        super().__init__(handle_negative=handle_negative)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['operating_cash_flow', 'net_income']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        ocf = data['operating_cash_flow']
        net_income = data['net_income']
        
        ratio = ocf / net_income.replace(0, np.nan)
        
        handle_negative = self.params.get('handle_negative', 'abs')
        if handle_negative == 'abs':
            ratio = ratio.abs()
        elif handle_negative == 'nan':
            ratio[ratio < 0] = np.nan
        
        return ratio


class CashConversionCycleFactor(BaseFactor):
    """
    现金循环周期因子 (Cash Conversion Cycle)
    
    计算公式: 
        CCC = 应收账款周转天数 + 存货周转天数 - 应付账款周转天数
        应收账款周转天数 = 365 * 应收账款 / 营业收入
        存货周转天数 = 365 * 存货 / 营业成本
        应付账款周转天数 = 365 * 应付账款 / 营业成本
    
    理论依据:
        现金循环周期衡量公司从投入资金到收回现金的时间。
        较短的CCC表示公司运营效率高，资金周转快。
    
    学术出处:
        Richards, V. D. & Laughlin, E. J. (1980). "A Cash Conversion Cycle Approach 
        to Liquidity Analysis". Financial Management, 9(1), 32-38.
    
    使用说明:
        - 方向: negative (短CCC更优)
        - 适用: 所有公司
        - 注意: 不同行业CCC差异大
    """
    
    name = "cash_conversion_cycle"
    category = "fundamental"
    description = "现金循环周期因子（运营效率）"
    
    def __init__(self, days_in_year: int = 365):
        super().__init__(days_in_year=days_in_year)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['receivables', 'inventory', 'accounts_payable', 'revenue', 'cost_of_goods']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        days = self.params.get('days_in_year', 365)
        
        receivables = data['receivables']
        inventory = data.get('inventory', pd.Series(0, index=data.index))
        accounts_payable = data.get('accounts_payable', pd.Series(0, index=data.index))
        revenue = data['revenue']
        cost_of_goods = data['cost_of_goods']
        
        ar_days = days * receivables / revenue.replace(0, np.nan)
        inv_days = days * inventory / cost_of_goods.replace(0, np.nan)
        ap_days = days * accounts_payable / cost_of_goods.replace(0, np.nan)
        
        ccc = ar_days + inv_days - ap_days
        
        return ccc


class CapExRatioFactor(BaseFactor):
    """
    资本支出比率因子 (Capital Expenditure Ratio)
    
    计算公式: 资本支出比率 = 资本支出 / 总资产
    
    理论依据:
        资本支出比率衡量公司的投资强度。
        过高的资本支出可能预示过度投资，Titman et al. (2004) 发现
        高资本支出的公司未来收益较低。
    
    学术出处:
        Titman, S., Wei, K. C. J. & Xie, F. (2004). "Capital Investments and 
        Stock Returns". Journal of Financial and Quantitative Analysis, 39(4), 677-700.
    
    使用说明:
        - 方向: negative (高资本支出比率可能不利)
        - 适用: 所有公司
        - 注意: 资本密集型行业资本支出通常较高
    """
    
    name = "capex_ratio"
    category = "fundamental"
    description = "资本支出比率因子（投资强度）"
    
    def __init__(self, annualize: bool = True):
        super().__init__(annualize=annualize)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['capital_expenditure', 'total_assets']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        capex = data['capital_expenditure'].abs()
        total_assets = data['total_assets']
        
        capex_ratio = capex / total_assets.replace(0, np.nan)
        
        if self.params.get('annualize', True):
            capex_ratio = capex_ratio * 4
        
        return capex_ratio
