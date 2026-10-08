import unittest
from src.core.index.avl_tree import AVLTreeIndex, AVLNode
from src.core.index.rb_tree import RedBlackTreeIndex, RED, BLACK
from src.core.index.hash_map_index import HashMapIndex
from src.core.index.cache import LRUHashCache
from src.core.index.index_registry import IndexRegistry, StaleIndexVersionError

class TestDataStructures(unittest.TestCase):
    def test_avl_tree_balance_and_operations(self):
        avl = AVLTreeIndex()
        keys = [f"key_{i:04d}" for i in range(100)]
        for k in keys:
            avl.put(k, f"val_{k}")

        self.assertEqual(avl.size(), 100)
        # Verify search
        for k in keys:
            self.assertEqual(avl.get(k), f"val_{k}")

        # Check AVL balance invariant on every node
        def check_balance(node):
            if not node:
                return True
            b = avl._get_balance(node)
            self.assertTrue(-1 <= b <= 1, f"AVL balance violated at key {node.key} with balance {b}")
            return check_balance(node.left) and check_balance(node.right)

        self.assertTrue(check_balance(avl.root))

        # Test deletion
        self.assertTrue(avl.delete("key_0050"))
        self.assertEqual(avl.size(), 99)
        self.assertIsNone(avl.get("key_0050"))
        self.assertTrue(check_balance(avl.root))

    def test_rb_tree_invariants(self):
        rb = RedBlackTreeIndex()
        keys = [f"chunk_hash_{i:03d}" for i in range(150)]
        for k in keys:
            rb.put(k, {"id": k})

        self.assertEqual(rb.size(), 150)
        for k in keys:
            self.assertEqual(rb.get(k), {"id": k})

        # Check RB invariants: Root is black
        self.assertEqual(rb.root.color, BLACK)

        # Check no consecutive red nodes
        def check_no_consecutive_red(node):
            if node == rb.NIL or node is None:
                return True
            if node.color == RED:
                if node.left and node.left.color == RED:
                    return False
                if node.right and node.right.color == RED:
                    return False
            return check_no_consecutive_red(node.left) and check_no_consecutive_red(node.right)

        self.assertTrue(check_no_consecutive_red(rb.root))

    def test_hash_map_index(self):
        hm = HashMapIndex()
        hm.put("hash_abc", "data_1")
        hm.put("hash_xyz", "data_2")
        self.assertEqual(hm.size(), 2)
        self.assertEqual(hm.get("hash_abc"), "data_1")
        self.assertTrue(hm.delete("hash_abc"))
        self.assertEqual(hm.size(), 1)
        self.assertIsNone(hm.get("hash_abc"))

    def test_lru_cache_hit_miss_and_invalidation(self):
        cache = LRUHashCache(capacity=3)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")

        # Hits
        self.assertEqual(cache.get("k1"), "v1")
        self.assertEqual(cache.get("k2"), "v2")

        # Eviction
        cache.put("k4", "v4")  # k3 was least recently used -> should be evicted
        self.assertIsNone(cache.get("k3"))
        self.assertEqual(cache.get("k4"), "v4")

        # Invalidation
        removed, lat_ms = cache.invalidate("k1")
        self.assertTrue(removed)
        self.assertIsNone(cache.get("k1"))
        self.assertLess(lat_ms, 2000.0, "Cache invalidation must complete within 2s")

        # Invalidate all
        count, lat_all = cache.invalidate_all()
        self.assertEqual(count, 2)
        self.assertEqual(cache.get_stats()["size"], 0)

    def test_index_registry_stale_version_rejection(self):
        registry = IndexRegistry(index_version="v1.0.0")
        with self.assertRaises(StaleIndexVersionError):
            registry.validate_index_version("v0.9.0")
        # Exact version passes
        registry.validate_index_version("v1.0.0")

if __name__ == "__main__":
    unittest.main()
