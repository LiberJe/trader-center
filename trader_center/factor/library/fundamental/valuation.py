"""
估值因子

包含市盈率、市净率、市销率、企业价值倍数、PEG、股价现金流比等估值因子。

学术出处:
- Fama, E. F., & French, K. R. (1992). The Cross-Section of Expected Stock Returns. Journal of Finance.
- Lakonishok, J., Shleifer, A., & Vishny, R. W. (1994). Contrarian Investment, Extrapolation, and Risk. Journal of Finance.
- Sloan, R. G. (1996). Do Stock Prices Reflect Information in Accruals and Cash Flows?. Accounting Review.
"""

from typing import List
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class PEFactor(BaseFactor):
    """
    市盈率因子 (Price-to-Earnings Ratio)
    
    计算公式: PE = 股价 / 每股收益
    
    理论依据:
        价值异象，低市盈率股票长期跑赢高市盈率股票。
        PE越低，股票越便宜，预期收益越高。
    
    学术出处:
        Fama & French (1992) "The Cross-Section of Expected Stock Returns"
    
    使用说明:
        - 方向: negative (低PE更优)
        - 适用: 盈利公司
        - 注意: 负PE需特殊处理
    """
    
    name = "pe_ratio"
    category = "fundamental"
    description = "市盈率因子（股价/每股收益）"
    
    def __init__(self, handle_negative: str = 'max'):
        """
        Args:
            handle_negative: 负PE处理方式
                - 'max': 设为最大值
                - 'abs': 取绝对值
                - 'nan': 设为NaN
        """
        super().__init__(handle_negative=handle_negative)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['pe_ratio']
    
    def _validate_params(self):
        if self.params.get('handle_negative', 'max') not in ['max', 'abs', 'nan']:
            raise ValueError("handle_negative 必须是 'max', 'abs' 或 'nan'")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        pe = data['pe_ratio'].copy()
        handle_negative = self.params['handle_negative']
        
        if handle_negative == 'max':
            max_pe = pe[pe > 0].max()
            pe[pe <= 0] = max_pe
        elif handle_negative == 'abs':
            pe = pe.abs()
        elif handle_negative == 'nan':
            pe[pe <= 0] = np.nan
        
        return pe


class PBFactor(BaseFactor):
    """
    市净率因子 (Price-to-Book Ratio)
    
    计算公式: PB = 股价 / 每股净资产
    
    理论依据:
        价值异象的核心因子，Fama-French三因子模型中的价值因子(HML)。
        低PB股票代表价值股，长期跑赢高PB的成长股。
    
    学术出处:
        Fama & French (1992) "The Cross-Section of Expected Stock Returns"
        Fama & French (1993) "Common Risk Factors in the Returns on Stocks and Bonds"
    
    使用说明:
        - 方向: negative (低PB更优)
        - 适用: 所有公司
        - 注意: PB<1可能表示资产被低估或公司困境
    """
    
    name = "pb_ratio"
    category = "fundamental"
    description = "市净率因子（股价/每股净资产）"
    
    def __init__(self, handle_negative: str = 'max'):
        super().__init__(handle_negative=handle_negative)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['pb_ratio']
    
    def _validate_params(self):
        if self.params.get('handle_negative', 'max') not in ['max', 'abs', 'nan']:
            raise ValueError("handle_negative 必须是 'max', 'abs' 或 'nan'")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        pb = data['pb_ratio'].copy()
        handle_negative = self.params['handle_negative']
        
        if handle_negative == 'max':
            max_pb = pb[pb > 0].max()
            pb[pb <= 0] = max_pb
        elif handle_negative == 'abs':
            pb = pb.abs()
        elif handle_negative == 'nan':
            pb[pb <= 0] = np.nan
        
        return pb


class PSFactor(BaseFactor):
    """
    市销率因子 (Price-to-Sales Ratio)
    
    计算公式: PS = 股价 / 每股销售额
    
    理论依据:
        对于尚未盈利的成长型公司，PS比PE更稳定。
        低PS股票通常表现更好，尤其适用于科技、互联网等行业。
    
    学术出处:
        Lakonishok, Shleifer & Vishny (1994) "Contrarian Investment, Extrapolation, and Risk"
    
    使用说明:
        - 方向: negative (低PS更优)
        - 适用: 所有公司，特别是未盈利公司
        - 注意: 不同行业PS差异大，需行业中性化
    """
    
    name = "ps_ratio"
    category = "fundamental"
    description = "市销率因子（股价/每股销售额）"
    
    def __init__(self, handle_negative: str = 'max'):
        super().__init__(handle_negative=handle_negative)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['ps_ratio']
    
    def _validate_params(self):
        if self.params.get('handle_negative', 'max') not in ['max', 'abs', 'nan']:
            raise ValueError("handle_negative 必须是 'max', 'abs' 或 'nan'")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        ps = data['ps_ratio'].copy()
        handle_negative = self.params['handle_negative']
        
        if handle_negative == 'max':
            max_ps = ps[ps > 0].max()
            ps[ps <= 0] = max_ps
        elif handle_negative == 'abs':
            ps = ps.abs()
        elif handle_negative == 'nan':
            ps[ps <= 0] = np.nan
        
        return ps


class EVEBITDAFactor(BaseFactor):
    """
    企业价值倍数因子 (EV/EBITDA)
    
    计算公式: EV/EBITDA = 企业价值 / 息税折旧摊销前利润
    
    理论依据:
        比PE更稳定的估值指标，不受资本结构影响。
        适用于比较不同杠杆水平的公司。
    
    学术出处:
        Damodaran (2006) "Damodaran on Valuation"
    
    使用说明:
        - 方向: negative (低EV/EBITDA更优)
        - 适用: 所有公司
        - 注意: 资本密集型行业EBITDA差异大
    """
    
    name = "ev_ebitda"
    category = "fundamental"
    description = "企业价值倍数因子（EV/EBITDA）"
    
    def __init__(self, handle_negative: str = 'max'):
        super().__init__(handle_negative=handle_negative)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['ev', 'ebitda']
    
    def _validate_params(self):
        if self.params.get('handle_negative', 'max') not in ['max', 'abs', 'nan']:
            raise ValueError("handle_negative 必须是 'max', 'abs' 或 'nan'")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        ev = data['ev']
        ebitda = data['ebitda']
        
        ev_ebitda = ev / ebitda.replace(0, np.nan)
        handle_negative = self.params['handle_negative']
        
        if handle_negative == 'max':
            max_val = ev_ebitda[ev_ebitda > 0].max()
            ev_ebitda[ev_ebitda <= 0] = max_val
        elif handle_negative == 'abs':
            ev_ebitda = ev_ebitda.abs()
        elif handle_negative == 'nan':
            ev_ebitda[ev_ebitda <= 0] = np.nan
        
        return ev_ebitda


class PEGFactor(BaseFactor):
    """
    PEG因子 (Price/Earnings-to-Growth Ratio)
    
    计算公式: PEG = PE / 盈利增长率
    
    理论依据:
        Peter Lynch提出的估值指标，将PE与增长率结合。
        PEG < 1 表示低估，PEG > 1 表示高估。
        平衡了估值与成长性。
    
    学术出处:
        Peter Lynch "One Up on Wall Street"
    
    使用说明:
        - 方向: negative (低PEG更优)
        - 适用: 盈利且增长的公司
        - 注意: 增长率波动大的公司PEG不稳定
    """
    
    name = "peg_ratio"
    category = "fundamental"
    description = "PEG因子（PE/盈利增长率）"
    
    def __init__(self, handle_negative: str = 'max', growth_floor: float = 0.05):
        """
        Args:
            handle_negative: 负值处理方式
            growth_floor: 增长率下限，避免极低增长率导致PEG过大
        """
        super().__init__(handle_negative=handle_negative, growth_floor=growth_floor)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['pe_ratio', 'eps_growth']
    
    def _validate_params(self):
        if self.params.get('handle_negative', 'max') not in ['max', 'abs', 'nan']:
            raise ValueError("handle_negative 必须是 'max', 'abs' 或 'nan'")
        if self.params.get('growth_floor', 0.05) <= 0:
            raise ValueError("growth_floor 必须大于0")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        pe = data['pe_ratio']
        eps_growth = data['eps_growth']
        
        growth_floor = self.params['growth_floor']
        eps_growth = eps_growth.clip(lower=growth_floor)
        
        peg = pe / (eps_growth * 100)
        handle_negative = self.params['handle_negative']
        
        if handle_negative == 'max':
            max_val = peg[peg > 0].max()
            peg[peg <= 0] = max_val
        elif handle_negative == 'abs':
            peg = peg.abs()
        elif handle_negative == 'nan':
            peg[peg <= 0] = np.nan
        
        return peg


class PCFFactor(BaseFactor):
    """
    股价现金流比因子 (Price-to-Cash-Flow Ratio)
    
    计算公式: PCF = 股价 / 每股现金流
    
    理论依据:
        现金流比利润更难操纵，PCF是更可靠的估值指标。
        Sloan (1996) 发现应计项目较低的股票表现更好。
    
    学术出处:
        Sloan, R. G. (1996) "Do Stock Prices Reflect Information in Accruals and Cash Flows?"
    
    使用说明:
        - 方向: negative (低PCF更优)
        - 适用: 所有公司
        - 注意: 资本密集型公司现金流波动大
    """
    
    name = "pcf_ratio"
    category = "fundamental"
    description = "股价现金流比因子（股价/每股现金流）"
    
    def __init__(self, handle_negative: str = 'max'):
        super().__init__(handle_negative=handle_negative)
    
    @property
    def author(self) -> str:
        return "factor_team"
    
    @property
    def required_data(self) -> List[str]:
        return ['price', 'operating_cash_flow', 'shares_outstanding']
    
    def _validate_params(self):
        if self.params.get('handle_negative', 'max') not in ['max', 'abs', 'nan']:
            raise ValueError("handle_negative 必须是 'max', 'abs' 或 'nan'")
    
    def compute(self, data: pd.DataFrame) -> pd.Series:
        price = data['price']
        ocf = data['operating_cash_flow']
        shares = data['shares_outstanding']
        
        ocf_per_share = ocf / shares.replace(0, np.nan)
        pcf = price / ocf_per_share.replace(0, np.nan)
        
        handle_negative = self.params['handle_negative']
        
        if handle_negative == 'max':
            max_val = pcf[pcf > 0].max()
            pcf[pcf <= 0] = max_val
        elif handle_negative == 'abs':
            pcf = pcf.abs()
        elif handle_negative == 'nan':
            pcf[pcf <= 0] = np.nan
        
        return pcf
