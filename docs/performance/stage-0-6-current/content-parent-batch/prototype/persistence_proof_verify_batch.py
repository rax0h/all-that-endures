"""Read-only membership proofs over the union of sorted requested paths."""
from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import Leaf, key_locator
from .persistence_proof_map import _nibbles, _prefix


class ProofValueMismatch(StoreIntegrityError):
    """A fully checked selected path disagrees with its expected commitment."""


def verify_sorted(proof_map, root, members):
    """Verify (typed_key, commitment-or-None) in strict locator order.

    Only one current member and the checked recursion path are retained. Every
    visited node goes through the ordinary map reader; no node survives this
    call and no write callback is used. Late stream failures propagate.
    """
    proof_map._reference(root)
    source = iter(members)
    current = previous = None

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
            raise StoreIntegrityError('invalid expected proof member')
        locator = key_locator(proof_map.map_domain, item[0])
        if previous is not None and locator <= previous:
            raise StoreIntegrityError('expected proof locators must be strictly increasing')
        previous = locator
        current = _nibbles(locator), item[1]

    def includes(prefix):
        return current is not None and current[0][:len(prefix)] == prefix

    def expect(commitment):
        if current[1] != commitment:
            raise ProofValueMismatch('expected proof member differs from checked path')
        advance()

    def absent(prefix):
        while includes(prefix):
            expect(None)

    def visit(ref, required):
        if not includes(required):
            return
        if not ref.count:
            absent(required)
            return
        node = proof_map._read(ref, required)
        prefix = _prefix(node)
        # A compressed node leaves proven-empty ranges before and after it.
        while includes(required) and not includes(prefix) and current[0] < prefix:
            expect(None)
        if type(node) is Leaf:
            if includes(prefix):
                expect(node.commitment)
        else:
            children = dict(node.children)
            for slot in range(16):
                child_prefix = prefix + (slot,)
                if includes(child_prefix):
                    child = children.get(slot)
                    if child is None:
                        absent(child_prefix)
                    else:
                        visit(child, child_prefix)
        absent(required)

    advance()
    visit(root, ())
