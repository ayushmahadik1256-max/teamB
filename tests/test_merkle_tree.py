import unittest
from src.core.integrity.merkle_tree import MerkleTree

class TestMerkleTree(unittest.TestCase):
    def test_empty_merkle_tree(self):
        tree = MerkleTree([])
        root = tree.get_root()
        self.assertIsNotNone(root)
        self.assertEqual(len(root), 64)

    def test_deterministic_root(self):
        chunks = ["hash_1", "hash_2", "hash_3", "hash_4", "hash_5"]
        tree1 = MerkleTree(chunks)
        tree2 = MerkleTree(chunks)
        self.assertEqual(tree1.get_root(), tree2.get_root(), "Merkle root must be deterministic")

    def test_audit_proof_verification(self):
        chunks = [f"chunk_leaf_hash_{i}" for i in range(8)]
        tree = MerkleTree(chunks)
        root = tree.get_root()

        for idx in range(len(chunks)):
            proof = tree.get_proof(idx)
            is_valid = MerkleTree.verify_proof(chunks[idx], proof, root)
            self.assertTrue(is_valid, f"Proof verification failed for leaf {idx}")

    def test_tamper_detection(self):
        original_chunks = [f"clean_hash_{i}" for i in range(10)]
        tampered_chunks = list(original_chunks)
        tampered_chunks[3] = "corrupted_payload_hash_xyz"

        is_valid, verified, corrupted, root, lat_ms = MerkleTree.verify_integrity(
            original_chunks,
            tampered_chunks
        )
        self.assertFalse(is_valid)
        self.assertEqual(len(corrupted), 1)
        self.assertEqual(corrupted[0], "corrupted_payload_hash_xyz")
        self.assertEqual(len(verified), 9)

if __name__ == "__main__":
    unittest.main()
