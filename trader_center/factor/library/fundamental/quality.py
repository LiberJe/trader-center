"""
质量因子

包含盈利能力、运营效率等质量相关因子。

学术出处:
    Novy-Marx, R. (2013). "The Other Side of Value: The Gross Profitability Premium"
    Journal of Financial Economics, 108(1), 1-28.
"""

from typing import List
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class ROEFactor(BaseFactor):
    """
    净资产收益率因子 (Return on Equity)
    
    计算公式: ROE = 净利润 / 净资产
    
    理论依据:
        衡量股东权益回报效率，是盈利能力的核心指标。
        高ROE公司通常具有竞争优势，长期表现更好。
    
    学术出处:
        Novy-Marx (2013) "The Other Side of Value: The Gross Profitability Premium"
        Haugen & Baker (1996) "Commonality in the Determinants of Expected Stock Returns"
    
    使用说明:
        - 方向: positive (高ROE更优)
        - 适用: 所有公司
        - 注意: 高ROE可能源于高杠杆，需结合负债率分析
    """
    
    name = "roe"
    category = "fundamental"
    description = "净资产收益率因子（净利润/净资产）"
    
    def __init__(self, annualize: bool = True):
        """
        Args:
            annualize: 是否年化（季度数据乘以4）
        """
        super().__init__(annualize=annualize)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['net_income', 'total_equity']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        net_income = data['net_income']
        total_equity = data['total_equity']
        
        roe = net_income / total_equity.replace(0, np.nan)
        
        if self.params.get('annualize', True):
            roe = roe * 4
        
        return roe


class ROAFactor(BaseFactor):
    """
    总资产收益率因子 (Return on Assets)
    
    计算公式: ROA = 净利润 / 总资产
    
    理论依据:
        衡量资产利用效率，不受资本结构影响。
        高ROA表示公司能有效利用资产创造利润。
    
    学术出处:
        Novy-Marx (2013) "The Other Side of Value: The Gross Profitability Premium"
        Balakrishnan et al. (2010) "Is Operating Cash Flow a Superior Measure?"
    
    使用说明:
        - 方向: positive (高ROA更优)
        - 适用: 所有公司
        - 注意: 资本密集型行业ROA通常较低
    """
    
    name = "roa"
    category = "fundamental"
    description = "总资产收益率因子（净利润/总资产）"
    
    def __init__(self, annualize: bool = True):
        super().__init__(annualize=annualize)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['net_income', 'total_assets']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        net_income = data['net_income']
        total_assets = data['total_assets']
        
        roa = net_income / total_assets.replace(0, np.nan)
        
        if self.params.get('annualize', True):
            roa = roa * 4
        
        return roa


class GrossMarginFactor(BaseFactor):
    """
    毛利率因子 (Gross Margin)
    
    计算公式: 毛利率 = (营业收入 - 营业成本) / 营业收入
    
    理论依据:
        衡量产品定价能力和成本控制能力。
        高毛利率通常表示公司具有竞争优势或品牌溢价。
    
    学术出处:
        Novy-Marx (2013) "The Other Side of Value: The Gross Profitability Premium"
        Fairfield & Yohn (2001) "Using Asset Turnover and Profit Margin"
    
    使用说明:
        - 方向: positive (高毛利率更优)
        - 适用: 所有公司
        - 注意: 不同行业毛利率差异大，需行业中性化
    """
    
    name = "gross_margin"
    category = "fundamental"
    description = "毛利率因子（(营收-成本)/营收）"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['revenue', 'cost_of_goods']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        revenue = data['revenue']
        cost_of_goods = data['cost_of_goods']
        
        gross_profit = revenue - cost_of_goods
        gross_margin = gross_profit / revenue.replace(0, np.nan)
        
        return gross_margin


class NetMarginFactor(BaseFactor):
    """
    净利率因子 (Net Profit Margin)
    
    计算公式: 净利率 = 净利润 / 营业收入
    
    理论依据:
        衡量公司的整体盈利能力，反映成本控制和运营效率。
        高净利率公司通常具有更好的成本管理和运营效率。
    
    学术出处:
        Novy-Marx (2013) "The Other Side of Value: The Gross Profitability Premium"
        Soliman (2008) "The Use of DuPont Analysis by Market Participants"
    
    使用说明:
        - 方向: positive (高净利率更优)
        - 适用: 所有公司
        - 注意: 净利率受非经常性损益影响
    """
    
    name = "net_margin"
    category = "fundamental"
    description = "净利率因子（净利润/营收）"
    
    def __init__(self):
        super().__init__()
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['net_income', 'revenue']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        net_income = data['net_income']
        revenue = data['revenue']
        
        net_margin = net_income / revenue.replace(0, np.nan)
        
        return net_margin


class AssetTurnoverFactor(BaseFactor):
    """
    资产周转率因子 (Asset Turnover)
    
    计算公式: 资产周转率 = 营业收入 / 总资产
    
    理论依据:
        衡量资产利用效率，是DuPont分析的核心组成部分。
        高资产周转率表示公司能有效利用资产产生收入。
    
    学术出处:
        Soliman (2008) "The Use of DuPont Analysis by Market Participants"
        Fairfield & Yohn (2001) "Using Asset Turnover and Profit Margin"
    
    使用说明:
        - 方向: positive (高周转率更优)
        - 适用: 所有公司
        - 注意: 资本密集型行业周转率通常较低
    """
    
    name = "asset_turnover"
    category = "fundamental"
    description = "资产周转率因子（营收/总资产）"
    
    def __init__(self, annualize: bool = True):
        super().__init__(annualize=annualize)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['revenue', 'total_assets']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        revenue = data['revenue']
        total_assets = data['total_assets']
        
        turnover = revenue / total_assets.replace(0, np.nan)
        
        if self.params.get('annualize', True):
            turnover = turnover * 4
        
        return turnover


class GrossProfitabilityFactor(BaseFactor):
    """
    毛利润率因子 (Gross Profitability)
    
    计算公式: 毛利润率 = (营业收入 - 营业成本) / 总资产
    
    理论依据:
        Novy-Marx (2013) 发现毛利润率是最强的质量因子。
        相比净利润，毛利润更稳定、更难操纵。
        高毛利润率公司具有持续竞争优势。
    
    学术出处:
        Novy-Marx, R. (2013) "The Other Side of Value: The Gross Profitability Premium"
        Journal of Financial Economics, 108(1), 1-28.
    
    使用说明:
        - 方向: positive (高毛利润率更优)
        - 适用: 所有公司
        - 注意: 是质量因子中最稳健的因子之一
    """
    
    name = "gross_profitability"
    category = "fundamental"
    description = "毛利润率因子（(营收-成本)/总资产）"
    
    def __init__(self, annualize: bool = True):
        super().__init__(annualize=annualize)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['revenue', 'cost_of_goods', 'total_assets']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        revenue = data['revenue']
        cost_of_goods = data['cost_of_goods']
        total_assets = data['total_assets']
        
        gross_profit = revenue - cost_of_goods
        gp_ratio = gross_profit / total_assets.replace(0, np.nan)
        
        if self.params.get('annualize', True):
            gp_ratio = gp_ratio * 4
        
        return gp_ratio
