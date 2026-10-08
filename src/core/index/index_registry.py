import time
from typing import Optional, Dict, Any, List, Tuple
from .base import BaseIndex
from .avl_tree import AVLTreeIndex
from .rb_tree import RedBlackTreeIndex
from .hash_map_index import HashMapIndex
from .cache import LRUHashCache
from ...models.schemas import ChunkIndexEntry

class StaleIndexVersionError(ValueError):
    pass

class IndexRegistry:
    """
    Central Index Registry for Team B.
    Maintains chunk metadata, enforces index_version reproducibility,
    supports hot-swappable search tree adapters (AVL, Red-Black Tree, Hash Map),
    and integrates the L1 LRU Hash Cache with latency telemetry.
    """
    def __init__(self, index_version: str = "v1.0.0", default_adapter: str = "rbtree"):
        self.index_version = index_version
        self.active_adapter_name = default_adapter
        
        # Instantiate index adapters
        self.avl_index = AVLTreeIndex()
        self.rb_index = RedBlackTreeIndex()
        self.hash_index = HashMapIndex()

        # Active primary index reference
        self.primary_index: BaseIndex = self._get_adapter_by_name(default_adapter)

        # L1 Cache
        self.cache = LRUHashCache(capacity=25000, default_ttl_seconds=3600)

        # Telemetry
        self.lookup_latencies_us: List[float] = []
        self._max_history = 5000

    def _get_adapter_by_name(self, name: str) -> BaseIndex:
        name_lower = name.lower()
        if name_lower in ("avl", "avl_tree", "avltree"):
            return self.avl_index
        elif name_lower in ("rbtree", "rb_tree", "redblack", "red_black"):
            return self.rb_index
        elif name_lower in ("hash", "hashmap", "hash_map"):
            return self.hash_index
        else:
            raise ValueError(f"Unknown index adapter: {name}")

    def set_active_adapter(self, name: str) -> None:
        self.primary_index = self._get_adapter_by_name(name)
        self.active_adapter_name = name

    def validate_index_version(self, requested_version: Optional[str]) -> None:
        if requested_version and requested_version != self.index_version:
            raise StaleIndexVersionError(
                f"Requested index_version '{requested_version}' does not match active version '{self.index_version}'"
            )

    def register_chunk(
        self,
        chunk_id: str,
        chunk_hash: str,
        chunk_size: int,
        file_id: str,
        index_version: Optional[str] = None
    ) -> ChunkIndexEntry:
        self.validate_index_version(index_version)

        # Check existing
        existing: Optional[ChunkIndexEntry] = self.hash_index.get(chunk_hash)
        if existing:
            existing.reference_count += 1
            # Update cache as well
            self.cache.put(chunk_hash, existing)
            return existing

        entry = ChunkIndexEntry(
            chunk_id=chunk_id,
            chunk_hash=chunk_hash,
            chunk_size=chunk_size,
            reference_count=1,
            first_seen_file_id=file_id,
            index_version=self.index_version
        )

        # Store in all adapters to allow instant comparative benchmarking
        self.avl_index.put(chunk_hash, entry)
        self.rb_index.put(chunk_hash, entry)
        self.hash_index.put(chunk_hash, entry)

        # Warm cache
        self.cache.put(chunk_hash, entry)
        return entry

    def lookup(self, chunk_hash: str) -> Tuple[Optional[ChunkIndexEntry], float, bool]:
        """
        Lookup chunk by hash key.
        Returns: (entry_or_None, lookup_time_us, cache_hit_bool)
        """
        start = time.perf_counter()
        
        # 1. Check L1 Cache
        cached_val = self.cache.get(chunk_hash)
        if cached_val is not None:
            latency_us = (time.perf_counter() - start) * 1_000_000.0
            self._record_latency(latency_us)
            return cached_val, latency_us, True

        # 2. Check Primary Index Adapter
        entry = self.primary_index.get(chunk_hash)
        latency_us = (time.perf_counter() - start) * 1_000_000.0
        self._record_latency(latency_us)

        if entry is not None:
            self.cache.put(chunk_hash, entry)

        return entry, latency_us, False

    def _record_latency(self, us: float) -> None:
        self.lookup_latencies_us.append(us)
        if len(self.lookup_latencies_us) > self._max_history:
            self.lookup_latencies_us.pop(0)

    def get_p95_lookup_us(self) -> float:
        if not self.lookup_latencies_us:
            return 0.0
        sorted_lat = sorted(self.lookup_latencies_us)
        idx = int(0.95 * len(sorted_lat))
        return round(sorted_lat[min(idx, len(sorted_lat) - 1)], 2)

    def compare_adapters(self, sample_keys: List[str]) -> Dict[str, Any]:
        """
        Benchmark search performance and memory cost across all 3 data structures.
        """
        results = {}
        adapters = [
            ("AVLTreeIndex", self.avl_index),
            ("RedBlackTreeIndex", self.rb_index),
            ("HashMapIndex", self.hash_index)
        ]

        for name, adapter in adapters:
            latencies = []
            for k in sample_keys:
                t0 = time.perf_counter()
                _ = adapter.get(k)
                latencies.append((time.perf_counter() - t0) * 1_000_000.0)

            latencies.sort()
            p50 = latencies[len(latencies) // 2] if latencies else 0.0
            p95 = latencies[int(0.95 * len(latencies))] if latencies else 0.0
            results[name] = {
                "size": adapter.size(),
                "memory_bytes": adapter.memory_usage_bytes(),
                "p50_lookup_us": round(p50, 3),
                "p95_lookup_us": round(p95, 3),
                "stats": adapter.get_stats()
            }
        return results

    def get_all_chunks(self) -> List[ChunkIndexEntry]:
        entries = self.hash_index.get_all_entries()
        return [val for _, val in entries]

    def total_size_bytes(self) -> int:
        return sum(entry.chunk_size for entry in self.get_all_chunks())
