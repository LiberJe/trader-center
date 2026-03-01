import pytest
from trader_center.monitor.base_task import BaseTask


class DummyTask(BaseTask):
    name = "dummy"
    description = "A dummy task for testing"

    def run(self, **kwargs):
        return {"status": "success", "data": kwargs}


class AnotherTask(BaseTask):
    name = "another"
    description = "Another task"
    category = "test_category"

    def run(self, **kwargs):
        return {"status": "success", "task": self.name}


def test_base_task_instantiation():
    """测试基类可以被继承实例化"""
    task = DummyTask()
    assert task.name == "dummy"
    assert task.description == "A dummy task for testing"
    assert task.category == "default"


def test_base_task_run():
    """测试 run 方法"""
    task = DummyTask()
    result = task.run(test_param="value")
    assert result["status"] == "success"
    assert result["data"]["test_param"] == "value"


def test_base_task_validate_params_default():
    """测试默认参数验证返回 True"""
    task = DummyTask()
    valid, error = task.validate_params()
    assert valid is True
    assert error is None


def test_base_task_format_output_default():
    """测试默认格式化输出"""
    task = DummyTask()
    result = {"status": "success", "data": "test"}
    output = task.format_output(result)
    assert "dummy" in output
    assert "success" in output


def test_base_task_custom_category():
    """测试自定义 category"""
    task = AnotherTask()
    assert task.category == "test_category"


def test_cannot_instantiate_base_task_directly():
    """测试不能直接实例化 BaseTask"""
    with pytest.raises(TypeError):
        BaseTask()
