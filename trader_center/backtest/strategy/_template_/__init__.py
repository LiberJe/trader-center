"""策略模板模块

此目录作为创建新策略的模板。
复制此目录并重命名以创建新策略。
"""
from .index import TemplateStrategy
from .config import TemplateConfig, DEFAULT_CONFIG

__all__ = [
    "TemplateStrategy",
    "TemplateConfig",
    "DEFAULT_CONFIG",
]
