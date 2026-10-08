from typing import List
from .base import BaseChunker, Chunk

class ContentDefinedChunker(BaseChunker):
    """
    Content-Defined Chunking (CDC) using Rabin-Karp Polynomial Rolling Hash.
    Dynamically identifies boundary cut-points based on byte content rather than fixed offsets.
    Solves the boundary-shift problem when insertions/deletions occur in files.
    """
    def __init__(
        self,
        avg_chunk_size: int = 8192,
        min_chunk_size: int = 2048,
        max_chunk_size: int = 65536,
        window_size: int = 48
    ):
        if min_chunk_size <= 0 or max_chunk_size <= min_chunk_size:
            raise ValueError("Invalid min/max chunk size bounds")
        self.avg_chunk_size = avg_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.window_size = window_size
        
        # Determine bitmask: e.g. avg 8192 -> mask 0x1fff (13 bits)
        power_of_two = 1
        while (power_of_two * 2) <= avg_chunk_size:
            power_of_two *= 2
        self.mask = power_of_two - 1

        # Rabin-Karp rolling hash constants
        self.prime_base = 257
        self.modulus = 1000000007
        self.power = pow(self.prime_base, self.window_size - 1, self.modulus)

    def chunk(self, data: bytes, hash_algorithm: str = "SHA-256") -> List[Chunk]:
        if not data:
            return []

        data_len = len(data)
        chunks: List[Chunk] = []
        chunk_start = 0

        # Optimization for tiny files
        if data_len <= self.min_chunk_size:
            chunk_hash = self.compute_hash(data, hash_algorithm)
            chunk_id = f"chk_{chunk_hash[:16]}"
            return [Chunk(
                chunk_id=chunk_id,
                chunk_hash=chunk_hash,
                chunk_size=data_len,
                offset=0,
                data=data,
                hash_algorithm=hash_algorithm
            )]

        curr_pos = 0
        while curr_pos < data_len:
            # We need to find the next boundary starting from chunk_start
            # Skip until min_chunk_size
            curr_pos = chunk_start + self.min_chunk_size
            if curr_pos >= data_len:
                # End of file reached
                chunk_data = data[chunk_start:data_len]
                chunk_hash = self.compute_hash(chunk_data, hash_algorithm)
                chunk_id = f"chk_{chunk_hash[:16]}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    chunk_hash=chunk_hash,
                    chunk_size=len(chunk_data),
                    offset=chunk_start,
                    data=chunk_data,
                    hash_algorithm=hash_algorithm
                ))
                break

            # Initialize rolling hash window
            window_start = curr_pos - self.window_size if curr_pos >= self.window_size else 0
            window_end = curr_pos
            window = data[window_start:window_end]

            rolling_hash = 0
            for b in window:
                rolling_hash = (rolling_hash * self.prime_base + b) % self.modulus

            boundary_found = False
            while curr_pos < data_len:
                chunk_len = curr_pos - chunk_start
                if chunk_len >= self.max_chunk_size:
                    boundary_found = True
                    break

                # Check if boundary condition met
                if (rolling_hash & self.mask) == 0:
                    boundary_found = True
                    break

                # Advance rolling window by 1 byte
                if curr_pos < data_len:
                    b_in = data[curr_pos]
                    out_idx = curr_pos - self.window_size
                    b_out = data[out_idx] if out_idx >= 0 else 0
                    rolling_hash = ((rolling_hash - (b_out * self.power)) * self.prime_base + b_in) % self.modulus
                    curr_pos += 1

            # Slice chunk
            chunk_data = data[chunk_start:curr_pos]
            chunk_hash = self.compute_hash(chunk_data, hash_algorithm)
            chunk_id = f"chk_{chunk_hash[:16]}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                chunk_hash=chunk_hash,
                chunk_size=len(chunk_data),
                offset=chunk_start,
                data=chunk_data,
                hash_algorithm=hash_algorithm
            ))
            chunk_start = curr_pos

        return chunks
