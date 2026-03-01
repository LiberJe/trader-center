"""任务模板 - 新任务开发参考

复制此目录并重命名，即可快速创建新任务。
步骤：
1. cp -r _template_ my_new_task
2. 修改 name, description, category 类属性
3. 实现 run() 方法
4. (可选) 实现 format_output() 方法
5. 在 tasks/__init__.py 中导入 (可选，auto_discover 会自动发现)
"""

from datetime import date
from typing import Any, Dict, Optional

from trader_center.monitor.base_task import BaseTask


class TemplateTask(BaseTask):
    """任务描述

    详细描述任务的功能和使用方式。

    Example:
        >>> task = TemplateTask()
        >>> result = task.run()
        >>> print(result['status'])
    """

    # 必须定义
    name = "template"              # 任务唯一标识符，用于 CLI 调用
    description = "任务模板示例"    # 任务描述，显示在 help 中

    # 可选定义
    category = "examples"          # 任务分类，用于组织任务列表

    def __init__(self):
        """初始化任务

        在此设置日志、API 客户端等。
        """
        # self.logger = logging.getLogger(__name__)
        pass

    def run(self, target_date: Optional[date] = None, **kwargs) -> Dict[str, Any]:
        """执行任务核心逻辑

        Args:
            target_date: 目标日期，默认今日
            **kwargs: 其他任务特定参数

        Returns:
            结果字典，必须包含 "status" 键
            {
                "status": "success" | "skipped" | "error",
                "date": date,
                # 其他任务特定数据...
            }
        """
        target_date = target_date or date.today()

        # TODO: 实现任务逻辑

        return {
            "status": "success",
            "date": target_date,
            "message": "任务执行成功",
        }

    def format_output(self, result: Dict[str, Any], **options) -> str:
        """格式化输出

        Args:
            result: run() 返回的结果
            **options: 格式化选项

        Returns:
            格式化后的字符串
        """
        lines = [
            f"任务: {self.name}",
            f"状态: {result.get('status')}",
            f"日期: {result.get('date')}",
            f"消息: {result.get('message')}",
        ]
        return "\n".join(lines)
