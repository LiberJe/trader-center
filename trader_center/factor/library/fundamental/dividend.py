"""
分红因子

包含股息率、分红率、股息增长等分红相关因子。

学术出处:
    Litzenberger & Ramaswamy (1979) "The Effect of Personal Taxes and Dividends 
    on Capital Asset Prices"
    Fama & French (2001) "Disappearing Dividends: Changing Firm Characteristics 
    or Lower Propensity to Pay?"
"""

from typing import List
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class DividendYieldFactor(BaseFactor):
    """
    股息率因子 (Dividend Yield)
    
    计算公式: 股息率 = 每股股息 / 股价
    
    理论依据:
        股息率是价值投资的核心指标之一。
        高股息率股票通常具有防御性，在市场下跌时表现更好。
        Litzenberger & Ramaswamy (1979) 发现股息率与预期收益正相关。
    
    学术出处:
        Litzenberger, R. H. & Ramaswamy, K. (1979). "The Effect of Personal Taxes 
        and Dividends on Capital Asset Prices". Journal of Financial Economics, 7(2), 163-195.
    
    使用说明:
        - 方向: positive (高股息率更优)
        - 适用: 分红公司
        - 注意: 过高股息率可能不可持续
    """
    
    name = "dividend_yield"
    category = "fundamental"
    description = "股息率因子（每股股息/股价）"
    
    def __init__(self, annualize: bool = True):
        super().__init__(annualize=annualize)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['dividend_per_share', 'price']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        dividend = data['dividend_per_share']
        price = data['price']
        
        dividend_yield = dividend / price.replace(0, np.nan)
        
        if self.params.get('annualize', True):
            dividend_yield = dividend_yield * 4
        
        return dividend_yield


class PayoutRatioFactor(BaseFactor):
    """
    分红率因子 (Payout Ratio)
    
    计算公式: 分红率 = 每股股息 / 每股收益
    
    理论依据:
        分红率反映公司的分红政策和财务健康。
        适度的分红率（30%-60%）通常表示公司财务稳健。
        过高分红率可能不可持续，过低可能表示公司处于成长期。
    
    学术出处:
        Fama, E. F. & French, K. R. (2001). "Disappearing Dividends: Changing Firm 
        Characteristics or Lower Propensity to Pay?". Journal of Financial Economics, 60(1), 3-43.
    
    使用说明:
        - 方向: 适中为佳（30%-60%）
        - 适用: 盈利且分红的公司
        - 注意: 分红率 > 100% 不可持续
    """
    
    name = "payout_ratio"
    category = "fundamental"
    description = "分红率因子（每股股息/每股收益）"
    
    def __init__(self, max_ratio: float = 2.0):
        """
        Args:
            max_ratio: 分红率上限，超过此值设为NaN
        """
        super().__init__(max_ratio=max_ratio)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['dividend_per_share', 'eps']
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        dividend = data['dividend_per_share']
        eps = data['eps']
        
        payout_ratio = dividend / eps.replace(0, np.nan)
        
        max_ratio = self.params.get('max_ratio', 2.0)
        payout_ratio[payout_ratio > max_ratio] = np.nan
        payout_ratio[payout_ratio < 0] = np.nan
        
        return payout_ratio


class DividendGrowthFactor(BaseFactor):
    """
    股息增长率因子 (Dividend Growth)
    
    计算公式: 股息增长率 = (本期股息 - 上期股息) / 上期股息
    
    理论依据:
        股息增长是公司财务健康和信心的信号。
        持续增长的股息通常预示着公司盈利能力稳定。
        Grullon et al. (2002) 发现股息增长与未来收益正相关。
    
    学术出处:
        Grullon, G., Michaely, R. & Swaminathan, B. (2002). "Are Dividend Changes 
        a Sign of Firm Maturity?". Journal of Business, 75(3), 387-424.
    
    使用说明:
        - 方向: positive (正增长更优)
        - 适用: 持续分红的公司
        - 注意: 需要至少2年分红数据
    """
    
    name = "dividend_growth"
    category = "fundamental"
    description = "股息增长率因子"
    
    def __init__(self, period: int = 1, yoy: bool = True):
        """
        Args:
            period: 增长周期（年数），默认1
            yoy: 是否同比
        """
        super().__init__(period=period, yoy=yoy)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['dividend_per_share']
    
    def _validate_params(self):
        if self.params.get('period', 1) <= 0:
            raise ValueError("period 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        yoy = self.params.get('yoy', True)
        
        dividend = data['dividend_per_share']
        
        if yoy:
            shift_period = period * 4
        else:
            shift_period = period
        
        prev_dividend = dividend.shift(shift_period)
        growth = (dividend - prev_dividend) / prev_dividend.replace(0, np.nan)
        
        return growth
