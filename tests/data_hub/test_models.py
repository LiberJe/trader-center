"""Tests for database models."""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from trader_center.data_hub.models import Base, Symbol, DailyBar, Watchlist


class TestModels:
    @pytest.fixture
    def session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    def test_create_symbol(self, session):
        symbol = Symbol(
            code="000001.SZ",
            name="平安银行",
            market="CN",
            exchange="SZSE",
            category="stock"
        )
        session.add(symbol)
        session.commit()

        result = session.query(Symbol).first()
        assert result.code == "000001.SZ"
        assert result.name == "平安银行"

    def test_create_daily_bar(self, session):
        symbol = Symbol(code="000001.SZ", name="平安银行", market="CN", exchange="SZSE")
        session.add(symbol)
        session.commit()

        bar = DailyBar(
            symbol_id=symbol.id,
            date=date(2024, 1, 15),
            open=10.5,
            high=10.8,
            low=10.3,
            close=10.6,
            volume=1000000,
            amount=10500000.0
        )
        session.add(bar)
        session.commit()

        result = session.query(DailyBar).first()
        assert result.close == 10.6
        assert result.symbol.code == "000001.SZ"

    def test_watchlist(self, session):
        symbol = Symbol(code="000001.SZ", name="平安银行", market="CN", exchange="SZSE")
        session.add(symbol)
        session.commit()

        watch = Watchlist(symbol_id=symbol.id, group_name="tech")
        session.add(watch)
        session.commit()

        result = session.query(Watchlist).first()
        assert result.group_name == "tech"
