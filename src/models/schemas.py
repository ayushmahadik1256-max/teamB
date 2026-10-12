from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class ChunkModel(BaseModel):
    chunk_id: str
    chunk_hash: str
    chunk_size: int
    offset: int
    is_duplicate: bool = False
    reference_count: int = 1

class ChunkRequest(BaseModel):
    chunk_request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_id: str
    chunk_size: int = 65536
    hash_algorithm: str = "SHA-256"
    chunk_boundaries: str = "fixed"  # "fixed" or "content-defined"
    version_ref: Optional[str] = None
    content_b64: Optional[str] = None
    raw_content: Optional[str] = None

class ChunkRecord(BaseModel):
    chunk_id: str
    chunk_hash: str
    chunk_size: int
    hash_algorithm: str = "SHA-256"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "ACTIVE"
    byte_content: Optional[str] = None  # Base64 encoded if stored

class ChunkIndexEntry(BaseModel):
    chunk_id: str
    chunk_hash: str
    chunk_size: int
    reference_count: int
    first_seen_file_id: str
    index_version: str

class ChunkIndexResponse(BaseModel):
    chunk_version: str
    total_chunks: int
    total_bytes: int
    chunks: List[ChunkIndexEntry]

class DedupComputeRequest(BaseModel):
    file_id: str
    chunk_boundaries: str = "fixed"  # "fixed" or "content-defined"
    chunk_size: int = 65536
    hash_algorithm: str = "SHA-256"
    index_version: str = "v1.0.0"
    diff_algorithm: str = "chunk-diff-v1"
    optimization_metric: str = "savings_ratio"
    content_b64: Optional[str] = None
    raw_text: Optional[str] = None
    existing_chunk_ids: Optional[List[str]] = None


class DedupResult(BaseModel):
    dedup_result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_id: str
    total_chunks: int
    unique_chunks: int
    duplicate_chunks: int
    unique_chunk_ids: List[str]
    duplicate_chunk_ids: List[str]
    chunk_refs: List[str] = Field(default_factory=list)  # <-- Added for Team C compatibility
    original_size_bytes: int
    delta_size_bytes: int
    savings_ratio: float
    algorithm: str
    hash_algorithm: str
    index_version: str
    merkle_root: str
    computed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class IntegrityVerifyRequest(BaseModel):
    file_id: str
    chunk_hashes: List[str] = Field(default_factory=list)  # <-- Default empty list
    expected_merkle_root: Optional[str] = None
    merkle_root: Optional[str] = None                     # <-- Accept Team C's key name
    verification_algorithm: str = "merkle_tree"
    benchmark_reps: int = 1
    simulate_corruption: Optional[bool] = False

class IntegrityVerifyResult(BaseModel):
    file_id: str
    merkle_root: str
    expected_merkle_root: Optional[str] = None
    is_valid: bool
    verified: bool = True                                 # <-- Added for Team C compatibility
    total_chunks: int
    verified_chunks: List[str]
    corrupted_chunks: List[str]
    verification_latency_ms: float
    algorithm: str
    evidence: Dict[str, Any]

class HashIndexLookupResponse(BaseModel):
    key: str
    existing_chunk_ref: Optional[str] = None
    found: bool
    lookup_time_us: float
    cache_hit: bool
    index_version: str
    index_type: str

class CacheInvalidateRequest(BaseModel):
    key: Optional[str] = None
    invalidate_all: bool = False

class CacheInvalidateResponse(BaseModel):
    invalidated_count: int
    invalidation_latency_ms: float
    status: str

class DedupMetricsResponse(BaseModel):
    service: str = "Team B - Deduplication & Integrity Engine"
    index_version: str
    active_index_adapter: str
    total_chunks_indexed: int
    total_dedup_operations: int
    cache_hit_rate_pct: float
    cache_total_hits: int
    cache_total_misses: int
    dedup_computation_p95_ms: float
    hash_index_lookup_p95_us: float
    verification_p95_ms: float
    memory_footprint_bytes: Dict[str, int]
    tree_depth: Optional[int] = None
