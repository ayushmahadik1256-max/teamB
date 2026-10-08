import time
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from ..models.schemas import (
    DedupComputeRequest, DedupResult, ChunkIndexResponse, ChunkRecord,
    IntegrityVerifyRequest, IntegrityVerifyResult, HashIndexLookupResponse,
    CacheInvalidateRequest, CacheInvalidateResponse, DedupMetricsResponse
)
from ..models.contracts import SuccessResponse
from ..core.index.index_registry import IndexRegistry, StaleIndexVersionError
from ..core.dedup.engine import DedupEngine, InvalidHashAlgorithmError
from ..core.integrity.merkle_tree import MerkleTree
from ..core.metrics.collector import MetricsCollector
from .middleware import build_meta, error_response

# Shared singleton instances across routes
index_registry = IndexRegistry(index_version="v1.0.0", default_adapter="rbtree")
dedup_engine = DedupEngine(index_registry)
metrics_collector = MetricsCollector(index_registry, dedup_engine)

router = APIRouter()

# -------------------------------------------------------------
# Health & Service Discovery
# -------------------------------------------------------------
@router.get("/health", tags=["Health"])
@router.get("/api/v1/health", tags=["Health"])
def health(request: Request):
    return SuccessResponse(
        data={"status": "UP", "service": "Team B Deduplication & Integrity Engine"},
        meta=build_meta(request)
    )

# -------------------------------------------------------------
# B1 & B2: Deduplication Endpoints
# -------------------------------------------------------------
@router.post("/api/v1/dedup/compute", response_model=SuccessResponse[DedupResult], tags=["Deduplication"])
def compute_deduplication(request: Request, body: DedupComputeRequest):
    """
    Computes deduplication, delta, savings ratio, and Merkle root for a file.
    Rejects mismatched hash algorithms or stale index versions.
    """
    corr_id = getattr(request.state, "correlation_id", "")
    try:
        result = dedup_engine.compute(body)
        return SuccessResponse(data=result, meta=build_meta(request))
    except InvalidHashAlgorithmError as e:
        return error_response("INVALID_HASH_ALGORITHM", str(e), status_code=400, correlation_id=corr_id)
    except StaleIndexVersionError as e:
        return error_response("STALE_INDEX_VERSION", str(e), status_code=409, correlation_id=corr_id)
    except Exception as e:
        return error_response("COMPUTATION_FAILED", str(e), status_code=500, correlation_id=corr_id)

@router.get("/api/v1/dedup/{resultId}", response_model=SuccessResponse[DedupResult], tags=["Deduplication"])
def get_dedup_result(request: Request, resultId: str):
    """
    Retrieve stored deduplication results, savings ratio, and algorithm metadata by result ID.
    """
    corr_id = getattr(request.state, "correlation_id", "")
    result = dedup_engine.get_result(resultId)
    if not result:
        return error_response("RESOURCE_NOT_FOUND", f"Dedup result '{resultId}' not found", status_code=404, correlation_id=corr_id)
    return SuccessResponse(data=result, meta=build_meta(request))

@router.get("/api/v1/chunks/index", response_model=SuccessResponse[ChunkIndexResponse], tags=["Chunk Registry"])
def get_chunk_index(request: Request):
    """
    Renders chunk index coverage, total indexed chunks, bytes, and version.
    """
    chunks = index_registry.get_all_chunks()
    resp = ChunkIndexResponse(
        chunk_version=index_registry.index_version,
        total_chunks=len(chunks),
        total_bytes=index_registry.total_size_bytes(),
        chunks=chunks
    )
    return SuccessResponse(data=resp, meta=build_meta(request))

@router.put("/internal/v1/chunks/{chunkId}", response_model=SuccessResponse[ChunkRecord], tags=["Internal Registry"])
def put_chunk_record(request: Request, chunkId: str, body: ChunkRecord):
    """
    Internal endpoint for Team C / Admin to register or update an authoritative chunk record.
    """
    corr_id = getattr(request.state, "correlation_id", "")
    try:
        index_registry.register_chunk(
            chunk_id=chunkId,
            chunk_hash=body.chunk_hash,
            chunk_size=body.chunk_size,
            file_id="authoritative_sync"
        )
        return SuccessResponse(data=body, meta=build_meta(request))
    except Exception as e:
        return error_response("CHUNK_REGISTRATION_FAILED", str(e), status_code=400, correlation_id=corr_id)

# -------------------------------------------------------------
# B3: Hash Index & Cache Invalidation
# -------------------------------------------------------------
@router.get("/internal/v1/hash-index/{key}", response_model=SuccessResponse[HashIndexLookupResponse], tags=["Internal Index"])
def lookup_hash_index(request: Request, key: str):
    """
    Direct hash index lookup with microsecond latency measurement and cache status.
    """
    entry, lookup_us, hit = index_registry.lookup(key)
    resp = HashIndexLookupResponse(
        key=key,
        existing_chunk_ref=entry.chunk_id if entry else None,
        found=entry is not None,
        lookup_time_us=round(lookup_us, 2),
        cache_hit=hit,
        index_version=index_registry.index_version,
        index_type=index_registry.active_adapter_name
    )
    return SuccessResponse(data=resp, meta=build_meta(request))

@router.post("/internal/v1/hash-cache/invalidate", response_model=SuccessResponse[CacheInvalidateResponse], tags=["Internal Cache"])
def invalidate_cache(request: Request, body: CacheInvalidateRequest):
    """
    Invalidates stale cache entries (single key or full cache).
    """
    if body.invalidate_all:
        count, latency_ms = index_registry.cache.invalidate_all()
        status_text = f"Invalidated {count} cache entries"
    elif body.key:
        removed, latency_ms = index_registry.cache.invalidate(body.key)
        count = 1 if removed else 0
        status_text = "Key invalidated" if removed else "Key not in cache"
    else:
        count = 0
        latency_ms = 0.0
        status_text = "No action specified"

    resp = CacheInvalidateResponse(
        invalidated_count=count,
        invalidation_latency_ms=round(latency_ms, 3),
        status=status_text
    )
    return SuccessResponse(data=resp, meta=build_meta(request))

# -------------------------------------------------------------
# B4: Integrity Verification & Telemetry
# -------------------------------------------------------------
@router.post("/api/v1/integrity/verify", response_model=SuccessResponse[IntegrityVerifyResult], tags=["Integrity Verification"])
def verify_integrity(request: Request, body: IntegrityVerifyRequest):
    """
    Run deterministic Merkle-tree integrity verification and corruption analysis.
    """
    corr_id = getattr(request.state, "correlation_id", "")
    t0 = time.perf_counter()

    tree = MerkleTree(body.chunk_hashes)
    merkle_root = tree.get_root()

    is_valid = True
    corrupted: list = []
    verified: list = list(body.chunk_hashes)

    if body.expected_merkle_root:
        if merkle_root != body.expected_merkle_root:
            is_valid = False
            # Locate corrupted chunks if an expected root was given but failed
            corrupted.append(f"root_mismatch:expected_{body.expected_merkle_root}_got_{merkle_root}")

    latency_ms = (time.perf_counter() - t0) * 1000.0
    metrics_collector.record_verification(latency_ms)

    result = IntegrityVerifyResult(
        file_id=body.file_id,
        merkle_root=merkle_root,
        expected_merkle_root=body.expected_merkle_root,
        is_valid=is_valid,
        total_chunks=len(body.chunk_hashes),
        verified_chunks=verified if is_valid else [],
        corrupted_chunks=corrupted,
        verification_latency_ms=round(latency_ms, 3),
        algorithm=body.verification_algorithm,
        evidence={
            "tree_levels": len(tree.levels),
            "chunk_count": len(body.chunk_hashes),
            "ordering_rule": "Ascending file byte offset [0..N-1]"
        }
    )
    return SuccessResponse(data=result, meta=build_meta(request))

@router.get("/api/v1/metrics/dedup", response_model=SuccessResponse[DedupMetricsResponse], tags=["Telemetry"])
def get_dedup_metrics(request: Request):
    """
    Telemetry endpoint returning p95 computation latency, cache hit rate,
    lookup latency, and index memory statistics.
    """
    metrics = metrics_collector.collect_metrics()
    return SuccessResponse(data=metrics, meta=build_meta(request))
