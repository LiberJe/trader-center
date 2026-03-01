"""Monitor Tasks 模块

自动发现并注册所有任务。
"""

from trader_center.monitor.tasks.fund_flow import FundFlowTask

# 任务注册表
TASK_REGISTRY = {
    FundFlowTask.name: FundFlowTask,
}

__all__ = ["FundFlowTask", "TASK_REGISTRY"]
