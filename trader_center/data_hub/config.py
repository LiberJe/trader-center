import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DataHubConfig:
    """DataHub 配置"""

    data_dir: Path = Path.home() / ".trader_center" / "data"
    cache_size: int = 1000
    sqlite_db_name: str = "metadata.db"

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / self.sqlite_db_name

    @property
    def bars_dir(self) -> Path:
        path = self.data_dir / "bars"
        path.mkdir(exist_ok=True)
        return path
