from typing import List
from .base import BaseChunker, Chunk

class FixedSizeChunker(BaseChunker):
    """
    Fixed-size chunking adapter.
    Slices byte streams into uniform blocks of size `chunk_size`.
    Provides baseline comparison for deduplication efficiency.
    """
    def __init__(self, chunk_size: int = 64 * 1024):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size

    def chunk(self, data: bytes, hash_algorithm: str = "SHA-256") -> List[Chunk]:
        if not data:
            return []

        chunks: List[Chunk] = []
        data_len = len(data)
        offset = 0

        while offset < data_len:
            end = min(offset + self.chunk_size, data_len)
            chunk_data = data[offset:end]
            chunk_hash = self.compute_hash(chunk_data, hash_algorithm)
            chunk_id = f"chk_{chunk_hash[:16]}"

            chunks.append(Chunk(
                chunk_id=chunk_id,
                chunk_hash=chunk_hash,
                chunk_size=len(chunk_data),
                offset=offset,
                data=chunk_data,
                hash_algorithm=hash_algorithm
            ))
            offset = end

        return chunks
