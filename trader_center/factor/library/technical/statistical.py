"""
统计/数学因子

包含12个统计和数学因子：线性回归、相关性、分布统计等。
"""

import pandas as pd
import numpy as np
from scipy import stats

from trader_center.factor.library.base import BaseFactor


class LinearRegressionSlope(BaseFactor):
    """
    线性回归斜率因子

    计算价格序列的线性回归斜率。

    Params:
        period: 周期，默认20天
    """

    name = "linear_regression_slope"
    category = "technical"
    description = "线性回归斜率"

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

        x = np.arange(period)

        def calc_slope(y):
            if len(y) < period:
                return np.nan
            slope, _, _, _, _ = stats.linregress(x, y)
            return slope

        slope = close.rolling(window=period).apply(calc_slope, raw=True)

        return slope


class LinearRegressionAngle(BaseFactor):
    """
    线性回归角度因子

    计算线性回归斜率对应的角度（度）。

    Params:
        period: 周期，默认20天
    """

    name = "linear_regression_angle"
    category = "technical"
    description = "线性回归角度"

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

        x = np.arange(period)

        def calc_angle(y):
            if len(y) < period:
                return np.nan
            slope, _, _, _, _ = stats.linregress(x, y)
            return np.degrees(np.arctan(slope))

        angle = close.rolling(window=period).apply(calc_angle, raw=True)

        return angle


class LinearRegressionIntercept(BaseFactor):
    """
    线性回归截距因子

    计算价格序列线性回归的截距。

    Params:
        period: 周期，默认20天
    """

    name = "linear_regression_intercept"
    category = "technical"
    description = "线性回归截距"

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

        x = np.arange(period)

        def calc_intercept(y):
            if len(y) < period:
                return np.nan
            _, intercept, _, _, _ = stats.linregress(x, y)
            return intercept

        intercept = close.rolling(window=period).apply(calc_intercept, raw=True)

        return intercept


class RSquared(BaseFactor):
    """
    R平方值因子

    线性回归的决定系数，衡量趋势强度。

    Params:
        period: 周期，默认20天
    """

    name = "r_squared"
    category = "technical"
    description = "R平方值"

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

        x = np.arange(period)

        def calc_r2(y):
            if len(y) < period:
                return np.nan
            _, _, r_value, _, _ = stats.linregress(x, y)
            return r_value ** 2

        r2 = close.rolling(window=period).apply(calc_r2, raw=True)

        return r2


class CorrelationPriceVolume(BaseFactor):
    """
    价量相关性因子

    计算价格变化与成交量的相关系数。

    Params:
        period: 周期，默认20天
    """

    name = "correlation_price_volume"
    category = "technical"
    description = "价量相关性"

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

        price_change = close.pct_change()

        correlation = price_change.rolling(window=period).corr(volume)

        return correlation


class AutocorrelationFactor(BaseFactor):
    """
    自相关性因子

    计算收益率与自身滞后值的相关系数。

    Params:
        period: 计算周期，默认20天
        lag: 滞后阶数，默认1天
    """

    name = "autocorrelation"
    category = "technical"
    description = "自相关性"

    def __init__(self, period: int = 20, lag: int = 1):
        super().__init__(period=period, lag=lag)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        lag = self.params['lag']

        returns = data['close'].pct_change()

        autocorr = returns.rolling(window=period).apply(
            lambda x: x.corr(x.shift(lag)) if len(x) >= period else np.nan,
            raw=False
        )

        return autocorr


class SkewnessFactor(BaseFactor):
    """
    收益率偏度因子

    衡量收益率分布的不对称性。

    Params:
        period: 周期，默认20天
    """

    name = "skewness"
    category = "technical"
    description = "收益率偏度"

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
        returns = data['close'].pct_change()

        skew = returns.rolling(window=period).skew()

        return skew


class KurtosisFactor(BaseFactor):
    """
    收益率峰度因子

    衡量收益率分布的尾部厚度。

    Params:
        period: 周期，默认20天
    """

    name = "kurtosis"
    category = "technical"
    description = "收益率峰度"

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
        returns = data['close'].pct_change()

        kurt = returns.rolling(window=period).kurt()

        return kurt


class VarianceFactor(BaseFactor):
    """
    收益率方差因子

    衡量收益率的离散程度。

    Params:
        period: 周期，默认20天
    """

    name = "variance"
    category = "technical"
    description = "收益率方差"

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
        returns = data['close'].pct_change()

        variance = returns.rolling(window=period).var()

        return variance


class StandardErrorFactor(BaseFactor):
    """
    标准误差因子

    线性回归斜率的标准误差。

    Params:
        period: 周期，默认20天
    """

    name = "standard_error"
    category = "technical"
    description = "标准误差"

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

        x = np.arange(period)

        def calc_stderr(y):
            if len(y) < period:
                return np.nan
            _, _, _, _, stderr = stats.linregress(x, y)
            return stderr

        stderr = close.rolling(window=period).apply(calc_stderr, raw=True)

        return stderr


class MeanAbsoluteDeviation(BaseFactor):
    """
    平均绝对偏差因子

    价格与均线绝对偏差的均值。

    Params:
        period: 周期，默认20天
    """

    name = "mean_absolute_deviation"
    category = "technical"
    description = "平均绝对偏差"

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

        ma = close.rolling(window=period).mean()
        mad = (close - ma).abs().rolling(window=period).mean()

        return mad


class MedianPriceFactor(BaseFactor):
    """
    中位数价格因子

    计算一段时间内的价格中位数。

    Params:
        period: 周期，默认20天
    """

    name = "median_price"
    category = "technical"
    description = "中位数价格"

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

        median = close.rolling(window=period).median()

        return median
