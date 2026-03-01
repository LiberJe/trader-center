# tests/backtest/test_data_feed.py
import pandas as pd
import pytest
from datetime import datetime, date


def test_pandas_data_feed_requires_required_columns():
    """测试 DataFeed 检查必需的 OHLCV 列"""
    from trader_center.backtest.data_feed import PandasDataFeed

    # 缺少必需列的 DataFrame
    df = pd.DataFrame({
        'close': [100.0, 101.0],
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        PandasDataFeed.validate_dataframe(df)


def test_pandas_data_feed_accepts_valid_dataframe():
    """测试有效的 DataFrame 通过验证"""
    from trader_center.backtest.data_feed import PandasDataFeed

    df = pd.DataFrame({
        'open': [100.0, 101.0],
        'high': [102.0, 103.0],
        'low': [99.0, 100.0],
        'close': [101.0, 102.0],
        'volume': [1000, 2000],
    }, index=pd.date_range('2024-01-01', periods=2))

    # 不应抛出异常
    PandasDataFeed.validate_dataframe(df)
