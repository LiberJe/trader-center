"""
移动平均线扩展因子

包含8种高级移动平均线因子：WMA、VWMA、DEMA、TEMA、KAMA等。
"""

import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class WMAFactor(BaseFactor):
    """
    加权移动平均线因子

    线性加权移动平均，近期价格权重更高。

    Params:
        period: 周期，默认20天
    """

    name = "wma"
    category = "technical"
    description = "加权移动平均线"

    def __init__(self, period: int = 20):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        close = data['close']

        weights = np.arange(1, period + 1)
        wma = close.rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

        return wma


class VWMAFactor(BaseFactor):
    """
    成交量加权移动平均线因子

    以成交量为权重的移动平均线。

    Params:
        period: 周期，默认20天
    """

    name = "vwma"
    category = "technical"
    description = "成交量加权移动平均线"

    def __init__(self, period: int = 20):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        close = data['close']
        volume = data['volume']

        vwma = (close * volume).rolling(window=period).sum() / volume.rolling(window=period).sum()

        return vwma


class DEMAFactor(BaseFactor):
    """
    双指数移动平均线因子 (DEMA)

    减少EMA滞后性的改进版本。

    Params:
        period: 周期，默认20天
    """

    name = "dema"
    category = "technical"
    description = "双指数移动平均线"

    def __init__(self, period: int = 20):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        close = data['close']

        ema1 = close.ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()

        dema = 2 * ema1 - ema2

        return dema


class TEMAFactor(BaseFactor):
    """
    三指数移动平均线因子 (TEMA)

    进一步减少滞后性的三重EMA平滑。

    Params:
        period: 周期，默认20天
    """

    name = "tema"
    category = "technical"
    description = "三指数移动平均线"

    def __init__(self, period: int = 20):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        close = data['close']

        ema1 = close.ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()

        tema = 3 * ema1 - 3 * ema2 + ema3

        return tema


class KAMAFactor(BaseFactor):
    """
    考夫曼自适应移动平均线因子 (KAMA)

    根据市场效率自动调整平滑系数。

    Params:
        period: 效率比率周期，默认10天
        fast_period: 快速EMA周期，默认2天
        slow_period: 慢速EMA周期，默认30天
    """

    name = "kama"
    category = "technical"
    description = "考夫曼自适应移动平均线"

    def __init__(self, period: int = 10, fast_period: int = 2, slow_period: int = 30):
        super().__init__(period=period, fast_period=fast_period, slow_period=slow_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 10) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        fast_p = self.params['fast_period']
        slow_p = self.params['slow_period']

        close = data['close']

        # 价格变化
        change = abs(close - close.shift(period))

        # 波动总和
        volatility = abs(close.diff()).rolling(window=period).sum()

        # 效率比率
        er = change / volatility
        er = er.fillna(0)

        # 平滑常数
        fast_sc = 2 / (fast_p + 1)
        slow_sc = 2 / (slow_p + 1)
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

        # KAMA计算
        kama = pd.Series(index=close.index, dtype=float)
        kama.iloc[0] = close.iloc[0]

        for i in range(1, len(close)):
            kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (close.iloc[i] - kama.iloc[i-1])

        return kama


class ALMAFactor(BaseFactor):
    """
    阿尔玛移动平均线因子 (ALMA)

    使用高斯分布加权的移动平均线，减少滞后和噪音。

    Params:
        period: 周期，默认20天
        offset: 偏移量(0-1)，默认0.85
        sigma: 标准差，默认6
    """

    name = "alma"
    category = "technical"
    description = "阿尔玛移动平均线"

    def __init__(self, period: int = 20, offset: float = 0.85, sigma: float = 6):
        super().__init__(period=period, offset=offset, sigma=sigma)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        offset = self.params['offset']
        sigma = self.params['sigma']
        close = data['close']

        m = np.floor(offset * (period - 1))
        s = period / sigma

        weights = np.exp(-((np.arange(period) - m) ** 2) / (2 * s ** 2))
        weights = weights / weights.sum()

        alma = close.rolling(window=period).apply(
            lambda x: np.dot(x, weights), raw=True
        )

        return alma


class HullMAFactor(BaseFactor):
    """
    赫尔移动平均线因子 (HMA)

    快速且平滑的移动平均线，减少滞后。

    Params:
        period: 周期，默认16天
    """

    name = "hull_ma"
    category = "technical"
    description = "赫尔移动平均线"

    def __init__(self, period: int = 16):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 16) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        close = data['close']

        half_period = period // 2
        sqrt_period = int(np.sqrt(period))

        wma_half = close.rolling(window=half_period).mean()
        wma_full = close.rolling(window=period).mean()

        raw_hma = 2 * wma_half - wma_full

        hull_ma = raw_hma.rolling(window=sqrt_period).mean()

        return hull_ma


class ZLEMAFactor(BaseFactor):
    """
    零滞后EMA因子 (ZLEMA)

    通过移除价格延迟来减少滞后。

    Params:
        period: 周期，默认20天
    """

    name = "zlema"
    category = "technical"
    description = "零滞后EMA"

    def __init__(self, period: int = 20):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        close = data['close']

        lag = (period - 1) // 2
        ema_data = 2 * close - close.shift(lag)

        zlema = ema_data.ewm(span=period, adjust=False).mean()

        return zlema
