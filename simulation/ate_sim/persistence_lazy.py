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

from .core import Person, Household, World
from .incremental_store import _record_checksum
from .magic_resources import MagicAspiration, MagicResource
from .materials import MaterialLot, CraftedItem
from .metaphysics import SoulState
from .advancement import EssencePath, AbilityProgress, Understanding
from .mastery_training import ResponseModel
from .institutions import MagicUserRecord, AdventureNotice, SocietyApplication
from .transmission import Transmission
from .agency import MotiveState
from .social import Relationship
from .skills import SkillHistory
from .lineage import LineageNode
from .persistence_lazy_household_members import (
    LENGTH_NAMESPACE as HOUSEHOLD_LENGTH_NAMESPACE,
    LazyHouseholdMembers,
    bootstrap_household_members,
)
from .persistence_lazy_lineage_children import (
    LINEAGE_CHILD_NAMESPACE,
    LINEAGE_CHILD_EDGE_NAMESPACE,
    LAZY_LINEAGE_CHILD_SCHEMA,
    LAZY_LINEAGE_CHILD_EDGE_SCHEMA,
    LazyLineageChildrenTable,
    LazyLineageTrackedSet,
    insert_lineage_child_bucket,
    insert_lineage_child_edge,
)

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
    IDENTITY_LINKS,
    META,
    RECORD_SCHEMA,
    ROOT_FIELDS,
    ROOT_TYPES,
    SCHEMA,
    WorldCodec,
    _at_path,
    _read_cold_manifest,
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
from .persistence_schema import RECORD_FIELDS
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
ASPIRATION_NAMESPACE = "world.magic_resources.aspirations"
RESOURCE_NAMESPACE = "world.magic_resources.resources"
OWNER_INDEX_NAMESPACE = "world.magic_resources.owner_index"
MATERIAL_LOT_NAMESPACE = "world.materials.lots"
MATERIAL_ITEM_NAMESPACE = "world.materials.items"
MATERIAL_LOT_INDEX_NAMESPACE = "world.materials.lot_index"
MATERIAL_ACTIVE_INDEX_NAMESPACE = "world.materials.active_lot_index"
WALLET_NAMESPACE = "world.currency.wallets"
TREASURY_NAMESPACE = "world.currency.treasuries"
SOUL_NAMESPACE = "world.metaphysics.souls"
ADVANCEMENT_NAMESPACE = "world.advancement.paths"
INSTITUTION_MAGIC_RECORD_NAMESPACE = "world.institutions.magic_records"
INSTITUTION_NOTICE_NAMESPACE = "world.institutions.notices"
INSTITUTION_APPLICATION_NAMESPACE = "world.institutions.applications"
TRANSMISSION_NAMESPACE = "world.transmission.records"
MOTIVE_NAMESPACE = "world.agency.motives"
SOCIAL_EDGE_NAMESPACE = "world.social.edges"
SOCIAL_ADJACENCY_NAMESPACE = "world.social.adjacency"
SOCIAL_PARTNERSHIP_NAMESPACE = "world.social.partnerships"
SKILL_NAMESPACE = "world.skills.skills"
LINEAGE_NODE_NAMESPACE = "world.lineage.nodes"
GENEALOGY_PARENT_NAMESPACE = "world.genealogy.parents"
GENEALOGY_CHILD_NAMESPACE = "world.genealogy.children"
COMMUNITY_MEMBERSHIP_NAMESPACE = "world.communities.memberships"
LAZY_PERSON_SCHEMA = 1
LAZY_ASPIRATION_SCHEMA = 1
LAZY_RESOURCE_SCHEMA = 1
LAZY_OWNER_INDEX_SCHEMA = 1
LAZY_MATERIAL_LOT_SCHEMA = 1
LAZY_MATERIAL_ITEM_SCHEMA = 1
LAZY_MATERIAL_LOT_INDEX_SCHEMA = 1
LAZY_MATERIAL_ACTIVE_INDEX_SCHEMA = 1
LAZY_WALLET_SCHEMA = 1
LAZY_TREASURY_SCHEMA = 1
LAZY_SOUL_SCHEMA = 1
LAZY_ADVANCEMENT_SCHEMA = 1
LAZY_INSTITUTION_MAGIC_RECORD_SCHEMA = 1
LAZY_INSTITUTION_NOTICE_SCHEMA = 1
LAZY_INSTITUTION_APPLICATION_SCHEMA = 1
LAZY_TRANSMISSION_SCHEMA = 1
LAZY_MOTIVE_SCHEMA = 1
LAZY_SOCIAL_EDGE_SCHEMA = 1
LAZY_SOCIAL_ADJACENCY_SCHEMA = 1
LAZY_SOCIAL_PARTNERSHIP_SCHEMA = 1
LAZY_SKILL_SCHEMA = 1
LAZY_LINEAGE_NODE_SCHEMA = 1
LAZY_GENEALOGY_PARENT_SCHEMA = 1
LAZY_GENEALOGY_CHILD_SCHEMA = 1
LAZY_COMMUNITY_MEMBERSHIP_SCHEMA = 1
CLEAN_GROUP_LIMIT = 256


class _StepAwareLRU(OrderedDict):
    """LRU that records the clean working set touched by one simulation step."""

    def __init__(self, session):
        super().__init__()
        self._session_ref = weakref.ref(session)
        self._step_epoch = None
        self._step_touched = set()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        session = self._session_ref()
        if session is None:
            return
        tracker = getattr(session, "_eager_tracker", None)
        if tracker is None or not tracker._cold_step_depth:
            return
        epoch = getattr(session, "_hot_step_epoch", 0)
        if self._step_epoch != epoch:
            self._step_epoch = epoch
            self._step_touched.clear()
        self._step_touched.add(key)

    def touched(self, epoch):
        if self._step_epoch != epoch:
            return set()
        return set(self._step_touched)

    def finish_step(self, epoch):
        if self._step_epoch == epoch:
            self._step_touched.clear()
            self._step_epoch = None

    def clear(self):
        super().clear()
        self._step_touched.clear()
        self._step_epoch = None


def _cross_boundary_field_value_is_immutable(value) -> bool:
    cls = type(value)
    if value is None or cls in (
        bool, int, float, str, bytes, FrozenDict, FrozenList
    ):
        return True
    if cls is tuple:
        return all(
            _cross_boundary_field_value_is_immutable(item)
            for item in value
        )
    if cls is frozenset:
        return all(
            _cross_boundary_field_value_is_immutable(item)
            for item in value
        )
    return False


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


def _insert_lazy_plain_record(
    destination: LazyRecordStore,
    *,
    namespace: str,
    generation: int,
    typed_key: bytes,
    ordinal: int,
    value: Any,
    record_schema: int,
) -> None:
    codec = destination.codec
    payload = codec.encode(value)
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
            namespace,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            record_schema,
            memberships_blob,
            _version_checksum(
                namespace,
                typed_key,
                record_schema,
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
            namespace,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                namespace, typed_key, ordinal, generation, None
            ),
        ),
    )


def _institution_memberships(namespace, record, ordinal):
    if namespace == SOCIAL_EDGE_NAMESPACE:
        if not isinstance(record, Relationship):
            raise TypeError("expected Relationship")
        return tuple(
            ("person", person, ordinal)
            for person in dict.fromkeys((record.a, record.b))
        )
    if namespace == SOCIAL_PARTNERSHIP_NAMESPACE:
        if (
            type(record) is not tuple
            or len(record) != 2
            or type(record[0]) is not tuple
            or len(record[0]) != 2
            or type(record[1]) is not int
        ):
            raise TypeError("expected ((person_a, person_b), event_id)")
        pair, _event_id = record
        return tuple(
            ("person", person, ordinal)
            for person in dict.fromkeys(pair)
        )
    if namespace == TRANSMISSION_NAMESPACE:
        if not isinstance(record, Transmission):
            raise TypeError("expected Transmission")
        return (
            ("item", (record.item_kind, record.item_id), ordinal),
        )
    if namespace == MOTIVE_NAMESPACE:
        if not isinstance(record, MotiveState):
            raise TypeError("expected MotiveState")
        return ()
    if namespace == INSTITUTION_MAGIC_RECORD_NAMESPACE:
        if not isinstance(record, MagicUserRecord):
            raise TypeError("expected MagicUserRecord")
        return (("person", record.person, ordinal),)
    if namespace == INSTITUTION_NOTICE_NAMESPACE:
        if not isinstance(record, AdventureNotice):
            raise TypeError("expected AdventureNotice")
        return (
            ("status", record.status, ordinal),
            ("cause_event", record.cause_event, ordinal),
        )
    if namespace == INSTITUTION_APPLICATION_NAMESPACE:
        if not isinstance(record, SocietyApplication):
            raise TypeError("expected SocietyApplication")
        return (
            ("passed", record.passed, ordinal),
            ("person_society", (record.person, record.society), ordinal),
            (
                "person_society_passed",
                (record.person, record.society, record.passed),
                ordinal,
            ),
        )
    raise ValueError(f"unsupported institution namespace: {namespace}")


def _insert_lazy_indexed_record(
    destination: LazyRecordStore,
    *,
    namespace: str,
    generation: int,
    typed_key: bytes,
    ordinal: int,
    value: Any,
    record_schema: int,
) -> None:
    codec = destination.codec
    memberships = _institution_memberships(namespace, value, ordinal)
    payload = codec.encode(value)
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
            namespace,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            record_schema,
            memberships_blob,
            _version_checksum(
                namespace,
                typed_key,
                record_schema,
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
            namespace,
            typed_key,
            ordinal,
            generation,
            _order_checksum(namespace, typed_key, ordinal, generation, None),
        ),
    )
    for index_name, index_value, member_ordinal in memberships:
        encoded_value = codec.encode(index_value)
        destination.db.execute(
            "INSERT INTO lazy_query_versions("
            "namespace,index_name,index_value,record_key,ordinal,"
            "valid_from,valid_to,row_checksum"
            ") VALUES (?,?,?,?,?,?,NULL,?)",
            (
                namespace,
                index_name,
                encoded_value,
                typed_key,
                member_ordinal,
                generation,
                _query_checksum(
                    namespace,
                    index_name,
                    encoded_value,
                    typed_key,
                    member_ordinal,
                    generation,
                    None,
                ),
            ),
        )


def _insert_lazy_social_partnership(
    destination: LazyRecordStore,
    *,
    generation: int,
    typed_key: bytes,
    pair: tuple[int, int],
    ordinal: int,
    event_id: int,
) -> None:
    codec = destination.codec
    memberships = tuple(
        ("person", person, ordinal)
        for person in dict.fromkeys(pair)
    )
    payload = codec.encode(event_id)
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
            SOCIAL_PARTNERSHIP_NAMESPACE,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            LAZY_SOCIAL_PARTNERSHIP_SCHEMA,
            memberships_blob,
            _version_checksum(
                SOCIAL_PARTNERSHIP_NAMESPACE,
                typed_key,
                LAZY_SOCIAL_PARTNERSHIP_SCHEMA,
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
            SOCIAL_PARTNERSHIP_NAMESPACE,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                SOCIAL_PARTNERSHIP_NAMESPACE,
                typed_key,
                ordinal,
                generation,
                None,
            ),
        ),
    )
    for index_name, index_value, member_ordinal in memberships:
        encoded_value = codec.encode(index_value)
        destination.db.execute(
            "INSERT INTO lazy_query_versions("
            "namespace,index_name,index_value,record_key,ordinal,"
            "valid_from,valid_to,row_checksum"
            ") VALUES (?,?,?,?,?,?,NULL,?)",
            (
                SOCIAL_PARTNERSHIP_NAMESPACE,
                index_name,
                encoded_value,
                typed_key,
                member_ordinal,
                generation,
                _query_checksum(
                    SOCIAL_PARTNERSHIP_NAMESPACE,
                    index_name,
                    encoded_value,
                    typed_key,
                    member_ordinal,
                    generation,
                    None,
                ),
            ),
        )


def _insert_lazy_community_membership(
    destination: LazyRecordStore,
    *,
    generation: int,
    typed_key: bytes,
    key: tuple[int, int],
    ordinal: int,
    strength: float,
) -> None:
    codec = destination.codec
    memberships = (("person", key[0], ordinal),)
    payload = codec.encode(strength)
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
            COMMUNITY_MEMBERSHIP_NAMESPACE,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            LAZY_COMMUNITY_MEMBERSHIP_SCHEMA,
            memberships_blob,
            _version_checksum(
                COMMUNITY_MEMBERSHIP_NAMESPACE,
                typed_key,
                LAZY_COMMUNITY_MEMBERSHIP_SCHEMA,
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
            COMMUNITY_MEMBERSHIP_NAMESPACE,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                COMMUNITY_MEMBERSHIP_NAMESPACE,
                typed_key,
                ordinal,
                generation,
                None,
            ),
        ),
    )
    encoded_value = codec.encode(key[0])
    destination.db.execute(
        "INSERT INTO lazy_query_versions("
        "namespace,index_name,index_value,record_key,ordinal,"
        "valid_from,valid_to,row_checksum"
        ") VALUES (?,?,?,?,?,?,NULL,?)",
        (
            COMMUNITY_MEMBERSHIP_NAMESPACE,
            "person",
            encoded_value,
            typed_key,
            ordinal,
            generation,
            _query_checksum(
                COMMUNITY_MEMBERSHIP_NAMESPACE,
                "person",
                encoded_value,
                typed_key,
                ordinal,
                generation,
                None,
            ),
        ),
    )


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



def _plain_resource_value(resource):
    """Storage value for a live lazy resource without runtime wrappers."""
    if not isinstance(resource, MagicResource):
        raise TypeError("expected MagicResource")
    return replace(resource, transfers=list(resource.transfers))


def _resource_memberships(resource, ordinal):
    rows = []
    if (
        resource.consumed_year is None
        and resource.owner_kind is not None
        and resource.owner_id is not None
    ):
        rows.append(
            ("owner", (resource.owner_kind, resource.owner_id), ordinal)
        )
        rows.append(("owner_kind", resource.owner_kind, ordinal))
    return tuple(rows)


def _insert_lazy_resource(
    destination: LazyRecordStore,
    *,
    generation: int,
    typed_key: bytes,
    ordinal: int,
    resource: MagicResource,
) -> None:
    codec = destination.codec
    payload = codec.encode(resource)
    memberships = _resource_memberships(resource, ordinal)
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
            RESOURCE_NAMESPACE,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            LAZY_RESOURCE_SCHEMA,
            memberships_blob,
            _version_checksum(
                RESOURCE_NAMESPACE,
                typed_key,
                LAZY_RESOURCE_SCHEMA,
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
            RESOURCE_NAMESPACE,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                RESOURCE_NAMESPACE, typed_key, ordinal, generation, None
            ),
        ),
    )
    for index_name, index_value, member_ordinal in memberships:
        encoded_value = codec.encode(index_value)
        destination.db.execute(
            "INSERT INTO lazy_query_versions("
            "namespace,index_name,index_value,record_key,ordinal,"
            "valid_from,valid_to,row_checksum"
            ") VALUES (?,?,?,?,?,?,NULL,?)",
            (
                RESOURCE_NAMESPACE,
                index_name,
                encoded_value,
                typed_key,
                member_ordinal,
                generation,
                _query_checksum(
                    RESOURCE_NAMESPACE,
                    index_name,
                    encoded_value,
                    typed_key,
                    member_ordinal,
                    generation,
                    None,
                ),
            ),
        )



def _plain_material_lot_value(lot):
    """Storage value for a live lazy material lot without runtime wrappers."""
    if not isinstance(lot, MaterialLot):
        raise TypeError("expected MaterialLot")
    return replace(lot, transfers=list(lot.transfers))


def _material_lot_memberships(lot, ordinal):
    if lot.quantity - lot.consumed <= .01:
        return ()
    return (
        ("active_settlement", lot.settlement, ordinal),
        ("active_rank", (lot.settlement, lot.material_rank), ordinal),
    )


def _insert_lazy_material_lot(
    destination: LazyRecordStore,
    *,
    generation: int,
    typed_key: bytes,
    ordinal: int,
    lot: MaterialLot,
) -> None:
    codec = destination.codec
    payload = codec.encode(lot)
    memberships = _material_lot_memberships(lot, ordinal)
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
            MATERIAL_LOT_NAMESPACE,
            typed_key,
            generation,
            payload,
            payload_checksum,
            codec.version,
            LAZY_MATERIAL_LOT_SCHEMA,
            memberships_blob,
            _version_checksum(
                MATERIAL_LOT_NAMESPACE,
                typed_key,
                LAZY_MATERIAL_LOT_SCHEMA,
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
            MATERIAL_LOT_NAMESPACE,
            typed_key,
            ordinal,
            generation,
            _order_checksum(
                MATERIAL_LOT_NAMESPACE, typed_key, ordinal, generation, None
            ),
        ),
    )
    for index_name, index_value, member_ordinal in memberships:
        encoded_value = codec.encode(index_value)
        destination.db.execute(
            "INSERT INTO lazy_query_versions("
            "namespace,index_name,index_value,record_key,ordinal,"
            "valid_from,valid_to,row_checksum"
            ") VALUES (?,?,?,?,?,?,NULL,?)",
            (
                MATERIAL_LOT_NAMESPACE,
                index_name,
                encoded_value,
                typed_key,
                member_ordinal,
                generation,
                _query_checksum(
                    MATERIAL_LOT_NAMESPACE,
                    index_name,
                    encoded_value,
                    typed_key,
                    member_ordinal,
                    generation,
                    None,
                ),
            ),
        )


def convert_cold_to_lazy(source, destination, *, rules_id, paged_household_members=False):
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
            if paged_household_members:
                for target_path, owner_path in capture.identity_links:
                    if _household_member_path(target_path) or _household_member_path(owner_path):
                        raise StoreError("paged household conversion requires shared members identity integration")
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
                    aspiration_count = 0
                    aspiration_next_ordinal = 0
                    resource_count = 0
                    resource_next_ordinal = 0
                    owner_index_count = 0
                    owner_index_next_ordinal = 0
                    material_lot_count = 0
                    material_lot_next_ordinal = 0
                    material_item_count = 0
                    material_item_next_ordinal = 0
                    material_lot_index_count = 0
                    material_lot_index_next_ordinal = 0
                    material_active_index_count = 0
                    material_active_index_next_ordinal = 0
                    wallet_count = 0
                    wallet_next_ordinal = 0
                    treasury_count = 0
                    treasury_next_ordinal = 0
                    soul_count = 0
                    soul_next_ordinal = 0
                    advancement_count = 0
                    advancement_next_ordinal = 0
                    institution_magic_record_count = 0
                    institution_magic_record_next_ordinal = 0
                    institution_notice_count = 0
                    institution_notice_next_ordinal = 0
                    institution_application_count = 0
                    institution_application_next_ordinal = 0
                    transmission_count = 0
                    transmission_next_ordinal = 0
                    motive_count = 0
                    motive_next_ordinal = 0
                    social_edge_count = 0
                    social_edge_next_ordinal = 0
                    social_adjacency_count = 0
                    social_adjacency_next_ordinal = 0
                    social_partnership_count = 0
                    social_partnership_next_ordinal = 0
                    skill_count = 0
                    skill_next_ordinal = 0
                    lineage_node_count = 0
                    lineage_node_next_ordinal = 0
                    genealogy_parent_count = 0
                    genealogy_parent_next_ordinal = 0
                    genealogy_child_count = 0
                    genealogy_child_next_ordinal = 0
                    community_membership_count = 0
                    community_membership_next_ordinal = 0
                    lineage_child_count = 0
                    lineage_child_next_ordinal = 0
                    lineage_child_edge_count = 0
                    lineage_child_edge_next_ordinal = 0
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
                        if namespace not in (
                            PEOPLE_NAMESPACE,
                            ASPIRATION_NAMESPACE,
                            RESOURCE_NAMESPACE,
                            OWNER_INDEX_NAMESPACE,
                            MATERIAL_LOT_NAMESPACE,
                            MATERIAL_ITEM_NAMESPACE,
                            MATERIAL_LOT_INDEX_NAMESPACE,
                            MATERIAL_ACTIVE_INDEX_NAMESPACE,
                            WALLET_NAMESPACE,
                            TREASURY_NAMESPACE,
                            SOUL_NAMESPACE,
                            ADVANCEMENT_NAMESPACE,
                            INSTITUTION_MAGIC_RECORD_NAMESPACE,
                            INSTITUTION_NOTICE_NAMESPACE,
                            INSTITUTION_APPLICATION_NAMESPACE,
                            TRANSMISSION_NAMESPACE,
                            MOTIVE_NAMESPACE,
                            SOCIAL_EDGE_NAMESPACE,
                            SOCIAL_ADJACENCY_NAMESPACE,
                            SOCIAL_PARTNERSHIP_NAMESPACE,
                            SKILL_NAMESPACE,
                            LINEAGE_NODE_NAMESPACE,
                            LINEAGE_CHILD_NAMESPACE,
                            GENEALOGY_PARENT_NAMESPACE,
                            GENEALOGY_CHILD_NAMESPACE,
                            COMMUNITY_MEMBERSHIP_NAMESPACE,
                        ):
                            if paged_household_members and namespace == "world.households":
                                envelope = codec.decode(payload)
                                if type(envelope) is not tuple or len(envelope) != 2:
                                    raise StoreFormatError("invalid household envelope")
                                ordinal, household = envelope
                                if not isinstance(household, Household):
                                    raise StoreFormatError("invalid household record")
                                compact = replace(household, members=[])
                                payload = codec.encode((ordinal, compact))
                                checksum = _record_checksum(
                                    namespace, typed_key, record_schema,
                                    codec_version, changed_generation, payload,
                                )
                                row = (namespace, typed_key, payload, checksum,
                                       codec_version, record_schema, changed_generation)
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
                        ):
                            raise StoreFormatError(
                                f"invalid lazy source envelope: {namespace}"
                            )
                        ordinal, value = envelope
                        if namespace == PEOPLE_NAMESPACE:
                            if not isinstance(value, Person):
                                raise StoreFormatError(
                                    "invalid world.people source envelope"
                                )
                            _insert_lazy_person(
                                target,
                                generation=generation,
                                typed_key=typed_key,
                                key=key,
                                ordinal=ordinal,
                                person=value,
                            )
                            people_count += 1
                            next_ordinal = max(next_ordinal, ordinal + 1)
                        elif namespace == ASPIRATION_NAMESPACE:
                            if not isinstance(value, MagicAspiration):
                                raise StoreFormatError(
                                    "invalid aspirations source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=ASPIRATION_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_ASPIRATION_SCHEMA,
                            )
                            aspiration_count += 1
                            aspiration_next_ordinal = max(
                                aspiration_next_ordinal, ordinal + 1
                            )
                        elif namespace == RESOURCE_NAMESPACE:
                            if not isinstance(value, MagicResource):
                                raise StoreFormatError(
                                    "invalid resources source envelope"
                                )
                            _insert_lazy_resource(
                                target,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                resource=value,
                            )
                            resource_count += 1
                            resource_next_ordinal = max(
                                resource_next_ordinal, ordinal + 1
                            )
                        elif namespace == OWNER_INDEX_NAMESPACE:
                            if type(value) is not set or any(
                                type(item) is not int for item in value
                            ):
                                raise StoreFormatError(
                                    "invalid owner-index source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=OWNER_INDEX_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_OWNER_INDEX_SCHEMA,
                            )
                            owner_index_count += 1
                            owner_index_next_ordinal = max(
                                owner_index_next_ordinal, ordinal + 1
                            )
                        elif namespace == MATERIAL_LOT_NAMESPACE:
                            if not isinstance(value, MaterialLot):
                                raise StoreFormatError(
                                    "invalid material-lot source envelope"
                                )
                            _insert_lazy_material_lot(
                                target,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                lot=value,
                            )
                            material_lot_count += 1
                            material_lot_next_ordinal = max(
                                material_lot_next_ordinal, ordinal + 1
                            )
                        elif namespace == MATERIAL_ITEM_NAMESPACE:
                            if not isinstance(value, CraftedItem):
                                raise StoreFormatError(
                                    "invalid crafted-item source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=MATERIAL_ITEM_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_MATERIAL_ITEM_SCHEMA,
                            )
                            material_item_count += 1
                            material_item_next_ordinal = max(
                                material_item_next_ordinal, ordinal + 1
                            )
                        elif namespace == MATERIAL_LOT_INDEX_NAMESPACE:
                            if type(value) is not list or any(
                                type(item) is not int for item in value
                            ):
                                raise StoreFormatError(
                                    "invalid material lot-index source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=MATERIAL_LOT_INDEX_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_MATERIAL_LOT_INDEX_SCHEMA,
                            )
                            material_lot_index_count += 1
                            material_lot_index_next_ordinal = max(
                                material_lot_index_next_ordinal, ordinal + 1
                            )
                        elif namespace == MATERIAL_ACTIVE_INDEX_NAMESPACE:
                            if type(value) is not set or any(
                                type(item) is not int for item in value
                            ):
                                raise StoreFormatError(
                                    "invalid material active-index source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=MATERIAL_ACTIVE_INDEX_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_MATERIAL_ACTIVE_INDEX_SCHEMA,
                            )
                            material_active_index_count += 1
                            material_active_index_next_ordinal = max(
                                material_active_index_next_ordinal, ordinal + 1
                            )
                        elif namespace == WALLET_NAMESPACE:
                            if type(value) is not dict:
                                raise StoreFormatError(
                                    "invalid wallet source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=WALLET_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_WALLET_SCHEMA,
                            )
                            wallet_count += 1
                            wallet_next_ordinal = max(
                                wallet_next_ordinal, ordinal + 1
                            )
                        elif namespace == TREASURY_NAMESPACE:
                            if type(value) is not dict:
                                raise StoreFormatError(
                                    "invalid treasury source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=TREASURY_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_TREASURY_SCHEMA,
                            )
                            treasury_count += 1
                            treasury_next_ordinal = max(
                                treasury_next_ordinal, ordinal + 1
                            )
                        elif namespace == SOUL_NAMESPACE:
                            if not isinstance(value, SoulState):
                                raise StoreFormatError(
                                    "invalid soul source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=SOUL_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_SOUL_SCHEMA,
                            )
                            soul_count += 1
                            soul_next_ordinal = max(
                                soul_next_ordinal, ordinal + 1
                            )
                        elif namespace == ADVANCEMENT_NAMESPACE:
                            if not isinstance(value, EssencePath):
                                raise StoreFormatError(
                                    "invalid advancement path source envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=ADVANCEMENT_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_ADVANCEMENT_SCHEMA,
                            )
                            advancement_count += 1
                            advancement_next_ordinal = max(
                                advancement_next_ordinal, ordinal + 1
                            )
                        elif namespace == INSTITUTION_MAGIC_RECORD_NAMESPACE:
                            if not isinstance(value, MagicUserRecord):
                                raise StoreFormatError(
                                    "invalid institution magic-record envelope"
                                )
                            _insert_lazy_indexed_record(
                                target,
                                namespace=namespace,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_INSTITUTION_MAGIC_RECORD_SCHEMA,
                            )
                            institution_magic_record_count += 1
                            institution_magic_record_next_ordinal = max(
                                institution_magic_record_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == INSTITUTION_NOTICE_NAMESPACE:
                            if not isinstance(value, AdventureNotice):
                                raise StoreFormatError(
                                    "invalid institution notice envelope"
                                )
                            _insert_lazy_indexed_record(
                                target,
                                namespace=namespace,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_INSTITUTION_NOTICE_SCHEMA,
                            )
                            institution_notice_count += 1
                            institution_notice_next_ordinal = max(
                                institution_notice_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == INSTITUTION_APPLICATION_NAMESPACE:
                            if not isinstance(value, SocietyApplication):
                                raise StoreFormatError(
                                    "invalid institution application envelope"
                                )
                            _insert_lazy_indexed_record(
                                target,
                                namespace=INSTITUTION_APPLICATION_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_INSTITUTION_APPLICATION_SCHEMA,
                            )
                            institution_application_count += 1
                            institution_application_next_ordinal = max(
                                institution_application_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == TRANSMISSION_NAMESPACE:
                            if not isinstance(value, Transmission):
                                raise StoreFormatError(
                                    "invalid transmission envelope"
                                )
                            _insert_lazy_indexed_record(
                                target,
                                namespace=TRANSMISSION_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_TRANSMISSION_SCHEMA,
                            )
                            transmission_count += 1
                            transmission_next_ordinal = max(
                                transmission_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == MOTIVE_NAMESPACE:
                            if not isinstance(value, MotiveState):
                                raise StoreFormatError(
                                    "invalid motive envelope"
                                )
                            _insert_lazy_indexed_record(
                                target,
                                namespace=MOTIVE_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_MOTIVE_SCHEMA,
                            )
                            motive_count += 1
                            motive_next_ordinal = max(
                                motive_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == SOCIAL_EDGE_NAMESPACE:
                            if not isinstance(value, Relationship):
                                raise StoreFormatError(
                                    "invalid social relationship envelope"
                                )
                            _insert_lazy_indexed_record(
                                target,
                                namespace=SOCIAL_EDGE_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_SOCIAL_EDGE_SCHEMA,
                            )
                            social_edge_count += 1
                            social_edge_next_ordinal = max(
                                social_edge_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == SOCIAL_ADJACENCY_NAMESPACE:
                            if type(value) is not set or any(
                                type(item) is not int for item in value
                            ):
                                raise StoreFormatError(
                                    "invalid social adjacency envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=SOCIAL_ADJACENCY_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_SOCIAL_ADJACENCY_SCHEMA,
                            )
                            social_adjacency_count += 1
                            social_adjacency_next_ordinal = max(
                                social_adjacency_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == SOCIAL_PARTNERSHIP_NAMESPACE:
                            if type(key) is not tuple or len(key) != 2 or type(value) is not int:
                                raise StoreFormatError(
                                    "invalid social partnership envelope"
                                )
                            _insert_lazy_social_partnership(
                                target,
                                generation=generation,
                                typed_key=typed_key,
                                pair=key,
                                ordinal=ordinal,
                                event_id=value,
                            )
                            social_partnership_count += 1
                            social_partnership_next_ordinal = max(
                                social_partnership_next_ordinal,
                                ordinal + 1,
                            )
                        elif namespace == SKILL_NAMESPACE:
                            if not isinstance(value, SkillHistory):
                                raise StoreFormatError(
                                    "invalid skill history envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=SKILL_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_SKILL_SCHEMA,
                            )
                            skill_count += 1
                            skill_next_ordinal = max(
                                skill_next_ordinal, ordinal + 1
                            )
                        elif namespace == LINEAGE_NODE_NAMESPACE:
                            if not isinstance(value, LineageNode):
                                raise StoreFormatError(
                                    "invalid lineage-node envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=LINEAGE_NODE_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_LINEAGE_NODE_SCHEMA,
                            )
                            lineage_node_count += 1
                            lineage_node_next_ordinal = max(
                                lineage_node_next_ordinal, ordinal + 1
                            )
                        elif namespace == LINEAGE_CHILD_NAMESPACE:
                            if (
                                type(key) is not tuple
                                or len(key) != 2
                                or type(key[0]) is not str
                                or type(key[1]) is not int
                                or type(value) is not set
                                or any(
                                    type(child) is not tuple
                                    or len(child) != 2
                                    or type(child[0]) is not str
                                    or type(child[1]) is not int
                                    for child in value
                                )
                            ):
                                raise StoreFormatError(
                                    "invalid lineage-child envelope"
                                )
                            insert_lineage_child_bucket(
                                target,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                count=len(value),
                            )
                            lineage_child_count += 1
                            lineage_child_next_ordinal = max(
                                lineage_child_next_ordinal, ordinal + 1
                            )
                            for child in sorted(
                                value, key=codec.encode
                            ):
                                insert_lineage_child_edge(
                                    target,
                                    generation=generation,
                                    parent=key,
                                    child=child,
                                    ordinal=lineage_child_edge_next_ordinal,
                                )
                                lineage_child_edge_count += 1
                                lineage_child_edge_next_ordinal += 1
                        elif namespace == GENEALOGY_PARENT_NAMESPACE:
                            if (
                                type(key) is not int
                                or type(value) is not tuple
                                or any(type(parent) is not int for parent in value)
                            ):
                                raise StoreFormatError(
                                    "invalid genealogy-parent envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=GENEALOGY_PARENT_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_GENEALOGY_PARENT_SCHEMA,
                            )
                            genealogy_parent_count += 1
                            genealogy_parent_next_ordinal = max(
                                genealogy_parent_next_ordinal, ordinal + 1
                            )
                        elif namespace == GENEALOGY_CHILD_NAMESPACE:
                            if (
                                type(key) is not int
                                or type(value) is not list
                                or any(type(child) is not int for child in value)
                            ):
                                raise StoreFormatError(
                                    "invalid genealogy-child envelope"
                                )
                            _insert_lazy_plain_record(
                                target,
                                namespace=GENEALOGY_CHILD_NAMESPACE,
                                generation=generation,
                                typed_key=typed_key,
                                ordinal=ordinal,
                                value=value,
                                record_schema=LAZY_GENEALOGY_CHILD_SCHEMA,
                            )
                            genealogy_child_count += 1
                            genealogy_child_next_ordinal = max(
                                genealogy_child_next_ordinal, ordinal + 1
                            )
                        else:
                            if (
                                type(key) is not tuple
                                or len(key) != 2
                                or any(type(part) is not int for part in key)
                                or type(value) not in (int, float)
                            ):
                                raise StoreFormatError(
                                    "invalid community-membership envelope"
                                )
                            _insert_lazy_community_membership(
                                target,
                                generation=generation,
                                typed_key=typed_key,
                                key=key,
                                ordinal=ordinal,
                                strength=value,
                            )
                            community_membership_count += 1
                            community_membership_next_ordinal = max(
                                community_membership_next_ordinal,
                                ordinal + 1,
                            )

                    for row in source_store.db.execute(
                        "SELECT namespace,index_name,index_value,record_key,"
                        "ordinal,generation FROM query_membership"
                    ):
                        if row[0] not in (
                            PEOPLE_NAMESPACE,
                            ASPIRATION_NAMESPACE,
                            RESOURCE_NAMESPACE,
                            OWNER_INDEX_NAMESPACE,
                            MATERIAL_LOT_NAMESPACE,
                            MATERIAL_ITEM_NAMESPACE,
                            MATERIAL_LOT_INDEX_NAMESPACE,
                            MATERIAL_ACTIVE_INDEX_NAMESPACE,
                            WALLET_NAMESPACE,
                            TREASURY_NAMESPACE,
                            SOUL_NAMESPACE,
                            ADVANCEMENT_NAMESPACE,
                            INSTITUTION_MAGIC_RECORD_NAMESPACE,
                            INSTITUTION_NOTICE_NAMESPACE,
                            INSTITUTION_APPLICATION_NAMESPACE,
                            TRANSMISSION_NAMESPACE,
                            MOTIVE_NAMESPACE,
                            SOCIAL_EDGE_NAMESPACE,
                            SOCIAL_ADJACENCY_NAMESPACE,
                            SOCIAL_PARTNERSHIP_NAMESPACE,
                            SKILL_NAMESPACE,
                            LINEAGE_NODE_NAMESPACE,
                            LINEAGE_CHILD_NAMESPACE,
                            GENEALOGY_PARENT_NAMESPACE,
                            GENEALOGY_CHILD_NAMESPACE,
                            COMMUNITY_MEMBERSHIP_NAMESPACE,
                        ):
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

                    target.db.execute(
                        "INSERT INTO lazy_namespace_state("
                        "namespace,valid_from,valid_to,member_count,"
                        "next_ordinal,row_checksum"
                        ") VALUES (?,?,NULL,?,?,?)",
                        (
                            ASPIRATION_NAMESPACE,
                            generation,
                            aspiration_count,
                            aspiration_next_ordinal,
                            _namespace_checksum(
                                ASPIRATION_NAMESPACE,
                                aspiration_count,
                                aspiration_next_ordinal,
                                generation,
                                None,
                            ),
                        ),
                    )

                    target.db.execute(
                        "INSERT INTO lazy_namespace_state("
                        "namespace,valid_from,valid_to,member_count,"
                        "next_ordinal,row_checksum"
                        ") VALUES (?,?,NULL,?,?,?)",
                        (
                            RESOURCE_NAMESPACE,
                            generation,
                            resource_count,
                            resource_next_ordinal,
                            _namespace_checksum(
                                RESOURCE_NAMESPACE,
                                resource_count,
                                resource_next_ordinal,
                                generation,
                                None,
                            ),
                        ),
                    )

                    target.db.execute(
                        "INSERT INTO lazy_namespace_state("
                        "namespace,valid_from,valid_to,member_count,"
                        "next_ordinal,row_checksum"
                        ") VALUES (?,?,NULL,?,?,?)",
                        (
                            OWNER_INDEX_NAMESPACE,
                            generation,
                            owner_index_count,
                            owner_index_next_ordinal,
                            _namespace_checksum(
                                OWNER_INDEX_NAMESPACE,
                                owner_index_count,
                                owner_index_next_ordinal,
                                generation,
                                None,
                            ),
                        ),
                    )

                    for namespace, member_count, next_ord in (
                        (
                            MATERIAL_LOT_NAMESPACE,
                            material_lot_count,
                            material_lot_next_ordinal,
                        ),
                        (
                            MATERIAL_ITEM_NAMESPACE,
                            material_item_count,
                            material_item_next_ordinal,
                        ),
                        (
                            MATERIAL_LOT_INDEX_NAMESPACE,
                            material_lot_index_count,
                            material_lot_index_next_ordinal,
                        ),
                        (
                            MATERIAL_ACTIVE_INDEX_NAMESPACE,
                            material_active_index_count,
                            material_active_index_next_ordinal,
                        ),
                        (WALLET_NAMESPACE, wallet_count, wallet_next_ordinal),
                        (
                            TREASURY_NAMESPACE,
                            treasury_count,
                            treasury_next_ordinal,
                        ),
                        (
                            SOUL_NAMESPACE,
                            soul_count,
                            soul_next_ordinal,
                        ),
                        (
                            ADVANCEMENT_NAMESPACE,
                            advancement_count,
                            advancement_next_ordinal,
                        ),
                        (
                            INSTITUTION_MAGIC_RECORD_NAMESPACE,
                            institution_magic_record_count,
                            institution_magic_record_next_ordinal,
                        ),
                        (
                            INSTITUTION_NOTICE_NAMESPACE,
                            institution_notice_count,
                            institution_notice_next_ordinal,
                        ),
                        (
                            INSTITUTION_APPLICATION_NAMESPACE,
                            institution_application_count,
                            institution_application_next_ordinal,
                        ),
                        (
                            TRANSMISSION_NAMESPACE,
                            transmission_count,
                            transmission_next_ordinal,
                        ),
                        (
                            MOTIVE_NAMESPACE,
                            motive_count,
                            motive_next_ordinal,
                        ),
                        (
                            SOCIAL_EDGE_NAMESPACE,
                            social_edge_count,
                            social_edge_next_ordinal,
                        ),
                        (
                            SOCIAL_ADJACENCY_NAMESPACE,
                            social_adjacency_count,
                            social_adjacency_next_ordinal,
                        ),
                        (
                            SOCIAL_PARTNERSHIP_NAMESPACE,
                            social_partnership_count,
                            social_partnership_next_ordinal,
                        ),
                        (
                            SKILL_NAMESPACE,
                            skill_count,
                            skill_next_ordinal,
                        ),
                        (
                            LINEAGE_NODE_NAMESPACE,
                            lineage_node_count,
                            lineage_node_next_ordinal,
                        ),
                        (
                            LINEAGE_CHILD_NAMESPACE,
                            lineage_child_count,
                            lineage_child_next_ordinal,
                        ),
                        (
                            LINEAGE_CHILD_EDGE_NAMESPACE,
                            lineage_child_edge_count,
                            lineage_child_edge_next_ordinal,
                        ),
                        (
                            GENEALOGY_PARENT_NAMESPACE,
                            genealogy_parent_count,
                            genealogy_parent_next_ordinal,
                        ),
                        (
                            GENEALOGY_CHILD_NAMESPACE,
                            genealogy_child_count,
                            genealogy_child_next_ordinal,
                        ),
                        (
                            COMMUNITY_MEMBERSHIP_NAMESPACE,
                            community_membership_count,
                            community_membership_next_ordinal,
                        ),
                    ):
                        target.db.execute(
                            "INSERT INTO lazy_namespace_state("
                            "namespace,valid_from,valid_to,member_count,"
                            "next_ordinal,row_checksum"
                            ") VALUES (?,?,NULL,?,?,?)",
                            (
                                namespace,
                                generation,
                                member_count,
                                next_ord,
                                _namespace_checksum(
                                    namespace,
                                    member_count,
                                    next_ord,
                                    generation,
                                    None,
                                ),
                            ),
                        )

                    if paged_household_members:
                        bootstrap_household_members(
                            target, generation,
                            ((hid, household.members)
                             for hid, household in capture.world.households.items()),
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
                "aspirations": aspiration_count,
                "resources": resource_count,
                "owner_index": owner_index_count,
                "material_lots": material_lot_count,
                "material_items": material_item_count,
                "material_lot_index": material_lot_index_count,
                "material_active_index": material_active_index_count,
                "wallets": wallet_count,
                "treasuries": treasury_count,
                "souls": soul_count,
                "advancement_paths": advancement_count,
                "institution_magic_records": institution_magic_record_count,
                "institution_notices": institution_notice_count,
                "institution_applications": institution_application_count,
                "transmissions": transmission_count,
                "motives": motive_count,
                "social_edges": social_edge_count,
                "social_adjacency": social_adjacency_count,
                "social_partnerships": social_partnership_count,
                "skills": skill_count,
                "lineage_nodes": lineage_node_count,
                "lineage_children": lineage_child_count,
                "lineage_child_edges": lineage_child_edge_count,
                "genealogy_parents": genealogy_parent_count,
                "genealogy_children": genealogy_child_count,
                "community_memberships": community_membership_count,
                "identity_occurrences": summary["identity_occurrences"],
                "next_incarnation_id": summary["next_incarnation_id"],
                "source_preserved": True,
            }
    finally:
        if capture is not None:
            capture.prefix.close()
        source_store.close()


def _household_member_path(path) -> bool:
    return (
        len(path) >= 3
        and path[0] == ("field", "households")
        and path[1][0] == "key"
        and path[2] == ("field", "members")
    )


def _path_under_people(path) -> bool:
    return bool(path) and path[0] == ("field", "people")


def _aspiration_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "magic_resources")
        and path[1] == ("field", "aspirations")
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _resource_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "magic_resources")
        and path[1] == ("field", "resources")
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _owner_index_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "magic_resources")
        and path[1] == ("field", "owner_index")
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None



def _material_occurrence_from_path(path, field):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "materials")
        and path[1] == ("field", field)
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None




def _genealogy_occurrence_from_path(path, field):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "genealogy")
        and path[1] == ("field", field)
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _currency_occurrence_from_path(path, field):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "currency")
        and path[1] == ("field", field)
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _soul_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "metaphysics")
        and path[1] == ("field", "souls")
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _advancement_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "advancement")
        and path[1] == ("field", "paths")
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _institution_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "institutions")
        and type(path[1]) is tuple
        and len(path[1]) == 2
        and path[1][0] == "field"
        and path[1][1] in ("magic_records", "notices", "applications")
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        namespace = {
            "magic_records": INSTITUTION_MAGIC_RECORD_NAMESPACE,
            "notices": INSTITUTION_NOTICE_NAMESPACE,
            "applications": INSTITUTION_APPLICATION_NAMESPACE,
        }[path[1][1]]
        return namespace, path[2][1], tuple(path[3:])
    return None


def _social_occurrence_from_path(path, field):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "social")
        and path[1] == ("field", field)
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _lineage_children_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and path[0] == ("field", "lineage")
        and path[1] == ("field", "children")
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        return path[2][1], tuple(path[3:])
    return None


def _scalar_archive_occurrence_from_path(path):
    if (
        type(path) is tuple
        and len(path) >= 3
        and type(path[0]) is tuple
        and len(path[0]) == 2
        and path[0][0] == "field"
        and type(path[1]) is tuple
        and len(path[1]) == 2
        and path[1][0] == "field"
        and type(path[2]) is tuple
        and len(path[2]) == 2
        and path[2][0] == "key"
    ):
        pair = (path[0][1], path[1][1])
        namespace = {
            ("transmission", "records"): TRANSMISSION_NAMESPACE,
            ("agency", "motives"): MOTIVE_NAMESPACE,
            ("skills", "skills"): SKILL_NAMESPACE,
            ("lineage", "nodes"): LINEAGE_NODE_NAMESPACE,
        }.get(pair)
        if namespace is not None:
            return namespace, path[2][1], tuple(path[3:])
    return None


def _lazy_occurrence_from_path(path):
    people = _people_occurrence_from_path(path)
    if people is not None:
        return PEOPLE_NAMESPACE, people[0], people[1], Person
    aspiration = _aspiration_occurrence_from_path(path)
    if aspiration is not None:
        return (
            ASPIRATION_NAMESPACE,
            aspiration[0],
            aspiration[1],
            MagicAspiration,
        )
    resource = _resource_occurrence_from_path(path)
    if resource is not None:
        relative = resource[1]
        expected_type = (
            list
            if relative == LazyResourceTable._transfer_path
            else MagicResource
        )
        return (
            RESOURCE_NAMESPACE,
            resource[0],
            relative,
            expected_type,
        )
    owner_bucket = _owner_index_occurrence_from_path(path)
    if owner_bucket is not None:
        return (
            OWNER_INDEX_NAMESPACE,
            owner_bucket[0],
            owner_bucket[1],
            set,
        )
    material_lot = _material_occurrence_from_path(path, "lots")
    if material_lot is not None:
        relative = material_lot[1]
        expected_type = (
            list
            if relative == LazyMaterialLotTable._transfer_path
            else MaterialLot
        )
        return (
            MATERIAL_LOT_NAMESPACE,
            material_lot[0],
            relative,
            expected_type,
        )
    material_item = _material_occurrence_from_path(path, "items")
    if material_item is not None:
        return (
            MATERIAL_ITEM_NAMESPACE,
            material_item[0],
            material_item[1],
            CraftedItem,
        )
    material_lot_index = _material_occurrence_from_path(path, "lot_index")
    if material_lot_index is not None:
        return (
            MATERIAL_LOT_INDEX_NAMESPACE,
            material_lot_index[0],
            material_lot_index[1],
            list,
        )
    material_active_index = _material_occurrence_from_path(
        path, "active_lot_index"
    )
    if material_active_index is not None:
        return (
            MATERIAL_ACTIVE_INDEX_NAMESPACE,
            material_active_index[0],
            material_active_index[1],
            set,
        )
    genealogy_child = _genealogy_occurrence_from_path(path, "children")
    if genealogy_child is not None:
        return (
            GENEALOGY_CHILD_NAMESPACE,
            genealogy_child[0],
            genealogy_child[1],
            list,
        )
    wallet = _currency_occurrence_from_path(path, "wallets")
    if wallet is not None:
        return WALLET_NAMESPACE, wallet[0], wallet[1], dict
    treasury = _currency_occurrence_from_path(path, "treasuries")
    if treasury is not None:
        return TREASURY_NAMESPACE, treasury[0], treasury[1], dict
    soul = _soul_occurrence_from_path(path)
    if soul is not None:
        relative = soul[1]
        if relative in (
            (("field", "authorities"),),
            (("field", "marks"),),
        ):
            expected_type = set
        elif relative == (("field", "cosmic_links"),):
            expected_type = dict
        elif relative == (("field", "transformations"),):
            expected_type = list
        else:
            expected_type = SoulState
        return SOUL_NAMESPACE, soul[0], relative, expected_type
    advancement = _advancement_occurrence_from_path(path)
    if advancement is not None:
        relative = advancement[1]
        return (
            ADVANCEMENT_NAMESPACE,
            advancement[0],
            relative,
            EssencePath if not relative else object,
        )
    institution = _institution_occurrence_from_path(path)
    if institution is not None:
        namespace, key, relative = institution
        expected = {
            INSTITUTION_MAGIC_RECORD_NAMESPACE: MagicUserRecord,
            INSTITUTION_NOTICE_NAMESPACE: AdventureNotice,
            INSTITUTION_APPLICATION_NAMESPACE: SocietyApplication,
        }[namespace]
        return namespace, key, relative, expected
    lineage_children = _lineage_children_occurrence_from_path(path)
    if lineage_children is not None:
        return (
            LINEAGE_CHILD_NAMESPACE,
            lineage_children[0],
            lineage_children[1],
            set,
        )
    scalar_archive = _scalar_archive_occurrence_from_path(path)
    if scalar_archive is not None:
        namespace, key, relative = scalar_archive
        expected = {
            TRANSMISSION_NAMESPACE: Transmission,
            MOTIVE_NAMESPACE: MotiveState,
            SKILL_NAMESPACE: SkillHistory,
            LINEAGE_NODE_NAMESPACE: LineageNode,
        }[namespace]
        return namespace, key, relative, expected
    social_edge = _social_occurrence_from_path(path, "edges")
    if social_edge is not None:
        relative = social_edge[1]
        expected = (
            list
            if relative == LazySocialEdgeTable._history_path
            else Relationship
        )
        return SOCIAL_EDGE_NAMESPACE, social_edge[0], relative, expected
    social_adjacency = _social_occurrence_from_path(path, "adjacency")
    if social_adjacency is not None:
        return (
            SOCIAL_ADJACENCY_NAMESPACE,
            social_adjacency[0],
            social_adjacency[1],
            set,
        )
    return None


def _path_under_lazy(path) -> bool:
    return _lazy_occurrence_from_path(path) is not None


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


def _seed_cross_boundary_lazy_identity(session, links):
    cross = []
    generation = session.pin.captured_head
    for target, owner in links:
        target_lazy = _lazy_occurrence_from_path(target)
        owner_lazy = _lazy_occurrence_from_path(owner)
        if target_lazy is None and owner_lazy is None:
            continue

        if target_lazy is not None and owner_lazy is not None:
            incarnations = []
            for namespace, key, relative, _expected_type in (
                target_lazy, owner_lazy
            ):
                encoded_key = session.store.codec.encode(key)
                encoded_path = session.store.codec.encode(relative)
                row = session.store._visible_identity_occurrence(
                    generation,
                    namespace,
                    encoded_key,
                    encoded_path,
                )
                if row is None:
                    raise StoreIntegrityError(
                        "lazy-to-lazy identity lacks incarnation label"
                    )
                incarnation = IncarnationId(
                    session.store.store_identity, int(row[0])
                )
                session._registry.attach_existing(
                    incarnation,
                    Occurrence(namespace, key, relative),
                )
                incarnations.append(incarnation)
            if incarnations[0] != incarnations[1]:
                raise StoreIntegrityError(
                    "lazy-to-lazy link joins different incarnations"
                )
            cross.append((target, owner))
            continue

        namespace, key, relative, expected_type = (
            target_lazy if target_lazy is not None else owner_lazy
        )
        eager_path = owner if target_lazy is not None else target
        encoded_key = session.store.codec.encode(key)
        encoded_path = session.store.codec.encode(relative)
        row = session.store._visible_identity_occurrence(
            generation,
            namespace,
            encoded_key,
            encoded_path,
        )
        if row is None:
            raise StoreIntegrityError(
                "cross-boundary lazy identity lacks incarnation label"
            )
        eager_object = _at_path(
            session.world,
            eager_path,
            mutable_event_tail_only=True,
        )
        incarnation = IncarnationId(
            session.store.store_identity, int(row[0])
        )
        live = session._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, expected_type):
                raise StoreIntegrityError(
                    "cross-boundary incarnation has wrong live type"
                )
            if eager_object is not live:
                _relative_set(session.world, eager_path, live)
            eager_object = live
        else:
            if (
                namespace in {WALLET_NAMESPACE, TREASURY_NAMESPACE}
                and type(eager_object) is dict
            ):
                eager_object = LazyTrackedDict(eager_object)
                _relative_set(session.world, eager_path, eager_object)
            elif namespace == SOUL_NAMESPACE and relative:
                if relative in (
                    (("field", "authorities"),),
                    (("field", "marks"),),
                ) and type(eager_object) is set:
                    eager_object = LazySoulTrackedSet(eager_object)
                    _relative_set(session.world, eager_path, eager_object)
                elif (
                    relative == (("field", "cosmic_links"),)
                    and type(eager_object) is dict
                ):
                    eager_object = LazyTrackedDict(eager_object)
                    _relative_set(session.world, eager_path, eager_object)
                elif (
                    relative == (("field", "transformations"),)
                    and type(eager_object) is list
                ):
                    eager_object = LazySoulTrackedList(eager_object)
                    _relative_set(session.world, eager_path, eager_object)
            elif (
                namespace == LINEAGE_CHILD_NAMESPACE
                and not relative
                and type(eager_object) is set
            ):
                eager_object = LazyLineageTrackedSet(eager_object)
                eager_object._attach(
                    session.lineage_children, key
                )
                _relative_set(session.world, eager_path, eager_object)
            elif namespace == ADVANCEMENT_NAMESPACE and relative:
                # A lazy advancement descendant can share identity with a
                # still-eager owner. Built-in containers are not weakrefable,
                # so give the eager side the same tracking-capable runtime
                # wrapper that will later be attached when the path loads.
                if type(eager_object) is dict:
                    eager_object = LazyTrackedDict(eager_object)
                    _relative_set(session.world, eager_path, eager_object)
                elif type(eager_object) is list:
                    eager_object = LazySoulTrackedList(eager_object)
                    _relative_set(session.world, eager_path, eager_object)
                elif type(eager_object) is set:
                    eager_object = LazySoulTrackedSet(eager_object)
                    _relative_set(session.world, eager_path, eager_object)
            if not isinstance(eager_object, expected_type):
                raise StoreIntegrityError(
                    "cross-boundary lazy identity resolves to wrong type"
                )
            session._registry.bind(
                eager_object, incarnation=incarnation
            )
        session._registry.attach_existing(
            incarnation,
            Occurrence(namespace, key, relative),
        )
        if not relative and isinstance(eager_object, IndexedRecord):
            table = {
                PEOPLE_NAMESPACE: session.people,
                ASPIRATION_NAMESPACE: session.aspirations,
                RESOURCE_NAMESPACE: session.resources,
                MATERIAL_LOT_NAMESPACE: session.material_lots,
                MATERIAL_ITEM_NAMESPACE: session.material_items,
                SOUL_NAMESPACE: session.souls,
                ADVANCEMENT_NAMESPACE: session.advancement_paths,
                INSTITUTION_MAGIC_RECORD_NAMESPACE: session.institution_magic_records,
                INSTITUTION_NOTICE_NAMESPACE: session.institution_notices,
                INSTITUTION_APPLICATION_NAMESPACE: session.institution_applications,
                TRANSMISSION_NAMESPACE: session.transmissions,
                MOTIVE_NAMESPACE: session.motives,
                SOCIAL_EDGE_NAMESPACE: session.social_edges,
            }.get(namespace)
            if table is None:
                raise StoreIntegrityError(
                    "indexed lazy occurrence has no owning table"
                )
            object.__setattr__(
                eager_object, "_index_table", weakref.ref(table)
            )
            object.__setattr__(eager_object, "_index_key", key)
        cross.append((target, owner))
    return tuple(cross)


def _seed_cross_boundary_people_identity(session, links):
    # Compatibility alias retained for the existing people-focused tests.
    return tuple(
        link for link in _seed_cross_boundary_lazy_identity(session, links)
        if _path_under_people(link[0]) != _path_under_people(link[1])
    )


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
    tracker._excluded_namespaces = {
        PEOPLE_NAMESPACE,
        ASPIRATION_NAMESPACE,
        RESOURCE_NAMESPACE,
        OWNER_INDEX_NAMESPACE,
        MATERIAL_LOT_NAMESPACE,
        MATERIAL_ITEM_NAMESPACE,
        MATERIAL_LOT_INDEX_NAMESPACE,
        MATERIAL_ACTIVE_INDEX_NAMESPACE,
        WALLET_NAMESPACE,
        TREASURY_NAMESPACE,
        SOUL_NAMESPACE,
        ADVANCEMENT_NAMESPACE,
        INSTITUTION_MAGIC_RECORD_NAMESPACE,
        INSTITUTION_NOTICE_NAMESPACE,
        INSTITUTION_APPLICATION_NAMESPACE,
        TRANSMISSION_NAMESPACE,
        MOTIVE_NAMESPACE,
        SOCIAL_EDGE_NAMESPACE,
        SOCIAL_ADJACENCY_NAMESPACE,
        SOCIAL_PARTNERSHIP_NAMESPACE,
        SKILL_NAMESPACE,
        LINEAGE_NODE_NAMESPACE,
        LINEAGE_CHILD_NAMESPACE,
        GENEALOGY_PARENT_NAMESPACE,
        GENEALOGY_CHILD_NAMESPACE,
        COMMUNITY_MEMBERSHIP_NAMESPACE,
    }
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
    aspiration_version_changes: tuple[VersionChange, ...]
    aspiration_identity_changes: tuple[IdentityOccurrenceChange, ...]
    resource_version_changes: tuple[VersionChange, ...]
    resource_identity_changes: tuple[IdentityOccurrenceChange, ...]
    owner_index_version_changes: tuple[VersionChange, ...]
    owner_index_identity_changes: tuple[IdentityOccurrenceChange, ...]
    cold_plan: Any
    touched_keys: tuple[Any, ...]
    structural_keys: tuple[Any, ...]
    aspiration_touched_keys: tuple[Any, ...]
    aspiration_structural_keys: tuple[Any, ...]
    resource_touched_keys: tuple[Any, ...]
    resource_structural_keys: tuple[Any, ...]
    owner_index_touched_keys: tuple[Any, ...]
    owner_index_structural_keys: tuple[Any, ...]
    material_lot_version_changes: tuple[VersionChange, ...]
    material_lot_identity_changes: tuple[IdentityOccurrenceChange, ...]
    material_lot_touched_keys: tuple[Any, ...]
    material_lot_structural_keys: tuple[Any, ...]
    material_item_version_changes: tuple[VersionChange, ...]
    material_item_identity_changes: tuple[IdentityOccurrenceChange, ...]
    material_item_touched_keys: tuple[Any, ...]
    material_item_structural_keys: tuple[Any, ...]
    material_lot_index_version_changes: tuple[VersionChange, ...]
    material_lot_index_identity_changes: tuple[IdentityOccurrenceChange, ...]
    material_lot_index_touched_keys: tuple[Any, ...]
    material_lot_index_structural_keys: tuple[Any, ...]
    material_active_index_version_changes: tuple[VersionChange, ...]
    material_active_index_identity_changes: tuple[IdentityOccurrenceChange, ...]
    material_active_index_touched_keys: tuple[Any, ...]
    material_active_index_structural_keys: tuple[Any, ...]
    wallet_version_changes: tuple[VersionChange, ...]
    wallet_identity_changes: tuple[IdentityOccurrenceChange, ...]
    wallet_touched_keys: tuple[Any, ...]
    wallet_structural_keys: tuple[Any, ...]
    treasury_version_changes: tuple[VersionChange, ...]
    treasury_identity_changes: tuple[IdentityOccurrenceChange, ...]
    treasury_touched_keys: tuple[Any, ...]
    treasury_structural_keys: tuple[Any, ...]
    soul_version_changes: tuple[VersionChange, ...]
    soul_identity_changes: tuple[IdentityOccurrenceChange, ...]
    soul_touched_keys: tuple[Any, ...]
    soul_structural_keys: tuple[Any, ...]
    advancement_version_changes: tuple[VersionChange, ...]
    advancement_identity_changes: tuple[IdentityOccurrenceChange, ...]
    advancement_touched_keys: tuple[Any, ...]
    advancement_structural_keys: tuple[Any, ...]
    institution_magic_record_version_changes: tuple[VersionChange, ...]
    institution_magic_record_identity_changes: tuple[IdentityOccurrenceChange, ...]
    institution_magic_record_touched_keys: tuple[Any, ...]
    institution_magic_record_structural_keys: tuple[Any, ...]
    institution_notice_version_changes: tuple[VersionChange, ...]
    institution_notice_identity_changes: tuple[IdentityOccurrenceChange, ...]
    institution_notice_touched_keys: tuple[Any, ...]
    institution_notice_structural_keys: tuple[Any, ...]
    institution_application_version_changes: tuple[VersionChange, ...]
    institution_application_identity_changes: tuple[IdentityOccurrenceChange, ...]
    institution_application_touched_keys: tuple[Any, ...]
    institution_application_structural_keys: tuple[Any, ...]
    transmission_version_changes: tuple[VersionChange, ...]
    transmission_identity_changes: tuple[IdentityOccurrenceChange, ...]
    transmission_touched_keys: tuple[Any, ...]
    transmission_structural_keys: tuple[Any, ...]
    motive_version_changes: tuple[VersionChange, ...]
    motive_identity_changes: tuple[IdentityOccurrenceChange, ...]
    motive_touched_keys: tuple[Any, ...]
    motive_structural_keys: tuple[Any, ...]
    social_edge_version_changes: tuple[VersionChange, ...]
    social_edge_identity_changes: tuple[IdentityOccurrenceChange, ...]
    social_edge_touched_keys: tuple[Any, ...]
    social_edge_structural_keys: tuple[Any, ...]
    social_adjacency_version_changes: tuple[VersionChange, ...]
    social_adjacency_identity_changes: tuple[IdentityOccurrenceChange, ...]
    social_adjacency_touched_keys: tuple[Any, ...]
    social_adjacency_structural_keys: tuple[Any, ...]
    social_partnership_version_changes: tuple[VersionChange, ...]
    social_partnership_identity_changes: tuple[IdentityOccurrenceChange, ...]
    social_partnership_touched_keys: tuple[Any, ...]
    social_partnership_structural_keys: tuple[Any, ...]
    skill_version_changes: tuple[VersionChange, ...]
    skill_identity_changes: tuple[IdentityOccurrenceChange, ...]
    skill_touched_keys: tuple[Any, ...]
    skill_structural_keys: tuple[Any, ...]
    lineage_node_version_changes: tuple[VersionChange, ...]
    lineage_node_identity_changes: tuple[IdentityOccurrenceChange, ...]
    lineage_node_touched_keys: tuple[Any, ...]
    lineage_node_structural_keys: tuple[Any, ...]
    lineage_child_version_changes: tuple[VersionChange, ...]
    lineage_child_identity_changes: tuple[IdentityOccurrenceChange, ...]
    lineage_child_touched_keys: tuple[Any, ...]
    lineage_child_structural_keys: tuple[Any, ...]
    lineage_child_edge_version_changes: tuple[VersionChange, ...]
    genealogy_parent_version_changes: tuple[VersionChange, ...]
    genealogy_parent_identity_changes: tuple[IdentityOccurrenceChange, ...]
    genealogy_parent_touched_keys: tuple[Any, ...]
    genealogy_parent_structural_keys: tuple[Any, ...]
    genealogy_child_version_changes: tuple[VersionChange, ...]
    genealogy_child_identity_changes: tuple[IdentityOccurrenceChange, ...]
    genealogy_child_touched_keys: tuple[Any, ...]
    genealogy_child_structural_keys: tuple[Any, ...]
    community_membership_version_changes: tuple[VersionChange, ...]
    community_membership_identity_changes: tuple[IdentityOccurrenceChange, ...]
    community_membership_touched_keys: tuple[Any, ...]
    community_membership_structural_keys: tuple[Any, ...]
    layout_value: dict[str, Any] | None
    household_member_version_changes: tuple[VersionChange, ...] = ()


class LazyRecordTable(RecordTable):
    """RecordTable-compatible lazy people authority with a bounded clean cache."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = PEOPLE_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
        self._alive_query_cache = _StepAwareLRU(session)
        self._query_caches = (self._alive_query_cache,)
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
        # Membership lookups without a resident/dirty owner are one-shot
        # checked projections: do not cache either positive history or misses.
        # __getitem__ and save pin the necessary working-state sidecars.
        if key in self._baseline_presence:
            return self._baseline_presence[key]
        return self._store.contains_lazy_key(
            self._pin, self._namespace, key
        )

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

    def _cached_query_keys(self, cache, index_name, value):
        # Query memberships are immutable for one captured generation.
        # During Simulation.run, cache only that pinned baseline; unsaved
        # mutations are still overlaid by each table's touched-owner logic.
        if not getattr(self._session, "_hot_run_depth", 0):
            return self._store.query_keys(
                self._pin, self._namespace, index_name, value
            )
        cache_key = (
            self._pin.captured_head,
            index_name,
            self._store.codec.encode(value),
        )
        try:
            rows = cache.pop(cache_key)
        except KeyError:
            rows = self._store.query_keys(
                self._pin, self._namespace, index_name, value
            )
        # A single huge historical query result can evade the count cap.
        # Live positive-alive results are proportionate to actual active state.
        if len(rows) <= self._clean_limit or (
            index_name == "alive" and value is True
        ):
            cache[cache_key] = rows
        return rows

    def _prune_query_caches(self, epoch=None, *, retain_hot=False):
        for cache in getattr(self, "_query_caches", ()):
            if epoch is None:
                limit = self._clean_limit
            else:
                touched = cache.touched(epoch)
                touched.intersection_update(cache.keys())
                limit = (
                    max(self._clean_limit, len(touched))
                    if retain_hot
                    else self._clean_limit
                )
            while len(cache) > limit:
                cache.popitem(last=False)
            if epoch is not None:
                cache.finish_step(epoch)

    def _discard_clean_baseline(self, key):
        """Release historical sidecars once a clean record is no longer hot.

        The checked persisted link/incarnation authority is not modified.
        Retained external aliases keep live runtime incarnations registered.
        """
        if key in self._dirty or key in self._new_keys or key in self._reinserted:
            return
        for name in (
            "_baseline_payload",
            "_baseline_presence",
            "_baseline_incarnation",
            "_baseline_ordinal",
            "_baseline_identity_labels",
        ):
            cache = getattr(self, name, None)
            if cache is not None:
                cache.pop(key, None)

    def _evict_clean(self):
        tracker = getattr(self._session, "_eager_tracker", None)
        if tracker is not None and tracker._cold_step_depth:
            # During a real simulation step, repeated access to live working
            # state must not churn through SQLite merely because the ordinary
            # clean-cache cap is smaller than the active workload. The step
            # boundary prunes this back to the actual hot working set.
            return
        while len(self._lru) > self._clean_limit:
            key, _ = self._lru.popitem(last=False)
            if key in self._dirty:
                continue
            if dict.__contains__(self, key):
                dict.__delitem__(self, key)
            self._discard_clean_baseline(key)
        self._prune_query_caches()

    def _finish_simulation_step(self, epoch, *, retain_hot):
        touched = self._lru.touched(epoch)
        # Dirty owners are already pinned outside the clean LRU. During a
        # multi-year Simulation.run, retain at most the clean keys actually
        # used by this step (or the ordinary small-query cache, whichever is
        # larger). Direct one-step calls keep the original 256-entry bound.
        # Every clean access moves its key to the LRU tail, so untouched
        # prior-step state is evicted first and historical growth cannot
        # accumulate in the hot set.
        touched.intersection_update(self._lru.keys())
        limit = (
            max(self._clean_limit, len(touched))
            if retain_hot
            else self._clean_limit
        )
        while len(self._lru) > limit:
            key, _ = self._lru.popitem(last=False)
            if key in self._dirty:
                continue
            if dict.__contains__(self, key):
                dict.__delitem__(self, key)
            self._discard_clean_baseline(key)
        self._last_step_hot_entries = len(touched) if retain_hot else 0
        self._lru.finish_step(epoch)
        self._prune_query_caches(epoch, retain_hot=retain_hot)

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
            self._cached_query_keys(
                self._alive_query_cache, "alive", desired
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
        # Match RecordTable.ids exactly. The live simulation's current_people()
        # contract is stable increasing person ID, independent of persistence
        # insertion/structural ordinals. Reopen must not change floating-point
        # aggregation order or deterministic history.
        return tuple(sorted(baseline))

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
        for key in plan.touched_keys:
            if self._baseline_presence.get(key) is False:
                self._discard_clean_baseline(key)
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


class LazyAspirationTable(LazyRecordTable):
    """Bounded lazy mapping for scalar-only MagicAspiration records."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = ASPIRATION_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_ASPIRATION_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

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
            expected_record_schema=LAZY_ASPIRATION_SCHEMA,
        )
        if not isinstance(checked.value, MagicAspiration):
            raise StoreFormatError(
                "lazy aspiration payload is not MagicAspiration"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._session._bind_loaded_aspiration(
            key, checked.value
        )
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy aspiration"
            )
        if not dict.__contains__(self, key):
            incarnation = self._session._registry.incarnation_for_occurrence(
                self._session._aspiration_occurrence(key)
            )
            live = (
                None if incarnation is None
                else self._session._registry.object_for_incarnation(
                    incarnation
                )
            )
            if live is None or not isinstance(live, MagicAspiration):
                raise StoreIntegrityError(
                    "evicted aspiration lost its live incarnation"
                )
            dict.__setitem__(self, key, live)
            object.__setattr__(live, "_index_table", weakref.ref(self))
            object.__setattr__(live, "_index_key", key)
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, MagicAspiration):
            raise TypeError(
                "world.magic_resources.aspirations values "
                "must be MagicAspiration"
            )
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is record and currently_visible:
            return

        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)

        self._session._bind_assigned_aspiration(key, record)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_index_binding(old)
            self._session._detach_assigned_aspiration(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_aspiration(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

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
                            record_schema=LAZY_ASPIRATION_SCHEMA,
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

            record = dict.__getitem__(self, key)
            payload = self._store.codec.encode(record)
            incarnation = self._session._registry.incarnation_for_object(
                record
            )
            if incarnation is None:
                raise StoreIntegrityError(
                    "current lazy aspiration has no runtime incarnation"
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
                        record_schema=LAZY_ASPIRATION_SCHEMA,
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
        for key in plan.aspiration_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                record = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    record
                )
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
                        "committed aspiration lost collection order"
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
        return {
            "logical_aspirations": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_aspirations": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "aspiration_payload_loads": self._loads,
            "dirty_aspirations": len(self._dirty),
            "removed_aspirations": len(self._removed),
            "new_aspirations": len(self._new_keys),
            "reinserted_aspirations": len(self._reinserted),
        }



class LazyTrackedDict(dict):
    """Mutable dict that can dirty multiple lazy owners sharing one identity."""

    def __init__(self, values=()):
        dict.__init__(self, values)
        self._lazy_bindings = {}

    def _bindings(self):
        dead = []
        out = []
        for token, (table_ref, key) in self._lazy_bindings.items():
            table = table_ref()
            if table is None:
                dead.append(token)
            else:
                out.append((table, key))
        for token in dead:
            self._lazy_bindings.pop(token, None)
        return tuple(out)

    def _attach(self, table, key):
        self._lazy_bindings[(id(table), key)] = (weakref.ref(table), key)

    def _detach(self, table, key):
        self._lazy_bindings.pop((id(table), key), None)

    def _guard(self):
        bindings = self._bindings()
        for table, key in bindings:
            table._ensure_mutation()
            if not table._visible(key):
                raise StoreIntegrityError(
                    "tracked currency dict retained a non-current owner"
                )
        return bindings

    @staticmethod
    def _touch(bindings):
        for table, key in bindings:
            table.changed(key)

    def __setitem__(self, key, value):
        bindings = self._guard()
        before = self.get(key, object())
        dict.__setitem__(self, key, value)
        if before != value:
            self._touch(bindings)

    def __delitem__(self, key):
        bindings = self._guard()
        dict.__delitem__(self, key)
        self._touch(bindings)

    def clear(self):
        bindings = self._guard()
        if self:
            dict.clear(self)
            self._touch(bindings)

    def pop(self, key, *default):
        bindings = self._guard()
        if key not in self:
            if default:
                return default[0]
            raise KeyError(key)
        value = dict.pop(self, key)
        self._touch(bindings)
        return value

    def popitem(self):
        bindings = self._guard()
        value = dict.popitem(self)
        self._touch(bindings)
        return value

    def setdefault(self, key, default=None):
        if key in self:
            return dict.__getitem__(self, key)
        bindings = self._guard()
        dict.__setitem__(self, key, default)
        self._touch(bindings)
        return default

    def update(self, *args, **kwargs):
        incoming = dict(*args, **kwargs)
        bindings = self._guard()
        changed = any(
            key not in self or self[key] != value
            for key, value in incoming.items()
        )
        dict.update(self, incoming)
        if changed:
            self._touch(bindings)

    def __ior__(self, other):
        self.update(other)
        return self


class LazyTrackedSet(set):
    """Weakly bound integer set whose mutations dirty one lazy owner bucket."""

    def __init__(self, values, table, key):
        values = self._validate(values)
        set.__init__(self, values)
        self._table_ref = weakref.ref(table)
        self._key = key

    @staticmethod
    def _validate(values):
        values = set(values)
        if any(type(value) is not int for value in values):
            raise TypeError("magic resource owner index requires integer IDs")
        return values

    def _table(self):
        return None if self._table_ref is None else self._table_ref()

    def _guard(self):
        table = self._table()
        if table is not None:
            table._ensure_mutation()
        return table

    def _touch(self, table):
        if table is not None:
            table.changed(self._key)

    def _attach(self, table, key):
        self._table_ref = weakref.ref(table)
        self._key = key

    def _detach(self):
        self._table_ref = None
        self._key = None

    def add(self, value):
        table = self._guard()
        self._validate((value,))
        before = len(self)
        set.add(self, value)
        if len(self) != before:
            self._touch(table)

    def discard(self, value):
        table = self._guard()
        before = len(self)
        set.discard(self, value)
        if len(self) != before:
            self._touch(table)

    def remove(self, value):
        table = self._guard()
        set.remove(self, value)
        self._touch(table)

    def pop(self):
        table = self._guard()
        value = set.pop(self)
        self._touch(table)
        return value

    def clear(self):
        table = self._guard()
        if self:
            set.clear(self)
            self._touch(table)

    def update(self, *others):
        values = []
        for other in others:
            values.extend(other)
        self._validate(values)
        table = self._guard()
        before = set(self)
        set.update(self, *others)
        if self != before:
            self._touch(table)

    def intersection_update(self, *others):
        table = self._guard()
        before = set(self)
        set.intersection_update(self, *others)
        if self != before:
            self._touch(table)

    def difference_update(self, *others):
        table = self._guard()
        before = set(self)
        set.difference_update(self, *others)
        if self != before:
            self._touch(table)

    def symmetric_difference_update(self, other):
        self._validate(other)
        table = self._guard()
        before = set(self)
        set.symmetric_difference_update(self, other)
        if self != before:
            self._touch(table)

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


class LazyOwnerIndexTable(LazyRecordTable):
    """Bounded lazy owner -> resource-ID set mapping."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = OWNER_INDEX_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_OWNER_INDEX_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

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
            expected_record_schema=LAZY_OWNER_INDEX_SCHEMA,
        )
        if type(checked.value) is not set or any(
            type(item) is not int for item in checked.value
        ):
            raise StoreFormatError(
                "lazy owner-index payload is not an integer set"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        bucket = self._session._bind_loaded_owner_bucket(
            key, checked.value
        )
        dict.__setitem__(self, key, bucket)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return bucket

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current owner-index bucket"
            )
        if not dict.__contains__(self, key):
            self[key]
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, value):
        self._ensure_mutation()
        if not isinstance(value, (set, LazyTrackedSet)):
            raise TypeError("owner-index values must be sets")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is value and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not value:
            self._session._detach_assigned_owner_bucket(key, old)
        bucket = self._session._bind_assigned_owner_bucket(key, value)
        dict.__setitem__(self, key, bucket)

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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._session._detach_assigned_owner_bucket(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_owner_bucket(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

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
                            record_schema=LAZY_OWNER_INDEX_SCHEMA,
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

            bucket = dict.__getitem__(self, key)
            stored_value = set(bucket)
            payload = self._store.codec.encode(stored_value)
            incarnation = self._session._registry.incarnation_for_object(
                bucket
            )
            if incarnation is None:
                raise StoreIntegrityError(
                    "current owner-index bucket has no runtime incarnation"
                )
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new
                or reinsertion
                or payload != self._baseline_bytes(key)
            )
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        stored_value,
                        record_schema=LAZY_OWNER_INDEX_SCHEMA,
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
        for key in plan.owner_index_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                bucket = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    set(bucket)
                )
                incarnation = self._session._registry.incarnation_for_object(
                    bucket
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
                        "committed owner-index bucket lost collection order"
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
        return {
            "logical_owner_buckets": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_owner_buckets": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "owner_bucket_payload_loads": self._loads,
            "dirty_owner_buckets": len(self._dirty),
            "removed_owner_buckets": len(self._removed),
            "new_owner_buckets": len(self._new_keys),
            "reinserted_owner_buckets": len(self._reinserted),
        }


class LazyTrackedList(list):
    """Weakly bound list whose supported mutations dirty one lazy owner."""

    def __init__(self, values, table, key):
        list.__init__(self, values)
        self._table_ref = weakref.ref(table)
        self._key = key

    @staticmethod
    def _validate(values):
        values = list(values)
        if any(type(value) is not int for value in values):
            raise TypeError("MagicResource.transfers requires integer event IDs")
        return values

    def _table(self):
        return None if self._table_ref is None else self._table_ref()

    def _guard(self):
        table = self._table()
        if table is not None:
            table._ensure_mutation()
        return table

    def _touch(self, table):
        if table is not None:
            table.changed(self._key, "transfers")

    def _attach(self, table, key):
        self._table_ref = weakref.ref(table)
        self._key = key

    def _detach(self):
        self._table_ref = None
        self._key = None

    def append(self, value):
        table = self._guard()
        self._validate((value,))
        list.append(self, value)
        self._touch(table)

    def extend(self, values):
        values = self._validate(values)
        table = self._guard()
        list.extend(self, values)
        self._touch(table)

    def insert(self, index, value):
        table = self._guard()
        self._validate((value,))
        list.insert(self, index, value)
        self._touch(table)

    def __setitem__(self, index, value):
        table = self._guard()
        if isinstance(index, slice):
            value = self._validate(value)
        else:
            self._validate((value,))
        list.__setitem__(self, index, value)
        self._touch(table)

    def __delitem__(self, index):
        table = self._guard()
        list.__delitem__(self, index)
        self._touch(table)

    def pop(self, index=-1):
        table = self._guard()
        value = list.pop(self, index)
        self._touch(table)
        return value

    def remove(self, value):
        table = self._guard()
        list.remove(self, value)
        self._touch(table)

    def clear(self):
        table = self._guard()
        if self:
            list.clear(self)
            self._touch(table)

    def reverse(self):
        table = self._guard()
        list.reverse(self)
        self._touch(table)

    def sort(self, *args, **kwargs):
        table = self._guard()
        list.sort(self, *args, **kwargs)
        self._touch(table)

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        table = self._guard()
        list.__imul__(self, count)
        self._touch(table)
        return self


class LazySocialEdgeTable(LazyRecordTable):
    """Bounded lazy Relationship authority with endpoint memberships."""

    _history_path = (("field", "shared_history"),)

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = SOCIAL_EDGE_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
        self._person_query_cache = _StepAwareLRU(session)
        self._query_caches = (self._person_query_cache,)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_identity_labels = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}
        self._pending_history_old = {}
        # Unsaved social-edge changes are indexed by endpoint so person-scoped
        # queries overlay only relevant touched edges instead of scanning every
        # touched relationship accumulated since the last save.
        self._touched_by_person = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_SOCIAL_EDGE_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _baseline_labels(self, key):
        if key not in self._baseline_identity_labels:
            self._baseline_identity_labels[key] = dict(
                self._store.identity_occurrences_for_owner(
                    self._pin, self._namespace, key
                )
            )
        return dict(self._baseline_identity_labels[key])

    @staticmethod
    def _plain(record):
        return replace(record, shared_history=list(record.shared_history))

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
            expected_record_schema=LAZY_SOCIAL_EDGE_SCHEMA,
        )
        if not isinstance(checked.value, Relationship):
            raise StoreFormatError(
                "lazy social edge payload is not Relationship"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._session._bind_loaded_social_edge(
            key, checked.value
        )
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def _index_touched_edge(self, key):
        people = set(key if type(key) is tuple else ())
        if dict.__contains__(self, key):
            record = dict.__getitem__(self, key)
            people.update((record.a, record.b))
        for person in people:
            self._touched_by_person.setdefault(person, set()).add(key)

    def preflight_change(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current social relationship"
            )
        if field == "shared_history":
            live = (
                dict.__getitem__(self, key)
                if dict.__contains__(self, key)
                else self._session._live_social_edge_for_key(key)
            )
            if live is not None:
                self._pending_history_old[key] = live.shared_history

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current social relationship"
            )
        if not dict.__contains__(self, key):
            self[key]
        record = dict.__getitem__(self, key)
        if field == "shared_history" and key in self._pending_history_old:
            old = self._pending_history_old.pop(key)
            if old is not record.shared_history:
                self._session._replace_social_history(
                    key, record, old, record.shared_history
                )
        self._dirty.add(key)
        self._index_touched_edge(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, Relationship):
            raise TypeError("world.social.edges values must be Relationship")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is record and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)
            self._session._detach_assigned_social_edge(key, old)
        record = self._session._bind_assigned_social_edge(key, record)
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
        self._index_touched_edge(key)
        self._lru.pop(key, None)

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_index_binding(old)
            self._session._detach_assigned_social_edge(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_social_edge(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)
        self._index_touched_edge(key)

    def _memberships(self, record, ordinal):
        return tuple(
            Membership("person", person, ordinal)
            for person in dict.fromkeys((record.a, record.b))
        )

    def ids_for_person(self, person):
        self._ensure()
        baseline = set(
            self._cached_query_keys(
                self._person_query_cache, "person", person
            )
        )
        touched = self._touched_by_person.get(person, ())
        baseline.difference_update(touched)
        for key in touched:
            if not self._visible(key):
                continue
            record = dict.__getitem__(self, key)
            if person in (record.a, record.b):
                baseline.add(key)
        return tuple(sorted(baseline, key=self._current_ordinal))

    def for_person(self, person):
        return [self[key] for key in self.ids_for_person(person)]

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
            baseline_labels = (
                self._baseline_labels(key) if baseline_exists else {}
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_SOCIAL_EDGE_SCHEMA,
                        )
                    )
                    for path in baseline_labels:
                        identity_changes.append(
                            IdentityOccurrenceChange(
                                self._namespace, key, path, delete=True
                            )
                        )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue
            record = dict.__getitem__(self, key)
            stored = self._plain(record)
            payload = self._store.codec.encode(stored)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new or reinsertion or payload != self._baseline_bytes(key)
            )
            ordinal = (
                structural_ordinals[key]
                if is_new or reinsertion
                else self._persisted_ordinal(key)
            )
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        stored,
                        record_schema=LAZY_SOCIAL_EDGE_SCHEMA,
                        memberships=self._memberships(record, ordinal),
                        reinsertion=reinsertion,
                    )
                )
            current_labels = (
                self._session._social_edge_incarnation_labels(key, record)
            )
            identity_changed = False
            for path in sorted(
                set(baseline_labels) | set(current_labels),
                key=self._store.codec.encode,
            ):
                before = baseline_labels.get(path)
                after = current_labels.get(path)
                if before == after:
                    continue
                identity_changed = True
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        path,
                        delete=after is None,
                        incarnation_id=after,
                    )
                )
            if value_changed or identity_changed:
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
        for key in plan.social_edge_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                record = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    self._plain(record)
                )
                labels = self._session._social_edge_incarnation_labels(
                    key, record
                )
                self._baseline_identity_labels[key] = labels
                self._baseline_incarnation[key] = labels.get(())
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed social edge lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_identity_labels.pop(key, None)
                self._baseline_incarnation[key] = None
                self._baseline_ordinal.pop(key, None)
        self._dirty.clear()
        self._removed.clear()
        self._new_keys.clear()
        self._reinserted.clear()
        self._overlay_ordinals.clear()
        self._pending_history_old.clear()
        self._touched_by_person.clear()
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        return {
            "logical_social_edges": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_social_edges": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "social_edge_payload_loads": self._loads,
            "dirty_social_edges": len(self._dirty),
        }


class LazySocialAdjacencyTable(LazyRecordTable):
    """Bounded lazy person -> neighbor-set authority."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = SOCIAL_ADJACENCY_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_SOCIAL_ADJACENCY_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

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
            expected_record_schema=LAZY_SOCIAL_ADJACENCY_SCHEMA,
        )
        if type(checked.value) is not set or any(
            type(item) is not int for item in checked.value
        ):
            raise StoreFormatError(
                "lazy social adjacency payload is not an integer set"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        bucket = self._session._bind_loaded_social_adjacency(
            key, checked.value
        )
        dict.__setitem__(self, key, bucket)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return bucket

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current social adjacency"
            )
        if not dict.__contains__(self, key):
            self[key]
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, value):
        self._ensure_mutation()
        if not isinstance(value, (set, LazyTrackedSet)):
            raise TypeError("social adjacency values must be sets")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is value and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not value:
            self._session._detach_assigned_social_adjacency(key, old)
        bucket = self._session._bind_assigned_social_adjacency(key, value)
        dict.__setitem__(self, key, bucket)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._session._detach_assigned_social_adjacency(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_social_adjacency(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
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
                            record_schema=LAZY_SOCIAL_ADJACENCY_SCHEMA,
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
            bucket = dict.__getitem__(self, key)
            stored = set(bucket)
            payload = self._store.codec.encode(stored)
            incarnation = self._session._registry.incarnation_for_object(
                bucket
            )
            if incarnation is None:
                raise StoreIntegrityError(
                    "current social adjacency lacks runtime incarnation"
                )
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
                        stored,
                        record_schema=LAZY_SOCIAL_ADJACENCY_SCHEMA,
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
        for key in plan.social_adjacency_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                bucket = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    set(bucket)
                )
                incarnation = self._session._registry.incarnation_for_object(
                    bucket
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
                        "committed social adjacency lost collection order"
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
        return {
            "logical_social_adjacency": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_social_adjacency": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "social_adjacency_payload_loads": self._loads,
            "dirty_social_adjacency": len(self._dirty),
        }


class LazySocialPartnershipTable(LazyRecordTable):
    """Bounded lazy pair -> formation-event authority."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = SOCIAL_PARTNERSHIP_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
        self._person_query_cache = _StepAwareLRU(session)
        self._query_caches = (self._person_query_cache,)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}
        self._touched_by_person = {}

    def _mark_touched_pair(self, key):
        for person in dict.fromkeys(key):
            self._touched_by_person.setdefault(person, set()).add(key)

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_SOCIAL_PARTNERSHIP_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

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
            expected_record_schema=LAZY_SOCIAL_PARTNERSHIP_SCHEMA,
        )
        if type(checked.value) is not int:
            raise StoreFormatError(
                "lazy social partnership payload is not an event ID"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        dict.__setitem__(self, key, checked.value)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return checked.value

    def __setitem__(self, key, event_id):
        self._ensure_mutation()
        if (
            type(key) is not tuple
            or len(key) != 2
            or any(type(pid) is not int for pid in key)
            or type(event_id) is not int
        ):
            raise TypeError(
                "social partnerships require (int,int) -> int"
            )
        baseline_exists = self._baseline_exists(key)
        was_removed = key in self._removed
        dict.__setitem__(self, key, event_id)
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
        self._mark_touched_pair(key)
        self._lru.pop(key, None)

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        if dict.__contains__(self, key):
            dict.__delitem__(self, key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)
        self._mark_touched_pair(key)

    @staticmethod
    def _memberships(key, ordinal):
        return tuple(
            Membership("person", person, ordinal)
            for person in dict.fromkeys(key)
        )

    def ids_for_person(self, person):
        self._ensure()
        baseline = set(
            self._cached_query_keys(
                self._person_query_cache, "person", person
            )
        )
        touched = self._touched_by_person.get(person, ())
        baseline.difference_update(touched)
        for key in touched:
            if self._visible(key):
                baseline.add(key)
        return tuple(sorted(baseline, key=self._current_ordinal))

    def for_people(self, people):
        self._ensure()
        pairs = set()
        for person in people:
            pairs.update(self.ids_for_person(person))
        pairs = {
            pair for pair in pairs
            if pair[0] in people and pair[1] in people
        }
        return {
            pair: self[pair]
            for pair in sorted(pairs, key=self._current_ordinal)
        }

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
        )
        structural_ordinals = self._planned_structural_ordinals()
        version_changes = []
        effective_keys = []
        structural_keys = []
        for key in touched:
            baseline_exists = self._baseline_exists(key)
            visible = self._visible(key)
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_SOCIAL_PARTNERSHIP_SCHEMA,
                        )
                    )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue
            event_id = dict.__getitem__(self, key)
            payload = self._store.codec.encode(event_id)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new or reinsertion or payload != self._baseline_bytes(key)
            )
            ordinal = (
                structural_ordinals[key]
                if is_new or reinsertion
                else self._persisted_ordinal(key)
            )
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        event_id,
                        record_schema=LAZY_SOCIAL_PARTNERSHIP_SCHEMA,
                        memberships=self._memberships(key, ordinal),
                        reinsertion=reinsertion,
                    )
                )
            if value_changed:
                effective_keys.append(key)
            if is_new or reinsertion:
                structural_keys.append(key)
        return (
            tuple(version_changes),
            (),
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
        for key in plan.social_partnership_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                value = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(value)
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed social partnership lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_ordinal.pop(key, None)
        self._dirty.clear()
        self._removed.clear()
        self._new_keys.clear()
        self._reinserted.clear()
        self._overlay_ordinals.clear()
        self._touched_by_person.clear()
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        return {
            "logical_social_partnerships": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_social_partnerships": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "social_partnership_payload_loads": self._loads,
            "dirty_social_partnerships": len(self._dirty),
        }


class LazyCommunityMembershipTable(LazyRecordTable):
    """Bounded lazy (person, community) -> strength authority."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = COMMUNITY_MEMBERSHIP_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_COMMUNITY_MEMBERSHIP_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

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
            expected_record_schema=LAZY_COMMUNITY_MEMBERSHIP_SCHEMA,
        )
        if type(checked.value) not in (int, float):
            raise StoreFormatError(
                "lazy community membership payload is not numeric"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        dict.__setitem__(self, key, checked.value)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return checked.value

    def __setitem__(self, key, strength):
        self._ensure_mutation()
        if (
            type(key) is not tuple
            or len(key) != 2
            or any(type(part) is not int for part in key)
            or type(strength) not in (int, float)
        ):
            raise TypeError(
                "community memberships require (int,int) -> numeric strength"
            )
        baseline_exists = self._baseline_exists(key)
        was_removed = key in self._removed
        dict.__setitem__(self, key, strength)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        if dict.__contains__(self, key):
            dict.__delitem__(self, key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    @staticmethod
    def _memberships(key, ordinal):
        return (Membership("person", key[0], ordinal),)

    def keys_for_person(self, person):
        self._ensure()
        # query_keys is already ordered by the persisted membership ordinal,
        # which is the semantic insertion order for CommunityState. Preserve
        # that order directly. Collection-order rows may be written in a
        # different batching order and must not redefine simulation history.
        baseline = [
            key for key in self._store.query_keys(
                self._pin, self._namespace, "person", person
            )
            if key not in self._removed and key not in self._reinserted
        ]
        appended = [
            key
            for key in (self._new_keys | self._reinserted)
            if key not in self._removed and key[0] == person
        ]
        appended.sort(key=lambda key: self._overlay_ordinals[key])
        return tuple(baseline + appended)

    def for_person(self, person):
        return {
            key[1]: self[key]
            for key in self.keys_for_person(person)
        }

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
        )
        structural_ordinals = self._planned_structural_ordinals()
        version_changes = []
        effective_keys = []
        structural_keys = []
        for key in touched:
            baseline_exists = self._baseline_exists(key)
            visible = self._visible(key)
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_COMMUNITY_MEMBERSHIP_SCHEMA,
                        )
                    )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue
            strength = dict.__getitem__(self, key)
            payload = self._store.codec.encode(strength)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new or reinsertion or payload != self._baseline_bytes(key)
            )
            ordinal = (
                structural_ordinals[key]
                if is_new or reinsertion
                else self._persisted_ordinal(key)
            )
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        strength,
                        record_schema=LAZY_COMMUNITY_MEMBERSHIP_SCHEMA,
                        memberships=self._memberships(key, ordinal),
                        reinsertion=reinsertion,
                    )
                )
                effective_keys.append(key)
            if is_new or reinsertion:
                structural_keys.append(key)
        return (
            tuple(version_changes),
            (),
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
        for key in plan.community_membership_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                value = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(value)
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed community membership lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
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
        return {
            "logical_community_memberships": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_community_memberships": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "community_membership_payload_loads": self._loads,
            "dirty_community_memberships": len(self._dirty),
        }


class LazyResourceTable(LazyRecordTable):
    """Bounded lazy mapping for MagicResource owner records."""

    _transfer_path = (("field", "transfers"),)

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = RESOURCE_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_identity_labels = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}
        self._pending_transfer_old = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_RESOURCE_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _baseline_labels(self, key):
        if key not in self._baseline_identity_labels:
            self._baseline_identity_labels[key] = dict(
                self._store.identity_occurrences_for_owner(
                    self._pin, self._namespace, key
                )
            )
        return dict(self._baseline_identity_labels[key])

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
            expected_record_schema=LAZY_RESOURCE_SCHEMA,
        )
        if not isinstance(checked.value, MagicResource):
            raise StoreFormatError(
                "lazy resource payload is not MagicResource"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._session._bind_loaded_resource(
            key, checked.value
        )
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def preflight_change(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy resource"
            )
        if field == "transfers":
            live = (
                dict.__getitem__(self, key)
                if dict.__contains__(self, key)
                else self._session._live_resource_for_key(key)
            )
            if live is not None:
                self._pending_transfer_old[key] = live.transfers

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy resource"
            )
        if not dict.__contains__(self, key):
            # A retained child alias can outlive the cached parent. Reloading
            # reuses the child's persisted incarnation and restores ownership.
            self[key]
        record = dict.__getitem__(self, key)
        if field == "transfers" and key in self._pending_transfer_old:
            old = self._pending_transfer_old.pop(key)
            if old is not record.transfers:
                self._session._replace_resource_transfers(
                    key, record, old, record.transfers
                )
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, MagicResource):
            raise TypeError(
                "world.magic_resources.resources values must be MagicResource"
            )
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is record and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)
            self._session._detach_assigned_resource(key, old)

        record = self._session._bind_assigned_resource(key, record)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_index_binding(old)
            self._session._detach_assigned_resource(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_resource(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    def _overlay_memberships(self, resource, ordinal):
        return tuple(
            Membership(name, value, member_ordinal)
            for name, value, member_ordinal
            in _resource_memberships(resource, ordinal)
        )

    def ids(self, index_name, value):
        self._ensure()
        if index_name not in {"owner", "owner_kind"}:
            raise StoreError("unsupported lazy resource membership query")
        baseline = set(
            self._store.query_keys(
                self._pin, self._namespace, index_name, value
            )
        )
        touched = self._effective_touched()
        baseline.difference_update(touched)
        for key in touched:
            if not self._visible(key):
                continue
            record = dict.__getitem__(self, key)
            ordinal = self._current_ordinal(key)
            current = {
                (member.index_name, member.value)
                for member in self._overlay_memberships(
                    record, ordinal
                )
            }
            if (index_name, value) in current:
                baseline.add(key)
        return tuple(sorted(baseline, key=self._current_ordinal))

    def owner_ids(self, owner_kind, owner_id):
        return self.ids("owner", (owner_kind, owner_id))

    def owner_kind_ids(self, owner_kind):
        return self.ids("owner_kind", owner_kind)

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
            baseline_labels = (
                self._baseline_labels(key) if baseline_exists else {}
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_RESOURCE_SCHEMA,
                        )
                    )
                    for path in baseline_labels:
                        identity_changes.append(
                            IdentityOccurrenceChange(
                                self._namespace,
                                key,
                                path,
                                delete=True,
                            )
                        )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue

            record = dict.__getitem__(self, key)
            stored_record = _plain_resource_value(record)
            payload = self._store.codec.encode(stored_record)
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
                        stored_record,
                        record_schema=LAZY_RESOURCE_SCHEMA,
                        memberships=self._overlay_memberships(
                            record, ordinal
                        ),
                        reinsertion=reinsertion,
                    )
                )

            current_labels = (
                self._session._resource_incarnation_labels(key, record)
            )
            all_paths = set(baseline_labels) | set(current_labels)
            identity_changed = False
            for path in sorted(
                all_paths, key=self._store.codec.encode
            ):
                before = baseline_labels.get(path)
                after = current_labels.get(path)
                if before == after:
                    continue
                identity_changed = True
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        path,
                        delete=after is None,
                        incarnation_id=after,
                    )
                )

            if value_changed or identity_changed:
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
        for key in plan.resource_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                record = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    _plain_resource_value(record)
                )
                self._baseline_identity_labels[key] = (
                    self._session._resource_incarnation_labels(
                        key, record
                    )
                )
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed resource lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_identity_labels.pop(key, None)
                self._baseline_ordinal.pop(key, None)
        self._dirty.clear()
        self._removed.clear()
        self._new_keys.clear()
        self._reinserted.clear()
        self._overlay_ordinals.clear()
        self._pending_transfer_old.clear()
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        return {
            "logical_resources": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_resources": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "resource_payload_loads": self._loads,
            "dirty_resources": len(self._dirty),
            "removed_resources": len(self._removed),
            "new_resources": len(self._new_keys),
            "reinserted_resources": len(self._reinserted),
        }



class LazyTrackedIdList(list):
    """Weakly bound integer list used by lazy material index buckets."""

    def __init__(self, values, table, key):
        values = self._validate(values)
        list.__init__(self, values)
        self._table_ref = weakref.ref(table)
        self._key = key

    @staticmethod
    def _validate(values):
        values = list(values)
        if any(type(value) is not int for value in values):
            raise TypeError("tracked material index requires integer IDs")
        return values

    def _table(self):
        return None if self._table_ref is None else self._table_ref()

    def _guard(self):
        table = self._table()
        if table is not None:
            table._ensure_mutation()
        return table

    def _touch(self, table):
        if table is not None:
            table.changed(self._key)

    def _attach(self, table, key):
        self._table_ref = weakref.ref(table)
        self._key = key

    def _detach(self):
        self._table_ref = None
        self._key = None

    def append(self, value):
        table = self._guard()
        self._validate((value,))
        list.append(self, value)
        self._touch(table)

    def extend(self, values):
        values = self._validate(values)
        table = self._guard()
        list.extend(self, values)
        self._touch(table)

    def insert(self, index, value):
        table = self._guard()
        self._validate((value,))
        list.insert(self, index, value)
        self._touch(table)

    def __setitem__(self, index, value):
        table = self._guard()
        if isinstance(index, slice):
            value = self._validate(value)
        else:
            self._validate((value,))
        list.__setitem__(self, index, value)
        self._touch(table)

    def __delitem__(self, index):
        table = self._guard()
        list.__delitem__(self, index)
        self._touch(table)

    def pop(self, index=-1):
        table = self._guard()
        value = list.pop(self, index)
        self._touch(table)
        return value

    def remove(self, value):
        table = self._guard()
        list.remove(self, value)
        self._touch(table)

    def clear(self):
        table = self._guard()
        if self:
            list.clear(self)
            self._touch(table)

    def reverse(self):
        table = self._guard()
        list.reverse(self)
        self._touch(table)

    def sort(self, *args, **kwargs):
        table = self._guard()
        list.sort(self, *args, **kwargs)
        self._touch(table)

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        table = self._guard()
        list.__imul__(self, count)
        self._touch(table)
        return self


class _LazySimpleMaterialObjectTable(LazyRecordTable):
    """Shared bounded mapping behavior for top-level material object records."""

    _record_type = object
    _record_schema = 0
    _touched_attr = ""
    _label = "material record"

    def __init__(self, session, namespace, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = namespace
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=self._record_schema,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _bind_loaded_record(self, key, record):
        raise NotImplementedError

    def _bind_assigned_record(self, key, record):
        raise NotImplementedError

    def _detach_assigned_record(self, key, record):
        raise NotImplementedError

    def _detach_unloaded_record(self, key):
        raise NotImplementedError

    def _memberships(self, record, ordinal):
        return ()

    def _index_name(self, fields):
        raise StoreError(f"{self._label} has no persistent query index")

    def ids(self, fields, *values):
        self._ensure()
        index_name = self._index_name(fields)
        index_value = values[0] if len(values) == 1 else tuple(values)
        baseline = set(
            self._store.query_keys(
                self._pin, self._namespace, index_name, index_value
            )
        )
        touched = self._effective_touched()
        baseline.difference_update(touched)
        for key in touched:
            if not self._visible(key):
                continue
            record = dict.__getitem__(self, key)
            ordinal = self._current_ordinal(key)
            memberships = {
                (member.index_name, member.value)
                for member in self._memberships(record, ordinal)
            }
            if (index_name, index_value) in memberships:
                baseline.add(key)
        return tuple(sorted(baseline))

    def select(self, fields, *values):
        return [self[key] for key in self.ids(fields, *values)]

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
            expected_record_schema=self._record_schema,
        )
        if not isinstance(checked.value, self._record_type):
            raise StoreFormatError(
                f"lazy {self._label} payload has wrong type"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._bind_loaded_record(key, checked.value)
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                f"mutation notification has no current lazy {self._label}"
            )
        if not dict.__contains__(self, key):
            self[key]
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, self._record_type):
            raise TypeError(f"{self._label} value has wrong type")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is record and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)
            self._detach_assigned_record(key, old)
        record = self._bind_assigned_record(key, record)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_index_binding(old)
            self._detach_assigned_record(key, old)
            dict.__delitem__(self, key)
        else:
            self._detach_unloaded_record(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

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
                            record_schema=self._record_schema,
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
            record = dict.__getitem__(self, key)
            payload = self._store.codec.encode(record)
            incarnation = self._session._registry.incarnation_for_object(
                record
            )
            if incarnation is None:
                raise StoreIntegrityError(
                    f"current lazy {self._label} has no runtime incarnation"
                )
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new or reinsertion or payload != self._baseline_bytes(key)
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
                        record_schema=self._record_schema,
                        memberships=self._memberships(record, ordinal),
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
        for key in getattr(plan, self._touched_attr):
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
                        f"committed {self._label} lost collection order"
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
        return {
            "logical_records": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_records": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "payload_loads": self._loads,
            "dirty_records": len(self._dirty),
            "removed_records": len(self._removed),
            "new_records": len(self._new_keys),
            "reinserted_records": len(self._reinserted),
        }


class LazyMaterialItemTable(_LazySimpleMaterialObjectTable):
    _record_type = CraftedItem
    _record_schema = LAZY_MATERIAL_ITEM_SCHEMA
    _touched_attr = "material_item_touched_keys"
    _label = "crafted item"

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session, MATERIAL_ITEM_NAMESPACE, clean_limit=clean_limit
        )

    def _bind_loaded_record(self, key, record):
        return self._session._bind_loaded_material_item(key, record)

    def _bind_assigned_record(self, key, record):
        return self._session._bind_assigned_material_item(key, record)

    def _detach_assigned_record(self, key, record):
        self._session._detach_assigned_material_item(key, record)

    def _detach_unloaded_record(self, key):
        self._session._detach_unloaded_material_item(key)


class _LazyInstitutionRecordTable(_LazySimpleMaterialObjectTable):
    """Shared bounded RecordTable-compatible institution record storage."""

    _index_fields = {}

    def __init__(self, session, namespace, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(session, namespace, clean_limit=clean_limit)
        # Unsaved institution records can grow large between checkpoints.
        # Keep an incremental candidate index so indexed lookups examine only
        # touched records that could match instead of rebuilding memberships
        # for every touched record on every query.
        self._touched_membership_index = {}
        self._overlay_query_checks = 0

    def _index_touched_memberships(self, key, record):
        for member in self._memberships(record, 0):
            bucket = self._touched_membership_index.setdefault(
                (member.index_name, member.value), set()
            )
            bucket.add(key)

    def ids(self, fields, *values):
        self._ensure()
        index_name = self._index_name(fields)
        index_value = values[0] if len(values) == 1 else tuple(values)
        baseline = set(
            self._store.query_keys(
                self._pin, self._namespace, index_name, index_value
            )
        )
        touched = self._effective_touched()
        baseline.difference_update(touched)
        candidates = self._touched_membership_index.get(
            (index_name, index_value), ()
        )
        for key in candidates:
            self._overlay_query_checks += 1
            if key not in touched or not self._visible(key):
                continue
            record = dict.__getitem__(self, key)
            memberships = {
                (member.index_name, member.value)
                for member in self._memberships(record, 0)
            }
            if (index_name, index_value) in memberships:
                baseline.add(key)
        return tuple(sorted(baseline))

    def changed(self, key, field=None):
        super().changed(key, field)
        if self._visible(key):
            self._index_touched_memberships(
                key, dict.__getitem__(self, key)
            )

    def __setitem__(self, key, record):
        super().__setitem__(key, record)
        if self._visible(key):
            self._index_touched_memberships(
                key, dict.__getitem__(self, key)
            )

    def accept_save(self, plan, new_pin):
        super().accept_save(plan, new_pin)
        self._touched_membership_index.clear()

    def diagnostics(self):
        result = super().diagnostics()
        result["overlay_query_checks"] = self._overlay_query_checks
        result["touched_membership_buckets"] = len(
            self._touched_membership_index
        )
        return result

    def _bind_loaded_record(self, key, record):
        return self._session._bind_loaded_institution_record(
            self, self._namespace, key, record, self._record_type
        )

    def _bind_assigned_record(self, key, record):
        return self._session._bind_assigned_institution_record(
            self, self._namespace, key, record
        )

    def _detach_assigned_record(self, key, record):
        self._session._detach_assigned_institution_record(
            self, self._namespace, key, record
        )

    def _detach_unloaded_record(self, key):
        self._session._detach_unloaded_institution_record(
            self, self._namespace, key
        )

    def _memberships(self, record, ordinal):
        return tuple(
            Membership(name, value, member_ordinal)
            for name, value, member_ordinal
            in _institution_memberships(
                self._namespace, record, ordinal
            )
        )

    def _index_name(self, fields):
        normalized = (fields,) if isinstance(fields, str) else tuple(fields)
        try:
            return self._index_fields[normalized]
        except KeyError as exc:
            raise StoreError(
                f"unsupported {self._label} membership query: {normalized!r}"
            ) from exc


class LazyInstitutionMagicRecordTable(_LazyInstitutionRecordTable):
    _record_type = MagicUserRecord
    _record_schema = LAZY_INSTITUTION_MAGIC_RECORD_SCHEMA
    _touched_attr = "institution_magic_record_touched_keys"
    _label = "institution magic record"
    _index_fields = {
        ("person",): "person",
    }

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session,
            INSTITUTION_MAGIC_RECORD_NAMESPACE,
            clean_limit=clean_limit,
        )


class LazyInstitutionNoticeTable(_LazyInstitutionRecordTable):
    _record_type = AdventureNotice
    _record_schema = LAZY_INSTITUTION_NOTICE_SCHEMA
    _touched_attr = "institution_notice_touched_keys"
    _label = "institution notice"
    _index_fields = {
        ("status",): "status",
        ("cause_event",): "cause_event",
    }

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session,
            INSTITUTION_NOTICE_NAMESPACE,
            clean_limit=clean_limit,
        )


class LazyInstitutionApplicationTable(_LazyInstitutionRecordTable):
    _record_type = SocietyApplication
    _record_schema = LAZY_INSTITUTION_APPLICATION_SCHEMA
    _touched_attr = "institution_application_touched_keys"
    _label = "institution application"
    _index_fields = {
        ("passed",): "passed",
        ("person", "society"): "person_society",
        ("person", "society", "passed"): "person_society_passed",
    }

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session,
            INSTITUTION_APPLICATION_NAMESPACE,
            clean_limit=clean_limit,
        )


class LazyTransmissionRecordTable(_LazyInstitutionRecordTable):
    _record_type = Transmission
    _record_schema = LAZY_TRANSMISSION_SCHEMA
    _touched_attr = "transmission_touched_keys"
    _label = "transmission record"
    _index_fields = {
        ("item_kind", "item_id"): "item",
    }

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session, TRANSMISSION_NAMESPACE, clean_limit=clean_limit
        )


class LazyMotiveTable(_LazyInstitutionRecordTable):
    _record_type = MotiveState
    _record_schema = LAZY_MOTIVE_SCHEMA
    _touched_attr = "motive_touched_keys"
    _label = "motive"

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session, MOTIVE_NAMESPACE, clean_limit=clean_limit
        )


class LazyLineageNodeTable(_LazyInstitutionRecordTable):
    _record_type = LineageNode
    _record_schema = LAZY_LINEAGE_NODE_SCHEMA
    _touched_attr = "lineage_node_touched_keys"
    _label = "lineage node"

    def _memberships(self, record, ordinal):
        del record, ordinal
        return ()

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session, LINEAGE_NODE_NAMESPACE, clean_limit=clean_limit
        )


class LazyGenealogyParentTable(LazyRecordTable):
    """Bounded lazy child -> immutable parent tuple authority."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = GENEALOGY_PARENT_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_GENEALOGY_PARENT_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

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
            expected_record_schema=LAZY_GENEALOGY_PARENT_SCHEMA,
        )
        value = checked.value
        if type(value) is not tuple or any(
            type(parent) is not int for parent in value
        ):
            raise StoreFormatError(
                "lazy genealogy parent payload is not an integer tuple"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(value)
        )
        self._baseline_presence.setdefault(key, True)
        dict.__setitem__(self, key, value)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return value

    def __setitem__(self, key, value):
        self._ensure_mutation()
        if (
            type(key) is not int
            or type(value) is not tuple
            or any(type(parent) is not int for parent in value)
        ):
            raise TypeError(
                "genealogy parents require int -> tuple[int,...]"
            )
        baseline_exists = self._baseline_exists(key)
        was_removed = key in self._removed
        dict.__setitem__(self, key, value)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        if dict.__contains__(self, key):
            dict.__delitem__(self, key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
        )
        version_changes = []
        effective_keys = []
        structural_keys = []
        for key in touched:
            baseline_exists = self._baseline_exists(key)
            visible = self._visible(key)
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_GENEALOGY_PARENT_SCHEMA,
                        )
                    )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue
            value = dict.__getitem__(self, key)
            payload = self._store.codec.encode(value)
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
                        value,
                        record_schema=LAZY_GENEALOGY_PARENT_SCHEMA,
                        reinsertion=reinsertion,
                    )
                )
                effective_keys.append(key)
            if is_new or reinsertion:
                structural_keys.append(key)
        return (
            tuple(version_changes),
            (),
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
        for key in plan.genealogy_parent_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                value = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(value)
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed genealogy parent lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
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
        return {
            "logical_genealogy_parents": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_genealogy_parents": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "genealogy_parent_payload_loads": self._loads,
            "dirty_genealogy_parents": len(self._dirty),
        }


class _LazyMaterialContainerTable(LazyRecordTable):
    """Bounded lazy material index whose values are mutable list/set buckets."""

    _record_schema = 0
    _touched_attr = ""
    _label = "material index"

    def __init__(self, session, namespace, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = namespace
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _plain(self, value):
        raise NotImplementedError

    def _valid_plain(self, value):
        raise NotImplementedError

    def _bind_loaded_bucket(self, key, value):
        raise NotImplementedError

    def _bind_assigned_bucket(self, key, value):
        raise NotImplementedError

    def _detach_assigned_bucket(self, key, value):
        raise NotImplementedError

    def _detach_unloaded_bucket(self, key):
        raise NotImplementedError

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=self._record_schema,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

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
            expected_record_schema=self._record_schema,
        )
        if not self._valid_plain(checked.value):
            raise StoreFormatError(
                f"lazy {self._label} payload has wrong type"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        bucket = self._bind_loaded_bucket(key, checked.value)
        dict.__setitem__(self, key, bucket)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return bucket

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                f"mutation notification has no current lazy {self._label}"
            )
        if not dict.__contains__(self, key):
            self[key]
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, value):
        self._ensure_mutation()
        if not self._valid_plain(self._plain(value)):
            raise TypeError(f"{self._label} value has wrong type")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is value and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not value:
            self._detach_assigned_bucket(key, old)
        bucket = self._bind_assigned_bucket(key, value)
        dict.__setitem__(self, key, bucket)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_assigned_bucket(key, old)
            dict.__delitem__(self, key)
        else:
            self._detach_unloaded_bucket(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
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
                            record_schema=self._record_schema,
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
            bucket = dict.__getitem__(self, key)
            stored_value = self._plain(bucket)
            payload = self._store.codec.encode(stored_value)
            incarnation = self._session._registry.incarnation_for_object(
                bucket
            )
            if incarnation is None:
                raise StoreIntegrityError(
                    f"current lazy {self._label} has no runtime incarnation"
                )
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
                        stored_value,
                        record_schema=self._record_schema,
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
        for key in getattr(plan, self._touched_attr):
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                bucket = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    self._plain(bucket)
                )
                incarnation = self._session._registry.incarnation_for_object(
                    bucket
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
                        f"committed {self._label} lost collection order"
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
        return {
            "logical_buckets": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_buckets": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "bucket_payload_loads": self._loads,
            "dirty_buckets": len(self._dirty),
        }


class LazyMaterialLotIndexTable(_LazyMaterialContainerTable):
    _record_schema = LAZY_MATERIAL_LOT_INDEX_SCHEMA
    _touched_attr = "material_lot_index_touched_keys"
    _label = "material lot-index bucket"

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session, MATERIAL_LOT_INDEX_NAMESPACE, clean_limit=clean_limit
        )

    def setdefault(self, key, default=None):
        self._ensure_mutation()
        if self._visible(key):
            return self[key]
        if default is None:
            default = []
        self[key] = default
        return self[key]

    def _plain(self, value):
        return list(value)

    def _valid_plain(self, value):
        return type(value) is list and all(type(item) is int for item in value)

    def _bind_loaded_bucket(self, key, value):
        return self._session._bind_loaded_material_lot_index(key, value)

    def _bind_assigned_bucket(self, key, value):
        return self._session._bind_assigned_material_lot_index(key, value)

    def _detach_assigned_bucket(self, key, value):
        self._session._detach_assigned_material_lot_index(key, value)

    def _detach_unloaded_bucket(self, key):
        self._session._detach_unloaded_material_lot_index(key)


class LazyMaterialActiveIndexTable(_LazyMaterialContainerTable):
    _record_schema = LAZY_MATERIAL_ACTIVE_INDEX_SCHEMA
    _touched_attr = "material_active_index_touched_keys"
    _label = "material active-index bucket"

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session, MATERIAL_ACTIVE_INDEX_NAMESPACE, clean_limit=clean_limit
        )

    def _plain(self, value):
        return set(value)

    def _valid_plain(self, value):
        return type(value) is set and all(type(item) is int for item in value)

    def _bind_loaded_bucket(self, key, value):
        return self._session._bind_loaded_material_active_index(key, value)

    def _bind_assigned_bucket(self, key, value):
        return self._session._bind_assigned_material_active_index(key, value)

    def _detach_assigned_bucket(self, key, value):
        self._session._detach_assigned_material_active_index(key, value)

    def _detach_unloaded_bucket(self, key):
        self._session._detach_unloaded_material_active_index(key)



class LazyGenealogyChildrenTable(_LazyMaterialContainerTable):
    """Bounded lazy parent -> ordered mutable child-ID list authority."""

    _record_schema = LAZY_GENEALOGY_CHILD_SCHEMA
    _touched_attr = "genealogy_child_touched_keys"
    _label = "genealogy child bucket"

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        super().__init__(
            session, GENEALOGY_CHILD_NAMESPACE, clean_limit=clean_limit
        )

    def _plain(self, value):
        return list(value)

    def _valid_plain(self, value):
        return type(value) is list and all(type(item) is int for item in value)

    def _bind_loaded_bucket(self, key, value):
        return self._session._bind_loaded_genealogy_children(key, value)

    def _bind_assigned_bucket(self, key, value):
        return self._session._bind_assigned_genealogy_children(key, value)

    def _detach_assigned_bucket(self, key, value):
        self._session._detach_assigned_genealogy_children(key, value)

    def _detach_unloaded_bucket(self, key):
        self._session._detach_unloaded_genealogy_children(key)


class LazyCurrencyBucketTable(_LazyMaterialContainerTable):
    """Bounded lazy outer mapping for shared mutable currency dictionaries."""

    def __init__(
        self,
        session,
        namespace,
        record_schema,
        touched_attr,
        label,
        *,
        clean_limit=CLEAN_GROUP_LIMIT,
    ):
        self._record_schema = record_schema
        self._touched_attr = touched_attr
        self._label = label
        super().__init__(session, namespace, clean_limit=clean_limit)
        self._baseline_identity_labels = {}

    def _baseline_labels(self, key):
        if key not in self._baseline_identity_labels:
            self._baseline_identity_labels[key] = dict(
                self._store.identity_occurrences_for_owner(
                    self._pin, self._namespace, key
                )
            )
        return dict(self._baseline_identity_labels[key])

    def _plain(self, value):
        return dict(value)

    def _valid_plain(self, value):
        return type(value) is dict

    def _bind_loaded_bucket(self, key, value):
        return self._session._bind_loaded_currency_bucket(
            self, self._namespace, key, value
        )

    def _bind_assigned_bucket(self, key, value):
        return self._session._bind_assigned_currency_bucket(
            self, self._namespace, key, value
        )

    def _detach_assigned_bucket(self, key, value):
        self._session._detach_assigned_currency_bucket(
            self, self._namespace, key, value
        )

    def _detach_unloaded_bucket(self, key):
        self._session._detach_unloaded_currency_bucket(
            self, self._namespace, key
        )

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
        )
        version_changes = []
        identity_changes = []
        effective_keys = []
        structural_keys = []
        for key in touched:
            baseline_exists = self._baseline_exists(key)
            visible = self._visible(key)
            baseline_labels = (
                self._baseline_labels(key) if baseline_exists else {}
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=self._record_schema,
                        )
                    )
                    for path in baseline_labels:
                        identity_changes.append(
                            IdentityOccurrenceChange(
                                self._namespace, key, path, delete=True
                            )
                        )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue

            bucket = dict.__getitem__(self, key)
            stored_value = self._plain(bucket)
            payload = self._store.codec.encode(stored_value)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new
                or reinsertion
                or payload != self._baseline_bytes(key)
            )
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        stored_value,
                        record_schema=self._record_schema,
                        reinsertion=reinsertion,
                    )
                )

            current_labels = self._session._currency_incarnation_labels(
                self._namespace, key, bucket
            )
            identity_changed = False
            for path in sorted(
                set(baseline_labels) | set(current_labels),
                key=self._store.codec.encode,
            ):
                before = baseline_labels.get(path)
                after = current_labels.get(path)
                if before == after:
                    continue
                identity_changed = True
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        path,
                        delete=after is None,
                        incarnation_id=after,
                    )
                )

            if value_changed or identity_changed:
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
        for key in getattr(plan, self._touched_attr):
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                bucket = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    self._plain(bucket)
                )
                labels = self._session._currency_incarnation_labels(
                    self._namespace, key, bucket
                )
                self._baseline_identity_labels[key] = labels
                self._baseline_incarnation[key] = labels.get(())
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        f"committed {self._label} lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_identity_labels.pop(key, None)
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


class LazyMaterialLotTable(LazyRecordTable):
    """Bounded lazy MaterialLot authority with persistent active memberships."""

    _transfer_path = (("field", "transfers"),)

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = MATERIAL_LOT_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_identity_labels = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}
        self._pending_transfer_old = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_MATERIAL_LOT_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _baseline_labels(self, key):
        if key not in self._baseline_identity_labels:
            self._baseline_identity_labels[key] = dict(
                self._store.identity_occurrences_for_owner(
                    self._pin, self._namespace, key
                )
            )
        return dict(self._baseline_identity_labels[key])

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
            expected_record_schema=LAZY_MATERIAL_LOT_SCHEMA,
        )
        if not isinstance(checked.value, MaterialLot):
            raise StoreFormatError(
                "lazy material-lot payload is not MaterialLot"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._session._bind_loaded_material_lot(
            key, checked.value
        )
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def preflight_change(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy material lot"
            )
        if field == "transfers":
            live = (
                dict.__getitem__(self, key)
                if dict.__contains__(self, key)
                else self._session._live_material_lot_for_key(key)
            )
            if live is not None:
                self._pending_transfer_old[key] = live.transfers

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy material lot"
            )
        if not dict.__contains__(self, key):
            self[key]
        record = dict.__getitem__(self, key)
        if field == "transfers" and key in self._pending_transfer_old:
            old = self._pending_transfer_old.pop(key)
            if old is not record.transfers:
                self._session._replace_material_lot_transfers(
                    key, record, old, record.transfers
                )
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, MaterialLot):
            raise TypeError("world.materials.lots values must be MaterialLot")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is record and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)
            self._session._detach_assigned_material_lot(key, old)
        record = self._session._bind_assigned_material_lot(key, record)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_index_binding(old)
            self._session._detach_assigned_material_lot(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_material_lot(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    def _overlay_memberships(self, lot, ordinal):
        return tuple(
            Membership(name, value, member_ordinal)
            for name, value, member_ordinal
            in _material_lot_memberships(lot, ordinal)
        )

    def ids(self, index_name, value):
        self._ensure()
        if index_name not in {"active_settlement", "active_rank"}:
            raise StoreError("unsupported lazy material-lot membership query")
        baseline = set(
            self._store.query_keys(
                self._pin, self._namespace, index_name, value
            )
        )
        touched = self._effective_touched()
        baseline.difference_update(touched)
        for key in touched:
            if not self._visible(key):
                continue
            record = dict.__getitem__(self, key)
            ordinal = self._current_ordinal(key)
            current = {
                (member.index_name, member.value)
                for member in self._overlay_memberships(record, ordinal)
            }
            if (index_name, value) in current:
                baseline.add(key)
        return tuple(sorted(baseline, key=self._current_ordinal))

    def active_ids(self, settlement):
        return self.ids("active_settlement", settlement)

    def active_rank_ids(self, settlement, rank):
        return self.ids("active_rank", (settlement, rank))

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
            baseline_labels = (
                self._baseline_labels(key) if baseline_exists else {}
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_MATERIAL_LOT_SCHEMA,
                        )
                    )
                    for path in baseline_labels:
                        identity_changes.append(
                            IdentityOccurrenceChange(
                                self._namespace, key, path, delete=True
                            )
                        )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue
            record = dict.__getitem__(self, key)
            stored_record = _plain_material_lot_value(record)
            payload = self._store.codec.encode(stored_record)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new or reinsertion or payload != self._baseline_bytes(key)
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
                        stored_record,
                        record_schema=LAZY_MATERIAL_LOT_SCHEMA,
                        memberships=self._overlay_memberships(
                            record, ordinal
                        ),
                        reinsertion=reinsertion,
                    )
                )
            current_labels = (
                self._session._material_lot_incarnation_labels(key, record)
            )
            all_paths = set(baseline_labels) | set(current_labels)
            identity_changed = False
            for path in sorted(
                all_paths, key=self._store.codec.encode
            ):
                before = baseline_labels.get(path)
                after = current_labels.get(path)
                if before == after:
                    continue
                identity_changed = True
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        path,
                        delete=after is None,
                        incarnation_id=after,
                    )
                )
            if value_changed or identity_changed:
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
        for key in plan.material_lot_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                record = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    _plain_material_lot_value(record)
                )
                self._baseline_identity_labels[key] = (
                    self._session._material_lot_incarnation_labels(
                        key, record
                    )
                )
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed material lot lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_identity_labels.pop(key, None)
                self._baseline_ordinal.pop(key, None)
        self._dirty.clear()
        self._removed.clear()
        self._new_keys.clear()
        self._reinserted.clear()
        self._overlay_ordinals.clear()
        self._pending_transfer_old.clear()
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        return {
            "logical_material_lots": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_material_lots": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "material_lot_payload_loads": self._loads,
            "dirty_material_lots": len(self._dirty),
        }


def _plain_soul_value(soul):
    """Storage value for a live lazy soul without runtime wrappers."""
    if not isinstance(soul, SoulState):
        raise TypeError("expected SoulState")
    return replace(
        soul,
        authorities=set(soul.authorities),
        marks=set(soul.marks),
        cosmic_links=dict(soul.cosmic_links),
        transformations=list(soul.transformations),
    )


class _LazySoulBindingMixin:
    """Multi-owner weak bindings for one nested mutable soul object."""

    def _init_soul_bindings(self):
        self._soul_bindings = {}

    def _bindings(self):
        dead = []
        out = []
        for token, (table_ref, key, field) in self._soul_bindings.items():
            table = table_ref()
            if table is None:
                dead.append(token)
            else:
                out.append((table, key, field))
        for token in dead:
            self._soul_bindings.pop(token, None)
        return tuple(out)

    def _attach(self, table, key, field):
        token = (id(table), key, field)
        self._soul_bindings[token] = (weakref.ref(table), key, field)

    def _detach(self, table, key, field):
        self._soul_bindings.pop((id(table), key, field), None)

    def _guard(self):
        bindings = self._bindings()
        for table, key, _field in bindings:
            table._ensure_mutation()
            if not table._visible(key):
                raise StoreIntegrityError(
                    "tracked soul child retained a non-current owner"
                )
        return bindings

    @staticmethod
    def _touch(bindings):
        for table, key, field in bindings:
            table.changed(key, field)


class LazySoulTrackedSet(_LazySoulBindingMixin, set):
    def __init__(self, values=()):
        set.__init__(self, values)
        self._init_soul_bindings()

    def add(self, value):
        bindings = self._guard()
        before = len(self)
        set.add(self, value)
        if len(self) != before:
            self._touch(bindings)

    def discard(self, value):
        bindings = self._guard()
        before = len(self)
        set.discard(self, value)
        if len(self) != before:
            self._touch(bindings)

    def remove(self, value):
        bindings = self._guard()
        set.remove(self, value)
        self._touch(bindings)

    def pop(self):
        bindings = self._guard()
        value = set.pop(self)
        self._touch(bindings)
        return value

    def clear(self):
        bindings = self._guard()
        if self:
            set.clear(self)
            self._touch(bindings)

    def update(self, *others):
        bindings = self._guard()
        before = set(self)
        set.update(self, *others)
        if self != before:
            self._touch(bindings)

    def intersection_update(self, *others):
        bindings = self._guard()
        before = set(self)
        set.intersection_update(self, *others)
        if self != before:
            self._touch(bindings)

    def difference_update(self, *others):
        bindings = self._guard()
        before = set(self)
        set.difference_update(self, *others)
        if self != before:
            self._touch(bindings)

    def symmetric_difference_update(self, other):
        bindings = self._guard()
        before = set(self)
        set.symmetric_difference_update(self, other)
        if self != before:
            self._touch(bindings)

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


class LazySoulTrackedList(_LazySoulBindingMixin, list):
    def __init__(self, values=()):
        list.__init__(self, values)
        self._init_soul_bindings()

    def append(self, value):
        bindings = self._guard()
        list.append(self, value)
        self._touch(bindings)

    def extend(self, values):
        bindings = self._guard()
        list.extend(self, values)
        if values:
            self._touch(bindings)

    def insert(self, index, value):
        bindings = self._guard()
        list.insert(self, index, value)
        self._touch(bindings)

    def __setitem__(self, index, value):
        bindings = self._guard()
        list.__setitem__(self, index, value)
        self._touch(bindings)

    def __delitem__(self, index):
        bindings = self._guard()
        list.__delitem__(self, index)
        self._touch(bindings)

    def pop(self, index=-1):
        bindings = self._guard()
        value = list.pop(self, index)
        self._touch(bindings)
        return value

    def remove(self, value):
        bindings = self._guard()
        list.remove(self, value)
        self._touch(bindings)

    def clear(self):
        bindings = self._guard()
        if self:
            list.clear(self)
            self._touch(bindings)

    def reverse(self):
        bindings = self._guard()
        list.reverse(self)
        self._touch(bindings)

    def sort(self, *args, **kwargs):
        bindings = self._guard()
        list.sort(self, *args, **kwargs)
        self._touch(bindings)

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        bindings = self._guard()
        list.__imul__(self, count)
        self._touch(bindings)
        return self



def _plain_advancement_value(value, memo=None):
    """Remove runtime lazy wrappers while preserving the path value graph."""
    if memo is None:
        memo = {}
    cls = type(value)
    if value is None or cls in (bool, int, float, str, bytes, FrozenDict, FrozenList):
        return value
    ident = id(value)
    if ident in memo:
        return memo[ident]
    if is_dataclass(value):
        memo[ident] = value
        updates = {
            name: _plain_advancement_value(getattr(value, name), memo)
            for name in RECORD_FIELDS.get(cls, ())
        }
        plain = replace(value, **updates)
        memo[ident] = plain
        return plain
    if isinstance(value, dict):
        out = {}
        memo[ident] = out
        for key, child in value.items():
            out[key] = _plain_advancement_value(child, memo)
        return out
    if isinstance(value, list):
        out = []
        memo[ident] = out
        out.extend(_plain_advancement_value(child, memo) for child in value)
        return out
    if isinstance(value, set):
        out = set()
        memo[ident] = out
        out.update(_plain_advancement_value(child, memo) for child in value)
        return out
    if cls is tuple:
        out = tuple(_plain_advancement_value(child, memo) for child in value)
        memo[ident] = out
        return out
    return value


class LazyAdvancementPathTable(LazyRecordTable):
    """Bounded lazy authority for one complete mutable EssencePath per person."""

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = ADVANCEMENT_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_identity_labels = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_ADVANCEMENT_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _baseline_labels(self, key):
        if key not in self._baseline_identity_labels:
            self._baseline_identity_labels[key] = dict(
                self._store.identity_occurrences_for_owner(
                    self._pin, self._namespace, key
                )
            )
        return dict(self._baseline_identity_labels[key])

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
            expected_record_schema=LAZY_ADVANCEMENT_SCHEMA,
        )
        if not isinstance(checked.value, EssencePath):
            raise StoreFormatError(
                "lazy advancement payload is not EssencePath"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        path = self._session._bind_loaded_advancement_path(
            key, checked.value
        )
        dict.__setitem__(self, key, path)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return path

    def preflight_change(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current advancement path"
            )

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current advancement path"
            )
        if not dict.__contains__(self, key):
            self[key]
        # Most advancement writes are scalar progress/rank/training updates.
        # Rewalking and reattaching the entire nested identity graph for those
        # cannot change identity topology and becomes quadratic at mature-world
        # scale. Reconcile only when a container/object-valued field can replace
        # or restructure mutable identity, or when a tracked container mutation
        # reports no field (field=None).
        identity_fields = {
            "base_essences",
            "abilities",
            "response_model",
            "understanding",
            "evidence",
            "applications",
            "transfers",
            "samples",
            "coefficients",
        }
        if field is None or field in identity_fields:
            path = dict.__getitem__(self, key)
            rebound, _labels = self._session._reconcile_advancement_graph(
                key, path
            )
            if rebound is not path:
                dict.__setitem__(self, key, rebound)
        self._dirty.add(key)
        self._lru.pop(key, None)
        self._session.world.advancement._invalidate_rank(key)

    def __setitem__(self, key, path):
        self._ensure_mutation()
        if not isinstance(path, EssencePath):
            raise TypeError(
                "world.advancement.paths values must be EssencePath"
            )
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is path and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not path:
            self._session._detach_assigned_advancement_path(key, old)
        path = self._session._bind_assigned_advancement_path(key, path)
        dict.__setitem__(self, key, path)
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
        self._session.world.advancement._invalidate_rank(key)

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._session._detach_assigned_advancement_path(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_advancement_path(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)
        self._session.world.advancement._invalidate_rank(key)

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
            baseline_labels = (
                self._baseline_labels(key) if baseline_exists else {}
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_ADVANCEMENT_SCHEMA,
                        )
                    )
                    for path in baseline_labels:
                        identity_changes.append(
                            IdentityOccurrenceChange(
                                self._namespace, key, path, delete=True
                            )
                        )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue

            path = dict.__getitem__(self, key)
            path, current_labels = (
                self._session._reconcile_advancement_graph(key, path)
            )
            dict.__setitem__(self, key, path)
            stored = _plain_advancement_value(path)
            payload = self._store.codec.encode(stored)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new
                or reinsertion
                or payload != self._baseline_bytes(key)
            )
            if is_new or reinsertion:
                structural_ordinals[key]
            else:
                self._persisted_ordinal(key)
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        stored,
                        record_schema=LAZY_ADVANCEMENT_SCHEMA,
                        reinsertion=reinsertion,
                    )
                )

            identity_changed = False
            for occurrence_path in sorted(
                set(baseline_labels) | set(current_labels),
                key=self._store.codec.encode,
            ):
                before = baseline_labels.get(occurrence_path)
                after = current_labels.get(occurrence_path)
                if before == after:
                    continue
                identity_changed = True
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        occurrence_path,
                        delete=after is None,
                        incarnation_id=after,
                    )
                )
            if value_changed or identity_changed:
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
        for key in plan.advancement_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                path = dict.__getitem__(self, key)
                stored = _plain_advancement_value(path)
                self._baseline_payload[key] = self._store.codec.encode(stored)
                self._baseline_identity_labels[key] = (
                    self._session._advancement_incarnation_labels(
                        key, path
                    )
                )
                top = self._session._registry.incarnation_for_object(path)
                self._baseline_incarnation[key] = (
                    None if top is None else top.value
                )
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed advancement path lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_identity_labels.pop(key, None)
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
        return {
            "logical_advancement_paths": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_advancement_paths": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "advancement_payload_loads": self._loads,
            "dirty_advancement_paths": len(self._dirty),
        }


class LazySkillTable(LazyRecordTable):
    """Bounded lazy SkillHistory authority with two tracked list children."""

    _nested_paths = {
        "teachers": (("field", "teachers"),),
        "provenance": (("field", "provenance"),),
    }

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = SKILL_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_identity_labels = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}
        self._pending_nested_old = {}

    @staticmethod
    def _plain(record):
        return replace(
            record,
            teachers=list(record.teachers),
            provenance=list(record.provenance),
        )

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_SKILL_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _baseline_labels(self, key):
        if key not in self._baseline_identity_labels:
            self._baseline_identity_labels[key] = dict(
                self._store.identity_occurrences_for_owner(
                    self._pin, self._namespace, key
                )
            )
        return dict(self._baseline_identity_labels[key])

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
            expected_record_schema=LAZY_SKILL_SCHEMA,
        )
        if not isinstance(checked.value, SkillHistory):
            raise StoreFormatError(
                "lazy skill payload is not SkillHistory"
            )
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._session._bind_loaded_skill(key, checked.value)
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def preflight_change(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current skill history"
            )
        if field in self._nested_paths:
            live = (
                dict.__getitem__(self, key)
                if dict.__contains__(self, key)
                else self._session._live_skill_for_key(key)
            )
            if live is not None:
                self._pending_nested_old[(key, field)] = getattr(live, field)

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current skill history"
            )
        if not dict.__contains__(self, key):
            self[key]
        record = dict.__getitem__(self, key)
        token = (key, field)
        if field in self._nested_paths and token in self._pending_nested_old:
            old = self._pending_nested_old.pop(token)
            new = getattr(record, field)
            if old is not new:
                self._session._replace_skill_nested(
                    key, record, field, old, new
                )
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, SkillHistory):
            raise TypeError(
                "world.skills.skills values must be SkillHistory"
            )
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is record and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)
            self._session._detach_assigned_skill(key, old)
        record = self._session._bind_assigned_skill(key, record)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_index_binding(old)
            self._session._detach_assigned_skill(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_skill(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

    def prepare_save_changes(self):
        touched = sorted(
            self._effective_touched(),
            key=lambda key: self._store.codec.encode(key),
        )
        version_changes = []
        identity_changes = []
        effective_keys = []
        structural_keys = []
        for key in touched:
            baseline_exists = self._baseline_exists(key)
            visible = self._visible(key)
            baseline_labels = (
                self._baseline_labels(key) if baseline_exists else {}
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_SKILL_SCHEMA,
                        )
                    )
                    for path in baseline_labels:
                        identity_changes.append(
                            IdentityOccurrenceChange(
                                self._namespace, key, path, delete=True
                            )
                        )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue

            record = dict.__getitem__(self, key)
            stored = self._plain(record)
            payload = self._store.codec.encode(stored)
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
                        stored,
                        record_schema=LAZY_SKILL_SCHEMA,
                        reinsertion=reinsertion,
                    )
                )
            current_labels = self._session._skill_incarnation_labels(
                key, record
            )
            identity_changed = False
            for path in sorted(
                set(baseline_labels) | set(current_labels),
                key=self._store.codec.encode,
            ):
                before = baseline_labels.get(path)
                after = current_labels.get(path)
                if before == after:
                    continue
                identity_changed = True
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        path,
                        delete=after is None,
                        incarnation_id=after,
                    )
                )
            if value_changed or identity_changed:
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
        for key in plan.skill_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                record = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    self._plain(record)
                )
                labels = self._session._skill_incarnation_labels(
                    key, record
                )
                self._baseline_identity_labels[key] = labels
                self._baseline_incarnation[key] = labels.get(())
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed skill history lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_identity_labels.pop(key, None)
                self._baseline_incarnation[key] = None
                self._baseline_ordinal.pop(key, None)
        self._dirty.clear()
        self._removed.clear()
        self._new_keys.clear()
        self._reinserted.clear()
        self._overlay_ordinals.clear()
        self._pending_nested_old.clear()
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        return {
            "logical_skills": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_skills": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "skill_payload_loads": self._loads,
            "dirty_skills": len(self._dirty),
        }


class LazySoulTable(LazyRecordTable):
    """Bounded lazy soul authority with nested mutable incarnation tracking."""

    _nested_paths = {
        "authorities": (("field", "authorities"),),
        "marks": (("field", "marks"),),
        "cosmic_links": (("field", "cosmic_links"),),
        "transformations": (("field", "transformations"),),
    }

    def __init__(self, session, *, clean_limit=CLEAN_GROUP_LIMIT):
        dict.__init__(self)
        self._session = session
        self._store = session.store
        self._pin = session.pin
        self._namespace = SOUL_NAMESPACE
        self._clean_limit = clean_limit
        self._lru = _StepAwareLRU(session)
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
        self._baseline_presence = {}
        self._baseline_payload = {}
        self._baseline_incarnation = {}
        self._baseline_identity_labels = {}
        self._baseline_ordinal = {}
        self._dirty = set()
        self._removed = set()
        self._new_keys = set()
        self._reinserted = set()
        self._overlay_ordinals = {}
        self._pending_nested_old = {}

    def _baseline_bytes(self, key):
        if key not in self._baseline_payload:
            checked = self._store.read_version(
                self._pin,
                self._namespace,
                key,
                expected_record_schema=LAZY_SOUL_SCHEMA,
            )
            self._baseline_payload[key] = self._store.codec.encode(
                checked.value
            )
        return self._baseline_payload[key]

    def _baseline_labels(self, key):
        if key not in self._baseline_identity_labels:
            self._baseline_identity_labels[key] = dict(
                self._store.identity_occurrences_for_owner(
                    self._pin, self._namespace, key
                )
            )
        return dict(self._baseline_identity_labels[key])

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
            expected_record_schema=LAZY_SOUL_SCHEMA,
        )
        if not isinstance(checked.value, SoulState):
            raise StoreFormatError("lazy soul payload is not SoulState")
        self._baseline_payload.setdefault(
            key, self._store.codec.encode(checked.value)
        )
        self._baseline_presence.setdefault(key, True)
        record = self._session._bind_loaded_soul(key, checked.value)
        dict.__setitem__(self, key, record)
        object.__setattr__(record, "_index_table", weakref.ref(self))
        object.__setattr__(record, "_index_key", key)
        self._loads += 1
        if key not in self._dirty:
            self._lru[key] = None
        self._evict_clean()
        return record

    def preflight_change(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy soul"
            )
        if field in self._nested_paths:
            live = (
                dict.__getitem__(self, key)
                if dict.__contains__(self, key)
                else self._session._live_soul_for_key(key)
            )
            if live is not None:
                self._pending_nested_old[(key, field)] = getattr(live, field)

    def changed(self, key, field=None):
        self._ensure_mutation()
        if not self._visible(key):
            raise StoreIntegrityError(
                "mutation notification has no current lazy soul"
            )
        if not dict.__contains__(self, key):
            self[key]
        record = dict.__getitem__(self, key)
        token = (key, field)
        if field in self._nested_paths and token in self._pending_nested_old:
            old = self._pending_nested_old.pop(token)
            new = getattr(record, field)
            if old is not new:
                self._session._replace_soul_nested(
                    key, record, field, old, new
                )
        self._dirty.add(key)
        self._lru.pop(key, None)

    def __setitem__(self, key, record):
        self._ensure_mutation()
        if not isinstance(record, SoulState):
            raise TypeError("world.metaphysics.souls values must be SoulState")
        baseline_exists = self._baseline_exists(key)
        currently_visible = self._visible(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is record and currently_visible:
            return
        was_removed = key in self._removed
        if old is not None and old is not record:
            self._detach_index_binding(old)
            self._session._detach_assigned_soul(key, old)
        record = self._session._bind_assigned_soul(key, record)
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

    def __delitem__(self, key):
        self._ensure_mutation()
        if not self._visible(key):
            raise KeyError(key)
        baseline_exists = self._baseline_exists(key)
        old = (
            dict.__getitem__(self, key)
            if dict.__contains__(self, key) else None
        )
        if old is not None:
            self._detach_index_binding(old)
            self._session._detach_assigned_soul(key, old)
            dict.__delitem__(self, key)
        else:
            self._session._detach_unloaded_soul(key)
        self._lru.pop(key, None)
        self._dirty.discard(key)
        self._reinserted.discard(key)
        if baseline_exists:
            self._removed.add(key)
        else:
            self._new_keys.discard(key)
            self._overlay_ordinals.pop(key, None)

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
            baseline_labels = (
                self._baseline_labels(key) if baseline_exists else {}
            )
            if not visible:
                if baseline_exists:
                    version_changes.append(
                        VersionChange(
                            self._namespace,
                            key,
                            delete=True,
                            record_schema=LAZY_SOUL_SCHEMA,
                        )
                    )
                    for path in baseline_labels:
                        identity_changes.append(
                            IdentityOccurrenceChange(
                                self._namespace,
                                key,
                                path,
                                delete=True,
                            )
                        )
                    effective_keys.append(key)
                    structural_keys.append(key)
                continue

            record = dict.__getitem__(self, key)
            stored_record = _plain_soul_value(record)
            payload = self._store.codec.encode(stored_record)
            reinsertion = key in self._reinserted
            is_new = not baseline_exists
            value_changed = (
                is_new
                or reinsertion
                or payload != self._baseline_bytes(key)
            )
            if is_new or reinsertion:
                structural_ordinals[key]
            else:
                self._persisted_ordinal(key)
            if value_changed:
                version_changes.append(
                    VersionChange(
                        self._namespace,
                        key,
                        stored_record,
                        record_schema=LAZY_SOUL_SCHEMA,
                        reinsertion=reinsertion,
                    )
                )

            current_labels = self._session._soul_incarnation_labels(
                key, record
            )
            all_paths = set(baseline_labels) | set(current_labels)
            identity_changed = False
            for path in sorted(
                all_paths, key=self._store.codec.encode
            ):
                before = baseline_labels.get(path)
                after = current_labels.get(path)
                if before == after:
                    continue
                identity_changed = True
                identity_changes.append(
                    IdentityOccurrenceChange(
                        self._namespace,
                        key,
                        path,
                        delete=after is None,
                        incarnation_id=after,
                    )
                )
            if value_changed or identity_changed:
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
        for key in plan.soul_touched_keys:
            visible = self._visible(key)
            self._baseline_presence[key] = visible
            if visible:
                soul = dict.__getitem__(self, key)
                self._baseline_payload[key] = self._store.codec.encode(
                    _plain_soul_value(soul)
                )
                self._baseline_identity_labels[key] = (
                    self._session._soul_incarnation_labels(key, soul)
                )
                top = self._session._registry.incarnation_for_object(soul)
                self._baseline_incarnation[key] = (
                    None if top is None else top.value
                )
                typed_key = self._store.codec.encode(key)
                order = self._store._visible_order(
                    self._namespace, typed_key, new_pin.captured_head
                )
                if order is None:
                    raise StoreIntegrityError(
                        "committed soul lost collection order"
                    )
                self._baseline_ordinal[key] = order[0]
            else:
                self._baseline_payload.pop(key, None)
                self._baseline_identity_labels.pop(key, None)
                self._baseline_incarnation[key] = None
                self._baseline_ordinal.pop(key, None)
        self._dirty.clear()
        self._removed.clear()
        self._new_keys.clear()
        self._reinserted.clear()
        self._overlay_ordinals.clear()
        self._pending_nested_old.clear()
        self._lru.clear()
        for key in list(dict.keys(self)):
            self._lru[key] = None
        self._evict_clean()

    def diagnostics(self):
        return {
            "logical_souls": (
                self._baseline_count
                - len(self._removed)
                + len(self._new_keys)
            ),
            "resident_souls": dict.__len__(self),
            "clean_cache_entries": len(self._lru),
            "clean_cache_limit": self._clean_limit,
            "soul_payload_loads": self._loads,
            "dirty_souls": len(self._dirty),
            "removed_souls": len(self._removed),
            "new_souls": len(self._new_keys),
            "reinserted_souls": len(self._reinserted),
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

    def begin_run(self):
        session = self._session()
        session._ensure_hybrid_mutation_allowed()
        if getattr(session, "_hot_run_depth", 0):
            raise StoreError("reentrant lazy simulation run is not allowed")
        session._hot_run_depth = 1

    def end_run(self):
        session = self._session_ref()
        if session is None or not session._active:
            return
        session._hot_run_depth = 0
        # A run may retain an active working set larger than the ordinary
        # point-query cache, but that residency must not escape the run.
        for value in tuple(session.__dict__.values()):
            if isinstance(value, LazyRecordTable):
                value._evict_clean()

    def begin_step(self):
        session = self._session()
        session._ensure_hybrid_mutation_allowed()
        tracker = session._eager_tracker
        if tracker._cold_step_depth:
            raise StoreError("reentrant lazy simulation step is not allowed")
        session._hot_step_epoch = getattr(session, "_hot_step_epoch", 0) + 1
        tracker._cold_step_depth += 1

    def end_step(self):
        session = self._session_ref()
        if (
            session is not None
            and session._active
            and session._eager_tracker._cold_step_depth
        ):
            session._eager_tracker._cold_step_depth -= 1
            if not session._eager_tracker._cold_step_depth:
                epoch = getattr(session, "_hot_step_epoch", 0)
                retain_hot = bool(getattr(session, "_hot_run_depth", 0))
                for value in tuple(session.__dict__.values()):
                    if isinstance(value, LazyRecordTable):
                        value._finish_simulation_step(
                            epoch, retain_hot=retain_hot
                        )

    def ensure_eventlog_read(self):
        session = self._session()
        if session._state == "recovery-required":
            raise StoreError(
                "lazy EventLog is unavailable until save acknowledgement resolves"
            )

    def begin_operation(self, operation, *, allow_stale=False):
        session = self._session()
        # Public World.digest/archive must acquire the same lifecycle guard as
        # explicit P3B operations, before traversing any mutable World state.
        session._begin_lifecycle_operation(operation, allow_stale=allow_stale)

    def end_operation(self, operation):
        self._session()._end_lifecycle_operation(operation)

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
        self._lifecycle_operation: str | None = None
        self._pending_save: LazyPeopleSavePlan | None = None
        self._head = head
        self._registry = LazyIdentityRegistry(
            store.store_identity,
            next_incarnation=next_incarnation,
            prune_dead_occurrences=True,
        )
        self.people = LazyRecordTable(self)
        object.__setattr__(world, "people", self.people)
        self.aspirations = LazyAspirationTable(self)
        object.__setattr__(
            world.magic_resources, "aspirations", self.aspirations
        )
        self.resources = LazyResourceTable(self)
        object.__setattr__(
            world.magic_resources, "resources", self.resources
        )
        self.owner_index = LazyOwnerIndexTable(self)
        object.__setattr__(
            world.magic_resources, "owner_index", self.owner_index
        )
        self.material_lots = LazyMaterialLotTable(self)
        object.__setattr__(world.materials, "lots", self.material_lots)
        self.material_items = LazyMaterialItemTable(self)
        object.__setattr__(world.materials, "items", self.material_items)
        self.material_lot_index = LazyMaterialLotIndexTable(self)
        object.__setattr__(
            world.materials, "lot_index", self.material_lot_index
        )
        self.material_active_index = LazyMaterialActiveIndexTable(self)
        object.__setattr__(
            world.materials, "active_lot_index", self.material_active_index
        )
        self.wallets = LazyCurrencyBucketTable(
            self,
            WALLET_NAMESPACE,
            LAZY_WALLET_SCHEMA,
            "wallet_touched_keys",
            "wallet",
        )
        object.__setattr__(world.currency, "wallets", self.wallets)
        self.treasuries = LazyCurrencyBucketTable(
            self,
            TREASURY_NAMESPACE,
            LAZY_TREASURY_SCHEMA,
            "treasury_touched_keys",
            "treasury",
        )
        object.__setattr__(world.currency, "treasuries", self.treasuries)
        self.souls = LazySoulTable(self)
        object.__setattr__(world.metaphysics, "souls", self.souls)
        self.advancement_paths = LazyAdvancementPathTable(self)
        object.__setattr__(
            world.advancement, "paths", self.advancement_paths
        )
        self.institution_magic_records = LazyInstitutionMagicRecordTable(self)
        object.__setattr__(
            world.institutions,
            "magic_records",
            self.institution_magic_records,
        )
        self.institution_notices = LazyInstitutionNoticeTable(self)
        object.__setattr__(
            world.institutions, "notices", self.institution_notices
        )
        self.institution_applications = LazyInstitutionApplicationTable(self)
        object.__setattr__(
            world.institutions,
            "applications",
            self.institution_applications,
        )
        self.transmissions = LazyTransmissionRecordTable(self)
        object.__setattr__(
            world.transmission, "records", self.transmissions
        )
        self.motives = LazyMotiveTable(self)
        object.__setattr__(world.agency, "motives", self.motives)
        self.lineage_nodes = LazyLineageNodeTable(self)
        object.__setattr__(world.lineage, "nodes", self.lineage_nodes)
        self.lineage_children = LazyLineageChildrenTable(self)
        object.__setattr__(
            world.lineage, "children", self.lineage_children
        )
        self.genealogy_parents = LazyGenealogyParentTable(self)
        object.__setattr__(
            world.genealogy, "parents", self.genealogy_parents
        )
        self.genealogy_children = LazyGenealogyChildrenTable(self)
        object.__setattr__(
            world.genealogy, "children", self.genealogy_children
        )
        self.community_memberships = LazyCommunityMembershipTable(self)
        object.__setattr__(
            world.communities, "memberships", self.community_memberships
        )
        self.social_edges = LazySocialEdgeTable(self)
        object.__setattr__(world.social, "edges", self.social_edges)
        self.social_adjacency = LazySocialAdjacencyTable(self)
        object.__setattr__(
            world.social, "adjacency", self.social_adjacency
        )
        self.social_partnerships = LazySocialPartnershipTable(self)
        object.__setattr__(
            world.social, "partnerships", self.social_partnerships
        )
        self.skills = LazySkillTable(self)
        object.__setattr__(world.skills, "skills", self.skills)

        self._cross_boundary_links = _seed_cross_boundary_lazy_identity(
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
        self._install_cross_boundary_tracker_baseline()
        self._paged_household_members = {}

        self._lifetime = _LazyLifetime(self)
        object.__setattr__(world, "_ate_persistence_lifetime", self._lifetime)
        world.events._ate_persistence_lifetime = self._lifetime

    def _activate_household_pages(self):
        if self._paged_household_members:
            raise StoreError("household member pages already active")
        for key, household in self.world.households.items():
            def guard(owner=key, record=household):
                self._ensure_people_mutation_allowed()
                if self.world.households.get(owner) is not record:
                    raise StoreError("retained household member alias has obsolete owner")
                if self._paged_household_members.get(owner) is not record.members:
                    raise StoreError("retained household member alias was replaced")
            sequence = LazyHouseholdMembers(
                self.store, self.pin, key, guard=guard,
            )
            object.__setattr__(household, "members", sequence)
            self._paged_household_members[key] = sequence
        self._eager_tracker._paged_household_members = True

    def _household_page_changes(self):
        if not self._paged_household_members:
            return ()
        if set(self.world.households) != set(self._paged_household_members):
            raise StoreError(
                "paged household pilot requires new/deleted household owner integration"
            )
        for key, sequence in self._paged_household_members.items():
            if self.world.households[key].members is not sequence:
                raise StoreError("household members were replaced without page binding")
        return tuple(
            change for sequence in self._paged_household_members.values()
            for change in sequence.pending_changes()
        )

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
        if self._lifecycle_operation is not None:
            raise StoreError(
                "lazy World mutation is blocked during "
                f"{self._lifecycle_operation}"
            )

    def _begin_lifecycle_operation(self, operation, *, allow_stale=False):
        self._ensure_active()
        # A caller can close the backing store directly. Public operations
        # must reject before executing their user-observable callback.
        self.store._ensure_open()
        if self._lifecycle_operation is not None:
            raise StoreError(
                f"reentrant lazy session {operation} is not allowed"
            )
        tracker = self._eager_tracker
        if tracker._cold_step_depth:
            raise StoreError(
                f"{operation} requires a completed simulation step"
            )
        if self.world.__dict__.get("_index_current_people"):
            raise StoreError(
                f"{operation} cannot run inside current_people_scope"
            )
        allowed = self._state == "active" or (
            allow_stale and self._state == "stale"
        )
        if not allowed:
            raise StoreError(
                f"lazy session cannot {operation} while {self._state}"
            )
        self._lifecycle_operation = operation

    def _end_lifecycle_operation(self, operation):
        if self._lifecycle_operation != operation:
            raise StoreError("lazy lifecycle operation guard changed")
        self._lifecycle_operation = None

    def _ensure_hybrid_mutation_allowed(
        self, *, subject=None, field=None, value=None
    ):
        self._ensure_people_mutation_allowed()
        if (
            isinstance(
                subject,
                (
                    Person,
                    MagicAspiration,
                    MagicResource,
                    MaterialLot,
                    CraftedItem,
                    SoulState,
                    MagicUserRecord,
                    AdventureNotice,
                    SocietyApplication,
                    Transmission,
                    MotiveState,
                    Relationship,
                    SkillHistory,
                    LineageNode,
                ),
            )
            and field in RECORD_FIELDS.get(type(subject), ())
            and not _cross_boundary_field_value_is_immutable(value)
        ):
            raise StoreError(
                "cross-boundary lazy record field edits require immutable values"
            )

    def _install_cross_boundary_tracker_baseline(self):
        tracker = self._eager_tracker
        persisted = tracker._cold_persisted_keys.setdefault(
            IDENTITY_LINKS, set()
        )
        for target, owner in self._cross_boundary_links:
            existing = tracker._committed_identity_targets.get(target)
            if existing is not None and existing != owner:
                raise StoreIntegrityError(
                    "cross-boundary identity target conflicts with eager link"
                )
            tracker._committed_identity_targets[target] = owner
            tracker._live_identity_targets[target] = owner
            persisted.add(target)

    def _cross_links_from_tracker(self):
        return tuple(
            sorted(
                (
                    (target, owner)
                    for target, owner
                    in self._eager_tracker._live_identity_targets.items()
                    if _path_under_lazy(target)
                    or _path_under_lazy(owner)
                ),
                key=self.store.codec.encode,
            )
        )

    def _absolute_lazy_occurrence_path(self, occurrence):
        return (
            _owner_path(self.manifest, occurrence.owner)
            + tuple(occurrence.path)
        )

    def _absolute_people_occurrence_path(self, occurrence):
        return self._absolute_lazy_occurrence_path(occurrence)

    def _refresh_cross_boundary_identity(self):
        tracker = self._eager_tracker

        # First let the accepted eager identity index reach the current live
        # graph for only owners actually dirtied by mutation.
        tracker._refresh_identity_index()

        old_by_incarnation = {}
        orphaned_old = []
        for link in tuple(self._cross_boundary_links):
            target, owner = link
            lazy_side = (
                _lazy_occurrence_from_path(target)
                or _lazy_occurrence_from_path(owner)
            )
            if lazy_side is None:
                raise StoreIntegrityError(
                    "recorded cross-boundary link lacks lazy occurrence"
                )
            namespace, key, relative, _expected_type = lazy_side
            incarnation = self._registry.incarnation_for_occurrence(
                Occurrence(namespace, key, relative)
            )
            if incarnation is None:
                orphaned_old.append(link)
            else:
                old_by_incarnation.setdefault(
                    incarnation, []
                ).append(link)

        live_by_incarnation = {
            incarnation: obj
            for incarnation, obj in self._registry.live_bindings()
        }

        lazy_incarnations = {
            incarnation
            for incarnation in live_by_incarnation
            if any(
                occurrence.owner_namespace in {
                    PEOPLE_NAMESPACE,
                    ASPIRATION_NAMESPACE,
                    RESOURCE_NAMESPACE,
                    MATERIAL_LOT_NAMESPACE,
                    MATERIAL_ITEM_NAMESPACE,
                    MATERIAL_LOT_INDEX_NAMESPACE,
                    MATERIAL_ACTIVE_INDEX_NAMESPACE,
                    WALLET_NAMESPACE,
                    TREASURY_NAMESPACE,
                    SOUL_NAMESPACE,
                    ADVANCEMENT_NAMESPACE,
                    INSTITUTION_MAGIC_RECORD_NAMESPACE,
                    INSTITUTION_NOTICE_NAMESPACE,
                    INSTITUTION_APPLICATION_NAMESPACE,
                    TRANSMISSION_NAMESPACE,
                    MOTIVE_NAMESPACE,
                    SOCIAL_EDGE_NAMESPACE,
                    SOCIAL_ADJACENCY_NAMESPACE,
                    SKILL_NAMESPACE,
                    LINEAGE_NODE_NAMESPACE,
                }
                for occurrence in
                self._registry.occurrences_for_incarnation(incarnation)
            )
        }

        removes = list(orphaned_old)
        adds = []
        desired_cross = []
        incarnations = (
            set(old_by_incarnation) | lazy_incarnations
        )

        for incarnation in sorted(incarnations):
            lazy_occurrences = tuple(
                occurrence
                for occurrence
                in self._registry.occurrences_for_incarnation(incarnation)
                if occurrence.owner_namespace in {
                    PEOPLE_NAMESPACE,
                    ASPIRATION_NAMESPACE,
                    RESOURCE_NAMESPACE,
                    MATERIAL_LOT_NAMESPACE,
                    MATERIAL_ITEM_NAMESPACE,
                    MATERIAL_LOT_INDEX_NAMESPACE,
                    MATERIAL_ACTIVE_INDEX_NAMESPACE,
                    WALLET_NAMESPACE,
                    TREASURY_NAMESPACE,
                    SOUL_NAMESPACE,
                    ADVANCEMENT_NAMESPACE,
                    INSTITUTION_MAGIC_RECORD_NAMESPACE,
                    INSTITUTION_NOTICE_NAMESPACE,
                    INSTITUTION_APPLICATION_NAMESPACE,
                    TRANSMISSION_NAMESPACE,
                    MOTIVE_NAMESPACE,
                    SOCIAL_EDGE_NAMESPACE,
                    SOCIAL_ADJACENCY_NAMESPACE,
                    LINEAGE_NODE_NAMESPACE,
                }
            )
            lazy_paths = {
                self._absolute_lazy_occurrence_path(occurrence)
                for occurrence in lazy_occurrences
            }

            eager_paths = set()
            obj = live_by_incarnation.get(incarnation)
            if obj is not None:
                entry = tracker._identity_index.occurrences.get(id(obj))
                if entry is not None:
                    if entry[0] is not obj:
                        raise StoreIntegrityError(
                            "eager identity address reused for another object"
                        )
                    eager_paths.update(entry[1])

            old_links = tuple(old_by_incarnation.get(incarnation, ()))
            historical_paths = {
                path
                for link in old_links
                for path in link
            }
            group_paths = lazy_paths | eager_paths | historical_paths

            desired_all = ()
            identity_paths = lazy_paths | eager_paths
            if len(identity_paths) > 1:
                desired_all = tuple(
                    tracker._identity_index._links_for(identity_paths)
                )
            desired_tokens = {
                self.store.codec.encode(link): link
                for link in desired_all
            }

            current_all = tuple(
                (target, owner)
                for target, owner
                in tracker._live_identity_targets.items()
                if target in group_paths or owner in group_paths
            )
            current_tokens = {
                self.store.codec.encode(link): link
                for link in current_all
            }

            removes.extend(
                current_tokens[token]
                for token in current_tokens.keys()
                - desired_tokens.keys()
            )
            adds.extend(
                desired_tokens[token]
                for token in desired_tokens.keys()
                - current_tokens.keys()
            )
            desired_cross.extend(
                link for link in desired_all
                if _path_under_lazy(link[0])
                or _path_under_lazy(link[1])
            )

        remove_map = {
            self.store.codec.encode(link): link for link in removes
        }
        add_map = {
            self.store.codec.encode(link): link for link in adds
        }
        overlap = remove_map.keys() & add_map.keys()
        for token in tuple(overlap):
            remove_map.pop(token, None)
            add_map.pop(token, None)

        if remove_map or add_map:
            tracker._merge_current_identity_patch(
                tuple(remove_map[token] for token in sorted(remove_map)),
                tuple(add_map[token] for token in sorted(add_map)),
            )

        desired_cross_map = {
            self.store.codec.encode(link): link
            for link in desired_cross
        }
        self._cross_boundary_links = tuple(
            desired_cross_map[token]
            for token in sorted(desired_cross_map)
        )

    def _advancement_occurrence(self, key, path=()):
        return Occurrence(ADVANCEMENT_NAMESPACE, key, tuple(path))

    @staticmethod
    def _advancement_identity_compatible(current, live):
        if is_dataclass(current) or is_dataclass(live):
            return type(current) is type(live)
        if isinstance(current, dict) or isinstance(live, dict):
            return isinstance(current, dict) and isinstance(live, dict)
        if isinstance(current, list) or isinstance(live, list):
            return isinstance(current, list) and isinstance(live, list)
        if isinstance(current, set) or isinstance(live, set):
            return isinstance(current, set) and isinstance(live, set)
        return type(current) is type(live)

    def _wrap_advancement_value(
        self, key, value, path=(), memo=None
    ):
        if memo is None:
            memo = {}
        cls = type(value)
        if value is None or cls in (
            bool, int, float, str, bytes, FrozenDict, FrozenList
        ):
            return value
        ident = id(value)
        if ident in memo:
            return memo[ident]

        if is_dataclass(value):
            memo[ident] = value
            if isinstance(value, IndexedRecord):
                object.__setattr__(
                    value, "_index_table", weakref.ref(self.advancement_paths)
                )
                object.__setattr__(value, "_index_key", key)
            for name in RECORD_FIELDS.get(cls, ()):
                child = getattr(value, name)
                wrapped = self._wrap_advancement_value(
                    key,
                    child,
                    path + (("field", name),),
                    memo,
                )
                if wrapped is not child:
                    object.__setattr__(value, name, wrapped)
            return value

        if isinstance(value, dict):
            if isinstance(value, LazyTrackedDict):
                wrapper = value
                wrapper._attach(self.advancement_paths, key)
                memo[ident] = wrapper
                for child_key, child in tuple(dict.items(wrapper)):
                    wrapped = self._wrap_advancement_value(
                        key,
                        child,
                        path + (("key", child_key),),
                        memo,
                    )
                    if wrapped is not child:
                        dict.__setitem__(wrapper, child_key, wrapped)
                return wrapper
            wrapper = LazyTrackedDict()
            memo[ident] = wrapper
            wrapper._attach(self.advancement_paths, key)
            for child_key, child in value.items():
                dict.__setitem__(
                    wrapper,
                    child_key,
                    self._wrap_advancement_value(
                        key,
                        child,
                        path + (("key", child_key),),
                        memo,
                    ),
                )
            return wrapper

        if isinstance(value, list):
            if isinstance(value, LazySoulTrackedList):
                wrapper = value
                wrapper._attach(self.advancement_paths, key, path)
                memo[ident] = wrapper
                for index, child in enumerate(tuple(wrapper)):
                    wrapped = self._wrap_advancement_value(
                        key,
                        child,
                        path + (("index", index),),
                        memo,
                    )
                    if wrapped is not child:
                        list.__setitem__(wrapper, index, wrapped)
                return wrapper
            wrapper = LazySoulTrackedList()
            memo[ident] = wrapper
            wrapper._attach(self.advancement_paths, key, path)
            for index, child in enumerate(value):
                list.append(
                    wrapper,
                    self._wrap_advancement_value(
                        key,
                        child,
                        path + (("index", index),),
                        memo,
                    ),
                )
            return wrapper

        if isinstance(value, set):
            if isinstance(value, LazySoulTrackedSet):
                wrapper = value
                wrapper._attach(self.advancement_paths, key, path)
                memo[ident] = wrapper
                return wrapper
            wrapper = LazySoulTrackedSet(value)
            memo[ident] = wrapper
            wrapper._attach(self.advancement_paths, key, path)
            return wrapper

        if cls is tuple:
            memo[ident] = value
            wrapped = tuple(
                self._wrap_advancement_value(
                    key,
                    child,
                    path + (("index", index),),
                    memo,
                )
                for index, child in enumerate(value)
            )
            memo[ident] = wrapped
            return wrapped

        return value

    def _probe_advancement_occurrences(self, key, path):
        owner = (ADVANCEMENT_NAMESPACE, key)
        owner_path = _owner_path(self.manifest, owner)
        probe = IdentityOccurrenceIndex(
            self.store.codec,
            RECORD_FIELDS,
            mutable_event_tail_only=True,
        )
        probe.bootstrap([(owner, path, owner_path)])
        rows = []
        for _ident, obj, absolute in probe.owner_occurrences[owner]:
            if absolute[: len(owner_path)] != owner_path:
                raise StoreIntegrityError(
                    "advancement identity occurrence escaped its owner"
                )
            rows.append((tuple(absolute[len(owner_path):]), obj))
        return tuple(rows)

    def _reconcile_advancement_graph(self, key, path):
        path = self._wrap_advancement_value(key, path)
        current = {}
        for relative, obj in self._probe_advancement_occurrences(key, path):
            occurrence = self._advancement_occurrence(key, relative)
            incarnation = self._registry.incarnation_for_object(obj)
            if incarnation is None:
                incarnation = self._registry.bind(obj)
            self._registry.attach_occurrence(obj, occurrence)
            current[relative] = incarnation.value

        current_occurrences = {
            self._advancement_occurrence(key, relative)
            for relative in current
        }
        for occurrence in self._registry.occurrences_for_owner(
            ADVANCEMENT_NAMESPACE, key
        ):
            if occurrence not in current_occurrences:
                self._registry.detach_occurrence(occurrence)
        return path, current

    def _advancement_incarnation_labels(self, key, path):
        _path, labels = self._reconcile_advancement_graph(key, path)
        return labels

    def _bind_loaded_advancement_path(self, key, path):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, ADVANCEMENT_NAMESPACE, key
            )
        )
        if () not in labels:
            raise StoreIntegrityError(
                "lazy advancement path lacks top-level occurrence label"
            )
        path = self._wrap_advancement_value(key, path)

        for relative, incarnation_value in sorted(
            labels.items(),
            key=lambda item: (
                len(item[0]),
                self.store.codec.encode(item[0]),
            ),
        ):
            incarnation = IncarnationId(
                self.store.store_identity, incarnation_value
            )
            try:
                current = _relative_get(path, relative)
            except (KeyError, IndexError, AttributeError, TypeError) as exc:
                raise StoreIntegrityError(
                    "lazy advancement identity path is absent from payload"
                ) from exc
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None and live is not current:
                if not self._advancement_identity_compatible(current, live):
                    raise StoreIntegrityError(
                        "advancement incarnation has incompatible live type"
                    )
                path = _relative_set(path, relative, live)
                current = live
            if live is None:
                try:
                    self._registry.bind(
                        current,
                        self._advancement_occurrence(key, relative),
                        incarnation=incarnation,
                    )
                except TypeError as exc:
                    raise StoreIntegrityError(
                        "advancement mutable identity is not weak-referenceable"
                    ) from exc
            self._registry.attach_existing(
                incarnation,
                self._advancement_occurrence(key, relative),
            )

        path = self._wrap_advancement_value(key, path)
        actual_paths = {
            relative
            for relative, _obj in self._probe_advancement_occurrences(
                key, path
            )
        }
        if actual_paths != set(labels):
            raise StoreIntegrityError(
                "lazy advancement occurrence labels are incomplete or extra"
            )
        self.advancement_paths._baseline_identity_labels[key] = dict(labels)
        self.advancement_paths._baseline_incarnation[key] = labels[()]
        return path

    def _bind_assigned_advancement_path(self, key, path):
        path, _labels = self._reconcile_advancement_graph(key, path)
        return path

    def _detach_advancement_runtime_bindings(self, key, path):
        for relative, obj in self._probe_advancement_occurrences(key, path):
            occurrence = self._advancement_occurrence(key, relative)
            incarnation = self._registry.incarnation_for_object(obj)
            if incarnation is not None:
                self._registry.detach_occurrence(
                    occurrence, expected=incarnation
                )
            if isinstance(obj, IndexedRecord):
                ref = obj.__dict__.get("_index_table")
                table = None if ref is None else ref()
                if table is self.advancement_paths:
                    object.__setattr__(obj, "_index_table", None)
            elif isinstance(obj, LazyTrackedDict):
                obj._detach(self.advancement_paths, key)
            elif isinstance(obj, (LazySoulTrackedList, LazySoulTrackedSet)):
                obj._detach(self.advancement_paths, key, relative)

    def _detach_assigned_advancement_path(self, key, path):
        self._detach_advancement_runtime_bindings(key, path)

    def _detach_unloaded_advancement_path(self, key):
        labels = self.advancement_paths._baseline_labels(key)
        for relative, incarnation_value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, incarnation_value
            )
            occurrence = self._advancement_occurrence(key, relative)
            self._registry.attach_existing(incarnation, occurrence)
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )

    def _top_occurrence(self, key):
        return Occurrence(PEOPLE_NAMESPACE, key, ())

    def _aspiration_occurrence(self, key):
        return Occurrence(ASPIRATION_NAMESPACE, key, ())

    def _bind_assigned_aspiration(self, key, aspiration):
        existing = self._registry.incarnation_for_object(aspiration)
        if existing is None:
            existing = self._registry.bind(aspiration)
        occurrences = self._registry.occurrences_for_incarnation(existing)
        foreign = [
            item for item in occurrences
            if item != self._aspiration_occurrence(key)
        ]
        if foreign:
            raise StoreError(
                "one aspiration incarnation cannot be assigned "
                "to multiple lazy owners"
            )
        self._registry.attach_occurrence(
            aspiration, self._aspiration_occurrence(key)
        )
        return existing

    def _detach_assigned_aspiration(self, key, aspiration):
        incarnation = self._registry.incarnation_for_object(aspiration)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._aspiration_occurrence(key),
                expected=incarnation,
            )

    def _detach_unloaded_aspiration(self, key):
        baseline = self.aspirations._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        self._registry.attach_existing(
            incarnation, self._aspiration_occurrence(key)
        )
        self._registry.detach_occurrence(
            self._aspiration_occurrence(key),
            expected=incarnation,
        )

    def _bind_loaded_aspiration(self, key, aspiration):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, ASPIRATION_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy aspiration occurrence labels are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, MagicAspiration):
                raise StoreIntegrityError(
                    "aspiration incarnation is bound to wrong type"
                )
            result = live
        else:
            result = aspiration
            self._registry.bind(
                result,
                self._aspiration_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._aspiration_occurrence(key)
        )
        self.aspirations._baseline_incarnation[key] = incarnation.value
        return result


    def _owner_bucket_occurrence(self, key):
        return Occurrence(OWNER_INDEX_NAMESPACE, key, ())

    def _bind_assigned_owner_bucket(self, key, bucket):
        if isinstance(bucket, LazyTrackedSet):
            wrapper = bucket
            wrapper._attach(self.owner_index, key)
        else:
            wrapper = LazyTrackedSet(bucket, self.owner_index, key)

        existing = self._registry.incarnation_for_object(wrapper)
        if existing is None:
            existing = self._registry.bind(wrapper)
        occurrences = self._registry.occurrences_for_incarnation(existing)
        foreign = [
            item for item in occurrences
            if item != self._owner_bucket_occurrence(key)
        ]
        if foreign:
            raise StoreError(
                "one owner-index bucket cannot be assigned to multiple owners"
            )
        self._registry.attach_occurrence(
            wrapper, self._owner_bucket_occurrence(key)
        )
        return wrapper

    def _detach_assigned_owner_bucket(self, key, bucket):
        incarnation = self._registry.incarnation_for_object(bucket)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._owner_bucket_occurrence(key),
                expected=incarnation,
            )
        if isinstance(bucket, LazyTrackedSet):
            bucket._detach()

    def _detach_unloaded_owner_bucket(self, key):
        baseline = self.owner_index._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._owner_bucket_occurrence(key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_owner_bucket(self, key, bucket):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, OWNER_INDEX_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy owner-index occurrence labels are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, LazyTrackedSet):
                raise StoreIntegrityError(
                    "owner-index incarnation is bound to wrong type"
                )
            live._attach(self.owner_index, key)
            result = live
        else:
            result = LazyTrackedSet(bucket, self.owner_index, key)
            self._registry.bind(
                result,
                self._owner_bucket_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._owner_bucket_occurrence(key)
        )
        self.owner_index._baseline_incarnation[key] = incarnation.value
        return result

    def _social_edge_occurrence(self, key, path=()):
        return Occurrence(SOCIAL_EDGE_NAMESPACE, key, tuple(path))

    def _live_social_edge_for_key(self, key):
        incarnation = self._registry.incarnation_for_occurrence(
            self._social_edge_occurrence(key)
        )
        if incarnation is None:
            return None
        value = self._registry.object_for_incarnation(incarnation)
        return value if isinstance(value, Relationship) else None

    def _bind_social_history(self, key, values, *, incarnation=None):
        occurrence = self._social_edge_occurrence(
            key, LazySocialEdgeTable._history_path
        )
        if incarnation is not None:
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None:
                if not isinstance(live, LazyTrackedList):
                    raise StoreIntegrityError(
                        "social history incarnation is bound to wrong type"
                    )
                live._attach(self.social_edges, key)
                self._registry.attach_existing(incarnation, occurrence)
                return live
        if isinstance(values, LazyTrackedList):
            wrapper = values
            wrapper._attach(self.social_edges, key)
        else:
            wrapper = LazyTrackedList(values, self.social_edges, key)
        existing = self._registry.incarnation_for_object(wrapper)
        if incarnation is not None:
            if existing is None:
                self._registry.bind(
                    wrapper, occurrence, incarnation=incarnation
                )
            elif existing != incarnation:
                raise StoreIntegrityError(
                    "social history is bound to wrong incarnation"
                )
            self._registry.attach_existing(incarnation, occurrence)
        else:
            self._registry.bind(wrapper, occurrence)
        return wrapper

    def _social_edge_incarnation_labels(self, key, record):
        top = self._registry.incarnation_for_object(record)
        history = self._registry.incarnation_for_object(
            record.shared_history
        )
        if top is None or history is None:
            raise StoreIntegrityError(
                "lazy social edge has incomplete runtime incarnation labels"
            )
        return {
            (): top.value,
            LazySocialEdgeTable._history_path: history.value,
        }

    def _bind_assigned_social_edge(self, key, record):
        top_occurrence = self._social_edge_occurrence(key)
        existing = self._registry.incarnation_for_object(record)
        if existing is None:
            existing = self._registry.bind(record)
        self._registry.attach_occurrence(record, top_occurrence)
        history = self._bind_social_history(
            key, record.shared_history
        )
        if history is not record.shared_history:
            object.__setattr__(record, "shared_history", history)
        return record

    def _detach_assigned_social_edge(self, key, record):
        labels = self._social_edge_incarnation_labels(key, record)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            self._registry.detach_occurrence(
                self._social_edge_occurrence(key, path),
                expected=incarnation,
            )
        if isinstance(record.shared_history, LazyTrackedList):
            record.shared_history._detach()

    def _detach_unloaded_social_edge(self, key):
        labels = self.social_edges._baseline_labels(key)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            occurrence = self._social_edge_occurrence(key, path)
            self._registry.attach_existing(incarnation, occurrence)
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )

    def _replace_social_history(self, key, record, old, new):
        occurrence = self._social_edge_occurrence(
            key, LazySocialEdgeTable._history_path
        )
        old_incarnation = self._registry.incarnation_for_object(old)
        if old_incarnation is not None:
            self._registry.detach_occurrence(
                occurrence, expected=old_incarnation
            )
        if isinstance(old, LazyTrackedList):
            old._detach()
        replacement = self._bind_social_history(key, new)
        object.__setattr__(record, "shared_history", replacement)

    def _bind_loaded_social_edge(self, key, record):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, SOCIAL_EDGE_NAMESPACE, key
            )
        )
        expected_paths = {
            (), LazySocialEdgeTable._history_path
        }
        if set(labels) != expected_paths:
            raise StoreIntegrityError(
                "lazy social edge occurrence labels are incomplete or extra"
            )
        top_incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(top_incarnation)
        if live is not None:
            if not isinstance(live, Relationship):
                raise StoreIntegrityError(
                    "social edge incarnation is bound to wrong type"
                )
            result = live
        else:
            result = record
            self._registry.bind(
                result,
                self._social_edge_occurrence(key),
                incarnation=top_incarnation,
            )
        self._registry.attach_existing(
            top_incarnation, self._social_edge_occurrence(key)
        )
        history_incarnation = IncarnationId(
            self.store.store_identity,
            labels[LazySocialEdgeTable._history_path],
        )
        history = self._bind_social_history(
            key,
            result.shared_history,
            incarnation=history_incarnation,
        )
        if history is not result.shared_history:
            object.__setattr__(result, "shared_history", history)
        self.social_edges._baseline_identity_labels[key] = labels
        return result

    def _social_adjacency_occurrence(self, key):
        return Occurrence(SOCIAL_ADJACENCY_NAMESPACE, key, ())

    def _bind_assigned_social_adjacency(self, key, values):
        if isinstance(values, LazyTrackedSet):
            bucket = values
            bucket._attach(self.social_adjacency, key)
        else:
            bucket = LazyTrackedSet(values, self.social_adjacency, key)
        existing = self._registry.incarnation_for_object(bucket)
        occurrence = self._social_adjacency_occurrence(key)
        if existing is None:
            existing = self._registry.bind(bucket)
        self._registry.attach_occurrence(bucket, occurrence)
        return bucket

    def _detach_assigned_social_adjacency(self, key, bucket):
        incarnation = self._registry.incarnation_for_object(bucket)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._social_adjacency_occurrence(key),
                expected=incarnation,
            )
        if isinstance(bucket, LazyTrackedSet):
            bucket._detach()

    def _detach_unloaded_social_adjacency(self, key):
        baseline = self.social_adjacency._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._social_adjacency_occurrence(key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_social_adjacency(self, key, values):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, SOCIAL_ADJACENCY_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy social adjacency occurrence labels are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, LazyTrackedSet):
                raise StoreIntegrityError(
                    "social adjacency incarnation is bound to wrong type"
                )
            live._attach(self.social_adjacency, key)
            result = live
        else:
            result = LazyTrackedSet(
                values, self.social_adjacency, key
            )
            self._registry.bind(
                result,
                self._social_adjacency_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._social_adjacency_occurrence(key)
        )
        self.social_adjacency._baseline_incarnation[key] = incarnation.value
        return result

    def _resource_occurrence(self, key, path=()):
        return Occurrence(RESOURCE_NAMESPACE, key, tuple(path))

    def _live_resource_for_key(self, key):
        incarnation = self._registry.incarnation_for_occurrence(
            self._resource_occurrence(key)
        )
        if incarnation is None:
            return None
        value = self._registry.object_for_incarnation(incarnation)
        return value if isinstance(value, MagicResource) else None

    def _bind_resource_transfers(
        self, key, transfers, *, incarnation=None
    ):
        occurrence = self._resource_occurrence(
            key, LazyResourceTable._transfer_path
        )
        if incarnation is not None:
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None:
                if not isinstance(live, LazyTrackedList):
                    raise StoreError(
                        "cross-boundary resource transfer-list sharing "
                        "requires an explicit lazy-list authority"
                    )
                live._attach(self.resources, key)
                self._registry.attach_existing(incarnation, occurrence)
                return live

        if isinstance(transfers, LazyTrackedList):
            wrapper = transfers
            wrapper._attach(self.resources, key)
        else:
            wrapper = LazyTrackedList(transfers, self.resources, key)

        existing = self._registry.incarnation_for_object(wrapper)
        if incarnation is not None:
            if existing is None:
                self._registry.bind(
                    wrapper, occurrence, incarnation=incarnation
                )
            elif existing != incarnation:
                raise StoreIntegrityError(
                    "resource transfers bound to wrong incarnation"
                )
            self._registry.attach_existing(incarnation, occurrence)
        else:
            self._registry.bind(wrapper, occurrence)
        return wrapper

    def _resource_incarnation_labels(self, key, resource):
        top = self._registry.incarnation_for_object(resource)
        transfers = self._registry.incarnation_for_object(
            resource.transfers
        )
        if top is None or transfers is None:
            raise StoreIntegrityError(
                "lazy resource has incomplete runtime incarnation labels"
            )
        return {
            (): top.value,
            LazyResourceTable._transfer_path: transfers.value,
        }

    def _bind_assigned_resource(self, key, resource):
        top_occurrence = self._resource_occurrence(key)
        existing = self._registry.incarnation_for_object(resource)
        if existing is None:
            existing = self._registry.bind(resource)
        self._registry.attach_occurrence(resource, top_occurrence)

        transfers = self._bind_resource_transfers(
            key, resource.transfers
        )
        if transfers is not resource.transfers:
            object.__setattr__(resource, "transfers", transfers)
        return resource

    def _detach_assigned_resource(self, key, resource):
        labels = self._resource_incarnation_labels(key, resource)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            self._registry.detach_occurrence(
                self._resource_occurrence(key, path),
                expected=incarnation,
            )
        if isinstance(resource.transfers, LazyTrackedList):
            resource.transfers._detach()

    def _detach_unloaded_resource(self, key):
        labels = self.resources._baseline_labels(key)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            occurrence = self._resource_occurrence(key, path)
            self._registry.attach_existing(incarnation, occurrence)
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )

    def _replace_resource_transfers(
        self, key, resource, old, new
    ):
        occurrence = self._resource_occurrence(
            key, LazyResourceTable._transfer_path
        )
        old_incarnation = self._registry.incarnation_for_object(old)
        if old_incarnation is not None:
            self._registry.detach_occurrence(
                occurrence, expected=old_incarnation
            )
        if isinstance(old, LazyTrackedList):
            old._detach()
        replacement = self._bind_resource_transfers(key, new)
        object.__setattr__(resource, "transfers", replacement)

    def _bind_loaded_resource(self, key, resource):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, RESOURCE_NAMESPACE, key
            )
        )
        expected_paths = {
            (), LazyResourceTable._transfer_path
        }
        if set(labels) != expected_paths:
            raise StoreIntegrityError(
                "lazy resource occurrence labels are incomplete or extra"
            )

        top_incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(top_incarnation)
        if live is not None:
            if not isinstance(live, MagicResource):
                raise StoreIntegrityError(
                    "resource incarnation is bound to wrong type"
                )
            result = live
        else:
            result = resource
            self._registry.bind(
                result,
                self._resource_occurrence(key),
                incarnation=top_incarnation,
            )
        self._registry.attach_existing(
            top_incarnation, self._resource_occurrence(key)
        )

        transfer_incarnation = IncarnationId(
            self.store.store_identity,
            labels[LazyResourceTable._transfer_path],
        )
        transfers = self._bind_resource_transfers(
            key,
            result.transfers,
            incarnation=transfer_incarnation,
        )
        if transfers is not result.transfers:
            object.__setattr__(result, "transfers", transfers)
        self.resources._baseline_identity_labels[key] = labels
        return result



    def _institution_table(self, namespace):
        table = {
            INSTITUTION_MAGIC_RECORD_NAMESPACE: self.institution_magic_records,
            INSTITUTION_NOTICE_NAMESPACE: self.institution_notices,
            INSTITUTION_APPLICATION_NAMESPACE: self.institution_applications,
            TRANSMISSION_NAMESPACE: self.transmissions,
            MOTIVE_NAMESPACE: self.motives,
            LINEAGE_NODE_NAMESPACE: self.lineage_nodes,
        }.get(namespace)
        if table is None:
            raise StoreIntegrityError(
                f"unknown lazy institution namespace: {namespace}"
            )
        return table

    def _institution_occurrence(self, namespace, key):
        return Occurrence(namespace, key, ())

    def _bind_assigned_institution_record(
        self, table, namespace, key, record
    ):
        existing = self._registry.incarnation_for_object(record)
        occurrence = self._institution_occurrence(namespace, key)
        if existing is None:
            existing = self._registry.bind(record)
        occurrences = self._registry.occurrences_for_incarnation(existing)
        foreign_lazy = [
            item
            for item in occurrences
            if item.owner_namespace in {
                INSTITUTION_MAGIC_RECORD_NAMESPACE,
                INSTITUTION_NOTICE_NAMESPACE,
                INSTITUTION_APPLICATION_NAMESPACE,
                TRANSMISSION_NAMESPACE,
                MOTIVE_NAMESPACE,
                LINEAGE_NODE_NAMESPACE,
            }
            and item != occurrence
        ]
        if foreign_lazy:
            raise StoreError(
                "one scalar record incarnation cannot own "
                "multiple lazy record keys"
            )
        self._registry.attach_occurrence(record, occurrence)
        return record

    def _detach_assigned_institution_record(
        self, table, namespace, key, record
    ):
        del table
        incarnation = self._registry.incarnation_for_object(record)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._institution_occurrence(namespace, key),
                expected=incarnation,
            )

    def _detach_unloaded_institution_record(
        self, table, namespace, key
    ):
        baseline = table._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._institution_occurrence(namespace, key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_institution_record(
        self, table, namespace, key, record, expected_type
    ):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, namespace, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy scalar record occurrence labels "
                "are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, expected_type):
                raise StoreIntegrityError(
                    "scalar record incarnation is bound to wrong type"
                )
            result = live
        else:
            result = record
            self._registry.bind(
                result,
                self._institution_occurrence(namespace, key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation,
            self._institution_occurrence(namespace, key),
        )
        table._baseline_incarnation[key] = incarnation.value
        return result

    def _material_item_occurrence(self, key):
        return Occurrence(MATERIAL_ITEM_NAMESPACE, key, ())

    def _bind_assigned_material_item(self, key, item):
        existing = self._registry.incarnation_for_object(item)
        if existing is None:
            existing = self._registry.bind(item)
        occurrences = self._registry.occurrences_for_incarnation(existing)
        foreign = [
            occurrence
            for occurrence in occurrences
            if occurrence != self._material_item_occurrence(key)
        ]
        if foreign:
            raise StoreError(
                "one crafted-item incarnation cannot be assigned "
                "to multiple lazy owners"
            )
        self._registry.attach_occurrence(
            item, self._material_item_occurrence(key)
        )
        return item

    def _detach_assigned_material_item(self, key, item):
        incarnation = self._registry.incarnation_for_object(item)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._material_item_occurrence(key),
                expected=incarnation,
            )

    def _detach_unloaded_material_item(self, key):
        baseline = self.material_items._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._material_item_occurrence(key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_material_item(self, key, item):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, MATERIAL_ITEM_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy crafted-item occurrence labels are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, CraftedItem):
                raise StoreIntegrityError(
                    "crafted-item incarnation is bound to wrong type"
                )
            result = live
        else:
            result = item
            self._registry.bind(
                result,
                self._material_item_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._material_item_occurrence(key)
        )
        self.material_items._baseline_incarnation[key] = incarnation.value
        return result

    def _material_lot_index_occurrence(self, key):
        return Occurrence(MATERIAL_LOT_INDEX_NAMESPACE, key, ())

    def _bind_assigned_material_lot_index(self, key, values):
        if isinstance(values, LazyTrackedIdList):
            wrapper = values
            wrapper._attach(self.material_lot_index, key)
        else:
            wrapper = LazyTrackedIdList(
                values, self.material_lot_index, key
            )
        existing = self._registry.incarnation_for_object(wrapper)
        if existing is None:
            existing = self._registry.bind(wrapper)
        occurrences = self._registry.occurrences_for_incarnation(existing)
        foreign = [
            occurrence
            for occurrence in occurrences
            if occurrence != self._material_lot_index_occurrence(key)
        ]
        if foreign:
            raise StoreError(
                "one material lot-index list cannot be assigned "
                "to multiple lazy owners"
            )
        self._registry.attach_occurrence(
            wrapper, self._material_lot_index_occurrence(key)
        )
        return wrapper

    def _detach_assigned_material_lot_index(self, key, values):
        incarnation = self._registry.incarnation_for_object(values)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._material_lot_index_occurrence(key),
                expected=incarnation,
            )
        if isinstance(values, LazyTrackedIdList):
            values._detach()

    def _detach_unloaded_material_lot_index(self, key):
        baseline = self.material_lot_index._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._material_lot_index_occurrence(key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_material_lot_index(self, key, values):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, MATERIAL_LOT_INDEX_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy material lot-index occurrence labels are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, LazyTrackedIdList):
                raise StoreIntegrityError(
                    "material lot-index incarnation is bound to wrong type"
                )
            live._attach(self.material_lot_index, key)
            result = live
        else:
            result = LazyTrackedIdList(
                values, self.material_lot_index, key
            )
            self._registry.bind(
                result,
                self._material_lot_index_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._material_lot_index_occurrence(key)
        )
        self.material_lot_index._baseline_incarnation[key] = incarnation.value
        return result

    def _material_active_index_occurrence(self, key):
        return Occurrence(MATERIAL_ACTIVE_INDEX_NAMESPACE, key, ())

    def _bind_assigned_material_active_index(self, key, values):
        if isinstance(values, LazyTrackedSet):
            wrapper = values
            wrapper._attach(self.material_active_index, key)
        else:
            wrapper = LazyTrackedSet(
                values, self.material_active_index, key
            )
        existing = self._registry.incarnation_for_object(wrapper)
        if existing is None:
            existing = self._registry.bind(wrapper)
        occurrences = self._registry.occurrences_for_incarnation(existing)
        foreign = [
            occurrence
            for occurrence in occurrences
            if occurrence != self._material_active_index_occurrence(key)
        ]
        if foreign:
            raise StoreError(
                "one material active-index set cannot be assigned "
                "to multiple lazy owners"
            )
        self._registry.attach_occurrence(
            wrapper, self._material_active_index_occurrence(key)
        )
        return wrapper

    def _detach_assigned_material_active_index(self, key, values):
        incarnation = self._registry.incarnation_for_object(values)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._material_active_index_occurrence(key),
                expected=incarnation,
            )
        if isinstance(values, LazyTrackedSet):
            values._detach()

    def _detach_unloaded_material_active_index(self, key):
        baseline = self.material_active_index._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._material_active_index_occurrence(key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_material_active_index(self, key, values):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, MATERIAL_ACTIVE_INDEX_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy material active-index occurrence labels "
                "are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, LazyTrackedSet):
                raise StoreIntegrityError(
                    "material active-index incarnation is bound to wrong type"
                )
            live._attach(self.material_active_index, key)
            result = live
        else:
            result = LazyTrackedSet(
                values, self.material_active_index, key
            )
            self._registry.bind(
                result,
                self._material_active_index_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._material_active_index_occurrence(key)
        )
        self.material_active_index._baseline_incarnation[key] = incarnation.value
        return result

    def _material_lot_occurrence(self, key, path=()):
        return Occurrence(MATERIAL_LOT_NAMESPACE, key, tuple(path))

    def _live_material_lot_for_key(self, key):
        incarnation = self._registry.incarnation_for_occurrence(
            self._material_lot_occurrence(key)
        )
        if incarnation is None:
            return None
        value = self._registry.object_for_incarnation(incarnation)
        return value if isinstance(value, MaterialLot) else None

    def _bind_material_lot_transfers(
        self, key, transfers, *, incarnation=None
    ):
        occurrence = self._material_lot_occurrence(
            key, LazyMaterialLotTable._transfer_path
        )
        if incarnation is not None:
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None:
                if not isinstance(live, LazyTrackedList):
                    raise StoreError(
                        "cross-boundary material transfer-list sharing "
                        "requires an explicit lazy-list authority"
                    )
                live._attach(self.material_lots, key)
                self._registry.attach_existing(incarnation, occurrence)
                return live

        if isinstance(transfers, LazyTrackedList):
            wrapper = transfers
            wrapper._attach(self.material_lots, key)
        else:
            wrapper = LazyTrackedList(
                transfers, self.material_lots, key
            )

        existing = self._registry.incarnation_for_object(wrapper)
        if incarnation is not None:
            if existing is None:
                self._registry.bind(
                    wrapper, occurrence, incarnation=incarnation
                )
            elif existing != incarnation:
                raise StoreIntegrityError(
                    "material transfers bound to wrong incarnation"
                )
            self._registry.attach_existing(incarnation, occurrence)
        else:
            self._registry.bind(wrapper, occurrence)
        return wrapper

    def _material_lot_incarnation_labels(self, key, lot):
        top = self._registry.incarnation_for_object(lot)
        transfers = self._registry.incarnation_for_object(lot.transfers)
        if top is None or transfers is None:
            raise StoreIntegrityError(
                "lazy material lot has incomplete runtime incarnation labels"
            )
        return {
            (): top.value,
            LazyMaterialLotTable._transfer_path: transfers.value,
        }

    def _bind_assigned_material_lot(self, key, lot):
        existing = self._registry.incarnation_for_object(lot)
        if existing is None:
            existing = self._registry.bind(lot)
        self._registry.attach_occurrence(
            lot, self._material_lot_occurrence(key)
        )
        transfers = self._bind_material_lot_transfers(
            key, lot.transfers
        )
        if transfers is not lot.transfers:
            object.__setattr__(lot, "transfers", transfers)
        return lot

    def _detach_assigned_material_lot(self, key, lot):
        labels = self._material_lot_incarnation_labels(key, lot)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            self._registry.detach_occurrence(
                self._material_lot_occurrence(key, path),
                expected=incarnation,
            )
        if isinstance(lot.transfers, LazyTrackedList):
            lot.transfers._detach()

    def _detach_unloaded_material_lot(self, key):
        labels = self.material_lots._baseline_labels(key)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            occurrence = self._material_lot_occurrence(key, path)
            self._registry.attach_existing(incarnation, occurrence)
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )

    def _replace_material_lot_transfers(
        self, key, lot, old, new
    ):
        occurrence = self._material_lot_occurrence(
            key, LazyMaterialLotTable._transfer_path
        )
        old_incarnation = self._registry.incarnation_for_object(old)
        if old_incarnation is not None:
            self._registry.detach_occurrence(
                occurrence, expected=old_incarnation
            )
        if isinstance(old, LazyTrackedList):
            old._detach()
        replacement = self._bind_material_lot_transfers(key, new)
        object.__setattr__(lot, "transfers", replacement)

    def _bind_loaded_material_lot(self, key, lot):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, MATERIAL_LOT_NAMESPACE, key
            )
        )
        expected_paths = {
            (), LazyMaterialLotTable._transfer_path
        }
        if set(labels) != expected_paths:
            raise StoreIntegrityError(
                "lazy material-lot occurrence labels are incomplete or extra"
            )

        top_incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(top_incarnation)
        if live is not None:
            if not isinstance(live, MaterialLot):
                raise StoreIntegrityError(
                    "material-lot incarnation is bound to wrong type"
                )
            result = live
        else:
            result = lot
            self._registry.bind(
                result,
                self._material_lot_occurrence(key),
                incarnation=top_incarnation,
            )
        self._registry.attach_existing(
            top_incarnation, self._material_lot_occurrence(key)
        )

        transfer_incarnation = IncarnationId(
            self.store.store_identity,
            labels[LazyMaterialLotTable._transfer_path],
        )
        transfers = self._bind_material_lot_transfers(
            key,
            result.transfers,
            incarnation=transfer_incarnation,
        )
        if transfers is not result.transfers:
            object.__setattr__(result, "transfers", transfers)
        self.material_lots._baseline_identity_labels[key] = labels
        return result



    def _attach_indexed_alias_callback(self, obj, incarnation):
        """Bind a live cross-boundary IndexedRecord to its lazy authority.

        A mutable record can first materialize through a nested lazy owner
        (for example, a wallet alias) before its top-level lazy payload is
        loaded. The identity registry already knows the top-level occurrence,
        so install that owner's mutation callback without forcing a payload
        read. Otherwise a mutation through the alias can be invisible to the
        authoritative lazy table until after the edit has happened.
        """
        if not isinstance(obj, IndexedRecord):
            return

        table_by_namespace = {
            PEOPLE_NAMESPACE: self.people,
            ASPIRATION_NAMESPACE: self.aspirations,
            RESOURCE_NAMESPACE: self.resources,
            MATERIAL_LOT_NAMESPACE: self.material_lots,
            MATERIAL_ITEM_NAMESPACE: self.material_items,
            SOUL_NAMESPACE: self.souls,
            ADVANCEMENT_NAMESPACE: self.advancement_paths,
            INSTITUTION_MAGIC_RECORD_NAMESPACE: self.institution_magic_records,
            INSTITUTION_NOTICE_NAMESPACE: self.institution_notices,
            INSTITUTION_APPLICATION_NAMESPACE: self.institution_applications,
            TRANSMISSION_NAMESPACE: self.transmissions,
            MOTIVE_NAMESPACE: self.motives,
            SOCIAL_EDGE_NAMESPACE: self.social_edges,
        }
        owners = []
        for occurrence in self._registry.occurrences_for_incarnation(
            incarnation
        ):
            if occurrence.path:
                continue
            table = table_by_namespace.get(occurrence.owner_namespace)
            if table is None:
                continue
            owners.append((table, occurrence.owner_key))

        if not owners:
            return
        unique = {(id(table), key) for table, key in owners}
        if len(unique) != 1:
            raise StoreIntegrityError(
                "cross-boundary IndexedRecord has multiple lazy authorities"
            )
        table, key = owners[0]
        object.__setattr__(obj, "_index_table", weakref.ref(table))
        object.__setattr__(obj, "_index_key", key)

    def _currency_occurrence(self, namespace, key, path=()):
        return Occurrence(namespace, key, tuple(path))

    def _currency_incarnation_labels(
        self, namespace, key, bucket
    ):
        owner = (namespace, key)
        owner_path = _owner_path(self.manifest, owner)
        probe = IdentityOccurrenceIndex(
            self.store.codec,
            RECORD_FIELDS,
            mutable_event_tail_only=True,
        )
        probe.bootstrap([(owner, bucket, owner_path)])
        labels = {}
        for _ident, obj, path in probe.owner_occurrences[owner]:
            if path[: len(owner_path)] != owner_path:
                raise StoreIntegrityError(
                    "currency identity occurrence escaped its owner"
                )
            relative = tuple(path[len(owner_path):])
            occurrence = self._currency_occurrence(
                namespace, key, relative
            )
            incarnation = self._registry.incarnation_for_object(obj)
            if incarnation is None:
                try:
                    incarnation = self._registry.bind(obj)
                except TypeError as exc:
                    raise StoreIntegrityError(
                        "lazy currency nested mutable identity "
                        "is not weak-referenceable"
                    ) from exc
            self._registry.attach_occurrence(obj, occurrence)
            self._attach_indexed_alias_callback(obj, incarnation)
            labels[relative] = incarnation.value
        if () not in labels:
            raise StoreIntegrityError(
                "lazy currency bucket lacks top-level identity"
            )

        # Reconcile runtime occurrence placement with the bucket's current
        # graph before global P2C link generation. Mutable aliases may move
        # between lazy buckets within one generation; leaving the old
        # occurrence attached would resurrect a stale identity link.
        current_paths = set(labels)
        # Occurrences are already indexed by owner. Scanning every live
        # incarnation here made one wallet/treasury mutation proportional to
        # the entire session identity graph. Reconcile only this bucket.
        for occurrence in self._registry.occurrences_for_owner(
            namespace, key
        ):
            if occurrence.path in current_paths:
                continue
            incarnation = self._registry.incarnation_for_occurrence(
                occurrence
            )
            if incarnation is None:
                raise StoreIntegrityError(
                    "currency owner occurrence lost its incarnation"
                )
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )
        return labels

    def _bind_assigned_currency_bucket(
        self, table, namespace, key, value
    ):
        if isinstance(value, LazyTrackedDict):
            wrapper = value
        else:
            wrapper = LazyTrackedDict(value)
        existing = self._registry.incarnation_for_object(wrapper)
        if existing is None:
            existing = self._registry.bind(wrapper)
        occurrence = self._currency_occurrence(namespace, key)
        self._registry.attach_occurrence(wrapper, occurrence)
        wrapper._attach(table, key)
        # Discover/attach any nested mutable identities immediately. This keeps
        # new cross-owner aliases visible to the same save's link reconciliation.
        self._currency_incarnation_labels(
            namespace, key, wrapper
        )
        return wrapper

    def _detach_assigned_currency_bucket(
        self, table, namespace, key, value
    ):
        labels = self._currency_incarnation_labels(
            namespace, key, value
        )
        for path, incarnation_value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, incarnation_value
            )
            self._registry.detach_occurrence(
                self._currency_occurrence(namespace, key, path),
                expected=incarnation,
            )
        if isinstance(value, LazyTrackedDict):
            value._detach(table, key)

    def _detach_unloaded_currency_bucket(
        self, table, namespace, key
    ):
        labels = (
            table._baseline_labels(key)
            if hasattr(table, "_baseline_labels")
            else {
                (): table._baseline_incarnation_id(key)
            }
        )
        for path, incarnation_value in labels.items():
            if incarnation_value is None:
                continue
            incarnation = IncarnationId(
                self.store.store_identity, incarnation_value
            )
            occurrence = self._currency_occurrence(
                namespace, key, path
            )
            self._registry.attach_existing(
                incarnation, occurrence
            )
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )

    def _bind_loaded_currency_bucket(
        self, table, namespace, key, value
    ):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, namespace, key
            )
        )
        if () not in labels:
            raise StoreIntegrityError(
                "lazy currency bucket lacks top-level occurrence label"
            )

        top_incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(
            top_incarnation
        )
        if live is not None:
            if not isinstance(live, LazyTrackedDict):
                raise StoreIntegrityError(
                    "currency incarnation is bound to wrong live type"
                )
            wrapper = live
        else:
            wrapper = LazyTrackedDict(value)
            self._registry.bind(
                wrapper,
                self._currency_occurrence(namespace, key),
                incarnation=top_incarnation,
            )
        self._registry.attach_existing(
            top_incarnation,
            self._currency_occurrence(namespace, key),
        )
        wrapper._attach(table, key)

        for path, incarnation_value in sorted(
            labels.items(),
            key=lambda item: (
                len(item[0]),
                self.store.codec.encode(item[0]),
            ),
        ):
            if not path:
                continue
            incarnation = IncarnationId(
                self.store.store_identity,
                incarnation_value,
            )
            try:
                current = _relative_get(wrapper, path)
            except (KeyError, IndexError, AttributeError, TypeError) as exc:
                raise StoreIntegrityError(
                    "lazy currency identity path is absent from payload"
                ) from exc
            existing = self._registry.object_for_incarnation(
                incarnation
            )
            if existing is not None and existing is not current:
                _relative_set(wrapper, path, existing)
                current = existing
            if existing is None:
                try:
                    self._registry.bind(
                        current,
                        self._currency_occurrence(
                            namespace, key, path
                        ),
                        incarnation=incarnation,
                    )
                except TypeError as exc:
                    raise StoreIntegrityError(
                        "lazy currency nested persisted identity "
                        "is not weak-referenceable"
                    ) from exc
            self._registry.attach_existing(
                incarnation,
                self._currency_occurrence(namespace, key, path),
            )

        actual = self._currency_incarnation_labels(
            namespace, key, wrapper
        )
        if actual != labels:
            raise StoreIntegrityError(
                "lazy currency bucket occurrence labels "
                "are incomplete or extra"
            )
        table._baseline_incarnation[key] = top_incarnation.value
        if hasattr(table, "_baseline_identity_labels"):
            table._baseline_identity_labels[key] = dict(labels)
        return wrapper


    def _soul_occurrence(self, key, path=()):
        return Occurrence(SOUL_NAMESPACE, key, tuple(path))

    def _live_soul_for_key(self, key):
        incarnation = self._registry.incarnation_for_occurrence(
            self._soul_occurrence(key)
        )
        if incarnation is None:
            return None
        value = self._registry.object_for_incarnation(incarnation)
        return value if isinstance(value, SoulState) else None

    def _bind_soul_set(self, key, field, values, *, incarnation=None):
        occurrence = self._soul_occurrence(
            key, LazySoulTable._nested_paths[field]
        )
        if incarnation is not None:
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None:
                if not isinstance(live, LazySoulTrackedSet):
                    raise StoreIntegrityError(
                        "soul set incarnation is bound to wrong live type"
                    )
                live._attach(self.souls, key, field)
                self._registry.attach_existing(incarnation, occurrence)
                return live
        wrapper = (
            values if isinstance(values, LazySoulTrackedSet)
            else LazySoulTrackedSet(values)
        )
        wrapper._attach(self.souls, key, field)
        existing = self._registry.incarnation_for_object(wrapper)
        if incarnation is not None:
            if existing is None:
                self._registry.bind(
                    wrapper, occurrence, incarnation=incarnation
                )
            elif existing != incarnation:
                raise StoreIntegrityError(
                    "soul set bound to wrong incarnation"
                )
            self._registry.attach_existing(incarnation, occurrence)
        else:
            if existing is None:
                self._registry.bind(wrapper, occurrence)
            else:
                self._registry.attach_occurrence(wrapper, occurrence)
        return wrapper

    def _bind_soul_dict(self, key, field, values, *, incarnation=None):
        occurrence = self._soul_occurrence(
            key, LazySoulTable._nested_paths[field]
        )
        if incarnation is not None:
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None:
                if not isinstance(live, LazyTrackedDict):
                    raise StoreIntegrityError(
                        "soul dict incarnation is bound to wrong live type"
                    )
                live._attach(self.souls, key)
                self._registry.attach_existing(incarnation, occurrence)
                return live
        wrapper = (
            values if isinstance(values, LazyTrackedDict)
            else LazyTrackedDict(values)
        )
        wrapper._attach(self.souls, key)
        existing = self._registry.incarnation_for_object(wrapper)
        if incarnation is not None:
            if existing is None:
                self._registry.bind(
                    wrapper, occurrence, incarnation=incarnation
                )
            elif existing != incarnation:
                raise StoreIntegrityError(
                    "soul dict bound to wrong incarnation"
                )
            self._registry.attach_existing(incarnation, occurrence)
        else:
            if existing is None:
                self._registry.bind(wrapper, occurrence)
            else:
                self._registry.attach_occurrence(wrapper, occurrence)
        return wrapper

    def _bind_soul_list(self, key, field, values, *, incarnation=None):
        occurrence = self._soul_occurrence(
            key, LazySoulTable._nested_paths[field]
        )
        if incarnation is not None:
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None:
                if not isinstance(live, LazySoulTrackedList):
                    raise StoreIntegrityError(
                        "soul list incarnation is bound to wrong live type"
                    )
                live._attach(self.souls, key, field)
                self._registry.attach_existing(incarnation, occurrence)
                return live
        wrapper = (
            values if isinstance(values, LazySoulTrackedList)
            else LazySoulTrackedList(values)
        )
        wrapper._attach(self.souls, key, field)
        existing = self._registry.incarnation_for_object(wrapper)
        if incarnation is not None:
            if existing is None:
                self._registry.bind(
                    wrapper, occurrence, incarnation=incarnation
                )
            elif existing != incarnation:
                raise StoreIntegrityError(
                    "soul list bound to wrong incarnation"
                )
            self._registry.attach_existing(incarnation, occurrence)
        else:
            if existing is None:
                self._registry.bind(wrapper, occurrence)
            else:
                self._registry.attach_occurrence(wrapper, occurrence)
        return wrapper

    def _bind_soul_nested(self, key, field, value, *, incarnation=None):
        if field in ("authorities", "marks"):
            return self._bind_soul_set(
                key, field, value, incarnation=incarnation
            )
        if field == "cosmic_links":
            return self._bind_soul_dict(
                key, field, value, incarnation=incarnation
            )
        if field == "transformations":
            return self._bind_soul_list(
                key, field, value, incarnation=incarnation
            )
        raise StoreIntegrityError("unknown nested soul field")

    def _soul_incarnation_labels(self, key, soul):
        labels = {}
        top = self._registry.incarnation_for_object(soul)
        if top is None:
            raise StoreIntegrityError(
                "lazy soul has no top-level incarnation"
            )
        labels[()] = top.value
        for field, path in LazySoulTable._nested_paths.items():
            value = getattr(soul, field)
            incarnation = self._registry.incarnation_for_object(value)
            if incarnation is None:
                raise StoreIntegrityError(
                    f"lazy soul field {field} has no incarnation"
                )
            labels[path] = incarnation.value
        return labels

    def _bind_assigned_soul(self, key, soul):
        existing = self._registry.incarnation_for_object(soul)
        if existing is None:
            existing = self._registry.bind(soul)
        self._registry.attach_occurrence(
            soul, self._soul_occurrence(key)
        )
        for field in LazySoulTable._nested_paths:
            value = getattr(soul, field)
            wrapper = self._bind_soul_nested(key, field, value)
            if wrapper is not value:
                object.__setattr__(soul, field, wrapper)
        return soul

    def _detach_soul_child_binding(self, key, field, value):
        path = LazySoulTable._nested_paths[field]
        occurrence = self._soul_occurrence(key, path)
        incarnation = self._registry.incarnation_for_object(value)
        if incarnation is not None:
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )
        if isinstance(value, LazySoulTrackedSet):
            value._detach(self.souls, key, field)
        elif isinstance(value, LazySoulTrackedList):
            value._detach(self.souls, key, field)
        elif isinstance(value, LazyTrackedDict):
            value._detach(self.souls, key)

    def _detach_assigned_soul(self, key, soul):
        labels = self._soul_incarnation_labels(key, soul)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            self._registry.detach_occurrence(
                self._soul_occurrence(key, path),
                expected=incarnation,
            )
        for field in LazySoulTable._nested_paths:
            value = getattr(soul, field)
            if isinstance(value, LazySoulTrackedSet):
                value._detach(self.souls, key, field)
            elif isinstance(value, LazySoulTrackedList):
                value._detach(self.souls, key, field)
            elif isinstance(value, LazyTrackedDict):
                value._detach(self.souls, key)

    def _detach_unloaded_soul(self, key):
        labels = self.souls._baseline_labels(key)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            occurrence = self._soul_occurrence(key, path)
            self._registry.attach_existing(incarnation, occurrence)
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )

    def _replace_soul_nested(self, key, soul, field, old, new):
        self._detach_soul_child_binding(key, field, old)
        replacement = self._bind_soul_nested(key, field, new)
        if replacement is not new:
            object.__setattr__(soul, field, replacement)

    def _bind_loaded_soul(self, key, soul):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, SOUL_NAMESPACE, key
            )
        )
        expected_paths = {
            (),
            *LazySoulTable._nested_paths.values(),
        }
        if set(labels) != expected_paths:
            raise StoreIntegrityError(
                "lazy soul occurrence labels are incomplete or extra"
            )
        top_incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(top_incarnation)
        if live is not None:
            if not isinstance(live, SoulState):
                raise StoreIntegrityError(
                    "soul incarnation is bound to wrong live type"
                )
            result = live
        else:
            result = soul
            self._registry.bind(
                result,
                self._soul_occurrence(key),
                incarnation=top_incarnation,
            )
        self._registry.attach_existing(
            top_incarnation, self._soul_occurrence(key)
        )
        for field, path in LazySoulTable._nested_paths.items():
            incarnation = IncarnationId(
                self.store.store_identity, labels[path]
            )
            current = getattr(result, field)
            wrapper = self._bind_soul_nested(
                key, field, current, incarnation=incarnation
            )
            if wrapper is not current:
                object.__setattr__(result, field, wrapper)
        self.souls._baseline_identity_labels[key] = labels
        self.souls._baseline_incarnation[key] = top_incarnation.value
        return result


    def _skill_occurrence(self, key, path=()):
        return Occurrence(SKILL_NAMESPACE, key, tuple(path))

    def _live_skill_for_key(self, key):
        incarnation = self._registry.incarnation_for_occurrence(
            self._skill_occurrence(key)
        )
        if incarnation is None:
            return None
        value = self._registry.object_for_incarnation(incarnation)
        return value if isinstance(value, SkillHistory) else None

    def _bind_skill_list(self, key, field, values, *, incarnation=None):
        occurrence = self._skill_occurrence(
            key, LazySkillTable._nested_paths[field]
        )
        if incarnation is not None:
            live = self._registry.object_for_incarnation(incarnation)
            if live is not None:
                if not isinstance(live, LazySoulTrackedList):
                    raise StoreIntegrityError(
                        "skill list incarnation is bound to wrong live type"
                    )
                live._attach(self.skills, key, field)
                self._registry.attach_existing(incarnation, occurrence)
                return live
        wrapper = (
            values if isinstance(values, LazySoulTrackedList)
            else LazySoulTrackedList(values)
        )
        wrapper._attach(self.skills, key, field)
        existing = self._registry.incarnation_for_object(wrapper)
        if incarnation is not None:
            if existing is None:
                self._registry.bind(
                    wrapper, occurrence, incarnation=incarnation
                )
            elif existing != incarnation:
                raise StoreIntegrityError(
                    "skill list bound to wrong incarnation"
                )
            self._registry.attach_existing(incarnation, occurrence)
        else:
            if existing is None:
                self._registry.bind(wrapper, occurrence)
            else:
                self._registry.attach_occurrence(wrapper, occurrence)
        return wrapper

    def _skill_incarnation_labels(self, key, record):
        labels = {}
        top = self._registry.incarnation_for_object(record)
        if top is None:
            raise StoreIntegrityError(
                "lazy skill history has no top-level incarnation"
            )
        labels[()] = top.value
        for field, path in LazySkillTable._nested_paths.items():
            value = getattr(record, field)
            incarnation = self._registry.incarnation_for_object(value)
            if incarnation is None:
                raise StoreIntegrityError(
                    f"lazy skill field {field} has no incarnation"
                )
            labels[path] = incarnation.value
        return labels

    def _bind_assigned_skill(self, key, record):
        existing = self._registry.incarnation_for_object(record)
        if existing is None:
            existing = self._registry.bind(record)
        self._registry.attach_occurrence(
            record, self._skill_occurrence(key)
        )
        for field in LazySkillTable._nested_paths:
            value = getattr(record, field)
            wrapper = self._bind_skill_list(key, field, value)
            if wrapper is not value:
                object.__setattr__(record, field, wrapper)
        return record

    def _detach_skill_child_binding(self, key, field, value):
        occurrence = self._skill_occurrence(
            key, LazySkillTable._nested_paths[field]
        )
        incarnation = self._registry.incarnation_for_object(value)
        if incarnation is not None:
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )
        if isinstance(value, LazySoulTrackedList):
            value._detach(self.skills, key, field)

    def _detach_assigned_skill(self, key, record):
        labels = self._skill_incarnation_labels(key, record)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            self._registry.detach_occurrence(
                self._skill_occurrence(key, path),
                expected=incarnation,
            )
        for field in LazySkillTable._nested_paths:
            value = getattr(record, field)
            if isinstance(value, LazySoulTrackedList):
                value._detach(self.skills, key, field)

    def _detach_unloaded_skill(self, key):
        labels = self.skills._baseline_labels(key)
        for path, value in labels.items():
            incarnation = IncarnationId(
                self.store.store_identity, value
            )
            occurrence = self._skill_occurrence(key, path)
            self._registry.attach_existing(incarnation, occurrence)
            self._registry.detach_occurrence(
                occurrence, expected=incarnation
            )

    def _replace_skill_nested(self, key, record, field, old, new):
        self._detach_skill_child_binding(key, field, old)
        replacement = self._bind_skill_list(key, field, new)
        if replacement is not new:
            object.__setattr__(record, field, replacement)

    def _bind_loaded_skill(self, key, record):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, SKILL_NAMESPACE, key
            )
        )
        expected_paths = {
            (),
            *LazySkillTable._nested_paths.values(),
        }
        if set(labels) != expected_paths:
            raise StoreIntegrityError(
                "lazy skill occurrence labels are incomplete or extra"
            )
        top_incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(top_incarnation)
        if live is not None:
            if not isinstance(live, SkillHistory):
                raise StoreIntegrityError(
                    "skill incarnation is bound to wrong live type"
                )
            result = live
        else:
            result = record
            self._registry.bind(
                result,
                self._skill_occurrence(key),
                incarnation=top_incarnation,
            )
        self._registry.attach_existing(
            top_incarnation, self._skill_occurrence(key)
        )
        for field, path in LazySkillTable._nested_paths.items():
            incarnation = IncarnationId(
                self.store.store_identity, labels[path]
            )
            current = getattr(result, field)
            wrapper = self._bind_skill_list(
                key, field, current, incarnation=incarnation
            )
            if wrapper is not current:
                object.__setattr__(result, field, wrapper)
        self.skills._baseline_identity_labels[key] = labels
        self.skills._baseline_incarnation[key] = top_incarnation.value
        return result


    def _lineage_child_occurrence(self, key):
        return Occurrence(LINEAGE_CHILD_NAMESPACE, key, ())

    def _bind_assigned_lineage_children(self, key, values):
        wrapper = (
            values
            if isinstance(values, LazyLineageTrackedSet)
            else LazyLineageTrackedSet(values)
        )
        wrapper._attach(self.lineage_children, key)
        existing = self._registry.incarnation_for_object(wrapper)
        if existing is None:
            existing = self._registry.bind(wrapper)
        self._registry.attach_occurrence(
            wrapper, self._lineage_child_occurrence(key)
        )
        return wrapper

    def _detach_assigned_lineage_children(self, key, values):
        incarnation = self._registry.incarnation_for_object(values)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._lineage_child_occurrence(key),
                expected=incarnation,
            )
        if isinstance(values, LazyLineageTrackedSet):
            values._detach(self.lineage_children, key)

    def _detach_unloaded_lineage_children(self, key):
        baseline = self.lineage_children._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._lineage_child_occurrence(key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_lineage_children(self, key, values):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, LINEAGE_CHILD_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy lineage-child occurrence labels are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, LazyLineageTrackedSet):
                raise StoreIntegrityError(
                    "lineage child-set incarnation is bound to wrong type"
                )
            if set(live) != set(values):
                raise StoreIntegrityError(
                    "shared lineage child-set disagrees with edge authority"
                )
            live._attach(self.lineage_children, key)
            result = live
        else:
            result = LazyLineageTrackedSet(values)
            result._attach(self.lineage_children, key)
            self._registry.bind(
                result,
                self._lineage_child_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._lineage_child_occurrence(key)
        )
        self.lineage_children._baseline_incarnation[key] = incarnation.value
        return result


    def _genealogy_child_occurrence(self, key):
        return Occurrence(GENEALOGY_CHILD_NAMESPACE, key, ())

    def _bind_assigned_genealogy_children(self, key, values):
        wrapper = (
            values if isinstance(values, LazySoulTrackedList)
            else LazySoulTrackedList(values)
        )
        wrapper._attach(self.genealogy_children, key, "children")
        existing = self._registry.incarnation_for_object(wrapper)
        if existing is None:
            existing = self._registry.bind(wrapper)
        self._registry.attach_occurrence(
            wrapper, self._genealogy_child_occurrence(key)
        )
        return wrapper

    def _detach_assigned_genealogy_children(self, key, values):
        incarnation = self._registry.incarnation_for_object(values)
        if incarnation is not None:
            self._registry.detach_occurrence(
                self._genealogy_child_occurrence(key),
                expected=incarnation,
            )
        if isinstance(values, LazySoulTrackedList):
            values._detach(self.genealogy_children, key, "children")

    def _detach_unloaded_genealogy_children(self, key):
        baseline = self.genealogy_children._baseline_incarnation_id(key)
        if baseline is None:
            return
        incarnation = IncarnationId(
            self.store.store_identity, baseline
        )
        occurrence = self._genealogy_child_occurrence(key)
        self._registry.attach_existing(incarnation, occurrence)
        self._registry.detach_occurrence(
            occurrence, expected=incarnation
        )

    def _bind_loaded_genealogy_children(self, key, values):
        labels = dict(
            self.store.identity_occurrences_for_owner(
                self.pin, GENEALOGY_CHILD_NAMESPACE, key
            )
        )
        if set(labels) != {()}:
            raise StoreIntegrityError(
                "lazy genealogy-child occurrence labels are incomplete or extra"
            )
        incarnation = IncarnationId(
            self.store.store_identity, labels[()]
        )
        live = self._registry.object_for_incarnation(incarnation)
        if live is not None:
            if not isinstance(live, LazySoulTrackedList):
                raise StoreIntegrityError(
                    "genealogy child-list incarnation is bound to wrong type"
                )
            live._attach(self.genealogy_children, key, "children")
            result = live
        else:
            result = LazySoulTrackedList(values)
            result._attach(self.genealogy_children, key, "children")
            self._registry.bind(
                result,
                self._genealogy_child_occurrence(key),
                incarnation=incarnation,
            )
        self._registry.attach_existing(
            incarnation, self._genealogy_child_occurrence(key)
        )
        self.genealogy_children._baseline_incarnation[key] = incarnation.value
        return result


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

    def _merge_aspiration_layout(self, cold_plan, structural_keys):
        layout_value = cold_plan.layout_value
        if not structural_keys:
            return cold_plan, layout_value

        if layout_value is None:
            layout_value = dict(self.manifest["collections"])
        else:
            layout_value = dict(layout_value)
        current = layout_value[ASPIRATION_NAMESPACE]
        if type(current) is not tuple or len(current) != 3:
            raise StoreFormatError(
                "invalid aspiration collection description"
            )
        layout_value[ASPIRATION_NAMESPACE] = (
            current[0],
            len(self.aspirations),
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


    def _merge_resource_layout(self, cold_plan, structural_keys):
        layout_value = cold_plan.layout_value
        if not structural_keys:
            return cold_plan, layout_value
        if layout_value is None:
            layout_value = dict(self.manifest["collections"])
        else:
            layout_value = dict(layout_value)
        current = layout_value[RESOURCE_NAMESPACE]
        if type(current) is not tuple or len(current) != 3:
            raise StoreFormatError(
                "invalid resource collection description"
            )
        layout_value[RESOURCE_NAMESPACE] = (
            current[0], len(self.resources), current[2]
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


    def _merge_owner_index_layout(self, cold_plan, structural_keys):
        layout_value = cold_plan.layout_value
        if not structural_keys:
            return cold_plan, layout_value

        if layout_value is None:
            layout_value = dict(self.manifest["collections"])
        else:
            layout_value = dict(layout_value)
        current = layout_value[OWNER_INDEX_NAMESPACE]
        if type(current) is not tuple or len(current) != 3:
            raise StoreFormatError(
                "invalid owner-index collection description"
            )
        layout_value[OWNER_INDEX_NAMESPACE] = (
            current[0],
            len(self.owner_index),
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


    def _merge_material_layout(
        self, cold_plan, namespace, table, structural_keys, label
    ):
        layout_value = cold_plan.layout_value
        if not structural_keys:
            return cold_plan, layout_value
        if layout_value is None:
            layout_value = dict(self.manifest["collections"])
        else:
            layout_value = dict(layout_value)
        current = layout_value[namespace]
        if type(current) is not tuple or len(current) != 3:
            raise StoreFormatError(
                f"invalid {label} collection description"
            )
        layout_value[namespace] = (
            current[0], len(table), current[2]
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
            for key in sorted(
                change_map, key=lambda item: (item[0], item[1])
            )
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
        household_member_version_changes = self._household_page_changes()
        (
            version_changes,
            identity_changes,
            touched_keys,
            structural_keys,
        ) = self.people.prepare_save_changes()
        (
            aspiration_version_changes,
            aspiration_identity_changes,
            aspiration_touched_keys,
            aspiration_structural_keys,
        ) = self.aspirations.prepare_save_changes()
        (
            resource_version_changes,
            resource_identity_changes,
            resource_touched_keys,
            resource_structural_keys,
        ) = self.resources.prepare_save_changes()
        (
            owner_index_version_changes,
            owner_index_identity_changes,
            owner_index_touched_keys,
            owner_index_structural_keys,
        ) = self.owner_index.prepare_save_changes()
        (
            material_lot_version_changes,
            material_lot_identity_changes,
            material_lot_touched_keys,
            material_lot_structural_keys,
        ) = self.material_lots.prepare_save_changes()
        (
            material_item_version_changes,
            material_item_identity_changes,
            material_item_touched_keys,
            material_item_structural_keys,
        ) = self.material_items.prepare_save_changes()
        (
            material_lot_index_version_changes,
            material_lot_index_identity_changes,
            material_lot_index_touched_keys,
            material_lot_index_structural_keys,
        ) = self.material_lot_index.prepare_save_changes()
        (
            material_active_index_version_changes,
            material_active_index_identity_changes,
            material_active_index_touched_keys,
            material_active_index_structural_keys,
        ) = self.material_active_index.prepare_save_changes()
        (
            wallet_version_changes,
            wallet_identity_changes,
            wallet_touched_keys,
            wallet_structural_keys,
        ) = self.wallets.prepare_save_changes()
        (
            treasury_version_changes,
            treasury_identity_changes,
            treasury_touched_keys,
            treasury_structural_keys,
        ) = self.treasuries.prepare_save_changes()
        (
            soul_version_changes,
            soul_identity_changes,
            soul_touched_keys,
            soul_structural_keys,
        ) = self.souls.prepare_save_changes()
        (
            advancement_version_changes,
            advancement_identity_changes,
            advancement_touched_keys,
            advancement_structural_keys,
        ) = self.advancement_paths.prepare_save_changes()
        (
            institution_magic_record_version_changes,
            institution_magic_record_identity_changes,
            institution_magic_record_touched_keys,
            institution_magic_record_structural_keys,
        ) = self.institution_magic_records.prepare_save_changes()
        (
            institution_notice_version_changes,
            institution_notice_identity_changes,
            institution_notice_touched_keys,
            institution_notice_structural_keys,
        ) = self.institution_notices.prepare_save_changes()
        (
            institution_application_version_changes,
            institution_application_identity_changes,
            institution_application_touched_keys,
            institution_application_structural_keys,
        ) = self.institution_applications.prepare_save_changes()
        (
            transmission_version_changes,
            transmission_identity_changes,
            transmission_touched_keys,
            transmission_structural_keys,
        ) = self.transmissions.prepare_save_changes()
        (
            motive_version_changes,
            motive_identity_changes,
            motive_touched_keys,
            motive_structural_keys,
        ) = self.motives.prepare_save_changes()
        (
            social_edge_version_changes,
            social_edge_identity_changes,
            social_edge_touched_keys,
            social_edge_structural_keys,
        ) = self.social_edges.prepare_save_changes()
        (
            social_adjacency_version_changes,
            social_adjacency_identity_changes,
            social_adjacency_touched_keys,
            social_adjacency_structural_keys,
        ) = self.social_adjacency.prepare_save_changes()
        (
            social_partnership_version_changes,
            social_partnership_identity_changes,
            social_partnership_touched_keys,
            social_partnership_structural_keys,
        ) = self.social_partnerships.prepare_save_changes()
        (
            skill_version_changes,
            skill_identity_changes,
            skill_touched_keys,
            skill_structural_keys,
        ) = self.skills.prepare_save_changes()
        (
            lineage_node_version_changes,
            lineage_node_identity_changes,
            lineage_node_touched_keys,
            lineage_node_structural_keys,
        ) = self.lineage_nodes.prepare_save_changes()
        (
            lineage_child_version_changes,
            lineage_child_identity_changes,
            lineage_child_touched_keys,
            lineage_child_structural_keys,
            lineage_child_edge_version_changes,
        ) = self.lineage_children.prepare_save_changes()
        (
            genealogy_parent_version_changes,
            genealogy_parent_identity_changes,
            genealogy_parent_touched_keys,
            genealogy_parent_structural_keys,
        ) = self.genealogy_parents.prepare_save_changes()
        (
            genealogy_child_version_changes,
            genealogy_child_identity_changes,
            genealogy_child_touched_keys,
            genealogy_child_structural_keys,
        ) = self.genealogy_children.prepare_save_changes()
        (
            community_membership_version_changes,
            community_membership_identity_changes,
            community_membership_touched_keys,
            community_membership_structural_keys,
        ) = self.community_memberships.prepare_save_changes()

        lazy_effective = bool(
            household_member_version_changes
            or version_changes
            or identity_changes
            or aspiration_version_changes
            or aspiration_identity_changes
            or resource_version_changes
            or resource_identity_changes
            or owner_index_version_changes
            or owner_index_identity_changes
            or material_lot_version_changes
            or material_lot_identity_changes
            or material_item_version_changes
            or material_item_identity_changes
            or material_lot_index_version_changes
            or material_lot_index_identity_changes
            or material_active_index_version_changes
            or material_active_index_identity_changes
            or wallet_version_changes
            or wallet_identity_changes
            or treasury_version_changes
            or treasury_identity_changes
            or soul_version_changes
            or soul_identity_changes
            or advancement_version_changes
            or advancement_identity_changes
            or institution_magic_record_version_changes
            or institution_magic_record_identity_changes
            or institution_notice_version_changes
            or institution_notice_identity_changes
            or institution_application_version_changes
            or institution_application_identity_changes
            or transmission_version_changes
            or transmission_identity_changes
            or motive_version_changes
            or motive_identity_changes
            or social_edge_version_changes
            or social_edge_identity_changes
            or social_adjacency_version_changes
            or social_adjacency_identity_changes
            or social_partnership_version_changes
            or social_partnership_identity_changes
            or skill_version_changes
            or skill_identity_changes
            or lineage_node_version_changes
            or lineage_node_identity_changes
            or lineage_child_version_changes
            or lineage_child_identity_changes
            or lineage_child_edge_version_changes
            or genealogy_parent_version_changes
            or genealogy_parent_identity_changes
            or genealogy_child_version_changes
            or genealogy_child_identity_changes
            or community_membership_version_changes
            or community_membership_identity_changes
        )

        prior_manifest_dirty = self._eager_tracker._manifest_dirty
        structural_dirty = bool(
            structural_keys
            or aspiration_structural_keys
            or resource_structural_keys
            or owner_index_structural_keys
            or material_lot_structural_keys
            or material_item_structural_keys
            or material_lot_index_structural_keys
            or material_active_index_structural_keys
            or wallet_structural_keys
            or treasury_structural_keys
            or soul_structural_keys
            or advancement_structural_keys
            or institution_magic_record_structural_keys
            or institution_notice_structural_keys
            or institution_application_structural_keys
            or transmission_structural_keys
            or motive_structural_keys
            or social_edge_structural_keys
            or social_adjacency_structural_keys
            or social_partnership_structural_keys
            or skill_structural_keys
            or lineage_node_structural_keys
            or lineage_child_structural_keys
            or genealogy_parent_structural_keys
            or genealogy_child_structural_keys
            or community_membership_structural_keys
        )
        if structural_dirty:
            self._eager_tracker._manifest_dirty = True

        self._refresh_cross_boundary_identity()

        token = uuid.uuid4().hex
        try:
            cold_plan = prepare_cold_save(
                self._eager_tracker,
                force=lazy_effective,
                token=token,
            )
        except Exception:
            if structural_dirty:
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

        # Structural changes across lazy families share one collection-layout
        # authority. Build that successor once and replace the manifest change
        # once; rebuilding/sorting the entire cold-plan change map separately
        # for every family makes save preparation quadratic in the number of
        # changed families and owners.
        layout_value = cold_plan.layout_value
        layout_updates = (
            (PEOPLE_NAMESPACE, self.people, structural_keys, "people"),
            (
                ASPIRATION_NAMESPACE,
                self.aspirations,
                aspiration_structural_keys,
                "aspirations",
            ),
            (
                RESOURCE_NAMESPACE,
                self.resources,
                resource_structural_keys,
                "resources",
            ),
            (
                OWNER_INDEX_NAMESPACE,
                self.owner_index,
                owner_index_structural_keys,
                "owner index",
            ),
            (
                MATERIAL_LOT_NAMESPACE,
                self.material_lots,
                material_lot_structural_keys,
                "material lots",
            ),
            (
                MATERIAL_ITEM_NAMESPACE,
                self.material_items,
                material_item_structural_keys,
                "material items",
            ),
            (
                MATERIAL_LOT_INDEX_NAMESPACE,
                self.material_lot_index,
                material_lot_index_structural_keys,
                "material lot index",
            ),
            (
                MATERIAL_ACTIVE_INDEX_NAMESPACE,
                self.material_active_index,
                material_active_index_structural_keys,
                "material active index",
            ),
            (
                WALLET_NAMESPACE,
                self.wallets,
                wallet_structural_keys,
                "currency wallets",
            ),
            (
                TREASURY_NAMESPACE,
                self.treasuries,
                treasury_structural_keys,
                "currency treasuries",
            ),
            (
                SOUL_NAMESPACE,
                self.souls,
                soul_structural_keys,
                "metaphysics souls",
            ),
            (
                ADVANCEMENT_NAMESPACE,
                self.advancement_paths,
                advancement_structural_keys,
                "advancement paths",
            ),
            (
                INSTITUTION_MAGIC_RECORD_NAMESPACE,
                self.institution_magic_records,
                institution_magic_record_structural_keys,
                "institution magic records",
            ),
            (
                INSTITUTION_NOTICE_NAMESPACE,
                self.institution_notices,
                institution_notice_structural_keys,
                "institution notices",
            ),
            (
                INSTITUTION_APPLICATION_NAMESPACE,
                self.institution_applications,
                institution_application_structural_keys,
                "institution applications",
            ),
            (
                TRANSMISSION_NAMESPACE,
                self.transmissions,
                transmission_structural_keys,
                "transmission records",
            ),
            (
                MOTIVE_NAMESPACE,
                self.motives,
                motive_structural_keys,
                "motives",
            ),
            (
                SOCIAL_EDGE_NAMESPACE,
                self.social_edges,
                social_edge_structural_keys,
                "social edges",
            ),
            (
                SOCIAL_ADJACENCY_NAMESPACE,
                self.social_adjacency,
                social_adjacency_structural_keys,
                "social adjacency",
            ),
            (
                SOCIAL_PARTNERSHIP_NAMESPACE,
                self.social_partnerships,
                social_partnership_structural_keys,
                "social partnerships",
            ),
            (
                SKILL_NAMESPACE,
                self.skills,
                skill_structural_keys,
                "skill histories",
            ),
            (
                LINEAGE_NODE_NAMESPACE,
                self.lineage_nodes,
                lineage_node_structural_keys,
                "lineage nodes",
            ),
            (
                LINEAGE_CHILD_NAMESPACE,
                self.lineage_children,
                lineage_child_structural_keys,
                "lineage children",
            ),
            (
                GENEALOGY_PARENT_NAMESPACE,
                self.genealogy_parents,
                genealogy_parent_structural_keys,
                "genealogy parents",
            ),
            (
                GENEALOGY_CHILD_NAMESPACE,
                self.genealogy_children,
                genealogy_child_structural_keys,
                "genealogy children",
            ),
            (
                COMMUNITY_MEMBERSHIP_NAMESPACE,
                self.community_memberships,
                community_membership_structural_keys,
                "community memberships",
            ),
        )
        changed_layout = [
            (namespace, table, label)
            for namespace, table, structural, label in layout_updates
            if structural
        ]
        if changed_layout:
            layout_value = dict(
                self.manifest["collections"]
                if layout_value is None
                else layout_value
            )
            for namespace, table, label in changed_layout:
                current = layout_value[namespace]
                if type(current) is not tuple or len(current) != 3:
                    raise StoreFormatError(
                        f"invalid {label} collection description"
                    )
                layout_value[namespace] = (
                    current[0], len(table), current[2]
                )

            change_map = {
                (
                    change.namespace,
                    self.store.codec.encode(change.key),
                ): change
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
                for key in sorted(
                    change_map, key=lambda item: (item[0], item[1])
                )
            )
            self._eager_tracker._manifest_dirty = True
            cold_plan = replace(
                cold_plan,
                changes=changes,
                record_evidence=_change_evidence(
                    self.store.codec, changes
                ),
                manifest_dirty=True,
                layout_value=layout_value,
            )

        expected_counts = self.store.codec.decode(
            cold_plan.expected_namespace_counts
        )
        for namespace, size in (
            (PEOPLE_NAMESPACE, len(self.people)),
            (ASPIRATION_NAMESPACE, len(self.aspirations)),
            (RESOURCE_NAMESPACE, len(self.resources)),
            (OWNER_INDEX_NAMESPACE, len(self.owner_index)),
            (MATERIAL_LOT_NAMESPACE, len(self.material_lots)),
            (MATERIAL_ITEM_NAMESPACE, len(self.material_items)),
            (MATERIAL_LOT_INDEX_NAMESPACE, len(self.material_lot_index)),
            (
                MATERIAL_ACTIVE_INDEX_NAMESPACE,
                len(self.material_active_index),
            ),
            (WALLET_NAMESPACE, len(self.wallets)),
            (TREASURY_NAMESPACE, len(self.treasuries)),
            (SOUL_NAMESPACE, len(self.souls)),
            (ADVANCEMENT_NAMESPACE, len(self.advancement_paths)),
            (
                INSTITUTION_MAGIC_RECORD_NAMESPACE,
                len(self.institution_magic_records),
            ),
            (
                INSTITUTION_NOTICE_NAMESPACE,
                len(self.institution_notices),
            ),
            (
                INSTITUTION_APPLICATION_NAMESPACE,
                len(self.institution_applications),
            ),
            (TRANSMISSION_NAMESPACE, len(self.transmissions)),
            (MOTIVE_NAMESPACE, len(self.motives)),
            (SOCIAL_EDGE_NAMESPACE, len(self.social_edges)),
            (SOCIAL_ADJACENCY_NAMESPACE, len(self.social_adjacency)),
            (SOCIAL_PARTNERSHIP_NAMESPACE, len(self.social_partnerships)),
            (SKILL_NAMESPACE, len(self.skills)),
            (LINEAGE_NODE_NAMESPACE, len(self.lineage_nodes)),
            (LINEAGE_CHILD_NAMESPACE, len(self.lineage_children)),
            (GENEALOGY_PARENT_NAMESPACE, len(self.genealogy_parents)),
            (GENEALOGY_CHILD_NAMESPACE, len(self.genealogy_children)),
            (
                COMMUNITY_MEMBERSHIP_NAMESPACE,
                len(self.community_memberships),
            ),
        ):
            if size:
                expected_counts[namespace] = (size, 0)
            else:
                expected_counts.pop(namespace, None)

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
            aspiration_version_changes=aspiration_version_changes,
            aspiration_identity_changes=aspiration_identity_changes,
            resource_version_changes=resource_version_changes,
            resource_identity_changes=resource_identity_changes,
            owner_index_version_changes=owner_index_version_changes,
            owner_index_identity_changes=owner_index_identity_changes,
            cold_plan=cold_plan,
            touched_keys=touched_keys,
            structural_keys=structural_keys,
            aspiration_touched_keys=aspiration_touched_keys,
            aspiration_structural_keys=aspiration_structural_keys,
            resource_touched_keys=resource_touched_keys,
            resource_structural_keys=resource_structural_keys,
            owner_index_touched_keys=owner_index_touched_keys,
            owner_index_structural_keys=owner_index_structural_keys,
            material_lot_version_changes=material_lot_version_changes,
            material_lot_identity_changes=material_lot_identity_changes,
            material_lot_touched_keys=material_lot_touched_keys,
            material_lot_structural_keys=material_lot_structural_keys,
            material_item_version_changes=material_item_version_changes,
            material_item_identity_changes=material_item_identity_changes,
            material_item_touched_keys=material_item_touched_keys,
            material_item_structural_keys=material_item_structural_keys,
            material_lot_index_version_changes=(
                material_lot_index_version_changes
            ),
            material_lot_index_identity_changes=(
                material_lot_index_identity_changes
            ),
            material_lot_index_touched_keys=(
                material_lot_index_touched_keys
            ),
            material_lot_index_structural_keys=(
                material_lot_index_structural_keys
            ),
            material_active_index_version_changes=(
                material_active_index_version_changes
            ),
            material_active_index_identity_changes=(
                material_active_index_identity_changes
            ),
            material_active_index_touched_keys=(
                material_active_index_touched_keys
            ),
            material_active_index_structural_keys=(
                material_active_index_structural_keys
            ),
            wallet_version_changes=wallet_version_changes,
            wallet_identity_changes=wallet_identity_changes,
            wallet_touched_keys=wallet_touched_keys,
            wallet_structural_keys=wallet_structural_keys,
            treasury_version_changes=treasury_version_changes,
            treasury_identity_changes=treasury_identity_changes,
            treasury_touched_keys=treasury_touched_keys,
            treasury_structural_keys=treasury_structural_keys,
            soul_version_changes=soul_version_changes,
            soul_identity_changes=soul_identity_changes,
            soul_touched_keys=soul_touched_keys,
            soul_structural_keys=soul_structural_keys,
            advancement_version_changes=advancement_version_changes,
            advancement_identity_changes=advancement_identity_changes,
            advancement_touched_keys=advancement_touched_keys,
            advancement_structural_keys=advancement_structural_keys,
            institution_magic_record_version_changes=(
                institution_magic_record_version_changes
            ),
            institution_magic_record_identity_changes=(
                institution_magic_record_identity_changes
            ),
            institution_magic_record_touched_keys=(
                institution_magic_record_touched_keys
            ),
            institution_magic_record_structural_keys=(
                institution_magic_record_structural_keys
            ),
            institution_notice_version_changes=(
                institution_notice_version_changes
            ),
            institution_notice_identity_changes=(
                institution_notice_identity_changes
            ),
            institution_notice_touched_keys=institution_notice_touched_keys,
            institution_notice_structural_keys=(
                institution_notice_structural_keys
            ),
            institution_application_version_changes=(
                institution_application_version_changes
            ),
            institution_application_identity_changes=(
                institution_application_identity_changes
            ),
            institution_application_touched_keys=(
                institution_application_touched_keys
            ),
            institution_application_structural_keys=(
                institution_application_structural_keys
            ),
            transmission_version_changes=transmission_version_changes,
            transmission_identity_changes=transmission_identity_changes,
            transmission_touched_keys=transmission_touched_keys,
            transmission_structural_keys=transmission_structural_keys,
            motive_version_changes=motive_version_changes,
            motive_identity_changes=motive_identity_changes,
            motive_touched_keys=motive_touched_keys,
            motive_structural_keys=motive_structural_keys,
            social_edge_version_changes=social_edge_version_changes,
            social_edge_identity_changes=social_edge_identity_changes,
            social_edge_touched_keys=social_edge_touched_keys,
            social_edge_structural_keys=social_edge_structural_keys,
            social_adjacency_version_changes=(
                social_adjacency_version_changes
            ),
            social_adjacency_identity_changes=(
                social_adjacency_identity_changes
            ),
            social_adjacency_touched_keys=social_adjacency_touched_keys,
            social_adjacency_structural_keys=(
                social_adjacency_structural_keys
            ),
            social_partnership_version_changes=(
                social_partnership_version_changes
            ),
            social_partnership_identity_changes=(
                social_partnership_identity_changes
            ),
            social_partnership_touched_keys=(
                social_partnership_touched_keys
            ),
            social_partnership_structural_keys=(
                social_partnership_structural_keys
            ),
            skill_version_changes=skill_version_changes,
            skill_identity_changes=skill_identity_changes,
            skill_touched_keys=skill_touched_keys,
            skill_structural_keys=skill_structural_keys,
            lineage_node_version_changes=lineage_node_version_changes,
            lineage_node_identity_changes=lineage_node_identity_changes,
            lineage_node_touched_keys=lineage_node_touched_keys,
            lineage_node_structural_keys=lineage_node_structural_keys,
            lineage_child_version_changes=lineage_child_version_changes,
            lineage_child_identity_changes=lineage_child_identity_changes,
            lineage_child_touched_keys=lineage_child_touched_keys,
            lineage_child_structural_keys=lineage_child_structural_keys,
            lineage_child_edge_version_changes=(
                lineage_child_edge_version_changes
            ),
            genealogy_parent_version_changes=(
                genealogy_parent_version_changes
            ),
            genealogy_parent_identity_changes=(
                genealogy_parent_identity_changes
            ),
            genealogy_parent_touched_keys=genealogy_parent_touched_keys,
            genealogy_parent_structural_keys=(
                genealogy_parent_structural_keys
            ),
            genealogy_child_version_changes=(
                genealogy_child_version_changes
            ),
            genealogy_child_identity_changes=(
                genealogy_child_identity_changes
            ),
            genealogy_child_touched_keys=genealogy_child_touched_keys,
            genealogy_child_structural_keys=(
                genealogy_child_structural_keys
            ),
            community_membership_version_changes=(
                community_membership_version_changes
            ),
            community_membership_identity_changes=(
                community_membership_identity_changes
            ),
            community_membership_touched_keys=(
                community_membership_touched_keys
            ),
            community_membership_structural_keys=(
                community_membership_structural_keys
            ),
            layout_value=layout_value,
            household_member_version_changes=household_member_version_changes,
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

    def _validate_aspiration_successor(self, plan, generation):
        for change in plan.aspiration_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, ASPIRATION_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted aspiration remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved aspiration is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                ASPIRATION_NAMESPACE,
                typed_key,
                row,
                decode=False,
            )
            if (
                schema != LAZY_ASPIRATION_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved aspiration payload evidence mismatch"
                )

        for change in plan.aspiration_identity_changes:
            encoded_key = self.store.codec.encode(change.owner_key)
            encoded_path = self.store.codec.encode(
                change.occurrence_path
            )
            row = self.store._visible_identity_occurrence(
                generation,
                change.owner_namespace,
                encoded_key,
                encoded_path,
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted aspiration incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved aspiration incarnation evidence mismatch"
                )



    def _validate_resource_successor(self, plan, generation):
        for change in plan.resource_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, RESOURCE_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted resource remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved resource is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                RESOURCE_NAMESPACE, typed_key, row, decode=False
            )
            expected_memberships = tuple(
                (
                    member.index_name,
                    member.value,
                    member.ordinal,
                )
                for member in change.memberships
            )
            if (
                schema != LAZY_RESOURCE_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships != expected_memberships
            ):
                raise StoreIntegrityError(
                    "saved resource payload evidence mismatch"
                )
        for change in plan.resource_identity_changes:
            encoded_key = self.store.codec.encode(change.owner_key)
            encoded_path = self.store.codec.encode(
                change.occurrence_path
            )
            row = self.store._visible_identity_occurrence(
                generation,
                change.owner_namespace,
                encoded_key,
                encoded_path,
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted resource incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved resource incarnation evidence mismatch"
                )

    def _validate_owner_index_successor(self, plan, generation):
        for change in plan.owner_index_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, OWNER_INDEX_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted owner-index bucket remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved owner-index bucket is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                OWNER_INDEX_NAMESPACE,
                typed_key,
                row,
                decode=False,
            )
            if (
                schema != LAZY_OWNER_INDEX_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved owner-index bucket evidence mismatch"
                )

        for change in plan.owner_index_identity_changes:
            encoded_key = self.store.codec.encode(change.owner_key)
            encoded_path = self.store.codec.encode(
                change.occurrence_path
            )
            row = self.store._visible_identity_occurrence(
                generation,
                change.owner_namespace,
                encoded_key,
                encoded_path,
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted owner-index incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved owner-index incarnation evidence mismatch"
                )


    def _validate_material_successor(self, plan, generation):
        version_specs = (
            (
                plan.material_lot_version_changes,
                MATERIAL_LOT_NAMESPACE,
                LAZY_MATERIAL_LOT_SCHEMA,
                "material lot",
                True,
            ),
            (
                plan.material_item_version_changes,
                MATERIAL_ITEM_NAMESPACE,
                LAZY_MATERIAL_ITEM_SCHEMA,
                "crafted item",
                False,
            ),
            (
                plan.material_lot_index_version_changes,
                MATERIAL_LOT_INDEX_NAMESPACE,
                LAZY_MATERIAL_LOT_INDEX_SCHEMA,
                "material lot-index bucket",
                False,
            ),
            (
                plan.material_active_index_version_changes,
                MATERIAL_ACTIVE_INDEX_NAMESPACE,
                LAZY_MATERIAL_ACTIVE_INDEX_SCHEMA,
                "material active-index bucket",
                False,
            ),
        )
        for changes, namespace, schema_expected, label, has_memberships in (
            version_specs
        ):
            for change in changes:
                typed_key = self.store.codec.encode(change.key)
                row = self.store._visible_record_row(
                    generation, namespace, typed_key
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} remains visible after save"
                        )
                    continue
                if row is None:
                    raise StoreIntegrityError(
                        f"saved {label} is absent after save"
                    )
                (
                    _value,
                    schema,
                    _valid_from,
                    _valid_to,
                    memberships,
                ) = self.store._check_record_row(
                    namespace, typed_key, row, decode=False
                )
                expected_memberships = (
                    tuple(
                        (
                            member.index_name,
                            member.value,
                            member.ordinal,
                        )
                        for member in change.memberships
                    )
                    if has_memberships else ()
                )
                if (
                    schema != schema_expected
                    or row[2] != self.store.codec.encode(change.value)
                    or memberships != expected_memberships
                ):
                    raise StoreIntegrityError(
                        f"saved {label} payload evidence mismatch"
                    )

        identity_specs = (
            (
                plan.material_lot_identity_changes,
                "material lot",
            ),
            (
                plan.material_item_identity_changes,
                "crafted item",
            ),
            (
                plan.material_lot_index_identity_changes,
                "material lot-index bucket",
            ),
            (
                plan.material_active_index_identity_changes,
                "material active-index bucket",
            ),
        )
        for changes, label in identity_specs:
            for change in changes:
                encoded_key = self.store.codec.encode(change.owner_key)
                encoded_path = self.store.codec.encode(
                    change.occurrence_path
                )
                row = self.store._visible_identity_occurrence(
                    generation,
                    change.owner_namespace,
                    encoded_key,
                    encoded_path,
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} incarnation remains visible"
                        )
                elif row is None or row[0] != change.incarnation_id:
                    raise StoreIntegrityError(
                        f"saved {label} incarnation evidence mismatch"
                    )



    def _validate_currency_successor(self, plan, generation):
        specs = (
            (
                plan.wallet_version_changes,
                plan.wallet_identity_changes,
                WALLET_NAMESPACE,
                LAZY_WALLET_SCHEMA,
                "wallet",
            ),
            (
                plan.treasury_version_changes,
                plan.treasury_identity_changes,
                TREASURY_NAMESPACE,
                LAZY_TREASURY_SCHEMA,
                "treasury",
            ),
        )
        for versions, identities, namespace, schema_expected, label in specs:
            for change in versions:
                typed_key = self.store.codec.encode(change.key)
                row = self.store._visible_record_row(
                    generation, namespace, typed_key
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} remains visible after save"
                        )
                    continue
                if row is None:
                    raise StoreIntegrityError(
                        f"saved {label} is absent after save"
                    )
                (
                    _value,
                    schema,
                    _valid_from,
                    _valid_to,
                    memberships,
                ) = self.store._check_record_row(
                    namespace, typed_key, row, decode=False
                )
                if (
                    schema != schema_expected
                    or row[2] != self.store.codec.encode(change.value)
                    or memberships
                ):
                    raise StoreIntegrityError(
                        f"saved {label} payload evidence mismatch"
                    )
            for change in identities:
                encoded_key = self.store.codec.encode(change.owner_key)
                encoded_path = self.store.codec.encode(
                    change.occurrence_path
                )
                row = self.store._visible_identity_occurrence(
                    generation,
                    change.owner_namespace,
                    encoded_key,
                    encoded_path,
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} incarnation remains visible"
                        )
                elif row is None or row[0] != change.incarnation_id:
                    raise StoreIntegrityError(
                        f"saved {label} incarnation evidence mismatch"
                    )


    def _validate_soul_successor(self, plan, generation):
        for change in plan.soul_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, SOUL_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted soul remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved soul is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                SOUL_NAMESPACE, typed_key, row, decode=False
            )
            if (
                schema != LAZY_SOUL_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved soul payload evidence mismatch"
                )
        for change in plan.soul_identity_changes:
            encoded_key = self.store.codec.encode(change.owner_key)
            encoded_path = self.store.codec.encode(
                change.occurrence_path
            )
            row = self.store._visible_identity_occurrence(
                generation,
                change.owner_namespace,
                encoded_key,
                encoded_path,
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted soul incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved soul incarnation evidence mismatch"
                )


    def _validate_advancement_successor(self, plan, generation):
        for change in plan.advancement_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, ADVANCEMENT_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted advancement path remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved advancement path is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                ADVANCEMENT_NAMESPACE, typed_key, row, decode=False
            )
            if (
                schema != LAZY_ADVANCEMENT_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved advancement path payload evidence mismatch"
                )
        for change in plan.advancement_identity_changes:
            encoded_key = self.store.codec.encode(change.owner_key)
            encoded_path = self.store.codec.encode(
                change.occurrence_path
            )
            row = self.store._visible_identity_occurrence(
                generation,
                change.owner_namespace,
                encoded_key,
                encoded_path,
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted advancement incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved advancement incarnation evidence mismatch"
                )


    def _validate_institution_successor(self, plan, generation):
        specs = (
            (
                plan.institution_magic_record_version_changes,
                plan.institution_magic_record_identity_changes,
                INSTITUTION_MAGIC_RECORD_NAMESPACE,
                LAZY_INSTITUTION_MAGIC_RECORD_SCHEMA,
                "institution magic record",
            ),
            (
                plan.institution_notice_version_changes,
                plan.institution_notice_identity_changes,
                INSTITUTION_NOTICE_NAMESPACE,
                LAZY_INSTITUTION_NOTICE_SCHEMA,
                "institution notice",
            ),
            (
                plan.institution_application_version_changes,
                plan.institution_application_identity_changes,
                INSTITUTION_APPLICATION_NAMESPACE,
                LAZY_INSTITUTION_APPLICATION_SCHEMA,
                "institution application",
            ),
            (
                plan.transmission_version_changes,
                plan.transmission_identity_changes,
                TRANSMISSION_NAMESPACE,
                LAZY_TRANSMISSION_SCHEMA,
                "transmission record",
            ),
            (
                plan.motive_version_changes,
                plan.motive_identity_changes,
                MOTIVE_NAMESPACE,
                LAZY_MOTIVE_SCHEMA,
                "motive",
            ),
        )
        for versions, identities, namespace, expected_schema, label in specs:
            for change in versions:
                typed_key = self.store.codec.encode(change.key)
                row = self.store._visible_record_row(
                    generation, namespace, typed_key
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} remains visible after save"
                        )
                    continue
                if row is None:
                    raise StoreIntegrityError(
                        f"saved {label} is absent after save"
                    )
                (
                    _value,
                    schema,
                    _valid_from,
                    _valid_to,
                    memberships,
                ) = self.store._check_record_row(
                    namespace, typed_key, row, decode=False
                )
                expected_memberships = tuple(
                    (
                        member.index_name,
                        member.value,
                        member.ordinal,
                    )
                    for member in change.memberships
                )
                if (
                    schema != expected_schema
                    or row[2] != self.store.codec.encode(change.value)
                    or memberships != expected_memberships
                ):
                    raise StoreIntegrityError(
                        f"saved {label} evidence mismatch"
                    )
            for change in identities:
                encoded_key = self.store.codec.encode(change.owner_key)
                encoded_path = self.store.codec.encode(
                    change.occurrence_path
                )
                row = self.store._visible_identity_occurrence(
                    generation,
                    change.owner_namespace,
                    encoded_key,
                    encoded_path,
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} incarnation remains visible"
                        )
                elif row is None or row[0] != change.incarnation_id:
                    raise StoreIntegrityError(
                        f"saved {label} incarnation evidence mismatch"
                    )


    def _validate_social_successor(self, plan, generation):
        specs = (
            (
                plan.social_edge_version_changes,
                plan.social_edge_identity_changes,
                SOCIAL_EDGE_NAMESPACE,
                LAZY_SOCIAL_EDGE_SCHEMA,
                "social edge",
                True,
            ),
            (
                plan.social_adjacency_version_changes,
                plan.social_adjacency_identity_changes,
                SOCIAL_ADJACENCY_NAMESPACE,
                LAZY_SOCIAL_ADJACENCY_SCHEMA,
                "social adjacency",
                False,
            ),
            (
                plan.social_partnership_version_changes,
                plan.social_partnership_identity_changes,
                SOCIAL_PARTNERSHIP_NAMESPACE,
                LAZY_SOCIAL_PARTNERSHIP_SCHEMA,
                "social partnership",
                True,
            ),
        )
        for versions, identities, namespace, schema_expected, label, has_memberships in specs:
            for change in versions:
                typed_key = self.store.codec.encode(change.key)
                row = self.store._visible_record_row(
                    generation, namespace, typed_key
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} remains visible after save"
                        )
                    continue
                if row is None:
                    raise StoreIntegrityError(
                        f"saved {label} is absent after save"
                    )
                (
                    _value,
                    schema,
                    _valid_from,
                    _valid_to,
                    memberships,
                ) = self.store._check_record_row(
                    namespace, typed_key, row, decode=False
                )
                expected_memberships = (
                    tuple(
                        (
                            member.index_name,
                            member.value,
                            member.ordinal,
                        )
                        for member in change.memberships
                    )
                    if has_memberships else ()
                )
                if (
                    schema != schema_expected
                    or row[2] != self.store.codec.encode(change.value)
                    or memberships != expected_memberships
                ):
                    raise StoreIntegrityError(
                        f"saved {label} evidence mismatch"
                    )
            for change in identities:
                encoded_key = self.store.codec.encode(change.owner_key)
                encoded_path = self.store.codec.encode(
                    change.occurrence_path
                )
                row = self.store._visible_identity_occurrence(
                    generation,
                    change.owner_namespace,
                    encoded_key,
                    encoded_path,
                )
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError(
                            f"deleted {label} incarnation remains visible"
                        )
                elif row is None or row[0] != change.incarnation_id:
                    raise StoreIntegrityError(
                        f"saved {label} incarnation evidence mismatch"
                    )


    def _validate_skill_successor(self, plan, generation):
        for change in plan.skill_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, SKILL_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted skill history remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved skill history is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                SKILL_NAMESPACE, typed_key, row, decode=False
            )
            if (
                schema != LAZY_SKILL_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved skill history evidence mismatch"
                )
        for change in plan.skill_identity_changes:
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
                        "deleted skill incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved skill incarnation evidence mismatch"
                )

    def _validate_lineage_node_successor(self, plan, generation):
        for change in plan.lineage_node_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, LINEAGE_NODE_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted lineage node remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved lineage node is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                LINEAGE_NODE_NAMESPACE, typed_key, row, decode=False
            )
            if (
                schema != LAZY_LINEAGE_NODE_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved lineage-node evidence mismatch"
                )
        for change in plan.lineage_node_identity_changes:
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
                        "deleted lineage-node incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved lineage-node incarnation evidence mismatch"
                )


    def _validate_lineage_child_successor(self, plan, generation):
        for change in plan.lineage_child_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, LINEAGE_CHILD_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted lineage child bucket remains visible"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved lineage child bucket is absent"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                LINEAGE_CHILD_NAMESPACE,
                typed_key,
                row,
                decode=False,
            )
            if (
                schema != LAZY_LINEAGE_CHILD_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved lineage-child bucket evidence mismatch"
                )

        for change in plan.lineage_child_edge_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, LINEAGE_CHILD_EDGE_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted lineage child edge remains visible"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved lineage child edge is absent"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                LINEAGE_CHILD_EDGE_NAMESPACE,
                typed_key,
                row,
                decode=False,
            )
            expected_memberships = tuple(
                (
                    member.index_name,
                    member.value,
                    member.ordinal,
                )
                for member in change.memberships
            )
            if (
                schema != LAZY_LINEAGE_CHILD_EDGE_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships != expected_memberships
            ):
                raise StoreIntegrityError(
                    "saved lineage-child edge evidence mismatch"
                )

        for change in plan.lineage_child_identity_changes:
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
                        "deleted lineage-child incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved lineage-child incarnation evidence mismatch"
                )


    def _validate_genealogy_parent_successor(self, plan, generation):
        for change in plan.genealogy_parent_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, GENEALOGY_PARENT_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted genealogy parent remains visible after save"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved genealogy parent is absent after save"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                GENEALOGY_PARENT_NAMESPACE,
                typed_key,
                row,
                decode=False,
            )
            if (
                schema != LAZY_GENEALOGY_PARENT_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved genealogy-parent evidence mismatch"
                )


    def _validate_genealogy_child_successor(self, plan, generation):
        for change in plan.genealogy_child_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, GENEALOGY_CHILD_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted genealogy child bucket remains visible"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved genealogy child bucket is absent"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                GENEALOGY_CHILD_NAMESPACE,
                typed_key,
                row,
                decode=False,
            )
            if (
                schema != LAZY_GENEALOGY_CHILD_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships
            ):
                raise StoreIntegrityError(
                    "saved genealogy-child evidence mismatch"
                )
        for change in plan.genealogy_child_identity_changes:
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
                        "deleted genealogy-child incarnation remains visible"
                    )
            elif row is None or row[0] != change.incarnation_id:
                raise StoreIntegrityError(
                    "saved genealogy-child incarnation evidence mismatch"
                )


    def _validate_community_membership_successor(
        self, plan, generation
    ):
        for change in plan.community_membership_version_changes:
            typed_key = self.store.codec.encode(change.key)
            row = self.store._visible_record_row(
                generation, COMMUNITY_MEMBERSHIP_NAMESPACE, typed_key
            )
            if change.delete:
                if row is not None:
                    raise StoreIntegrityError(
                        "deleted community membership remains visible"
                    )
                continue
            if row is None:
                raise StoreIntegrityError(
                    "saved community membership is absent"
                )
            (
                _value,
                schema,
                _valid_from,
                _valid_to,
                memberships,
            ) = self.store._check_record_row(
                COMMUNITY_MEMBERSHIP_NAMESPACE,
                typed_key,
                row,
                decode=False,
            )
            expected_memberships = tuple(
                (
                    member.index_name,
                    member.value,
                    member.ordinal,
                )
                for member in change.memberships
            )
            if (
                schema != LAZY_COMMUNITY_MEMBERSHIP_SCHEMA
                or row[2] != self.store.codec.encode(change.value)
                or memberships != expected_memberships
            ):
                raise StoreIntegrityError(
                    "saved community-membership evidence mismatch"
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
        self.aspirations._pin = result.pin
        self.resources._pin = result.pin
        self.owner_index._pin = result.pin
        self.material_lots._pin = result.pin
        self.material_items._pin = result.pin
        self.material_lot_index._pin = result.pin
        self.material_active_index._pin = result.pin
        self.wallets._pin = result.pin
        self.treasuries._pin = result.pin
        self.souls._pin = result.pin
        self.advancement_paths._pin = result.pin
        self.institution_magic_records._pin = result.pin
        self.institution_notices._pin = result.pin
        self.institution_applications._pin = result.pin
        self.transmissions._pin = result.pin
        self.motives._pin = result.pin
        self.social_edges._pin = result.pin
        self.social_adjacency._pin = result.pin
        self.social_partnerships._pin = result.pin
        self.skills._pin = result.pin
        self.lineage_nodes._pin = result.pin
        self.lineage_children._pin = result.pin
        self.genealogy_parents._pin = result.pin
        self.genealogy_children._pin = result.pin
        self.community_memberships._pin = result.pin
        self._arm_cold_publication(plan)
        tracker = self._eager_tracker
        self._validate_people_successor(
            plan, result.generation
        )
        self._validate_aspiration_successor(
            plan, result.generation
        )
        self._validate_resource_successor(
            plan, result.generation
        )
        self._validate_owner_index_successor(
            plan, result.generation
        )
        self._validate_material_successor(
            plan, result.generation
        )
        self._validate_currency_successor(
            plan, result.generation
        )
        self._validate_soul_successor(
            plan, result.generation
        )
        self._validate_advancement_successor(
            plan, result.generation
        )
        self._validate_institution_successor(
            plan, result.generation
        )
        self._validate_social_successor(
            plan, result.generation
        )
        self._validate_skill_successor(
            plan, result.generation
        )
        self._validate_lineage_node_successor(
            plan, result.generation
        )
        self._validate_lineage_child_successor(
            plan, result.generation
        )
        self._validate_genealogy_parent_successor(
            plan, result.generation
        )
        self._validate_genealogy_child_successor(
            plan, result.generation
        )
        self._validate_community_membership_successor(
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
        self.aspirations.accept_save(plan, result.pin)
        self.resources.accept_save(plan, result.pin)
        self.owner_index.accept_save(plan, result.pin)
        self.material_lots.accept_save(plan, result.pin)
        self.material_items.accept_save(plan, result.pin)
        self.material_lot_index.accept_save(plan, result.pin)
        self.material_active_index.accept_save(plan, result.pin)
        self.wallets.accept_save(plan, result.pin)
        self.treasuries.accept_save(plan, result.pin)
        self.souls.accept_save(plan, result.pin)
        self.advancement_paths.accept_save(plan, result.pin)
        self.institution_magic_records.accept_save(plan, result.pin)
        self.institution_notices.accept_save(plan, result.pin)
        self.institution_applications.accept_save(plan, result.pin)
        self.transmissions.accept_save(plan, result.pin)
        self.motives.accept_save(plan, result.pin)
        self.social_edges.accept_save(plan, result.pin)
        self.social_adjacency.accept_save(plan, result.pin)
        self.social_partnerships.accept_save(plan, result.pin)
        self.skills.accept_save(plan, result.pin)
        self.lineage_nodes.accept_save(plan, result.pin)
        self.lineage_children.accept_save(plan, result.pin)
        self.genealogy_parents.accept_save(plan, result.pin)
        self.genealogy_children.accept_save(plan, result.pin)
        self.community_memberships.accept_save(plan, result.pin)
        for sequence in self._paged_household_members.values():
            sequence.accept_save(result.pin)
        self.prefix = self.world.events._disk_prefix
        self._head = head
        self.identity_links = tuple(
            sorted(
                self._eager_tracker._committed_identity_targets.items(),
                key=lambda item: self.store.codec.encode(item[0]),
            )
        )
        self._cross_boundary_links = tuple(
            link for link in self.identity_links
            if _path_under_lazy(link[0])
            or _path_under_lazy(link[1])
        )
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
                version_changes=(
                    plan.version_changes
                    + plan.aspiration_version_changes
                    + plan.resource_version_changes
                    + plan.owner_index_version_changes
                    + plan.material_lot_version_changes
                    + plan.material_item_version_changes
                    + plan.material_lot_index_version_changes
                    + plan.material_active_index_version_changes
                    + plan.wallet_version_changes
                    + plan.treasury_version_changes
                    + plan.soul_version_changes
                    + plan.advancement_version_changes
                    + plan.institution_magic_record_version_changes
                    + plan.institution_notice_version_changes
                    + plan.institution_application_version_changes
                    + plan.transmission_version_changes
                    + plan.motive_version_changes
                    + plan.social_edge_version_changes
                    + plan.social_adjacency_version_changes
                    + plan.social_partnership_version_changes
                    + plan.skill_version_changes
                    + plan.lineage_node_version_changes
                    + plan.lineage_child_version_changes
                    + plan.lineage_child_edge_version_changes
                    + plan.genealogy_parent_version_changes
                    + plan.genealogy_child_version_changes
                    + plan.community_membership_version_changes
                    + plan.household_member_version_changes
                ),
                identity_changes=(
                    plan.identity_changes
                    + plan.aspiration_identity_changes
                    + plan.resource_identity_changes
                    + plan.owner_index_identity_changes
                    + plan.material_lot_identity_changes
                    + plan.material_item_identity_changes
                    + plan.material_lot_index_identity_changes
                    + plan.material_active_index_identity_changes
                    + plan.wallet_identity_changes
                    + plan.treasury_identity_changes
                    + plan.soul_identity_changes
                    + plan.advancement_identity_changes
                    + plan.institution_magic_record_identity_changes
                    + plan.institution_notice_identity_changes
                    + plan.institution_application_identity_changes
                    + plan.transmission_identity_changes
                    + plan.motive_identity_changes
                    + plan.social_edge_identity_changes
                    + plan.social_adjacency_identity_changes
                    + plan.social_partnership_identity_changes
                    + plan.skill_identity_changes
                    + plan.lineage_node_identity_changes
                    + plan.lineage_child_identity_changes
                    + plan.genealogy_parent_identity_changes
                    + plan.genealogy_child_identity_changes
                    + plan.community_membership_identity_changes
                ),
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

    def _stage_detached_people(self):
        """Materialize the complete logical people table without publishing it."""
        expected = len(self.people)
        detached = RecordTable()
        count = 0
        for key in self.people:
            person = self.people[key]
            if not isinstance(person, Person):
                raise StoreIntegrityError(
                    "lazy detach encountered a non-Person people value"
                )
            # Do not call RecordTable.__setitem__ while staging: that would
            # rebind live records before detach publication is known to succeed.
            dict.__setitem__(detached, key, person)
            count += 1
        if count != expected or dict.__len__(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach people materialization count mismatch"
            )
        return detached

    def _stage_detached_aspirations(self):
        expected = len(self.aspirations)
        detached = {}
        for key in self.aspirations:
            value = self.aspirations[key]
            if not isinstance(value, MagicAspiration):
                raise StoreIntegrityError(
                    "lazy detach encountered non-aspiration value"
                )
            detached[key] = value
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach aspiration materialization count mismatch"
            )
        return detached

    def _stage_detached_resources(self, transfer_replacements=None):
        expected = len(self.resources)
        detached = {}
        if transfer_replacements is None:
            transfer_replacements = {}
        transfer_assignments = []
        for key in self.resources:
            resource = self.resources[key]
            if not isinstance(resource, MagicResource):
                raise StoreIntegrityError(
                    "lazy detach encountered non-resource value"
                )
            transfers = resource.transfers
            if isinstance(transfers, LazyTrackedList):
                replacement = transfer_replacements.get(id(transfers))
                if replacement is None:
                    replacement = list(transfers)
                    transfer_replacements[id(transfers)] = replacement
                transfer_assignments.append(
                    (resource, "transfers", replacement)
                )
            detached[key] = resource
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach resource materialization count mismatch"
            )
        return detached, transfer_replacements, transfer_assignments

    def _stage_detached_owner_index(self, replacements=None):
        expected = len(self.owner_index)
        detached = {}
        if replacements is None:
            replacements = {}
        for key in self.owner_index:
            bucket = self.owner_index[key]
            if not isinstance(bucket, (set, LazyTrackedSet)):
                raise StoreIntegrityError(
                    "lazy detach encountered non-set owner-index bucket"
                )
            replacement = replacements.get(id(bucket))
            if replacement is None:
                replacement = set(bucket)
                replacements[id(bucket)] = replacement
            detached[key] = replacement
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach owner-index materialization count mismatch"
            )
        return detached, replacements


    def _stage_detached_material_lots(self, replacements=None):
        expected = len(self.material_lots)
        detached = {}
        if replacements is None:
            replacements = {}
        transfer_assignments = []
        for key in self.material_lots:
            lot = self.material_lots[key]
            if not isinstance(lot, MaterialLot):
                raise StoreIntegrityError(
                    "lazy detach encountered non-MaterialLot value"
                )
            transfers = lot.transfers
            if isinstance(transfers, LazyTrackedList):
                replacement = replacements.get(id(transfers))
                if replacement is None:
                    replacement = list(transfers)
                    replacements[id(transfers)] = replacement
                transfer_assignments.append(
                    (lot, "transfers", replacement)
                )
            detached[key] = lot
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach material-lot count mismatch"
            )
        return detached, replacements, transfer_assignments

    def _stage_detached_material_items(self):
        expected = len(self.material_items)
        detached = {}
        for key in self.material_items:
            item = self.material_items[key]
            if not isinstance(item, CraftedItem):
                raise StoreIntegrityError(
                    "lazy detach encountered non-CraftedItem value"
                )
            detached[key] = item
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach crafted-item count mismatch"
            )
        return detached

    def _stage_detached_material_lot_index(self, replacements=None):
        expected = len(self.material_lot_index)
        detached = {}
        if replacements is None:
            replacements = {}
        for key in self.material_lot_index:
            bucket = self.material_lot_index[key]
            if not isinstance(bucket, (list, LazyTrackedIdList)):
                raise StoreIntegrityError(
                    "lazy detach encountered non-list material lot index"
                )
            replacement = replacements.get(id(bucket))
            if replacement is None:
                replacement = list(bucket)
                replacements[id(bucket)] = replacement
            detached[key] = replacement
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach material lot-index count mismatch"
            )
        return detached, replacements

    def _stage_detached_material_active_index(self, replacements=None):
        expected = len(self.material_active_index)
        detached = {}
        if replacements is None:
            replacements = {}
        for key in self.material_active_index:
            bucket = self.material_active_index[key]
            if not isinstance(bucket, (set, LazyTrackedSet)):
                raise StoreIntegrityError(
                    "lazy detach encountered non-set material active index"
                )
            replacement = replacements.get(id(bucket))
            if replacement is None:
                replacement = set(bucket)
                replacements[id(bucket)] = replacement
            detached[key] = replacement
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach material active-index count mismatch"
            )
        return detached, replacements


    def _stage_plain_advancement_value(
        self,
        value,
        replacements,
        assignments,
        records,
        memo,
    ):
        cls = type(value)
        if value is None or cls in (
            bool, int, float, str, bytes, FrozenDict, FrozenList
        ):
            return value
        ident = id(value)
        if ident in memo:
            return memo[ident]
        if ident in replacements:
            memo[ident] = replacements[ident]
            return replacements[ident]

        if is_dataclass(value):
            memo[ident] = value
            if isinstance(value, IndexedRecord):
                records[id(value)] = value
            for name in RECORD_FIELDS.get(cls, ()):
                child = getattr(value, name)
                replacement = self._stage_plain_advancement_value(
                    child,
                    replacements,
                    assignments,
                    records,
                    memo,
                )
                if replacement is not child:
                    assignments.append((value, name, replacement))
            return value

        if isinstance(value, dict):
            plain = {}
            memo[ident] = plain
            replacements[ident] = plain
            for key, child in value.items():
                plain[key] = self._stage_plain_advancement_value(
                    child,
                    replacements,
                    assignments,
                    records,
                    memo,
                )
            return plain

        if isinstance(value, list):
            plain = []
            memo[ident] = plain
            replacements[ident] = plain
            plain.extend(
                self._stage_plain_advancement_value(
                    child,
                    replacements,
                    assignments,
                    records,
                    memo,
                )
                for child in value
            )
            return plain

        if isinstance(value, set):
            plain = set(value)
            memo[ident] = plain
            replacements[ident] = plain
            return plain

        if cls is tuple:
            plain = tuple(
                self._stage_plain_advancement_value(
                    child,
                    replacements,
                    assignments,
                    records,
                    memo,
                )
                for child in value
            )
            memo[ident] = plain
            return plain

        return value

    def _stage_detached_advancement_paths(self, replacements=None):
        expected = len(self.advancement_paths)
        detached = {}
        if replacements is None:
            replacements = {}
        assignments = []
        records = {}
        memo = {}
        for key in self.advancement_paths:
            path = self.advancement_paths[key]
            if not isinstance(path, EssencePath):
                raise StoreIntegrityError(
                    "lazy detach encountered non-EssencePath value"
                )
            staged = self._stage_plain_advancement_value(
                path,
                replacements,
                assignments,
                records,
                memo,
            )
            if staged is not path:
                raise StoreIntegrityError(
                    "advancement detach replaced top-level path identity"
                )
            detached[key] = path
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach advancement path count mismatch"
            )
        return (
            detached,
            replacements,
            assignments,
            tuple(records.values()),
        )


    def _stage_detached_souls(self, replacements=None):
        expected = len(self.souls)
        detached = {}
        if replacements is None:
            replacements = {}
        nested_assignments = []
        for key in self.souls:
            soul = self.souls[key]
            if not isinstance(soul, SoulState):
                raise StoreIntegrityError(
                    "lazy detach encountered non-SoulState value"
                )
            for field in LazySoulTable._nested_paths:
                value = getattr(soul, field)
                replacement = replacements.get(id(value))
                if replacement is None:
                    if field in ("authorities", "marks"):
                        replacement = set(value)
                    elif field == "cosmic_links":
                        replacement = dict(value)
                    else:
                        replacement = list(value)
                    replacements[id(value)] = replacement
                nested_assignments.append(
                    (soul, field, replacement)
                )
            detached[key] = soul
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach soul materialization count mismatch"
            )
        return detached, replacements, nested_assignments


    def _stage_detached_skills(self, replacements=None):
        expected = len(self.skills)
        detached = {}
        if replacements is None:
            replacements = {}
        nested_assignments = []
        for key in self.skills:
            record = self.skills[key]
            if not isinstance(record, SkillHistory):
                raise StoreIntegrityError(
                    "lazy detach encountered non-SkillHistory value"
                )
            for field in LazySkillTable._nested_paths:
                value = getattr(record, field)
                replacement = replacements.get(id(value))
                if replacement is None:
                    replacement = list(value)
                    replacements[id(value)] = replacement
                nested_assignments.append(
                    (record, field, replacement)
                )
            detached[key] = record
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach skill-history count mismatch"
            )
        return detached, replacements, nested_assignments


    def _stage_detached_lineage_nodes(self):
        expected = len(self.lineage_nodes)
        detached = {}
        for key in self.lineage_nodes:
            record = self.lineage_nodes[key]
            if not isinstance(record, LineageNode):
                raise StoreIntegrityError(
                    "lazy detach encountered non-LineageNode value"
                )
            detached[key] = record
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach lineage-node count mismatch"
            )
        return detached


    def _stage_detached_lineage_children(self, replacements=None):
        expected = len(self.lineage_children)
        detached = {}
        if replacements is None:
            replacements = {}
        for key in self.lineage_children:
            bucket = self.lineage_children[key]
            if not isinstance(bucket, (set, LazyLineageTrackedSet)):
                raise StoreIntegrityError(
                    "lazy detach encountered invalid lineage child set"
                )
            replacement = replacements.get(id(bucket))
            if replacement is None:
                replacement = set(bucket)
                replacements[id(bucket)] = replacement
            detached[key] = replacement
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach lineage-child count mismatch"
            )
        return detached, replacements


    def _stage_detached_genealogy_parents(self):
        expected = len(self.genealogy_parents)
        detached = {}
        for key in self.genealogy_parents:
            value = self.genealogy_parents[key]
            if type(value) is not tuple or any(
                type(parent) is not int for parent in value
            ):
                raise StoreIntegrityError(
                    "lazy detach encountered invalid genealogy parent tuple"
                )
            detached[key] = value
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach genealogy-parent count mismatch"
            )
        return detached


    def _stage_detached_genealogy_children(self, replacements=None):
        expected = len(self.genealogy_children)
        detached = {}
        if replacements is None:
            replacements = {}
        for key in self.genealogy_children:
            bucket = self.genealogy_children[key]
            if not isinstance(bucket, (list, LazySoulTrackedList)):
                raise StoreIntegrityError(
                    "lazy detach encountered invalid genealogy child list"
                )
            replacement = replacements.get(id(bucket))
            if replacement is None:
                replacement = list(bucket)
                replacements[id(bucket)] = replacement
            detached[key] = replacement
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach genealogy-child count mismatch"
            )
        return detached, replacements


    def _stage_detached_institution_table(
        self, table, expected_type, label
    ):
        expected = len(table)
        detached = RecordTable()
        for key in table:
            record = table[key]
            if not isinstance(record, expected_type):
                raise StoreIntegrityError(
                    f"lazy detach encountered wrong {label} value"
                )
            detached[key] = record
        if len(detached) != expected:
            raise StoreIntegrityError(
                f"lazy detach {label} count mismatch"
            )
        return detached


    def _stage_detached_currency_table(self, table, replacements=None):
        expected = len(table)
        detached = {}
        if replacements is None:
            replacements = {}
        for key in table:
            bucket = table[key]
            if not isinstance(bucket, (dict, LazyTrackedDict)):
                raise StoreIntegrityError(
                    "lazy detach encountered non-dict currency bucket"
                )
            replacement = replacements.get(id(bucket))
            if replacement is None:
                replacement = dict(bucket)
                replacements[id(bucket)] = replacement
            detached[key] = replacement
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach currency bucket count mismatch"
            )
        return detached, replacements

    def _stage_detached_social_edges(self, replacements=None):
        expected = len(self.social_edges)
        detached = {}
        if replacements is None:
            replacements = {}
        assignments = []
        for key in self.social_edges:
            record = self.social_edges[key]
            if not isinstance(record, Relationship):
                raise StoreIntegrityError(
                    "lazy detach encountered non-Relationship social edge"
                )
            history = record.shared_history
            if isinstance(history, LazyTrackedList):
                replacement = replacements.get(id(history))
                if replacement is None:
                    replacement = list(history)
                    replacements[id(history)] = replacement
                assignments.append((record, "shared_history", replacement))
            dict.__setitem__(detached, key, record)
        if dict.__len__(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach social-edge count mismatch"
            )
        return detached, replacements, assignments

    def _stage_detached_social_adjacency(self, replacements=None):
        expected = len(self.social_adjacency)
        detached = {}
        if replacements is None:
            replacements = {}
        for key in self.social_adjacency:
            bucket = self.social_adjacency[key]
            if not isinstance(bucket, (set, LazyTrackedSet)):
                raise StoreIntegrityError(
                    "lazy detach encountered non-set social adjacency"
                )
            replacement = replacements.get(id(bucket))
            if replacement is None:
                replacement = set(bucket)
                replacements[id(bucket)] = replacement
            detached[key] = replacement
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach social-adjacency count mismatch"
            )
        return detached, replacements

    def _stage_detached_social_partnerships(self):
        expected = len(self.social_partnerships)
        detached = {}
        for key in self.social_partnerships:
            value = self.social_partnerships[key]
            if type(value) is not int:
                raise StoreIntegrityError(
                    "lazy detach encountered non-int partnership event"
                )
            detached[key] = value
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach social-partnership count mismatch"
            )
        return detached


    def _stage_detached_community_memberships(self):
        expected = len(self.community_memberships)
        detached = {}
        for key in self.community_memberships:
            value = self.community_memberships[key]
            if (
                type(key) is not tuple
                or len(key) != 2
                or any(type(part) is not int for part in key)
                or type(value) not in (int, float)
            ):
                raise StoreIntegrityError(
                    "lazy detach encountered invalid community membership"
                )
            detached[key] = value
        if len(detached) != expected:
            raise StoreIntegrityError(
                "lazy detach community-membership count mismatch"
            )
        return detached


    def _publish_materialized_detach(
        self,
        old_log,
        new_log,
        detached_people,
        detached_aspirations,
        detached_resources,
        detached_owner_index,
        detached_material_lots,
        detached_material_items,
        detached_material_lot_index,
        detached_material_active_index,
        detached_wallets,
        detached_treasuries,
        detached_souls,
        detached_advancement_paths,
        detached_institution_magic_records,
        detached_institution_notices,
        detached_institution_applications,
        detached_transmissions,
        detached_motives,
        detached_social_edges,
        detached_social_adjacency,
        detached_social_partnerships,
        detached_skills,
        detached_lineage_nodes,
        detached_lineage_children,
        detached_genealogy_parents,
        detached_genealogy_children,
        detached_community_memberships,
        advancement_records,
        assignments,
        cache_removals,
        index_rebindings,
    ):
        """Publish a fully staged portable graph; remaining work is teardown."""
        tracker = self._eager_tracker
        old_prefix = old_log._disk_prefix
        pending_old_prefix = tracker._cold_old_prefix_pending

        # Weak references can theoretically fail for unsupported table types.
        # Precompute them before the durable pin is released so every remaining
        # publication step is deterministic in-memory teardown.
        prepared_rebindings = [
            (record, weakref.ref(table), key)
            for record, table, key in index_rebindings
        ]
        aspiration_records = tuple(detached_aspirations.values())
        resource_records = tuple(detached_resources.values())
        material_lot_records = tuple(detached_material_lots.values())
        material_item_records = tuple(detached_material_items.values())
        soul_records = tuple(detached_souls.values())
        social_edge_records = tuple(detached_social_edges.values())
        skill_records = tuple(detached_skills.values())
        lineage_node_records = tuple(detached_lineage_nodes.values())

        # This is the final fallible storage operation.  If release/cleanup
        # fails, no staged graph replacement has been published and the session
        # remains usable.
        self.store.release_pin(self.pin)

        tracker._suspended += 1
        try:
            for obj, name, replacement in assignments:
                object.__setattr__(obj, name, replacement)
            for obj, names in cache_removals:
                for name in names:
                    obj.__dict__.pop(name, None)
            for record, table_ref, key in prepared_rebindings:
                object.__setattr__(record, "_index_table", table_ref)
                object.__setattr__(record, "_index_key", key)
            for record in aspiration_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            for record in resource_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            for record in material_lot_records + material_item_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            for record in soul_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            for record in advancement_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            for record in social_edge_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            for record in skill_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            for record in lineage_node_records:
                object.__setattr__(record, "_index_table", None)
                object.__setattr__(record, "_index_key", None)
            self.world.__dict__.pop("_ate_persistence_lifetime", None)
            new_log.__dict__.pop("_ate_persistence_lifetime", None)
        finally:
            tracker._suspended -= 1

        tracker._clear_bindings()
        tracker._active = False
        tracker._cold_state = "closed"
        tracker._cold_plan = None
        tracker._cold_publication_phase = None
        tracker._cold_old_prefix_pending = None
        tracker._memo.clear()
        tracker._memo_reverse.clear()
        tracker._bound_root_originals.clear()
        tracker._bootstrap_originals.clear()
        tracker._root_containers.clear()
        tracker._scalar_fields.clear()
        tracker._cold_persisted_keys.clear()
        tracker._identity_dirty_owners.clear()
        tracker._identity_index = None
        tracker._committed_identity_targets.clear()
        tracker._live_identity_targets.clear()
        tracker._pending_identity_current.clear()

        self._lifetime.close()
        if old_prefix is not None:
            old_prefix.close()
        if (
            pending_old_prefix is not None
            and pending_old_prefix is not old_prefix
        ):
            pending_old_prefix.close()

        self._registry.close()
        self.people = detached_people
        self.aspirations = detached_aspirations
        self.resources = detached_resources
        self.owner_index = detached_owner_index
        self.material_lots = detached_material_lots
        self.material_items = detached_material_items
        self.material_lot_index = detached_material_lot_index
        self.material_active_index = detached_material_active_index
        self.wallets = detached_wallets
        self.treasuries = detached_treasuries
        self.souls = detached_souls
        self.advancement_paths = detached_advancement_paths
        self.institution_magic_records = detached_institution_magic_records
        self.institution_notices = detached_institution_notices
        self.institution_applications = detached_institution_applications
        self.transmissions = detached_transmissions
        self.motives = detached_motives
        self.social_edges = detached_social_edges
        self.social_adjacency = detached_social_adjacency
        self.social_partnerships = detached_social_partnerships
        self.skills = detached_skills
        self.lineage_nodes = detached_lineage_nodes
        self.lineage_children = detached_lineage_children
        self.genealogy_parents = detached_genealogy_parents
        self.genealogy_children = detached_genealogy_children
        self.community_memberships = detached_community_memberships
        self.world.communities.__dict__.pop("_membership_index", None)
        self._cross_boundary_links = ()
        self.identity_links = ()
        self.store.close()
        self._active = False
        self._state = "closed"
        self._lifecycle_operation = None
        return self.world

    def detach(self, *, materialize_history=False):
        """Detach the lazy session into one portable in-memory World."""
        self._begin_lifecycle_operation("detach", allow_stale=True)
        published = False
        try:
            if not materialize_history:
                raise StoreError(
                    "lazy history requires detach(materialize_history=True)"
                )
            from . import persistence_lifecycle as lifecycle

            old_log = self.world.events
            lifecycle._lifecycle_phase("before_history", self)
            new_log = lifecycle._standalone_log(old_log, self)
            lifecycle._lifecycle_phase("after_history", self)

            detached_people = self._stage_detached_people()
            detached_aspirations = self._stage_detached_aspirations()
            mutable_replacements = {}
            (
                detached_resources,
                mutable_replacements,
                transfer_assignments,
            ) = self._stage_detached_resources(mutable_replacements)
            (
                detached_owner_index,
                mutable_replacements,
            ) = self._stage_detached_owner_index(mutable_replacements)
            (
                detached_material_lots,
                mutable_replacements,
                material_transfer_assignments,
            ) = self._stage_detached_material_lots(mutable_replacements)
            detached_material_items = (
                self._stage_detached_material_items()
            )
            (
                detached_material_lot_index,
                mutable_replacements,
            ) = self._stage_detached_material_lot_index(
                mutable_replacements
            )
            (
                detached_material_active_index,
                mutable_replacements,
            ) = self._stage_detached_material_active_index(
                mutable_replacements
            )
            (
                detached_wallets,
                mutable_replacements,
            ) = self._stage_detached_currency_table(
                self.wallets, mutable_replacements
            )
            (
                detached_treasuries,
                mutable_replacements,
            ) = self._stage_detached_currency_table(
                self.treasuries, mutable_replacements
            )
            (
                detached_souls,
                mutable_replacements,
                soul_nested_assignments,
            ) = self._stage_detached_souls(mutable_replacements)
            (
                detached_advancement_paths,
                mutable_replacements,
                advancement_assignments,
                advancement_records,
            ) = self._stage_detached_advancement_paths(
                mutable_replacements
            )
            detached_institution_magic_records = (
                self._stage_detached_institution_table(
                    self.institution_magic_records,
                    MagicUserRecord,
                    "institution magic-record",
                )
            )
            detached_institution_notices = (
                self._stage_detached_institution_table(
                    self.institution_notices,
                    AdventureNotice,
                    "institution notice",
                )
            )
            detached_institution_applications = (
                self._stage_detached_institution_table(
                    self.institution_applications,
                    SocietyApplication,
                    "institution application",
                )
            )
            detached_transmissions = self._stage_detached_institution_table(
                self.transmissions, Transmission, "transmission record"
            )
            detached_motives = self._stage_detached_institution_table(
                self.motives, MotiveState, "motive"
            )
            (
                detached_social_edges,
                mutable_replacements,
                social_edge_assignments,
            ) = self._stage_detached_social_edges(
                mutable_replacements
            )
            (
                detached_social_adjacency,
                mutable_replacements,
            ) = self._stage_detached_social_adjacency(
                mutable_replacements
            )
            detached_social_partnerships = (
                self._stage_detached_social_partnerships()
            )
            (
                detached_skills,
                mutable_replacements,
                skill_nested_assignments,
            ) = self._stage_detached_skills(mutable_replacements)
            detached_lineage_nodes = self._stage_detached_lineage_nodes()
            (
                detached_lineage_children,
                mutable_replacements,
            ) = self._stage_detached_lineage_children(
                mutable_replacements
            )
            detached_genealogy_parents = (
                self._stage_detached_genealogy_parents()
            )
            (
                detached_genealogy_children,
                mutable_replacements,
            ) = self._stage_detached_genealogy_children(
                mutable_replacements
            )
            detached_community_memberships = (
                self._stage_detached_community_memberships()
            )
            assignments, cache_removals, index_rebindings = (
                lifecycle._stage_plain_graph(
                    self._eager_tracker,
                    old_log,
                    new_log,
                    replacements={
                        id(self.people): detached_people,
                        id(self.aspirations): detached_aspirations,
                        id(self.resources): detached_resources,
                        id(self.owner_index): detached_owner_index,
                        id(self.material_lots): detached_material_lots,
                        id(self.material_items): detached_material_items,
                        id(self.material_lot_index): detached_material_lot_index,
                        id(self.material_active_index): (
                            detached_material_active_index
                        ),
                        id(self.wallets): detached_wallets,
                        id(self.treasuries): detached_treasuries,
                        id(self.souls): detached_souls,
                        id(self.advancement_paths): detached_advancement_paths,
                        id(self.institution_magic_records): (
                            detached_institution_magic_records
                        ),
                        id(self.institution_notices): (
                            detached_institution_notices
                        ),
                        id(self.institution_applications): (
                            detached_institution_applications
                        ),
                        id(self.transmissions): detached_transmissions,
                        id(self.motives): detached_motives,
                        id(self.social_edges): detached_social_edges,
                        id(self.social_adjacency): detached_social_adjacency,
                        id(self.social_partnerships): (
                            detached_social_partnerships
                        ),
                        id(self.skills): detached_skills,
                        id(self.lineage_nodes): detached_lineage_nodes,
                        id(self.lineage_children): (
                            detached_lineage_children
                        ),
                        id(self.genealogy_parents): (
                            detached_genealogy_parents
                        ),
                        id(self.genealogy_children): (
                            detached_genealogy_children
                        ),
                        id(self.community_memberships): (
                            detached_community_memberships
                        ),
                        **mutable_replacements,
                    },
                )
            )
            assignments.extend(transfer_assignments)
            assignments.extend(material_transfer_assignments)
            assignments.extend(soul_nested_assignments)
            assignments.extend(advancement_assignments)
            assignments.extend(social_edge_assignments)
            assignments.extend(skill_nested_assignments)
            for key, person in dict.items(detached_people):
                if isinstance(person, IndexedRecord):
                    index_rebindings.append(
                        (person, detached_people, key)
                    )
            for table in (
                detached_institution_magic_records,
                detached_institution_notices,
                detached_institution_applications,
                detached_transmissions,
                detached_motives,
            ):
                for key, record in dict.items(table):
                    index_rebindings.append((record, table, key))

            lifecycle._lifecycle_phase("before_publish", self)
            world = self._publish_materialized_detach(
                old_log,
                new_log,
                detached_people,
                detached_aspirations,
                detached_resources,
                detached_owner_index,
                detached_material_lots,
                detached_material_items,
                detached_material_lot_index,
                detached_material_active_index,
                detached_wallets,
                detached_treasuries,
                detached_souls,
                detached_advancement_paths,
                detached_institution_magic_records,
                detached_institution_notices,
                detached_institution_applications,
                detached_transmissions,
                detached_motives,
                detached_social_edges,
                detached_social_adjacency,
                detached_social_partnerships,
                detached_skills,
                detached_lineage_nodes,
                detached_lineage_children,
                detached_genealogy_parents,
                detached_genealogy_children,
                detached_community_memberships,
                advancement_records,
                assignments,
                cache_removals,
                index_rebindings,
            )
            published = True
            return world
        finally:
            if not published and self._active:
                self._end_lifecycle_operation("detach")

    def diagnostics(self):
        self._ensure_active()
        tracker = self._eager_tracker
        return {
            "state": self._state,
            "people": self.people.diagnostics(),
            "aspirations": self.aspirations.diagnostics(),
            "resources": self.resources.diagnostics(),
            "owner_index": self.owner_index.diagnostics(),
            "material_lots": self.material_lots.diagnostics(),
            "material_items": self.material_items.diagnostics(),
            "material_lot_index": self.material_lot_index.diagnostics(),
            "material_active_index": self.material_active_index.diagnostics(),
            "wallets": self.wallets.diagnostics(),
            "treasuries": self.treasuries.diagnostics(),
            "souls": self.souls.diagnostics(),
            "advancement_paths": self.advancement_paths.diagnostics(),
            "institution_magic_records": (
                self.institution_magic_records.diagnostics()
            ),
            "institution_notices": self.institution_notices.diagnostics(),
            "institution_applications": (
                self.institution_applications.diagnostics()
            ),
            "transmissions": self.transmissions.diagnostics(),
            "motives": self.motives.diagnostics(),
            "social_edges": self.social_edges.diagnostics(),
            "social_adjacency": self.social_adjacency.diagnostics(),
            "social_partnerships": self.social_partnerships.diagnostics(),
            "skills": self.skills.diagnostics(),
            "lineage_nodes": self.lineage_nodes.diagnostics(),
            "lineage_children": self.lineage_children.diagnostics(),
            "genealogy_parents": self.genealogy_parents.diagnostics(),
            "genealogy_children": self.genealogy_children.diagnostics(),
            "community_memberships": (
                self.community_memberships.diagnostics()
            ),
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
        if self._lifecycle_operation is not None:
            raise StoreError(
                "lazy close is blocked during "
                f"{self._lifecycle_operation}"
            )
        if self._eager_tracker._cold_step_depth:
            raise StoreError("lazy close requires a completed simulation step")
        if self.world.__dict__.get("_index_current_people"):
            raise StoreError(
                "lazy close cannot run inside current_people_scope"
            )
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


def open_lazy_world_session(path, *, rules_id, paged_household_members=False):
    """Open P4 lazy World without decoding migrated record families."""
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

            member_pages_present = (
                store._namespace_state_at(
                    HOUSEHOLD_LENGTH_NAMESPACE, head.generation
                ) is not None
            )
            if member_pages_present != bool(paged_household_members):
                raise StoreFormatError(
                    "household members storage mode mismatch; explicit paged flag required"
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
                excluded_namespaces={
                    PEOPLE_NAMESPACE,
                    ASPIRATION_NAMESPACE,
                    RESOURCE_NAMESPACE,
                    OWNER_INDEX_NAMESPACE,
                    MATERIAL_LOT_NAMESPACE,
                    MATERIAL_ITEM_NAMESPACE,
                    MATERIAL_LOT_INDEX_NAMESPACE,
                    MATERIAL_ACTIVE_INDEX_NAMESPACE,
                    WALLET_NAMESPACE,
                    TREASURY_NAMESPACE,
                    SOUL_NAMESPACE,
                    ADVANCEMENT_NAMESPACE,
                    INSTITUTION_MAGIC_RECORD_NAMESPACE,
                    INSTITUTION_NOTICE_NAMESPACE,
                    INSTITUTION_APPLICATION_NAMESPACE,
                    TRANSMISSION_NAMESPACE,
                    MOTIVE_NAMESPACE,
                    SOCIAL_EDGE_NAMESPACE,
                    SOCIAL_ADJACENCY_NAMESPACE,
                    SOCIAL_PARTNERSHIP_NAMESPACE,
                    SKILL_NAMESPACE,
                    LINEAGE_NODE_NAMESPACE,
                    LINEAGE_CHILD_NAMESPACE,
                    GENEALOGY_PARENT_NAMESPACE,
                    GENEALOGY_CHILD_NAMESPACE,
                    COMMUNITY_MEMBERSHIP_NAMESPACE,
                },
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
                    elif namespace in (
                        PEOPLE_NAMESPACE,
                        ASPIRATION_NAMESPACE,
                        RESOURCE_NAMESPACE,
                        OWNER_INDEX_NAMESPACE,
                        MATERIAL_LOT_NAMESPACE,
                        MATERIAL_ITEM_NAMESPACE,
                        MATERIAL_LOT_INDEX_NAMESPACE,
                        MATERIAL_ACTIVE_INDEX_NAMESPACE,
                        WALLET_NAMESPACE,
                        TREASURY_NAMESPACE,
                        SOUL_NAMESPACE,
                        ADVANCEMENT_NAMESPACE,
                        INSTITUTION_MAGIC_RECORD_NAMESPACE,
                        INSTITUTION_NOTICE_NAMESPACE,
                        INSTITUTION_APPLICATION_NAMESPACE,
                        TRANSMISSION_NAMESPACE,
                        MOTIVE_NAMESPACE,
                        SOCIAL_EDGE_NAMESPACE,
                        SOCIAL_ADJACENCY_NAMESPACE,
                        SOCIAL_PARTNERSHIP_NAMESPACE,
                        SKILL_NAMESPACE,
                        LINEAGE_NODE_NAMESPACE,
                        LINEAGE_CHILD_NAMESPACE,
                        GENEALOGY_PARENT_NAMESPACE,
                        GENEALOGY_CHILD_NAMESPACE,
                        COMMUNITY_MEMBERSHIP_NAMESPACE,
                    ):
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
                if not _path_under_lazy(link[0])
                and not _path_under_lazy(link[1])
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
            if paged_household_members:
                session._activate_household_pages()
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
