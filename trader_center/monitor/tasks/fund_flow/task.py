"""资金流向每日观察任务"""

import logging
import time
from datetime import date
from typing import Optional, Dict, Any

import pandas as pd

import trader_center.data_hub as dh
from trader_center.monitor.base_task import BaseTask


class FundFlowTask(BaseTask):
    """每日资金流向汇总任务

    手动执行，汇总当日A股市场资金流向数据，包括：
    - 大盘资金流向（主力、超大单、大单、中单、小单）
    - 个股资金流向排名
    - 行业板块资金流向
    - 概念板块资金流向

    Example:
        >>> task = FundFlowTask()
        >>> result = task.run()  # 汇总今日数据
        >>> print(result['status'])
        'success'
    """

    name = "fund_flow"
    description = "A股每日资金流向观察任务"
    category = "market_data"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._ak = None

    def _get_ak(self):
        """延迟导入 akshare"""
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak

    def run(self, target_date: Optional[date] = None, **kwargs) -> Dict[str, Any]:
        """执行任务

        Args:
            target_date: 目标日期，默认今日
            **kwargs: 额外参数（预留）

        Returns:
            {
                "status": "success" | "skipped",
                "date": date,
                "market": DataFrame,       # 大盘资金流向
                "top_stocks": DataFrame,   # 个股流向排名（前200）
                "industries": DataFrame,   # 行业板块流向
                "concepts": DataFrame,     # 概念板块流向
            }
        """
        target_date = target_date or date.today()

        self.logger.info(f"开始汇总资金流向数据: {target_date}")

        # 1. 检查是否交易日
        if not self._is_trading_day(target_date):
            self.logger.info(f"{target_date} 非交易日，跳过")
            return {
                "status": "skipped",
                "reason": "non_trading_day",
                "date": target_date,
                "market": pd.DataFrame(),
                "top_stocks": pd.DataFrame(),
                "industries": pd.DataFrame(),
                "concepts": pd.DataFrame(),
            }

        # 2. 获取大盘资金流向
        self.logger.info("获取大盘资金流向...")
        market_flow = self._get_market_fund_flow_with_retry(target_date)

        # 3. 获取个股资金流向排名
        self.logger.info("获取个股资金流向排名...")
        stock_flow = self._get_stock_fund_flow_with_retry(target_date, top_n=200)

        # 4. 获取行业板块资金流向
        self.logger.info("获取行业板块资金流向...")
        industry_flow = self._get_sector_fund_flow_with_retry(
            target_date, sector_type="industry"
        )

        # 5. 获取概念板块资金流向
        self.logger.info("获取概念板块资金流向...")
        concept_flow = self._get_sector_fund_flow_with_retry(
            target_date, sector_type="concept"
        )

        self.logger.info(f"资金流向数据汇总完成: {target_date}")

        return {
            "status": "success",
            "date": target_date,
            "market": market_flow,
            "top_stocks": stock_flow,
            "industries": industry_flow,
            "concepts": concept_flow,
        }

    def format_output(self, result: Dict[str, Any], **options) -> str:
        """格式化资金流向任务输出

        Args:
            result: run() 返回的结果
            **options: 包含 top_n 等选项

        Returns:
            格式化后的报告字符串
        """
        from .formatter import format_full_report
        top_n = options.get('top_n', 10)
        return format_full_report(result, top_n)

    def _is_trading_day(self, target_date: date) -> bool:
        """检查是否为交易日"""
        try:
            ak = self._get_ak()
            trade_date_df = ak.tool_trade_date_hist_sina()
            if trade_date_df.empty:
                return target_date.weekday() < 5

            trade_dates = pd.to_datetime(trade_date_df["trade_date"]).dt.date
            return target_date in trade_dates.values
        except Exception as e:
            self.logger.warning(f"获取交易日历失败: {e}，按工作日判断")
            return target_date.weekday() < 5

    def _get_market_fund_flow_with_retry(
        self, target_date: date, max_retries: int = 3
    ) -> pd.DataFrame:
        """获取大盘资金流向（带重试）"""
        for attempt in range(max_retries):
            try:
                result = dh.get_market_fund_flow(target_date)
                return result if result is not None else pd.DataFrame()
            except Exception as e:
                self.logger.warning(f"获取大盘资金流向失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error("获取大盘资金流向最终失败")
                    return pd.DataFrame()
        return pd.DataFrame()

    def _get_stock_fund_flow_with_retry(
        self, target_date: date, top_n: int = 100, max_retries: int = 3
    ) -> pd.DataFrame:
        """获取个股资金流向（带重试）"""
        for attempt in range(max_retries):
            try:
                result = dh.get_stock_fund_flow_rank(target_date, top_n=top_n)
                return result if result is not None else pd.DataFrame()
            except Exception as e:
                self.logger.warning(f"获取个股资金流向失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error("获取个股资金流向最终失败")
                    return pd.DataFrame()
        return pd.DataFrame()

    def _get_sector_fund_flow_with_retry(
        self, target_date: date, sector_type: str = "industry", max_retries: int = 3
    ) -> pd.DataFrame:
        """获取板块资金流向（带重试）"""
        for attempt in range(max_retries):
            try:
                result = dh.get_sector_fund_flow(target_date, sector_type=sector_type)
                return result if result is not None else pd.DataFrame()
            except Exception as e:
                self.logger.warning(
                    f"获取{sector_type}板块资金流向失败（尝试 {attempt + 1}/{max_retries}）: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"获取{sector_type}板块资金流向最终失败")
                    return pd.DataFrame()
        return pd.DataFrame()
