"""
技术指标因子扩展

包含20个常见技术指标因子：随机指标、威廉指标、CCI、布林带、DMI、SAR等。
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class StochasticKD(BaseFactor):
    """
    随机指标K值因子

    计算快速随机指标的%K线，反映价格相对于一定周期内价格区间的位置。

    Params:
        period: 周期，默认14天
        smooth_k: K线平滑周期，默认3天
    """

    name = "stoch_kd"
    category = "technical"
    description = "随机指标K值"

    def __init__(self, period: int = 14, smooth_k: int = 3):
        super().__init__(period=period, smooth_k=smooth_k)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 14) <= 0:
            raise ValueError("period 必须大于0")
        if self.params.get('smooth_k', 3) <= 0:
            raise ValueError("smooth_k 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        smooth_k = self.params['smooth_k']

        low_min = data['low'].rolling(window=period).min()
        high_max = data['high'].rolling(window=period).max()

        k = 100 * (data['close'] - low_min) / (high_max - low_min)
        k = k.rolling(window=smooth_k).mean()

        return k


class StochasticKSlow(BaseFactor):
    """
    慢速随机指标K值因子

    对%K进行二次平滑得到慢速随机指标。

    Params:
        period: 周期，默认14天
        smooth_k: K线平滑周期，默认3天
        smooth_d: D线平滑周期，默认3天
    """

    name = "stoch_kslow"
    category = "technical"
    description = "慢速随机指标K值"

    def __init__(self, period: int = 14, smooth_k: int = 3, smooth_d: int = 3):
        super().__init__(period=period, smooth_k=smooth_k, smooth_d=smooth_d)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 14) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        smooth_k = self.params['smooth_k']
        smooth_d = self.params['smooth_d']

        low_min = data['low'].rolling(window=period).min()
        high_max = data['high'].rolling(window=period).max()

        k = 100 * (data['close'] - low_min) / (high_max - low_min)
        k_smooth = k.rolling(window=smooth_k).mean()
        d = k_smooth.rolling(window=smooth_d).mean()

        return d


class WilliamsR(BaseFactor):
    """
    威廉指标因子

    衡量收盘价相对于最高价和最低价区间的位置，与随机指标相反。

    Params:
        period: 周期，默认14天
    """

    name = "williams_r"
    category = "technical"
    description = "威廉指标"

    def __init__(self, period: int = 14):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 14) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']

        high_max = data['high'].rolling(window=period).max()
        low_min = data['low'].rolling(window=period).min()

        wr = -100 * (high_max - data['close']) / (high_max - low_min)

        return wr


class CCIFactor(BaseFactor):
    """
    顺势指标因子 (CCI)

    衡量价格相对于平均价格的偏离程度，用于判断超买超卖。

    Params:
        period: 周期，默认20天
    """

    name = "cci"
    category = "technical"
    description = "顺势指标"

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

        tp = (data['high'] + data['low'] + data['close']) / 3
        tp_sma = tp.rolling(window=period).mean()
        tp_mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        cci = (tp - tp_sma) / (0.015 * tp_mad)

        return cci


class BollingerPosition(BaseFactor):
    """
    布林带位置因子

    计算收盘价在布林带中的相对位置 (0-1)。

    Params:
        period: 周期，默认20天
        std_dev: 标准差倍数，默认2
    """

    name = "bollinger_position"
    category = "technical"
    description = "布林带位置"

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(period=period, std_dev=std_dev)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        std_dev = self.params['std_dev']

        middle = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()

        upper = middle + std_dev * std
        lower = middle - std_dev * std

        position = (data['close'] - lower) / (upper - lower)

        return position


class BollingerWidth(BaseFactor):
    """
    布林带宽度因子

    衡量布林带上下轨之间的距离，反映波动率。

    Params:
        period: 周期，默认20天
        std_dev: 标准差倍数，默认2
    """

    name = "bollinger_width"
    category = "technical"
    description = "布林带宽度"

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(period=period, std_dev=std_dev)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        std_dev = self.params['std_dev']

        middle = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()

        upper = middle + std_dev * std
        lower = middle - std_dev * std

        width = (upper - lower) / middle

        return width


class BollingerSqueeze(BaseFactor):
    """
    布林带挤压因子

    判断布林带是否处于收缩状态（低波动期）。

    Params:
        period: 周期，默认20天
        std_dev: 标准差倍数，默认2
        squeeze_period: 挤压判断周期，默认125天
    """

    name = "bollinger_squeeze"
    category = "technical"
    description = "布林带挤压"

    def __init__(self, period: int = 20, std_dev: float = 2.0, squeeze_period: int = 125):
        super().__init__(period=period, std_dev=std_dev, squeeze_period=squeeze_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        std_dev = self.params['std_dev']
        squeeze_period = self.params['squeeze_period']

        middle = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()

        upper = middle + std_dev * std
        lower = middle - std_dev * std

        width = upper - lower
        squeeze = width / width.rolling(window=squeeze_period).min()

        return squeeze


class DMIPlus(BaseFactor):
    """
    DMI+指标因子

    上升方向线，衡量上涨力度。

    Params:
        period: 周期，默认14天
    """

    name = "dmi_plus"
    category = "technical"
    description = "DMI+指标"

    def __init__(self, period: int = 14):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 14) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']

        high_diff = data['high'].diff()
        low_diff = -data['low'].diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift(1))
        tr3 = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr

        return plus_di


class DMIMinus(BaseFactor):
    """
    DMI-指标因子

    下降方向线，衡量下跌力度。

    Params:
        period: 周期，默认14天
    """

    name = "dmi_minus"
    category = "technical"
    description = "DMI-指标"

    def __init__(self, period: int = 14):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 14) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']

        high_diff = data['high'].diff()
        low_diff = -data['low'].diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift(1))
        tr3 = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr

        return minus_di


class ADXTrend(BaseFactor):
    """
    ADX趋势强度因子

    平均趋向指数，衡量趋势强度（非方向）。

    Params:
        period: 周期，默认14天
    """

    name = "adx_trend"
    category = "technical"
    description = "ADX趋势强度"

    def __init__(self, period: int = 14):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 14) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']

        high_diff = data['high'].diff()
        low_diff = -data['low'].diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift(1))
        tr3 = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period, adjust=False).mean()

        return adx


class SARFactor(BaseFactor):
    """
    抛物线转向因子 (SAR)

    抛物线停止和反转指标，用于追踪趋势。

    Params:
        acceleration: 加速因子，默认0.02
        max_acceleration: 最大加速因子，默认0.2
    """

    name = "sar"
    category = "technical"
    description = "抛物线转向"

    def __init__(self, acceleration: float = 0.02, max_acceleration: float = 0.2):
        super().__init__(acceleration=acceleration, max_acceleration=max_acceleration)

    @property
    def author(self) -> str:
        return "factor_team"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        af = self.params['acceleration']
        max_af = self.params['max_acceleration']

        high = data['high']
        low = data['low']
        close = data['close']

        n = len(close)
        sar = pd.Series(index=close.index, dtype=float)
        trend = pd.Series(index=close.index, dtype=float)

        # 初始化
        sar.iloc[0] = low.iloc[0]
        trend.iloc[0] = 1
        ep = high.iloc[0]
        af_curr = af

        for i in range(1, n):
            sar.iloc[i] = sar.iloc[i-1] + af_curr * (ep - sar.iloc[i-1])

            if trend.iloc[i-1] == 1:  # 上升趋势
                if low.iloc[i] < sar.iloc[i]:
                    trend.iloc[i] = -1
                    sar.iloc[i] = ep
                    ep = low.iloc[i]
                    af_curr = af
                else:
                    trend.iloc[i] = 1
                    if high.iloc[i] > ep:
                        ep = high.iloc[i]
                        af_curr = min(af_curr + af, max_af)
            else:  # 下降趋势
                if high.iloc[i] > sar.iloc[i]:
                    trend.iloc[i] = 1
                    sar.iloc[i] = ep
                    ep = high.iloc[i]
                    af_curr = af
                else:
                    trend.iloc[i] = -1
                    if low.iloc[i] < ep:
                        ep = low.iloc[i]
                        af_curr = min(af_curr + af, max_af)

        return sar


class IchimokuCloud(BaseFactor):
    """
    一目均衡表因子

    计算一目均衡表的延迟线（Chikou Span）。

    Params:
        tenkan_period: 转换线周期，默认9
        kijun_period: 基准线周期，默认26
        senkou_b_period: 先行上线B周期，默认52
    """

    name = "ichimoku_cloud"
    category = "technical"
    description = "一目均衡表延迟线"

    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52):
        super().__init__(tenkan_period=tenkan_period, kijun_period=kijun_period, senkou_b_period=senkou_b_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('tenkan_period', 9) <= 0:
            raise ValueError("tenkan_period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        tenkan_period = self.params['tenkan_period']
        kijun_period = self.params['kijun_period']

        tenkan_sen = (data['high'].rolling(window=tenkan_period).max() + data['low'].rolling(window=tenkan_period).min()) / 2
        kijun_sen = (data['high'].rolling(window=kijun_period).max() + data['low'].rolling(window=kijun_period).min()) / 2

        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)

        return senkou_span_a


class ParabolicSAR(BaseFactor):
    """
    抛物线SAR因子（简化版）

    返回SAR值相对于收盘价的位置。

    Params:
        period: 计算周期，默认14天
    """

    name = "parabolic_sar"
    category = "technical"
    description = "抛物线SAR相对位置"

    def __init__(self, period: int = 14):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']

        high_max = data['high'].rolling(window=period).max()
        low_min = data['low'].rolling(window=period).min()

        sar_pos = (data['close'] - (high_max + low_min) / 2) / (high_max - low_min)

        return sar_pos


class TRIXFactor(BaseFactor):
    """
    三重指数平滑因子 (TRIX)

    收盘价经过三次指数平滑后的变化率。

    Params:
        period: 周期，默认15天
    """

    name = "trix"
    category = "technical"
    description = "三重指数平滑"

    def __init__(self, period: int = 15):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 15) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']

        ema1 = data['close'].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()

        trix = ema3.pct_change() * 100

        return trix


class UltimateOscillator(BaseFactor):
    """
    终极震荡指标因子

    结合三个不同周期的买入压力与真实波幅。

    Params:
        short_period: 短周期，默认7天
        medium_period: 中周期，默认14天
        long_period: 长周期，默认28天
    """

    name = "ultimate_oscillator"
    category = "technical"
    description = "终极震荡指标"

    def __init__(self, short_period: int = 7, medium_period: int = 14, long_period: int = 28):
        super().__init__(short_period=short_period, medium_period=medium_period, long_period=long_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('short_period', 7) <= 0:
            raise ValueError("short_period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        short_p = self.params['short_period']
        medium_p = self.params['medium_period']
        long_p = self.params['long_period']

        close = data['close']
        low = data['low']
        high = data['high']

        buying_pressure = close - low.shift(1).combine(low, min)
        true_range = (high - low.shift(1)).combine(high.combine(low, max), max)

        avg_short = buying_pressure.rolling(short_p).sum() / true_range.rolling(short_p).sum()
        avg_medium = buying_pressure.rolling(medium_p).sum() / true_range.rolling(medium_p).sum()
        avg_long = buying_pressure.rolling(long_p).sum() / true_range.rolling(long_p).sum()

        uo = 100 * ((4 * avg_short) + (2 * avg_medium) + avg_long) / 7

        return uo


class AwesomeOscillator(BaseFactor):
    """
    动量震荡指标因子 (AO)

    中期均线与短期均线的差值。

    Params:
        short_period: 短周期，默认5天
        long_period: 长周期，默认34天
    """

    name = "awesome_oscillator"
    category = "technical"
    description = "动量震荡指标"

    def __init__(self, short_period: int = 5, long_period: int = 34):
        super().__init__(short_period=short_period, long_period=long_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('short_period', 5) <= 0:
            raise ValueError("short_period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        short_p = self.params['short_period']
        long_p = self.params['long_period']

        median_price = (data['high'] + data['low']) / 2

        short_sma = median_price.rolling(window=short_p).mean()
        long_sma = median_price.rolling(window=long_p).mean()

        ao = short_sma - long_sma

        return ao


class KeltnerChannel(BaseFactor):
    """
    肯特纳通道因子

    基于ATR的通道，返回价格在通道中的位置。

    Params:
        period: 周期，默认20天
        atr_multiplier: ATR乘数，默认2.0
    """

    name = "keltner_channel"
    category = "technical"
    description = "肯特纳通道位置"

    def __init__(self, period: int = 20, atr_multiplier: float = 2.0):
        super().__init__(period=period, atr_multiplier=atr_multiplier)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 20) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        atr_mult = self.params['atr_multiplier']

        tp = (data['high'] + data['low'] + data['close']) / 3
        middle = tp.rolling(window=period).mean()

        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift(1))
        tr3 = abs(data['low'] - data['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        upper = middle + atr_mult * atr
        lower = middle - atr_mult * atr

        position = (data['close'] - lower) / (upper - lower)

        return position


class DonchianChannel(BaseFactor):
    """
    唐奇安通道因子

    基于最高价和最低价的通道，返回突破信号。

    Params:
        period: 周期，默认20天
    """

    name = "donchian_channel"
    category = "technical"
    description = "唐奇安通道"

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

        upper = data['high'].rolling(window=period).max()
        lower = data['low'].rolling(window=period).min()

        position = (data['close'] - lower) / (upper - lower)

        return position


class ChaikinOscillator(BaseFactor):
    """
    蔡金震荡指标因子

    ADL的MACD指标。

    Params:
        fast_period: 快线周期，默认3天
        slow_period: 慢线周期，默认10天
    """

    name = "chaikin_oscillator"
    category = "technical"
    description = "蔡金震荡指标"

    def __init__(self, fast_period: int = 3, slow_period: int = 10):
        super().__init__(fast_period=fast_period, slow_period=slow_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('fast_period', 3) <= 0:
            raise ValueError("fast_period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        fast_p = self.params['fast_period']
        slow_p = self.params['slow_period']

        money_flow_multiplier = ((data['close'] - data['low']) - (data['high'] - data['close'])) / (data['high'] - data['low'])
        money_flow_volume = money_flow_multiplier * data['volume']

        adl = money_flow_volume.cumsum()

        adl_ema_fast = adl.ewm(span=fast_p, adjust=False).mean()
        adl_ema_slow = adl.ewm(span=slow_p, adjust=False).mean()

        co = adl_ema_fast - adl_ema_slow

        return co


class ChaikinMoneyFlow(BaseFactor):
    """
    蔡金资金流量因子 (CMF)

    衡量资金流入流出的强度。

    Params:
        period: 周期，默认20天
    """

    name = "cmf"
    category = "technical"
    description = "蔡金资金流量"

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

        money_flow_multiplier = ((data['close'] - data['low']) - (data['high'] - data['close'])) / (data['high'] - data['low'])
        money_flow_volume = money_flow_multiplier * data['volume']

        cmf = money_flow_volume.rolling(window=period).sum() / data['volume'].rolling(window=period).sum()

        return cmf
