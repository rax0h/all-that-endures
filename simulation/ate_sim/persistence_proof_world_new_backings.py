"""Finite fresh backing forests, borrowing existing source/scope authority.

Accepted old targets terminate traversal at their authenticated backing fact.
Only newly allocated backing extents and their outgoing edges are visited.
"""
from functools import lru_cache
from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as HISTORY, PAGE_NAMESPACE, ENTRY_NAMESPACE
from .persistence_record_headers import NAMESPACE as RECORDS, checked_record_header
from .persistence_history_types import NAMESPACE as TYPES, TAG, member_counts, incoming_owner_policy
from .persistence_history_dependencies import NAMESPACE as DEPENDENCIES, dependency_value
from . import persistence_proof_world as world
from . import persistence_proof_scope as scope

MAX_PROJECTIONS = 4096
MAX_OLD_ALIASES = 4096


class Unsupported(Exception):
    """Keep the fully checked path for an unsupported or over-budget shape."""


@lru_cache(maxsize=128)
def _families(cls):
    return tuple(ns for ns in world.FAMILIES if world._record_class(ns) is cls)


class Forest:
    def __init__(self, store, request, by_key, predecessor):
        self.store, self.request, self.rows, self.predecessor = store, request, by_key, predecessor
        self.codec = store.codec
        self.backings, self.new_rows, self.children, self.edges = {}, set(), {}, set()
        self.old_targets = {}
        self.projections = 0
        self._collect()

    def old(self, namespace, key):
        ok, row = self.predecessor(namespace, self.codec.encode(key))
        if not ok:
            raise Unsupported()
        return row

    def value(self, namespace, key, *, successor=True, metadata=False):
        typed = self.codec.encode(key)
        item = self.rows.get((namespace, typed)) if successor else None
        if item is not None:
            if item['change'].delete or item['change'].record_schema != 1:
                raise Unsupported()
            payload, members = item['payload'], item['memberships_blob']
        else:
            row = self.old(namespace, key)
            if row is None or row.record_schema != 1:
                raise StoreIntegrityError('missing accepted backing source')
            payload, members = row.payload, row.memberships
        if metadata and members != self.codec.encode(()):
            raise StoreIntegrityError('backing metadata has memberships')
        return self.codec.decode(payload)

    def header(self, incarnation):
        value = self.value(RECORDS, (incarnation, 0), metadata=True)
        checked_record_header(value)
        return value

    def _fresh(self, namespace, key):
        marker = namespace, self.codec.encode(key)
        item = self.rows.get(marker)
        if (item is None or item['change'].delete or item['change'].reinsertion
                or item['change'].record_schema != 1 or self.old(namespace, key) is not None):
            raise Unsupported()
        self.new_rows.add(marker)
        return item

    def _collect(self):
        parent_allocator = self.request.pairs[1][0].next_incarnation_id
        for (namespace, typed), item in self.rows.items():
            if namespace not in (HISTORY, RECORDS) or item['change'].delete:
                continue
            key = self.codec.decode(typed)
            if self.old(namespace, key) is not None:
                continue
            incarnation = key[0] if namespace == RECORDS and type(key) is tuple and len(key) == 2 and key[1] == 0 else key
            if type(incarnation) is not int or not parent_allocator <= incarnation < 2**63:
                raise Unsupported()
            value = self.value(namespace, key, metadata=True)
            kind = 'record' if namespace == RECORDS else value[0] if type(value) is tuple and value else None
            if kind not in ('list', 'map', 'set', 'record'):
                raise Unsupported()
            world.target._validate_descriptor(kind, incarnation, value)
            if kind == 'record':
                _cls, _fields, state = checked_record_header(value)
                if state is not None:
                    raise Unsupported()
            if incarnation in self.backings:
                raise StoreIntegrityError('fresh incarnation has competing backing families')
            self._fresh(namespace, key)
            self.backings[incarnation] = kind, namespace, key, value
        for incarnation, (kind, namespace, key, value) in self.backings.items():
            child_rows = []
            members = []
            if kind == 'record':
                child_rows.append(self._fresh(RECORDS, key))
            else:
                expected_ns = PAGE_NAMESPACE if kind == 'list' else ENTRY_NAMESPACE
                ordinals = set()
                for (ns, typed), item in self.rows.items():
                    if ns not in (PAGE_NAMESPACE, ENTRY_NAMESPACE, RECORDS):
                        continue
                    child = self.codec.decode(typed)
                    if type(child) is not tuple or len(child) != 2 or child[0] != incarnation:
                        continue
                    if ns != expected_ns:
                        raise StoreIntegrityError('fresh backing has wrong-kind physical children')
                    self._fresh(ns, child)
                    change = item['change']
                    from dataclasses import replace
                    from .incremental_store import Membership
                    frozen = replace(change, key=child, value=self.codec.decode(item['payload']),
                                     memberships=tuple(Membership(*m) for m in self.codec.decode(item['memberships_blob'])))
                    world.AUXILIARY_OWNER_FAMILIES[ns].validate_source(frozen, 'lazy', self.codec)
                    if kind == 'list':
                        number = child[1]
                        if type(number) is not int or not 0 <= number < (value[1]+127)//128 or len(frozen.value) != min(128, value[1]-128*number):
                            raise StoreIntegrityError('fresh list page disagrees with extent')
                        ordinals.add(number)
                        members.extend(frozen.value)
                    else:
                        ordinal, native_key, member = frozen.value
                        if ordinal in ordinals or not 0 <= ordinal < value[2] or kind == 'set' and member is not None:
                            raise StoreIntegrityError('fresh map/set ordinal or value disagreement')
                        ordinals.add(ordinal)
                        members.append(native_key)
                    child_rows.append(item)
                expected_count = (value[1]+127)//128 if kind == 'list' else value[1]
                if len(child_rows) != expected_count:
                    raise StoreIntegrityError('fresh backing has incomplete physical extent')
                self._fresh(TYPES, incarnation)
                if self.codec.encode(self.value(TYPES, incarnation, metadata=True)) != self.codec.encode((TAG, kind, member_counts(members))):
                    raise StoreIntegrityError('fresh backing member counts disagree')
            self._fresh(DEPENDENCIES, incarnation)
            dependency = self.value(DEPENDENCIES, incarnation, metadata=True)
            if (type(dependency) is not tuple or len(dependency) != 3
                    or dependency != dependency_value(kind, dependency[2])):
                raise StoreIntegrityError('fresh backing dependency kind disagreement')
            self.children[incarnation] = tuple(child_rows)

    def project(self, change):
        ns = change.namespace
        if ns not in world.AUXILIARY_OWNER_FAMILIES:
            return tuple(world._project(self.store, ns, change.key, change.value, False, record_header=self.header))
        adapter = world.AUXILIARY_OWNER_FAMILIES[ns]
        adapter.validate_source(change, 'lazy', self.codec)
        if ns == RECORDS:
            cls, fields, _state = checked_record_header(change.value)
            world._check_field_values(self.store, None, cls, fields, self.header)
            for family in _families(cls):
                try:
                    world._check_field_values(self.store, family, cls, fields, self.header)
                except StoreIntegrityError:
                    # A generic backed record can use a different concrete
                    # container representation than its optimized World family.
                    raise Unsupported() from None
        return tuple((path, incarnation, world.target._reference(adapter.resolve_path(change.value, path))[0], None)
                     for path, incarnation in adapter.reference_placements(change.value))

    def _target(self, kind, incarnation):
        if incarnation in self.backings:
            actual, _ns, _key, value = self.backings[incarnation]
            if kind != actual:
                raise StoreIntegrityError('fresh reference has wrong target kind')
            return value
        if incarnation >= self.request.pairs[1][0].next_incarnation_id:
            if kind in ('sequence', 'frozen-list', 'frozen-map', 'nan-key', 'event-ids'):
                raise Unsupported()
            raise StoreIntegrityError('fresh reference has no complete backing')
        marker = kind, incarnation
        if marker in self.old_targets:
            return self.old_targets[marker]
        from .persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as SEQUENCE
        from .persistence_nonreflexive_keys import NAMESPACE as NAN
        if kind in ('list', 'map', 'set', 'frozen-list', 'frozen-map'):
            ns, key = HISTORY, incarnation
        elif kind in ('record', 'nan-key'):
            ns, key = (RECORDS if kind == 'record' else NAN), (incarnation, 0)
        elif kind == 'sequence':
            ns, key = SEQUENCE, incarnation
        else:
            raise Unsupported()
        old = self.old(ns, key)
        if old is None:
            raise StoreIntegrityError('reference lacks accepted backing descriptor')
        before = self.codec.decode(old.payload)
        world.target._validate_descriptor(kind, incarnation, before)
        if ns == HISTORY and before[0] != kind:
            raise StoreIntegrityError('old backing kind disagreement')
        mapping = world._map(self.store, b'backing-inventory')
        position = incarnation.to_bytes(8, 'big')
        expected = _digest(b'ate-world-backing/1', kind.encode(), ns.encode(), self.codec.encode(key),
                           world._structural_descriptor(self.codec, kind, old.payload))
        if mapping.get(self.request.facts[0], position) != expected:
            raise StoreIntegrityError('reference lacks accepted semantic backing')
        value = self.value(ns, key, metadata=True)
        after = _digest(b'ate-world-backing/1', kind.encode(), ns.encode(), self.codec.encode(key),
                        world._structural_descriptor(self.codec, kind, self.codec.encode(value)))
        if mapping.get((self.request.tail_facts or self.request.facts)[0], position) != after:
            raise Unsupported()
        self.old_targets[marker] = value
        if kind == 'record':
            cls, fields, _state = checked_record_header(value)
            world._check_field_values(self.store, None, cls, fields, self.header)
            adapter = world.AUXILIARY_OWNER_FAMILIES[RECORDS]
            for family in _families(cls):
                try:
                    world._check_field_values(self.store, family, cls, fields, self.header)
                except StoreIntegrityError:
                    raise Unsupported() from None
            for path, child in adapter.reference_placements(value):
                policies = {incoming_owner_policy(ns, path) for ns in _families(cls)} - {None}
                if policies:
                    child_kind, _inc = world.target._reference(adapter.resolve_path(value, path))
                    self._target(child_kind, child)
                    self._policy_counts(child_kind, child, policies)
        return value

    def _policy_counts(self, kind, incarnation, policies):
        for policy in policies:
            counts = self.value(TYPES, incarnation, metadata=True)
            if (type(counts) is not tuple or len(counts) != 3 or counts[:2] != (TAG, kind.removeprefix('frozen-'))
                    or type(counts[2]) is not tuple or len(counts[2]) != 3
                    or any(type(n) is not int or n < 0 for n in counts[2])
                    or counts[2][0 if policy == 'int' else 1] != sum(counts[2])):
                raise StoreIntegrityError('fresh reference violates incoming member policy')

    def check(self, change, projections):
        self.projections += len(projections)
        if self.projections > MAX_PROJECTIONS:
            raise Unsupported()
        for path, incarnation, kind, fingerprint in projections:
            if fingerprint is not None:
                continue
            self._target(kind, incarnation)
            policies = {incoming_owner_policy(change.namespace, path)} - {None}
            if change.namespace == RECORDS:
                cls = checked_record_header(change.value)[0]
                # Reuse registered consuming-family policies for backed records;
                # container annotations alone do not certify int member types.
                policies.update(incoming_owner_policy(ns, path) for ns in _families(cls))
                policies.discard(None)
            self._policy_counts(kind, incarnation, policies)
            if change.namespace in world.AUXILIARY_OWNER_FAMILIES and change.key[0] in self.backings:
                self.edges.add((change.key[0], incarnation))

    def guard_alias_work(self, incarnations):
        old = {i for i in incarnations if i < self.request.pairs[1][0].next_incarnation_id}
        count = sum(scope._resolve(self.store, self.request.pairs[1][0], scope.GroupScope(i)).count for i in old)
        if count > MAX_OLD_ALIASES:
            raise Unsupported()

    def facts(self, facts, child_root):
        OrderedSeekMap(self.store.db, b'').create_schema()
        degree = dict.fromkeys(self.backings, 0)
        outgoing = {i: set() for i in self.backings}
        for parent, child in self.edges:
            if child in self.backings:
                outgoing[parent].add(child)
                degree[child] += 1
        ready = [i for i, n in degree.items() if not n]
        visited = 0
        while ready:
            parent = ready.pop(); visited += 1
            for child in outgoing[parent]:
                degree[child] -= 1
                if not degree[child]: ready.append(child)
        if visited != len(self.backings):
            raise StoreIntegrityError('cyclic fresh backing forest')
        facts = list(facts)
        directory = scope._map(self.store, 4)
        for incarnation, (kind, namespace, key, value) in self.backings.items():
            position = incarnation.to_bytes(8, 'big')
            mapping = world._map(self.store, b'backing-inventory')
            if mapping.get(facts[0], position) is not None:
                raise StoreIntegrityError('fresh backing lacks accepted semantic absence')
            descriptor = self.codec.encode(value)
            facts[0] = mapping.set(facts[0], position, _digest(b'ate-world-backing/1', kind.encode(), namespace.encode(),
                self.codec.encode(key), world._structural_descriptor(self.codec, kind, descriptor)))
            if kind != 'record':
                mapping = world._map(self.store, b'backing-orders')
                if mapping.get(facts[4], position) is not None:
                    raise StoreIntegrityError('fresh backing has competing order authority')
                facts[4] = mapping.set(facts[4], position, _digest(b'ate-world-history-order/1', kind.encode(), descriptor))
            selected = scope.ChildScope(incarnation)
            if scope._resolve(self.store, self.request.pairs[1][0], selected).count:
                raise StoreIntegrityError('fresh backing has predecessor children')
            domain = scope._seek_domain(self.store, selected)
            seek = OrderedSeekMap(self.store.db, domain); root = seek.empty
            for item in self.children[incarnation]:
                _inc, where = scope._child_locator(item['namespace'], item['typed_key'])
                root = seek.set(root, where, scope._child_member(domain, where))
            child_root = directory.set(child_root, scope._scope_key(selected),
                scope._write_descriptor(self.store, selected, root) if root.count else None)
        return tuple(facts), child_root
