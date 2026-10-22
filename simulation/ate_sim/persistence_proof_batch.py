"""Final-path merge of locator-sorted deltas; the caller owns the transaction."""
from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import Branch, Leaf, key_locator
from .persistence_proof_map import _nibbles, _prefix


def update_sorted(proof_map, root, changes):
    """Apply exact-key changes in strictly increasing domain locator order.

    The input is streamed, not sorted here. Late input or callback failures
    propagate: the caller must roll back any immutable writes before reusing
    its transaction. This helper never publishes a head or retains a cache.
    """
    proof_map._reference(root)
    source = iter(changes)
    current = None
    previous = None

    def advance():
        nonlocal current, previous
        try:
            item = next(source)
        except StopIteration:
            current = None
            return
        if (type(item) not in (tuple, list) or len(item) != 2
                or type(item[0]) is not bytes
                or item[1] is not None and (type(item[1]) is not bytes or len(item[1]) != 32)):
            raise StoreIntegrityError('invalid proof batch change')
        locator = key_locator(proof_map.map_domain, item[0])
        if previous is not None and locator <= previous:
            raise StoreIntegrityError('proof batch locators must be strictly increasing')
        previous = locator
        current = (locator, _nibbles(locator), item[1])

    def includes(prefix):
        return current is not None and current[1][:len(prefix)] == prefix

    def build(prefix):
        # In an empty range, ascending locators let us finish a subtree as
        # soon as the next locator leaves its prefix. Later input can only
        # wrap that finished subtree, never modify it. Thus singleton paths
        # need no 64-level virtual walk and every emitted node is final.
        while includes(prefix) and current[2] is None:
            advance()
        if not includes(prefix):
            return proof_map.empty, None
        locator, first, commitment = current
        advance()
        node = Leaf(locator, commitment)
        result = proof_map._write(node)
        while includes(prefix):
            if current[2] is None:
                advance()
                continue
            depth = len(prefix)
            while first[depth] == current[1][depth]:
                depth += 1
            parent = first[:depth]
            children = [(first[depth], result)]
            while includes(parent):
                slot = current[1][depth]
                child, _ = build(parent + (slot,))
                if child.count:
                    children.append((slot, child))
            if len(children) > 1:
                node = Branch(parent, tuple(children))
                result = proof_map._write(node)
        return result, node

    def merge(ref, prefix, checked=None):
        if not includes(prefix):
            return ref, checked
        if not ref.count:
            return build(prefix)
        if ref.count and checked is None:
            checked = proof_map._read(ref, prefix)
        depth = len(prefix)
        if depth == 64:
            locator, _, commitment = current
            advance()
            if commitment is None:
                return proof_map.empty, None
            if checked is not None and commitment == checked.commitment:
                return ref, checked
            leaf = Leaf(locator, commitment)
            return proof_map._write(leaf), leaf

        # A compressed node is carried down its virtual single-child path
        # without fetching it again. No intermediate single-child node is
        # encoded. Real branches keep only their bounded child inventory.
        old_children = {}
        if checked is not None:
            old_prefix = _prefix(checked)
            if len(old_prefix) == depth:
                old_children = dict(checked.children)
            else:
                old_children[old_prefix[depth]] = ref
        children = []
        survivor = None
        for slot in range(16):
            old = old_children.get(slot, proof_map.empty)
            carried = checked if old is ref else None
            child, child_node = merge(old, prefix + (slot,), carried) if includes(prefix + (slot,)) else (old, carried)
            if child.count:
                children.append((slot, child))
                survivor = child_node
        if not children:
            return proof_map.empty, None
        if len(children) == 1:
            slot, child = children[0]
            if survivor is None:
                survivor = proof_map._read(child, prefix + (slot,))
            return child, survivor
        branch = Branch(prefix, tuple(children))
        if branch == checked:
            return ref, checked
        return proof_map._write(branch), branch

    advance()
    result, _ = merge(root, ())
    return root if result == root else result
