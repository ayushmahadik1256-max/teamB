#!/usr/bin/env python3
"""
Team B — End-to-End Interactive Demonstration Script
Simulates full integration lifecycle: Chunking -> Deduplication -> Merkle Integrity -> Corruption Detection
"""
import os
import sys
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.chunking.fixed_chunker import FixedSizeChunker
from src.core.chunking.cdc_chunker import ContentDefinedChunker
from src.core.index.index_registry import IndexRegistry
from src.core.dedup.engine import DedupEngine
from src.core.integrity.merkle_tree import MerkleTree
from src.models.schemas import DedupComputeRequest

def run_demo():
    print("=" * 80)
    print("SMART FILE BACKUP SYSTEM — TEAM B END-TO-END DEMONSTRATION")
    print("Academic Year 2026-27 | Data Structures Engine")
    print("=" * 80)

    # 1. Initialize Registry and Engine
    print("\n[Step 1] Initializing Index Registry with Red-Black Tree and L1 Cache...")
    registry = IndexRegistry(index_version="v1.0.0", default_adapter="rbtree")
    engine = DedupEngine(registry)
    print(f"  ✓ Active Index Adapter: {registry.active_adapter_name}")
    print(f"  ✓ Index Version: {registry.index_version}")
    print(f"  ✓ Cache Capacity: {registry.cache.capacity} entries")

    # 2. File 1: Initial Backup
    print("\n[Step 2] Processing File 1 (Initial Backup)...")
    content1 = "".join([f"Paragraph {i:03d}: System design specifications for Team B components.\n" * 4 for i in range(40)])
    req1 = DedupComputeRequest(
        file_id="project_spec_v1.txt",
        chunk_boundaries="fixed",
        chunk_size=1024,
        hash_algorithm="SHA-256",
        index_version="v1.0.0",
        raw_text=content1
    )
    res1 = engine.compute(req1)
    print(f"  ✓ File ID: {res1.file_id}")
    print(f"  ✓ Total Chunks: {res1.total_chunks}")
    print(f"  ✓ Unique Chunks: {res1.unique_chunks} (Stored)")
    print(f"  ✓ Duplicate Chunks: {res1.duplicate_chunks}")
    print(f"  ✓ Savings Ratio: {res1.savings_ratio * 100:.1f}%")
    print(f"  ✓ Merkle Root: {res1.merkle_root}")

    # 3. File 2: Exact Duplicate Backup
    print("\n[Step 3] Processing File 2 (Exact Duplicate Backup)...")
    req2 = DedupComputeRequest(
        file_id="project_spec_v1_backup.txt",
        chunk_boundaries="fixed",
        chunk_size=1024,
        hash_algorithm="SHA-256",
        index_version="v1.0.0",
        raw_text=content1
    )
    res2 = engine.compute(req2)
    print(f"  ✓ Total Chunks: {res2.total_chunks}")
    print(f"  ✓ Unique Chunks: {res2.unique_chunks}")
    print(f"  ✓ Duplicate Chunks: {res2.duplicate_chunks} (Deduplicated)")
    print(f"  ✓ Savings Ratio: {res2.savings_ratio * 100:.1f}% (Zero new bytes stored!)")
    print(f"  ✓ Merkle Root Matches File 1: {res1.merkle_root == res2.merkle_root}")

    # 4. File 3: Modified Version (Delta Computation)
    print("\n[Step 4] Processing File 3 (v2 with Partial Edits)...")
    content3 = content1 + "".join([f"New Appendix Section {i:02d}: Performance benchmark evidence.\n" * 4 for i in range(20)])
    req3 = DedupComputeRequest(
        file_id="project_spec_v2.txt",
        chunk_boundaries="fixed",
        chunk_size=1024,
        hash_algorithm="SHA-256",
        index_version="v1.0.0",
        raw_text=content3
    )
    res3 = engine.compute(req3)
    print(f"  ✓ Total Chunks: {res3.total_chunks}")
    print(f"  ✓ Duplicate Chunks: {res3.duplicate_chunks} (Reused from v1)")
    print(f"  ✓ Unique Chunks: {res3.unique_chunks} (Delta chunks)")
    print(f"  ✓ Storage Savings: {res3.savings_ratio * 100:.1f}%")
    print(f"  ✓ New Merkle Root: {res3.merkle_root}")

    # 5. Merkle Tree Proof and Tamper Detection
    print("\n[Step 5] Merkle Tree Audit Proof & Tamper Detection...")
    chunker = FixedSizeChunker(chunk_size=1024)
    chunks3 = chunker.chunk(content3.encode("utf-8"))
    chunk_hashes = [c.chunk_hash for c in chunks3]

    tree = MerkleTree(chunk_hashes)
    root = tree.get_root()
    proof = tree.get_proof(2)
    valid_proof = MerkleTree.verify_proof(chunk_hashes[2], proof, root)
    print(f"  ✓ Proof verification for chunk 2: {'VALID' if valid_proof else 'INVALID'}")

    # Corrupt chunk 2
    corrupted_hashes = list(chunk_hashes)
    corrupted_hashes[2] = "0" * 64  # Injected bit corruption
    is_valid, verified, corrupted, c_root, lat_ms = MerkleTree.verify_integrity(chunk_hashes, corrupted_hashes)
    print(f"  ✓ Injected corruption detected? {'YES' if not is_valid else 'NO'}")
    print(f"  ✓ Corrupted chunk hash isolated: {corrupted[0]}")
    print(f"  ✓ Verification latency: {lat_ms:.3f} ms")

    # 6. Data Structure Comparison
    print("\n[Step 6] Comparing AVL Tree vs Red-Black Tree vs Hash-Map...")
    comp = registry.compare_adapters(chunk_hashes[:10])
    for name, data in comp.items():
        print(f"  • {name:<20}: p95 lookup = {data['p95_lookup_us']:>6.2f} µs | Memory = {data['memory_bytes']:>8} bytes")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_demo()
