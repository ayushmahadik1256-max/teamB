import hashlib
import time
from typing import List, Optional, Tuple, Dict, Any

class MerkleTree:
    """
    Deterministic Merkle Tree for File Chunk Integrity Verification.
    
    Documented Chunk-Ordering Rule:
    Chunks MUST be ordered strictly by ascending byte offset of the file 
    (or sequential list index [0, 1, ..., N-1]).
    
    Leaf node hash: SHA-256("leaf:" + chunk_hash)
    Internal node hash: SHA-256("node:" + left_hash + right_hash)
    Odd-length levels: Last node is duplicated to guarantee balanced binary tree pairing.
    """
    def __init__(self, chunk_hashes: Optional[List[str]] = None):
        self.chunk_hashes: List[str] = chunk_hashes or []
        self.levels: List[List[str]] = []
        self.root: Optional[str] = None
        if self.chunk_hashes:
            self.build(self.chunk_hashes)

    @staticmethod
    def hash_leaf(chunk_hash: str) -> str:
        payload = f"leaf:{chunk_hash}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def hash_internal(left_hash: str, right_hash: str) -> str:
        payload = f"node:{left_hash}{right_hash}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def build(self, chunk_hashes: List[str]) -> str:
        if not chunk_hashes:
            self.root = hashlib.sha256(b"empty_merkle_tree").hexdigest()
            self.levels = [[]]
            return self.root

        self.chunk_hashes = list(chunk_hashes)
        # Level 0: leaf hashes
        current_level = [self.hash_leaf(ch) for ch in self.chunk_hashes]
        self.levels = [current_level]

        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    # Odd count: duplicate last node
                    right = left
                parent_hash = self.hash_internal(left, right)
                next_level.append(parent_hash)
            self.levels.append(next_level)
            current_level = next_level

        self.root = self.levels[-1][0]
        return self.root

    def get_root(self) -> str:
        if self.root is None:
            return self.build(self.chunk_hashes)
        return self.root

    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Generate audit path proof for chunk at index.
        Returns list of (sibling_hash, direction) where direction is 'left' or 'right'.
        """
        if index < 0 or index >= len(self.chunk_hashes):
            raise IndexError("Chunk index out of bounds for Merkle proof generation")

        proof: List[Tuple[str, str]] = []
        curr_idx = index

        for level in self.levels[:-1]:
            is_right_child = (curr_idx % 2 == 1)
            sibling_idx = curr_idx - 1 if is_right_child else curr_idx + 1

            if sibling_idx < len(level):
                sibling_hash = level[sibling_idx]
            else:
                # Sibling was duplicated self
                sibling_hash = level[curr_idx]

            direction = "left" if is_right_child else "right"
            proof.append((sibling_hash, direction))
            curr_idx = curr_idx // 2

        return proof

    @classmethod
    def verify_proof(cls, chunk_hash: str, proof: List[Tuple[str, str]], expected_root: str) -> bool:
        curr_hash = cls.hash_leaf(chunk_hash)
        for sibling_hash, direction in proof:
            if direction == "left":
                curr_hash = cls.hash_internal(sibling_hash, curr_hash)
            else:
                curr_hash = cls.hash_internal(curr_hash, sibling_hash)
        return curr_hash == expected_root

    @classmethod
    def verify_integrity(
        cls,
        expected_chunk_hashes: List[str],
        actual_chunk_hashes: List[str]
    ) -> Tuple[bool, List[str], List[str], str, float]:
        """
        Compare expected vs actual chunks, detect corruptions, and compute verification latency.
        Returns: (is_valid, verified_chunks, corrupted_chunks, merkle_root, latency_ms)
        """
        t0 = time.perf_counter()
        
        tree = cls(actual_chunk_hashes)
        actual_root = tree.get_root()

        verified: List[str] = []
        corrupted: List[str] = []

        max_len = max(len(expected_chunk_hashes), len(actual_chunk_hashes))
        for i in range(max_len):
            exp = expected_chunk_hashes[i] if i < len(expected_chunk_hashes) else None
            act = actual_chunk_hashes[i] if i < len(actual_chunk_hashes) else None

            if exp is not None and act is not None and exp == act:
                verified.append(act)
            else:
                corrupted.append(act if act is not None else f"missing_chunk_{i}")

        is_valid = (len(corrupted) == 0 and len(expected_chunk_hashes) == len(actual_chunk_hashes))
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return is_valid, verified, corrupted, actual_root, latency_ms
