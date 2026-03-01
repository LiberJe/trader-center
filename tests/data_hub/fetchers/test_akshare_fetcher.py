import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from trader_center.data_hub.fetchers.akshare_fetcher import AkshareFetcher
from trader_center.data_hub.models import Frequency


class TestAkshareFetcher:
    @pytest.fixture
    def fetcher(self):
        return AkshareFetcher()

    def test_parse_symbol(self, fetcher):
        code, exchange = fetcher._parse_symbol("000001.SZ")
        assert code == "000001"
        assert exchange == "SZ"

    def test_parse_symbol_invalid(self, fetcher):
        with pytest.raises(ValueError):
            fetcher._parse_symbol("INVALID")

    def test_map_frequency(self, fetcher):
        assert fetcher._map_frequency("1d") == "daily"
        assert fetcher._map_frequency("5min") == "5"
        assert fetcher._map_frequency("unknown") == "daily"

    def test_get_bars(self, fetcher):
        # Mock akshare by setting _ak directly
        import pandas as pd

        mock_ak = Mock()
        mock_ak.stock_zh_a_hist.return_value = pd.DataFrame(
            {
                "日期": ["2024-01-01", "2024-01-02"],
                "开盘": [10.0, 10.5],
                "最高": [11.0, 10.8],
                "最低": [9.5, 10.2],
                "收盘": [10.5, 10.6],
                "成交量": [10000, 8000],
                "成交额": [105000, 84800],
            }
        )

        fetcher._ak = mock_ak
        bars = fetcher.get_bars(
            "000001.SZ", datetime(2024, 1, 1), datetime(2024, 1, 2), "1d"
        )

        assert len(bars) == 2
        assert bars[0].close == 10.5
        assert bars[1].close == 10.6
