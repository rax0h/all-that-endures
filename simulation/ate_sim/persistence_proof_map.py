"""Checked path-copy maps over immutable nodes, independent of World state."""
from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import (
    Root, Leaf, Branch, MAX_COUNT, empty_root, key_locator,
    encode_node, decode_node, node_digest,
)


def _nibbles(locator):
    return tuple(n for byte in locator for n in (byte >> 4, byte & 15))


def _prefix(node):
    return _nibbles(node.locator) if type(node) is Leaf else node.prefix


def _count(node):
    return 1 if type(node) is Leaf else sum(ref.count for _, ref in node.children)


class ProofMap:
    def __init__(self, map_domain, read_node, write_node):
        self.map_domain = map_domain
        self.empty = empty_root(map_domain)
        self.read_node, self.write_node = read_node, write_node

    def _reference(self, root):
        if (type(root) is not Root or type(root.digest) is not bytes or len(root.digest) != 32
                or type(root.count) is not int or not 0 <= root.count <= MAX_COUNT
                or root.count == 0 and root != self.empty):
            raise StoreIntegrityError('invalid proof root reference')

    def _read(self, root, required_prefix=()):
        self._reference(root)
        if root.count == 0:
            raise StoreIntegrityError('empty proof root used as a child')
        try:
            raw = self.read_node(root.digest)
        except KeyError as exc:
            raise StoreIntegrityError('missing immutable proof node') from exc
        if node_digest(self.map_domain, raw) != root.digest:
            raise StoreIntegrityError('proof node digest disagreement')
        node = decode_node(raw)
        if _count(node) != root.count or _prefix(node)[:len(required_prefix)] != required_prefix:
            raise StoreIntegrityError('proof child path/count disagreement')
        return node

    def _write(self, node):
        raw = encode_node(node)
        root = Root(node_digest(self.map_domain, raw), _count(node))
        self.write_node(root.digest, raw)
        return root

    def get(self, root, typed_key):
        wanted = _nibbles(key_locator(self.map_domain, typed_key))
        self._reference(root)
        if root.count == 0:
            return None
        required = ()
        while True:
            node = self._read(root, required)
            prefix = _prefix(node)
            if wanted[:len(prefix)] != prefix:
                return None
            if type(node) is Leaf:
                return node.commitment
            slot = wanted[len(prefix)]
            child = next((ref for chosen, ref in node.children if chosen == slot), None)
            if child is None:
                return None
            root, required = child, prefix + (slot,)

    def set(self, root, typed_key, commitment):
        locator = key_locator(self.map_domain, typed_key)
        wanted = _nibbles(locator)
        if commitment is not None and (type(commitment) is not bytes or len(commitment) != 32):
            raise StoreIntegrityError('invalid proof value commitment')
        self._reference(root)
        if root.count == 0:
            return root if commitment is None else self._write(Leaf(locator, commitment))
        current, required, path = root, (), []
        while True:
            node = self._read(current, required)
            prefix = _prefix(node)
            if wanted[:len(prefix)] != prefix:
                if commitment is None:
                    return root
                length = 0
                while length < len(prefix) and wanted[length] == prefix[length]:
                    length += 1
                added = self._write(Leaf(locator, commitment))
                result = self._write(Branch(prefix[:length], tuple(sorted((
                    (prefix[length], current), (wanted[length], added))))))
                break
            if type(node) is Leaf:
                if commitment == node.commitment:
                    return root
                result = None if commitment is None else self._write(Leaf(locator, commitment))
                break
            slot = wanted[len(prefix)]
            child = next((ref for chosen, ref in node.children if chosen == slot), None)
            if child is None:
                if commitment is None:
                    return root
                added = self._write(Leaf(locator, commitment))
                result = self._write(Branch(prefix, tuple(sorted((*node.children, (slot, added))))))
                break
            path.append((node, slot))
            current, required = child, prefix + (slot,)
        for node, slot in reversed(path):
            children = tuple((chosen, result if chosen == slot else ref)
                             for chosen, ref in node.children if chosen != slot or result is not None)
            if len(children) == 1:
                # This unchanged boundary becomes the new subtree root. Check
                # its bytes/count/path once before promoting it.
                chosen, result = children[0]
                self._read(result, node.prefix + (chosen,))
            else:
                result = self._write(Branch(node.prefix, children))
        return self.empty if result is None else result

    def iter_leaves(self, root):
        self._reference(root)
        if root.count == 0:
            return
        pending = [(root, ())]
        while pending:
            ref, required = pending.pop()
            node = self._read(ref, required)
            if type(node) is Leaf:
                yield node.locator, node.commitment
            else:
                pending.extend((child, node.prefix + (slot,))
                               for slot, child in reversed(node.children))
