import unittest
from src.core.index.index_registry import IndexRegistry, StaleIndexVersionError
from src.core.dedup.engine import DedupEngine, InvalidHashAlgorithmError
from src.models.schemas import DedupComputeRequest

class TestDedupEngine(unittest.TestCase):
    def setUp(self):
        self.registry = IndexRegistry(index_version="v1.0.0")
        self.engine = DedupEngine(self.registry)

    def test_first_and_second_backup_dedup(self):
        # 1st backup: new file with unique blocks
        content = "".join([f"Unique sector block {i:04d} with random entropy {i*31:08x}.\n" for i in range(100)])
        req1 = DedupComputeRequest(
            file_id="doc_v1.txt",
            chunk_boundaries="fixed",
            chunk_size=512,
            hash_algorithm="SHA-256",
            index_version="v1.0.0",
            raw_text=content
        )
        res1 = self.engine.compute(req1)
        self.assertEqual(res1.unique_chunks, res1.total_chunks)
        self.assertEqual(res1.duplicate_chunks, 0)
        self.assertEqual(res1.savings_ratio, 0.0)

        # 2nd backup: identical file
        req2 = DedupComputeRequest(
            file_id="doc_v1_copy.txt",
            chunk_boundaries="fixed",
            chunk_size=512,
            hash_algorithm="SHA-256",
            index_version="v1.0.0",
            raw_text=content
        )
        res2 = self.engine.compute(req2)
        self.assertEqual(res2.unique_chunks, 0)
        self.assertEqual(res2.duplicate_chunks, res2.total_chunks)
        self.assertEqual(res2.savings_ratio, 1.0)
        self.assertEqual(res2.delta_size_bytes, 0)
        self.assertEqual(res1.merkle_root, res2.merkle_root)

    def test_partial_modification_dedup(self):
        content1 = "".join([f"Block A: System architecture line {i}.\n" for i in range(50)])
        content2 = content1 + "".join([f"Block B: Newly appended changes line {i}.\n" for i in range(25)])

        # Ingest content 1
        req1 = DedupComputeRequest(file_id="file1", chunk_size=256, raw_text=content1)
        res1 = self.engine.compute(req1)

        # Ingest content 2
        req2 = DedupComputeRequest(file_id="file2", chunk_size=256, raw_text=content2)
        res2 = self.engine.compute(req2)

        self.assertGreater(res2.duplicate_chunks, 0)
        self.assertGreater(res2.unique_chunks, 0)
        self.assertGreater(res2.savings_ratio, 0.0)
        self.assertLess(res2.savings_ratio, 1.0)

    def test_reject_mismatched_hash_algo(self):
        req = DedupComputeRequest(
            file_id="test_fail",
            hash_algorithm="MD5_UNKNOWN",
            raw_text="sample"
        )
        with self.assertRaises(InvalidHashAlgorithmError):
            self.engine.compute(req)

    def test_reject_stale_index_version(self):
        req = DedupComputeRequest(
            file_id="test_fail",
            index_version="v0.0.1_STALE",
            raw_text="sample"
        )
        with self.assertRaises(StaleIndexVersionError):
            self.engine.compute(req)

if __name__ == "__main__":
    unittest.main()
