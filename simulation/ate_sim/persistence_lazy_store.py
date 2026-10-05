from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from .incremental_store import (
    CODEC_VERSION,
    DDL as P1_DDL,
    Membership,
    NewSegment,
    RecordChange,
    StoreConflictError,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TypedCodec,
    _bump_count,
    _counts_blob,
    _framed_sha,
    _head_checksum,
    _head_values,
    _int_bytes,
    _namespace_counts,
    _record_checksum,
    _segment_checksum,
    _validate_namespace,
)

FORMAT_VERSION = 3
MAX_PINS = 64
MAX_PAGE_SIZE = 128


class GenerationPressureError(StoreConflictError):
    def __init__(self, head_generation: int, minimum_pinned_generation: int):
        self.head_generation = head_generation
        self.minimum_pinned_generation = minimum_pinned_generation
        super().__init__(
            f"generation pressure: head={head_generation}, "
            f"minimum pinned generation={minimum_pinned_generation}"
        )


@dataclass(frozen=True)
class GenerationPin:
    token: str
    store_identity: str
    captured_head: int


@dataclass(frozen=True)
class CheckedVersion:
    value: Any
    record_schema: int
    valid_from: int
    valid_to: int | None


@dataclass(frozen=True)
class VersionChange:
    namespace: str
    key: Any
    value: Any = None
    record_schema: int = 1
    delete: bool = False
    memberships: tuple[Membership, ...] = ()
    reinsertion: bool = False


@dataclass(frozen=True)
class IdentityOccurrenceChange:
    owner_namespace: str
    owner_key: Any
    occurrence_path: tuple[Any, ...]
    incarnation_id: int | None = None
    delete: bool = False


@dataclass(frozen=True)
class CheckedIdentityOccurrence:
    incarnation_id: int
    valid_from: int
    valid_to: int | None


@dataclass(frozen=True)
class CommitResult:
    outcome: str
    generation: int
    pin: GenerationPin
    stale: bool = False


@dataclass(frozen=True)
class CopyResult:
    path: Path
    store_identity: str
    generation: int


@dataclass(frozen=True)
class LazyStoreDiagnostics:
    payload_reads: int
    payload_read_bytes: int
    payload_check_reads: int
    payload_check_bytes: int
    payload_writes: int
    payload_write_bytes: int
    metadata_rows: int
    query_rows: int
    pin_rows: int
    maintenance_rows: int
    temporary_keys_peak: int


P4_DDL = """
CREATE TABLE lazy_record_versions(
    namespace TEXT NOT NULL,
    typed_key BLOB NOT NULL,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER,
    payload BLOB NOT NULL,
    payload_checksum TEXT NOT NULL,
    codec_version INTEGER NOT NULL,
    record_schema INTEGER NOT NULL,
    memberships BLOB NOT NULL,
    row_checksum TEXT NOT NULL,
    PRIMARY KEY(namespace, typed_key, valid_from),
    CHECK(valid_from >= 0),
    CHECK(valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX lazy_record_lookup
    ON lazy_record_versions(namespace, typed_key, valid_from, valid_to);
CREATE INDEX lazy_record_expiry
    ON lazy_record_versions(valid_to, namespace, typed_key, valid_from);

CREATE TABLE lazy_order_versions(
    namespace TEXT NOT NULL,
    typed_key BLOB NOT NULL,
    ordinal INTEGER NOT NULL,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER,
    row_checksum TEXT NOT NULL,
    PRIMARY KEY(namespace, typed_key, valid_from),
    CHECK(ordinal >= 0),
    CHECK(valid_from >= 0),
    CHECK(valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX lazy_order_visible
    ON lazy_order_versions(namespace, valid_from, valid_to, ordinal, typed_key);
CREATE INDEX lazy_order_current
    ON lazy_order_versions(namespace, ordinal, typed_key, valid_from)
    WHERE valid_to IS NULL;
CREATE INDEX lazy_order_closed_generation
    ON lazy_order_versions(namespace, valid_to, ordinal, typed_key)
    WHERE valid_to IS NOT NULL;
CREATE INDEX lazy_order_expiry
    ON lazy_order_versions(valid_to, namespace, typed_key, valid_from);

CREATE TABLE lazy_query_versions(
    namespace TEXT NOT NULL,
    index_name TEXT NOT NULL,
    index_value BLOB NOT NULL,
    record_key BLOB NOT NULL,
    ordinal INTEGER NOT NULL,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER,
    row_checksum TEXT NOT NULL,
    PRIMARY KEY(namespace, index_name, index_value, record_key, ordinal, valid_from),
    CHECK(ordinal >= 0),
    CHECK(valid_from >= 0),
    CHECK(valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX lazy_query_visible
    ON lazy_query_versions(namespace, index_name, index_value, valid_from, valid_to, ordinal, record_key);
CREATE INDEX lazy_query_current
    ON lazy_query_versions(namespace, index_name, index_value, ordinal, record_key, valid_from)
    WHERE valid_to IS NULL;
CREATE INDEX lazy_query_open_generation
    ON lazy_query_versions(namespace, index_name, index_value, valid_from, ordinal, record_key)
    WHERE valid_to IS NULL;
CREATE INDEX lazy_query_closed_generation
    ON lazy_query_versions(namespace, index_name, index_value, valid_to, ordinal, record_key)
    WHERE valid_to IS NOT NULL;
CREATE INDEX lazy_query_owner_visible
    ON lazy_query_versions(namespace, record_key, valid_from, valid_to);
CREATE INDEX lazy_query_expiry
    ON lazy_query_versions(valid_to, namespace, record_key, valid_from);

CREATE TABLE lazy_namespace_state(
    namespace TEXT NOT NULL,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER,
    member_count INTEGER NOT NULL,
    next_ordinal INTEGER NOT NULL,
    row_checksum TEXT NOT NULL,
    PRIMARY KEY(namespace, valid_from),
    CHECK(member_count >= 0),
    CHECK(next_ordinal >= 0),
    CHECK(valid_from >= 0),
    CHECK(valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX lazy_namespace_visible
    ON lazy_namespace_state(namespace, valid_from, valid_to);
CREATE INDEX lazy_namespace_expiry
    ON lazy_namespace_state(valid_to, namespace, valid_from);

CREATE TABLE lazy_identity_occurrence_versions(
    owner_namespace TEXT NOT NULL,
    owner_key BLOB NOT NULL,
    occurrence_path BLOB NOT NULL,
    incarnation_id INTEGER NOT NULL,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER,
    row_checksum TEXT NOT NULL,
    PRIMARY KEY(owner_namespace, owner_key, occurrence_path, valid_from),
    CHECK(incarnation_id > 0),
    CHECK(valid_from >= 0),
    CHECK(valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX lazy_identity_occurrence_lookup
    ON lazy_identity_occurrence_versions(
        owner_namespace, owner_key, occurrence_path, valid_from, valid_to
    );
CREATE INDEX lazy_identity_occurrence_current
    ON lazy_identity_occurrence_versions(
        owner_namespace, owner_key, occurrence_path, incarnation_id
    )
    WHERE valid_to IS NULL;
CREATE INDEX lazy_identity_occurrence_expiry
    ON lazy_identity_occurrence_versions(
        valid_to, owner_namespace, owner_key, occurrence_path, valid_from
    );

CREATE TABLE lazy_identity_state(
    valid_from INTEGER PRIMARY KEY,
    valid_to INTEGER,
    next_incarnation_id INTEGER NOT NULL,
    row_checksum TEXT NOT NULL,
    CHECK(next_incarnation_id > 0),
    CHECK(valid_from >= 0),
    CHECK(valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX lazy_identity_state_visible
    ON lazy_identity_state(valid_from, valid_to);
CREATE INDEX lazy_identity_state_expiry
    ON lazy_identity_state(valid_to, valid_from);

CREATE TABLE generation_pins(
    token TEXT PRIMARY KEY,
    store_uuid TEXT NOT NULL,
    generation INTEGER NOT NULL,
    row_checksum TEXT NOT NULL,
    CHECK(generation >= 0)
);
CREATE INDEX generation_pins_generation ON generation_pins(generation, token);

CREATE TABLE pin_receipts(
    pin_token TEXT PRIMARY KEY,
    commit_token BLOB NOT NULL,
    generation INTEGER NOT NULL,
    parent_generation INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    row_checksum TEXT NOT NULL,
    FOREIGN KEY(pin_token) REFERENCES generation_pins(token) ON DELETE CASCADE
);

CREATE TABLE pin_attempts(
    pin_token TEXT PRIMARY KEY,
    commit_token BLOB NOT NULL,
    parent_generation INTEGER NOT NULL,
    state TEXT NOT NULL,
    generation INTEGER,
    row_checksum TEXT NOT NULL,
    FOREIGN KEY(pin_token) REFERENCES generation_pins(token) ON DELETE CASCADE,
    CHECK(state IN ('pending','committed','acknowledged','not_committed','conflict')),
    CHECK(generation IS NULL OR generation >= 0)
);
"""


def _optional_int(value: int | None) -> bytes:
    return b"null" if value is None else _int_bytes(value)


def _version_checksum(
    namespace: str,
    typed_key: bytes,
    record_schema: int,
    codec_version: int,
    valid_from: int,
    valid_to: int | None,
    memberships: bytes,
    payload: bytes,
) -> str:
    return _framed_sha(
        b"lazy-record-v1",
        namespace.encode("utf-8"),
        typed_key,
        _int_bytes(record_schema),
        _int_bytes(codec_version),
        _int_bytes(valid_from),
        _optional_int(valid_to),
        memberships,
        payload,
    )


def _order_checksum(
    namespace: str,
    typed_key: bytes,
    ordinal: int,
    valid_from: int,
    valid_to: int | None,
) -> str:
    return _framed_sha(
        b"lazy-order-v1",
        namespace.encode("utf-8"),
        typed_key,
        _int_bytes(ordinal),
        _int_bytes(valid_from),
        _optional_int(valid_to),
    )


def _query_checksum(
    namespace: str,
    index_name: str,
    index_value: bytes,
    record_key: bytes,
    ordinal: int,
    valid_from: int,
    valid_to: int | None,
) -> str:
    return _framed_sha(
        b"lazy-query-v1",
        namespace.encode("utf-8"),
        index_name.encode("utf-8"),
        index_value,
        record_key,
        _int_bytes(ordinal),
        _int_bytes(valid_from),
        _optional_int(valid_to),
    )


def _namespace_checksum(
    namespace: str,
    member_count: int,
    next_ordinal: int,
    valid_from: int,
    valid_to: int | None,
) -> str:
    return _framed_sha(
        b"lazy-namespace-v1",
        namespace.encode("utf-8"),
        _int_bytes(member_count),
        _int_bytes(next_ordinal),
        _int_bytes(valid_from),
        _optional_int(valid_to),
    )


def _identity_occurrence_checksum(
    owner_namespace: str,
    owner_key: bytes,
    occurrence_path: bytes,
    incarnation_id: int,
    valid_from: int,
    valid_to: int | None,
) -> str:
    return _framed_sha(
        b"lazy-identity-occurrence-v1",
        owner_namespace.encode("utf-8"),
        owner_key,
        occurrence_path,
        _int_bytes(incarnation_id),
        _int_bytes(valid_from),
        _optional_int(valid_to),
    )


def _identity_state_checksum(
    next_incarnation_id: int,
    valid_from: int,
    valid_to: int | None,
) -> str:
    return _framed_sha(
        b"lazy-identity-state-v1",
        _int_bytes(next_incarnation_id),
        _int_bytes(valid_from),
        _optional_int(valid_to),
    )


def _pin_checksum(store_uuid: str, token: str, generation: int) -> str:
    return _framed_sha(
        b"generation-pin-v1",
        store_uuid.encode("ascii"),
        token.encode("ascii"),
        _int_bytes(generation),
    )


def _receipt_checksum(
    pin_token: str,
    commit_token: bytes,
    generation: int,
    parent_generation: int,
    outcome: str,
) -> str:
    return _framed_sha(
        b"pin-receipt-v1",
        pin_token.encode("ascii"),
        commit_token,
        _int_bytes(generation),
        _int_bytes(parent_generation),
        outcome.encode("ascii"),
    )


def _attempt_checksum(
    pin_token: str,
    commit_token: bytes,
    parent_generation: int,
    state: str,
    generation: int | None,
) -> str:
    return _framed_sha(
        b"pin-attempt-v1",
        pin_token.encode("ascii"),
        commit_token,
        _int_bytes(parent_generation),
        state.encode("ascii"),
        _optional_int(generation),
    )


class LazyRecordStore:
    _copy_phase_hook = staticmethod(lambda phase: None)

    def __init__(self, path: Path, db: sqlite3.Connection, codec: TypedCodec, store_identity: str):
        self.path = path
        self.db = db
        self.codec = codec
        self.store_identity = store_identity
        self._closed = False
        self._phase_hook = lambda phase: None
        self._recovery_required: dict[str, bytes] = {}
        self.reset_diagnostics()

    @classmethod
    def create(
        cls,
        path: str | os.PathLike[str],
        *,
        codec: TypedCodec,
        simulation_schema: str,
        rules_id: str,
    ) -> "LazyRecordStore":
        path = Path(path)
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".ate-lazy-store-", dir=path.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        db = None
        try:
            db = sqlite3.connect(tmp, timeout=30.0)
            cls._configure(db)
            db.executescript(P1_DDL)
            db.executescript(P4_DDL)
            store_identity = str(uuid.uuid4())
            rows = {
                "store_uuid": store_identity,
                "format_version": str(FORMAT_VERSION),
                "codec_version": str(codec.version),
                "simulation_schema": str(simulation_schema),
                "rules_id": str(rules_id),
                "journal_mode": "delete",
                "synchronous": "2",
            }
            db.executemany("INSERT INTO store_metadata(key,value) VALUES (?,?)", rows.items())
            position, seed, next_ids, namespaces = _head_values(
                codec,
                {"simulation_position": None, "seed": 0, "next_ids": {}, "namespaces": ()},
            )
            counts = _counts_blob(codec, {})
            checksum = _head_checksum(0, None, position, seed, next_ids, namespaces, counts)
            db.execute(
                "INSERT INTO save_head VALUES (1,0,NULL,?,?,?,?,?,?)",
                (position, seed, next_ids, namespaces, counts, checksum),
            )
            db.execute(
                "INSERT INTO lazy_identity_state(valid_from,valid_to,next_incarnation_id,row_checksum) "
                "VALUES (0,NULL,1,?)",
                (_identity_state_checksum(1, 0, None),),
            )
            db.commit()
            db.close()
            db = None
            os.link(tmp, path)
            tmp.unlink()
            cls._fsync_dir(path.parent)
            return cls.open(
                path,
                codec=codec,
                expected_simulation_schema=simulation_schema,
                expected_rules_id=rules_id,
            )
        except Exception:
            if db is not None:
                db.close()
            if tmp.exists():
                tmp.unlink()
            raise

    @classmethod
    def open(
        cls,
        path: str | os.PathLike[str],
        *,
        codec: TypedCodec,
        expected_simulation_schema: str,
        expected_rules_id: str,
    ) -> "LazyRecordStore":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            db = sqlite3.connect(path, timeout=30.0)
        except sqlite3.DatabaseError as exc:
            raise StoreFormatError("not a readable SQLite save store") from exc
        try:
            cls._configure_open(db)
            rows = dict(db.execute("SELECT key,value FROM store_metadata"))
            if int(rows.get("format_version", -1)) != FORMAT_VERSION:
                raise StoreFormatError("unsupported persistence format")
            if int(rows.get("codec_version", -1)) != codec.version:
                raise StoreFormatError("unsupported codec version")
            if rows.get("simulation_schema") != str(expected_simulation_schema):
                raise StoreFormatError("simulation schema mismatch")
            if rows.get("rules_id") != str(expected_rules_id):
                raise StoreFormatError("rules identifier mismatch")
            if rows.get("journal_mode") != "delete" or rows.get("synchronous") != "2":
                raise StoreFormatError("store was not created with required durability settings")
            store_identity = rows.get("store_uuid")
            if not store_identity:
                raise StoreIntegrityError("missing store identity")
            store = cls(path, db, codec, store_identity)
            store._checked_head_row()
            return store
        except Exception:
            db.close()
            raise

    @staticmethod
    def _configure(db: sqlite3.Connection) -> None:
        db.execute("PRAGMA foreign_keys=ON")
        mode = db.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        db.execute("PRAGMA synchronous=FULL")
        sync = db.execute("PRAGMA synchronous").fetchone()[0]
        if str(mode).lower() != "delete" or int(sync) != 2:
            raise StoreFormatError("SQLite could not provide rollback/FULL durability mode")

    @staticmethod
    def _configure_open(db: sqlite3.Connection) -> None:
        db.execute("PRAGMA foreign_keys=ON")
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        if str(mode).lower() != "delete":
            raise StoreFormatError("save store requires rollback journal mode DELETE")
        db.execute("PRAGMA synchronous=FULL")
        if int(db.execute("PRAGMA synchronous").fetchone()[0]) != 2:
            raise StoreFormatError("SQLite could not provide synchronous=FULL")

    def _commit_sqlite(self) -> None:
        self.db.commit()

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        if os.name != "posix":
            return
        try:
            fd = os.open(path, os.O_DIRECTORY)
        except (AttributeError, OSError):
            return
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _ensure_open(self) -> None:
        if self._closed:
            raise StoreError("store is closed")

    def reset_diagnostics(self) -> None:
        self._payload_reads = 0
        self._payload_read_bytes = 0
        self._payload_check_reads = 0
        self._payload_check_bytes = 0
        self._payload_writes = 0
        self._payload_write_bytes = 0
        self._metadata_rows = 0
        self._query_rows = 0
        self._pin_rows = 0
        self._maintenance_rows = 0
        self._temporary_keys_peak = 0

    def diagnostics(self) -> LazyStoreDiagnostics:
        return LazyStoreDiagnostics(
            self._payload_reads,
            self._payload_read_bytes,
            self._payload_check_reads,
            self._payload_check_bytes,
            self._payload_writes,
            self._payload_write_bytes,
            self._metadata_rows,
            self._query_rows,
            self._pin_rows,
            self._maintenance_rows,
            self._temporary_keys_peak,
        )

    def _checked_head_row(self) -> tuple[Any, ...]:
        row = self.db.execute(
            "SELECT generation,parent_generation,simulation_position,seed,next_ids,"
            "namespace_inventory,namespace_counts,head_checksum FROM save_head WHERE singleton=1"
        ).fetchone()
        self._metadata_rows += 1
        if row is None:
            raise StoreIntegrityError("missing save head")
        if _head_checksum(*row[:-1]) != row[-1]:
            raise StoreIntegrityError("save head checksum mismatch")
        generation, parent = row[0], row[1]
        if type(generation) is not int or generation < 0:
            raise StoreIntegrityError("invalid save head generation")
        if generation == 0:
            if parent is not None:
                raise StoreIntegrityError("initial save head has a parent generation")
        elif type(parent) is not int or parent != generation - 1:
            raise StoreIntegrityError("invalid save head lineage")
        self.codec.decode(row[2])
        self.codec.decode(row[4])
        namespaces = self.codec.decode(row[5])
        if type(namespaces) is not tuple or any(type(v) is not str for v in namespaces):
            raise StoreIntegrityError("invalid namespace inventory")
        counts = _namespace_counts(self.codec, row[6])
        if not set(counts).issubset(set(namespaces)):
            raise StoreIntegrityError("namespace counts are outside head inventory")
        return row

    @property
    def generation(self) -> int:
        self._ensure_open()
        return int(self._checked_head_row()[0])

    def head_metadata(self) -> dict[str, Any]:
        self._ensure_open()
        row = self._checked_head_row()
        return {
            "simulation_position": self.codec.decode(row[2]),
            "seed": row[3],
            "next_ids": self.codec.decode(row[4]),
            "namespaces": self.codec.decode(row[5]),
        }

    def _checked_pin_row(self, token: str) -> tuple[str, int, str]:
        row = self.db.execute(
            "SELECT store_uuid,generation,row_checksum FROM generation_pins WHERE token=?",
            (token,),
        ).fetchone()
        self._pin_rows += 1
        if row is None:
            raise StoreConflictError("generation pin is not registered")
        store_uuid, generation, checksum = row
        if store_uuid != self.store_identity:
            raise StoreIntegrityError("pin store identity mismatch")
        if checksum != _pin_checksum(store_uuid, token, generation):
            raise StoreIntegrityError("generation pin checksum mismatch")
        return store_uuid, int(generation), checksum

    def _require_pin(self, pin: GenerationPin, *, exact_generation: bool = True) -> int:
        if not isinstance(pin, GenerationPin):
            raise TypeError("pin must be GenerationPin")
        if pin.store_identity != self.store_identity:
            raise StoreConflictError("generation pin belongs to another store")
        _, generation, _ = self._checked_pin_row(pin.token)
        if exact_generation and generation != pin.captured_head:
            raise StoreConflictError(
                f"generation pin moved from {pin.captured_head} to {generation}; resolve or use the updated pin"
            )
        return generation

    def _checked_operational_rows(
        self, head_generation: int
    ) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], list[tuple[Any, ...]]]:
        pins = self.db.execute(
            "SELECT token,store_uuid,generation,row_checksum FROM generation_pins"
        ).fetchall()
        self._pin_rows += len(pins)
        if len(pins) > MAX_PINS:
            raise StoreIntegrityError("generation pin capacity exceeded")
        pin_tokens = set()
        pin_generation: dict[str, int] = {}
        for token, store_uuid, generation, checksum in pins:
            if (
                store_uuid != self.store_identity
                or type(generation) is not int
                or checksum != _pin_checksum(store_uuid, token, generation)
            ):
                raise StoreIntegrityError("generation pin checksum mismatch")
            if generation > head_generation or generation < max(0, head_generation - 1):
                raise StoreIntegrityError("generation pin lies outside two-snapshot retention")
            pin_tokens.add(token)
            pin_generation[token] = generation

        receipts = self.db.execute(
            "SELECT pin_token,commit_token,generation,parent_generation,outcome,row_checksum FROM pin_receipts"
        ).fetchall()
        self._pin_rows += len(receipts)
        if len(receipts) > len(pins):
            raise StoreIntegrityError("receipt bookkeeping exceeds live pins")
        receipt_by_pin = {}
        for token, commit_token, generation, parent, outcome, checksum in receipts:
            if token not in pin_tokens:
                raise StoreIntegrityError("receipt exists without a pin")
            if checksum != _receipt_checksum(token, commit_token, generation, parent, outcome):
                raise StoreIntegrityError("pin receipt checksum mismatch")
            if outcome != "committed" or parent != generation - 1:
                raise StoreIntegrityError("invalid pin receipt outcome")
            if pin_generation[token] != generation:
                raise StoreIntegrityError("pin receipt is inconsistent with durable pin state")
            receipt_by_pin[token] = (commit_token, generation, parent)

        attempts = self.db.execute(
            "SELECT pin_token,commit_token,parent_generation,state,generation,row_checksum FROM pin_attempts"
        ).fetchall()
        self._pin_rows += len(attempts)
        if len(attempts) > len(pins):
            raise StoreIntegrityError("attempt bookkeeping exceeds live pins")
        for token, commit_token, parent, state, generation, checksum in attempts:
            if token not in pin_tokens:
                raise StoreIntegrityError("attempt exists without a pin")
            if state not in {"pending", "committed", "acknowledged", "not_committed", "conflict"}:
                raise StoreIntegrityError("invalid pin attempt state")
            if checksum != _attempt_checksum(token, commit_token, parent, state, generation):
                raise StoreIntegrityError("pin attempt checksum mismatch")
            if state in {"committed", "acknowledged"}:
                if generation != parent + 1:
                    raise StoreIntegrityError("committed attempt has invalid generation")
                receipt = receipt_by_pin.get(token)
                if receipt is None or receipt != (commit_token, generation, parent):
                    raise StoreIntegrityError("committed attempt is inconsistent with receipt")
            elif generation is not None:
                raise StoreIntegrityError("noncommitted attempt carries a generation")
            if parent > head_generation:
                raise StoreIntegrityError("attempt parent is ahead of save head")
        return pins, receipts, attempts

    def _validated_retention_floor(self, head_generation: int) -> int:
        pins, _, _ = self._checked_operational_rows(head_generation)
        if not pins:
            return head_generation
        return min(int(row[2]) for row in pins)

    def _attempt_row(self, pin_token: str) -> tuple[Any, ...] | None:
        row = self.db.execute(
            "SELECT commit_token,parent_generation,state,generation,row_checksum FROM pin_attempts WHERE pin_token=?",
            (pin_token,),
        ).fetchone()
        self._pin_rows += int(row is not None)
        return row

    def _write_attempt_state(
        self,
        pin_token: str,
        commit_token: bytes,
        parent_generation: int,
        state: str,
        generation: int | None,
    ) -> None:
        checksum = _attempt_checksum(pin_token, commit_token, parent_generation, state, generation)
        self.db.execute(
            "INSERT INTO pin_attempts(pin_token,commit_token,parent_generation,state,generation,row_checksum) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(pin_token) DO UPDATE SET "
            "commit_token=excluded.commit_token,parent_generation=excluded.parent_generation,"
            "state=excluded.state,generation=excluded.generation,row_checksum=excluded.row_checksum",
            (pin_token, commit_token, parent_generation, state, generation, checksum),
        )
        self._pin_rows += 1

    def _register_attempt(
        self, pin: GenerationPin, encoded_commit_token: bytes, expected_parent: int
    ) -> None:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            head = int(self._checked_head_row()[0])
            pins, receipts, attempts = self._checked_operational_rows(head)
            pin_row = next((row for row in pins if row[0] == pin.token), None)
            if pin_row is None:
                raise StoreConflictError("generation pin is not registered")
            if pin.store_identity != self.store_identity:
                raise StoreConflictError("generation pin belongs to another store")
            if int(pin_row[2]) != expected_parent or head != expected_parent:
                raise StoreConflictError("generation pin or save head moved before attempt registration")
            existing = next((row for row in attempts if row[0] == pin.token), None)
            if existing is not None:
                _, old_token, _old_parent, old_state, _old_generation, _ = existing
                if old_state in {"pending", "committed"}:
                    raise StoreConflictError("pin has an unresolved commit attempt")
                if old_token == encoded_commit_token:
                    raise StoreConflictError("commit token is already the pin's latest attempt")
            receipt = next((row for row in receipts if row[0] == pin.token), None)
            if receipt is not None and receipt[1] == encoded_commit_token:
                raise StoreConflictError("commit token is already the pin's latest receipt")
            self._write_attempt_state(
                pin.token, encoded_commit_token, expected_parent, "pending", None
            )
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

    def _acknowledge_attempt(
        self, pin: GenerationPin, encoded_commit_token: bytes, generation: int
    ) -> None:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            head = int(self._checked_head_row()[0])
            self._checked_operational_rows(head)
            row = self._attempt_row(pin.token)
            if row is None:
                raise StoreIntegrityError("missing durable commit attempt")
            token, parent, state, stored_generation, checksum = row
            if token != encoded_commit_token:
                raise StoreConflictError("commit token does not match the pin's latest attempt")
            if checksum != _attempt_checksum(pin.token, token, parent, state, stored_generation):
                raise StoreIntegrityError("pin attempt checksum mismatch")
            if state not in {"committed", "acknowledged"} or stored_generation != generation:
                raise StoreIntegrityError("commit attempt cannot be acknowledged")
            self._write_attempt_state(
                pin.token, token, parent, "acknowledged", stored_generation
            )
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

    def capture_pin(self) -> GenerationPin:
        self._ensure_open()
        token = str(uuid.uuid4())
        self._phase_hook("before_pin_capture")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            head = int(self._checked_head_row()[0])
            pins, _, _ = self._checked_operational_rows(head)
            if len(pins) >= MAX_PINS:
                raise GenerationPressureError(head, head)
            checksum = _pin_checksum(self.store_identity, token, head)
            self.db.execute(
                "INSERT INTO generation_pins(token,store_uuid,generation,row_checksum) VALUES (?,?,?,?)",
                (token, self.store_identity, head, checksum),
            )
            self._pin_rows += 1
            self._phase_hook("before_pin_capture_commit")
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise
        return GenerationPin(token, self.store_identity, head)

    def release_pin(self, pin: GenerationPin) -> None:
        self._ensure_open()
        if pin.token in self._recovery_required:
            raise StoreConflictError("pin has unresolved commit acknowledgement")
        self._phase_hook("before_pin_release")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if pin.store_identity != self.store_identity:
                raise StoreConflictError("generation pin belongs to another store")
            head = int(self._checked_head_row()[0])
            pins, _, attempts = self._checked_operational_rows(head)
            row = next((item for item in pins if item[0] == pin.token), None)
            if row is None:
                self.db.rollback()
                return
            if int(row[2]) != pin.captured_head:
                raise StoreConflictError("generation pin has advanced; use the updated pin")
            attempt = next((item for item in attempts if item[0] == pin.token), None)
            if attempt is not None and attempt[3] in {"pending", "committed"}:
                raise StoreConflictError("pin has unresolved commit acknowledgement")
            self.db.execute("DELETE FROM pin_receipts WHERE pin_token=?", (pin.token,))
            self.db.execute("DELETE FROM pin_attempts WHERE pin_token=?", (pin.token,))
            self.db.execute("DELETE FROM generation_pins WHERE token=?", (pin.token,))
            self._pin_rows += 3
            floor = self._validated_retention_floor(head)
            self._cleanup_expired(floor)
            self._phase_hook("during_pin_release_cleanup")
            self._phase_hook("before_pin_release_commit")
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

    def _read_snapshot_start(self, pin: GenerationPin) -> int:
        self.db.execute("BEGIN")
        try:
            generation = self._require_pin(pin)
            head = int(self._checked_head_row()[0])
            floor = self._validated_retention_floor(head)
            if generation < floor or generation > head:
                raise StoreConflictError("generation pin is outside retained visibility")
            return generation
        except Exception:
            self.db.rollback()
            raise

    def _read_snapshot_end(self) -> None:
        if self.db.in_transaction:
            self.db.rollback()

    def _visible_record_row(self, generation: int, namespace: str, typed_key: bytes) -> tuple[Any, ...] | None:
        rows = self.db.execute(
            "SELECT valid_from,valid_to,payload,payload_checksum,codec_version,record_schema,memberships,row_checksum "
            "FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_from<=? "
            "AND (valid_to IS NULL OR ?<valid_to) ORDER BY valid_from DESC LIMIT 2",
            (namespace, typed_key, generation, generation),
        ).fetchall()
        self._metadata_rows += len(rows)
        if len(rows) > 1:
            raise StoreIntegrityError("overlapping visible record versions")
        return rows[0] if rows else None

    def _check_record_row(
        self, namespace: str, typed_key: bytes, row: tuple[Any, ...], *, decode: bool
    ) -> tuple[Any, int, int, int | None, tuple[tuple[str, Any, int], ...]]:
        valid_from, valid_to, payload, payload_checksum, codec_version, record_schema, memberships_blob, row_checksum = row
        if type(valid_from) is not int or valid_from < 0 or (
            valid_to is not None and (type(valid_to) is not int or valid_to <= valid_from)
        ):
            raise StoreIntegrityError("invalid record validity interval")
        if codec_version != self.codec.version:
            raise StoreFormatError("payload codec version mismatch")
        self._payload_check_reads += 1
        self._payload_check_bytes += len(payload)
        if payload_checksum != _framed_sha(b"lazy-payload-v1", payload):
            raise StoreIntegrityError("lazy payload checksum mismatch")
        expected = _version_checksum(
            namespace, typed_key, record_schema, codec_version, valid_from, valid_to, memberships_blob, payload
        )
        if row_checksum != expected:
            raise StoreIntegrityError("lazy record row checksum mismatch")
        memberships = self._decode_memberships(memberships_blob)
        value = None
        if decode:
            self._payload_reads += 1
            self._payload_read_bytes += len(payload)
            value = self.codec.decode(payload)
        return value, int(record_schema), int(valid_from), valid_to, memberships

    def read_version(
        self,
        pin: GenerationPin,
        namespace: str,
        key: Any,
        *,
        expected_record_schema: int,
    ) -> CheckedVersion:
        self._ensure_open()
        _validate_namespace(namespace)
        typed_key = self.codec.encode(key)
        generation = self._read_snapshot_start(pin)
        try:
            row = self._visible_record_row(generation, namespace, typed_key)
            if row is None:
                dangling_order = self.db.execute(
                    "SELECT 1 FROM lazy_order_versions WHERE namespace=? AND typed_key=? AND valid_from<=? "
                    "AND (valid_to IS NULL OR ?<valid_to) LIMIT 1",
                    (namespace, typed_key, generation, generation),
                ).fetchone()
                dangling_query = self.db.execute(
                    "SELECT 1 FROM lazy_query_versions WHERE namespace=? AND record_key=? AND valid_from<=? "
                    "AND (valid_to IS NULL OR ?<valid_to) LIMIT 1",
                    (namespace, typed_key, generation, generation),
                ).fetchone()
                self._metadata_rows += int(dangling_order is not None) + int(dangling_query is not None)
                if dangling_order or dangling_query:
                    raise StoreIntegrityError("membership/order points to absent lazy record")
                raise KeyError((namespace, key))
            value, schema, valid_from, valid_to, _ = self._check_record_row(
                namespace, typed_key, row, decode=True
            )
            if schema != expected_record_schema:
                raise StoreFormatError(
                    f"record schema mismatch for {(namespace, key)!r}: expected {expected_record_schema}, found {schema}"
                )
            return CheckedVersion(value, schema, valid_from, valid_to)
        finally:
            self._read_snapshot_end()

    def iter_keys(
        self, pin: GenerationPin, namespace: str, *, page_size: int = 128
    ) -> Iterator[Any]:
        self._ensure_open()
        _validate_namespace(namespace)
        if type(page_size) is not int or page_size <= 0 or page_size > MAX_PAGE_SIZE:
            raise ValueError("page_size must be in 1..128")

        def iterator() -> Iterator[Any]:
            last_ordinal = -1
            last_key = b""
            yielded = 0
            expected_count: int | None = None
            while expected_count is None or yielded < expected_count:
                self._ensure_open()
                generation = self._read_snapshot_start(pin)
                decoded_page: list[tuple[int, bytes, Any]] = []
                try:
                    head = int(self._checked_head_row()[0])
                    state = self._namespace_state_at(namespace, generation)
                    if state is None:
                        expected_count = 0
                        page = []
                    else:
                        expected_count = int(state[0])
                        if expected_count == 0:
                            page = []
                        elif generation == head:
                            page = self.db.execute(
                                "SELECT typed_key,ordinal,valid_from,valid_to,row_checksum "
                                "FROM lazy_order_versions INDEXED BY lazy_order_current "
                                "WHERE namespace=? AND valid_to IS NULL "
                                "AND (ordinal,typed_key) > (?,?) "
                                "ORDER BY ordinal,typed_key LIMIT ?",
                                (namespace, last_ordinal, last_key, page_size),
                            ).fetchall()
                        else:
                            open_rows = self.db.execute(
                                "SELECT typed_key,ordinal,valid_from,valid_to,row_checksum "
                                "FROM lazy_order_versions INDEXED BY lazy_order_current "
                                "WHERE namespace=? AND valid_to IS NULL AND valid_from<=? "
                                "AND (ordinal,typed_key) > (?,?) "
                                "ORDER BY ordinal,typed_key LIMIT ?",
                                (
                                    namespace,
                                    generation,
                                    last_ordinal,
                                    last_key,
                                    page_size,
                                ),
                            ).fetchall()
                            closed_rows = self.db.execute(
                                "SELECT typed_key,ordinal,valid_from,valid_to,row_checksum "
                                "FROM lazy_order_versions INDEXED BY lazy_order_closed_generation "
                                "WHERE namespace=? AND valid_to=? "
                                "AND (ordinal,typed_key) > (?,?) "
                                "ORDER BY ordinal,typed_key LIMIT ?",
                                (
                                    namespace,
                                    generation + 1,
                                    last_ordinal,
                                    last_key,
                                    page_size,
                                ),
                            ).fetchall()
                            page = sorted(
                                open_rows + closed_rows,
                                key=lambda row: (int(row[1]), row[0]),
                            )[:page_size]
                    self._query_rows += len(page)
                    for typed_key, ordinal, valid_from, valid_to, checksum in page:
                        if checksum != _order_checksum(
                            namespace, typed_key, ordinal, valid_from, valid_to
                        ):
                            raise StoreIntegrityError("lazy order checksum mismatch")
                        record = self._visible_record_row(generation, namespace, typed_key)
                        if record is None:
                            raise StoreIntegrityError("ordered key has no visible record")
                        self._check_record_row(
                            namespace, typed_key, record, decode=False
                        )
                        decoded_page.append(
                            (int(ordinal), typed_key, self.codec.decode(typed_key))
                        )
                    self._temporary_keys_peak = max(
                        self._temporary_keys_peak, len(decoded_page)
                    )
                finally:
                    self._read_snapshot_end()

                if not decoded_page:
                    if yielded != expected_count:
                        raise StoreIntegrityError(
                            "lazy collection order ended before namespace count"
                        )
                    return
                for ordinal, typed_key, decoded_key in decoded_page:
                    last_ordinal, last_key = ordinal, typed_key
                    yielded += 1
                    yield decoded_key
                if len(decoded_page) < page_size and yielded != expected_count:
                    raise StoreIntegrityError(
                        "lazy collection order ended before namespace count"
                    )

        return iterator()

    def query_keys(
        self, pin: GenerationPin, namespace: str, index_name: str, value: Any
    ) -> tuple[Any, ...]:
        self._ensure_open()
        _validate_namespace(namespace)
        if not isinstance(index_name, str) or not index_name or "\x00" in index_name:
            raise ValueError("index_name must be non-empty text")
        encoded_value = self.codec.encode(value)
        generation = self._read_snapshot_start(pin)
        try:
            head = int(self._checked_head_row()[0])
            if generation == head:
                rows = self.db.execute(
                    "SELECT record_key,ordinal,valid_from,valid_to,row_checksum "
                    "FROM lazy_query_versions INDEXED BY lazy_query_current "
                    "WHERE namespace=? AND index_name=? AND index_value=? AND valid_to IS NULL "
                    "ORDER BY ordinal,record_key",
                    (namespace, index_name, encoded_value),
                ).fetchall()
            else:
                open_rows = self.db.execute(
                    "SELECT record_key,ordinal,valid_from,valid_to,row_checksum "
                    "FROM lazy_query_versions INDEXED BY lazy_query_open_generation "
                    "WHERE namespace=? AND index_name=? AND index_value=? "
                    "AND valid_to IS NULL AND valid_from<=? "
                    "ORDER BY ordinal,record_key",
                    (namespace, index_name, encoded_value, generation),
                ).fetchall()
                closed_rows = self.db.execute(
                    "SELECT record_key,ordinal,valid_from,valid_to,row_checksum "
                    "FROM lazy_query_versions INDEXED BY lazy_query_closed_generation "
                    "WHERE namespace=? AND index_name=? AND index_value=? AND valid_to=? "
                    "ORDER BY ordinal,record_key",
                    (namespace, index_name, encoded_value, generation + 1),
                ).fetchall()
                rows = sorted(
                    open_rows + closed_rows,
                    key=lambda row: (int(row[1]), row[0]),
                )
            self._query_rows += len(rows)
            out = []
            seen = set()
            decoded_value = self.codec.decode(encoded_value)
            for record_key, ordinal, valid_from, valid_to, checksum in rows:
                marker_key = (record_key, int(ordinal))
                if marker_key in seen:
                    raise StoreIntegrityError("duplicate visible lazy query membership")
                seen.add(marker_key)
                expected = _query_checksum(
                    namespace,
                    index_name,
                    encoded_value,
                    record_key,
                    ordinal,
                    valid_from,
                    valid_to,
                )
                if checksum != expected:
                    raise StoreIntegrityError("lazy query checksum mismatch")
                record = self._visible_record_row(generation, namespace, record_key)
                if record is None:
                    raise StoreIntegrityError("query membership has no visible owner")
                _, _, _, _, memberships = self._check_record_row(
                    namespace, record_key, record, decode=False
                )
                owner_marker = (index_name, decoded_value, int(ordinal))
                if owner_marker not in memberships:
                    raise StoreIntegrityError(
                        "query membership is absent from owner metadata"
                    )
                out.append(self.codec.decode(record_key))
            return tuple(out)
        finally:
            self._read_snapshot_end()

    def _decode_memberships(self, blob: bytes) -> tuple[tuple[str, Any, int], ...]:
        raw = self.codec.decode(blob)
        if type(raw) is not tuple:
            raise StoreIntegrityError("invalid owner membership metadata")
        out = []
        seen = set()
        for item in raw:
            if type(item) is not tuple or len(item) != 3:
                raise StoreIntegrityError("invalid owner membership entry")
            index_name, value, ordinal = item
            if not isinstance(index_name, str) or not index_name or "\x00" in index_name:
                raise StoreIntegrityError("invalid membership index name")
            if type(ordinal) is not int or ordinal < 0:
                raise StoreIntegrityError("invalid membership ordinal")
            marker = (index_name, self.codec.encode(value), ordinal)
            if marker in seen:
                raise StoreIntegrityError("duplicate owner membership metadata")
            seen.add(marker)
            out.append((index_name, value, ordinal))
        return tuple(out)

    def _prepare_version_changes(self, changes: Iterable[VersionChange]) -> tuple[dict[str, Any], ...]:
        prepared = []
        seen = set()
        for change in tuple(changes):
            if not isinstance(change, VersionChange):
                raise TypeError("version_changes must contain VersionChange")
            namespace = _validate_namespace(change.namespace)
            typed_key = self.codec.encode(change.key)
            identity = (namespace, typed_key)
            if identity in seen:
                raise ValueError("duplicate version change")
            seen.add(identity)
            if type(change.record_schema) is not int or change.record_schema < 1:
                raise ValueError("record_schema must be a positive int")
            if change.delete and change.reinsertion:
                raise ValueError("delete and reinsertion are mutually exclusive")
            members = []
            member_markers = set()
            for membership in tuple(change.memberships):
                if not isinstance(membership, Membership):
                    raise TypeError("memberships must contain Membership")
                if not membership.index_name or "\x00" in membership.index_name:
                    raise ValueError("membership index_name must be non-empty text")
                if type(membership.ordinal) is not int or membership.ordinal < 0:
                    raise ValueError("membership ordinal must be a nonnegative int")
                encoded = self.codec.encode(membership.value)
                marker = (membership.index_name, encoded, membership.ordinal)
                if marker in member_markers:
                    raise ValueError("duplicate membership")
                member_markers.add(marker)
                members.append((membership.index_name, membership.value, membership.ordinal, encoded))
            canonical = tuple((name, value, ordinal) for name, value, ordinal, _ in members)
            memberships_blob = self.codec.encode(canonical)
            payload = None if change.delete else self.codec.encode(change.value)
            prepared.append(
                {
                    "change": change,
                    "namespace": namespace,
                    "typed_key": typed_key,
                    "payload": payload,
                    "memberships": tuple(members),
                    "memberships_blob": memberships_blob,
                }
            )
        return tuple(prepared)



    def _identity_state_at(
        self, generation: int
    ) -> tuple[int, int, int | None]:
        rows = self.db.execute(
            "SELECT next_incarnation_id,valid_from,valid_to,row_checksum "
            "FROM lazy_identity_state WHERE valid_from<=? "
            "AND (valid_to IS NULL OR ?<valid_to) "
            "ORDER BY valid_from DESC LIMIT 2",
            (generation, generation),
        ).fetchall()
        self._metadata_rows += len(rows)
        if len(rows) != 1:
            raise StoreIntegrityError(
                "identity state must have exactly one visible version"
            )
        next_id, valid_from, valid_to, checksum = rows[0]
        if (
            type(next_id) is not int
            or next_id <= 0
            or checksum
            != _identity_state_checksum(next_id, valid_from, valid_to)
        ):
            raise StoreIntegrityError("lazy identity state checksum mismatch")
        return int(next_id), int(valid_from), valid_to

    def _visible_identity_occurrence(
        self,
        generation: int,
        owner_namespace: str,
        owner_key: bytes,
        occurrence_path: bytes,
    ) -> tuple[int, int, int | None, str] | None:
        rows = self.db.execute(
            "SELECT incarnation_id,valid_from,valid_to,row_checksum "
            "FROM lazy_identity_occurrence_versions "
            "WHERE owner_namespace=? AND owner_key=? AND occurrence_path=? "
            "AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) "
            "ORDER BY valid_from DESC LIMIT 2",
            (
                owner_namespace,
                owner_key,
                occurrence_path,
                generation,
                generation,
            ),
        ).fetchall()
        self._metadata_rows += len(rows)
        if len(rows) > 1:
            raise StoreIntegrityError(
                "overlapping visible identity occurrence versions"
            )
        if not rows:
            return None
        incarnation_id, valid_from, valid_to, checksum = rows[0]
        if (
            type(incarnation_id) is not int
            or incarnation_id <= 0
            or checksum
            != _identity_occurrence_checksum(
                owner_namespace,
                owner_key,
                occurrence_path,
                incarnation_id,
                valid_from,
                valid_to,
            )
        ):
            raise StoreIntegrityError(
                "lazy identity occurrence checksum mismatch"
            )
        return int(incarnation_id), int(valid_from), valid_to, checksum

    def read_identity_state(self, pin: GenerationPin) -> int:
        self._ensure_open()
        generation = self._read_snapshot_start(pin)
        try:
            return self._identity_state_at(generation)[0]
        finally:
            self._read_snapshot_end()

    def read_identity_occurrence(
        self,
        pin: GenerationPin,
        owner_namespace: str,
        owner_key: Any,
        occurrence_path: tuple[Any, ...],
    ) -> CheckedIdentityOccurrence:
        self._ensure_open()
        namespace = _validate_namespace(owner_namespace)
        if type(occurrence_path) is not tuple:
            raise TypeError("identity occurrence path must be a tuple")
        encoded_key = self.codec.encode(owner_key)
        encoded_path = self.codec.encode(occurrence_path)
        generation = self._read_snapshot_start(pin)
        try:
            row = self._visible_identity_occurrence(
                generation, namespace, encoded_key, encoded_path
            )
            if row is None:
                raise KeyError(
                    (owner_namespace, owner_key, occurrence_path)
                )
            return CheckedIdentityOccurrence(row[0], row[1], row[2])
        finally:
            self._read_snapshot_end()

    def identity_occurrences_for_owner(
        self,
        pin: GenerationPin,
        owner_namespace: str,
        owner_key: Any,
    ) -> tuple[tuple[tuple[Any, ...], int], ...]:
        self._ensure_open()
        namespace = _validate_namespace(owner_namespace)
        encoded_key = self.codec.encode(owner_key)
        generation = self._read_snapshot_start(pin)
        try:
            rows = self.db.execute(
                "SELECT occurrence_path,incarnation_id,valid_from,valid_to,row_checksum "
                "FROM lazy_identity_occurrence_versions "
                "WHERE owner_namespace=? AND owner_key=? AND valid_from<=? "
                "AND (valid_to IS NULL OR ?<valid_to) ORDER BY occurrence_path",
                (namespace, encoded_key, generation, generation),
            ).fetchall()
            self._metadata_rows += len(rows)
            out = []
            for path, incarnation_id, valid_from, valid_to, checksum in rows:
                if checksum != _identity_occurrence_checksum(
                    namespace,
                    encoded_key,
                    path,
                    incarnation_id,
                    valid_from,
                    valid_to,
                ):
                    raise StoreIntegrityError(
                        "lazy identity occurrence checksum mismatch"
                    )
                decoded_path = self.codec.decode(path)
                if type(decoded_path) is not tuple:
                    raise StoreIntegrityError(
                        "identity occurrence path is not a tuple"
                    )
                out.append((decoded_path, int(incarnation_id)))
            return tuple(out)
        finally:
            self._read_snapshot_end()

    def _prepare_identity_changes(
        self, changes: Iterable[IdentityOccurrenceChange]
    ) -> tuple[dict[str, Any], ...]:
        prepared = []
        seen = set()
        for change in tuple(changes):
            if not isinstance(change, IdentityOccurrenceChange):
                raise TypeError(
                    "identity_changes must contain IdentityOccurrenceChange"
                )
            namespace = _validate_namespace(change.owner_namespace)
            if type(change.occurrence_path) is not tuple:
                raise TypeError("identity occurrence path must be a tuple")
            owner_key = self.codec.encode(change.owner_key)
            occurrence_path = self.codec.encode(change.occurrence_path)
            identity = (namespace, owner_key, occurrence_path)
            if identity in seen:
                raise ValueError("duplicate identity occurrence change")
            seen.add(identity)
            if change.delete:
                if change.incarnation_id is not None:
                    raise ValueError(
                        "deleted identity occurrence must not supply incarnation_id"
                    )
            elif type(change.incarnation_id) is not int or change.incarnation_id <= 0:
                raise ValueError(
                    "identity occurrence incarnation_id must be a positive int"
                )
            prepared.append(
                {
                    "change": change,
                    "owner_namespace": namespace,
                    "owner_key": owner_key,
                    "occurrence_path": occurrence_path,
                }
            )
        return tuple(prepared)

    def _prepare_ordinary_changes(self, changes: Iterable[RecordChange]) -> tuple[dict[str, Any], ...]:
        prepared = []
        seen = set()
        for change in tuple(changes):
            if not isinstance(change, RecordChange):
                raise TypeError("changes must contain RecordChange")
            namespace = _validate_namespace(change.namespace)
            typed_key = self.codec.encode(change.key)
            identity = (namespace, typed_key)
            if identity in seen:
                raise ValueError("duplicate ordinary record change")
            seen.add(identity)
            if type(change.record_schema) is not int or change.record_schema < 1:
                raise ValueError("record_schema must be a positive int")
            memberships = []
            mseen = set()
            for membership in tuple(change.memberships):
                if not isinstance(membership, Membership):
                    raise TypeError("memberships must contain Membership")
                if not membership.index_name or "\x00" in membership.index_name:
                    raise ValueError("membership index_name must be non-empty text")
                if type(membership.ordinal) is not int or membership.ordinal < 0:
                    raise ValueError("membership ordinal must be a nonnegative int")
                encoded = self.codec.encode(membership.value)
                marker = (membership.index_name, encoded, membership.ordinal)
                if marker in mseen:
                    raise ValueError("duplicate membership")
                mseen.add(marker)
                memberships.append((membership.index_name, encoded, membership.ordinal))
            payload = None if change.delete else self.codec.encode(change.value)
            prepared.append(
                {"change": change, "namespace": namespace, "typed_key": typed_key, "payload": payload, "memberships": tuple(memberships)}
            )
        return tuple(prepared)

    def _prepare_segments(self, segments: Iterable[NewSegment]) -> tuple[dict[str, Any], ...]:
        prepared = []
        seen = set()
        for segment in tuple(segments):
            if not isinstance(segment, NewSegment):
                raise TypeError("new_segments must contain NewSegment")
            namespace = _validate_namespace(segment.namespace)
            if type(segment.ordinal) is not int or segment.ordinal < 0:
                raise ValueError("segment ordinal must be a nonnegative int")
            if type(segment.element_count) is not int or segment.element_count < 0:
                raise ValueError("element_count must be a nonnegative int")
            identity = (namespace, segment.ordinal)
            if identity in seen:
                raise ValueError("duplicate new segment")
            seen.add(identity)
            prepared.append(
                {
                    "segment": segment,
                    "namespace": namespace,
                    "payload": self.codec.encode(segment.value),
                    "first_id": self.codec.encode(segment.first_id),
                    "last_id": self.codec.encode(segment.last_id),
                }
            )
        return tuple(prepared)

    def _namespace_state_at(self, namespace: str, generation: int) -> tuple[int, int, int, int | None] | None:
        rows = self.db.execute(
            "SELECT member_count,next_ordinal,valid_from,valid_to,row_checksum FROM lazy_namespace_state "
            "WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) "
            "ORDER BY valid_from DESC LIMIT 2",
            (namespace, generation, generation),
        ).fetchall()
        self._metadata_rows += len(rows)
        if len(rows) > 1:
            raise StoreIntegrityError("overlapping namespace state versions")
        if not rows:
            return None
        count, next_ordinal, valid_from, valid_to, checksum = rows[0]
        if checksum != _namespace_checksum(namespace, count, next_ordinal, valid_from, valid_to):
            raise StoreIntegrityError("lazy namespace state checksum mismatch")
        return int(count), int(next_ordinal), int(valid_from), valid_to

    def _close_record(self, namespace: str, typed_key: bytes, generation: int) -> tuple[Any, ...] | None:
        row = self._visible_record_row(generation - 1, namespace, typed_key)
        if row is None:
            return None
        valid_from, _, payload, payload_checksum, codec_version, record_schema, memberships_blob, _ = row
        checksum = _version_checksum(
            namespace, typed_key, record_schema, codec_version, valid_from, generation, memberships_blob, payload
        )
        self.db.execute(
            "UPDATE lazy_record_versions SET valid_to=?,row_checksum=? WHERE namespace=? AND typed_key=? AND valid_from=?",
            (generation, checksum, namespace, typed_key, valid_from),
        )
        self._metadata_rows += 1
        return row

    def _visible_order(self, namespace: str, typed_key: bytes, generation: int) -> tuple[Any, ...] | None:
        rows = self.db.execute(
            "SELECT ordinal,valid_from,valid_to,row_checksum FROM lazy_order_versions "
            "WHERE namespace=? AND typed_key=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) "
            "ORDER BY valid_from DESC LIMIT 2",
            (namespace, typed_key, generation, generation),
        ).fetchall()
        self._metadata_rows += len(rows)
        if len(rows) > 1:
            raise StoreIntegrityError("overlapping order versions")
        if not rows:
            return None
        ordinal, valid_from, valid_to, checksum = rows[0]
        if checksum != _order_checksum(namespace, typed_key, ordinal, valid_from, valid_to):
            raise StoreIntegrityError("lazy order checksum mismatch")
        return int(ordinal), int(valid_from), valid_to

    def _close_order(self, namespace: str, typed_key: bytes, generation: int) -> int | None:
        row = self._visible_order(namespace, typed_key, generation - 1)
        if row is None:
            return None
        ordinal, valid_from, _ = row
        checksum = _order_checksum(namespace, typed_key, ordinal, valid_from, generation)
        self.db.execute(
            "UPDATE lazy_order_versions SET valid_to=?,row_checksum=? WHERE namespace=? AND typed_key=? AND valid_from=?",
            (generation, checksum, namespace, typed_key, valid_from),
        )
        self._metadata_rows += 1
        return ordinal

    def _close_queries(self, namespace: str, typed_key: bytes, generation: int) -> None:
        rows = self.db.execute(
            "SELECT index_name,index_value,ordinal,valid_from FROM lazy_query_versions "
            "WHERE namespace=? AND record_key=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
            (namespace, typed_key, generation - 1, generation - 1),
        ).fetchall()
        self._query_rows += len(rows)
        for index_name, index_value, ordinal, valid_from in rows:
            checksum = _query_checksum(
                namespace, index_name, index_value, typed_key, ordinal, valid_from, generation
            )
            self.db.execute(
                "UPDATE lazy_query_versions SET valid_to=?,row_checksum=? WHERE namespace=? AND index_name=? "
                "AND index_value=? AND record_key=? AND ordinal=? AND valid_from=?",
                (generation, checksum, namespace, index_name, index_value, typed_key, ordinal, valid_from),
            )
            self._query_rows += 1

    def _validate_owner_projection(
        self,
        namespace: str,
        typed_key: bytes,
        generation: int,
        record_row: tuple[Any, ...],
        order_row: tuple[Any, ...] | None,
    ) -> None:
        if order_row is None:
            raise StoreIntegrityError("visible lazy record is missing collection order")
        _, _, _, _, memberships = self._check_record_row(
            namespace, typed_key, record_row, decode=False
        )
        expected = {
            (name, self.codec.encode(value), typed_key, ordinal)
            for name, value, ordinal in memberships
        }
        rows = self.db.execute(
            "SELECT index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum "
            "FROM lazy_query_versions WHERE namespace=? AND record_key=? AND valid_from<=? "
            "AND (valid_to IS NULL OR ?<valid_to)",
            (namespace, typed_key, generation, generation),
        ).fetchall()
        self._query_rows += len(rows)
        actual = set()
        for index_name, index_value, record_key, ordinal, valid_from, valid_to, checksum in rows:
            if checksum != _query_checksum(
                namespace, index_name, index_value, record_key, ordinal, valid_from, valid_to
            ):
                raise StoreIntegrityError("lazy query checksum mismatch")
            actual.add((index_name, index_value, record_key, int(ordinal)))
        if actual != expected:
            raise StoreIntegrityError(
                "lazy query membership is incomplete or inconsistent with owner metadata"
            )

    def _write_lazy_changes(
        self,
        prepared: tuple[dict[str, Any], ...],
        current_generation: int,
        new_generation: int,
        counts: dict[str, tuple[int, int]],
    ) -> None:
        by_namespace: dict[str, list[dict[str, Any]]] = {}
        for item in prepared:
            by_namespace.setdefault(item["namespace"], []).append(item)
        for namespace, items in by_namespace.items():
            if self.db.execute("SELECT 1 FROM records WHERE namespace=? LIMIT 1", (namespace,)).fetchone():
                raise StoreConflictError("lazy namespace already has ordinary record authority")
            state = self._namespace_state_at(namespace, current_generation)
            if state is None:
                member_count, next_ordinal = 0, 0
            else:
                member_count, next_ordinal = state[:2]
            final_count = member_count
            final_next = next_ordinal
            for item in items:
                change: VersionChange = item["change"]
                typed_key = item["typed_key"]
                existing = self._visible_record_row(current_generation, namespace, typed_key)
                order = self._visible_order(namespace, typed_key, current_generation)
                exists = existing is not None
                if exists:
                    self._validate_owner_projection(
                        namespace, typed_key, current_generation, existing, order
                    )
                elif order is not None:
                    raise StoreIntegrityError("collection order points to an absent lazy record")
                if change.delete:
                    if exists:
                        self._close_record(namespace, typed_key, new_generation)
                        self._close_order(namespace, typed_key, new_generation)
                        self._close_queries(namespace, typed_key, new_generation)
                        final_count -= 1
                        _bump_count(counts, namespace, records=-1)
                    continue
                if change.reinsertion and not exists:
                    historical = self.db.execute(
                        "SELECT 1 FROM lazy_record_versions WHERE namespace=? AND typed_key=? LIMIT 1",
                        (namespace, typed_key),
                    ).fetchone()
                    self._metadata_rows += 1
                    if historical is None:
                        raise ValueError("reinsertion requires an existing or historical key")
                if exists:
                    self._close_record(namespace, typed_key, new_generation)
                    self._close_queries(namespace, typed_key, new_generation)
                    if change.reinsertion:
                        self._close_order(namespace, typed_key, new_generation)
                        ordinal = final_next
                        final_next += 1
                    else:
                        if order is None:
                            raise StoreIntegrityError("visible lazy record is missing collection order")
                        ordinal = order[0]
                else:
                    ordinal = final_next
                    final_next += 1
                    final_count += 1
                    _bump_count(counts, namespace, records=1)
                payload = item["payload"]
                payload_checksum = _framed_sha(b"lazy-payload-v1", payload)
                row_checksum = _version_checksum(
                    namespace,
                    typed_key,
                    change.record_schema,
                    self.codec.version,
                    new_generation,
                    None,
                    item["memberships_blob"],
                    payload,
                )
                self.db.execute(
                    "INSERT INTO lazy_record_versions(namespace,typed_key,valid_from,valid_to,payload,payload_checksum,"
                    "codec_version,record_schema,memberships,row_checksum) VALUES (?,?,?,NULL,?,?,?,?,?,?)",
                    (
                        namespace,
                        typed_key,
                        new_generation,
                        payload,
                        payload_checksum,
                        self.codec.version,
                        change.record_schema,
                        item["memberships_blob"],
                        row_checksum,
                    ),
                )
                self._payload_writes += 1
                self._payload_write_bytes += len(payload)
                if not exists or change.reinsertion:
                    self.db.execute(
                        "INSERT INTO lazy_order_versions(namespace,typed_key,ordinal,valid_from,valid_to,row_checksum) "
                        "VALUES (?,?,?,?,NULL,?)",
                        (
                            namespace,
                            typed_key,
                            ordinal,
                            new_generation,
                            _order_checksum(namespace, typed_key, ordinal, new_generation, None),
                        ),
                    )
                    self._metadata_rows += 1
                for index_name, _value, membership_ordinal, encoded_value in item["memberships"]:
                    checksum = _query_checksum(
                        namespace,
                        index_name,
                        encoded_value,
                        typed_key,
                        membership_ordinal,
                        new_generation,
                        None,
                    )
                    self.db.execute(
                        "INSERT INTO lazy_query_versions(namespace,index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum) "
                        "VALUES (?,?,?,?,?,?,NULL,?)",
                        (
                            namespace,
                            index_name,
                            encoded_value,
                            typed_key,
                            membership_ordinal,
                            new_generation,
                            checksum,
                        ),
                    )
                    self._query_rows += 1
            if state is not None:
                _, _, old_from, _ = state
                checksum = _namespace_checksum(namespace, member_count, next_ordinal, old_from, new_generation)
                self.db.execute(
                    "UPDATE lazy_namespace_state SET valid_to=?,row_checksum=? WHERE namespace=? AND valid_from=?",
                    (new_generation, checksum, namespace, old_from),
                )
                self._metadata_rows += 1
            checksum = _namespace_checksum(namespace, final_count, final_next, new_generation, None)
            self.db.execute(
                "INSERT INTO lazy_namespace_state(namespace,valid_from,valid_to,member_count,next_ordinal,row_checksum) "
                "VALUES (?,?,NULL,?,?,?)",
                (namespace, new_generation, final_count, final_next, checksum),
            )
            self._metadata_rows += 1



    def _identity_changes_would_change(
        self,
        prepared: tuple[dict[str, Any], ...],
        generation: int,
        requested_next_incarnation_id: int | None,
    ) -> bool:
        current_next = self._identity_state_at(generation)[0]
        maximum_seen = current_next - 1
        for item in prepared:
            change: IdentityOccurrenceChange = item["change"]
            existing = self._visible_identity_occurrence(
                generation,
                item["owner_namespace"],
                item["owner_key"],
                item["occurrence_path"],
            )
            if change.delete:
                if existing is not None:
                    return True
                continue
            incarnation_id = int(change.incarnation_id)
            maximum_seen = max(maximum_seen, incarnation_id)
            if existing is None or existing[0] != incarnation_id:
                return True
        derived_next = max(current_next, maximum_seen + 1)
        if requested_next_incarnation_id is None:
            return derived_next != current_next
        if (
            type(requested_next_incarnation_id) is not int
            or requested_next_incarnation_id <= 0
        ):
            raise ValueError("next_incarnation_id must be a positive int")
        if requested_next_incarnation_id < derived_next:
            raise ValueError(
                "next_incarnation_id cannot move behind observed incarnations"
            )
        return requested_next_incarnation_id != current_next

    def _write_identity_changes(
        self,
        prepared: tuple[dict[str, Any], ...],
        current_generation: int,
        new_generation: int,
        *,
        requested_next_incarnation_id: int | None,
    ) -> None:
        current_next, state_from, _state_to = self._identity_state_at(
            current_generation
        )
        maximum_seen = current_next - 1
        changed = False
        for item in prepared:
            change: IdentityOccurrenceChange = item["change"]
            namespace = item["owner_namespace"]
            owner_key = item["owner_key"]
            occurrence_path = item["occurrence_path"]
            existing = self._visible_identity_occurrence(
                current_generation, namespace, owner_key, occurrence_path
            )
            if change.delete:
                if existing is None:
                    continue
                incarnation_id, valid_from, _valid_to, _checksum = existing
                new_checksum = _identity_occurrence_checksum(
                    namespace,
                    owner_key,
                    occurrence_path,
                    incarnation_id,
                    valid_from,
                    new_generation,
                )
                self.db.execute(
                    "UPDATE lazy_identity_occurrence_versions "
                    "SET valid_to=?,row_checksum=? "
                    "WHERE owner_namespace=? AND owner_key=? "
                    "AND occurrence_path=? AND valid_from=?",
                    (
                        new_generation,
                        new_checksum,
                        namespace,
                        owner_key,
                        occurrence_path,
                        valid_from,
                    ),
                )
                self._metadata_rows += 1
                changed = True
                continue

            incarnation_id = int(change.incarnation_id)
            maximum_seen = max(maximum_seen, incarnation_id)
            if existing is not None and existing[0] == incarnation_id:
                continue
            if existing is not None:
                old_id, valid_from, _valid_to, _checksum = existing
                close_checksum = _identity_occurrence_checksum(
                    namespace,
                    owner_key,
                    occurrence_path,
                    old_id,
                    valid_from,
                    new_generation,
                )
                self.db.execute(
                    "UPDATE lazy_identity_occurrence_versions "
                    "SET valid_to=?,row_checksum=? "
                    "WHERE owner_namespace=? AND owner_key=? "
                    "AND occurrence_path=? AND valid_from=?",
                    (
                        new_generation,
                        close_checksum,
                        namespace,
                        owner_key,
                        occurrence_path,
                        valid_from,
                    ),
                )
                self._metadata_rows += 1
            row_checksum = _identity_occurrence_checksum(
                namespace,
                owner_key,
                occurrence_path,
                incarnation_id,
                new_generation,
                None,
            )
            self.db.execute(
                "INSERT INTO lazy_identity_occurrence_versions("
                "owner_namespace,owner_key,occurrence_path,incarnation_id,"
                "valid_from,valid_to,row_checksum) VALUES (?,?,?,?,?,NULL,?)",
                (
                    namespace,
                    owner_key,
                    occurrence_path,
                    incarnation_id,
                    new_generation,
                    row_checksum,
                ),
            )
            self._metadata_rows += 1
            changed = True

        derived_next = max(current_next, maximum_seen + 1)
        if requested_next_incarnation_id is None:
            final_next = derived_next
        else:
            if (
                type(requested_next_incarnation_id) is not int
                or requested_next_incarnation_id <= 0
            ):
                raise ValueError(
                    "next_incarnation_id must be a positive int"
                )
            if requested_next_incarnation_id < derived_next:
                raise ValueError(
                    "next_incarnation_id cannot move behind observed incarnations"
                )
            final_next = requested_next_incarnation_id

        if not changed and final_next == current_next:
            return
        closed_checksum = _identity_state_checksum(
            current_next, state_from, new_generation
        )
        updated = self.db.execute(
            "UPDATE lazy_identity_state SET valid_to=?,row_checksum=? "
            "WHERE valid_from=? AND valid_to IS NULL",
            (new_generation, closed_checksum, state_from),
        ).rowcount
        if updated != 1:
            raise StoreIntegrityError(
                "current lazy identity state could not be closed"
            )
        self.db.execute(
            "INSERT INTO lazy_identity_state("
            "valid_from,valid_to,next_incarnation_id,row_checksum"
            ") VALUES (?,NULL,?,?)",
            (
                new_generation,
                final_next,
                _identity_state_checksum(final_next, new_generation, None),
            ),
        )
        self._metadata_rows += 2

    def _write_ordinary_changes(
        self,
        prepared: tuple[dict[str, Any], ...],
        new_generation: int,
        counts: dict[str, tuple[int, int]],
    ) -> tuple[int, int]:
        writes = deletes = 0
        lazy_namespaces = {
            row[0] for row in self.db.execute("SELECT DISTINCT namespace FROM lazy_namespace_state")
        }
        self._metadata_rows += len(lazy_namespaces)
        for item in prepared:
            change: RecordChange = item["change"]
            namespace = item["namespace"]
            typed_key = item["typed_key"]
            if namespace in lazy_namespaces:
                raise StoreConflictError("ordinary record change targets a declared lazy namespace")
            existed = self.db.execute(
                "SELECT 1 FROM records WHERE namespace=? AND typed_key=?", (namespace, typed_key)
            ).fetchone() is not None
            self._metadata_rows += 1
            if change.delete:
                deleted = self.db.execute(
                    "DELETE FROM records WHERE namespace=? AND typed_key=?", (namespace, typed_key)
                ).rowcount
                if deleted:
                    deletes += 1
                    _bump_count(counts, namespace, records=-1)
                continue
            payload = item["payload"]
            checksum = _record_checksum(
                namespace, typed_key, change.record_schema, self.codec.version, new_generation, payload
            )
            self.db.execute(
                "INSERT INTO records(namespace,typed_key,payload,payload_checksum,codec_version,record_schema,last_changed_generation) "
                "VALUES (?,?,?,?,?,?,?) ON CONFLICT(namespace,typed_key) DO UPDATE SET "
                "payload=excluded.payload,payload_checksum=excluded.payload_checksum,codec_version=excluded.codec_version,"
                "record_schema=excluded.record_schema,last_changed_generation=excluded.last_changed_generation",
                (namespace, typed_key, payload, checksum, self.codec.version, change.record_schema, new_generation),
            )
            if not existed:
                _bump_count(counts, namespace, records=1)
            self.db.execute("DELETE FROM query_membership WHERE namespace=? AND record_key=?", (namespace, typed_key))
            for index_name, encoded_value, ordinal in item["memberships"]:
                self.db.execute(
                    "INSERT INTO query_membership VALUES (?,?,?,?,?,?)",
                    (namespace, index_name, encoded_value, typed_key, ordinal, new_generation),
                )
            writes += 1
            self._payload_writes += 1
            self._payload_write_bytes += len(payload)
        return writes, deletes

    def _write_segments(
        self,
        prepared: tuple[dict[str, Any], ...],
        new_generation: int,
        counts: dict[str, tuple[int, int]],
    ) -> int:
        writes = 0
        for item in prepared:
            segment: NewSegment = item["segment"]
            namespace = item["namespace"]
            payload = item["payload"]
            checksum = _segment_checksum(
                namespace,
                segment.ordinal,
                item["first_id"],
                item["last_id"],
                segment.element_count,
                self.codec.version,
                new_generation,
                payload,
            )
            try:
                self.db.execute(
                    "INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        namespace,
                        segment.ordinal,
                        payload,
                        checksum,
                        self.codec.version,
                        segment.element_count,
                        item["first_id"],
                        item["last_id"],
                        new_generation,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise StoreConflictError(
                    f"segment already exists: {(namespace, segment.ordinal)}"
                ) from exc
            _bump_count(counts, namespace, segments=1)
            writes += 1
            self._payload_writes += 1
            self._payload_write_bytes += len(payload)
        return writes

    def _cleanup_expired(self, floor: int, *, batch_size: int = 4096) -> int:
        removed = 0
        for table in (
            "lazy_query_versions",
            "lazy_order_versions",
            "lazy_record_versions",
            "lazy_namespace_state",
            "lazy_identity_occurrence_versions",
            "lazy_identity_state",
        ):
            while True:
                rowids = [
                    row[0]
                    for row in self.db.execute(
                        f"SELECT rowid FROM {table} WHERE valid_to IS NOT NULL AND valid_to<=? LIMIT ?",
                        (floor, batch_size),
                    )
                ]
                self._maintenance_rows += len(rowids)
                if not rowids:
                    break
                placeholders = ",".join("?" for _ in rowids)
                self.db.execute(f"DELETE FROM {table} WHERE rowid IN ({placeholders})", rowids)
                removed += len(rowids)
                self._maintenance_rows += len(rowids)
                if len(rowids) < batch_size:
                    break
        return removed

    def commit(
        self,
        pin: GenerationPin,
        *,
        commit_token: Any,
        version_changes: Iterable[VersionChange],
        changes: Iterable[RecordChange],
        new_segments: Iterable[NewSegment],
        metadata: Mapping[str, Any],
        identity_changes: Iterable[IdentityOccurrenceChange] = (),
        next_incarnation_id: int | None = None,
    ) -> CommitResult:
        self._ensure_open()
        if pin.token in self._recovery_required:
            raise StoreConflictError("pin has unresolved commit acknowledgement")
        encoded_commit_token = self.codec.encode(commit_token)
        version_prepared = self._prepare_version_changes(version_changes)
        identity_prepared = self._prepare_identity_changes(identity_changes)
        ordinary_prepared = self._prepare_ordinary_changes(changes)
        segment_prepared = self._prepare_segments(new_segments)
        position, seed, next_ids, namespaces_blob = _head_values(self.codec, metadata)
        namespace_inventory = set(self.codec.decode(namespaces_blob))

        current = self._checked_head_row()
        current_generation = int(current[0])
        if pin.store_identity != self.store_identity:
            raise StoreConflictError("generation pin belongs to another store")
        try:
            registered_generation = self._require_pin(pin)
        except StoreConflictError:
            return CommitResult("conflict", current_generation, pin, stale=True)
        if registered_generation != current_generation:
            return CommitResult("conflict", current_generation, pin, stale=True)
        identity_effective = self._identity_changes_would_change(
            identity_prepared,
            current_generation,
            next_incarnation_id,
        )
        if (
            not version_prepared
            and not identity_effective
            and not ordinary_prepared
            and not segment_prepared
            and current[2:6]
            == (position, seed, next_ids, namespaces_blob)
        ):
            return CommitResult(
                "not_committed", current_generation, pin, stale=False
            )

        pins, _, attempts = self._checked_operational_rows(current_generation)
        existing_attempt = next(
            (row for row in attempts if row[0] == pin.token), None
        )
        if (
            existing_attempt is not None
            and existing_attempt[3] in {"pending", "committed"}
        ):
            raise StoreConflictError("pin has an unresolved commit attempt")
        other_generations = [
            int(row[2]) for row in pins if row[0] != pin.token
        ]
        if other_generations and min(other_generations) < current_generation:
            raise GenerationPressureError(
                current_generation, min(other_generations)
            )

        self._register_attempt(
            pin, encoded_commit_token, current_generation
        )
        self._phase_hook("before_transaction")
        self.db.execute("BEGIN IMMEDIATE")
        committed = False
        try:
            locked = self._checked_head_row()
            locked_generation = int(locked[0])
            pins, _, attempts = self._checked_operational_rows(
                locked_generation
            )
            pin_row = next(
                (row for row in pins if row[0] == pin.token), None
            )
            if pin_row is None:
                raise StoreConflictError("generation pin is not registered")
            attempt = next(
                (row for row in attempts if row[0] == pin.token), None
            )
            if (
                attempt is None
                or attempt[1] != encoded_commit_token
                or attempt[3] != "pending"
            ):
                raise StoreConflictError(
                    "commit attempt is no longer pending"
                )
            if (
                locked_generation != pin.captured_head
                or int(pin_row[2]) != pin.captured_head
            ):
                self.db.rollback()
                self.db.execute("BEGIN IMMEDIATE")
                row = self._attempt_row(pin.token)
                if (
                    row is not None
                    and row[0] == encoded_commit_token
                    and row[2] == "pending"
                ):
                    self._write_attempt_state(
                        pin.token,
                        encoded_commit_token,
                        current_generation,
                        "conflict",
                        None,
                    )
                self.db.commit()
                return CommitResult(
                    "conflict", locked_generation, pin, stale=True
                )

            other_generations = [
                int(row[2]) for row in pins if row[0] != pin.token
            ]
            if other_generations and min(other_generations) < locked_generation:
                raise GenerationPressureError(
                    locked_generation, min(other_generations)
                )

            counts = _namespace_counts(self.codec, locked[6])
            new_generation = locked_generation + 1
            self._write_lazy_changes(
                version_prepared,
                locked_generation,
                new_generation,
                counts,
            )
            self._phase_hook("during_version_writes")
            self._write_identity_changes(
                identity_prepared,
                locked_generation,
                new_generation,
                requested_next_incarnation_id=next_incarnation_id,
            )
            self._phase_hook("during_identity_writes")
            self._write_ordinary_changes(
                ordinary_prepared, new_generation, counts
            )
            self._phase_hook("during_ordinary_writes")
            self._write_segments(
                segment_prepared, new_generation, counts
            )
            self._phase_hook("during_segment_writes")

            missing = set(counts) - namespace_inventory
            if missing:
                raise ValueError(
                    f"head namespace inventory omits retained namespace: {sorted(missing)}"
                )
            counts_blob = _counts_blob(self.codec, counts)
            checksum = _head_checksum(
                new_generation,
                locked_generation,
                position,
                seed,
                next_ids,
                namespaces_blob,
                counts_blob,
            )
            self._phase_hook("before_head")
            self.db.execute(
                "UPDATE save_head SET generation=?,parent_generation=?,simulation_position=?,seed=?,next_ids=?,"
                "namespace_inventory=?,namespace_counts=?,head_checksum=? WHERE singleton=1",
                (
                    new_generation,
                    locked_generation,
                    position,
                    seed,
                    next_ids,
                    namespaces_blob,
                    counts_blob,
                    checksum,
                ),
            )
            new_pin_checksum = _pin_checksum(
                self.store_identity, pin.token, new_generation
            )
            self.db.execute(
                "UPDATE generation_pins SET generation=?,row_checksum=? WHERE token=?",
                (
                    new_generation,
                    new_pin_checksum,
                    pin.token,
                ),
            )
            receipt_checksum = _receipt_checksum(
                pin.token,
                encoded_commit_token,
                new_generation,
                locked_generation,
                "committed",
            )
            self.db.execute(
                "INSERT INTO pin_receipts(pin_token,commit_token,generation,parent_generation,outcome,row_checksum) "
                "VALUES (?,?,?,?,?,?) ON CONFLICT(pin_token) DO UPDATE SET commit_token=excluded.commit_token,"
                "generation=excluded.generation,parent_generation=excluded.parent_generation,outcome=excluded.outcome,"
                "row_checksum=excluded.row_checksum",
                (
                    pin.token,
                    encoded_commit_token,
                    new_generation,
                    locked_generation,
                    "committed",
                    receipt_checksum,
                ),
            )
            self._write_attempt_state(
                pin.token,
                encoded_commit_token,
                locked_generation,
                "committed",
                new_generation,
            )
            self._pin_rows += 2
            floor = self._validated_retention_floor(new_generation)
            self._cleanup_expired(floor)
            self._phase_hook("before_commit")
            try:
                self._commit_sqlite()
                committed = True
            except sqlite3.Error:
                if self.db.in_transaction:
                    self.db.rollback()
                self._recovery_required[pin.token] = (
                    encoded_commit_token
                )
                raise
        except Exception:
            if not committed and self.db.in_transaction:
                self.db.rollback()
            raise

        updated = GenerationPin(
            pin.token, self.store_identity, new_generation
        )
        try:
            self._phase_hook("after_commit")
            self._acknowledge_attempt(
                updated, encoded_commit_token, new_generation
            )
        except Exception:
            self._recovery_required[pin.token] = encoded_commit_token
            raise
        return CommitResult(
            "committed", new_generation, updated, stale=False
        )

    def resolve_commit(self, pin: GenerationPin, commit_token: Any) -> CommitResult:
        self._ensure_open()
        if pin.store_identity != self.store_identity:
            raise StoreConflictError("generation pin belongs to another store")
        encoded = self.codec.encode(commit_token)
        result: CommitResult | None = None
        self.db.execute("BEGIN IMMEDIATE")
        try:
            head = int(self._checked_head_row()[0])
            pins, receipts, attempts = self._checked_operational_rows(head)
            pin_row = next((row for row in pins if row[0] == pin.token), None)
            if pin_row is None:
                raise StoreConflictError("generation pin is not registered")
            attempt = next((row for row in attempts if row[0] == pin.token), None)
            if attempt is None or attempt[1] != encoded:
                raise StoreConflictError(
                    "commit token does not match the pin's latest attempt"
                )
            _, stored_token, parent, state, generation, checksum = attempt
            if checksum != _attempt_checksum(
                pin.token, stored_token, parent, state, generation
            ):
                raise StoreIntegrityError("pin attempt checksum mismatch")
            pin_generation = int(pin_row[2])
            receipt = next((row for row in receipts if row[0] == pin.token), None)

            if state in {"committed", "acknowledged"}:
                if (
                    receipt is None
                    or receipt[1] != encoded
                    or int(receipt[2]) != int(generation)
                    or int(receipt[3]) != int(parent)
                    or pin_generation != int(generation)
                ):
                    raise StoreIntegrityError(
                        "committed attempt is inconsistent with durable receipt or pin"
                    )
                if state == "committed":
                    self._write_attempt_state(
                        pin.token,
                        encoded,
                        int(parent),
                        "acknowledged",
                        int(generation),
                    )
                updated = GenerationPin(
                    pin.token, self.store_identity, int(generation)
                )
                result = CommitResult(
                    "committed",
                    int(generation),
                    updated,
                    stale=head > int(generation),
                )
            elif state == "pending":
                if receipt is not None and receipt[1] == encoded:
                    raise StoreIntegrityError(
                        "pending attempt unexpectedly has a committed receipt"
                    )
                if pin_generation == int(parent) and head == int(parent):
                    self._write_attempt_state(
                        pin.token, encoded, int(parent), "not_committed", None
                    )
                    result = CommitResult(
                        "not_committed",
                        pin_generation,
                        GenerationPin(
                            pin.token, self.store_identity, pin_generation
                        ),
                        stale=False,
                    )
                elif pin_generation == int(parent) and head > int(parent):
                    self._write_attempt_state(
                        pin.token, encoded, int(parent), "conflict", None
                    )
                    result = CommitResult(
                        "conflict",
                        head,
                        GenerationPin(
                            pin.token, self.store_identity, pin_generation
                        ),
                        stale=True,
                    )
                else:
                    raise StoreIntegrityError(
                        "pending attempt cannot be reconciled with head and pin"
                    )
            elif state == "not_committed":
                result = CommitResult(
                    "not_committed",
                    pin_generation,
                    GenerationPin(pin.token, self.store_identity, pin_generation),
                    stale=head > pin_generation,
                )
            elif state == "conflict":
                result = CommitResult(
                    "conflict",
                    head,
                    GenerationPin(pin.token, self.store_identity, pin_generation),
                    stale=head > pin_generation,
                )
            else:
                raise StoreIntegrityError("invalid pin attempt state")
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise
        if self._recovery_required.get(pin.token) == encoded:
            self._recovery_required.pop(pin.token, None)
        assert result is not None
        return result

    def _verify_ordinary(self, inventory: set[str]) -> tuple[dict[str, tuple[int, int]], int, int]:
        counts: dict[str, tuple[int, int]] = {}
        records = segments = 0
        lazy_namespaces = {row[0] for row in self.db.execute("SELECT DISTINCT namespace FROM lazy_namespace_state")}
        for namespace, typed_key, payload, checksum, codec_version, record_schema, generation in self.db.execute(
            "SELECT namespace,typed_key,payload,payload_checksum,codec_version,record_schema,last_changed_generation FROM records"
        ):
            if namespace in lazy_namespaces:
                raise StoreIntegrityError("lazy namespace also contains ordinary record authority")
            if namespace not in inventory:
                raise StoreIntegrityError("ordinary record namespace missing from head inventory")
            self.codec.decode(typed_key)
            expected = _record_checksum(namespace, typed_key, record_schema, codec_version, generation, payload)
            if checksum != expected or codec_version != self.codec.version:
                raise StoreIntegrityError("ordinary record checksum mismatch")
            self.codec.decode(payload)
            _bump_count(counts, namespace, records=1)
            records += 1
        for namespace, ordinal, first_id, last_id, element_count, payload, checksum, codec_version, generation in self.db.execute(
            "SELECT namespace,ordinal,first_id,last_id,element_count,payload,payload_checksum,codec_version,created_generation FROM segments"
        ):
            if namespace not in inventory:
                raise StoreIntegrityError("segment namespace missing from head inventory")
            self.codec.decode(first_id)
            self.codec.decode(last_id)
            expected = _segment_checksum(
                namespace, ordinal, first_id, last_id, element_count, codec_version, generation, payload
            )
            if checksum != expected or codec_version != self.codec.version:
                raise StoreIntegrityError("segment checksum mismatch")
            self.codec.decode(payload)
            _bump_count(counts, namespace, segments=1)
            segments += 1
        for namespace, record_key, index_value in self.db.execute(
            "SELECT namespace,record_key,index_value FROM query_membership"
        ):
            owner = self.db.execute(
                "SELECT 1 FROM records WHERE namespace=? AND typed_key=?", (namespace, record_key)
            ).fetchone()
            if owner is None:
                raise StoreIntegrityError("ordinary query membership has no owner")
            self.codec.decode(record_key)
            self.codec.decode(index_value)
        return counts, records, segments

    def _retained_generations(self, head: int) -> tuple[int, ...]:
        floor = self._validated_retention_floor(head)
        if floor < head - 1:
            raise StoreIntegrityError("more than two visible snapshots are retained")
        return tuple(range(floor, head + 1))

    def _verify_lazy_generation(self, generation: int) -> dict[str, int]:
        namespaces = [
            row[0]
            for row in self.db.execute(
                "SELECT namespace FROM lazy_namespace_state WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            )
        ]
        counts: dict[str, int] = {}
        for namespace in namespaces:
            state = self._namespace_state_at(namespace, generation)
            if state is None:
                raise StoreIntegrityError("visible lazy namespace has no state")
            expected_count, next_ordinal = state[:2]
            records = self.db.execute(
                "SELECT typed_key,valid_from,valid_to,payload,payload_checksum,codec_version,record_schema,memberships,row_checksum "
                "FROM lazy_record_versions WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (namespace, generation, generation),
            ).fetchall()
            seen_keys = set()
            expected_queries = set()
            for typed_key, valid_from, valid_to, payload, payload_checksum, codec_version, record_schema, memberships, row_checksum in records:
                if typed_key in seen_keys:
                    raise StoreIntegrityError("overlapping visible lazy record versions")
                seen_keys.add(typed_key)
                self.codec.decode(typed_key)
                self._check_record_row(
                    namespace,
                    typed_key,
                    (valid_from, valid_to, payload, payload_checksum, codec_version, record_schema, memberships, row_checksum),
                    decode=True,
                )
                for name, value, ordinal in self._decode_memberships(memberships):
                    expected_queries.add((name, self.codec.encode(value), typed_key, ordinal))
            if len(records) != expected_count:
                raise StoreIntegrityError("lazy namespace count does not match visible records")
            orders = self.db.execute(
                "SELECT typed_key,ordinal,valid_from,valid_to,row_checksum FROM lazy_order_versions "
                "WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (namespace, generation, generation),
            ).fetchall()
            if len(orders) != expected_count:
                raise StoreIntegrityError("lazy collection order is incomplete")
            seen_ordinals = set()
            order_keys = set()
            for typed_key, ordinal, valid_from, valid_to, checksum in orders:
                if checksum != _order_checksum(namespace, typed_key, ordinal, valid_from, valid_to):
                    raise StoreIntegrityError("lazy order checksum mismatch")
                if ordinal in seen_ordinals:
                    raise StoreIntegrityError("duplicate visible collection ordinal")
                seen_ordinals.add(ordinal)
                order_keys.add(typed_key)
                if ordinal >= next_ordinal:
                    raise StoreIntegrityError("collection ordinal is outside namespace counter")
            if order_keys != seen_keys:
                raise StoreIntegrityError("lazy collection order does not match visible owners")
            actual_queries = set()
            qrows = self.db.execute(
                "SELECT index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum FROM lazy_query_versions "
                "WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (namespace, generation, generation),
            ).fetchall()
            for index_name, index_value, record_key, ordinal, valid_from, valid_to, checksum in qrows:
                if checksum != _query_checksum(
                    namespace, index_name, index_value, record_key, ordinal, valid_from, valid_to
                ):
                    raise StoreIntegrityError("lazy query checksum mismatch")
                actual_queries.add((index_name, index_value, record_key, ordinal))
            if actual_queries != expected_queries:
                raise StoreIntegrityError("lazy query membership is incomplete or contains extra rows")
            counts[namespace] = expected_count
        return counts

    def verify_all(self) -> dict[str, int]:
        self._ensure_open()
        owns_snapshot = not self.db.in_transaction
        if owns_snapshot:
            self.db.execute("BEGIN")
        try:
            return self._verify_all_in_snapshot()
        finally:
            if owns_snapshot and self.db.in_transaction:
                self.db.rollback()

    def _verify_all_in_snapshot(self) -> dict[str, int]:
        integrity = self.db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise StoreIntegrityError(f"SQLite integrity check failed: {integrity}")
        if self.db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise StoreIntegrityError("foreign key check failed")
        head = self._checked_head_row()
        head_generation = int(head[0])
        inventory = set(self.codec.decode(head[5]))
        expected_counts = _namespace_counts(self.codec, head[6])

        pins, receipts, attempts = self._checked_operational_rows(head_generation)

        ordinary_counts, ordinary_records, segments = self._verify_ordinary(inventory)
        retained = self._retained_generations(head_generation)
        floor = retained[0]
        for table in (
            "lazy_query_versions",
            "lazy_order_versions",
            "lazy_record_versions",
            "lazy_namespace_state",
            "lazy_identity_occurrence_versions",
            "lazy_identity_state",
        ):
            obsolete = self.db.execute(
                f"SELECT 1 FROM {table} WHERE valid_to IS NOT NULL AND valid_to<=? LIMIT 1",
                (floor,),
            ).fetchone()
            if obsolete is not None:
                raise StoreIntegrityError("expired lazy versions remain below the retention floor")
        current_lazy_counts: dict[str, int] = {}
        current_identity_occurrences = 0
        for generation in retained:
            lazy_counts = self._verify_lazy_generation(generation)
            next_identity = self._identity_state_at(generation)[0]
            occurrence_rows = self.db.execute(
                "SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,"
                "valid_from,valid_to,row_checksum "
                "FROM lazy_identity_occurrence_versions "
                "WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            ).fetchall()
            seen_occurrences = set()
            for (
                owner_namespace,
                owner_key,
                occurrence_path,
                incarnation_id,
                valid_from,
                valid_to,
                checksum,
            ) in occurrence_rows:
                marker = (owner_namespace, owner_key, occurrence_path)
                if marker in seen_occurrences:
                    raise StoreIntegrityError(
                        "overlapping visible identity occurrences"
                    )
                seen_occurrences.add(marker)
                if checksum != _identity_occurrence_checksum(
                    owner_namespace,
                    owner_key,
                    occurrence_path,
                    incarnation_id,
                    valid_from,
                    valid_to,
                ):
                    raise StoreIntegrityError(
                        "lazy identity occurrence checksum mismatch"
                    )
                self.codec.decode(owner_key)
                path_value = self.codec.decode(occurrence_path)
                if type(path_value) is not tuple:
                    raise StoreIntegrityError(
                        "identity occurrence path is not a tuple"
                    )
                if incarnation_id >= next_identity:
                    raise StoreIntegrityError(
                        "identity occurrence exceeds allocator state"
                    )
            if generation == head_generation:
                current_lazy_counts = lazy_counts
                current_identity_occurrences = len(occurrence_rows)

        actual_counts = dict(ordinary_counts)
        for namespace, count in current_lazy_counts.items():
            if count:
                _bump_count(actual_counts, namespace, records=count)
            if namespace not in inventory:
                raise StoreIntegrityError("lazy namespace missing from head inventory")
        if actual_counts != expected_counts:
            raise StoreIntegrityError("committed namespace counts do not match current rows")

        # Every stored historical row is checksummed and structurally valid, even if not retained-visible.
        for namespace, typed_key, valid_from, valid_to, payload, payload_checksum, codec_version, record_schema, memberships, checksum in self.db.execute(
            "SELECT namespace,typed_key,valid_from,valid_to,payload,payload_checksum,codec_version,record_schema,memberships,row_checksum FROM lazy_record_versions"
        ):
            self.codec.decode(typed_key)
            self._check_record_row(
                namespace,
                typed_key,
                (valid_from, valid_to, payload, payload_checksum, codec_version, record_schema, memberships, checksum),
                decode=True,
            )
        for namespace, typed_key, ordinal, valid_from, valid_to, checksum in self.db.execute(
            "SELECT namespace,typed_key,ordinal,valid_from,valid_to,row_checksum FROM lazy_order_versions"
        ):
            if checksum != _order_checksum(namespace, typed_key, ordinal, valid_from, valid_to):
                raise StoreIntegrityError("lazy order checksum mismatch")
        for namespace, index_name, index_value, record_key, ordinal, valid_from, valid_to, checksum in self.db.execute(
            "SELECT namespace,index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum FROM lazy_query_versions"
        ):
            if checksum != _query_checksum(
                namespace, index_name, index_value, record_key, ordinal, valid_from, valid_to
            ):
                raise StoreIntegrityError("lazy query checksum mismatch")
        for namespace, member_count, next_ordinal, valid_from, valid_to, checksum in self.db.execute(
            "SELECT namespace,member_count,next_ordinal,valid_from,valid_to,row_checksum FROM lazy_namespace_state"
        ):
            if checksum != _namespace_checksum(namespace, member_count, next_ordinal, valid_from, valid_to):
                raise StoreIntegrityError("lazy namespace state checksum mismatch")
        for owner_namespace, owner_key, occurrence_path, incarnation_id, valid_from, valid_to, checksum in self.db.execute(
            "SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,valid_from,valid_to,row_checksum "
            "FROM lazy_identity_occurrence_versions"
        ):
            if checksum != _identity_occurrence_checksum(
                owner_namespace,
                owner_key,
                occurrence_path,
                incarnation_id,
                valid_from,
                valid_to,
            ):
                raise StoreIntegrityError(
                    "lazy identity occurrence checksum mismatch"
                )
            self.codec.decode(owner_key)
            if type(self.codec.decode(occurrence_path)) is not tuple:
                raise StoreIntegrityError(
                    "identity occurrence path is not a tuple"
                )
        for next_identity, valid_from, valid_to, checksum in self.db.execute(
            "SELECT next_incarnation_id,valid_from,valid_to,row_checksum "
            "FROM lazy_identity_state"
        ):
            if checksum != _identity_state_checksum(
                next_identity, valid_from, valid_to
            ):
                raise StoreIntegrityError(
                    "lazy identity state checksum mismatch"
                )

        return {
            "generation": head_generation,
            "lazy_records": sum(current_lazy_counts.values()),
            "ordinary_records": ordinary_records,
            "segments": segments,
            "pins": len(pins),
            "receipts": len(receipts),
            "attempts": len(attempts),
            "identity_occurrences": current_identity_occurrences,
            "next_incarnation_id": self._identity_state_at(
                head_generation
            )[0],
        }

    def storage_metrics(self) -> dict[str, int]:
        self._ensure_open()
        page_count = int(self.db.execute("PRAGMA page_count").fetchone()[0])
        freelist = int(self.db.execute("PRAGMA freelist_count").fetchone()[0])
        page_size = int(self.db.execute("PRAGMA page_size").fetchone()[0])
        return {
            "lazy_record_versions": self.db.execute("SELECT COUNT(*) FROM lazy_record_versions").fetchone()[0],
            "lazy_order_versions": self.db.execute("SELECT COUNT(*) FROM lazy_order_versions").fetchone()[0],
            "lazy_query_versions": self.db.execute("SELECT COUNT(*) FROM lazy_query_versions").fetchone()[0],
            "lazy_namespace_versions": self.db.execute("SELECT COUNT(*) FROM lazy_namespace_state").fetchone()[0],
            "identity_occurrence_versions": self.db.execute(
                "SELECT COUNT(*) FROM lazy_identity_occurrence_versions"
            ).fetchone()[0],
            "identity_state_versions": self.db.execute(
                "SELECT COUNT(*) FROM lazy_identity_state"
            ).fetchone()[0],
            "lazy_payload_bytes": self.db.execute("SELECT COALESCE(SUM(LENGTH(payload)),0) FROM lazy_record_versions").fetchone()[0],
            "ordinary_payload_bytes": self.db.execute("SELECT COALESCE(SUM(LENGTH(payload)),0) FROM records").fetchone()[0],
            "segment_payload_bytes": self.db.execute("SELECT COALESCE(SUM(LENGTH(payload)),0) FROM segments").fetchone()[0],
            "pins": self.db.execute("SELECT COUNT(*) FROM generation_pins").fetchone()[0],
            "receipts": self.db.execute("SELECT COUNT(*) FROM pin_receipts").fetchone()[0],
            "attempts": self.db.execute("SELECT COUNT(*) FROM pin_attempts").fetchone()[0],
            "sqlite_bytes": page_count * page_size,
            "sqlite_reusable_bytes": freelist * page_size,
        }

    def query_plan(
        self, pin: GenerationPin, namespace: str, index_name: str, value: Any
    ) -> tuple[str, ...]:
        encoded = self.codec.encode(value)
        generation = self._read_snapshot_start(pin)
        try:
            head = int(self._checked_head_row()[0])
            if generation == head:
                rows = self.db.execute(
                    "EXPLAIN QUERY PLAN SELECT record_key FROM lazy_query_versions "
                    "INDEXED BY lazy_query_current WHERE namespace=? AND index_name=? "
                    "AND index_value=? AND valid_to IS NULL ORDER BY ordinal,record_key",
                    (namespace, index_name, encoded),
                ).fetchall()
            else:
                rows = self.db.execute(
                    "EXPLAIN QUERY PLAN SELECT record_key FROM lazy_query_versions "
                    "INDEXED BY lazy_query_open_generation WHERE namespace=? AND index_name=? "
                    "AND index_value=? AND valid_to IS NULL AND valid_from<=? "
                    "ORDER BY ordinal,record_key",
                    (namespace, index_name, encoded, generation),
                ).fetchall()
                rows += self.db.execute(
                    "EXPLAIN QUERY PLAN SELECT record_key FROM lazy_query_versions "
                    "INDEXED BY lazy_query_closed_generation WHERE namespace=? AND index_name=? "
                    "AND index_value=? AND valid_to=? ORDER BY ordinal,record_key",
                    (namespace, index_name, encoded, generation + 1),
                ).fetchall()
            return tuple(str(row[-1]) for row in rows)
        finally:
            self._read_snapshot_end()

    def backup(self, destination: str | os.PathLike[str]) -> Path:
        self._ensure_open()
        destination = Path(destination)
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".ate-lazy-backup-", dir=destination.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        target = sqlite3.connect(tmp)
        try:
            self.db.backup(target)
            target.close()
            target = None
            os.link(tmp, destination)
            tmp.unlink()
            self._fsync_dir(destination.parent)
            return destination
        except Exception:
            if target is not None:
                target.close()
            if tmp.exists():
                tmp.unlink()
            raise

    @classmethod
    def copy_current_head(
        cls,
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        codec: TypedCodec,
        expected_simulation_schema: str,
        expected_rules_id: str,
    ) -> CopyResult:
        source = Path(source)
        destination = Path(destination)
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_store = cls.open(
            source,
            codec=codec,
            expected_simulation_schema=expected_simulation_schema,
            expected_rules_id=expected_rules_id,
        )
        staging = destination.parent / f".ate-current-copy-{uuid.uuid4().hex}.sqlite"
        new_store = None
        try:
            # Pin one source snapshot, scrub that exact snapshot, then copy only current authority.
            source_store.db.execute("BEGIN")
            source_store.verify_all()
            head = source_store._checked_head_row()
            generation = int(head[0])
            lazy_records = source_store.db.execute(
                "SELECT namespace,typed_key,valid_from,valid_to,payload,payload_checksum,codec_version,record_schema,memberships,row_checksum "
                "FROM lazy_record_versions WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            ).fetchall()
            lazy_orders = source_store.db.execute(
                "SELECT namespace,typed_key,ordinal,valid_from,valid_to,row_checksum FROM lazy_order_versions "
                "WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            ).fetchall()
            lazy_queries = source_store.db.execute(
                "SELECT namespace,index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum "
                "FROM lazy_query_versions WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            ).fetchall()
            lazy_states = source_store.db.execute(
                "SELECT namespace,valid_from,valid_to,member_count,next_ordinal,row_checksum FROM lazy_namespace_state "
                "WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            ).fetchall()
            identity_occurrences = source_store.db.execute(
                "SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,"
                "valid_from,valid_to,row_checksum "
                "FROM lazy_identity_occurrence_versions "
                "WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            ).fetchall()
            identity_state = source_store.db.execute(
                "SELECT valid_from,valid_to,next_incarnation_id,row_checksum "
                "FROM lazy_identity_state WHERE valid_from<=? "
                "AND (valid_to IS NULL OR ?<valid_to)",
                (generation, generation),
            ).fetchall()
            if len(identity_state) != 1:
                raise StoreIntegrityError(
                    "identity state must have exactly one current version"
                )
            ordinary_records = source_store.db.execute("SELECT * FROM records").fetchall()
            ordinary_memberships = source_store.db.execute("SELECT * FROM query_membership").fetchall()
            segments = source_store.db.execute("SELECT * FROM segments").fetchall()

            cls._copy_phase_hook("after_source_capture")
            new_store = cls.create(
                staging,
                codec=codec,
                simulation_schema=expected_simulation_schema,
                rules_id=expected_rules_id,
            )
            new_store.db.execute("BEGIN IMMEDIATE")
            try:
                new_store.db.execute("DELETE FROM save_head")
                new_store.db.execute(
                    "INSERT INTO save_head VALUES (1,?,?,?,?,?,?,?,?)",
                    head,
                )
                new_store.db.executemany(
                    "INSERT INTO records VALUES (?,?,?,?,?,?,?)", ordinary_records
                )
                new_store.db.executemany(
                    "INSERT INTO query_membership VALUES (?,?,?,?,?,?)", ordinary_memberships
                )
                new_store.db.executemany(
                    "INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?)", segments
                )
                new_store.db.executemany(
                    "INSERT INTO lazy_record_versions VALUES (?,?,?,?,?,?,?,?,?,?)", lazy_records
                )
                new_store.db.executemany(
                    "INSERT INTO lazy_order_versions VALUES (?,?,?,?,?,?)", lazy_orders
                )
                new_store.db.executemany(
                    "INSERT INTO lazy_query_versions VALUES (?,?,?,?,?,?,?,?)", lazy_queries
                )
                new_store.db.executemany(
                    "INSERT INTO lazy_namespace_state VALUES (?,?,?,?,?,?)", lazy_states
                )
                new_store.db.execute("DELETE FROM lazy_identity_state")
                new_store.db.executemany(
                    "INSERT INTO lazy_identity_occurrence_versions VALUES (?,?,?,?,?,?,?)",
                    identity_occurrences,
                )
                new_store.db.executemany(
                    "INSERT INTO lazy_identity_state VALUES (?,?,?,?)",
                    identity_state,
                )
                # create() starts with no pins/receipts; keep operational state empty.
                new_store.db.execute("DELETE FROM save_receipts")
                new_store.db.execute("DELETE FROM pin_receipts")
                new_store.db.execute("DELETE FROM pin_attempts")
                new_store.db.execute("DELETE FROM generation_pins")
                new_store.db.commit()
            except Exception:
                new_store.db.rollback()
                raise
            source_store.db.rollback()
            new_store.verify_all()
            identity = new_store.store_identity
            new_store.close()
            new_store = None
            cls._copy_phase_hook("before_publish")
            if destination.exists():
                raise FileExistsError(destination)
            os.link(staging, destination)
            staging.unlink()
            cls._fsync_dir(destination.parent)
            return CopyResult(destination, identity, generation)
        except Exception:
            if source_store.db.in_transaction:
                source_store.db.rollback()
            if new_store is not None:
                new_store.close()
            if staging.exists():
                staging.unlink()
            raise
        finally:
            source_store.close()

    def close(self) -> None:
        if not self._closed:
            self.db.close()
            self._closed = True

    def __enter__(self) -> "LazyRecordStore":
        self._ensure_open()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
