import sys
from typing import Any, Optional, List, Tuple
from .base import BaseIndex

class AVLNode:
    __slots__ = ("key", "value", "height", "left", "right")
    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value
        self.height = 1
        self.left: Optional["AVLNode"] = None
        self.right: Optional["AVLNode"] = None

class AVLTreeIndex(BaseIndex):
    """
    Self-balancing AVL Tree Index adapter.
    Guarantees strict height balance where |height(left) - height(right)| <= 1.
    Theoretical search/insert/delete complexity: O(log n).
    """
    def __init__(self):
        self.root: Optional[AVLNode] = None
        self._count = 0
        self.rotations = 0

    def _get_height(self, node: Optional[AVLNode]) -> int:
        return node.height if node else 0

    def _get_balance(self, node: Optional[AVLNode]) -> int:
        if not node:
            return 0
        return self._get_height(node.left) - self._get_height(node.right)

    def _update_height(self, node: AVLNode) -> None:
        node.height = 1 + max(self._get_height(node.left), self._get_height(node.right))

    def _right_rotate(self, y: AVLNode) -> AVLNode:
        x = y.left
        assert x is not None
        T2 = x.right

        # Perform rotation
        x.right = y
        y.left = T2

        # Update heights
        self._update_height(y)
        self._update_height(x)
        self.rotations += 1
        return x

    def _left_rotate(self, x: AVLNode) -> AVLNode:
        y = x.right
        assert y is not None
        T2 = y.left

        # Perform rotation
        y.left = x
        x.right = T2

        # Update heights
        self._update_height(x)
        self._update_height(y)
        self.rotations += 1
        return y

    def _insert(self, node: Optional[AVLNode], key: str, value: Any) -> AVLNode:
        if not node:
            self._count += 1
            return AVLNode(key, value)

        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            # Key already exists, update value
            node.value = value
            return node

        self._update_height(node)
        balance = self._get_balance(node)

        # 4 balancing cases:
        # Left-Left
        if balance > 1 and node.left and key < node.left.key:
            return self._right_rotate(node)

        # Right-Right
        if balance < -1 and node.right and key > node.right.key:
            return self._left_rotate(node)

        # Left-Right
        if balance > 1 and node.left and key > node.left.key:
            node.left = self._left_rotate(node.left)
            return self._right_rotate(node)

        # Right-Left
        if balance < -1 and node.right and key < node.right.key:
            node.right = self._right_rotate(node.right)
            return self._left_rotate(node)

        return node

    def put(self, key: str, value: Any) -> None:
        self.root = self._insert(self.root, key, value)

    def get(self, key: str) -> Optional[Any]:
        curr = self.root
        while curr:
            if key == curr.key:
                return curr.value
            elif key < curr.key:
                curr = curr.left
            else:
                curr = curr.right
        return None

    def contains(self, key: str) -> bool:
        return self.get(key) is not None

    def _min_value_node(self, node: AVLNode) -> AVLNode:
        current = node
        while current.left is not None:
            current = current.left
        return current

    def _delete(self, root: Optional[AVLNode], key: str, deleted_flag: List[bool]) -> Optional[AVLNode]:
        if not root:
            return root

        if key < root.key:
            root.left = self._delete(root.left, key, deleted_flag)
        elif key > root.key:
            root.right = self._delete(root.right, key, deleted_flag)
        else:
            deleted_flag[0] = True
            if root.left is None:
                temp = root.right
                root = None
                return temp
            elif root.right is None:
                temp = root.left
                root = None
                return temp

            temp = self._min_value_node(root.right)
            root.key = temp.key
            root.value = temp.value
            root.right = self._delete(root.right, temp.key, [False])

        if root is None:
            return root

        self._update_height(root)
        balance = self._get_balance(root)

        # Balance after deletion
        if balance > 1 and self._get_balance(root.left) >= 0:
            return self._right_rotate(root)
        if balance > 1 and self._get_balance(root.left) < 0:
            if root.left:
                root.left = self._left_rotate(root.left)
            return self._right_rotate(root)
        if balance < -1 and self._get_balance(root.right) <= 0:
            return self._left_rotate(root)
        if balance < -1 and self._get_balance(root.right) > 0:
            if root.right:
                root.right = self._right_rotate(root.right)
            return self._left_rotate(root)

        return root

    def delete(self, key: str) -> bool:
        flag = [False]
        self.root = self._delete(self.root, key, flag)
        if flag[0]:
            self._count -= 1
        return flag[0]

    def size(self) -> int:
        return self._count

    def get_all_entries(self) -> List[Tuple[str, Any]]:
        entries: List[Tuple[str, Any]] = []
        def inorder(node: Optional[AVLNode]):
            if node:
                inorder(node.left)
                entries.append((node.key, node.value))
                inorder(node.right)
        inorder(self.root)
        return entries

    def memory_usage_bytes(self) -> int:
        total = sys.getsizeof(self)
        def calc_node(node: Optional[AVLNode]):
            nonlocal total
            if not node:
                return
            total += sys.getsizeof(node)
            total += sys.getsizeof(node.key)
            calc_node(node.left)
            calc_node(node.right)
        calc_node(self.root)
        return total

    def get_stats(self) -> dict:
        return {
            "type": "AVLTreeIndex",
            "size": self._count,
            "height": self._get_height(self.root),
            "rotations": self.rotations,
            "memory_bytes": self.memory_usage_bytes()
        }
