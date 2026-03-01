"""CLI 测试"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from trader_center.monitor import cli


def test_parse_date_iso():
    """测试 ISO 格式日期解析"""
    result = cli.parse_date("2025-08-26")
    assert result == date(2025, 8, 26)


def test_parse_date_compact():
    """测试紧凑格式日期解析"""
    result = cli.parse_date("20250826")
    assert result == date(2025, 8, 26)


def test_parse_date_none():
    """测试 None 返回今日"""
    result = cli.parse_date(None)
    assert result == date.today()


def test_parse_date_invalid():
    """测试无效日期格式"""
    with pytest.raises(cli.DateParseError):
        cli.parse_date("invalid")


def test_format_value_yi():
    """测试亿单位格式化"""
    assert cli.format_value(150000000) == "+1.50亿"
    assert cli.format_value(-150000000) == "-1.50亿"


def test_format_value_wan():
    """测试万单位格式化"""
    assert cli.format_value(15000) == "+1.50万"


def test_format_value_yuan():
    """测试元单位格式化"""
    assert cli.format_value(150) == "+150.00"


@patch('trader_center.monitor.task_router.get_task_router')
def test_main_list(mock_get_router, capsys):
    """测试列出任务"""
    mock_router = MagicMock()
    mock_router.list_tasks.return_value = ['fund_flow', 'another']
    mock_router.get_task_info.side_effect = lambda x: {
        'fund_flow': {'name': 'fund_flow', 'description': 'Fund flow task', 'category': 'data'},
        'another': {'name': 'another', 'description': 'Another task', 'category': 'data'}
    }.get(x)
    mock_get_router.return_value = mock_router

    with pytest.raises(SystemExit) as exc:
        with patch('sys.argv', ['monitor', '--list']):
            cli.main()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    assert 'fund_flow' in captured.out


@patch('trader_center.monitor.task_router.get_task_router')
def test_main_execute_task(mock_get_router, capsys):
    """测试执行任务"""
    mock_router = MagicMock()
    mock_router.execute.return_value = {'status': 'success', 'data': 'test'}
    mock_router.get_task_info.return_value = {'name': 'fund_flow', 'category': 'data'}
    mock_get_router.return_value = mock_router

    with pytest.raises(SystemExit) as exc:
        with patch('sys.argv', ['monitor', 'fund_flow']):
            cli.main()
    assert exc.value.code == 0
    mock_router.execute.assert_called_once_with('fund_flow', target_date=date.today())


@patch('trader_center.monitor.task_router.get_task_router')
def test_main_task_not_found(mock_get_router, capsys):
    """测试任务不存在"""
    mock_router = MagicMock()
    mock_router.get_task_info.return_value = None
    mock_router.list_tasks.return_value = ['other_task']
    mock_get_router.return_value = mock_router

    with pytest.raises(SystemExit) as exc:
        with patch('sys.argv', ['monitor', 'nonexistent']):
            cli.main()
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert 'nonexistent' in captured.err or 'other_task' in captured.err


@patch('trader_center.monitor.task_router.get_task_router')
def test_main_no_task_name(mock_get_router):
    """测试未指定任务名称"""
    mock_router = MagicMock()
    mock_router.list_tasks.return_value = ['fund_flow']
    mock_get_router.return_value = mock_router

    with pytest.raises(SystemExit) as exc:
        with patch('sys.argv', ['monitor']):
            cli.main()
    assert exc.value.code == 1


@patch('trader_center.monitor.task_router.get_task_router')
def test_main_execute_with_date(mock_get_router):
    """测试指定日期执行任务"""
    mock_router = MagicMock()
    mock_router.execute.return_value = {'status': 'success'}
    mock_router.get_task_info.return_value = {'name': 'fund_flow', 'category': 'data'}
    mock_get_router.return_value = mock_router

    with pytest.raises(SystemExit) as exc:
        with patch('sys.argv', ['monitor', 'fund_flow', '--date', '2025-03-01']):
            cli.main()
    assert exc.value.code == 0
    mock_router.execute.assert_called_once_with('fund_flow', target_date=date(2025, 3, 1))


@patch('trader_center.monitor.task_router.get_task_router')
def test_main_skipped_status(mock_get_router, capsys):
    """测试任务跳过状态"""
    mock_router = MagicMock()
    mock_router.execute.return_value = {'status': 'skipped', 'reason': 'non_trading_day', 'date': date.today()}
    mock_router.get_task_info.return_value = {'name': 'fund_flow', 'category': 'data'}
    mock_get_router.return_value = mock_router

    with pytest.raises(SystemExit) as exc:
        with patch('sys.argv', ['monitor', 'fund_flow']):
            cli.main()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    assert 'SKIP' in captured.out or '跳过' in captured.out


@patch('trader_center.monitor.task_router.get_task_router')
def test_main_error_status(mock_get_router):
    """测试任务错误状态"""
    mock_router = MagicMock()
    mock_router.execute.return_value = {'status': 'error', 'reason': 'API error'}
    mock_router.get_task_info.return_value = {'name': 'fund_flow', 'category': 'data'}
    mock_get_router.return_value = mock_router

    with pytest.raises(SystemExit) as exc:
        with patch('sys.argv', ['monitor', 'fund_flow']):
            cli.main()
    assert exc.value.code == 1
