"""
价量关系因子

包含10个价格和成交量关系因子：EOM、力量指数、成交量变化率等。
"""

import pandas as pd
import numpy as np

from trader_center.factor.library.base import BaseFactor


class EaseOfMovement(BaseFactor):
    """
    简易波动指标因子 (EOM)

    衡量价格变动与成交量的关系，反映价格移动的难易程度。

    Params:
        period: 周期，默认14天
    """

    name = "ease_of_movement"
    category = "technical"
    description = "简易波动指标"

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

        high = data['high']
        low = data['low']
        volume = data['volume']

        # 距离移动
        distance_moved = ((high + low) / 2) - ((high.shift(1) + low.shift(1)) / 2)

        # 箱形比率
        box_ratio = volume / (high - low)

        # 原始EOM
        eom_raw = distance_moved / box_ratio

        # 平滑
        eom = eom_raw.rolling(window=period).mean()

        return eom


class ForceIndex(BaseFactor):
    """
    力量指数因子

    结合价格和成交量的动量指标。

    Params:
        period: 周期，默认13天
    """

    name = "force_index"
    category = "technical"
    description = "力量指数"

    def __init__(self, period: int = 13):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 13) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']

        close = data['close']
        volume = data['volume']

        # 原始力量指数
        force_raw = (close - close.shift(1)) * volume

        # EMA平滑
        force_index = force_raw.ewm(span=period, adjust=False).mean()

        return force_index


class NegativeVolumeIndex(BaseFactor):
    """
    负成交量指标因子 (NVI)

    关注成交量比前一日低的价格变动。

    Params:
        initial_value: 初始值，默认1000
    """

    name = "negative_volume_index"
    category = "technical"
    description = "负成交量指标"

    def __init__(self, initial_value: float = 1000):
        super().__init__(initial_value=initial_value)

    @property
    def author(self) -> str:
        return "factor_team"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        initial = self.params['initial_value']

        close = data['close']
        volume = data['volume']

        price_change = close.pct_change()
        volume_decrease = volume < volume.shift(1)

        nvi = pd.Series(index=close.index, dtype=float)
        nvi.iloc[0] = initial

        for i in range(1, len(close)):
            if volume_decrease.iloc[i]:
                nvi.iloc[i] = nvi.iloc[i-1] * (1 + price_change.iloc[i])
            else:
                nvi.iloc[i] = nvi.iloc[i-1]

        return nvi


class PositiveVolumeIndex(BaseFactor):
    """
    正成交量指标因子 (PVI)

    关注成交量比前一日高的价格变动。

    Params:
        initial_value: 初始值，默认1000
    """

    name = "positive_volume_index"
    category = "technical"
    description = "正成交量指标"

    def __init__(self, initial_value: float = 1000):
        super().__init__(initial_value=initial_value)

    @property
    def author(self) -> str:
        return "factor_team"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        initial = self.params['initial_value']

        close = data['close']
        volume = data['volume']

        price_change = close.pct_change()
        volume_increase = volume > volume.shift(1)

        pvi = pd.Series(index=close.index, dtype=float)
        pvi.iloc[0] = initial

        for i in range(1, len(close)):
            if volume_increase.iloc[i]:
                pvi.iloc[i] = pvi.iloc[i-1] * (1 + price_change.iloc[i])
            else:
                pvi.iloc[i] = pvi.iloc[i-1]

        return pvi


class VolumeRateOfChange(BaseFactor):
    """
    成交量变化率因子 (VROC)

    衡量成交量的变化速度。

    Params:
        period: 周期，默认14天
    """

    name = "volume_rate_of_change"
    category = "technical"
    description = "成交量变化率"

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
        volume = data['volume']

        vroc = ((volume - volume.shift(period)) / volume.shift(period)) * 100

        return vroc


class PriceVolumeTrend(BaseFactor):
    """
    价量趋势因子 (PVT)

    累积的价量变化，类似OBV但使用百分比变化。

    Params:
        initial_value: 初始值，默认0
    """

    name = "price_volume_trend"
    category = "technical"
    description = "价量趋势"

    def __init__(self, initial_value: float = 0):
        super().__init__(initial_value=initial_value)

    @property
    def author(self) -> str:
        return "factor_team"

    def compute(self, data: pd.DataFrame) -> pd.Series:
        initial = self.params['initial_value']

        close = data['close']
        volume = data['volume']

        price_change_pct = close.pct_change()
        pvt_change = price_change_pct * volume

        pvt = pvt_change.cumsum() + initial

        return pvt


class TradeIntensity(BaseFactor):
    """
    交易强度因子

    衡量单位价格变动对应的成交量。

    Params:
        period: 周期，默认20天
    """

    name = "trade_intensity"
    category = "technical"
    description = "交易强度"

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

        price_change = close.diff().abs()

        intensity = volume / price_change.replace(0, np.nan)
        intensity_smooth = intensity.rolling(window=period).mean()

        return intensity_smooth


class VolumeProfile(BaseFactor):
    """
    成交量分布因子

    计算当前成交量在历史分布中的位置。

    Params:
        period: 周期，默认60天
    """

    name = "volume_profile"
    category = "technical"
    description = "成交量分布"

    def __init__(self, period: int = 60):
        super().__init__(period=period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('period', 60) <= 0:
            raise ValueError("period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        period = self.params['period']
        volume = data['volume']

        rank = volume.rolling(window=period).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) >= period else np.nan,
            raw=False
        )

        return rank


class OBVEMFactor(BaseFactor):
    """
    OBV指数平滑因子

    对OBV进行指数平滑处理。

    Params:
        obv_period: OBV计算周期，默认1（日度）
        ema_period: EMA平滑周期，默认20天
    """

    name = "on_balance_volume_ema"
    category = "technical"
    description = "OBV指数平滑"

    def __init__(self, obv_period: int = 1, ema_period: int = 20):
        super().__init__(obv_period=obv_period, ema_period=ema_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('ema_period', 20) <= 0:
            raise ValueError("ema_period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        ema_period = self.params['ema_period']

        close = data['close']
        volume = data['volume']

        # 计算OBV
        price_change = close.diff()
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]

        for i in range(1, len(close)):
            if price_change.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif price_change.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]

        # EMA平滑
        obv_ema = obv.ewm(span=ema_period, adjust=False).mean()

        return obv_ema


class VolumeDivergence(BaseFactor):
    """
    成交量背离因子

    检测价格与成交量的背离情况。

    Params:
        price_period: 价格变化周期，默认10天
        volume_period: 成交量变化周期，默认10天
    """

    name = "volume_divergence"
    category = "technical"
    description = "成交量背离"

    def __init__(self, price_period: int = 10, volume_period: int = 10):
        super().__init__(price_period=price_period, volume_period=volume_period)

    @property
    def author(self) -> str:
        return "factor_team"

    def _validate_params(self):
        if self.params.get('price_period', 10) <= 0:
            raise ValueError("price_period 必须大于0")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        price_p = self.params['price_period']
        volume_p = self.params['volume_period']

        close = data['close']
        volume = data['volume']

        # 价格变化方向
        price_change = close.diff(price_p)

        # 成交量变化方向
        volume_ma = volume.rolling(window=volume_p).mean()
        volume_change = volume - volume_ma

        # 背离信号：价格上涨但成交量下降为负，价格下跌但成交量下降为正
        divergence = np.where(
            (price_change > 0) & (volume_change < 0), -1,  # 顶背离
            np.where(
                (price_change < 0) & (volume_change < 0), 1,  # 底背离
                0  # 无背离
            )
        )

        return pd.Series(divergence, index=close.index)
