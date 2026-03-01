"""Database connection manager."""

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from trader_center.data_hub.models import Base


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None
    _engine = None
    _session_factory = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init_database(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = Path.home() / ".trader_center" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "trader_center.db"

        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def get_session(self) -> Session:
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call init_database() first.")
        return self._session_factory()

    def get_engine(self):
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call init_database() first.")
        return self._engine

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


def get_db() -> DatabaseManager:
    return DatabaseManager()
