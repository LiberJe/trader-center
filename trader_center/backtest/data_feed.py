"""
DataHub → Backtrader 数据适配器

将 DataHub 获取的 pandas DataFrame 转换为 backtrader 可用的数据 feed。
"""

import backtrader as bt
import pandas as pd
from datetime import datetime
from typing import Optional


class PandasDataFeed(bt.feeds.PandasData):
    """
    基于 pandas DataFrame 的数据适配器

    适配 DataHub 返回的数据格式，支持 A股日线数据。

    Args:
        dataname: pandas DataFrame，包含 open/high/low/close/volume
        name: 股票代码，如 "000001.SZ"

    Example:
        >>> df = data_hub.get_daily_bars("000001.SZ", "2024-01-01", "2024-12-31")
        >>> feed = PandasDataFeed(dataname=df, name="000001.SZ")
        >>> cerebro.adddata(feed)
    """

    # 定义列映射（DataHub 列名 -> backtrader 字段）
    params = (
        ('datetime', None),  # 使用 DataFrame index 作为 datetime
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),  # A股无持仓量概念
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._symbol = kwargs.get('name', 'unknown')

    @classmethod
    def from_datahub(cls, symbol: str, df: pd.DataFrame) -> 'PandasDataFeed':
        """
        从 DataHub 数据创建 feed

        Args:
            symbol: 股票代码
            df: DataHub 返回的 DataFrame

        Returns:
            PandasDataFeed 实例

        Raises:
            ValueError: 如果 DataFrame 缺少必要列
        """
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame 缺少必要列: {missing}")

        # 确保 index 是 datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            else:
                raise ValueError("DataFrame 需要 datetime index 或 timestamp 列")

        return cls(dataname=df, name=symbol)
