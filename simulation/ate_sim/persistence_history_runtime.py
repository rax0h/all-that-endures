"""Recursive values borrow the existing registry, physical catalog and publisher.

Only explicitly activated checked sessions select this runtime. Backing pages
contain compact references, never live child payload copies or a second DAG.
"""
from dataclasses import dataclass
from collections import deque
from contextlib import contextmanager
import sys
import weakref

from .incremental_store import StoreIntegrityError, StoreError, Membership
from .persistence_lazy_store import VersionChange
from .persistence_lazy_identity import IncarnationId, Occurrence
from .persistence_lazy_nested_history import (
    HISTORY_TYPES, HISTORY_CLASSES, reference, immutable_value,
    LazyHistoryList, LazyHistoryMap, LazyHistorySet, PAGE_NAMESPACE, ENTRY_NAMESPACE, PAGE_SIZE,
    history_storage_kind,
)
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_lazy_identity_catalog import OWNER_NAMESPACE
from .persistence_lazy_sequence import LazyOrderedSequence, NODE_NAMESPACE
from .persistence_record_headers import (
    RecordReference, record_reference, record_header, read_record_header,
    restore_record_header, NAMESPACE as RECORD_NAMESPACE,
)
from .persistence_event_id_reference import EventIdReference, event_id_reference
from .persistence_event_ids import EventIdSet
from .persistence_record_runtime import (
    mutable_record, record_backing, backing_for, canonical_for, RecordBacking, bind_record,
)
from .event_log import FrozenDict, FrozenList
from .persistence_nonreflexive_keys import (
    NonreflexiveKeyReference, NonreflexiveKeyBacking, nonreflexive_key_reference,
    nonreflexive_key_header, read_nonreflexive_key_header,
    restore_nonreflexive_key_header, project_immutable_key,
    NAMESPACE as NAN_NAMESPACE,
)


@dataclass(frozen=True)
class PhysicalHistoryOwner:
    runtime: object
    owner: tuple
    value: tuple


class RecursiveHistoryRuntime:
    def __init__(self, session):
        self._session_ref = weakref.ref(session)
        self._admitting = set()
        self._synchronizing = False
        self._source_leases = {}
        self._new_sources = []
        self._source_queue = deque()
        self._source_release_checks = 0
        self._new_nan_incarnations = []

    def remember_source(self, source, proxy):
        """Track only input D/U; the existing memo owns each actual source."""
        marker = id(source), proxy._incarnation
        if self._source_leases.get(marker[0]) != marker[1]:
            self._source_leases[marker[0]] = marker[1]
            self._new_sources.append(marker)

    def _release_source(self, marker):
        source_id, incarnation = marker
        if self._source_leases.get(source_id) != incarnation:
            return True
        tracker = self.session()._eager_tracker
        pair = tracker._memo.get(source_id)
        self._source_release_checks += 1
        if (pair is None or type(pair[1]) not in HISTORY_TYPES
                or pair[1]._incarnation != incarnation):
            self._source_leases.pop(source_id, None)
            return True
        # CPython: the memo tuple and this temporary getrefcount argument are
        # the only two references when no caller/container holds the source.
        # Keeping the actual source until this check prevents address reuse
        # from ever identifying another object as the original alias.
        if sys.getrefcount(pair[0]) != 2:
            return False
        if tracker._memo_reverse.get(id(pair[1])) == source_id:
            tracker._memo_reverse.pop(id(pair[1]), None)
        tracker._memo.pop(source_id)
        self._source_leases.pop(source_id)
        return True

    def accept_source_memos(self):
        # Parents were admitted last. Release them before their descendants;
        # this pass costs actual new input D, never a clean archive inventory.
        for marker in reversed(self._new_sources):
            if not self._release_source(marker):
                self._source_queue.append(marker)
        self._new_sources.clear()
        session = self.session()
        session._registry.release_nonreflexive_incarnations(self._new_nan_incarnations)
        self._new_nan_incarnations.clear()

    def collect_source_memos(self, budget=256):
        for _ in range(min(budget, len(self._source_queue))):
            marker = self._source_queue.popleft()
            if not self._release_source(marker):
                self._source_queue.append(marker)
        self.session()._registry.collect_nonreflexive_keys(budget=budget)

    def project_nan(self, value, *, allocate):
        session = self.session()
        incarnation = session._registry.incarnation_for_object(value)
        if incarnation is None:
            if not allocate:
                raise KeyError(value)
            incarnation = session._registry.bind_nonreflexive_key(value)
            root = session._registry.nonreflexive_root_for(value)
            root.backing = NonreflexiveKeyBacking(self, root, incarnation,
                nonreflexive_key_header(value), new=True)
            self._new_nan_incarnations.append(incarnation)
        else:
            backing = session._registry.nonreflexive_root_for(value).backing
            if backing._new and not backing._input_pending:
                backing._input_pending = True
                self._new_nan_incarnations.append(incarnation)
        session._register_nested_overlay(value)
        return NonreflexiveKeyReference(incarnation.value)

    def project_key(self, value, *, allocate=False, canonical=True):
        return project_immutable_key(value,
            lambda nan: self.project_nan(nan, allocate=allocate), canonical=canonical)

    def load_nan(self, ref):
        session = self.session()
        incarnation = IncarnationId(session.store.store_identity, ref.incarnation)
        current = session._registry.object_for_incarnation(incarnation)
        if current is not None:
            import math
            if (type(current) is not float or not math.isnan(current)
                    or type(self.backing_for(current)) is not NonreflexiveKeyBacking):
                raise StoreIntegrityError('native NaN reference has a different canonical type')
            return current
        header = read_nonreflexive_key_header(session.store, session.pin, ref.incarnation)
        value = restore_nonreflexive_key_header(header)
        session._registry.bind_nonreflexive_key(value, incarnation=incarnation)
        root = session._registry.nonreflexive_root_for(value)
        root.backing = NonreflexiveKeyBacking(self, root, incarnation, header, new=False)
        session._register_nested_overlay(value)
        return value

    def backing_for(self, value):
        return backing_for(value, self.session()._registry)

    def source_diagnostics(self):
        return {'source_memo_leases': len(self._source_leases),
                'new_source_memos': len(self._new_sources),
                'source_release_queue': len(self._source_queue),
                'source_release_checks': self._source_release_checks}

    def session(self):
        session = self._session_ref()
        if session is None:
            raise StoreError('recursive history session is closed')
        session._ensure_active()
        if session._state == 'recovery-required':
            raise StoreError('nested history read requires save acknowledgement')
        return session

    def initial_values(self, kind, value):
        self.validate_native(value)
        return self._initial_validated_values(kind, value)

    def copy_input(self, value):
        """Explicit full input staging; ordinary admission preserves its source.

        This creates new native objects and does not carry source incarnation
        assignments. The full store converter owns that separate checked mapping.
        """
        from .persistence_native_copy import copy_native_input
        session = self.session()
        session._begin_lifecycle_operation('copy-history-input')
        try:
            copied = copy_native_input(value, publisher=session)
            self.validate_native(copied)
            return copied
        finally:
            session._end_lifecycle_operation('copy-history-input')

    def validate_native_batch(self, values, validator=None, *, destination=None):
        """Check a finite operation's actual input once, before any allocation."""
        if type(values) not in (list, tuple):
            raise TypeError('recursive batch preflight requires finite builtin input')
        self.session()._ensure_people_mutation_allowed()
        completed = {}
        for value in values:
            self.validate_native(value, completed=completed)
        if validator is not None:
            for value in values:
                validator(value)
        self.check_reference_cycle(destination, values)

    def _admit_validated_batch(self, values):
        # Only finite, preflighted public operations use this builder. There is
        # no callback/yield or retained validation memo between check and build.
        return tuple(self._admit_validated(value) for value in values)

    def _initial_validated_values(self, kind, value):
        if kind in ('map', 'frozen-map'):
            return {key: self._admit_validated(child) for key, child in value.items()}
        if kind in ('list', 'sequence', 'frozen-list'):
            return [self._admit_validated(child) for child in value]
        return value

    def validate_native(self, value, active=None, completed=None):
        """Validate actual incoming D before allocating children or changing owners."""
        session = self.session()
        active = set() if active is None else active
        completed = {} if completed is None else completed
        if type(value) is EventIdSet:
            self.event_id_storage_reference(value)
            return
        if type(value) in HISTORY_TYPES:
            if value._store is not session.store or value._pin != session.pin:
                raise StoreError('cross-session recursive history')
            value._ensure()
            return
        if reference(value) or immutable_value(value):
            session.store.codec.encode(value)
            return
        is_record = mutable_record(value)
        if type(value) not in (list, dict, tuple, set, FrozenDict, FrozenList) and not is_record:
            raise TypeError('recursive history value is outside the typed container schema')
        if id(value) in active:
            raise TypeError('cyclic history value is outside the typed container schema')
        if completed.get(id(value)) is value:
            return
        active.add(id(value))
        try:
            if type(value) in (FrozenDict, FrozenList) and vars(value):
                raise TypeError('frozen snapshot has unclassified non-field state')
            if is_record:
                from .persistence_adapters import _check_record
                from .persistence_schema import RECORD_FIELDS
                from .persistence_tracking import _binding
                from .core import Event
                _check_record(value)
                if type(value) is Event and '_sealed' in vars(value) and type(vars(value)['_sealed']) is not bool:
                    raise TypeError('Event seal state must be a boolean')
                bound = _binding(value)
                if bound is not None and bound.session is not session._eager_tracker:
                    raise StoreError('cross-session recursive record')
                backing = record_backing(value)
                if backing is not None:
                    backing._ensure()
                for field in RECORD_FIELDS[type(value)]:
                    self.validate_native(getattr(value, field), active, completed)
            elif type(value) in (dict, FrozenDict):
                from .persistence_lazy_nested_history import equality_key
                for key, child in value.items():
                    session.store.codec.encode(equality_key(key))
                    self.validate_native(child, active, completed)
            elif type(value) is set:
                from .persistence_lazy_nested_history import equality_key
                for key in value:
                    session.store.codec.encode(equality_key(key))
            else:
                for child in value:
                    self.validate_native(child, active, completed)
            # Actual input objects live until this preflight returns; callback
            # collection/address reuse cannot make another source look checked.
            completed[id(value)] = value
        finally:
            active.remove(id(value))

    def admit(self, value, *, destination=None):
        session = self.session()
        session._ensure_people_mutation_allowed()
        self.validate_native(value)
        self.check_reference_cycle(destination, value)
        return self._admit_validated(value)

    def _admit_validated(self, value):
        """Build only the graph which the public entry preflight just checked.

        Exact builtin containers have no caller iteration callbacks. This path
        never consumes generators or keeps validation state across operations.
        """
        session = self.session()
        session._ensure_people_mutation_allowed()
        if type(value) is EventIdSet:
            return self.event_id_storage_reference(value, bind=True)
        if type(value) in HISTORY_TYPES:
            session._register_nested_overlay(value)
            self.bind(value)
            return value.storage_reference()
        if reference(value):
            return value
        if immutable_value(value):
            return self.project_key(value, allocate=True, canonical=False)
        if mutable_record(value):
            backing = record_backing(value)
            if backing is not None:
                session._register_nested_overlay(value)
                return backing.storage_reference()
            from .persistence_schema import RECORD_FIELDS
            fields = tuple(self._admit_validated(getattr(value, field))
                           for field in RECORD_FIELDS[type(value)])
            incarnation = session._registry.incarnation_for_object(value)
            if incarnation is None:
                incarnation = session._registry.bind(value)
            header = record_header(value, values=fields)
            backing = bind_record(self, value, incarnation, header, new=True)
            for field, child in zip(RECORD_FIELDS[type(value)], fields):
                object.__setattr__(value, field, self.admitted_value(child))
            session._register_nested_overlay(value)
            self.retain_pending_children(backing)
            return backing.storage_reference()
        if type(value) is tuple:
            return tuple(self._admit_validated(child) for child in value)
        if type(value) not in (list, dict, set, FrozenDict, FrozenList):
            raise TypeError('recursive history value is outside the typed container schema')
        tracker = session._eager_tracker
        memo = tracker._memo.get(id(value))
        if memo is not None and memo[0] is value and type(memo[1]) in HISTORY_TYPES:
            proxy = memo[1]
            session._register_nested_overlay(proxy)
            return proxy.storage_reference()
        if id(value) in self._admitting:
            raise TypeError('cyclic history value is outside the typed container schema')
        self._admitting.add(id(value))
        try:
            kind = {list: 'list', dict: 'map', set: 'set',
                    FrozenDict: 'frozen-map', FrozenList: 'frozen-list'}[type(value)]
            values = self._initial_validated_values(kind, value)
            incarnation = session._registry.allocator.allocate()
            proxy = HISTORY_CLASSES[kind](session.store, session.pin, incarnation.value,
                initial_values=values, cache_budget=session._history_cache_budget, recursive=True,
                **({'key_runtime': self} if kind in ('map', 'set', 'frozen-map') else {}),
                **({'reference_is_immutable': self.frozen_reference_is_immutable} if kind.startswith('frozen-') else {}))
            session._registry.bind(proxy, incarnation=incarnation)
            tracker._remember_memo(value, proxy)
            self.remember_source(value, proxy)
            session._register_nested_overlay(proxy)
            self.bind(proxy)
            return proxy.storage_reference()
        finally:
            self._admitting.remove(id(value))

    def admitted_value(self, value):
        """Resolve newly checked incoming D, before its placement is installed."""
        if reference(value) or record_reference(value) or event_id_reference(value) or nonreflexive_key_reference(value):
            session = self.session()
            result = session._registry.object_for_incarnation(
                IncarnationId(session.store.store_identity, value.incarnation))
            if result is None:
                raise StoreIntegrityError('admitted reference lost its canonical object')
            return result
        if type(value) is tuple:
            return tuple(self.admitted_value(child) for child in value)
        from .core import Ref
        if type(value) is Ref:
            return Ref(self.admitted_value(value.kind), self.admitted_value(value.id))
        if type(value) is frozenset:
            return frozenset(self.admitted_value(child) for child in value)
        return value

    def sealed_snapshot_authority(self, value):
        from .persistence_lazy_nested_history import HISTORY_CLASSES
        if type(value) is not HISTORY_CLASSES['frozen-map']:
            return False
        value._ensure()
        session = self.session()
        if value._store is not session.store or value._pin is not session.pin:
            raise StoreIntegrityError('sealed snapshot belongs to another publisher')
        return value._deep_immutable is True

    def frozen_reference_is_immutable(self, value):
        if nonreflexive_key_reference(value):
            child = self.load_nan(value)
            self.backing_for(child)  # Only checked immutable body metadata qualifies.
            return True
        if not reference(value) or value.kind not in ('frozen-list', 'frozen-map'):
            return False
        session = self.session()
        child = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, value.incarnation))
        if child is None or type(child) is not HISTORY_CLASSES[value.kind]:
            raise StoreIntegrityError('frozen certification lost its canonical child')
        child._ensure()
        if child._store is not session.store or child._pin != session.pin:
            raise StoreError('frozen certification has a different publisher lease')
        return child._deep_immutable

    def check_assignment_cycle(self, record, value):
        """Check the actual incoming native graph, never walk a clean history."""
        seen = set()
        def visit(child):
            if child is record:
                raise TypeError('cyclic record assignment is outside the typed schema')
            if id(child) in seen:
                return
            seen.add(id(child))
            if mutable_record(child):
                from .persistence_schema import RECORD_FIELDS
                for field in RECORD_FIELDS[type(child)]:
                    visit(getattr(child, field))
            elif type(child) in (list, tuple, FrozenList):
                for member in child:
                    visit(member)
            elif type(child) in (dict, FrozenDict):
                for member in child.values():
                    visit(member)
        visit(value)
        self.check_reference_cycle(record, value)

    def check_reference_cycle(self, destination, value):
        """Use the existing placement relation to reject ancestor references.

        Work follows actual incoming D and related parent placements. It does
        not read clean child payloads or maintain another graph/registry.
        """
        if destination is None:
            return
        session = self.session()
        destination_inc = session._registry.incarnation_for_object(destination)
        if destination_inc is None:
            return
        incoming, seen = set(), set()
        def visit(child):
            if id(child) in seen:
                return
            seen.add(id(child))
            if reference(child):
                incoming.add(child.incarnation)
            elif type(child) in HISTORY_TYPES:
                incoming.add(child._incarnation)
            elif mutable_record(child):
                from .persistence_schema import RECORD_FIELDS
                inc = session._registry.incarnation_for_object(child)
                if inc is not None:
                    incoming.add(inc.value)
                for field in RECORD_FIELDS[type(child)]:
                    visit(getattr(child, field))
            elif type(child) in (list, tuple, FrozenList):
                for member in child:
                    visit(member)
            elif type(child) in (dict, FrozenDict):
                for member in child.values():
                    visit(member)
        visit(value)
        if not incoming:
            return
        self.synchronize()
        coord = session._identity_coordinator
        pending, checked = deque((destination_inc.value,)), set()
        while pending:
            incarnation = pending.popleft()
            if incarnation in checked:
                continue
            if incarnation in incoming:
                raise TypeError('cyclic canonical reference is outside the typed schema')
            checked.add(incarnation)
            placements = coord._current_placements(coord.discover_group(incarnation))
            try:
                for namespace, key, _path in placements:
                    if namespace in AUXILIARY_OWNER_FAMILIES:
                        pending.append(key[0])
            finally:
                if hasattr(placements, 'close'):
                    placements.close()

    def invalidate_advancement_ancestors(self, value):
        """Invalidate cached ranks through the existing physical placement relation.

        Only an active, populated rank scope needs this work. Related parents
        are followed without loading clean child payloads or another owner map.
        """
        session = self.session()
        state = session.world.advancement
        if not state.__dict__.get('_rank_cache'):
            return
        incarnation = session._registry.incarnation_for_object(value)
        if incarnation is None:
            return
        coord = session._identity_coordinator
        pending, checked = deque((incarnation.value,)), set()
        while pending:
            current = pending.popleft()
            if current in checked:
                continue
            checked.add(current)
            placements = coord._current_placements(coord.discover_group(current))
            try:
                for namespace, key, _path in placements:
                    if namespace == 'world.advancement.paths':
                        state._invalidate_rank(key)
                    elif namespace in AUXILIARY_OWNER_FAMILIES:
                        pending.append(key[0])
            finally:
                if hasattr(placements, 'close'):
                    placements.close()

    def load_record(self, value):
        session = self.session()
        incarnation = IncarnationId(session.store.store_identity, value.incarnation)
        current = session._registry.object_for_incarnation(incarnation)
        if current is not None:
            backing = record_backing(current)
            if backing is not None and backing._incarnation != value.incarnation:
                raise StoreIntegrityError('record reference has a different canonical type')
            if backing is not None:
                backing._ensure()
                return current
        from .persistence_schema import RECORD_FIELDS
        header = read_record_header(session.store, session.pin, value.incarnation)
        if current is None:
            from .persistence_lazy_families import FAMILIES
            from .persistence_adapters import AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY
            # Only related checked family record roots are read. Reuse their
            # native body before recursive access creates another decoded copy.
            coord = session._identity_coordinator
            placements = coord._current_placements(coord.discover_group(value.incarnation, read_only=True))
            try:
                for namespace, key, path in placements:
                    packed = (namespace == AGENCY_ACTIONS_NAMESPACE and key == PACKED_LIST_KEY
                        and len(path) == 1 and path[0][0] == 'index')
                    if namespace not in FAMILIES or (path and not packed):
                        continue
                    table = session._family_bindings.tables.get(namespace)
                    if namespace == 'world.advancement.paths':
                        # A compact family root borrows this same checked body.
                        # Loading its table here would recursively request it.
                        root = session.store.read_version(session.pin, namespace, key,
                            expected_record_schema=1).value
                        if record_reference(root):
                            from .advancement import EssencePath
                            if root != value or type(restore_record_header(header)) is not EssencePath:
                                raise StoreIntegrityError('compact advancement root has a different record body')
                            continue
                    if packed:
                        candidate = session.world.agency.actions[path[0][1]]
                    else:
                        candidate = (table[key] if table is not None else session._eager_tracker._owner_value((namespace, key)))
                    if candidate is None or not mutable_record(candidate) or type(candidate) is not type(restore_record_header(header)):
                        raise StoreIntegrityError('record placement lacks its matching native family body')
                    if current is not None and current is not candidate:
                        raise StoreIntegrityError('record has distinct native family bodies')
                    current = candidate
            finally:
                if hasattr(placements, 'close'):
                    placements.close()
        result = restore_record_header(header) if current is None else current
        if current is not None:
            if not mutable_record(current) or type(current) is not type(restore_record_header(header)):
                raise StoreIntegrityError('record reference has a different canonical type')
            matched_atoms = []
            def compact(child, expected=None):
                if nonreflexive_key_reference(expected):
                    import math
                    if type(child) is not float or not math.isnan(child):
                        return child
                    checked = read_nonreflexive_key_header(session.store, session.pin, expected.incarnation)
                    if nonreflexive_key_header(child) != checked:
                        raise StoreIntegrityError('eager and backed native NaN bits disagree')
                    inc = session._registry.incarnation_for_object(child)
                    if inc is not None and inc.value != expected.incarnation:
                        raise StoreIntegrityError('eager native NaN has a different incarnation')
                    matched_atoms.append((child, expected, checked))
                    return expected
                if type(child) is EventIdSet:
                    return self.event_id_storage_reference(child)
                if type(child) in HISTORY_TYPES:
                    child._ensure()
                    return child.storage_reference()
                if mutable_record(child):
                    inc = session._registry.incarnation_for_object(child)
                    if inc is None:
                        raise StoreIntegrityError('eager record child lacks checked identity')
                    return RecordReference(inc.value)
                if type(child) is tuple:
                    values = expected if type(expected) is tuple and len(expected) == len(child) else (None,) * len(child)
                    return tuple(compact(member, counterpart) for member, counterpart in zip(child, values))
                return child
            projected = record_header(current, values=tuple(compact(getattr(current, field), expected)
                                      for field, expected in zip(RECORD_FIELDS[type(current)], header[2])))
            if session.store.codec.encode(projected) != session.store.codec.encode(header):
                raise StoreIntegrityError('eager and backed record payloads disagree')
            # Only after the entire native body agrees, retain its float aliases
            # in the sole conditional registry. Decode then reuses those atoms.
            for child, ref, checked in matched_atoms:
                inc = IncarnationId(session.store.store_identity, ref.incarnation)
                if session._registry.object_for_incarnation(inc) is None:
                    session._registry.bind_nonreflexive_key(child, incarnation=inc)
                    root = session._registry.nonreflexive_root_for(child)
                    root.backing = NonreflexiveKeyBacking(self, root, inc, checked, new=False)
                    session._register_nested_overlay(child)
        actual = session._registry.incarnation_for_object(result)
        if actual is not None and actual != incarnation:
            raise StoreIntegrityError('resident record has a different canonical incarnation')
        if actual is None:
            session._registry.bind(result, incarnation=incarnation)
        bind_record(self, result, incarnation, header, new=False)
        session._register_nested_overlay(result)
        owner = RECORD_NAMESPACE, (value.incarnation, 0)
        for field, child in zip(RECORD_FIELDS[type(result)], header[2]):
            object.__setattr__(result, field, self.decode(child, owner, (('field', field),)))
        return result

    def event_id_storage_reference(self, value, *, bind=False):
        """Read only the one checked root authority; never visit its members."""
        session = self.session()
        from .persistence_lazy_identity_headers import _IdentityHeaderCodec
        _IdentityHeaderCodec(session.store, session.pin)._check_event_authority(value)
        if value is not session.world.event_ids or value.descriptor() is None:
            raise StoreError('recursive Event-ID reference requires the current compact World authority')
        owner = ('world.event_ids', 0)
        coord = session._identity_coordinator
        rows = coord._owner_changes(owner, ())
        root = rows.get(coord._marker(owner, ()))
        if root is None or root[2] is None:
            raise StoreIntegrityError('Event-ID authority lacks its checked owner-zero incarnation')
        incarnation = IncarnationId(session.store.store_identity, root[2])
        coord.discover_group(incarnation, read_only=True)
        actual = session._registry.incarnation_for_object(value)
        if actual is not None and actual != incarnation:
            raise StoreIntegrityError('Event-ID facade has a different checked incarnation')
        if bind and actual is None:
            session._registry.bind(value, incarnation=incarnation)
        return EventIdReference(incarnation.value)

    def load_event_id_reference(self, value):
        session = self.session()
        facade = session.world.event_ids
        if self.event_id_storage_reference(facade, bind=True) != value:
            raise StoreIntegrityError('Event-ID graph reference disagrees with World authority')
        return facade

    def bind(self, proxy, *, before_mutation=None, after_change=None):
        session = self.session()
        # A component may also be exposed through another family. Rebinding
        # that alias must keep its facade's descriptor notification.
        if before_mutation is not None:
            proxy._recursive_before_mutation = before_mutation
        if after_change is not None:
            proxy._recursive_after_change = after_change
        before_mutation = getattr(proxy, '_recursive_before_mutation', None)
        after_change = getattr(proxy, '_recursive_after_change', None)
        proxy._recursive = True
        proxy._recursive_runtime = self
        if isinstance(proxy, (LazyHistoryMap, LazyHistorySet)):
            proxy._key_runtime = self
        self.retain_pending_children(proxy)
        def guard():
            if before_mutation is not None:
                before_mutation()
            session._shared_object_routes(proxy)
        def changed():
            self.retain_pending_children(proxy)
            session._shared_object_routes(proxy)
            self.invalidate_advancement_ancestors(proxy)
            incarnation = session._registry.incarnation_for_object(proxy)
            coord = session._identity_coordinator
            placements = coord._current_placements(coord.discover_group(incarnation))
            try:
                if placements:
                    session._nested_dirty[incarnation.value] = proxy
            finally:
                if hasattr(placements, 'close'):
                    placements.close()
            if after_change is not None:
                after_change()
        def read_guard():
            session._ensure_active()
            if session._state == 'recovery-required':
                raise StoreError('nested history read requires save acknowledgement')
        proxy.bind(guard, changed, read_guard)

    def retain_pending_children(self, proxy):
        """Private unpublished D keeps canonical descendants alive through U.

        These references are not placements or a second identity authority.
        Publication clears them; only unpublished dirty payload is traversed.
        """
        if not proxy._new:
            return
        session = self.session()
        children = {}
        for source in self._changes(proxy):
            if source.delete:
                continue
            for _path, inc in AUXILIARY_OWNER_FAMILIES[source.namespace].reference_placements(source.value):
                child = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
                if child is None:
                    raise StoreIntegrityError('unpublished child lost its canonical object')
                children[inc] = child
        proxy._recursive_pending_children = children

    def decode(self, value, owner, path):
        if reference(value) or record_reference(value) or event_id_reference(value) or nonreflexive_key_reference(value):
            session = self.session()
            parent = session._registry.object_for_incarnation(
                IncarnationId(session.store.store_identity, owner[1][0]))
            parent_backing = self.backing_for(parent) if parent is not None else None
            if parent_backing is not None and parent_backing._new:
                source = self._source_change(parent_backing, owner)
                child = getattr(parent_backing, '_recursive_pending_children', {}).get(value.incarnation)
                if source is not None and not source.delete and child is not None:
                    current = AUXILIARY_OWNER_FAMILIES[owner[0]].resolve_path(source.value, path)
                    if current != value or (reference(value) and history_storage_kind(self.backing_for(child)) != value.kind):
                        raise StoreIntegrityError('private recursive reference disagrees with its pending value')
                    return child
            if owner[0] == NODE_NAMESPACE:
                if (type(parent) is LazyOrderedSequence and parent._mutation_depth
                        and owner[1][1] in parent._recursive_preflight_leaves
                        and owner in parent._dirty):
                    # Caller iteration can read its native partial prefix.
                    # These leaves passed source/incoming preflight, but their
                    # physical routes cannot escape a rollback scope yet.
                    current = AUXILIARY_OWNER_FAMILIES[owner[0]].resolve_path(parent._dirty[owner], path)
                    child = session._registry.object_for_incarnation(
                        IncarnationId(session.store.store_identity, value.incarnation))
                    if child is None and event_id_reference(value):
                        child = self.load_event_id_reference(value)
                    elif child is None and nonreflexive_key_reference(value):
                        child = self.load_nan(value)
                    elif child is None and record_reference(value):
                        child = self.load_record(value)
                    elif child is None:
                        child = HISTORY_CLASSES[value.kind](session.store, session.pin, value.incarnation,
                            cache_budget=session._history_cache_budget, recursive=True)
                        session._registry.bind(child, incarnation=IncarnationId(session.store.store_identity, value.incarnation))
                        session._register_nested_overlay(child)
                        self.bind(child)
                    if current != value or (reference(value) and history_storage_kind(self.backing_for(child)) != value.kind):
                        raise StoreIntegrityError('pending recursive reference lacks its canonical child')
                    return child
            if session._lifecycle_operation is None:
                self.synchronize()
            coord = session._identity_coordinator
            rows = coord._owner_changes(owner, ())
            marker = coord._marker(owner, path)
            if marker not in rows or rows[marker][2] != value.incarnation:
                raise StoreIntegrityError('recursive reference lacks its checked physical placement')
            if nonreflexive_key_reference(value):
                coord.discover_group(value.incarnation, read_only=True)
                result = self.load_nan(value)
                session._registry.attach_occurrence(result, Occurrence(*owner, path))
                return result
            if event_id_reference(value):
                result = self.load_event_id_reference(value)
                session._registry.attach_occurrence(result, Occurrence(*owner, path))
                return result
            if record_reference(value):
                coord.discover_group(value.incarnation, read_only=True)
                result = self.load_record(value)
                session._registry.attach_occurrence(result, Occurrence(*owner, path))
                return result
            return session._bind_history_list(value, Occurrence(*owner, path),
                IncarnationId(session.store.store_identity, value.incarnation), kind=value.kind)
        if type(value) is tuple:
            return tuple(self.decode(child, owner, path + (('index', slot),)) for slot, child in enumerate(value))
        from .core import Ref
        if type(value) is Ref:
            return Ref(self.decode(value.kind, owner, path + (('field', 'kind'),)),
                       self.decode(value.id, owner, path + (('field', 'id'),)))
        if type(value) is frozenset:
            return frozenset(self.decode(child, owner, path + (('key', child),)) for child in value)
        return value

    def validate_physical_children(self, owner, value):
        """A touched bounded page checks all existing child groups before edits."""
        refs = AUXILIARY_OWNER_FAMILIES[owner[0]].reference_placements(value)
        if not refs:
            return
        # Counted operations synchronize their prior D in the entry guard.
        # Their in-progress leaves must not publish placement overlays before
        # the sequence's rollback scope has accepted the complete journal.
        if owner[0] != NODE_NAMESPACE:
            self.synchronize()
        session = self.session()
        coord = session._identity_coordinator
        rows = coord._owner_changes(owner, ())
        for path, inc in refs:
            marker = coord._marker(owner, path)
            if marker not in rows or rows[marker][2] != inc:
                raise StoreIntegrityError('recursive reference lacks its checked physical placement')
            coord.discover_group(inc)

    def _changes(self, proxy):
        if type(proxy) in (RecordBacking, NonreflexiveKeyBacking):
            yield from proxy.pending_changes()
            return
        if isinstance(proxy, LazyHistoryList):
            owners = ((PAGE_NAMESPACE, (proxy._incarnation, number)) for number in tuple(proxy._dirty_pages))
        elif isinstance(proxy, (LazyHistoryMap, LazyHistorySet)):
            owners = ((ENTRY_NAMESPACE, (proxy._incarnation, key))
                      for key in tuple(proxy._dirty_entries.keys() | proxy._cancelled_entries))
        elif type(proxy) is LazyOrderedSequence:
            owners = (owner for owner in tuple(proxy._dirty) if owner[0] == NODE_NAMESPACE)
        else:
            return
        for owner in owners:
            source = self._source_change(proxy, owner)
            if source is not None:
                yield source

    def _source_change(self, proxy, owner):
        """Resolve a requested pending physical key without visiting other D."""
        namespace, key = owner
        if key[0] != proxy._incarnation:
            raise StoreIntegrityError('physical history owner belongs to another backing')
        if type(proxy) is RecordBacking and namespace == RECORD_NAMESPACE and key[1] == 0:
            return VersionChange(namespace, key, proxy._header)
        if type(proxy) is NonreflexiveKeyBacking and namespace == NAN_NAMESPACE and key[1] == 0:
            return VersionChange(namespace, key, proxy._header)
        if isinstance(proxy, LazyHistoryList) and namespace == PAGE_NAMESPACE:
            number = key[1]
            if number not in proxy._dirty_pages:
                return None
            deleted = number * PAGE_SIZE >= proxy._length
            value = None if deleted else tuple(proxy._dirty_pages[number])
            return VersionChange(namespace, key, value, delete=deleted)
        if isinstance(proxy, (LazyHistoryMap, LazyHistorySet)) and namespace == ENTRY_NAMESPACE and (
                key[1] in proxy._dirty_entries or key[1] in proxy._cancelled_entries):
            entry = (proxy._dirty_entries[key[1]] if key[1] in proxy._dirty_entries
                     else proxy._baseline(key[1]))
            return VersionChange(namespace, key, entry, delete=entry is None,
                memberships=() if entry is None else (Membership('incarnation', proxy._incarnation, entry[0]),))
        if type(proxy) is LazyOrderedSequence and namespace == NODE_NAMESPACE and owner in proxy._dirty:
            value = proxy._dirty[owner]
            if value is None or value[0] == 'leaf':
                return VersionChange(namespace, key, value, delete=value is None)
        return None

    @contextmanager
    def prepared_routes(self):
        """The caller synchronized D; routing cannot change backing values."""
        if self._synchronizing:
            raise StoreError('recursive save routing is reentrant')
        self._synchronizing = True
        try:
            yield
        finally:
            self._synchronizing = False

    def retire_unpublished_pages(self, proxy):
        session = self.session()
        coord = session._identity_coordinator
        if not proxy._new:
            raise StoreIntegrityError('recursive promotion has a published append source')
        for number in tuple(proxy._dirty_pages):
            owner = PAGE_NAMESPACE, (proxy._incarnation, number)
            if owner in coord.dirty_owners or owner in coord._by_owner:
                coord.retire_owner(owner)
                # This physical source never published and is removed from D.
                # Its cancelled routes need no witness/header/tombstone.
                coord.dirty_owners.discard(owner)

    def retire_unowned_new_routes(self):
        """Cancel only actual unpublished D which lost its owning placement.

        Removing one private parent's routes can orphan its new children. The
        queue visits those outgoing D edges once; published backing retirement
        remains the existing bounded retirement participant's responsibility.
        """
        session = self.session()
        coord = session._identity_coordinator
        pending = deque(session._nested_dirty.values())
        retired = set()
        while pending:
            proxy = pending.popleft()
            inc = proxy._incarnation
            if not proxy._new or inc in retired:
                continue
            if (session._registry.occurrences_for_incarnation(
                    IncarnationId(session.store.store_identity, inc))
                    or session._nested_eager_owners(canonical_for(proxy))):
                continue
            retired.add(inc)
            for source in self._changes(proxy):
                owner = source.namespace, source.key
                if owner not in coord.dirty_owners and owner not in coord._by_owner:
                    continue
                rows = coord._owner_changes(owner, ())
                children = {child for _path, _original, child in rows.values() if child is not None}
                coord.retire_owner(owner)
                coord.dirty_owners.discard(owner)
                self.release_unowned_memos(children)
                for child in children:
                    backing = session._nested_dirty.get(child)
                    if backing is not None:
                        pending.append(backing)

    def release_unowned_memos(self, incarnations):
        session = self.session()
        coord = session._identity_coordinator
        for inc in set(incarnations):
            obj = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
            if obj is None:
                continue
            current = coord._current_placements(coord.discover_group(inc))
            try:
                if not current:
                    session._eager_tracker._drop_memo_if_unowned(obj)
                    backing = self.backing_for(obj)
                    if type(backing) is NonreflexiveKeyBacking and backing._new:
                        backing._input_pending = False
                        session._backing_dependencies.discard_unpublished_atom(inc)
                        session._nested_dirty.pop(inc, None)
            finally:
                if hasattr(current, 'close'):
                    current.close()

    def synchronize(self):
        if self._synchronizing:
            return
        session = self.session()
        # Synchronization only reflects already guarded values in D. Pinned
        # reads remain available in a stale session; public edits still guard.
        coord = session._identity_coordinator
        self._synchronizing = True
        try:
            pending = deque(session._nested_dirty.values())
            processed = set()
            while pending:
                proxy = pending.popleft()
                if proxy._incarnation in processed:
                    continue
                if proxy._new:
                    placements = session._registry.occurrences_for_incarnation(
                        IncarnationId(session.store.store_identity, proxy._incarnation))
                    if not any(o.owner_namespace not in AUXILIARY_OWNER_FAMILIES
                               or o.owner_key[0] in processed
                               or o.owner_key[0] not in session._nested_dirty for o in placements):
                        continue  # Unattached input D belongs only to private aliases.
                processed.add(proxy._incarnation)
                for source in self._changes(proxy):
                    owner = source.namespace, source.key
                    cancelled = (isinstance(proxy, (LazyHistoryMap, LazyHistorySet))
                                 and source.key[1] in proxy._cancelled_entries)
                    adapter = AUXILIARY_OWNER_FAMILIES[source.namespace]
                    refs = () if source.delete else adapter.reference_placements(source.value)
                    # Earlier scalar-only pages have no physical catalog owner.
                    # Do not manufacture their missing witness on ordinary use.
                    present = session.store._visible_record_row(session.pin.captured_head,
                        OWNER_NAMESPACE, session.store.codec.encode(owner))
                    source_present = session.store._visible_record_row(session.pin.captured_head,
                        source.namespace, session.store.codec.encode(source.key))
                    if source.delete and source_present is None:
                        # A read may have checked an addition which was then
                        # cancelled. Retire only this dirty physical owner;
                        # never publish a witness for its absent source.
                        before = coord._owner_changes(owner, ())
                        removed = {inc for _path, _original, inc in before.values() if inc is not None}
                        if removed:
                            coord.retire_owner(owner)
                            self.release_unowned_memos(removed)
                        coord.dirty_owners.discard(owner)
                        if isinstance(proxy, (LazyHistoryMap, LazyHistorySet)):
                            proxy._cancelled_entries.discard(source.key[1])
                        continue
                    if not refs and present is None and source_present is not None and owner not in coord.dirty_owners:
                        continue
                    before = coord._owner_changes(owner, ())
                    current = {path: inc for path, _, inc in before.values() if inc is not None}
                    for _path, inc in refs:
                        child = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
                        if child is not None and type(child) is not EventIdSet and self.backing_for(child)._new and inc not in processed:
                            session._register_nested_overlay(child)
                            pending.append(self.backing_for(child))
                    if current == dict(refs):
                        # New scalar-only pages also need an empty completeness
                        # witness, before a later edit introduces references.
                        if present is not None or source_present is None:
                            coord.dirty_owners.add(owner)
                        if cancelled:
                            proxy._cancelled_entries.discard(source.key[1])
                            if source_present is not None and not coord._by_owner.get(owner):
                                coord.dirty_owners.discard(owner)
                        continue
                    placements = []
                    for path, inc in refs:
                        child = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
                        if child is None:
                            ref = adapter.resolve_path(source.value, path)
                            if event_id_reference(ref):
                                child = self.load_event_id_reference(ref)
                            elif nonreflexive_key_reference(ref):
                                child = self.load_nan(ref)
                            elif record_reference(ref):
                                child = self.load_record(ref)
                            else:
                                child = HISTORY_CLASSES[ref.kind](session.store, session.pin, inc,
                                    cache_budget=session._history_cache_budget, recursive=True)
                                session._registry.bind(child, incarnation=IncarnationId(session.store.store_identity, inc))
                                session._register_nested_overlay(child)
                                self.bind(child)
                        placements.append((path, child))
                    coord.replace_owner(owner, placements)
                    self.release_unowned_memos(set(current.values()) - {inc for _path, inc in refs})
                    if cancelled:
                        proxy._cancelled_entries.discard(source.key[1])
                        if source_present is not None and not coord._by_owner.get(owner):
                            coord.dirty_owners.discard(owner)
        finally:
            self._synchronizing = False

    def load_owner(self, owner):
        session = self.session()
        proxy = session._nested_dirty.get(owner[1][0])
        source = self._source_change(proxy, owner) if proxy is not None else None
        if source is not None:
            if source.delete:
                raise StoreIntegrityError('recursive owner has a pending deletion')
            value = source.value
        else:
            value = session.store.read_version(session.pin, *owner, expected_record_schema=1).value
        return PhysicalHistoryOwner(self, owner, value)

    def resolve_path(self, physical, path):
        adapter = AUXILIARY_OWNER_FAMILIES[physical.owner[0]]
        value = adapter.resolve_path(physical.value, path)
        return self.decode(value, physical.owner, path)

    def install_path(self, owner, path, obj):
        session = self.session()
        physical = self.load_owner(owner)
        current = AUXILIARY_OWNER_FAMILIES[owner[0]].resolve_path(physical.value, path)
        incarnation = session._registry.incarnation_for_object(obj)
        if (not (reference(current) or record_reference(current) or event_id_reference(current) or nonreflexive_key_reference(current)) or incarnation is None
                or current.incarnation != incarnation.value
                or (reference(current) and current.kind != history_storage_kind(self.backing_for(obj)))
                or (nonreflexive_key_reference(current) and type(self.backing_for(obj)) is not NonreflexiveKeyBacking)
                or (record_reference(current) and record_backing(obj) is None)
                or (event_id_reference(current) and obj is not session.world.event_ids)
                or session._registry.object_for_incarnation(incarnation) is not obj):
            raise StoreIntegrityError('recursive reference resolves to a different canonical object')

    def unchanged_header(self, owner):
        session = self.session()
        value = self.load_owner(owner).value
        adapter = AUXILIARY_OWNER_FAMILIES[owner[0]]
        members = (Membership('incarnation', owner[1][0], value[0]),) if adapter.owner_kind == 'entry' else ()
        return VersionChange(*owner, value, memberships=members)
