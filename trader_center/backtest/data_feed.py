# trader_center/backtest/data_feed.py
"""Data feed adapters for backtest engine."""

import backtrader as bt
import pandas as pd


REQUIRED_COLUMNS = {'open', 'high', 'low', 'close', 'volume'}


class PandasDataFeed(bt.feeds.PandasData):
    """适配 DataHub 输出的 DataFrame.

    DataHub 返回的 DataFrame 列名: open, high, low, close, volume
    backtrader 默认期望的列名: Open, High, Low, Close, Volume
    """
    params = (
        ('datetime', None),      # 使用索引作为日期
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> None:
        """验证 DataFrame 包含必需的 OHLCV 列."""
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if df.empty:
            raise ValueError("DataFrame is empty")

        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
