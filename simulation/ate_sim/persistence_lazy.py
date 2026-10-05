"""Opt-in P4 lazy World conversion and people pilot.

P3B remains unchanged.  This module adds an explicit cold->P4 conversion and
an initial read/query lazy session whose world.people collection is backed by
LazyRecordStore.  Save/lifecycle mutation is intentionally enabled in a later
slice after the open/query proof gate.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import ItemsView, KeysView, ValuesView
from dataclasses import is_dataclass
import os
from pathlib import Path
import tempfile
import weakref
from typing import Any, Iterator

from .core import Person, World
from .event_log import EventLog, FrozenDict, FrozenList
from .incremental_store import (
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
    _read_current_identity_links,
    _restore_collection,
    _restore_identity,
    _roots,
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
    LazyRecordStore,
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
    _capture_cold_world,
    _preflight_conversion_paths,
    _publish_private_cold_file,
    _read_event_descriptors,
    _read_suffix,
    _validate_head_inventory,
)


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
                        "ordinal,last_changed_generation FROM query_membership"
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


class LazyRecordTable(RecordTable):
    """RecordTable-compatible storage facade; underlying dict is cache only."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = PEOPLE_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = OrderedDict()
        self._loads = 0

    def _ensure(self):
        self._session._ensure_active()

    def __len__(self):
        self._ensure()
        return self._store.namespace_size(self._pin, self._namespace)

    def __iter__(self) -> Iterator[Any]:
        self._ensure()
        return self._store.iter_keys(self._pin, self._namespace)

    def __contains__(self, key):
        self._ensure()
        if dict.__contains__(self, key):
            return True
        return self._store.contains_lazy_key(self._pin, self._namespace, key)

    def __getitem__(self, key):
        self._ensure()
        if dict.__contains__(self, key):
            self._lru.pop(key, None)
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
        record = self._session._bind_loaded_person(key, checked.value)
        dict.__setitem__(self, key, record)
        if isinstance(record, IndexedRecord):
            object.__setattr__(record, "_index_table", weakref.ref(self))
            object.__setattr__(record, "_index_key", key)
        self._loads += 1
        self._lru[key] = None
        self._evict_clean()
        return record

    def _evict_clean(self):
        while len(self._lru) > self._clean_limit:
            key, _ = self._lru.popitem(last=False)
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

    def ids(self, fields, *values):
        self._ensure()
        fields = (fields,) if isinstance(fields, str) else tuple(fields)
        if fields != ("alive",) or len(values) != 1:
            raise StoreError(
                "people pilot currently supports only indexed alive queries"
            )
        return self._store.query_keys(
            self._pin, self._namespace, "alive", values[0]
        )

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

    # Mutation becomes available in the next lifecycle slice.  Blocking it here
    # makes accidental partial-save semantics impossible.
    def changed(self, key, field=None):
        if key in self.__dict__.get("_loading_keys", ()):
            return
        raise StoreError(
            "lazy people pilot mutation is not enabled until lifecycle integration"
        )

    def __setitem__(self, key, record):
        raise StoreError(
            "lazy people pilot mutation is not enabled until lifecycle integration"
        )

    def __delitem__(self, key):
        raise StoreError(
            "lazy people pilot mutation is not enabled until lifecycle integration"
        )

    def clear(self):
        raise StoreError(
            "lazy people pilot mutation is not enabled until lifecycle integration"
        )

    def diagnostics(self):
        return {
            "loaded_people": len(self),
            "resident_people": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "person_payload_loads": self._loads,
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
        raise StoreError(
            "lazy people pilot mutation is not enabled until lifecycle integration"
        )

    def ensure_simulation(self, _operation="simulation"):
        raise StoreError(
            "lazy people pilot simulation is not enabled until lifecycle integration"
        )

    def ensure_eventlog_read(self):
        self._session()

    def begin_operation(self, operation, *, allow_stale=False):
        self._session()

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
    ):
        self.store = store
        self.pin = pin
        self.world = world
        self.manifest = manifest
        self.identity_links = tuple(links)
        self.prefix = prefix
        self._active = True
        self._registry = LazyIdentityRegistry(
            store.store_identity,
            next_incarnation=store.read_identity_state(pin),
        )
        self.people = LazyRecordTable(self)
        object.__setattr__(world, "people", self.people)
        self._lifetime = _LazyLifetime(self)
        object.__setattr__(world, "_ate_persistence_lifetime", self._lifetime)
        world.events._ate_persistence_lifetime = self._lifetime

    def _ensure_active(self):
        if not self._active:
            raise StoreError("lazy World session is closed")

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

        # Prove label completeness for this decoded owner without walking any
        # unrelated Person/archive rows.
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

    def diagnostics(self):
        self._ensure_active()
        return {
            "people": self.people.diagnostics(),
            "identity": self._registry.diagnostics(),
            "store": self.store.diagnostics(),
        }

    def close(self):
        if not self._active:
            return
        self._lifetime.close()
        self.prefix.close()
        try:
            self.store.release_pin(self.pin)
        finally:
            self._registry.close()
            self.store.close()
            self._active = False

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
            manifest = store.read_record(
                META, "manifest", expected_record_schema=RECORD_SCHEMA
            )
            if (
                type(manifest) is not dict
                or manifest.get("event_storage") != COLD_EVENT_STORAGE
            ):
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

            session = LazyWorldSession(
                store, pin, world, manifest, links, prefix
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
