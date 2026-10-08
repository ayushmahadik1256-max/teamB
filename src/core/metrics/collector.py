from typing import List, Dict, Any
from ..index.index_registry import IndexRegistry
from ..dedup.engine import DedupEngine
from ...models.schemas import DedupMetricsResponse

class MetricsCollector:
    """
    Telemetry and Benchmark Metric Collector for Team B.
    Aggregates runtime latency distributions, cache effectiveness, and memory profiling.
    """
    def __init__(self, registry: IndexRegistry, engine: DedupEngine):
        self.registry = registry
        self.engine = engine
        self.verification_latencies_ms: List[float] = []
        self._max_history = 1000

    def record_verification(self, latency_ms: float) -> None:
        self.verification_latencies_ms.append(latency_ms)
        if len(self.verification_latencies_ms) > self._max_history:
            self.verification_latencies_ms.pop(0)

    def get_p95_verification_ms(self) -> float:
        if not self.verification_latencies_ms:
            return 0.0
        s = sorted(self.verification_latencies_ms)
        return round(s[int(0.95 * len(s))], 2)

    def collect_metrics(self) -> DedupMetricsResponse:
        cache_stats = self.registry.cache.get_stats()
        
        # Memory stats
        memory_stats = {
            "avl_tree_bytes": self.registry.avl_index.memory_usage_bytes(),
            "rb_tree_bytes": self.registry.rb_index.memory_usage_bytes(),
            "hash_map_bytes": self.registry.hash_index.memory_usage_bytes()
        }

        # Tree depth
        tree_depth = None
        if self.registry.active_adapter_name in ("avl", "avl_tree"):
            tree_depth = self.registry.avl_index._get_height(self.registry.avl_index.root)
        elif self.registry.active_adapter_name in ("rbtree", "rb_tree"):
            tree_depth = self.registry.rb_index._get_max_depth(self.registry.rb_index.root)

        return DedupMetricsResponse(
            service="Team B - Deduplication & Integrity Engine",
            index_version=self.registry.index_version,
            active_index_adapter=self.registry.active_adapter_name,
            total_chunks_indexed=self.registry.hash_index.size(),
            total_dedup_operations=len(self.engine.computation_latencies_ms),
            cache_hit_rate_pct=cache_stats["hit_rate_pct"],
            cache_total_hits=cache_stats["hits"],
            cache_total_misses=cache_stats["misses"],
            dedup_computation_p95_ms=self.engine.get_p95_computation_ms(),
            hash_index_lookup_p95_us=self.registry.get_p95_lookup_us(),
            verification_p95_ms=self.get_p95_verification_ms(),
            memory_footprint_bytes=memory_stats,
            tree_depth=tree_depth
        )
