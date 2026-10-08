from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
import hashlib

@dataclass
class Chunk:
    chunk_id: str
    chunk_hash: str
    chunk_size: int
    offset: int
    data: Optional[bytes] = None
    hash_algorithm: str = "SHA-256"

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, data: bytes, hash_algorithm: str = "SHA-256") -> List[Chunk]:
        """
        Split raw data into chunks deterministically according to the chunking policy.
        """
        pass

    @staticmethod
    def compute_hash(data: bytes, hash_algorithm: str = "SHA-256") -> str:
        """
        Compute hash of data using supported algorithms.
        """
        algo_lower = hash_algorithm.lower().replace("-", "").replace("_", "")
        if algo_lower in ("sha256", "sha-256"):
            return hashlib.sha256(data).hexdigest()
        elif algo_lower in ("sha1", "sha-1"):
            return hashlib.sha1(data).hexdigest()
        elif algo_lower in ("rabinkarp", "rollinghash"):
            # Compute 64-bit Rabin-Karp polynomial hash formatted as 16-hex string
            h = 0
            base = 257
            mod = 1000000007
            for b in data:
                h = (h * base + b) % mod
            return f"{h:016x}"
        else:
            raise ValueError(f"Unsupported hash algorithm: {hash_algorithm}")
