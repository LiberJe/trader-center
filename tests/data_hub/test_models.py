import pytest
from datetime import datetime, date
from trader_center.data_hub.models import (
    BarData,
    SymbolInfo,
    FinancialReport,
    MacroData,
    Frequency,
)


class TestBarData:
    def test_create_bar(self):
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 1, 9, 30),
            frequency=Frequency.DAILY,
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            volume=10000.0,
        )
        assert bar.symbol == "000001.SZ"
        assert bar.close == 10.5

    def test_bar_is_frozen(self):
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 1),
            frequency=Frequency.DAILY,
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=100.0,
        )
        with pytest.raises(Exception):
            bar.close = 11.0

    def test_bar_with_optional_fields(self):
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 1),
            frequency=Frequency.DAILY,
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            volume=10000.0,
            amount=105000.0,
            adj_factor=1.05,
            is_suspended=False,
        )
        assert bar.amount == 105000.0


class TestSymbolInfo:
    def test_create_symbol(self):
        symbol = SymbolInfo(
            symbol="000001.SZ",
            name="平安银行",
            exchange="SZ",
            type="stock",
            list_date=date(1991, 4, 3),
            industry="银行",
        )
        assert symbol.name == "平安银行"

    def test_symbol_exchange_validation(self):
        with pytest.raises(ValueError):
            SymbolInfo(
                symbol="INVALID", name="Invalid", exchange="XX"  # Invalid exchange
            )
