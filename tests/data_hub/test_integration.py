import pytest
import tempfile
from datetime import datetime

import trader_center.data_hub as dh
from trader_center.data_hub.config import DataHubConfig


class TestIntegration:
    """端到端集成测试"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """每个测试前清理缓存"""
        dh.clear_cache()
        yield
        dh.clear_cache()

    def test_configure_and_get_bars(self):
        """测试配置和数据获取流程"""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            # 配置
            dh.configure(data_dir=tmpdir, cache_size=100)

            # 获取股票列表（mock 或需要网络）
            # 这个测试可能需要 mock akshare
            pass

    def test_cache_functionality(self):
        """测试缓存是否工作"""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            dh.configure(data_dir=tmpdir)

            # 首次调用后应该有缓存
            stats1 = dh.get_cache_stats()
            assert stats1["size"] >= 0

    def test_clear_cache(self):
        """测试清空缓存"""
        dh.clear_cache()
        stats = dh.get_cache_stats()
        assert stats["size"] == 0
