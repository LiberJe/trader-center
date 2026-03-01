import time
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict

logger = logging.getLogger(__name__)


class CacheManager:
    """
    LRU 内存缓存管理器
    支持 TTL 和容量限制
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._ttl: Dict[str, float] = {}
        self._access_count: Dict[str, int] = {}
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            self._miss_count += 1
            return None

        # 检查 TTL
        if key in self._ttl and time.time() > self._ttl[key]:
            self._delete(key)
            self._miss_count += 1
            return None

        # 更新访问顺序（LRU）
        self._cache.move_to_end(key)
        self._access_count[key] = self._access_count.get(key, 0) + 1
        self._hit_count += 1

        return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        # 如果已存在，先删除
        if key in self._cache:
            del self._cache[key]

        # LRU 淘汰
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        self._cache[key] = value
        if ttl:
            self._ttl[key] = time.time() + ttl

    def _evict_lru(self):
        """淘汰最少使用的缓存"""
        if not self._cache:
            return
        oldest_key = next(iter(self._cache))
        self._delete(oldest_key)
        logger.debug(f"Evicted cache key: {oldest_key}")

    def _delete(self, key: str):
        """删除缓存项"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        self._access_count.pop(key, None)

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._ttl.clear()
        self._access_count.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": f"{hit_rate:.2%}",
        }
