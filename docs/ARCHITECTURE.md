# Team B — Deduplication & Integrity Engine Architecture

## 1. System Boundary and Mission
The **Deduplication & Integrity Engine** (Data Structures Engine) is an autonomous, high-performance microservice responsible for:
1. **Deterministic File Chunking**: Slicing byte streams via Fixed-Size chunking and Content-Defined Chunking (CDC) using a Rabin-Karp polynomial rolling hash.
2. **Cryptographic & Rolling Hashing**: Computing SHA-256 digests and rolling signatures for chunk identification.
3. **Pluggable Tree & Hash Indexing**: Indexing chunk hashes using AVL Trees, Red-Black Trees, and Hash-Maps, backed by an L1 LRU Cache.
4. **Delta & Savings Computation**: Evaluating duplicate vs unique chunks, calculating storage savings ratios, and delta sizes.
5. **Merkle Tree Integrity Verification**: Constructing canonical, deterministic Merkle trees to detect and isolate bit rot and data corruptions.

```
       +-------------------------------------------------------------+
       | Team D - Backup Control & Restore Dashboard (BFF & UI)      |
       +-------------------------------------------------------------+
                                      |
                           HTTPS /api/v1 (queries/telemetry)
                                      v
+-----------------------+   +---------------------------------------+
| Team A - OS Engine    |   | Team B - Data Structures Engine       |
| (Queues, Leases,      |   | [Chunker, Hash Index, Merkle Builder] |
|  Deadlocks, Workers)  |   +---------------------------------------+
+-----------------------+              ^
            ^                          | HTTPS /api/v1, /internal/v1
            | scheduling/lease         | (chunk, dedup, verify)
            +--------------------------+
                         |
       +-------------------------------------------------------------+
       | Team C - Metadata, Version & Restore Manager (Authoritative)|
       +-------------------------------------------------------------+
```

---

## 2. Component Building Blocks

### 2.1 Chunking Subsystem
- **FixedSizeChunker (`src/core/chunking/fixed_chunker.py`)**:
  - Baseline chunking strategy dividing input bytes into uniform blocks (default 64 KB).
  - Offset calculation: `offset_i = i * chunk_size`.
  - Deterministic chunk ID assignment: `chk_{sha256[:16]}`.
- **ContentDefinedChunker (`src/core/chunking/cdc_chunker.py`)**:
  - Dynamic boundary cut-point detection using Rabin-Karp polynomial rolling hash.
  - Rolling window size: 48 bytes; prime base: 257; modulus: $10^9 + 7$.
  - Boundary condition: `(rolling_hash & mask) == 0`.
  - Guaranteed size constraints: $min\_chunk \le size \le max\_chunk$.
  - Solves the boundary-shift problem: insertions or deletions only affect the modified chunk, leaving preceding and subsequent chunk boundaries identical.

### 2.2 Indexing Subsystem
- **AVLTreeIndex (`src/core/index/avl_tree.py`)**:
  - Height-balanced binary search tree enforcing $|height(left) - height(right)| \le 1$.
  - Dynamic single (LL, RR) and double (LR, RL) rotations maintain worst-case $O(\log n)$ search and insert.
- **RedBlackTreeIndex (`src/core/index/rb_tree.py`)**:
  - Self-balancing binary search tree with RED/BLACK coloring and sentinel NIL node.
  - Invariants: root is black, no consecutive red nodes, equal black-height along all paths.
  - Fewer structural rotations during high-write backup ingest.
- **HashMapIndex (`src/core/index/hash_map_index.py`)**:
  - Direct hash table wrapper providing average $O(1)$ operations for high-throughput baselines.
- **LRUHashCache (`src/core/index/cache.py`)**:
  - In-memory L1 cache with TTL and capacity bounds. Tracks hit rate and provides sub-millisecond invalidation.
- **IndexRegistry (`src/core/index/index_registry.py`)**:
  - Enforces `index_version` consistency (rejecting stale versions with HTTP 409).
  - Collects microsecond-level lookup latency distributions.

### 2.3 Deduplication Engine (`src/core/dedup/engine.py`)
- Coordinates the complete deduplication pipeline:
  1. Validates `hash_algorithm` and `index_version`.
  2. Invokes the selected chunker.
  3. Queries `IndexRegistry` + `LRUHashCache` for every chunk hash.
  4. Partitions chunks into `unique_chunk_ids` and `duplicate_chunk_ids`.
  5. Computes:
     $$\text{Original Size} = \sum_{c \in \text{chunks}} \text{size}(c)$$
     $$\text{Delta Size} = \sum_{u \in \text{unique}} \text{size}(u)$$
     $$\text{Savings Ratio} = 1.0 - \frac{\text{Delta Size}}{\text{Original Size}}$$
  6. Builds Merkle Tree and computes `merkle_root`.
  7. Registers new unique chunks in the index and persists `DedupResult`.

### 2.4 Merkle Tree Integrity Engine (`src/core/integrity/merkle_tree.py`)
- **Documented Chunk-Ordering Rule**: Chunks are ordered strictly by ascending byte offset of the file.
- **Leaf Hashing**: $H_{\text{leaf}} = \text{SHA-256}(\text{"leaf:"} \parallel \text{chunk\_hash})$.
- **Internal Node Hashing**: $H_{\text{node}} = \text{SHA-256}(\text{"node:"} \parallel H_{\text{left}} \parallel H_{\text{right}})$.
- **Odd Node Handling**: If a level has an odd count, the last node is duplicated to guarantee balanced binary pairing.
- **Audit Proofs & Verification**: Generates $O(\log N)$ sibling path proofs and isolates corrupted chunk IDs.

---

## 3. Sequence Flow (Page 8 Specification)

```
Team C / D              Team B API              Chunker             Hash Index           Merkle Builder
    |                        |                     |                     |                     |
    |-- POST /dedup/compute->|                     |                     |                     |
    |                        |-- split(file, sz) ->|                     |                     |
    |                        |<- (chunk_ids, hash)-|                     |                     |
    |                        |                                           |                     |
    |                        |------- lookup(hash keys) ---------------->|                     |
    |                        |<------ (duplicate / unique chunks) -------|                     |
    |                        |                                                                 |
    |                        |------- build(chunk hashes) ------------------------------------>|
    |                        |<------ (merkle_root) -------------------------------------------|
    |                        |                                                                 |
    |<- (dedup_result, ratio)|                                                                 |
```

---

## 4. Cross-Team Interface Standards
- **Envelopes**:
  - Success: `{"data": {...}, "meta": {"correlation_id": "...", "api_version": "v1", "timestamp": "..."}}`
  - Error: `{"error": {"code": "...", "message": "...", "details": [...]}, "meta": {"correlation_id": "..."}}`
- **Headers**:
  - `X-Correlation-ID`: Propagated end-to-end through every log and response.
  - `Idempotency-Key`: Supported for deduplication and mutation operations.
  - `Authorization`: Bearer token for service-to-service validation.
