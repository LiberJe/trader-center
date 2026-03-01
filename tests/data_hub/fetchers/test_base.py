"""Tests for base fetcher."""

import pytest
import pandas as pd
from datetime import date

from trader_center.data_hub.fetchers.base import BaseFetcher, FetcherError


class TestBaseFetcher:
    def test_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseFetcher()

    def test_fetcher_error(self):
        error = FetcherError("test error", source="test")
        assert str(error) == "[test] test error"


class ConcreteFetcher(BaseFetcher):
    @property
    def source_name(self) -> str:
        return "test"

    def fetch_daily_bars(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame({
            "date": [date(2024, 1, 1)],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000000],
        })

    def fetch_symbols(self) -> pd.DataFrame:
        return pd.DataFrame({
            "code": ["TEST001"],
            "name": ["Test Stock"],
            "market": ["CN"],
            "exchange": ["TEST"],
        })


class TestConcreteFetcher:
    def test_source_name(self):
        fetcher = ConcreteFetcher()
        assert fetcher.source_name == "test"

    def test_fetch_daily_bars(self):
        fetcher = ConcreteFetcher()
        df = fetcher.fetch_daily_bars("TEST001", date(2024, 1, 1), date(2024, 1, 31))
        assert not df.empty
        assert "date" in df.columns
        assert "close" in df.columns

    def test_validate_ohlcv_passes(self):
        fetcher = ConcreteFetcher()
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [1000000, 1100000],
        })
        result = fetcher.validate_ohlcv(df)
        assert len(result) == 2
        assert result["date"].iloc[0] == date(2024, 1, 1)

    def test_validate_ohlcv_missing_column(self):
        fetcher = ConcreteFetcher()
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "open": [100.0],
            # missing high, low, close, volume
        })
        with pytest.raises(FetcherError, match="Missing required column"):
            fetcher.validate_ohlcv(df)
