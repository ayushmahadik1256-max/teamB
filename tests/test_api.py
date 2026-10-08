import unittest
from starlette.testclient import TestClient
from src.main import app

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertIn("data", json_data)
        self.assertEqual(json_data["data"]["status"], "UP")
        self.assertIn("meta", json_data)
        self.assertIn("correlation_id", json_data["meta"])

    def test_dedup_compute_lifecycle(self):
        headers = {"X-Correlation-ID": "test-corr-123"}
        payload = {
            "file_id": "api_test_file.txt",
            "chunk_boundaries": "fixed",
            "chunk_size": 2048,
            "hash_algorithm": "SHA-256",
            "index_version": "v1.0.0",
            "raw_text": "Sample text content for testing Team B HTTP endpoints." * 100
        }
        res = self.client.post("/api/v1/dedup/compute", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        result_id = data["dedup_result_id"]
        self.assertIsNotNone(result_id)
        self.assertGreater(data["total_chunks"], 0)
        self.assertEqual(res.headers.get("X-Correlation-ID"), "test-corr-123")

        # Query GET /dedup/{resultId}
        get_res = self.client.get(f"/api/v1/dedup/{result_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["data"]["dedup_result_id"], result_id)

    def test_dedup_invalid_hash_algorithm(self):
        payload = {
            "file_id": "api_test_file.txt",
            "hash_algorithm": "UNSUPPORTED_ALGO_XYZ",
            "raw_text": "hello"
        }
        res = self.client.post("/api/v1/dedup/compute", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())
        self.assertEqual(res.json()["error"]["code"], "INVALID_HASH_ALGORITHM")

    def test_dedup_stale_index_version(self):
        payload = {
            "file_id": "api_test_file.txt",
            "index_version": "v999.0.0_STALE",
            "raw_text": "hello"
        }
        res = self.client.post("/api/v1/dedup/compute", json=payload)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["error"]["code"], "STALE_INDEX_VERSION")

    def test_chunk_index_summary(self):
        res = self.client.get("/api/v1/chunks/index")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIn("total_chunks", data)
        self.assertIn("total_bytes", data)

    def test_internal_chunk_put(self):
        payload = {
            "chunk_id": "chk_ext_12345",
            "chunk_hash": "a" * 64,
            "chunk_size": 4096,
            "hash_algorithm": "SHA-256"
        }
        res = self.client.put("/internal/v1/chunks/chk_ext_12345", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["chunk_id"], "chk_ext_12345")

    def test_internal_hash_lookup_and_cache(self):
        # Put chunk
        h = "b" * 64
        self.client.put("/internal/v1/chunks/chk_b", json={"chunk_id": "chk_b", "chunk_hash": h, "chunk_size": 1024})
        
        # 1st lookup: cache miss
        res1 = self.client.get(f"/internal/v1/hash-index/{h}")
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()["data"]["found"])

        # 2nd lookup: cache hit
        res2 = self.client.get(f"/internal/v1/hash-index/{h}")
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json()["data"]["cache_hit"])

        # Invalidate cache
        inv_res = self.client.post("/internal/v1/hash-cache/invalidate", json={"key": h})
        self.assertEqual(inv_res.status_code, 200)
        self.assertEqual(inv_res.json()["data"]["invalidated_count"], 1)

    def test_integrity_verify_endpoint(self):
        payload = {
            "file_id": "file_verify.dat",
            "chunk_hashes": ["hash_1", "hash_2", "hash_3"],
            "verification_algorithm": "merkle_tree"
        }
        res = self.client.post("/api/v1/integrity/verify", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertTrue(data["is_valid"])
        self.assertIsNotNone(data["merkle_root"])

    def test_metrics_endpoint(self):
        res = self.client.get("/api/v1/metrics/dedup")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIn("dedup_computation_p95_ms", data)
        self.assertIn("hash_index_lookup_p95_us", data)
        self.assertIn("cache_hit_rate_pct", data)

if __name__ == "__main__":
    unittest.main()
