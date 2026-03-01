import pytest
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.storage.parquet_store import ParquetStorage
from trader_center.data_hub.models import BarData, Frequency


class TestParquetStorage:
    @pytest.fixture
    def storage(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            config = DataHubConfig(data_dir=tmpdir)
            store = ParquetStorage(config)
            yield store

    def test_save_and_get_daily_bars(self, storage):
        bars = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 1),
                frequency=Frequency.DAILY,
                open=10.0, high=11.0, low=9.5, close=10.5, volume=10000.0
            ),
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 2),
                frequency=Frequency.DAILY,
                open=10.5, high=10.8, low=10.2, close=10.6, volume=8000.0
            ),
        ]
        storage.save_bars(bars)

        df = storage.get_bars(
            "000001.SZ",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            "1d"
        )
        assert len(df) == 2
        assert df.iloc[0]['close'] == 10.5

    def test_get_data_range(self, storage):
        bars = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 15),
                frequency=Frequency.DAILY,
                open=10.0, high=11.0, low=9.5, close=10.5, volume=10000.0
            ),
        ]
        storage.save_bars(bars)

        start, end = storage.get_data_range("000001.SZ", "1d")
        assert start == datetime(2024, 1, 15)
        assert end == datetime(2024, 1, 15)

    def test_incremental_save(self, storage):
        """测试增量保存不会重复数据"""
        bars1 = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 1),
                frequency=Frequency.DAILY,
                open=10.0, high=11.0, low=9.5, close=10.5, volume=10000.0
            ),
        ]
        bars2 = [
            BarData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 2),
                frequency=Frequency.DAILY,
                open=10.5, high=10.8, low=10.2, close=10.6, volume=8000.0
            ),
        ]
        storage.save_bars(bars1)
        storage.save_bars(bars2)

        df = storage.get_bars(
            "000001.SZ",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            "1d"
        )
        assert len(df) == 2
