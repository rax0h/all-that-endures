import enum
import os
import sqlite3
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from simulation.ate_sim.incremental_store import (
    CodecError,
    Membership,
    NewSegment,
    RecordChange,
    StoreConflictError,
    StoreFormatError,
    StoreIntegrityError,
    TypedCodec,
    create,
    open as open_store,
)


class Mood(enum.Enum):
    CALM = "calm"
    ALERT = "alert"


@dataclass
class Sample:
    name: str
    values: tuple


def codec():
    c = TypedCodec()
    c.register_enum("test.Mood", Mood)
    c.register_record("test.Sample", Sample)
    return c


def metadata(position=0, seed=7, namespaces=("people", "events"), next_ids=None):
    return {
        "simulation_position": position,
        "seed": seed,
        "next_ids": {"person": 2, "event": 1} if next_ids is None else next_ids,
        "namespaces": namespaces,
    }


def make_store(path):
    return create(path, simulation_schema="8", rules_id="stage-0.5", codec=codec(), metadata=metadata())


def float_bits(value):
    return struct.pack(">d", value)


def test_typed_codec_round_trip_preserves_types_order_keys_enum_record_and_float_bits():
    c = codec()
    negative_zero = -0.0
    weird_nan = struct.unpack(">d", bytes.fromhex("7ff8000000000042"))[0]
    value = {
        4: "typed-int-key",
        "ordered": [1, (2, 3), {5, 4}, frozenset({"b", "a"})],
        ("pair", 1): {True: b"bytes", None: Mood.ALERT},
        "record": Sample("x", (negative_zero, weird_nan)),
    }
    restored = c.decode(c.encode(value))
    assert list(restored) == list(value)
    assert restored[4] == "typed-int-key"
    assert isinstance(restored["ordered"], list)
    assert isinstance(restored["ordered"][1], tuple)
    assert isinstance(restored["ordered"][2], set)
    assert isinstance(restored["ordered"][3], frozenset)
    assert restored[("pair", 1)][None] is Mood.ALERT
    assert restored["record"].name == "x"
    assert float_bits(restored["record"].values[0]) == float_bits(negative_zero)
    assert float_bits(restored["record"].values[1]) == float_bits(weird_nan)


def test_codec_rejects_unregistered_unsupported_cycles_and_shared_mutable_identity():
    c = TypedCodec()
    with pytest.raises(CodecError): c.encode(Sample("x", ()))
    with pytest.raises(CodecError): c.encode(object())
    cyclic = []; cyclic.append(cyclic)
    with pytest.raises(CodecError, match="cycles"): c.encode(cyclic)
    shared = []
    with pytest.raises(CodecError, match="shared mutable"): c.encode([shared, shared])
    # Arbitrary type names in stored bytes are never imported.
    bad = b'["record","os.system",[]]'
    with pytest.raises(CodecError, match="unregistered record"): c.decode(bad)


def test_record_segment_commit_read_delete_membership_and_diagnostics(tmp_path):
    path = tmp_path / "save.sqlite"
    with make_store(path) as store:
        g = store.commit(
            0,
            [RecordChange("people", 1, Sample("Ada", (1, 2)), memberships=(Membership("alive", True),))],
            [NewSegment("events", 0, ("e1", "e2"), 2, 1, 2)],
            metadata(10),
        )
        assert g == 1
        assert store.read_record("people", 1) == Sample("Ada", (1, 2))
        assert store.read_segment("events", 0) == ("e1", "e2")
        d = store.diagnostics()
        assert d.payload_writes == 2 and d.payload_write_bytes > 0
        assert d.payload_reads == 2 and d.payload_read_bytes > 0
        row = store.db.execute("SELECT generation FROM query_membership WHERE namespace='people'").fetchone()
        assert row == (1,)
        g = store.commit(1, [RecordChange("people", 1, delete=True)], [], metadata(11))
        assert g == 2
        with pytest.raises(KeyError): store.read_record("people", 1)
        assert store.db.execute("SELECT COUNT(*) FROM query_membership").fetchone()[0] == 0


def test_noop_commit_does_not_advance_or_write(tmp_path):
    with make_store(tmp_path / "save") as store:
        store.reset_diagnostics()
        assert store.commit(0, [], [], metadata()) == 0
        assert store.generation == 0
        assert store.diagnostics().payload_writes == 0
        assert store.db.execute("SELECT COUNT(*) FROM save_receipts").fetchone()[0] == 0


def test_stale_generation_and_immutable_segment_are_rejected_atomically(tmp_path):
    path = tmp_path / "save"
    with make_store(path) as first, open_store(path, codec=codec(), expected_simulation_schema="8", expected_rules_id="stage-0.5") as second:
        assert first.commit(0, [RecordChange("people", 1, "a")], [NewSegment("events", 0, [1], 1, 1, 1)], metadata(1)) == 1
        with pytest.raises(StoreConflictError): second.commit(0, [RecordChange("people", 2, "b")], [], metadata(2))
        # Refreshing generation cannot overwrite an immutable segment ordinal.
        with pytest.raises(StoreConflictError): first.commit(1, [], [NewSegment("events", 0, [2], 1, 2, 2)], metadata(2))
        assert first.generation == 1
        assert first.read_segment("events", 0) == [1]


def test_failed_encoding_and_injected_write_error_leave_old_head_and_retry_clean(tmp_path):
    path = tmp_path / "save"
    with make_store(path) as store:
        with pytest.raises(CodecError):
            store.commit(0, [RecordChange("people", 1, object())], [], metadata(1))
        assert store.generation == 0
        change = RecordChange("people", 1, {"wallet": 4})
        segment = NewSegment("events", 0, ["event"], 1, 1, 1)
        store._phase_hook = lambda phase: (_ for _ in ()).throw(OSError("disk full")) if phase == "before_commit" else None
        with pytest.raises(OSError, match="disk full"):
            store.commit(0, [change], [segment], metadata(1))
        store._phase_hook = lambda phase: None
        assert store.generation == 0
        with pytest.raises(KeyError): store.read_record("people", 1)
        assert store.commit(0, [change], [segment], metadata(1)) == 1
        assert store.read_record("people", 1) == {"wallet": 4}
        assert store.read_segment("events", 0) == ["event"]


def _crash_script():
    return r'''
import os, signal, sys
from simulation.ate_sim.incremental_store import TypedCodec, RecordChange, NewSegment, open
path, phase = sys.argv[1], sys.argv[2]
s = open(path, codec=TypedCodec(), expected_simulation_schema="8", expected_rules_id="stage-0.5")
s._phase_hook = lambda p: os.kill(os.getpid(), signal.SIGKILL) if p == phase else None
s.commit(0, [RecordChange("people", 1, {"value": 9})], [NewSegment("events", 0, [1], 1, 1, 1)], {"simulation_position":1,"seed":7,"next_ids":{},"namespaces":("people","events")})
'''


@pytest.mark.parametrize("phase,expected_generation", [
    ("before_transaction", 0),
    ("during_writes", 0),
    ("after_commit", 1),
])
def test_process_kill_recovers_old_or_new_generation_never_mixed(tmp_path, phase, expected_generation):
    path = tmp_path / "save"
    s = create(path, simulation_schema="8", rules_id="stage-0.5", metadata={"simulation_position":0,"seed":7,"next_ids":{},"namespaces":("people","events")})
    s.close()
    env = dict(os.environ)
    root = Path(__file__).parents[2]
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run([sys.executable, "-c", _crash_script(), str(path), phase], env=env)
    assert p.returncode != 0
    with open_store(path, expected_simulation_schema="8", expected_rules_id="stage-0.5") as recovered:
        assert recovered.generation == expected_generation
        recovered.verify_all()
        if expected_generation == 0:
            with pytest.raises(KeyError): recovered.read_record("people", 1)
            with pytest.raises(KeyError): recovered.read_segment("events", 0)
        else:
            assert recovered.read_record("people", 1) == {"value": 9}
            assert recovered.read_segment("events", 0) == [1]


def test_lost_acknowledgement_is_resolved_by_committed_head(tmp_path):
    path = tmp_path / "save"
    store = create(path, simulation_schema="8", rules_id="stage-0.5", metadata={"simulation_position":0,"seed":7,"next_ids":{},"namespaces":("people",)})
    store._phase_hook = lambda phase: (_ for _ in ()).throw(OSError("ack lost")) if phase == "after_commit" else None
    with pytest.raises(OSError, match="ack lost"):
        store.commit(0, [RecordChange("people", 1, "committed")], [], {"simulation_position":1,"seed":7,"next_ids":{},"namespaces":("people",)})
    store.close()
    with open_store(path, expected_simulation_schema="8", expected_rules_id="stage-0.5") as recovered:
        assert recovered.generation == 1
        assert recovered.read_record("people", 1) == "committed"
        with pytest.raises(StoreConflictError):
            recovered.commit(0, [RecordChange("people", 1, "duplicate")], [], {"simulation_position":2,"seed":7,"next_ids":{},"namespaces":("people",)})


def test_corrupt_or_missing_payloads_fail_explicitly_and_full_verify_detects_them(tmp_path):
    path = tmp_path / "save"
    with make_store(path) as store:
        store.commit(0, [RecordChange("people", 1, {"x": 1})], [], metadata(1))
        with pytest.raises(KeyError): store.read_record("people", 999)
        store.db.execute("UPDATE records SET payload=? WHERE namespace='people'", (b'bad',)); store.db.commit()
        with pytest.raises(StoreIntegrityError): store.read_record("people", 1)
        with pytest.raises(StoreIntegrityError): store.verify_all()


def test_open_rejects_wrong_versions_schema_rules_and_durability_metadata(tmp_path):
    path = tmp_path / "save"
    s = make_store(path); s.close()
    with pytest.raises(StoreFormatError): open_store(path, codec=codec(), expected_simulation_schema="9")
    with pytest.raises(StoreFormatError): open_store(path, codec=codec(), expected_rules_id="other")
    db = sqlite3.connect(path)
    db.execute("UPDATE store_metadata SET value='999' WHERE key='format_version'"); db.commit(); db.close()
    with pytest.raises(StoreFormatError): open_store(path, codec=codec())


def test_backup_restore_and_relocation_preserve_store_without_external_paths(tmp_path):
    source = tmp_path / "a" / "save.sqlite"
    backup = tmp_path / "elsewhere" / "manual.sqlite"
    with make_store(source) as store:
        store.commit(0, [RecordChange("people", 1, "Ada")], [NewSegment("events", 0, [1, 2], 2, 1, 2)], metadata(2))
        store.backup(backup)
    source.unlink()
    with open_store(backup, codec=codec(), expected_simulation_schema="8", expected_rules_id="stage-0.5") as restored:
        assert restored.verify_all() == {"generation": 1, "records": 1, "segments": 1}
        assert restored.read_record("people", 1) == "Ada"
        assert restored.read_segment("events", 0) == [1, 2]
        metadata_rows = dict(restored.db.execute("SELECT key,value FROM store_metadata"))
        assert all(str(tmp_path) not in value for value in metadata_rows.values())


def test_head_namespace_inventory_is_complete_and_typed_keys_do_not_collide(tmp_path):
    path = tmp_path / "save"
    with make_store(path) as store:
        with pytest.raises(ValueError, match="omits"):
            store.commit(0, [RecordChange("other", 1, "x")], [], metadata(1))
        assert store.commit(0, [RecordChange("people", 1, "int"), RecordChange("people", "1", "str")], [], metadata(1)) == 1
        assert store.read_record("people", 1) == "int"
        assert store.read_record("people", "1") == "str"


def test_receipts_are_bounded_storage_metadata(tmp_path):
    path = tmp_path / "save"
    with create(path, simulation_schema="8", rules_id="stage-0.5", metadata={"simulation_position":0,"seed":1,"next_ids":{},"namespaces":("people",)}) as store:
        for i in range(70):
            store.commit(i, [RecordChange("people", 1, i)], [], {"simulation_position":i+1,"seed":1,"next_ids":{},"namespaces":("people",)})
        assert store.generation == 70
        assert store.db.execute("SELECT COUNT(*) FROM save_receipts").fetchone()[0] == 64
        assert store.db.execute("SELECT MIN(generation),MAX(generation) FROM save_receipts").fetchone() == (7, 70)


def test_open_does_not_create_missing_file_and_rejects_non_store(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError): open_store(missing)
    assert not missing.exists()
    bogus = tmp_path / "bogus"
    bogus.write_bytes(b"not sqlite")
    with pytest.raises((StoreFormatError, sqlite3.DatabaseError)):
        open_store(bogus)


def test_open_checks_head_only_while_cold_corruption_fails_on_access_or_scrub(tmp_path):
    path = tmp_path / "save"
    with make_store(path) as store:
        store.commit(0, [RecordChange("people", 1, {"x": 1})], [], metadata(1))
    db = sqlite3.connect(path)
    db.execute("UPDATE records SET payload=? WHERE namespace='people'", (b'corrupt',)); db.commit(); db.close()
    # Opening verifies bounded store/head metadata, not every cold payload.
    with open_store(path, codec=codec(), expected_simulation_schema="8", expected_rules_id="stage-0.5") as store:
        with pytest.raises(StoreIntegrityError): store.read_record("people", 1)
        with pytest.raises(StoreIntegrityError): store.verify_all()


def test_effective_sqlite_durability_settings_are_required(tmp_path):
    path = tmp_path / "save"
    with make_store(path) as store:
        assert store.db.execute("PRAGMA journal_mode").fetchone()[0].lower() == "delete"
        assert store.db.execute("PRAGMA synchronous").fetchone()[0] == 2
    with pytest.raises(ValueError):
        create(tmp_path / "wal", simulation_schema="8", rules_id="x", journal_mode="WAL")
