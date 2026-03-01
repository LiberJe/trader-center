import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MonitorConfig:
    """Monitor 模块配置

    Attributes:
        data_dir: 数据存储目录
        log_dir: 日志存储目录
        max_retries: 网络请求最大重试次数
        retry_delay: 重试间隔（秒）
    """

    data_dir: Path = Path.home() / ".trader_center" / "monitor"
    log_dir: Path = Path.home() / ".trader_center" / "logs"
    max_retries: int = 3
    retry_delay: int = 2

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.log_dir = Path(self.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def report_dir(self) -> Path:
        """报告输出目录"""
        path = self.data_dir / "reports"
        path.mkdir(exist_ok=True)
        return path
