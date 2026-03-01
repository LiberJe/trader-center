"""Monitor模块 - 每日观察动作集合

Monitor模块用于手动执行每日A股市场观察任务，包括：
- 资金流向数据汇总
- 市场热点追踪
- 个股异动监测

Example:
    >>> import trader_center.monitor as mon
    >>> from datetime import date
    >>> # 通过路由器执行任务
    >>> router = mon.get_task_router()
    >>> result = router.execute('fund_flow', target_date=date.today())
    >>> print(result['status'])
    'success'
"""

from datetime import date
from typing import Optional, Dict, Any

# 导出核心组件
from trader_center.monitor.base_task import BaseTask
from trader_center.monitor.task_router import get_task_router, TaskRouter

# 为向后兼容保留的快捷函数
def summarize_daily_fund_flow(
    target_date: Optional[date] = None
) -> Dict[str, Any]:
    """汇总每日A股资金流向数据 (向后兼容)

    手动执行，获取大盘、个股、板块的资金流向数据。
    如果指定日期不是交易日，则返回跳过状态。

    Args:
        target_date: 目标日期，默认为今日

    Returns:
        {
            "status": "success" | "skipped",
            "date": date,
            "market": DataFrame,       # 大盘资金流向
            "top_stocks": DataFrame,   # 个股流向排名
            "industries": DataFrame,   # 行业板块流向
            "concepts": DataFrame,     # 概念板块流向
        }
    """
    from trader_center.monitor.tasks.fund_flow import FundFlowTask

    task = FundFlowTask()
    return task.run(target_date)


__all__ = [
    # 核心组件
    "BaseTask",
    "TaskRouter",
    "get_task_router",
    # 向后兼容
    "summarize_daily_fund_flow",
]
