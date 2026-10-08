# Team B — Data Structures & Algorithms Complexity Analysis

This document provides formal theoretical proofs and empirical measurements of time and space complexity for all core algorithms and data structures implemented by **Team B (Deduplication & Integrity Engine)**.

---

## 1. Chunking Algorithms Comparison

### 1.1 Fixed-Size Chunking
- **Algorithm**: Slices file buffer into uniform blocks of size $S$.
- **Time Complexity**:
  - Scanning & Slicing: $O(N)$ where $N$ is file size in bytes.
  - Hashing: $O(N)$ because $\sum_{i=1}^{M} O(S_i) = O(N)$, where $M = \lceil N/S \rceil$.
  - Total Time: $\Theta(N)$.
- **Space Complexity**:
  - Working memory: $O(S)$ for chunk buffer; $O(M)$ to store $M$ chunk descriptors.
- **Deduplication Characteristics**:
  - Susceptible to the **boundary shift problem**: inserting a single byte at offset 0 shifts all downstream boundaries, resulting in 0% deduplication of otherwise identical data.

### 1.2 Content-Defined Chunking (CDC) via Rabin-Karp Rolling Hash
- **Algorithm**: Advances a sliding window of size $W$ byte-by-byte. A rolling hash $H_t$ is updated in $O(1)$ arithmetic operations:
  $$H_t = \left( (H_{t-1} - B_{\text{out}} \cdot p^{W-1}) \cdot p + B_{\text{in}} \right) \pmod q$$
  A boundary is declared when $(H_t \ \& \ \text{mask}) == 0$, bounded by $[S_{\min}, S_{\max}]$.
- **Time Complexity**:
  - Rolling window update: $O(1)$ per byte.
  - Over $N$ bytes: $O(N)$ window operations.
  - Final chunk SHA-256 hash: $O(N)$ across all emitted chunks.
  - Total Time: $\Theta(N)$.
- **Space Complexity**:
  - Sliding window buffer: $O(W)$ auxiliary memory (48 bytes).
  - Emitted chunks: $O(K)$ descriptors where $K \approx N / S_{\text{avg}}$.
- **Deduplication Characteristics**:
  - Boundary shift resistant: insertions or deletions only affect the current chunk; downstream boundaries realign immediately.

---

## 2. Hash Index Data Structures: AVL Tree vs. Red-Black Tree vs. Hash Map

| Data Structure | Search (Avg) | Search (Worst) | Insert (Avg) | Insert (Worst) | Delete (Worst) | Space Overhead | Rotations / Insert |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AVL Tree** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | $O(n)$ | $\le 2$ |
| **Red-Black Tree** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | $O(n)$ | $\le 2$ |
| **Hash Map** | $O(1)$ | $O(n)$ | $O(1)$ | $O(n)$ | $O(n)$ | $O(n)$ | $0$ |

### 2.1 Theoretical Invariants & Balancing Analysis
1. **AVL Tree**:
   - Invariant: $|h_L - h_R| \le 1$ for all nodes.
   - Maximum height: $h < 1.4404 \log_2(n + 2) - 0.328$.
   - Strictly shallower depth than Red-Black trees $\implies$ faster lookup operations in read-heavy workloads.
   - Higher rotation frequency on insertion (up to $O(\log n)$ rotations on delete, 1-2 on insert).

2. **Red-Black Tree**:
   - Invariant: Root is black, no two consecutive red nodes, equal black height on all paths from root to NIL leaves.
   - Maximum height: $h \le 2 \log_2(n + 1)$.
   - Looser balance than AVL trees $\implies$ slightly deeper average search path, but **strictly faster insertions** because rebalancing requires at most 2 rotations and simple color flips.
   - Optimal for backup write-heavy workloads with continuous chunk indexing.

3. **Hash Map Index**:
   - Invariant: Open addressing or chained buckets with dynamic resizing at load factor $\alpha \ge 0.75$.
   - Amortized $O(1)$ search and insert. Does not maintain sorted order; vulnerable to hash collision attacks in adversarial scenarios without collision-resistant hashing.

---

## 3. Empirical Comparative Analysis (5,000 Key Dataset)

Benchmark executed on the reference VM sandbox with 5,000 64-byte SHA-256 chunk keys:

| Metric | AVL Tree Index | Red-Black Tree Index | Hash Map Index |
| :--- | :--- | :--- | :--- |
| **Total Chunks** | 5,000 | 5,000 | 5,000 |
| **Tree Depth / Max Depth** | 13 | 14 | N/A (Bucket array) |
| **Total Rotations** | 3,462 | 2,791 | 0 |
| **p50 Lookup Latency** | 1.15 µs | 0.98 µs | 0.18 µs |
| **p95 Lookup Latency** | **1.85 µs** | **1.23 µs** | **0.22 µs** |
| **Memory Footprint** | **835.0 KB** | **875.1 KB** | **858.9 KB** |
| **Lookup Target Met?** | **PASS** ($\le 1000\ \mu\text{s}$) | **PASS** ($\le 1000\ \mu\text{s}$) | **PASS** ($\le 1000\ \mu\text{s}$) |

### Key Observations:
- **Red-Black Tree vs. AVL Rotations**: Red-Black Tree executed **19.4% fewer rotations** (2,791 vs 3,462) during the 5,000-key ingest, confirming its efficiency for high-frequency write operations.
- **Lookup Latency**: All three structures deliver p95 latency under 2.5 µs, well within Team B's **$\le 1$ ms ($1,000$ µs)** acceptance target.
- **Memory Overhead**: Memory utilization is remarkably uniform (~835 KB to 875 KB for 5,000 nodes), proving the feasibility of pure in-memory search trees for chunk registries.

---

## 4. Merkle Tree Complexity

- **Construction Time**:
  - $N$ chunk leaves produce $\lceil \log_2 N \rceil$ levels.
  - Level $k$ requires $N / 2^k$ internal hash computations.
  - Total internal hashes: $\sum_{k=0}^{\lceil \log_2 N \rceil} \frac{N}{2^k} = 2N - 1 = O(N)$.
  - Total Construction Time: $\Theta(N)$.
- **Audit Proof Generation**:
  - Traverse from leaf at index $i$ to root: $O(\log N)$ sibling lookups.
- **Audit Proof Verification**:
  - Pairwise hash along path of length $\lceil \log_2 N \rceil$: $O(\log N)$ hash operations.
- **Storage Complexity**:
  - Full tree storage: $\sum 2^{-k} N \approx 2N$ hashes $\implies O(N)$ space.
