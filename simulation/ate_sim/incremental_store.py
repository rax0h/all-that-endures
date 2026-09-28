from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import os
import sqlite3
import struct
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

FORMAT_VERSION = 2
CODEC_VERSION = 1
RECEIPT_RETENTION = 64


class StoreError(Exception):
    pass


class StoreFormatError(StoreError):
    pass


class StoreIntegrityError(StoreError):
    pass


class StoreConflictError(StoreError):
    pass


class CodecError(StoreError):
    pass


@dataclass(frozen=True)
class Membership:
    index_name: str
    value: Any
    ordinal: int = 0


@dataclass(frozen=True)
class RecordChange:
    namespace: str
    key: Any
    value: Any = None
    record_schema: int = 1
    delete: bool = False
    memberships: tuple[Membership, ...] = ()


@dataclass(frozen=True)
class NewSegment:
    namespace: str
    ordinal: int
    value: Any
    element_count: int
    first_id: Any = None
    last_id: Any = None


@dataclass(frozen=True)
class StoreDiagnostics:
    payload_reads: int
    payload_read_bytes: int
    payload_writes: int
    payload_write_bytes: int


@dataclass(frozen=True)
class CheckedSegment:
    """Decoded immutable segment plus checksum-protected storage metadata."""

    value: Any
    element_count: int
    first_id: Any
    last_id: Any
    created_generation: int
    payload_bytes: int


class TypedCodec:
    """Versioned, allowlisted, lossless serializer for persistence payloads."""

    def __init__(self):
        self._enum_by_type: dict[type[Enum], str] = {}
        self._enum_by_name: dict[str, type[Enum]] = {}
        self._record_by_type: dict[type[Any], str] = {}
        self._record_by_name: dict[str, type[Any]] = {}

    @property
    def version(self) -> int:
        return CODEC_VERSION

    def register_enum(self, name: str, enum_type: type[Enum]) -> None:
        self._register_name(name)
        if not issubclass(enum_type, Enum):
            raise TypeError("enum_type must subclass Enum")
        if enum_type in self._enum_by_type or name in self._enum_by_name:
            raise ValueError("enum registration already exists")
        self._enum_by_type[enum_type] = name
        self._enum_by_name[name] = enum_type

    def register_record(self, name: str, record_type: type[Any]) -> None:
        self._register_name(name)
        if not dataclasses.is_dataclass(record_type):
            raise TypeError("record_type must be a dataclass type")
        if record_type in self._record_by_type or name in self._record_by_name:
            raise ValueError("record registration already exists")
        self._record_by_type[record_type] = name
        self._record_by_name[name] = record_type

    @staticmethod
    def _register_name(name: str) -> None:
        if not isinstance(name, str) or not name or "\x00" in name:
            raise ValueError("registration name must be non-empty text")

    def encode(self, value: Any) -> bytes:
        node = self._encode_value(value, set(), set())
        return json.dumps(node, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def decode(self, payload: bytes) -> Any:
        try:
            node = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise CodecError("invalid typed payload") from exc
        return self._decode_value(node)

    def _encode_value(self, value: Any, active: set[int], seen_mutable: set[int]) -> Any:
        if value is None:
            return ["none"]
        if type(value) is bool:
            return ["bool", value]
        if type(value) is int:
            return ["int", str(value)]
        if type(value) is float:
            return ["float64", struct.pack(">d", value).hex()]
        if type(value) is str:
            return ["str", value]
        if type(value) is bytes:
            return ["bytes", base64.b64encode(value).decode("ascii")]

        enum_name = self._enum_by_type.get(type(value))
        if enum_name is not None:
            return ["enum", enum_name, value.name]

        record_name = self._record_by_type.get(type(value))
        if record_name is not None:
            self._enter(value, active, seen_mutable, mutable=True)
            try:
                fields = []
                for field in dataclasses.fields(value):
                    fields.append([field.name, self._encode_value(getattr(value, field.name), active, seen_mutable)])
                return ["record", record_name, fields]
            finally:
                active.remove(id(value))

        if type(value) is list:
            self._enter(value, active, seen_mutable, mutable=True)
            try:
                return ["list", [self._encode_value(v, active, seen_mutable) for v in value]]
            finally:
                active.remove(id(value))
        if type(value) is tuple:
            self._enter(value, active, seen_mutable, mutable=False)
            try:
                return ["tuple", [self._encode_value(v, active, seen_mutable) for v in value]]
            finally:
                active.remove(id(value))
        if type(value) is set:
            self._enter(value, active, seen_mutable, mutable=True)
            try:
                encoded = [self._encode_value(v, active, seen_mutable) for v in value]
                encoded.sort(key=self._node_sort_key)
                return ["set", encoded]
            finally:
                active.remove(id(value))
        if type(value) is frozenset:
            self._enter(value, active, seen_mutable, mutable=False)
            try:
                encoded = [self._encode_value(v, active, seen_mutable) for v in value]
                encoded.sort(key=self._node_sort_key)
                return ["frozenset", encoded]
            finally:
                active.remove(id(value))
        if type(value) is dict:
            self._enter(value, active, seen_mutable, mutable=True)
            try:
                pairs = [
                    [self._encode_value(k, active, seen_mutable), self._encode_value(v, active, seen_mutable)]
                    for k, v in value.items()
                ]
                return ["dict", pairs]
            finally:
                active.remove(id(value))
        raise CodecError(f"unsupported typed value: {type(value).__name__}")

    @staticmethod
    def _node_sort_key(node: Any) -> bytes:
        return json.dumps(node, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _enter(value: Any, active: set[int], seen_mutable: set[int], *, mutable: bool) -> None:
        ident = id(value)
        if ident in active:
            raise CodecError("cycles are not supported")
        if mutable:
            if ident in seen_mutable:
                raise CodecError("shared mutable identity requires an explicit adapter")
            seen_mutable.add(ident)
        active.add(ident)

    def _decode_value(self, node: Any) -> Any:
        if not isinstance(node, list) or not node or not isinstance(node[0], str):
            raise CodecError("invalid typed node")
        tag = node[0]
        if tag == "none" and len(node) == 1:
            return None
        if tag == "bool" and len(node) == 2 and type(node[1]) is bool:
            return node[1]
        if tag == "int" and len(node) == 2 and isinstance(node[1], str):
            try:
                return int(node[1])
            except ValueError as exc:
                raise CodecError("invalid integer payload") from exc
        if tag == "float64" and len(node) == 2 and isinstance(node[1], str):
            try:
                raw = bytes.fromhex(node[1])
                if len(raw) != 8:
                    raise ValueError
                return struct.unpack(">d", raw)[0]
            except Exception as exc:
                raise CodecError("invalid float payload") from exc
        if tag == "str" and len(node) == 2 and isinstance(node[1], str):
            return node[1]
        if tag == "bytes" and len(node) == 2 and isinstance(node[1], str):
            try:
                return base64.b64decode(node[1].encode("ascii"), validate=True)
            except Exception as exc:
                raise CodecError("invalid bytes payload") from exc
        if tag in ("list", "tuple", "set", "frozenset") and len(node) == 2 and isinstance(node[1], list):
            values = [self._decode_value(v) for v in node[1]]
            if tag == "list":
                return values
            if tag == "tuple":
                return tuple(values)
            if tag == "set":
                try:
                    return set(values)
                except TypeError as exc:
                    raise CodecError("decoded set contains unhashable value") from exc
            try:
                return frozenset(values)
            except TypeError as exc:
                raise CodecError("decoded frozenset contains unhashable value") from exc
        if tag == "dict" and len(node) == 2 and isinstance(node[1], list):
            result = {}
            for pair in node[1]:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise CodecError("invalid dictionary entry")
                key = self._decode_value(pair[0])
                try:
                    if key in result:
                        raise CodecError("duplicate dictionary key")
                except TypeError as exc:
                    raise CodecError("dictionary key is unhashable") from exc
                result[key] = self._decode_value(pair[1])
            return result
        if tag == "enum" and len(node) == 3 and all(isinstance(x, str) for x in node[1:]):
            enum_type = self._enum_by_name.get(node[1])
            if enum_type is None:
                raise CodecError(f"unregistered enum type: {node[1]}")
            try:
                return enum_type[node[2]]
            except KeyError as exc:
                raise CodecError("unknown enum member") from exc
        if tag == "record" and len(node) == 3 and isinstance(node[1], str) and isinstance(node[2], list):
            record_type = self._record_by_name.get(node[1])
            if record_type is None:
                raise CodecError(f"unregistered record type: {node[1]}")
            expected = [f.name for f in dataclasses.fields(record_type)]
            actual = []
            restored = {}
            for pair in node[2]:
                if not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], str):
                    raise CodecError("invalid record field")
                actual.append(pair[0])
                restored[pair[0]] = self._decode_value(pair[1])
            if actual != expected:
                raise CodecError("record field schema mismatch")
            try:
                obj = object.__new__(record_type)
                for field in dataclasses.fields(record_type):
                    object.__setattr__(obj, field.name, restored[field.name])
                return obj
            except Exception as exc:
                raise CodecError("registered record restoration failed") from exc
        raise CodecError(f"unknown or malformed typed tag: {tag}")


DDL = """
CREATE TABLE store_metadata(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE save_head(
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    generation INTEGER NOT NULL,
    parent_generation INTEGER,
    simulation_position BLOB NOT NULL,
    seed INTEGER NOT NULL,
    next_ids BLOB NOT NULL,
    namespace_inventory BLOB NOT NULL,
    namespace_counts BLOB NOT NULL,
    head_checksum TEXT NOT NULL
);
CREATE TABLE records(
    namespace TEXT NOT NULL,
    typed_key BLOB NOT NULL,
    payload BLOB NOT NULL,
    payload_checksum TEXT NOT NULL,
    codec_version INTEGER NOT NULL,
    record_schema INTEGER NOT NULL,
    last_changed_generation INTEGER NOT NULL,
    PRIMARY KEY(namespace,typed_key)
);
CREATE TABLE segments(
    namespace TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    payload BLOB NOT NULL,
    payload_checksum TEXT NOT NULL,
    codec_version INTEGER NOT NULL,
    element_count INTEGER NOT NULL,
    first_id BLOB NOT NULL,
    last_id BLOB NOT NULL,
    created_generation INTEGER NOT NULL,
    PRIMARY KEY(namespace,ordinal)
);
CREATE TABLE query_membership(
    namespace TEXT NOT NULL,
    index_name TEXT NOT NULL,
    index_value BLOB NOT NULL,
    record_key BLOB NOT NULL,
    ordinal INTEGER NOT NULL,
    generation INTEGER NOT NULL,
    PRIMARY KEY(namespace,index_name,index_value,record_key,ordinal),
    FOREIGN KEY(namespace,record_key) REFERENCES records(namespace,typed_key) ON DELETE CASCADE
);
CREATE INDEX query_membership_lookup
    ON query_membership(namespace,index_name,index_value,ordinal,record_key);
CREATE TABLE save_receipts(
    generation INTEGER PRIMARY KEY,
    parent_generation INTEGER,
    committed_at REAL NOT NULL,
    record_writes INTEGER NOT NULL,
    record_deletes INTEGER NOT NULL,
    segment_writes INTEGER NOT NULL,
    payload_bytes INTEGER NOT NULL
);
"""


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _framed_sha(*parts: bytes) -> str:
    h = hashlib.sha256()
    for piece in parts:
        h.update(len(piece).to_bytes(8, "big"))
        h.update(piece)
    return h.hexdigest()


def _int_bytes(value: int) -> bytes:
    return str(value).encode("ascii")


def _record_checksum(
    namespace: str,
    typed_key: bytes,
    record_schema: int,
    codec_version: int,
    generation: int,
    payload: bytes,
) -> str:
    return _framed_sha(
        b"record",
        namespace.encode("utf-8"),
        typed_key,
        _int_bytes(record_schema),
        _int_bytes(codec_version),
        _int_bytes(generation),
        payload,
    )


def _segment_checksum(
    namespace: str,
    ordinal: int,
    first_id: bytes,
    last_id: bytes,
    element_count: int,
    codec_version: int,
    generation: int,
    payload: bytes,
) -> str:
    return _framed_sha(
        b"segment",
        namespace.encode("utf-8"),
        _int_bytes(ordinal),
        first_id,
        last_id,
        _int_bytes(element_count),
        _int_bytes(codec_version),
        _int_bytes(generation),
        payload,
    )


def _validate_namespace(namespace: str) -> str:
    if not isinstance(namespace, str) or not namespace or "\x00" in namespace:
        raise ValueError("namespace must be non-empty text")
    return namespace


def _head_values(codec: TypedCodec, metadata: Mapping[str, Any]) -> tuple[bytes, int, bytes, bytes]:
    required = {"simulation_position", "seed", "next_ids", "namespaces"}
    if set(metadata) != required:
        raise ValueError(f"head metadata keys must be exactly {sorted(required)}")
    seed = metadata["seed"]
    if type(seed) is not int:
        raise TypeError("seed must be int")
    namespaces = metadata["namespaces"]
    if not isinstance(namespaces, (list, tuple, set, frozenset)):
        raise TypeError("namespaces must be a collection")
    normalized = tuple(sorted({_validate_namespace(x) for x in namespaces}))
    return (
        codec.encode(metadata["simulation_position"]),
        seed,
        codec.encode(metadata["next_ids"]),
        codec.encode(normalized),
    )


def _namespace_counts(codec: TypedCodec, blob: bytes) -> dict[str, tuple[int, int]]:
    raw = codec.decode(blob)
    if type(raw) is not dict:
        raise StoreIntegrityError("invalid namespace counts")
    result: dict[str, tuple[int, int]] = {}
    for namespace, pair in raw.items():
        if type(namespace) is not str:
            raise StoreIntegrityError("invalid namespace count key")
        _validate_namespace(namespace)
        if type(pair) is not tuple or len(pair) != 2 or any(type(v) is not int or v < 0 for v in pair):
            raise StoreIntegrityError("invalid namespace count value")
        if pair == (0, 0):
            raise StoreIntegrityError("zero namespace count must be omitted")
        result[namespace] = pair
    return result


def _counts_blob(codec: TypedCodec, counts: Mapping[str, tuple[int, int]]) -> bytes:
    normalized = {
        namespace: (int(pair[0]), int(pair[1]))
        for namespace, pair in sorted(counts.items())
        if pair != (0, 0)
    }
    return codec.encode(normalized)


def _bump_count(
    counts: dict[str, tuple[int, int]],
    namespace: str,
    *,
    records: int = 0,
    segments: int = 0,
) -> None:
    before = counts.get(namespace, (0, 0))
    after = (before[0] + records, before[1] + segments)
    if after[0] < 0 or after[1] < 0:
        raise StoreIntegrityError("namespace count underflow")
    if after == (0, 0):
        counts.pop(namespace, None)
    else:
        counts[namespace] = after


def _head_checksum(
    generation: int,
    parent: int | None,
    position: bytes,
    seed: int,
    next_ids: bytes,
    namespaces: bytes,
    namespace_counts: bytes,
) -> str:
    return _framed_sha(
        _int_bytes(generation),
        str(parent).encode("ascii"),
        position,
        _int_bytes(seed),
        next_ids,
        namespaces,
        namespace_counts,
    )


class TransactionalStore:
    def __init__(self, path: Path, db: sqlite3.Connection, codec: TypedCodec):
        self.path = path
        self.db = db
        self.codec = codec
        self._closed = False
        self._payload_reads = 0
        self._payload_read_bytes = 0
        self._payload_writes = 0
        self._payload_write_bytes = 0
        self._phase_hook = lambda phase: None

    @classmethod
    def create(
        cls,
        path: str | os.PathLike[str],
        *,
        simulation_schema: str,
        rules_id: str,
        codec: TypedCodec | None = None,
        metadata: Mapping[str, Any] | None = None,
        journal_mode: str = "DELETE",
        synchronous: str = "FULL",
    ) -> "TransactionalStore":
        if journal_mode.upper() != "DELETE" or synchronous.upper() != "FULL":
            raise ValueError("P1 supports only journal_mode=DELETE and synchronous=FULL")
        codec = codec or TypedCodec()
        path = Path(path)
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".ate-store-", dir=path.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        db = None
        try:
            db = sqlite3.connect(tmp)
            cls._configure(db)
            db.executescript(DDL)
            store_id = str(uuid.uuid4())
            rows = {
                "store_uuid": store_id,
                "format_version": str(FORMAT_VERSION),
                "codec_version": str(codec.version),
                "simulation_schema": str(simulation_schema),
                "rules_id": str(rules_id),
                "journal_mode": "delete",
                "synchronous": "2",
            }
            db.executemany("INSERT INTO store_metadata(key,value) VALUES (?,?)", rows.items())
            metadata = metadata or {"simulation_position": None, "seed": 0, "next_ids": {}, "namespaces": ()}
            position, seed, next_ids, namespaces = _head_values(codec, metadata)
            namespace_counts = _counts_blob(codec, {})
            checksum = _head_checksum(0, None, position, seed, next_ids, namespaces, namespace_counts)
            db.execute(
                "INSERT INTO save_head VALUES (1,0,NULL,?,?,?,?,?,?)",
                (position, seed, next_ids, namespaces, namespace_counts, checksum),
            )
            db.commit()
            db.close(); db = None
            os.link(tmp, path)
            tmp.unlink()
            cls._fsync_dir(path.parent)
            return cls.open(
                path,
                codec=codec,
                expected_simulation_schema=str(simulation_schema),
                expected_rules_id=str(rules_id),
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
        codec: TypedCodec | None = None,
        expected_simulation_schema: str | None = None,
        expected_rules_id: str | None = None,
    ) -> "TransactionalStore":
        codec = codec or TypedCodec()
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
            if rows.get("journal_mode") != "delete" or rows.get("synchronous") != "2":
                raise StoreFormatError("store was not created with required durability settings")
            if expected_simulation_schema is not None and rows.get("simulation_schema") != str(expected_simulation_schema):
                raise StoreFormatError("simulation schema mismatch")
            if expected_rules_id is not None and rows.get("rules_id") != str(expected_rules_id):
                raise StoreFormatError("rules identifier mismatch")
            head = db.execute("SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts,head_checksum FROM save_head WHERE singleton=1").fetchone()
            if head is None:
                raise StoreIntegrityError("missing save head")
            if _head_checksum(*head[:-1]) != head[-1]:
                raise StoreIntegrityError("save head checksum mismatch")
            # Decode only bounded head metadata on open; cold payloads are verified on access/full scrub.
            codec.decode(head[2]); codec.decode(head[4]); codec.decode(head[5])
            counts = _namespace_counts(codec, head[6])
            inventory = set(codec.decode(head[5]))
            if not set(counts).issubset(inventory):
                raise StoreIntegrityError("namespace counts are outside head inventory")
            return cls(path, db, codec)
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
            raise StoreFormatError("SQLite could not provide required rollback/FULL durability mode")

    @staticmethod
    def _configure_open(db: sqlite3.Connection) -> None:
        db.execute("PRAGMA foreign_keys=ON")
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        if str(mode).lower() != "delete":
            raise StoreFormatError("save store requires rollback journal mode DELETE")
        db.execute("PRAGMA synchronous=FULL")
        sync = db.execute("PRAGMA synchronous").fetchone()[0]
        if int(sync) != 2:
            raise StoreFormatError("SQLite could not provide synchronous=FULL")

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

    @property
    def generation(self) -> int:
        self._ensure_open()
        row = self.db.execute("SELECT generation FROM save_head WHERE singleton=1").fetchone()
        if row is None:
            raise StoreIntegrityError("missing save head")
        return int(row[0])

    def head_metadata(self) -> dict[str, Any]:
        self._ensure_open()
        row = self.db.execute("SELECT simulation_position,seed,next_ids,namespace_inventory FROM save_head WHERE singleton=1").fetchone()
        if row is None:
            raise StoreIntegrityError("missing save head")
        return {
            "simulation_position": self.codec.decode(row[0]),
            "seed": row[1],
            "next_ids": self.codec.decode(row[2]),
            "namespaces": self.codec.decode(row[3]),
        }

    def diagnostics(self) -> StoreDiagnostics:
        return StoreDiagnostics(self._payload_reads, self._payload_read_bytes, self._payload_writes, self._payload_write_bytes)

    def reset_diagnostics(self) -> None:
        self._payload_reads = self._payload_read_bytes = self._payload_writes = self._payload_write_bytes = 0

    @contextmanager
    def read_transaction(self):
        """Pin one bounded-lifetime SQLite snapshot for a multi-record restore."""
        self._ensure_open()
        if self.db.in_transaction:
            raise StoreError("store already has an active transaction")
        self.db.execute("BEGIN")
        try:
            # The first read pins the snapshot in rollback-journal mode.
            generation = self.generation
            yield generation
        finally:
            if self.db.in_transaction:
                self.db.rollback()

    def _decode_checked(self, payload: bytes, checksum: str, codec_version: int, expected_checksum: str) -> Any:
        if codec_version != self.codec.version:
            raise StoreFormatError("payload codec version mismatch")
        if checksum != expected_checksum:
            raise StoreIntegrityError("payload checksum mismatch")
        self._payload_reads += 1
        self._payload_read_bytes += len(payload)
        return self.codec.decode(payload)

    def read_record(self, namespace: str, key: Any, *, expected_record_schema: int | None = None) -> Any:
        self._ensure_open(); _validate_namespace(namespace)
        typed_key = self.codec.encode(key)
        row = self.db.execute(
            "SELECT payload,payload_checksum,codec_version,record_schema,last_changed_generation FROM records WHERE namespace=? AND typed_key=?",
            (namespace, typed_key),
        ).fetchone()
        if row is None:
            raise KeyError((namespace, key))
        payload, checksum, codec_version, record_schema, generation = row
        if expected_record_schema is not None and record_schema != expected_record_schema:
            raise StoreFormatError(
                f"record schema mismatch for {(namespace, key)!r}: "
                f"expected {expected_record_schema}, found {record_schema}"
            )
        expected = _record_checksum(namespace, typed_key, record_schema, codec_version, generation, payload)
        return self._decode_checked(payload, checksum, codec_version, expected)

    def read_records(
        self, namespace: str, *, expected_record_schema: int | None = None
    ) -> tuple[tuple[Any, Any, int], ...]:
        """Return one namespace through the same checksum/schema path as point reads.

        SQL row order is intentionally not authoritative; callers that model
        ordered collections must carry and validate their own ordinals.
        """
        self._ensure_open(); _validate_namespace(namespace)
        rows = self.db.execute(
            """SELECT typed_key,payload,payload_checksum,codec_version,record_schema,last_changed_generation
               FROM records WHERE namespace=?""",
            (namespace,),
        )
        out = []
        for typed_key, payload, checksum, codec_version, record_schema, generation in rows:
            key = self.codec.decode(typed_key)
            if expected_record_schema is not None and record_schema != expected_record_schema:
                raise StoreFormatError(
                    f"record schema mismatch in {namespace!r}: "
                    f"expected {expected_record_schema}, found {record_schema}"
                )
            expected = _record_checksum(
                namespace, typed_key, record_schema, codec_version, generation, payload
            )
            value = self._decode_checked(payload, checksum, codec_version, expected)
            out.append((key, value, record_schema))
        return tuple(out)

    def read_segment_checked(self, namespace: str, ordinal: int) -> CheckedSegment:
        """Read one segment with its checksum-protected count/ID metadata."""
        self._ensure_open(); _validate_namespace(namespace)
        if type(ordinal) is not int or ordinal < 0:
            raise ValueError("segment ordinal must be a nonnegative int")
        row = self.db.execute(
            "SELECT payload,payload_checksum,codec_version,element_count,first_id,last_id,created_generation FROM segments WHERE namespace=? AND ordinal=?",
            (namespace, ordinal),
        ).fetchone()
        if row is None:
            raise KeyError((namespace, ordinal))
        payload, checksum, codec_version, element_count, first_id, last_id, generation = row
        expected = _segment_checksum(
            namespace, ordinal, first_id, last_id, element_count, codec_version, generation, payload
        )
        value = self._decode_checked(payload, checksum, codec_version, expected)
        return CheckedSegment(
            value=value,
            element_count=element_count,
            first_id=self.codec.decode(first_id),
            last_id=self.codec.decode(last_id),
            created_generation=generation,
            payload_bytes=len(payload),
        )

    def read_segment(self, namespace: str, ordinal: int) -> Any:
        return self.read_segment_checked(namespace, ordinal).value

    def commit(
        self,
        expected_generation: int,
        changes: Iterable[RecordChange],
        new_segments: Iterable[NewSegment],
        metadata: Mapping[str, Any],
    ) -> int:
        self._ensure_open()
        if self.db.in_transaction:
            raise StoreError("cannot commit within an active transaction")
        if type(expected_generation) is not int or expected_generation < 0:
            raise ValueError("expected_generation must be a nonnegative int")

        # Encode and validate caller-owned changes before opening a write transaction.
        prepared_changes = []
        seen_records = set()
        for change in tuple(changes):
            if not isinstance(change, RecordChange):
                raise TypeError("changes must contain RecordChange")
            namespace = _validate_namespace(change.namespace)
            typed_key = self.codec.encode(change.key)
            identity = (namespace, typed_key)
            if identity in seen_records:
                raise ValueError("duplicate record change")
            seen_records.add(identity)
            if type(change.record_schema) is not int or change.record_schema < 1:
                raise ValueError("record_schema must be a positive int")
            memberships = []
            seen_memberships = set()
            for membership in change.memberships:
                if not isinstance(membership, Membership):
                    raise TypeError("memberships must contain Membership")
                if not membership.index_name or "\x00" in membership.index_name:
                    raise ValueError("membership index_name must be non-empty text")
                if type(membership.ordinal) is not int or membership.ordinal < 0:
                    raise ValueError("membership ordinal must be a nonnegative int")
                encoded_value = self.codec.encode(membership.value)
                marker = (membership.index_name, encoded_value, membership.ordinal)
                if marker in seen_memberships:
                    raise ValueError("duplicate membership")
                seen_memberships.add(marker)
                memberships.append((membership.index_name, encoded_value, membership.ordinal))
            payload = None
            if not change.delete:
                payload = self.codec.encode(change.value)
            prepared_changes.append((change, namespace, typed_key, payload, memberships))

        prepared_segments = []
        seen_segments = set()
        for segment in tuple(new_segments):
            if not isinstance(segment, NewSegment):
                raise TypeError("new_segments must contain NewSegment")
            namespace = _validate_namespace(segment.namespace)
            if type(segment.ordinal) is not int or segment.ordinal < 0:
                raise ValueError("segment ordinal must be a nonnegative int")
            if type(segment.element_count) is not int or segment.element_count < 0:
                raise ValueError("element_count must be a nonnegative int")
            identity = (namespace, segment.ordinal)
            if identity in seen_segments:
                raise ValueError("duplicate new segment")
            seen_segments.add(identity)
            payload = self.codec.encode(segment.value)
            prepared_segments.append((segment, namespace, payload, self.codec.encode(segment.first_id), self.codec.encode(segment.last_id)))

        position, seed, next_ids, namespaces_blob = _head_values(self.codec, metadata)
        namespace_inventory = set(self.codec.decode(namespaces_blob))

        current_row = self.db.execute(
            "SELECT generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts FROM save_head WHERE singleton=1"
        ).fetchone()
        if current_row is None:
            raise StoreIntegrityError("missing save head")
        current_generation = int(current_row[0])
        if current_generation != expected_generation:
            raise StoreConflictError(f"expected generation {expected_generation}, found {current_generation}")
        if not prepared_changes and not prepared_segments and current_row[1:5] == (position, seed, next_ids, namespaces_blob):
            return current_generation

        new_generation = current_generation + 1
        record_writes = record_deletes = segment_writes = payload_bytes = 0
        self._phase_hook("before_transaction")
        self.db.execute("BEGIN IMMEDIATE")
        committed = False
        try:
            locked = self.db.execute(
                "SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts,head_checksum FROM save_head WHERE singleton=1"
            ).fetchone()
            if locked is None:
                raise StoreIntegrityError("missing save head")
            if _head_checksum(*locked[:-1]) != locked[-1]:
                raise StoreIntegrityError("save head checksum mismatch")
            locked_generation = int(locked[0])
            if locked_generation != expected_generation:
                raise StoreConflictError(f"expected generation {expected_generation}, found {locked_generation}")
            counts = _namespace_counts(self.codec, locked[6])
            for change, namespace, typed_key, payload, memberships in prepared_changes:
                existed = self.db.execute(
                    "SELECT 1 FROM records WHERE namespace=? AND typed_key=?",
                    (namespace, typed_key),
                ).fetchone() is not None
                if change.delete:
                    deleted = self.db.execute(
                        "DELETE FROM records WHERE namespace=? AND typed_key=?", (namespace, typed_key)
                    ).rowcount
                    if deleted:
                        record_deletes += 1
                        _bump_count(counts, namespace, records=-1)
                    continue
                checksum = _record_checksum(
                    namespace, typed_key, change.record_schema, self.codec.version, new_generation, payload
                )
                self.db.execute(
                    """INSERT INTO records(namespace,typed_key,payload,payload_checksum,codec_version,record_schema,last_changed_generation)
                       VALUES (?,?,?,?,?,?,?)
                       ON CONFLICT(namespace,typed_key) DO UPDATE SET
                         payload=excluded.payload,payload_checksum=excluded.payload_checksum,
                         codec_version=excluded.codec_version,record_schema=excluded.record_schema,
                         last_changed_generation=excluded.last_changed_generation""",
                    (namespace, typed_key, payload, checksum, self.codec.version, change.record_schema, new_generation),
                )
                if not existed:
                    _bump_count(counts, namespace, records=1)
                self.db.execute("DELETE FROM query_membership WHERE namespace=? AND record_key=?", (namespace, typed_key))
                for index_name, index_value, ordinal in memberships:
                    self.db.execute(
                        "INSERT INTO query_membership VALUES (?,?,?,?,?,?)",
                        (namespace, index_name, index_value, typed_key, ordinal, new_generation),
                    )
                record_writes += 1
                payload_bytes += len(payload)
                self._payload_writes += 1
                self._payload_write_bytes += len(payload)
            for segment, namespace, payload, first_id, last_id in prepared_segments:
                checksum = _segment_checksum(
                    namespace,
                    segment.ordinal,
                    first_id,
                    last_id,
                    segment.element_count,
                    self.codec.version,
                    new_generation,
                    payload,
                )
                try:
                    self.db.execute(
                        "INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?)",
                        (namespace, segment.ordinal, payload, checksum, self.codec.version, segment.element_count, first_id, last_id, new_generation),
                    )
                except sqlite3.IntegrityError as exc:
                    raise StoreConflictError(f"segment already exists: {(namespace, segment.ordinal)}") from exc
                _bump_count(counts, namespace, segments=1)
                segment_writes += 1
                payload_bytes += len(payload)
                self._payload_writes += 1
                self._payload_write_bytes += len(payload)
            self._phase_hook("during_writes")
            retained_namespaces = set(counts)
            missing = retained_namespaces - namespace_inventory
            if missing:
                raise ValueError(f"head namespace inventory omits retained namespace: {sorted(missing)}")
            namespace_counts_blob = _counts_blob(self.codec, counts)
            parent = current_generation
            checksum = _head_checksum(
                new_generation, parent, position, seed, next_ids, namespaces_blob, namespace_counts_blob
            )
            self.db.execute(
                """UPDATE save_head SET generation=?,parent_generation=?,simulation_position=?,seed=?,next_ids=?,namespace_inventory=?,namespace_counts=?,head_checksum=? WHERE singleton=1""",
                (new_generation, parent, position, seed, next_ids, namespaces_blob, namespace_counts_blob, checksum),
            )
            self.db.execute(
                "INSERT INTO save_receipts VALUES (?,?,?,?,?,?,?)",
                (new_generation, parent, time.time(), record_writes, record_deletes, segment_writes, payload_bytes),
            )
            self.db.execute(
                "DELETE FROM save_receipts WHERE generation NOT IN (SELECT generation FROM save_receipts ORDER BY generation DESC LIMIT ?)",
                (RECEIPT_RETENTION,),
            )
            self._phase_hook("before_commit")
            self.db.commit(); committed = True
        except Exception:
            if not committed:
                self.db.rollback()
            raise
        self._phase_hook("after_commit")
        return new_generation

    def verify_all(self) -> dict[str, int]:
        self._ensure_open()
        integrity = self.db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise StoreIntegrityError(f"SQLite integrity check failed: {integrity}")
        fk = self.db.execute("PRAGMA foreign_key_check").fetchone()
        if fk is not None:
            raise StoreIntegrityError("foreign key check failed")
        head = self.db.execute("SELECT generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts,head_checksum FROM save_head WHERE singleton=1").fetchone()
        if head is None or _head_checksum(*head[:-1]) != head[-1]:
            raise StoreIntegrityError("save head checksum mismatch")
        position = self.codec.decode(head[2]); next_ids = self.codec.decode(head[4]); namespaces = self.codec.decode(head[5])
        del position, next_ids
        if type(namespaces) is not tuple or any(type(x) is not str for x in namespaces):
            raise StoreIntegrityError("invalid namespace inventory")
        inventory = set(namespaces)
        expected_counts = _namespace_counts(self.codec, head[6])
        if not set(expected_counts).issubset(inventory):
            raise StoreIntegrityError("namespace counts are outside head inventory")
        actual_counts: dict[str, tuple[int, int]] = {}
        record_count = segment_count = 0
        for namespace, typed_key, payload, checksum, codec_version, record_schema, generation in self.db.execute(
            "SELECT namespace,typed_key,payload,payload_checksum,codec_version,record_schema,last_changed_generation FROM records"
        ):
            if namespace not in inventory:
                raise StoreIntegrityError("record namespace missing from head inventory")
            self.codec.decode(typed_key)
            expected = _record_checksum(namespace, typed_key, record_schema, codec_version, generation, payload)
            self._decode_checked(payload, checksum, codec_version, expected)
            _bump_count(actual_counts, namespace, records=1)
            record_count += 1
        for namespace, ordinal, first_id, last_id, element_count, payload, checksum, codec_version, generation in self.db.execute(
            "SELECT namespace,ordinal,first_id,last_id,element_count,payload,payload_checksum,codec_version,created_generation FROM segments"
        ):
            if namespace not in inventory:
                raise StoreIntegrityError("segment namespace missing from head inventory")
            self.codec.decode(first_id); self.codec.decode(last_id)
            expected = _segment_checksum(
                namespace, ordinal, first_id, last_id, element_count, codec_version, generation, payload
            )
            self._decode_checked(payload, checksum, codec_version, expected)
            _bump_count(actual_counts, namespace, segments=1)
            segment_count += 1
        if actual_counts != expected_counts:
            raise StoreIntegrityError("committed namespace counts do not match stored rows")
        # Membership typed values/keys must decode and already have FK-backed owners.
        for index_value, record_key in self.db.execute("SELECT index_value,record_key FROM query_membership"):
            self.codec.decode(index_value); self.codec.decode(record_key)
        return {"generation": head[0], "records": record_count, "segments": segment_count}

    def backup(self, destination: str | os.PathLike[str]) -> Path:
        self._ensure_open()
        destination = Path(destination)
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".ate-backup-", dir=destination.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        target = sqlite3.connect(tmp)
        try:
            self.db.backup(target)
            target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            target.close(); target = None
            os.link(tmp, destination)
            tmp.unlink()
            self._fsync_dir(destination.parent)
        except Exception:
            if target is not None:
                target.close()
            if tmp.exists():
                tmp.unlink()
            raise
        return destination

    def close(self) -> None:
        if not self._closed:
            self.db.close()
            self._closed = True

    def __enter__(self) -> "TransactionalStore":
        self._ensure_open(); return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def create(path: str | os.PathLike[str], **kwargs: Any) -> TransactionalStore:
    return TransactionalStore.create(path, **kwargs)


def open(path: str | os.PathLike[str], **kwargs: Any) -> TransactionalStore:
    return TransactionalStore.open(path, **kwargs)
