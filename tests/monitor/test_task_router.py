"""任务路由器测试"""

import pytest
from datetime import date

from trader_center.monitor.task_router import TaskRouter, get_task_router
from trader_center.monitor.base_task import BaseTask


class DummyTask(BaseTask):
    name = "dummy"
    description = "A dummy task"

    def run(self, **kwargs):
        return {"status": "success", "task": self.name}


class AnotherTask(BaseTask):
    name = "another"
    description = "Another task"

    def run(self, **kwargs):
        return {"status": "success", "task": self.name}


class NoNameTask(BaseTask):
    """Task without name defined"""
    description = "No name task"

    def run(self, **kwargs):
        return {"status": "success"}


def test_task_router_register():
    """测试任务注册"""
    router = TaskRouter()
    router.register(DummyTask)

    assert "dummy" in router.list_tasks()
    assert router.get_task("dummy") == DummyTask


def test_task_router_register_duplicate():
    """测试重复注册覆盖"""
    router = TaskRouter()
    router.register(DummyTask)
    router.register(DummyTask)  # 不应报错

    assert router.get_task("dummy") == DummyTask


def test_task_router_register_no_name():
    """测试注册没有 name 的任务会报错"""
    router = TaskRouter()
    with pytest.raises(ValueError, match="name"):
        router.register(NoNameTask)


def test_task_router_get_nonexistent():
    """测试获取不存在的任务"""
    router = TaskRouter()
    assert router.get_task("nonexistent") is None


def test_task_router_list_tasks():
    """测试列出所有任务"""
    router = TaskRouter()
    router.register(DummyTask)
    router.register(AnotherTask)

    tasks = router.list_tasks()
    assert "dummy" in tasks
    assert "another" in tasks
    assert len(tasks) == 2


def test_task_router_get_task_info():
    """测试获取任务信息"""
    router = TaskRouter()
    router.register(DummyTask)

    info = router.get_task_info("dummy")
    assert info is not None
    assert info["name"] == "dummy"
    assert info["description"] == "A dummy task"
    assert info["category"] == "default"


def test_task_router_get_nonexistent_info():
    """测试获取不存在任务的信息"""
    router = TaskRouter()
    assert router.get_task_info("nonexistent") is None


def test_task_router_execute_success():
    """测试成功执行任务"""
    router = TaskRouter()
    router.register(DummyTask)

    result = router.execute("dummy")
    assert result["status"] == "success"
    assert result["task"] == "dummy"


def test_task_router_execute_nonexistent():
    """测试执行不存在的任务"""
    router = TaskRouter()

    with pytest.raises(ValueError, match="Task 'nonexistent' not found"):
        router.execute("nonexistent")


def test_task_router_execute_with_params():
    """测试带参数执行任务"""
    router = TaskRouter()
    router.register(DummyTask)

    result = router.execute("dummy", extra_param="value")
    # DummyTask 忽略额外参数，但不应报错
    assert result["status"] == "success"


def test_task_router_execute_returns_instance():
    """测试 execute 创建新实例并执行"""
    router = TaskRouter()
    router.register(DummyTask)

    # 每次 execute 应该创建新实例
    result1 = router.execute("dummy")
    result2 = router.execute("dummy")
    assert result1 == result2


def test_auto_discover():
    """测试自动发现任务"""
    router = TaskRouter()
    router.auto_discover()

    # 应该发现 fund_flow 任务
    assert "fund_flow" in router.list_tasks()

    # 验证任务信息
    info = router.get_task_info("fund_flow")
    assert info is not None
    assert info["name"] == "fund_flow"
    assert info["category"] == "market_data"


def test_register_non_basetask():
    """测试注册非 BaseTask 类会报错"""
    router = TaskRouter()

    class NotATask:
        name = "not_a_task"
        description = "Not a task"

    with pytest.raises(TypeError, match="BaseTask"):
        router.register(NotATask)
