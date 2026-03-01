"""任务路由器 - 动态发现与执行任务"""

import importlib
import inspect
import pkgutil
from typing import Dict, List, Optional, Type, Any

from trader_center.monitor.base_task import BaseTask


class TaskRouter:
    """任务路由器

    负责任务的注册、发现和执行。支持动态加载 tasks 目录下的所有任务。

    Example:
        >>> router = TaskRouter()
        >>> router.auto_discover()  # 自动发现所有任务
        >>> router.list_tasks()
        ['fund_flow', ...]
        >>> result = router.execute('fund_flow', target_date=date.today())
    """

    def __init__(self):
        self._registry: Dict[str, Type[BaseTask]] = {}

    def register(self, task_class: Type[BaseTask]) -> None:
        """注册任务类

        Args:
            task_class: 继承自 BaseTask 的任务类
        """
        if not issubclass(task_class, BaseTask):
            raise TypeError(f"Task class must inherit from BaseTask: {task_class}")

        task_name = task_class.name
        if not task_name:
            raise ValueError(f"Task class must define 'name' attribute: {task_class}")

        self._registry[task_name] = task_class

    def get_task(self, name: str) -> Optional[Type[BaseTask]]:
        """获取任务类

        Args:
            name: 任务名称

        Returns:
            任务类，如果不存在返回 None
        """
        return self._registry.get(name)

    def list_tasks(self) -> List[str]:
        """列出所有已注册的任务名称"""
        return list(self._registry.keys())

    def get_task_info(self, name: str) -> Optional[Dict[str, str]]:
        """获取任务信息

        Args:
            name: 任务名称

        Returns:
            包含 name, description, category 的字典
        """
        task_class = self._registry.get(name)
        if task_class is None:
            return None

        return {
            "name": task_class.name,
            "description": task_class.description,
            "category": task_class.category,
        }

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """执行指定任务

        Args:
            name: 任务名称
            **kwargs: 传递给任务 run() 方法的参数

        Returns:
            任务执行结果

        Raises:
            ValueError: 任务不存在
        """
        task_class = self.get_task(name)
        if task_class is None:
            raise ValueError(f"Task '{name}' not found. Available: {self.list_tasks()}")

        task = task_class()
        return task.run(**kwargs)

    def auto_discover(self) -> None:
        """自动发现并注册 tasks 目录下的所有任务

        扫描 trader_center.monitor.tasks 包及其子目录，
        自动导入并注册继承自 BaseTask 的类。
        """
        import trader_center.monitor.tasks as tasks_package

        # 扫描 tasks 包下的所有模块
        for _, module_name, is_pkg in pkgutil.iter_modules(
            tasks_package.__path__, tasks_package.__name__ + "."
        ):
            try:
                if is_pkg:
                    # 是子目录，尝试导入 task.py
                    task_module_name = f"{module_name}.task"
                    try:
                        module = importlib.import_module(task_module_name)
                        self._register_tasks_from_module(module)
                    except ImportError:
                        # 没有 task.py，跳过
                        pass
                else:
                    # 是模块，直接导入
                    module = importlib.import_module(module_name)
                    self._register_tasks_from_module(module)
            except Exception as e:
                # 导入失败，记录警告但继续
                print(f"Warning: Failed to import {module_name}: {e}")
                continue

    def _register_tasks_from_module(self, module) -> None:
        """从模块中注册所有任务类"""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                issubclass(obj, BaseTask) and
                obj is not BaseTask and
                obj.name):  # 确保 name 已定义
                self.register(obj)


# 全局单例
_router_instance: Optional[TaskRouter] = None


def get_task_router() -> TaskRouter:
    """获取任务路由器单例"""
    global _router_instance
    if _router_instance is None:
        _router_instance = TaskRouter()
        _router_instance.auto_discover()
    return _router_instance
