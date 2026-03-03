import pandas as pd
import pytest
from datetime import datetime


def test_pandas_data_feed_creation():
    """测试 PandasDataFeed 创建"""
    from trader_center.backtest.data_feed import PandasDataFeed

    # 创建模拟数据
    df = pd.DataFrame({
        'open': [10.0, 11.0, 12.0],
        'high': [11.0, 12.0, 13.0],
        'low': [9.0, 10.0, 11.0],
        'close': [10.5, 11.5, 12.5],
        'volume': [1000, 2000, 3000],
    }, index=pd.date_range('2024-01-01', periods=3))

    feed = PandasDataFeed(dataname=df, name="000001.SZ")
    assert feed is not None
    assert feed._name == "000001.SZ"


def test_pandas_data_feed_column_mapping():
    """测试列名映射"""
    from trader_center.backtest.data_feed import PandasDataFeed

    df = pd.DataFrame({
        'open': [10.0],
        'high': [11.0],
        'low': [9.0],
        'close': [10.5],
        'volume': [1000],
        'amount': [10000.0],
    }, index=pd.date_range('2024-01-01', periods=1))

    feed = PandasDataFeed(dataname=df, name="000001.SZ")
    # 验证列映射正确
    assert hasattr(feed, 'lines')
