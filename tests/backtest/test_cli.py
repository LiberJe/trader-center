import pytest


def test_cli_import():
    """测试 CLI 模块可导入"""
    from trader_center.backtest.cli import main
    assert callable(main)
