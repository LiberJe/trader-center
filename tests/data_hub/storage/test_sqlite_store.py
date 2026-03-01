import pytest
import tempfile
import uuid
from datetime import datetime, date
from pathlib import Path

from trader_center.data_hub.config import DataHubConfig
from trader_center.data_hub.storage.sqlite_store import SQLiteStorage
from trader_center.data_hub.models import SymbolInfo, FinancialReport


class TestSQLiteStorage:
    @pytest.fixture
    def storage(self):
        # ignore_cleanup_errors=True for Windows SQLite file locking
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            # Use unique db name per test to avoid Windows file locking issues
            config = DataHubConfig(
                data_dir=tmpdir, sqlite_db_name=f"test_{uuid.uuid4().hex}.db"
            )
            store = SQLiteStorage(config)
            yield store

    def test_save_and_get_symbols(self, storage):
        symbols = [
            SymbolInfo(symbol="000001.SZ", name="平安银行", exchange="SZ"),
            SymbolInfo(symbol="600000.SH", name="浦发银行", exchange="SH"),
        ]
        storage.save_symbols(symbols)

        result = storage.get_symbols()
        assert len(result) == 2
        assert result[0].symbol == "000001.SZ"

    def test_get_symbols_by_exchange(self, storage):
        symbols = [
            SymbolInfo(symbol="000001.SZ", name="平安银行", exchange="SZ"),
            SymbolInfo(symbol="600000.SH", name="浦发银行", exchange="SH"),
        ]
        storage.save_symbols(symbols)

        sz_symbols = storage.get_symbols(exchange="SZ")
        assert len(sz_symbols) == 1
        assert sz_symbols[0].exchange == "SZ"
