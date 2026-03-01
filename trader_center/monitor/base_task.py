"""Task 基类定义 - 所有 Monitor 任务的标准接口"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTask(ABC):
    """Monitor Task 抽象基类

    所有任务必须继承此类并实现标准接口。
    类属性 name 和 description 必须定义。

    Example:
        >>> class MyTask(BaseTask):
        ...     name = "my_task"
        ...     description = "My task description"
        ...
        ...     def run(self, **kwargs):
        ...         return {"status": "success", "data": []}
        ...
        >>> task = MyTask()
        >>> result = task.run()
    """

    # 子类必须定义的类属性
    name: str = ""
    description: str = ""
    category: str = "default"

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """执行任务核心逻辑

        Args:
            **kwargs: 任务特定的参数

        Returns:
            包含 "status" 键的结果字典
            - status: "success" | "skipped" | "error"
            - 其他任务特定数据
        """
        pass

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """验证任务参数

        子类可重写此方法添加参数校验逻辑。

        Args:
            **kwargs: 待验证的参数

        Returns:
            (是否有效, 错误信息)。有效时错误信息为 None。
        """
        return True, None

    def format_output(self, result: Dict[str, Any], **options) -> str:
        """格式化任务输出

        子类可重写此方法提供自定义格式化。

        Args:
            result: run() 返回的结果字典
            **options: 格式化选项 (如 max_lines, format_type 等)

        Returns:
            格式化后的字符串输出
        """
        return f"Task: {self.name}\nResult: {result}"
