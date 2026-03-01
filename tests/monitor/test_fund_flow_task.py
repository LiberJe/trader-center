"""资金流向任务测试"""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pandas as pd

from trader_center.monitor.tasks.fund_flow import FundFlowTask


class TestFundFlowTask:
    """资金流向任务测试"""

    @pytest.fixture
    def task(self):
        return FundFlowTask()

    def test_task_initialization(self, task):
        """测试任务初始化"""
        assert task.logger is not None

    @patch.object(FundFlowTask, '_is_trading_day')
    def test_run_on_non_trading_day(self, mock_is_trading_day, task):
        """测试非交易日跳过"""
        mock_is_trading_day.return_value = False

        result = task.run(date(2024, 1, 1))

        assert result['status'] == 'skipped'
        assert result['reason'] == 'non_trading_day'

    @patch.object(FundFlowTask, '_is_trading_day')
    @patch.object(FundFlowTask, '_get_market_fund_flow_with_retry')
    @patch.object(FundFlowTask, '_get_stock_fund_flow_with_retry')
    @patch.object(FundFlowTask, '_get_sector_fund_flow_with_retry')
    def test_run_on_trading_day(
        self,
        mock_sector_flow,
        mock_stock_flow,
        mock_market_flow,
        mock_is_trading_day,
        task,
    ):
        """测试交易日正常执行"""
        mock_is_trading_day.return_value = True

        # Mock 数据返回
        mock_market_flow.return_value = pd.DataFrame({
            'date': [date(2024, 1, 15)],
            'market': ['all'],
            'main_force_net': [100.5],
        })
        mock_stock_flow.return_value = pd.DataFrame({
            'symbol': ['000001.SZ'],
            'name': ['Test Bank'],
            'fund_flow': [1000.0],
        })
        mock_sector_flow.return_value = pd.DataFrame({
            'sector_name': ['Bank'],
            'fund_flow': [5000.0],
        })

        result = task.run(date(2024, 1, 15))

        assert result['status'] == 'success'
        assert result['date'] == date(2024, 1, 15)
        assert not result['market'].empty
        assert not result['top_stocks'].empty
        assert not result['industries'].empty
        assert not result['concepts'].empty

    @patch('trader_center.monitor.tasks.fund_flow.task.dh.get_market_fund_flow')
    def test_get_market_fund_flow_with_retry(self, mock_get, task):
        """测试获取大盘资金流向带重试"""
        mock_get.return_value = pd.DataFrame({
            'date': [date(2024, 1, 15)],
            'market': ['all'],
            'main_force_net': [100.5],
        })

        result = task._get_market_fund_flow_with_retry(date(2024, 1, 15))

        assert not result.empty
        assert result.iloc[0]['market'] == 'all'

    @patch('trader_center.monitor.tasks.fund_flow.task.dh.get_market_fund_flow')
    def test_get_market_fund_flow_retry_on_failure(self, mock_get, task):
        """测试获取失败时重试"""
        mock_get.side_effect = Exception("Network error")

        result = task._get_market_fund_flow_with_retry(
            date(2024, 1, 15), max_retries=2
        )

        assert result.empty
        assert mock_get.call_count == 2


class TestMonitorAPI:
    """Monitor 模块 API 测试"""

    @patch('trader_center.monitor.tasks.fund_flow.task.FundFlowTask.run')
    def test_summarize_daily_fund_flow(self, mock_run):
        """测试 summarize_daily_fund_flow 函数"""
        import trader_center.monitor as mon

        mock_run.return_value = {
            'status': 'success',
            'date': date(2024, 1, 15),
            'market': pd.DataFrame(),
            'top_stocks': pd.DataFrame(),
            'industries': pd.DataFrame(),
            'concepts': pd.DataFrame(),
        }

        result = mon.summarize_daily_fund_flow(date(2024, 1, 15))

        assert result['status'] == 'success'
        mock_run.assert_called_once_with(date(2024, 1, 15))

    def test_summarize_daily_fund_flow_default_date(self):
        """测试默认使用今日日期"""
        import trader_center.monitor as mon

        with patch.object(
            FundFlowTask, 'run', return_value={'status': 'success'}
        ) as mock_run:
            mon.summarize_daily_fund_flow()
            # 验证使用了今天的日期
            call_args = mock_run.call_args[0][0]
            assert call_args == date.today() or call_args is None
