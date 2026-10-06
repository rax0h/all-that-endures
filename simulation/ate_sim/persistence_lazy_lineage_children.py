from __future__ import annotations

from collections import OrderedDict
from collections.abc import ItemsView, KeysView, ValuesView
import weakref

from .incremental_store import Membership, StoreError, StoreFormatError, StoreIntegrityError
from .persistence_lazy_store import (
    IdentityOccurrenceChange,
    VersionChange,
    _order_checksum,
    _query_checksum,
    _version_checksum,
)


LINEAGE_CHILD_NAMESPACE = "world.lineage.children"
LINEAGE_CHILD_EDGE_NAMESPACE = "aux.lazy.lineage.child_edges"
LAZY_LINEAGE_CHILD_SCHEMA = 1
LAZY_LINEAGE_CHILD_EDGE_SCHEMA = 1
CLEAN_GROUP_LIMIT = 256


def _valid_lineage_key(value):
    return (
        type(value) is tuple
        and len(value) == 2
        and type(value[0]) is str
        and type(value[1]) is int
    )


def insert_lineage_child_bucket(
    destination,
    *,
    generation,
    typed_key,
    ordinal,
    count,
):
    codec = destination.codec
    payload = codec.encode(count)
    memberships_blob = codec.encode(())
    payload_checksum = __import__(
        "ate_sim.incremental_store", fromlist=["_framed_sha"]
    )._framed_sha(b"lazy-payload-v1", payload)
    destination.db.execute(
        "INSERT INTO lazy_record_versions("
        "namespace,typed_key,valid_from,valid_to,payload,payload_checksum,"
        "codec_version,record_schema,memberships,row_checksum"
        ") VALUES (?,?,?,NULL,?,?,?,?,?,?)",
        (
            LINEAGE_CHILD_NAMESPACE,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            LAZY_LINEAGE_CHILD_SCHEMA,
            memberships_blob,
            _version_checksum(
                LINEAGE_CHILD_NAMESPACE,
                typed_key,
                LAZY_LINEAGE_CHILD_SCHEMA,
                codec.version,
                generation,
                None,
                memberships_blob,
                payload,
            ),
        ),
    )
    destination.db.execute(
        "INSERT INTO lazy_order_versions("
        "namespace,typed_key,ordinal,valid_from,valid_to,row_checksum"
        ") VALUES (?,?,?,?,NULL,?)",
        (
            LINEAGE_CHILD_NAMESPACE,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                LINEAGE_CHILD_NAMESPACE,
                typed_key,
                ordinal,
                generation,
                None,
            ),
        ),
    )


def insert_lineage_child_edge(
    destination,
    *,
    generation,
    parent,
    child,
    ordinal,
):
    codec = destination.codec
    edge_key = (parent, child)
    typed_key = codec.encode(edge_key)
    payload = codec.encode(True)
    memberships = (("parent", parent, ordinal),)
    memberships_blob = codec.encode(memberships)
    payload_checksum = __import__(
        "ate_sim.incremental_store", fromlist=["_framed_sha"]
    )._framed_sha(b"lazy-payload-v1", payload)
    destination.db.execute(
        "INSERT INTO lazy_record_versions("
        "namespace,typed_key,valid_from,valid_to,payload,payload_checksum,"
        "codec_version,record_schema,memberships,row_checksum"
        ") VALUES (?,?,?,NULL,?,?,?,?,?,?)",
        (
            LINEAGE_CHILD_EDGE_NAMESPACE,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            LAZY_LINEAGE_CHILD_EDGE_SCHEMA,
            memberships_blob,
            _version_checksum(
                LINEAGE_CHILD_EDGE_NAMESPACE,
                typed_key,
                LAZY_LINEAGE_CHILD_EDGE_SCHEMA,
                codec.version,
                generation,
                None,
                memberships_blob,
                payload,
            ),
        ),
    )
    destination.db.execute(
        "INSERT INTO lazy_order_versions("
        "namespace,typed_key,ordinal,valid_from,valid_to,row_checksum"
        ") VALUES (?,?,?,?,NULL,?)",
        (
            LINEAGE_CHILD_EDGE_NAMESPACE,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                LINEAGE_CHILD_EDGE_NAMESPACE,
                typed_key,
                ordinal,
                generation,
                None,
            ),
        ),
    )
    encoded_parent = codec.encode(parent)
    destination.db.execute(
        "INSERT INTO lazy_query_versions("
        "namespace,index_name,index_value,record_key,ordinal,"
        "valid_from,valid_to,row_checksum"
        ") VALUES (?,?,?,?,?,?,NULL,?)",
        (
            LINEAGE_CHILD_EDGE_NAMESPACE,
            "parent",
            encoded_parent,
            typed_key,
            ordinal,
            generation,
            _query_checksum(
                LINEAGE_CHILD_EDGE_NAMESPACE,
                "parent",
                encoded_parent,
                typed_key,
                ordinal,
                generation,
                None,
            ),
        ),
    )


class LazyLineageTrackedSet(set):
    @staticmethod
    def _validate(values):
        values = set(values)
        if any(not _valid_lineage_key(value) for value in values):
            raise TypeError("lineage children require (str,int) keys")
        return values

    def __init__(self, values, table, key):
        set.__init__(self, self._validate(values))
        self._table_ref = weakref.ref(table)
        self._key = key

    def _table(self):
        return None if self._table_ref is None else self._table_ref()

    def _guard(self):
        table = self._table()
        if table is not None:
            table._ensure_mutation()
        return table

    def _attach(self, table, key):
        self._table_ref = weakref.ref(table)
        self._key = key

    def _detach(self):
        self._table_ref = None
        self._key = None

    def add(self, value):
        self._validate((value,))
        table = self._guard()
        if value in self:
            return
        if table is not None:
            table._record_edge_add(self._key, value)
        set.add(self, value)

    def discard(self, value):
        table = self._guard()
        if value not in self:
            return
        if table is not None:
            table._record_edge_remove(self._key, value)
        set.discard(self, value)

    def remove(self, value):
        table = self._guard()
        if value not in self:
            raise KeyError(value)
        if table is not None:
            table._record_edge_remove(self._key, value)
        set.remove(self, value)

    def pop(self):
        table = self._guard()
        if not self:
            raise KeyError("pop from an empty set")
        value = next(iter(self))
        if table is not None:
            table._record_edge_remove(self._key, value)
        set.remove(self, value)
        return value

    def clear(self):
        table = self._guard()
        before = tuple(self)
        if table is not None:
            for value in before:
                table._record_edge_remove(self._key, value)
        set.clear(self)

    def update(self, *others):
        values = set()
        for other in others:
            values.update(other)
        for value in self._validate(values):
            self.add(value)

    def difference_update(self, *others):
        remove = set()
        for other in others:
            remove.update(other)
        for value in tuple(self.intersection(remove)):
            self.discard(value)

    def intersection_update(self, *others):
        keep = set(self)
        for other in others:
            keep.intersection_update(other)
        for value in tuple(self.difference(keep)):
            self.discard(value)

    def symmetric_difference_update(self, other):
        other = self._validate(other)
        before = set(self)
        for value in before.intersection(other):
            self.discard(value)
        for value in other.difference(before):
            self.add(value)

    def __ior__(self, other):
        self.update(other)
        return self

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def __ixor__(self, other):
        self.symmetric_difference_update(other)
        return self


class LazyLineageChildrenTable(dict):
    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = LINEAGE_CHILD_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = OrderedDict()
        self._loads = 0
        state = self._store._namespace_state_at(
            self._namespace, self._pin.captured_head
        )
        if state is None:
            self._baseline_count = 0
            self._next_overlay_ordinal = 0
        else:
            self._baseline_count = state[0]
            self._next_overlay_ordinal = state[1]
        edge_state = self._store._namespace_state_at(
            LINEAGE_CHILD_EDGE_NAMESPACE, self._pin.captured_head
        )
        self._edge_baseline_count = 0 if edge_state is None else edge_state[0]
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}
        self._count_overrides = {}
        self._edge_added = set()
        self._edge_removed = set()

    def _ensure(self):
        self._session._ensure_active()
        if self._session._state == "recovery-required":
            raise StoreError("lineage child reads blocked during recovery")

    def _ensure_mutation(self):
        self._session._ensure_people_mutation_allowed()

    def _baseline_exists(self, key):
        if key not in self._baseline_presence:
            self._baseline_presence[key] = self._store.contains_lazy_key(
                self._pin, self._namespace, key
            )
        return self._baseline_presence[key]

    def _persisted_ordinal(self, key):
        if key not in self._baseline_ordinal:
            typed = self._store.codec.encode(key)
            order = self._store._visible_order(
                self._namespace, typed, self._pin.captured_head
            )
            if order is None:
                raise KeyError(key)
            self._baseline_ordinal[key] = order[0]
        return self._baseline_ordinal[key]

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_LINEAGE_CHILD_SCHEMA,
            )
            if type(checked.value) is not int or checked.value < 0:
                raise StoreFormatError("invalid lineage child count")
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _baseline_incarnation_id(self, key):
        if key not in self._baseline_incarnation:
            try:
                checked = self._store.read_identity_occurrence(
                    self._pin, self._namespace, key, ()
                )
            except KeyError:
                self._baseline_incarnation[key] = None
            else:
                self._baseline_incarnation[key] = checked.incarnation_id
        return self._baseline_incarnation[key]

    def _visible(self, key):
        if key in self._new_keys or key in self._reinserted:
            return True
        if key in self._removed:
            return False
        return self._baseline_exists(key)

    def __len__(self):
        self._ensure()
        return self._baseline_count - len(self._removed) + len(self._new_keys)

    def __iter__(self):
        self._ensure()
        for key in self._store.iter_keys(self._pin, self._namespace):
            if key in self._removed or key in self._reinserted:
                continue
            yield key
        appended = [
            key for key in (self._new_keys | self._reinserted)
            if key not in self._removed
        ]
        appended.sort(key=lambda key: self._overlay_ordinals[key])
        yield from appended

    def __contains__(self, key):
        self._ensure()
        return self._visible(key)

    def keys(self):
        return KeysView(self)

    def items(self):
        return ItemsView(self)

    def values(self):
        return ValuesView(self)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def _current_ordinal(self, key):
        if key in self._overlay_ordinals and (
            key in self._new_keys or key in self._reinserted
        ):
            return self._overlay_ordinals[key]
        return self._persisted_ordinal(key)

    def _evict_clean(self):
        while len(self._lru) > self._clean_limit:
            key, _ = self._lru.popitem(last=False)
            if key in self._dirty:
                continue
            if dict.__contains__(self, key):
                dict.__delitem__(self, key)

    def _baseline_bucket_count(self, key):
        return int(self._store.codec.decode(self._baseline_bytes(key)))

    def _current_count(self, key):
        if key in self._count_overrides:
            return self._count_overrides[key]
        if dict.__contains__(self, key):
            return set.__len__(dict.__getitem__(self, key))
        return self._baseline_bucket_count(key)

    @staticmethod
    def _edge_key(parent, child):
        return (parent, child)

    def _edge_baseline_exists(self, parent, child):
        return self._store.contains_lazy_key(
            self._pin,
            LINEAGE_CHILD_EDGE_NAMESPACE,
            self._edge_key(parent, child),
        )

    def _edge_visible(self, parent, child):
        edge = self._edge_key(parent, child)
        if edge in self._edge_added:
            return True
        if edge in self._edge_removed:
            return False
        return self._edge_baseline_exists(parent, child)

    def _edge_keys(self, parent):
        rows = self._store.query_keys(
            self._pin,
            LINEAGE_CHILD_EDGE_NAMESPACE,
            "parent",
            parent,
        )
        children = set()
        for edge in rows:
            if (
                type(edge) is not tuple
                or len(edge) != 2
                or edge[0] != parent
                or not _valid_lineage_key(edge[1])
            ):
                raise StoreIntegrityError("invalid lineage child edge key")
            if edge not in self._edge_removed:
                children.add(edge[1])
        for edge in self._edge_added:
            if edge[0] == parent:
                children.add(edge[1])
        return children

    def _record_edge_add(self, parent, child):
        self._ensure_mutation()
        if not _valid_lineage_key(parent) or not _valid_lineage_key(child):
            raise TypeError("lineage edge requires (str,int) keys")
        edge = self._edge_key(parent, child)
        if edge in self._edge_added:
            return
        if edge in self._edge_removed:
            self._edge_removed.remove(edge)
        elif self._edge_baseline_exists(parent, child):
            return
        else:
            self._edge_added.add(edge)
        self._count_overrides[parent] = self._current_count(parent) + 1
        self._dirty.add(parent)
        self._lru.pop(parent, None)

    def _record_edge_remove(self, parent, child):
        self._ensure_mutation()
        edge = self._edge_key(parent, child)
        if edge in self._edge_removed:
            return
        if edge in self._edge_added:
            self._edge_added.remove(edge)
        elif not self._edge_baseline_exists(parent, child):
            return
        else:
            self._edge_removed.add(edge)
        self._count_overrides[parent] = self._current_count(parent) - 1
        self._dirty.add(parent)
        self._lru.pop(parent, None)

    def add_child(self, parent, child):
        self._ensure_mutation()
        if not _valid_lineage_key(parent) or not _valid_lineage_key(child):
            raise TypeError("lineage child edge requires (str,int) keys")
        if dict.__contains__(self, parent):
            dict.__getitem__(self, parent).add(child)
            return
        if not self._visible(parent):
            self[parent] = set()
            dict.__getitem__(self, parent).add(child)
            return
        if not self._edge_visible(parent, child):
            self._record_edge_add(parent, child)

    def __getitem__(self, key):
        self._ensure()
        if not self._visible(key):
            raise KeyError(key)
        if dict.__contains__(self, key):
            self._lru.pop(key, None)
            if key not in self._dirty:
                self._lru[key] = None
            return dict.__getitem__(self, key)
        checked = self._store.read_version(
            self._pin,
            self._namespace,
            key,
            expected_record_schema=LAZY_LINEAGE_CHILD_SCHEMA,
        )
        if type(checked.value) is not int or checked.value < 0:
            raise StoreFormatError("invalid lineage child bucket count")
        values = self._edge_keys(key)
        if len(values) != checked.value:
            raise StoreIntegrityError(
                "lineage child count disagrees with edge rows"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        bucket = self._session._bind_loaded_lineage_children(key, values)
        dict.__setitem__(self, key, bucket)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return bucket

    def __setitem__(self, key, values):
        self._ensure_mutation()
        if not _valid_lineage_key(key):
            raise TypeError("lineage parent key must be (str,int)")
        desired = LazyLineageTrackedSet._validate(values)
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = self[key] if currently_visible else None
        if old is values and currently_visible:
            return
        current = set() if old is None else set(old)
        if key not in self._count_overrides:
            self._count_overrides[key] = len(current)
        for child in current - desired:
            self._record_edge_remove(key, child)
        for child in desired - current:
            self._record_edge_add(key, child)
        if old is not None:
            self._session._detach_assigned_lineage_children(key, old)
        bucket = self._session._bind_assigned_lineage_children(key, desired)
        dict.__setitem__(self, key, bucket)
        was_removed = key in self._removed
        if baseline_exists:
            self._removed.discard(key)
            if was_removed:
                self._reinserted.add(key)
                self._overlay_ordinals[key] = self._next_overlay_ordinal
                self._next_overlay_ordinal += 1
        else:
            self._new_keys.add(key)
            if key not in self._overlay_ordinals:
                self._overlay_ordinals[key] = self._next_overlay_ordinal
                self._next_overlay_ordinal += 1
        self._count_overrides[key] = len(desired)
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        bucket = self[key]
        for child in tuple(bucket):
            self._record_edge_remove(key, child)
        self._session._detach_assigned_lineage_children(key, bucket)
        dict.__delitem__(self, key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._count_overrides.pop(key, None)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    def clear(self):
        for key in tuple(self):
            del self[key]

    def update(self, records=(), **kwargs):
        for key, value in dict(records, **kwargs).items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = set() if default is None else default
        return self[key]

    def pop(self, key, *default):
        if key not in self:
            if default:
                return default[0]
            raise KeyError(key)
        value = self[key]
        del self[key]
        return value

    def popitem(self):
        keys = tuple(self)
        if not keys:
            raise KeyError("popitem(): dictionary is empty")
        key = keys[-1]
        return key, self.pop(key)

    def _effective_touched(self):
        return (
            set(self._dirty)
            | set(self._removed)
            | set(self._new_keys)
            | set(self._reinserted)
        )

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=self._store.codec.encode,
        )
        version_changes = []
        identity_changes = []
        effective_keys = []
        structural_keys = []

        for key in touched:
            baseline_exists = self._baseline_exists(key)
            visible = self._visible(key)
            baseline_incarnation = (
                self._baseline_incarnation_id(key)
                if baseline_exists else None
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_LINEAGE_CHILD_SCHEMA,
                        )
                    )
                    identity_changes.append(
                        IdentityOccurrenceChange(
                            self._namespace, key, (), delete=True
                        )
                    )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue

            count = self._current_count(key)
            payload = self._store.codec.encode(count)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new or reinsertion or payload != self._baseline_bytes(key)
            )
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        count,
                        record_schema=LAZY_LINEAGE_CHILD_SCHEMA,
                        reinsertion=reinsertion,
                    )
                )

            current_incarnation = baseline_incarnation
            if dict.__contains__(self, key):
                incarnation = self._session._registry.incarnation_for_object(
                    dict.__getitem__(self, key)
                )
                if incarnation is None:
                    raise StoreIntegrityError(
                        "lineage child bucket lacks runtime incarnation"
                    )
                current_incarnation = incarnation.value
            if current_incarnation != baseline_incarnation:
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        (),
                        incarnation_id=current_incarnation,
                    )
                )
            if value_changed or current_incarnation != baseline_incarnation:
                effective_keys.append(key)
            if is_new or reinsertion:
                structural_keys.append(key)

        edge_changes = []
        for parent, child in sorted(
            self._edge_removed, key=self._store.codec.encode
        ):
            edge_changes.append(
                VersionChange(
                    LINEAGE_CHILD_EDGE_NAMESPACE,
                    (parent, child),
                    delete=True,
                    record_schema=LAZY_LINEAGE_CHILD_EDGE_SCHEMA,
                )
            )
        for parent, child in sorted(
            self._edge_added, key=self._store.codec.encode
        ):
            edge_changes.append(
                VersionChange(
                    LINEAGE_CHILD_EDGE_NAMESPACE,
                    (parent, child),
                    True,
                    record_schema=LAZY_LINEAGE_CHILD_EDGE_SCHEMA,
                    memberships=(Membership("parent", parent, 0),),
                )
            )

        return (
            tuple(version_changes),
            tuple(identity_changes),
            tuple(effective_keys),
            tuple(structural_keys),
            tuple(edge_changes),
        )

    def accept_save(self, plan, new_pin):
        self._pin = new_pin
        self._baseline_count = self._store.namespace_size(
            new_pin, self._namespace
        )
        edge_state = self._store._namespace_state_at(
            LINEAGE_CHILD_EDGE_NAMESPACE, new_pin.captured_head
        )
        self._edge_baseline_count = 0 if edge_state is None else edge_state[0]
        state = self._store._namespace_state_at(
            self._namespace, new_pin.captured_head
        )
        self._next_overlay_ordinal = 0 if state is None else state[1]
        for key in plan.lineage_child_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                count = self._current_count(key)
                self._baseline_payload[key] = self._store.codec.encode(count)
                if dict.__contains__(self, key):
                    incarnation = self._session._registry.incarnation_for_object(
                        dict.__getitem__(self, key)
                    )
                    self._baseline_incarnation[key] = (
                        None if incarnation is None else incarnation.value
                    )
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed lineage child bucket lost order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_incarnation[key] = None
                self._baseline_ordinal.pop(key, None)
        self._dirty.clear()
        self._removed.clear()
        self._new_keys.clear()
        self._reinserted.clear()
        self._overlay_ordinals.clear()
        self._count_overrides.clear()
        self._edge_added.clear()
        self._edge_removed.clear()
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        return {
            "logical_lineage_child_buckets": (
                self._baseline_count - len(self._removed) + len(self._new_keys)
            ),
            "logical_lineage_child_edges": (
                self._edge_baseline_count
                - len(self._edge_removed)
                + len(self._edge_added)
            ),
            "resident_lineage_child_buckets": dict.__len__(self),
            "lineage_child_bucket_payload_loads": self._loads,
            "dirty_lineage_child_buckets": len(self._dirty),
            "pending_lineage_child_edge_adds": len(self._edge_added),
            "pending_lineage_child_edge_removes": len(self._edge_removed),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
        }
