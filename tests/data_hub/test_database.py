"""Tests for database manager."""

import pytest
import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from trader_center.data_hub.models import Base, Symbol
from trader_center.data_hub.database import DatabaseManager


class TestDatabaseManager:
    def setup_method(self):
        """Reset singleton before each test."""
        DatabaseManager._instance = None
        DatabaseManager._engine = None
        DatabaseManager._session_factory = None

    def teardown_method(self):
        """Close database connection after each test."""
        db = DatabaseManager()
        db.close()
        DatabaseManager._instance = None
        DatabaseManager._engine = None
        DatabaseManager._session_factory = None

    def test_singleton_instance(self):
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        assert db1 is db2

    def test_init_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseManager()
            db.init_database(db_path)
            assert os.path.exists(db_path)
            db.close()  # Close before temp dir cleanup

    def test_get_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseManager()
            db.init_database(db_path)
            session = db.get_session()
            assert session is not None

            # Test that we can actually use the session
            symbol = Symbol(code="TEST", name="Test", market="CN", exchange="TEST")
            session.add(symbol)
            session.commit()

            result = session.query(Symbol).first()
            assert result.code == "TEST"
            session.close()
            db.close()  # Close before temp dir cleanup

    def test_not_initialized_error(self):
        self.setup_method()  # Reset to ensure not initialized
        db = DatabaseManager()
        with pytest.raises(RuntimeError, match="Database not initialized"):
            db.get_session()
