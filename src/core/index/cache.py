import time
from typing import Any, Optional, Dict, Tuple
from collections import OrderedDict

class LRUHashCache:
    """
    High-performance LRU Cache with TTL support and telemetry.
    Supports invalidation tracking to satisfy the >=80% hit rate and <2s invalidation KPIs.
    """
    def __init__(self, capacity: int = 20000, default_ttl_seconds: int = 3600):
        self.capacity = capacity
        self.default_ttl = default_ttl_seconds
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            self.misses += 1
            return None

        val, expiry = self._cache[key]
        now = time.time()
        if expiry and now > expiry:
            # Expired
            del self._cache[key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self.hits += 1
        return val

    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = time.time() + ttl if ttl > 0 else 0.0

        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.capacity:
                self._cache.popitem(last=False)  # pop LRU
                self.evictions += 1

        self._cache[key] = (value, expiry)

    def invalidate(self, key: str) -> Tuple[bool, float]:
        start = time.perf_counter()
        removed = False
        if key in self._cache:
            del self._cache[key]
            self.invalidations += 1
            removed = True
        latency_ms = (time.perf_counter() - start) * 1000.0
        return removed, latency_ms

    def invalidate_all(self) -> Tuple[int, float]:
        start = time.perf_counter()
        count = len(self._cache)
        self._cache.clear()
        self.invalidations += count
        latency_ms = (time.perf_counter() - start) * 1000.0
        return count, latency_ms

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    def get_stats(self) -> dict:
        return {
            "size": len(self._cache),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(self.hit_rate() * 100.0, 2),
            "evictions": self.evictions,
            "invalidations": self.invalidations
        }
