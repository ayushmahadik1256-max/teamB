from abc import ABC, abstractmethod
from typing import Any, Optional, List, Tuple
import sys

class BaseIndex(ABC):
    """
    Abstract interface for search tree and hash-based index adapters.
    Used for comparative analysis of lookup complexity, latency, and memory cost.
    """
    @abstractmethod
    def put(self, key: str, value: Any) -> None:
        """Insert or update key-value mapping."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value by key; return None if not present."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove key from index; return True if found and deleted, False otherwise."""
        pass

    @abstractmethod
    def contains(self, key: str) -> bool:
        """Return True if key exists in index."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return total number of entries in the index."""
        pass

    @abstractmethod
    def memory_usage_bytes(self) -> int:
        """Estimate total memory footprint of the index structure in bytes."""
        pass

    @abstractmethod
    def get_all_entries(self) -> List[Tuple[str, Any]]:
        """Return all key-value pairs."""
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """Return statistical metadata for index inspection."""
        pass
