"""
成长因子

包含营收增长、利润增长、资产增长等成长相关因子。

学术出处:
    Lakonishok, Shleifer & Vishny (1994) "Contrarian Investment, Extrapolation, and Risk"
    Cooper, Gulen & Schill (2008) "Asset Growth and the Cross-Section of Stock Returns"
"""

from typing import List
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class RevenueGrowthFactor(BaseFactor):
    """
    营收增长率因子 (Revenue Growth)
    
    计算公式: 营收增长率 = (本期营收 - 上期营收) / 上期营收
    
    理论依据:
        营收增长是公司成长性的核心指标。
        持续的营收增长通常预示着市场份额扩张和竞争优势。
    
    学术出处:
        Lakonishok, Shleifer & Vishny (1994) "Contrarian Investment, Extrapolation, and Risk"
        Chan et al. (2003) "Earnings Quality and Stock Returns"
    
    使用说明:
        - 方向: positive (高增长更优)
        - 适用: 所有公司
        - 注意: 高增长可能不可持续，需关注增长质量
    """
    
    name = "revenue_growth"
    category = "fundamental"
    description = "营收增长率因子"
    
    def __init__(self, period: int = 1, yoy: bool = True):
        """
        Args:
            period: 增长周期（季度数），默认1
            yoy: 是否同比（True为同比，False为环比）
        """
        super().__init__(period=period, yoy=yoy)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['revenue']
    
    def _validate_params(self):
        if self.params.get('period', 1) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        yoy = self.params.get('yoy', True)
        
        revenue = data['revenue']
        
        if yoy:
            shift_period = period * 4
        else:
            shift_period = period
        
        growth = (revenue - revenue.shift(shift_period)) / revenue.shift(shift_period)
        
        return growth


class EarningsGrowthFactor(BaseFactor):
    """
    净利润增长率因子 (Earnings Growth)
    
    计算公式: 净利润增长率 = (本期净利润 - 上期净利润) / |上期净利润|
    
    理论依据:
        利润增长是股价上涨的核心驱动力。
        但高利润增长可能被市场过度定价。
    
    学术出处:
        Chan et al. (2003) "Earnings Quality and Stock Returns"
        Hou, van Dijk & Zhang (2012) "The Implied Cost of Capital"
    
    使用说明:
        - 方向: positive (高增长更优)
        - 适用: 盈利公司
        - 注意: 利润波动大的公司增长率不稳定
    """
    
    name = "earnings_growth"
    category = "fundamental"
    description = "净利润增长率因子"
    
    def __init__(self, period: int = 1, yoy: bool = True):
        super().__init__(period=period, yoy=yoy)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['net_income']
    
    def _validate_params(self):
        if self.params.get('period', 1) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        yoy = self.params.get('yoy', True)
        
        net_income = data['net_income']
        
        if yoy:
            shift_period = period * 4
        else:
            shift_period = period
        
        prev_income = net_income.shift(shift_period)
        growth = (net_income - prev_income) / prev_income.abs().replace(0, np.nan)
        
        return growth


class EPSGrowthFactor(BaseFactor):
    """
    EPS增长率因子 (EPS Growth)
    
    计算公式: EPS增长率 = (本期EPS - 上期EPS) / |上期EPS|
    
    理论依据:
        EPS增长直接反映股东价值的增长。
        相比净利润增长，EPS增长考虑了股本变化的影响。
    
    学术出处:
        Chan et al. (2003) "Earnings Quality and Stock Returns"
        Hou, van Dijk & Zhang (2012) "The Implied Cost of Capital"
    
    使用说明:
        - 方向: positive (高增长更优)
        - 适用: 盈利公司
        - 注意: 需关注EPS增长是否来自股票回购
    """
    
    name = "eps_growth"
    category = "fundamental"
    description = "EPS增长率因子"
    
    def __init__(self, period: int = 1, yoy: bool = True):
        super().__init__(period=period, yoy=yoy)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['eps']
    
    def _validate_params(self):
        if self.params.get('period', 1) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        yoy = self.params.get('yoy', True)
        
        eps = data['eps']
        
        if yoy:
            shift_period = period * 4
        else:
            shift_period = period
        
        prev_eps = eps.shift(shift_period)
        growth = (eps - prev_eps) / prev_eps.abs().replace(0, np.nan)
        
        return growth


class AssetGrowthFactor(BaseFactor):
    """
    资产增长率因子 (Asset Growth)
    
    计算公式: 资产增长率 = (本期资产 - 上期资产) / 上期资产
    
    理论依据:
        Cooper et al. (2008) 发现资产增长率与未来收益负相关。
        资产快速扩张的公司往往过度投资，导致未来收益下降。
        这是一个**负向因子**。
    
    学术出处:
        Cooper, Gulen & Schill (2008) "Asset Growth and the Cross-Section of Stock Returns"
        Journal of Finance, 63(4), 1609-1651.
    
    使用说明:
        - 方向: negative (低增长更优，资产扩张过快不利)
        - 适用: 所有公司
        - 注意: 是显著的负向因子，资产扩张过快往往预示未来收益下降
    """
    
    name = "asset_growth"
    category = "fundamental"
    description = "资产增长率因子（负向因子）"
    
    def __init__(self, period: int = 1, yoy: bool = True):
        super().__init__(period=period, yoy=yoy)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['total_assets']
    
    def _validate_params(self):
        if self.params.get('period', 1) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        yoy = self.params.get('yoy', True)
        
        total_assets = data['total_assets']
        
        if yoy:
            shift_period = period * 4
        else:
            shift_period = period
        
        growth = (total_assets - total_assets.shift(shift_period)) / total_assets.shift(shift_period)
        
        return growth


class OCFGrowthFactor(BaseFactor):
    """
    经营现金流增长率因子 (Operating Cash Flow Growth)
    
    计算公式: OCF增长率 = (本期OCF - 上期OCF) / |上期OCF|
    
    理论依据:
        现金流增长比利润增长更可靠，更难操纵。
        Sloan (1996) 发现现金流质量高的公司表现更好。
    
    学术出处:
        Sloan, R. G. (1996) "Do Stock Prices Reflect Information in Accruals and Cash Flows?"
        Accounting Review, 71(3), 289-315.
    
    使用说明:
        - 方向: positive (高增长更优)
        - 适用: 所有公司
        - 注意: 现金流增长比利润增长更稳定
    """
    
    name = "ocf_growth"
    category = "fundamental"
    description = "经营现金流增长率因子"
    
    def __init__(self, period: int = 1, yoy: bool = True):
        super().__init__(period=period, yoy=yoy)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['operating_cash_flow']
    
    def _validate_params(self):
        if self.params.get('period', 1) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        yoy = self.params.get('yoy', True)
        
        ocf = data['operating_cash_flow']
        
        if yoy:
            shift_period = period * 4
        else:
            shift_period = period
        
        prev_ocf = ocf.shift(shift_period)
        growth = (ocf - prev_ocf) / prev_ocf.abs().replace(0, np.nan)
        
        return growth
