import sys
from typing import Any, Optional, List, Tuple, Dict
from .base import BaseIndex

class HashMapIndex(BaseIndex):
    """
    Hash-Map based index adapter.
    Provides average O(1) time complexity for lookup and insert operations.
    Serves as the high-throughput reference for comparing tree-based indexing overhead.
    """
    def __init__(self):
        self._map: Dict[str, Any] = {}

    def put(self, key: str, value: Any) -> None:
        self._map[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._map.get(key)

    def delete(self, key: str) -> bool:
        if key in self._map:
            del self._map[key]
            return True
        return False

    def contains(self, key: str) -> bool:
        return key in self._map

    def size(self) -> int:
        return len(self._map)

    def get_all_entries(self) -> List[Tuple[str, Any]]:
        return list(self._map.items())

    def memory_usage_bytes(self) -> int:
        total = sys.getsizeof(self) + sys.getsizeof(self._map)
        for k, v in self._map.items():
            total += sys.getsizeof(k)
            total += sys.getsizeof(v)
        return total

    def get_stats(self) -> dict:
        return {
            "type": "HashMapIndex",
            "size": len(self._map),
            "memory_bytes": self.memory_usage_bytes()
        }
