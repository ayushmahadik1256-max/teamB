import unittest
from src.core.chunking.fixed_chunker import FixedSizeChunker
from src.core.chunking.cdc_chunker import ContentDefinedChunker
from src.core.chunking.base import BaseChunker

class TestChunking(unittest.TestCase):
    def test_fixed_chunker_basic(self):
        chunker = FixedSizeChunker(chunk_size=1024)
        data = b"A" * 2500  # Expect 3 chunks: 1024, 1024, 452
        chunks = chunker.chunk(data, hash_algorithm="SHA-256")
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].chunk_size, 1024)
        self.assertEqual(chunks[1].chunk_size, 1024)
        self.assertEqual(chunks[2].chunk_size, 452)
        self.assertEqual(chunks[0].offset, 0)
        self.assertEqual(chunks[1].offset, 1024)
        self.assertEqual(chunks[2].offset, 2048)

    def test_fixed_chunker_empty(self):
        chunker = FixedSizeChunker(chunk_size=1024)
        chunks = chunker.chunk(b"")
        self.assertEqual(len(chunks), 0)

    def test_cdc_chunker_basic(self):
        chunker = ContentDefinedChunker(avg_chunk_size=1024, min_chunk_size=256, max_chunk_size=2048, window_size=16)
        data = b"".join([f"Block_{i:04d}_entropy_{i*2654435761:08x}\n".encode() * 4 for i in range(50)])
        chunks = chunker.chunk(data, hash_algorithm="SHA-256")
        self.assertGreater(len(chunks), 0)
        total_size = sum(c.chunk_size for c in chunks)
        self.assertEqual(total_size, len(data))

    def test_cdc_boundary_shift_resistance(self):
        """
        Tests that inserting bytes at the beginning of a file does NOT shift
        the boundaries of downstream chunks in Content-Defined Chunking.
        """
        chunker = ContentDefinedChunker(avg_chunk_size=512, min_chunk_size=128, max_chunk_size=2048, window_size=16)
        base_text = b"".join([f"block_{i:04d}_with_lots_of_unique_entropy_data_{i*7919:08x}_end.\n".encode() * 5 for i in range(100)])
        chunks1 = chunker.chunk(base_text)

        # Prepend a small modification at head
        modified_text = b"PREFIX_HEADER_1234567890_" + base_text
        chunks2 = chunker.chunk(modified_text)

        hashes1 = set(c.chunk_hash for c in chunks1)
        hashes2 = set(c.chunk_hash for c in chunks2)
        common = hashes1.intersection(hashes2)

        # CDC must preserve a significant number of identical chunks despite prefix insertion
        self.assertGreater(len(common), len(chunks1) // 2, "CDC preserved fewer than 50% of chunks across shifted content")

    def test_hash_algorithms(self):
        data = b"Testing multiple hash algorithms"
        sha256_hash = BaseChunker.compute_hash(data, "SHA-256")
        rk_hash = BaseChunker.compute_hash(data, "Rabin-Karp")
        self.assertEqual(len(sha256_hash), 64)
        self.assertEqual(len(rk_hash), 16)
        with self.assertRaises(ValueError):
            BaseChunker.compute_hash(data, "MD5_UNSUPPORTED")

if __name__ == "__main__":
    unittest.main()
