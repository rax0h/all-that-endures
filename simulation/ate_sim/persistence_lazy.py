"""Opt-in P4 lazy World conversion and people pilot.

P3B remains unchanged.  This module adds an explicit cold->P4 conversion and
an initial read/query lazy session whose world.people collection is backed by
LazyRecordStore.  Save/lifecycle mutation is intentionally enabled in a later
slice after the open/query proof gate.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import ItemsView, KeysView, ValuesView
from dataclasses import dataclass, is_dataclass, replace
import os
from pathlib import Path
import tempfile
import uuid
import weakref
from typing import Any, Iterator

from .core import Person, World
from .event_log import EventLog, FrozenDict, FrozenList
from .incremental_store import (
    Membership,
    RecordChange,
    StoreConflictError,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from .persistence_adapters import (
    COLLECTION_LAYOUT,
    META,
    RECORD_SCHEMA,
    ROOT_FIELDS,
    ROOT_TYPES,
    SCHEMA,
    WorldCodec,
    _at_path,
    _read_current_identity_links,
    _restore_collection,
    _restore_identity,
    _roots,
)
from .persistence_cold_save import (
    _capture_successor,
    _change_evidence,
    _counts_tuple,
    prepare_cold_save,
    publish_cold_save,
)
from .persistence_events import SealedEventPrefix
from .persistence_identity import (
    IdentityOccurrenceIndex,
    iter_mutable_event_owners,
)
from .persistence_lazy_identity import (
    IncarnationId,
    LazyIdentityRegistry,
    Occurrence,
)
from .persistence_lazy_store import (
    GenerationPressureError,
    IdentityOccurrenceChange,
    LazyRecordStore,
    VersionChange,
    _identity_occurrence_checksum,
    _identity_state_checksum,
    _namespace_checksum,
    _order_checksum,
    _query_checksum,
    _version_checksum,
)
from .record_index import IndexedRecord, RecordTable
from .persistence_session import (
    COLD_EVENT_KIND,
    COLD_EVENT_STORAGE,
    COMMIT_DESCRIPTOR_KEY,
    EVENT_STORAGE,
    SESSION_DESCRIPTOR_SCHEMA,
    _capture_cold_baseline_ordinals,
    _capture_cold_world,
    _preflight_conversion_paths,
    _publish_private_cold_file,
    _read_event_descriptors,
    _read_suffix,
    _validate_head_inventory,
)
from .persistence_tracking import IncrementalWorldSession


PEOPLE_NAMESPACE = "world.people"
LAZY_PERSON_SCHEMA = 1
CLEAN_GROUP_LIMIT = 256


def _base_kind(kind: str) -> str:
    return {
        "dict-stable/v1": "dict",
        "RecordTable-stable/v1": "RecordTable",
        "set-stable/v1": "set",
        "EventLog-disk/v1": "EventLog",
    }.get(kind, kind)


def _namespace_path(namespace: str) -> tuple[tuple[str, Any], ...]:
    parts = namespace.split(".")
    if not parts or parts[0] != "world":
        raise StoreFormatError(f"invalid World namespace: {namespace}")
    return tuple(("field", part) for part in parts[1:])


def _owner_path(manifest, owner) -> tuple[tuple[str, Any], ...]:
    namespace, key = owner
    base = _namespace_path(namespace)
    description = manifest["collections"].get(namespace)
    if type(description) is not tuple or len(description) != 3:
        raise StoreFormatError(f"missing collection description: {namespace}")
    kind = _base_kind(description[0])
    if kind in ("dict", "RecordTable"):
        return base + (("key", key),)
    if kind in ("list", "EventLog", "set"):
        return base + (("index", key),)
    return base


def _iter_identity_owners(world, manifest):
    for root, obj in _roots(world):
        for name, expected in ROOT_FIELDS[root].items():
            if expected in ("state", "int"):
                continue
            namespace = root + "." + name
            value = getattr(obj, name)
            if expected == "dict":
                for key, child in value.items():
                    owner = (namespace, key)
                    yield owner, child, _owner_path(manifest, owner)
            elif expected == "events":
                if isinstance(value, EventLog) and value._disk_prefix is not None:
                    yield from iter_mutable_event_owners(value)
                else:
                    for index, child in enumerate(value):
                        owner = (namespace, index)
                        yield owner, child, _owner_path(manifest, owner)
            elif expected == "list":
                for index, child in enumerate(value):
                    owner = (namespace, index)
                    yield owner, child, _owner_path(manifest, owner)
            elif expected == "set":
                continue


def _identity_labels(world, manifest, links, codec):
    owners = list(_iter_identity_owners(world, manifest))
    index = IdentityOccurrenceIndex(
        codec, __import__("ate_sim.persistence_schema", fromlist=["RECORD_FIELDS"]).RECORD_FIELDS,
        mutable_event_tail_only=True,
    )
    index.bootstrap(owners)
    index.seed_explicit_links(list(links))

    # P2C links must be the complete sharing authority: every multiply occurring
    # mutable identity must project to the same canonical links.
    for ident, entry in index.occurrences.items():
        expected = {
            codec.encode(link): link
            for link in index._links_for(entry[1])
        }
        actual = {
            codec.encode(link): link
            for link in index.links_by_ident.get(ident, ())
        }
        if set(expected) != set(actual):
            raise StoreIntegrityError(
                "P2C identity links disagree with current mutable sharing"
            )

    anchors = []
    for ident, (_obj, paths) in index.occurrences.items():
        anchor = min((codec.encode(path), path) for path in paths)
        anchors.append((anchor[0], ident))
    anchors.sort()
    incarnation_for_ident = {
        ident: number for number, (_anchor, ident) in enumerate(anchors, 1)
    }

    owner_paths = {owner: path for owner, _value, path in owners}
    rows = []
    for owner, occurrences in index.owner_occurrences.items():
        namespace, key = owner
        prefix = owner_paths[owner]
        for ident, _obj, path in occurrences:
            if path[: len(prefix)] != prefix:
                raise StoreIntegrityError(
                    "identity occurrence escaped persistence owner"
                )
            rows.append(
                (
                    namespace,
                    key,
                    path[len(prefix):],
                    incarnation_for_ident[ident],
                )
            )
    rows.sort(key=lambda row: codec.encode(row[:3]))
    return rows, len(incarnation_for_ident) + 1


def _insert_lazy_person(
    destination: LazyRecordStore,
    *,
    generation: int,
    typed_key: bytes,
    key: Any,
    ordinal: int,
    person: Person,
) -> None:
    codec = destination.codec
    payload = codec.encode(person)
    memberships = (("alive", bool(person.alive), ordinal),)
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
            PEOPLE_NAMESPACE,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            LAZY_PERSON_SCHEMA,
            memberships_blob,
            _version_checksum(
                PEOPLE_NAMESPACE,
                typed_key,
                LAZY_PERSON_SCHEMA,
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
            PEOPLE_NAMESPACE,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                PEOPLE_NAMESPACE, typed_key, ordinal, generation, None
            ),
        ),
    )
    encoded_alive = codec.encode(bool(person.alive))
    destination.db.execute(
        "INSERT INTO lazy_query_versions("
        "namespace,index_name,index_value,record_key,ordinal,"
        "valid_from,valid_to,row_checksum"
        ") VALUES (?,?,?,?,?,?,NULL,?)",
        (
            PEOPLE_NAMESPACE,
            "alive",
            encoded_alive,
            typed_key,
            ordinal,
            generation,
            _query_checksum(
                PEOPLE_NAMESPACE,
                "alive",
                encoded_alive,
                typed_key,
                ordinal,
                generation,
                None,
            ),
        ),
    )


def convert_cold_to_lazy(source, destination, *, rules_id):
    """Explicit checked P3B cold -> P4 conversion into a new destination."""
    source, destination = _preflight_conversion_paths(source, destination)
    codec = WorldCodec(identity_links_recorded=True)
    source_store = TransactionalStore.open(
        source,
        codec=codec,
        expected_simulation_schema=SCHEMA,
        expected_rules_id=rules_id,
    )
    capture = None
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with source_store.read_transaction():
            source_store.verify_all()
            raw_manifest = source_store.read_record(
                META, "manifest", expected_record_schema=RECORD_SCHEMA
            )
            if (
                type(raw_manifest) is not dict
                or raw_manifest.get("event_storage") != COLD_EVENT_STORAGE
            ):
                raise StoreFormatError(
                    "convert_cold_to_lazy requires P3B cold event storage"
                )
            capture = _capture_cold_world(source_store)
            source_head = source_store.db.execute(
                "SELECT generation,parent_generation,simulation_position,seed,"
                "next_ids,namespace_inventory,namespace_counts,head_checksum "
                "FROM save_head WHERE singleton=1"
            ).fetchone()
            if source_head is None:
                raise StoreIntegrityError("missing source save head")
            generation = int(source_head[0])
            identity_rows, next_incarnation = _identity_labels(
                capture.world,
                capture.manifest,
                capture.identity_links,
                codec,
            )

            with tempfile.TemporaryDirectory(
                prefix=".ate-p4-convert-", dir=destination.parent
            ) as directory:
                private_path = Path(directory) / "lazy.sqlite"
                target = LazyRecordStore.create(
                    private_path,
                    codec=codec,
                    simulation_schema=SCHEMA,
                    rules_id=rules_id,
                )
                try:
                    target.db.execute("BEGIN IMMEDIATE")
                    target.db.execute("DELETE FROM save_head")
                    target.db.execute(
                        "INSERT INTO save_head VALUES (1,?,?,?,?,?,?,?,?)",
                        source_head,
                    )

                    people_count = 0
                    next_ordinal = 0
                    for row in source_store.db.execute(
                        "SELECT namespace,typed_key,payload,payload_checksum,"
                        "codec_version,record_schema,last_changed_generation "
                        "FROM records"
                    ):
                        (
                            namespace,
                            typed_key,
                            payload,
                            checksum,
                            codec_version,
                            record_schema,
                            changed_generation,
                        ) = row
                        if namespace != PEOPLE_NAMESPACE:
                            target.db.execute(
                                "INSERT INTO records VALUES (?,?,?,?,?,?,?)",
                                row,
                            )
                            continue
                        key = codec.decode(typed_key)
                        envelope = codec.decode(payload)
                        if (
                            type(envelope) is not tuple
                            or len(envelope) != 2
                            or type(envelope[0]) is not int
                            or envelope[0] < 0
                            or not isinstance(envelope[1], Person)
                        ):
                            raise StoreFormatError(
                                "invalid world.people source envelope"
                            )
                        ordinal, person = envelope
                        _insert_lazy_person(
                            target,
                            generation=generation,
                            typed_key=typed_key,
                            key=key,
                            ordinal=ordinal,
                            person=person,
                        )
                        people_count += 1
                        next_ordinal = max(next_ordinal, ordinal + 1)

                    for row in source_store.db.execute(
                        "SELECT namespace,index_name,index_value,record_key,"
                        "ordinal,generation FROM query_membership"
                    ):
                        if row[0] != PEOPLE_NAMESPACE:
                            target.db.execute(
                                "INSERT INTO query_membership VALUES (?,?,?,?,?,?)",
                                row,
                            )

                    # Stream immutable history row-by-row.  No EventLog segment
                    # payload collection is accumulated in Python memory.
                    for row in source_store.db.execute(
                        "SELECT namespace,ordinal,payload,payload_checksum,"
                        "codec_version,element_count,first_id,last_id,"
                        "created_generation FROM segments ORDER BY namespace,ordinal"
                    ):
                        target.db.execute(
                            "INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?)",
                            row,
                        )

                    target.db.execute(
                        "INSERT INTO lazy_namespace_state("
                        "namespace,valid_from,valid_to,member_count,"
                        "next_ordinal,row_checksum"
                        ") VALUES (?,?,NULL,?,?,?)",
                        (
                            PEOPLE_NAMESPACE,
                            generation,
                            people_count,
                            next_ordinal,
                            _namespace_checksum(
                                PEOPLE_NAMESPACE,
                                people_count,
                                next_ordinal,
                                generation,
                                None,
                            ),
                        ),
                    )

                    target.db.execute("DELETE FROM lazy_identity_state")
                    for namespace, key, path, incarnation_id in identity_rows:
                        encoded_key = codec.encode(key)
                        encoded_path = codec.encode(path)
                        target.db.execute(
                            "INSERT INTO lazy_identity_occurrence_versions("
                            "owner_namespace,owner_key,occurrence_path,"
                            "incarnation_id,valid_from,valid_to,row_checksum"
                            ") VALUES (?,?,?,?,?,NULL,?)",
                            (
                                namespace,
                                encoded_key,
                                encoded_path,
                                incarnation_id,
                                generation,
                                _identity_occurrence_checksum(
                                    namespace,
                                    encoded_key,
                                    encoded_path,
                                    incarnation_id,
                                    generation,
                                    None,
                                ),
                            ),
                        )
                    target.db.execute(
                        "INSERT INTO lazy_identity_state("
                        "valid_from,valid_to,next_incarnation_id,row_checksum"
                        ") VALUES (?,NULL,?,?)",
                        (
                            generation,
                            next_incarnation,
                            _identity_state_checksum(
                                next_incarnation, generation, None
                            ),
                        ),
                    )
                    target.db.commit()
                    target.verify_all()
                    target.close()
                    target = None
                    _publish_private_cold_file(private_path, destination)
                finally:
                    if target is not None:
                        target.close()

        with LazyRecordStore.open(
            destination,
            codec=codec,
            expected_simulation_schema=SCHEMA,
            expected_rules_id=rules_id,
        ) as check:
            summary = check.verify_all()
            return {
                "source_format": "p3b-cold/current-links",
                "destination_format": 3,
                "generation": summary["generation"],
                "people": people_count,
                "identity_occurrences": summary["identity_occurrences"],
                "next_incarnation_id": summary["next_incarnation_id"],
                "source_preserved": True,
            }
    finally:
        if capture is not None:
            capture.prefix.close()
        source_store.close()


def _path_under_people(path) -> bool:
    return bool(path) and path[0] == ("field", "people")


def _relative_get(root, path):
    value = root
    for kind, key in path:
        if kind == "field":
            value = getattr(value, key)
        elif kind == "key":
            value = value[key]
        elif kind == "index":
            value = value[key]
        else:
            raise StoreFormatError("unsupported identity path component")
    return value


def _relative_set(root, path, value):
    if not path:
        return value
    parent = _relative_get(root, path[:-1])
    kind, key = path[-1]
    if kind == "field":
        if is_dataclass(parent):
            object.__setattr__(parent, key, value)
        else:
            setattr(parent, key, value)
    elif kind == "key":
        dict.__setitem__(parent, key, value)
    elif kind == "index":
        list.__setitem__(parent, key, value)
    else:
        raise StoreFormatError("unsupported identity path component")
    return root



def _people_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 2
        and path[0] == ("field", "people")
        and type(path[1]) is tuple
        and len(path[1]) == 2
        and path[1][0] == "key"
    ):
        return path[1][1], tuple(path[2:])
    return None


def _seed_cross_boundary_people_identity(session, links):
    cross = []
    generation = session.pin.captured_head
    for target, owner in links:
        target_people = _people_occurrence_from_path(target)
        owner_people = _people_occurrence_from_path(owner)
        if (target_people is None) == (owner_people is None):
            continue
        people_key, relative = (
            target_people if target_people is not None else owner_people
        )
        eager_path = owner if target_people is not None else target
        encoded_key = session.store.codec.encode(people_key)
        encoded_path = session.store.codec.encode(relative)
        row = session.store._visible_identity_occurrence(
            generation,
            PEOPLE_NAMESPACE,
            encoded_key,
            encoded_path,
        )
        if row is None:
            raise StoreIntegrityError(
                "cross-boundary people identity lacks incarnation label"
            )
        eager_object = _at_path(
            session.world,
            eager_path,
            mutable_event_tail_only=True,
        )
        if not isinstance(eager_object, Person):
            raise StoreIntegrityError(
                "cross-boundary people identity does not resolve to Person"
            )
        incarnation = IncarnationId(
            session.store.store_identity, int(row[0])
        )
        live = session._registry.object_for_incarnation(incarnation)
        if live is not None and live is not eager_object:
            raise StoreIntegrityError(
                "cross-boundary incarnation has two live objects"
            )
        if live is None:
            session._registry.bind(
                eager_object, incarnation=incarnation
            )
        session._registry.attach_existing(
            incarnation,
            Occurrence(
                PEOPLE_NAMESPACE,
                people_key,
                relative,
            ),
        )
        cross.append((target, owner))
    return tuple(cross)


def _initialize_eager_tracker(
    session,
    *,
    baseline_ordinals,
    resident_links,
    prefix_descriptor,
    tail_descriptor,
    commit_descriptor,
):
    tracker = IncrementalWorldSession.__new__(IncrementalWorldSession)
    tracker._initialize_runtime(
        session.world,
        session.store,
        codec=session.store.codec,
        cold_mode=True,
    )
    tracker._excluded_namespaces = {PEOPLE_NAMESPACE}
    tracker._external_mutation_guard = session._ensure_hybrid_mutation_allowed
    try:
        tracker.generation = session.pin.captured_head
        tracker._manifest = session.manifest
        tracker._identity_mode = "current"
        tracker._initial_links = list(resident_links)
        tracker._committed_identity_targets = dict(tracker._initial_links)
        tracker._live_identity_targets = dict(tracker._initial_links)
        tracker._baseline_ordinals = {
            namespace: dict(ordinals)
            for namespace, ordinals in baseline_ordinals.items()
        }
        tracker._cold_head = session._head
        tracker._cold_prefix_descriptor = prefix_descriptor
        tracker._cold_tail_descriptor = tail_descriptor
        tracker._cold_commit_descriptor = commit_descriptor
        tracker._cold_committed_n = tail_descriptor.total_events
        tracker._normalize_bootstrap()
        tracker._bind_roots()
        tracker._bootstrap_identity_index()
        tracker._initialize_cold_persisted_keys()
    except Exception:
        try:
            tracker._undo_bound_roots()
            tracker._undo_bootstrap()
        finally:
            tracker._clear_bindings()
            tracker._active = False
        raise
    finally:
        tracker._suspended = 0
    return tracker

@dataclass(frozen=True)
class LazyPeopleSavePlan:
    token: str
    target_generation: int
    version_changes: tuple[VersionChange, ...]
    identity_changes: tuple[IdentityOccurrenceChange, ...]
    cold_plan: Any
    touched_keys: tuple[Any, ...]
    structural_keys: tuple[Any, ...]
    layout_value: dict[str, Any] | None


class LazyRecordTable(RecordTable):
    """RecordTable-compatible lazy people authority with a bounded clean cache."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = PEOPLE_NAMESPACE
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
        self._baseline_presence: dict[Any, bool] = {}
        self._baseline_payload: dict[Any, bytes] = {}
        self._baseline_incarnation: dict[Any, int | None] = {}
        self._baseline_ordinal: dict[Any, int] = {}
        self._dirty: set[Any] = set()
        self._removed: set[Any] = set()
        self._new_keys: set[Any] = set()
        self._reinserted: set[Any] = set()
        self._overlay_ordinals: dict[Any, int] = {}

    def _ensure(self):
        self._session._ensure_active()
        if self._session._state == "recovery-required":
            raise StoreError(
                "lazy people reads are blocked until save acknowledgement resolves"
            )

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
            typed_key = self._store.codec.encode(key)
            order = self._store._visible_order(
                self._namespace, typed_key, self._pin.captured_head
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
                expected_record_schema=LAZY_PERSON_SCHEMA,
            )
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
        return (
            self._baseline_count
            - len(self._removed)
            + len(self._new_keys)
        )

    def __iter__(self) -> Iterator[Any]:
        self._ensure()
        for key in self._store.iter_keys(self._pin, self._namespace):
            if key in self._removed or key in self._reinserted:
                continue
            yield key
        appended = [
            key
            for key in (self._new_keys | self._reinserted)
            if key not in self._removed
        ]
        appended.sort(key=lambda key: self._overlay_ordinals[key])
        yield from appended

    def __contains__(self, key):
        self._ensure()
        return self._visible(key)

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
            expected_record_schema=LAZY_PERSON_SCHEMA,
        )
        if not isinstance(checked.value, Person):
            raise StoreFormatError("lazy world.people payload is not Person")
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._session._bind_loaded_person(key, checked.value)
        dict.__setitem__(self, key, record)
        if isinstance(record, IndexedRecord):
            object.__setattr__(record, "_index_table", weakref.ref(self))
            object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def _evict_clean(self):
        while len(self._lru) > self._clean_limit:
            key, _ = self._lru.popitem(last=False)
            if key in self._dirty:
                continue
            if dict.__contains__(self, key):
                dict.__delitem__(self, key)

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

    def ids(self, fields, *values):
        self._ensure()
        fields = (fields,) if isinstance(fields, str) else tuple(fields)
        if fields != ("alive",) or len(values) != 1:
            raise StoreError(
                "people pilot currently supports only indexed alive queries"
            )
        desired = values[0]
        baseline = set(
            self._store.query_keys(
                self._pin, self._namespace, "alive", desired
            )
        )
        touched = self._dirty | self._new_keys | self._reinserted | self._removed
        baseline.difference_update(touched)
        for key in touched:
            if not self._visible(key):
                continue
            record = dict.__getitem__(self, key)
            if bool(record.alive) == desired:
                baseline.add(key)
        return tuple(sorted(baseline, key=self._current_ordinal))

    def select(self, fields, *values):
        return [self[key] for key in self.ids(fields, *values)]

    def buckets(self, fields):
        self._ensure()
        fields = (fields,) if isinstance(fields, str) else tuple(fields)
        if fields != ("alive",):
            raise StoreError(
                "people pilot currently supports only indexed alive queries"
            )
        return {
            (False,): set(self.ids(fields, False)),
            (True,): set(self.ids(fields, True)),
        }

    def preflight_change(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy Person"
            )

    def changed(self, key, field=None):
        if key in self.__dict__.get("_loading_keys", ()):
            return
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy Person"
            )
        if not dict.__contains__(self, key):
            incarnation = self._session._registry.incarnation_for_occurrence(
                self._session._top_occurrence(key)
            )
            live = (
                None
                if incarnation is None
                else self._session._registry.object_for_incarnation(incarnation)
            )
            if live is None or not isinstance(live, Person):
                raise StoreIntegrityError(
                    "evicted current Person lost its live incarnation"
                )
            dict.__setitem__(self, key, live)
            object.__setattr__(live, "_index_table", weakref.ref(self))
            object.__setattr__(live, "_index_key", key)
        self._dirty.add(key)
        self._lru.pop(key, None)
        if field == "alive":
            self._session.world.__dict__.pop("_living_cache", None)

    def _detach_index_binding(self, value):
        if isinstance(value, IndexedRecord):
            object.__setattr__(value, "_index_table", None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, Person):
            raise TypeError("world.people values must be Person")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = dict.__getitem__(self, key) if dict.__contains__(self, key) else None
        if old is record and currently_visible:
            return

        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)

        incarnation = self._session._bind_assigned_person(key, record)
        del incarnation
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)

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
        self._dirty.add(key)
        self._lru.pop(key, None)
        self._session.world.__dict__.pop("_living_cache", None)

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = dict.__getitem__(self, key) if dict.__contains__(self, key) else None
        if old is not None:
            self._detach_index_binding(old)
            self._session._detach_assigned_person(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_person(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)
        self._session.world.__dict__.pop("_living_cache", None)

    def clear(self):
        for key in tuple(self):
            del self[key]

    def update(self, records=(), **kwargs):
        for key, value in dict(records, **kwargs).items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
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

    def _planned_structural_ordinals(self):
        state = self._store._namespace_state_at(
            self._namespace, self._pin.captured_head
        )
        next_ordinal = 0 if state is None else state[1]
        structural = [
            key for key in (self._new_keys | self._reinserted)
            if key not in self._removed
        ]
        structural.sort(key=lambda key: self._overlay_ordinals[key])
        return {
            key: next_ordinal + index
            for index, key in enumerate(structural)
        }

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
        )
        structural_ordinals = self._planned_structural_ordinals()
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
                            record_schema=LAZY_PERSON_SCHEMA,
                        )
                    )
                    identity_changes.append(
                        IdentityOccurrenceChange(
                            self._namespace,
                            key,
                            (),
                            delete=True,
                        )
                    )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue

            record = dict.__getitem__(self, key)
            payload = self._store.codec.encode(record)
            incarnation = self._session._registry.incarnation_for_object(record)
            if incarnation is None:
                raise StoreIntegrityError(
                    "current lazy Person has no runtime incarnation"
                )
            if incarnation.store_identity != self._store.store_identity:
                raise StoreIntegrityError(
                    "current lazy Person incarnation belongs to another store"
                )
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new
                or reinsertion
                or payload != self._baseline_bytes(key)
            )
            if is_new or reinsertion:
                ordinal = structural_ordinals[key]
            else:
                ordinal = self._persisted_ordinal(key)
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        record,
                        record_schema=LAZY_PERSON_SCHEMA,
                        memberships=(
                            Membership("alive", bool(record.alive), ordinal),
                        ),
                        reinsertion=reinsertion,
                    )
                )
            if baseline_incarnation != incarnation.value:
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        (),
                        incarnation_id=incarnation.value,
                    )
                )
            if value_changed or baseline_incarnation != incarnation.value:
                effective_keys.append(key)
            if is_new or reinsertion:
                structural_keys.append(key)

        return (
            tuple(version_changes),
            tuple(identity_changes),
            tuple(effective_keys),
            tuple(structural_keys),
        )

    def accept_save(self, plan, new_pin):
        self._pin = new_pin
        self._baseline_count = self._store.namespace_size(
            new_pin, self._namespace
        )
        state = self._store._namespace_state_at(
            self._namespace, new_pin.captured_head
        )
        self._next_overlay_ordinal = 0 if state is None else state[1]
        for key in plan.touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                record = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(record)
                incarnation = self._session._registry.incarnation_for_object(
                    record
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
                        "committed lazy Person lost collection order"
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
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        # Diagnostics remain readable while save acknowledgement is uncertain;
        # do not route through guarded mapping reads here.
        logical_people = (
            self._baseline_count
            - len(self._removed)
            + len(self._new_keys)
        )
        return {
            "logical_people": logical_people,
            "resident_people": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "person_payload_loads": self._loads,
            "dirty_people": len(self._dirty),
            "removed_people": len(self._removed),
            "new_people": len(self._new_keys),
            "reinserted_people": len(self._reinserted),
        }


class _LazyLifetime:
    def __init__(self, session):
        self._session_ref = weakref.ref(session)
        self.closed = False

    def _session(self):
        session = self._session_ref()
        if self.closed or session is None or not session._active:
            raise StoreError("lazy World session is closed")
        return session

    def ensure_mutation(self, _operation="mutation"):
        self._session()._ensure_hybrid_mutation_allowed()

    def ensure_simulation(self, _operation="simulation"):
        self._session()._ensure_hybrid_mutation_allowed()

    def begin_step(self):
        session = self._session()
        session._ensure_hybrid_mutation_allowed()
        tracker = session._eager_tracker
        if tracker._cold_step_depth:
            raise StoreError("reentrant lazy simulation step is not allowed")
        tracker._cold_step_depth += 1

    def end_step(self):
        session = self._session_ref()
        if (
            session is not None
            and session._active
            and session._eager_tracker._cold_step_depth
        ):
            session._eager_tracker._cold_step_depth -= 1

    def ensure_eventlog_read(self):
        session = self._session()
        if session._state == "recovery-required":
            raise StoreError(
                "lazy EventLog is unavailable until save acknowledgement resolves"
            )

    def begin_operation(self, operation, *, allow_stale=False):
        session = self._session()
        if session._state == "stale" and not allow_stale:
            raise StoreConflictError("lazy World session is stale")
        if session._state not in ("active", "stale"):
            raise StoreError(
                f"lazy World cannot {operation} while {session._state}"
            )

    def end_operation(self, operation):
        self._session()

    def close(self):
        self.closed = True
        self._session_ref = lambda: None


class LazyWorldSession:
    def __init__(
        self,
        store,
        pin,
        world,
        manifest,
        links,
        prefix,
        next_incarnation,
        head,
        *,
        baseline_ordinals,
        resident_links,
        prefix_descriptor,
        tail_descriptor,
        commit_descriptor,
    ):
        self.store = store
        self.pin = pin
        self.world = world
        self.manifest = manifest
        self.identity_links = tuple(links)
        self.prefix = prefix
        self._active = True
        self._state = "active"
        self._pending_save: LazyPeopleSavePlan | None = None
        self._head = head
        self._registry = LazyIdentityRegistry(
            store.store_identity,
            next_incarnation=next_incarnation,
        )
        self.people = LazyRecordTable(self)
        object.__setattr__(world, "people", self.people)

        self._cross_boundary_links = _seed_cross_boundary_people_identity(
            self, links
        )
        self._eager_tracker = _initialize_eager_tracker(
            self,
            baseline_ordinals=baseline_ordinals,
            resident_links=resident_links,
            prefix_descriptor=prefix_descriptor,
            tail_descriptor=tail_descriptor,
            commit_descriptor=commit_descriptor,
        )

        self._lifetime = _LazyLifetime(self)
        object.__setattr__(world, "_ate_persistence_lifetime", self._lifetime)
        world.events._ate_persistence_lifetime = self._lifetime

    def _ensure_active(self):
        if not self._active:
            raise StoreError("lazy World session is closed")

    def _ensure_people_mutation_allowed(self):
        self._ensure_active()
        if self._state == "stale":
            raise StoreConflictError("lazy World session is stale")
        if self._state != "active":
            raise StoreError(
                f"lazy World mutation is unavailable while {self._state}"
            )

    def _ensure_hybrid_mutation_allowed(self):
        self._ensure_people_mutation_allowed()
        if self._cross_boundary_links:
            raise StoreError(
                "mutation of the eager graph is blocked while a persisted "
                "identity group crosses world.people; cross-boundary owner "
                "transfer requires the next identity integration proof"
            )

    def _top_occurrence(self, key):
        return Occurrence(PEOPLE_NAMESPACE, key, ())

    def _bind_assigned_person(self, key, person):
        existing = self._registry.incarnation_for_object(person)
        if existing is None:
            existing = self._registry.bind(person)
        occurrences = self._registry.occurrences_for_incarnation(existing)
        foreign = [
            item for item in occurrences
            if item != self._top_occurrence(key)
        ]
        if foreign:
            raise StoreError(
                "one Person incarnation cannot be newly assigned to multiple people keys"
            )
        self._registry.attach_occurrence(
            person, self._top_occurrence(key)
        )
        return existing

    def _detach_assigned_person(self, key, person):
        incarnation = self._registry.incarnation_for_object(person)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._top_occurrence(key), expected=incarnation
            )

    def _detach_unloaded_person(self, key):
        baseline = self.people._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        self._registry.attach_existing(
            incarnation, self._top_occurrence(key)
        )
        self._registry.detach_occurrence(
            self._top_occurrence(key), expected=incarnation
        )

    def _bind_loaded_person(self, key, person):
        owner = (PEOPLE_NAMESPACE, key)
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, PEOPLE_NAMESPACE, key
            )
        )
        if () not in labels:
            raise StoreIntegrityError(
                "lazy Person is missing top-level incarnation label"
            )
        result = person
        for path, incarnation_value in sorted(
            labels.items(), key=lambda item: (len(item[0]), repr(item[0]))
        ):
            incarnation = IncarnationId(
                self.store.store_identity, incarnation_value
            )
            occurrence = Occurrence(
                PEOPLE_NAMESPACE, key, tuple(path)
            )
            if not path:
                live = self._registry.object_for_incarnation(incarnation)
                if live is not None:
                    if not isinstance(live, Person):
                        raise StoreIntegrityError(
                            "Person incarnation is bound to wrong type"
                        )
                    result = live
                else:
                    self._registry.bind(
                        result,
                        occurrence,
                        incarnation=incarnation,
                    )
                self._registry.attach_existing(incarnation, occurrence)
                self.people._baseline_incarnation[key] = incarnation.value
                continue

            current = _relative_get(result, path)
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None and live is not current:
                result = _relative_set(result, path, live)
                current = live
            if live is None:
                self._registry.bind(
                    current,
                    occurrence,
                    incarnation=incarnation,
                )
            self._registry.attach_existing(incarnation, occurrence)

        from .persistence_schema import RECORD_FIELDS

        probe = IdentityOccurrenceIndex(
            self.store.codec,
            RECORD_FIELDS,
            mutable_event_tail_only=True,
        )
        owner_path = _owner_path(self.manifest, owner)
        probe.bootstrap([(owner, result, owner_path)])
        actual = {
            path[len(owner_path):]
            for _ident, _obj, path in probe.owner_occurrences[owner]
        }
        if actual != set(labels):
            raise StoreIntegrityError(
                "lazy Person occurrence labels are incomplete or extra"
            )
        return result

    def _merge_people_layout(self, cold_plan, structural_keys):
        layout_value = cold_plan.layout_value
        if not structural_keys:
            return cold_plan, layout_value

        if layout_value is None:
            layout_value = dict(self.manifest["collections"])
        else:
            layout_value = dict(layout_value)
        current = layout_value[PEOPLE_NAMESPACE]
        if type(current) is not tuple or len(current) != 3:
            raise StoreFormatError(
                "invalid world.people collection description"
            )
        layout_value[PEOPLE_NAMESPACE] = (
            current[0],
            len(self.people),
            current[2],
        )

        change_map = {
            (change.namespace, self.store.codec.encode(change.key)): change
            for change in cold_plan.changes
        }
        layout_change = RecordChange(
            META,
            COLLECTION_LAYOUT,
            layout_value,
            record_schema=RECORD_SCHEMA,
        )
        change_map[
            (META, self.store.codec.encode(COLLECTION_LAYOUT))
        ] = layout_change
        changes = tuple(
            change_map[key]
            for key in sorted(change_map, key=lambda item: (item[0], item[1]))
        )
        self._eager_tracker._manifest_dirty = True
        return replace(
            cold_plan,
            changes=changes,
            record_evidence=_change_evidence(
                self.store.codec, changes
            ),
            manifest_dirty=True,
            layout_value=layout_value,
        ), layout_value

    def _prepare_hybrid_save(self):
        (
            version_changes,
            identity_changes,
            touched_keys,
            structural_keys,
        ) = self.people.prepare_save_changes()
        people_effective = bool(version_changes or identity_changes)

        prior_manifest_dirty = self._eager_tracker._manifest_dirty
        if structural_keys:
            # Make the shared cold journal aware that collection-layout
            # publication is pending before it freezes acknowledgement state.
            self._eager_tracker._manifest_dirty = True

        token = uuid.uuid4().hex
        try:
            cold_plan = prepare_cold_save(
                self._eager_tracker,
                force=people_effective,
                token=token,
            )
        except Exception:
            if structural_keys:
                # Restore any pre-existing eager structural journal exactly.
                self._eager_tracker._manifest_dirty = prior_manifest_dirty
            raise

        if cold_plan is None:
            return None
        if (
            cold_plan.expected_generation != self.pin.captured_head
            or cold_plan.target_generation != self.pin.captured_head + 1
            or cold_plan.token != token
        ):
            raise StoreIntegrityError(
                "hybrid cold plan generation/token mismatch"
            )

        cold_plan, layout_value = self._merge_people_layout(
            cold_plan, structural_keys
        )
        expected_counts = self.store.codec.decode(
            cold_plan.expected_namespace_counts
        )
        expected_counts[PEOPLE_NAMESPACE] = (len(self.people), 0)
        cold_plan = replace(
            cold_plan,
            expected_namespace_counts=_counts_tuple(
                self.store.codec, expected_counts
            ),
        )
        return LazyPeopleSavePlan(
            token=token,
            target_generation=cold_plan.target_generation,
            version_changes=version_changes,
            identity_changes=identity_changes,
            cold_plan=cold_plan,
            touched_keys=touched_keys,
            structural_keys=structural_keys,
            layout_value=layout_value,
        )

    def _validate_people_successor(self, plan, generation):
        for change in plan.version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, PEOPLE_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted lazy Person remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved lazy Person is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                PEOPLE_NAMESPACE, typed_key, row, decode=False
            )
            if (
                schema != LAZY_PERSON_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
            ):
                raise StoreIntegrityError(
                    "saved lazy Person payload evidence mismatch"
                )
            expected_memberships = tuple(
                (
                    member.index_name,
                    member.value,
                    member.ordinal,
                )
                for member in change.memberships
            )
            if memberships != expected_memberships:
                raise StoreIntegrityError(
                    "saved lazy Person membership evidence mismatch"
                )

        for change in plan.identity_changes:
            encoded_key = self.store.codec.encode(change.owner_key)
            encoded_path = self.store.codec.encode(change.occurrence_path)
            row = self.store._visible_identity_occurrence(
                generation,
                change.owner_namespace,
                encoded_key,
                encoded_path,
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted Person incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved Person incarnation evidence mismatch"
                )

        if (
            self.store._identity_state_at(generation)[0]
            != self._registry.next_incarnation
        ):
            raise StoreIntegrityError(
                "saved incarnation allocator state mismatch"
            )

    def _arm_cold_publication(self, plan):
        tracker = self._eager_tracker
        if tracker._cold_plan is None:
            tracker._cold_plan = plan.cold_plan
            tracker._cold_publication_phase = "prepared"
        elif tracker._cold_plan is not plan.cold_plan:
            raise StoreIntegrityError(
                "hybrid cold publication plan changed"
            )
        tracker._cold_state = "recovery-required"

    def _publish_committed_hybrid(self, plan, result):
        # The durable pin has already moved with the commit. Advance runtime
        # pin references immediately so recovery/stale close can release the
        # correct generation even if later publication checks fail.
        self.pin = result.pin
        self.people._pin = result.pin
        self._arm_cold_publication(plan)
        tracker = self._eager_tracker
        self._validate_people_successor(
            plan, result.generation
        )
        status, head, replacement_prefix = _capture_successor(
            tracker, plan.cold_plan, full_evidence=False
        )
        if status != "ours":
            if replacement_prefix is not None:
                replacement_prefix.close()
            if status == "foreign":
                self._state = "stale"
                tracker._cold_state = "stale"
                raise StoreConflictError(
                    "hybrid successor was replaced by another writer"
                )
            raise StoreIntegrityError(
                "committed hybrid successor was not visible"
            )
        tracker._cold_head = head
        publish_cold_save(
            tracker, plan.cold_plan, replacement_prefix
        )
        self.people.accept_save(plan, result.pin)
        self.prefix = self.world.events._disk_prefix
        self._head = head
        self.identity_links = tuple(
            sorted(
                self._eager_tracker._committed_identity_targets.items(),
                key=lambda item: self.store.codec.encode(item[0]),
            )
        ) + tuple(self._cross_boundary_links)
        self._pending_save = None
        self._state = "active"
        return result.generation

    def _reset_uncommitted_plan(self):
        tracker = self._eager_tracker
        tracker._cold_plan = None
        tracker._cold_publication_phase = None
        tracker._cold_old_prefix_pending = None
        tracker._cold_state = "active"
        self._pending_save = None
        self._state = "active"

    def save(self):
        self._ensure_people_mutation_allowed()
        tracker = self._eager_tracker
        if tracker._cold_step_depth:
            raise StoreError(
                "lazy save requires a completed simulation step"
            )
        if self.world.__dict__.get("_index_current_people"):
            raise StoreError(
                "lazy save cannot run inside current_people_scope"
            )

        try:
            plan = self._prepare_hybrid_save()
        except StoreConflictError:
            self._eager_tracker._cold_state = "stale"
            self._state = "stale"
            raise
        if plan is None:
            return self.pin.captured_head

        self._pending_save = plan
        self._state = "saving"
        tracker._cold_plan = plan.cold_plan
        tracker._cold_publication_phase = "prepared"
        tracker._cold_state = "preparing"
        try:
            result = self.store.commit(
                self.pin,
                commit_token=plan.token,
                version_changes=plan.version_changes,
                identity_changes=plan.identity_changes,
                next_incarnation_id=self._registry.next_incarnation,
                changes=plan.cold_plan.changes,
                new_segments=plan.cold_plan.new_segments,
                metadata=plan.cold_plan.metadata,
            )
        except GenerationPressureError:
            self._reset_uncommitted_plan()
            raise
        except StoreConflictError:
            tracker._cold_state = "stale"
            tracker._cold_plan = None
            tracker._cold_publication_phase = None
            self._pending_save = None
            self._state = "stale"
            raise
        except Exception:
            encoded = self.store.codec.encode(plan.token)
            attempt = self.store._attempt_row(self.pin.token)
            if (
                attempt is not None
                and attempt[0] == encoded
                and attempt[2] in {"pending", "committed"}
            ):
                self._state = "recovery-required"
                tracker._cold_state = "recovery-required"
            else:
                self._reset_uncommitted_plan()
            raise

        if result.outcome == "conflict":
            tracker._cold_state = "stale"
            tracker._cold_plan = None
            tracker._cold_publication_phase = None
            self._pending_save = None
            self._state = "stale"
            raise StoreConflictError(
                "lazy World save lost the generation race"
            )
        if result.outcome == "not_committed":
            self._reset_uncommitted_plan()
            return result.generation
        if result.outcome != "committed":
            self._state = "recovery-required"
            tracker._cold_state = "recovery-required"
            raise StoreIntegrityError(
                f"unexpected lazy save outcome: {result.outcome}"
            )

        # Keep the original pin object until all runtime publication succeeds;
        # resolve_commit can reconcile it by token if acknowledgement is lost.
        try:
            return self._publish_committed_hybrid(plan, result)
        except Exception:
            if self._state != "stale":
                self._state = "recovery-required"
                tracker._cold_state = "recovery-required"
            raise

    def resolve_save(self):
        self._ensure_active()
        if self._state == "stale":
            raise StoreConflictError("lazy World session is stale")
        plan = self._pending_save
        if plan is None:
            if self._state != "active":
                raise StoreError(
                    f"lazy session has no resolvable save while {self._state}"
                )
            return self.pin.captured_head
        if self._state != "recovery-required":
            raise StoreError(
                f"lazy save cannot resolve while {self._state}"
            )

        result = self.store.resolve_commit(
            self.pin, plan.token
        )
        if result.outcome == "committed":
            return self._publish_committed_hybrid(plan, result)
        if result.outcome == "not_committed":
            self._reset_uncommitted_plan()
            return result.generation
        self._eager_tracker._cold_state = "stale"
        self._state = "stale"
        raise StoreConflictError(
            "lazy World save resolved as stale/conflict"
        )

    def diagnostics(self):
        self._ensure_active()
        tracker = self._eager_tracker
        return {
            "state": self._state,
            "people": self.people.diagnostics(),
            "identity": self._registry.diagnostics(),
            "store": self.store.diagnostics(),
            "eager_dirty_owners": len(tracker._dirty),
            "eager_deleted_owners": len(tracker._deleted),
            "eager_bound_objects": len(tracker._bound_ids),
            "cross_boundary_identity_links": len(
                self._cross_boundary_links
            ),
            "event_disk_events": self.world.events._disk_count,
            "event_pending_chunks": len(self.world.events._chunks),
            "event_tail_events": len(self.world.events._tail),
        }

    def _teardown_eager_tracker(self):
        tracker = self._eager_tracker
        if not tracker._active:
            return
        error = None
        try:
            tracker._unbind_world()
        except Exception as exc:
            error = exc
        finally:
            tracker._active = False
            tracker._clear_bindings()
            tracker._memo.clear()
            tracker._memo_reverse.clear()
            tracker._bound_root_originals.clear()
            tracker._bootstrap_originals.clear()
            tracker._cold_plan = None
            tracker._cold_publication_phase = None
            tracker._cold_old_prefix_pending = None
            tracker._cold_state = "closed"
        if error is not None:
            raise error

    def close(self):
        if not self._active:
            return
        if self._state == "recovery-required":
            raise StoreError(
                "resolve uncertain lazy save before closing the session"
            )
        self._lifetime.close()
        teardown_error = None
        try:
            self._teardown_eager_tracker()
        except Exception as exc:
            teardown_error = exc
        current_prefix = (
            self.world.events._disk_prefix
            if isinstance(self.world.events, EventLog)
            else None
        )
        if current_prefix is not None:
            current_prefix.close()
        try:
            self.store.release_pin(self.pin)
        finally:
            self._registry.close()
            self.store.close()
            self._active = False
            self._state = "closed"
        if teardown_error is not None:
            raise teardown_error

    def __enter__(self):
        self._ensure_active()
        return self

    def __exit__(self, *_args):
        self.close()

def _begin_matching_snapshot(store, pin):
    store.db.execute("BEGIN")
    store._active_read_transaction = True
    head = store.checked_head()
    if head.generation != pin.captured_head:
        store._active_read_transaction = False
        store.db.rollback()
        return None
    return head


def open_lazy_world_session(path, *, rules_id):
    """Open P4 people pilot without decoding world.people at ordinary open."""
    path = Path(path)
    store = LazyRecordStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=rules_id,
    )

    pin = None
    prefix = None
    try:
        # A pin can allow one concurrent advance.  Retry until the ordinary
        # eager capture transaction is exactly the pin's generation.
        for _attempt in range(4):
            candidate = store.capture_pin()
            head = _begin_matching_snapshot(store, candidate)
            if head is not None:
                pin = candidate
                break
            store.release_pin(candidate)
        if pin is None:
            raise StoreError(
                "could not capture a stable lazy World open generation"
            )

        try:
            # Use the accepted cold manifest reader so a structurally
            # updated collections/v1 overlay is authority for current
            # collection sizes. Reading only the fixed base manifest here
            # makes a valid post-save successor appear corrupt on reopen.
            manifest = _read_cold_manifest(store)
            if manifest.get("event_storage") != COLD_EVENT_STORAGE:
                raise StoreFormatError(
                    "open_lazy_world_session requires converted cold P4 storage"
                )

            metadata_rows = store.read_records(
                META, expected_record_schema=RECORD_SCHEMA
            )
            prefix_descriptor, tail_descriptor, commit_descriptor = (
                _read_event_descriptors(store)
            )
            if commit_descriptor.captured_generation != head.generation:
                raise StoreIntegrityError(
                    "cold commit generation disagrees with lazy head"
                )
            links = _read_current_identity_links(store)
            baseline_ordinals = _capture_cold_baseline_ordinals(
                store,
                manifest,
                excluded_namespaces={PEOPLE_NAMESPACE},
            )
            _validate_head_inventory(
                head,
                manifest,
                links,
                {
                    "metadata_rows": metadata_rows,
                    "prefix": prefix_descriptor,
                    "tail": tail_descriptor,
                },
            )

            description = manifest["collections"]["world.events"]
            expected_event_description = (
                COLD_EVENT_KIND,
                tail_descriptor.total_events,
                tail_descriptor.sealed_events // EventLog.chunk_size,
            )
            if description != expected_event_description:
                raise StoreIntegrityError(
                    "cold EventLog collection description disagrees with descriptors"
                )

            prefix = SealedEventPrefix.from_active_read_transaction(store)
            suffix = _read_suffix(
                store, tail_descriptor, prefix_descriptor
            )
            log = EventLog.from_disk_prefix(
                prefix,
                suffix,
                pending_sealed_events=(
                    tail_descriptor.sealed_events
                    - tail_descriptor.disk_events
                ),
            )

            objects = {
                root: object.__new__(cls)
                for root, cls in ROOT_TYPES.items()
            }
            for root, obj in objects.items():
                for name, kind in ROOT_FIELDS[root].items():
                    namespace = root + "." + name
                    if kind == "state":
                        value = objects[namespace]
                    elif namespace == PEOPLE_NAMESPACE:
                        value = None
                    elif namespace == "world.events":
                        value = log
                    else:
                        value = _restore_collection(
                            store,
                            namespace,
                            kind,
                            manifest["collections"][namespace],
                        )
                    object.__setattr__(obj, name, value)
            world = objects["world"]

            # Restore only aliases whose complete authority is already resident.
            resident_links = [
                link
                for link in links
                if not _path_under_people(link[0])
                and not _path_under_people(link[1])
            ]
            _restore_identity(
                world,
                resident_links,
                mutable_event_tail_only=True,
            )

            if (
                world.seed != head.metadata["seed"]
                or world.year != head.metadata["simulation_position"]
                or head.metadata["next_ids"]
                != {
                    key: getattr(world, key)
                    for key in (
                        "next_person",
                        "next_household",
                        "next_settlement",
                        "next_event",
                    )
                }
            ):
                raise StoreIntegrityError(
                    "lazy World disagrees with checked head"
                )
            if world.next_event != tail_descriptor.total_events + 1:
                raise StoreIntegrityError(
                    "lazy World next_event disagrees with EventLog"
                )

            next_incarnation = store._identity_state_at(
                head.generation
            )[0]
            session = LazyWorldSession(
                store,
                pin,
                world,
                manifest,
                links,
                prefix,
                next_incarnation,
                head,
                baseline_ordinals=baseline_ordinals,
                resident_links=resident_links,
                prefix_descriptor=prefix_descriptor,
                tail_descriptor=tail_descriptor,
                commit_descriptor=commit_descriptor,
            )
            prefix = None
            pin = None
            return session
        finally:
            store._active_read_transaction = False
            if store.db.in_transaction:
                store.db.rollback()
    except Exception:
        if prefix is not None:
            prefix.close()
        if pin is not None:
            try:
                store.release_pin(pin)
            except Exception:
                pass
        store.close()
        raise
