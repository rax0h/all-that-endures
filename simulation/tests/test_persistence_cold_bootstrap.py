import gc
import hashlib
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import weakref

import pytest

from ate_sim import Simulation, generate_world
from ate_sim.core import Event, Layer, Ref, World
from ate_sim.event_log import EventLog, FrozenDict
from ate_sim.incremental_store import (
    CodecError,
    RecordChange,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import (
    COLLECTION_LAYOUT,
    IDENTITY_DELTAS,
    META,
    RECORD_SCHEMA,
    SCHEMA,
    WorldCodec,
    _write_legacy_snapshot,
    read_snapshot,
    write_snapshot,
)
from ate_sim.persistence_events import (
    CHUNK_SIZE,
    EVENT_STORAGE,
    SEALED_EVENTS,
)
from ate_sim.persistence_session import (
    _capture_cold_world,
    convert_event_storage,
    write_cold_snapshot,
)
import ate_sim.persistence_session as persistence_session
from ate_sim.persistence_tracking import bind_snapshot


RULES = "stage-0.5-p3b-cold-bootstrap-tests"


def make_event(event_id, *, year=0, data=None):
    return Event(
        event_id,
        year,
        "bootstrap",
        Layer.REALITY,
        (Ref("person", (event_id % 7) + 1),),
        None,
        () if event_id == 1 else (event_id - 1,),
        {} if data is None else data,
    )


def segmented_world(
    segments,
    *,
    tail_count=3,
    seed=843000,
    current_alias=False,
    sealed_tail=False,
):
    world = World(seed)
    world.year = 5
    log = EventLog()
    next_id = 1
    for _segment in range(segments):
        for _ in range(CHUNK_SIZE):
            log.append(make_event(next_id))
            next_id += 1
        log.seal_before(1)
    shared = {"child": [1, 2, 3]}
    for offset in range(tail_count):
        data = (
            {"shared": shared, "typed": [True, 1, 1.0, 0.0, -0.0]}
            if current_alias and offset == 0
            else {"tail": offset}
        )
        log.append(make_event(next_id, data=data))
        next_id += 1
    if sealed_tail and tail_count >= 2:
        log._tail[1].seal()
        world.currency.wallets[2] = {
            "first": log._tail[1],
            "second": log._tail[1],
        }
    if current_alias and tail_count:
        world.currency.wallets[1] = {
            "left": shared,
            "right": shared,
        }
    world.events = log
    world.next_event = next_id
    return world


def list_world(*, count=4, seed=321):
    world = World(seed)
    world.year = 8
    shared = {"nested": [True, 1, 1.0, 0.0, -0.0]}
    events = []
    for i in range(count):
        event = Event(
            i + 1,
            3 + i // 2,
            f"list-{i}",
            Layer.KNOWLEDGE if i % 2 else Layer.REALITY,
            (Ref("person", i + 1),),
            Ref("settlement", 1) if i % 2 else None,
            () if i == 0 else (i,),
            {"shared": shared if i == count - 1 else {"i": i}},
        )
        events.append(event)
    if events:
        events[-1].seal()
    world.events = events
    world.next_event = len(events) + 1
    world.currency.wallets[1] = {"shared": shared}
    return world


def open_cold(path):
    return TransactionalStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )


def capture_cold(path):
    store = open_cold(path)
    with store.read_transaction():
        capture = _capture_cold_world(store)
    return store, capture


def event_codec(value):
    return WorldCodec(identity_links_recorded=True).encode(value)


def source_log_state(world):
    if type(world.events) is list:
        return {
            "kind": "list",
            "container": id(world.events),
            "events": tuple(id(e) for e in world.events),
            "flags": tuple(
                ("_sealed" in vars(e), vars(e).get("_sealed"))
                for e in world.events
            ),
            "values": tuple(event_codec(e) for e in world.events),
        }
    log = world.events
    return {
        "kind": "EventLog",
        "container": id(log),
        "chunks": tuple(log._chunks),
        "tail": tuple(id(e) for e in log._tail),
        "flags": tuple(
            ("_sealed" in vars(e), vars(e).get("_sealed"))
            for e in log._tail
        ),
        "years": tuple(log._years),
        "offsets": tuple(log._offsets),
        "last_year": log._last_year,
        "count": log._count,
        "cache": tuple((key, id(value)) for key, value in log._cache.items()),
    }


@pytest.mark.parametrize("shape", ["empty-list", "list-tail", "eventlog-tail"])
def test_write_cold_snapshot_basic_shapes_and_source_preservation(
    tmp_path, shape
):
    if shape == "empty-list":
        world = list_world(count=0)
    elif shape == "list-tail":
        world = list_world(count=5)
    else:
        world = segmented_world(0, tail_count=5, current_alias=True)

    before = source_log_state(world)
    destination = tmp_path / f"{shape}.sqlite"
    diagnostics = write_cold_snapshot(world, destination, rules_id=RULES)
    assert source_log_state(world) == before
    assert diagnostics["disk_segments"] == 0
    assert diagnostics["disk_events"] == 0
    assert diagnostics["event_count"] == len(world.events)
    assert diagnostics["remaining_suffix_records"] == len(world.events)
    assert diagnostics["largest_transfer_batch_chunks"] == 0

    store, capture = capture_cold(destination)
    try:
        assert capture.prefix.segment_count == 0
        assert len(capture.world.events) == len(world.events)
        for actual, expected in zip(capture.world.events, world.events):
            assert event_codec(actual) == event_codec(expected)
        if shape == "eventlog-tail":
            row = capture.world.currency.wallets[1]
            assert row["left"] is row["right"]
            assert (
                capture.world.events[0].data["shared"]
                is row["left"]
            )
    finally:
        capture.prefix.close()
        store.close()


def test_write_cold_snapshot_prefix_only_exact_partition(tmp_path):
    world = segmented_world(1, tail_count=0)
    before = source_log_state(world)
    destination = tmp_path / "prefix-only.sqlite"
    diagnostics = write_cold_snapshot(world, destination, rules_id=RULES)
    assert source_log_state(world) == before
    assert diagnostics["disk_segments"] == 1
    assert diagnostics["disk_events"] == CHUNK_SIZE
    assert diagnostics["remaining_suffix_records"] == 0
    store, capture = capture_cold(destination)
    try:
        assert len(capture.world.events) == CHUNK_SIZE
        assert capture.world.events.storage_stats()["tail_events"] == 0
        assert capture.world.events.storage_stats()["pending_sealed_events"] == 0
        assert capture.prefix.diagnostics().segment_reads == 0
        assert capture.world.events[0].id == 1
        assert capture.world.events[-1].id == CHUNK_SIZE
    finally:
        capture.prefix.close()
        store.close()


def test_write_cold_snapshot_transfers_six_chunks_and_preserves_aliases_flags_cache(
    tmp_path, monkeypatch
):
    world = segmented_world(
        6,
        tail_count=4,
        current_alias=True,
        sealed_tail=True,
    )
    warmed = world.events._chunk(0)
    assert warmed[0].id == 1
    before = source_log_state(world)
    destination = tmp_path / "six.sqlite"
    transfer_refs = []
    original_prepare = persistence_session.prepare_sealed_append

    def observe_prepare(store, events, **kwargs):
        if events:
            transfer_refs.append(weakref.ref(events[0]))
        return original_prepare(store, events, **kwargs)

    monkeypatch.setattr(
        persistence_session, "prepare_sealed_append", observe_prepare
    )
    diagnostics = write_cold_snapshot(world, destination, rules_id=RULES)
    gc.collect()
    assert transfer_refs and all(ref() is None for ref in transfer_refs)
    assert source_log_state(world) == before
    assert diagnostics["disk_segments"] == 6
    assert diagnostics["disk_events"] == 6 * CHUNK_SIZE
    assert diagnostics["transferred_events"] == 6 * CHUNK_SIZE
    assert diagnostics["deleted_event_rows"] == 6 * CHUNK_SIZE
    assert diagnostics["transfer_commits"] == 2
    assert diagnostics["largest_transfer_batch_chunks"] == 4
    assert diagnostics["remaining_suffix_records"] == 4

    store, capture = capture_cold(destination)
    try:
        assert capture.prefix.diagnostics().segment_reads == 0
        stats = capture.world.events.storage_stats()
        assert stats["disk_segments"] == 6
        assert stats["pending_sealed_segments"] == 0
        assert stats["tail_events"] == 4

        current = capture.world.currency.wallets[1]["left"]
        assert capture.world.currency.wallets[1]["right"] is current
        first_tail = 6 * CHUNK_SIZE
        assert capture.world.events[first_tail].data["shared"] is current

        # The individually sealed log occurrence is value history for identity,
        # while the two surviving non-log references still share identity.
        sealed = capture.world.currency.wallets[2]
        assert sealed["first"] is sealed["second"]
        assert sealed["first"] is not capture.world.events[first_tail + 1]
        assert event_codec(sealed["first"]) == event_codec(
            capture.world.events[first_tail + 1]
        )
        assert capture.world.events[first_tail + 1].__dict__["_sealed"] is True
    finally:
        capture.prefix.close()
        store.close()


def test_list_backed_shared_container_is_explicit_compatibility_rejection(
    tmp_path,
):
    world = list_world(count=2)
    world.currency.wallets[9] = {"same_list": world.events}
    before = source_log_state(world)
    destination = tmp_path / "reject.sqlite"
    with pytest.raises(CodecError, match="event list is legacy-only"):
        write_cold_snapshot(world, destination, rules_id=RULES)
    assert not destination.exists()
    assert source_log_state(world) == before


def test_write_cold_snapshot_rejects_bound_active_and_disk_backed_inputs(
    tmp_path,
):
    ordinary = World(77)
    source = tmp_path / "bound-source.sqlite"
    write_snapshot(ordinary, source, rules_id=RULES)
    with bind_snapshot(ordinary, source, rules_id=RULES):
        with pytest.raises(StoreError, match="unbound"):
            write_cold_snapshot(
                ordinary, tmp_path / "bound.sqlite", rules_id=RULES
            )

    active = World(78)
    active._index_current_people = True
    with pytest.raises(CodecError, match="completed simulation step"):
        write_cold_snapshot(
            active, tmp_path / "active.sqlite", rules_id=RULES
        )

    base = segmented_world(1, tail_count=1)
    cold = tmp_path / "base-cold.sqlite"
    write_cold_snapshot(base, cold, rules_id=RULES)
    store, capture = capture_cold(cold)
    try:
        with pytest.raises(CodecError, match="disk-backed"):
            write_cold_snapshot(
                capture.world,
                tmp_path / "cold-again.sqlite",
                rules_id=RULES,
            )
    finally:
        capture.prefix.close()
        store.close()


def test_write_cold_snapshot_rejects_invalid_exact_event_metadata(tmp_path):
    cases = []
    wrong_id = list_world(count=2)
    object.__setattr__(wrong_id.events[1], "id", True)
    cases.append(wrong_id)

    wrong_year = list_world(count=2)
    object.__setattr__(wrong_year.events[1], "year", 4.0)
    cases.append(wrong_year)

    wrong_next = list_world(count=2)
    wrong_next.next_event = True
    cases.append(wrong_next)

    backwards = list_world(count=2)
    object.__setattr__(backwards.events[1], "year", 1)
    cases.append(backwards)

    for i, world in enumerate(cases):
        with pytest.raises(CodecError):
            write_cold_snapshot(
                world, tmp_path / f"bad-{i}.sqlite", rules_id=RULES
            )


def test_convert_current_p2c_preserves_source_bytes_and_exact_state(tmp_path):
    world = segmented_world(1, tail_count=3, current_alias=True)
    source = tmp_path / "current.sqlite"
    destination = tmp_path / "current-cold.sqlite"
    write_snapshot(world, source, rules_id=RULES)
    before = source.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()

    diagnostics = convert_event_storage(
        source, destination, rules_id=RULES
    )
    assert diagnostics["source_format"] == "p2-record-snapshot"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before_hash
    assert source.read_bytes() == before

    p2 = read_snapshot(source, rules_id=RULES)
    store, capture = capture_cold(destination)
    try:
        assert p2.digest() == capture.world.digest()
        assert (
            capture.world.currency.wallets[1]["left"]
            is capture.world.currency.wallets[1]["right"]
        )
    finally:
        capture.prefix.close()
        store.close()


def test_convert_genuine_legacy_p2a_without_deltas(tmp_path):
    world = list_world(count=3, seed=901)
    source = tmp_path / "legacy-p2a.sqlite"
    destination = tmp_path / "legacy-p2a-cold.sqlite"
    _write_legacy_snapshot(world, source, rules_id=RULES)
    before = source.read_bytes()
    convert_event_storage(source, destination, rules_id=RULES)
    assert source.read_bytes() == before
    original = read_snapshot(source, rules_id=RULES)
    store, capture = capture_cold(destination)
    try:
        assert original.digest() == capture.world.digest()
        assert capture.prefix.segment_count == 0
    finally:
        capture.prefix.close()
        store.close()


def test_convert_genuine_legacy_p2b_with_deltas_and_layout_overlay(tmp_path):
    world = World(902)
    world.currency.wallets = {1: {"a": {"value": 1}}}
    source = tmp_path / "legacy.sqlite"
    _write_legacy_snapshot(world, source, rules_id=RULES)

    with bind_snapshot(world, source, rules_id=RULES) as session:
        for i in range(13):
            row = world.currency.wallets[1]
            if i % 2 == 0:
                row["b"] = row["a"]
            else:
                del row["b"]
            row["a"]["value"] = i
            if i == 0:
                world.currency.wallets[2] = {"iron": 2}
            session.save()
        assert len(session.store.read_records(IDENTITY_DELTAS)) == 13
        assert session.store.read_record(META, COLLECTION_LAYOUT)

    before = source.read_bytes()
    destination = tmp_path / "legacy-cold.sqlite"
    convert_event_storage(source, destination, rules_id=RULES)
    assert source.read_bytes() == before

    legacy = read_snapshot(source, rules_id=RULES)
    store, capture = capture_cold(destination)
    try:
        assert legacy.digest() == capture.world.digest()
        assert capture.world.currency.wallets[1]["a"] is (
            capture.world.currency.wallets[1]["b"]
        )
        assert capture.world.currency.wallets[2] == {"iron": 2}
    finally:
        capture.prefix.close()
        store.close()


def test_conversion_compatibility_path_and_source_failures(tmp_path):
    source = tmp_path / "source.sqlite"
    write_snapshot(World(100), source, rules_id=RULES)

    with pytest.raises(ValueError, match="different paths"):
        convert_event_storage(source, source, rules_id=RULES)

    alias = tmp_path / "source-alias.sqlite"
    os.link(source, alias)
    with pytest.raises(ValueError, match="same file"):
        convert_event_storage(source, alias, rules_id=RULES)

    dangling = tmp_path / "dangling.sqlite"
    dangling.symlink_to(tmp_path / "missing-target.sqlite")
    with pytest.raises(FileExistsError):
        convert_event_storage(
            source, dangling, rules_id=RULES
        )
    assert dangling.is_symlink()

    existing = tmp_path / "existing.sqlite"
    existing.write_text("keep")
    with pytest.raises(FileExistsError):
        convert_event_storage(
            source, existing, rules_id=RULES
        )
    assert existing.read_text() == "keep"

    with pytest.raises(StoreFormatError):
        convert_event_storage(
            source,
            tmp_path / "wrong-rules.sqlite",
            rules_id="wrong-rules",
        )

    # Malformed checked source remains rejected through the accepted reader.
    malformed = tmp_path / "malformed.sqlite"
    write_snapshot(World(101), malformed, rules_id=RULES)
    store = TransactionalStore.open(
        malformed,
        codec=WorldCodec(),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )
    store.db.execute(
        "UPDATE records SET payload_checksum='bad' "
        "WHERE namespace='world.next_person'"
    )
    store.db.commit()
    store.close()
    with pytest.raises(StoreIntegrityError):
        convert_event_storage(
            malformed,
            tmp_path / "malformed-dest.sqlite",
            rules_id=RULES,
        )

    cold_source = tmp_path / "already-cold.sqlite"
    write_cold_snapshot(World(102), cold_source, rules_id=RULES)
    with pytest.raises(StoreFormatError, match="already cold"):
        convert_event_storage(
            cold_source,
            tmp_path / "cold-copy.sqlite",
            rules_id=RULES,
        )


@pytest.mark.parametrize(
    "phase,should_exist",
    [
        ("after_staging", False),
        ("before_transfer_commit", False),
        ("after_transfer_commit", False),
        ("before_final_commit", False),
        ("after_final_commit", False),
        ("before_validation", False),
        ("before_publication", False),
        ("after_publication_link", True),
    ],
)
def test_bootstrap_failure_boundaries_are_absent_or_complete(
    tmp_path, monkeypatch, phase, should_exist
):
    world = segmented_world(1, tail_count=2, current_alias=True)
    before = source_log_state(world)
    destination = tmp_path / f"fail-{phase}.sqlite"
    original = persistence_session._bootstrap_phase

    def fail(current):
        if current == phase:
            raise OSError(f"injected {phase}")
        return original(current)

    monkeypatch.setattr(persistence_session, "_bootstrap_phase", fail)
    with pytest.raises(OSError, match="injected"):
        write_cold_snapshot(world, destination, rules_id=RULES)
    assert source_log_state(world) == before
    assert destination.exists() is should_exist

    monkeypatch.setattr(persistence_session, "_bootstrap_phase", original)
    if should_exist:
        store, capture = capture_cold(destination)
        try:
            store.verify_all()
            capture.prefix.verify_full()
        finally:
            capture.prefix.close()
            store.close()
        with pytest.raises(FileExistsError):
            write_cold_snapshot(world, destination, rules_id=RULES)


def test_destination_created_after_preflight_is_never_overwritten(
    tmp_path, monkeypatch
):
    world = World(333)
    destination = tmp_path / "race.sqlite"
    original = persistence_session._publish_private_cold_file

    def race(private, target):
        target.write_text("competitor")
        return original(private, target)

    monkeypatch.setattr(
        persistence_session, "_publish_private_cold_file", race
    )
    with pytest.raises(FileExistsError):
        write_cold_snapshot(world, destination, rules_id=RULES)
    assert destination.read_text() == "competitor"


def test_publication_fsync_failure_leaves_complete_destination(
    tmp_path, monkeypatch
):
    world = segmented_world(1, tail_count=1)
    destination = tmp_path / "fsync-uncertain.sqlite"

    def fail_fsync(_path):
        raise OSError("injected publication fsync failure")

    monkeypatch.setattr(
        persistence_session, "_fsync_publication_dir", fail_fsync
    )
    with pytest.raises(OSError, match="fsync"):
        write_cold_snapshot(world, destination, rules_id=RULES)
    assert destination.exists()

    store, capture = capture_cold(destination)
    try:
        store.verify_all()
        capture.prefix.verify_full()
    finally:
        capture.prefix.close()
        store.close()

    with pytest.raises(FileExistsError):
        write_cold_snapshot(world, destination, rules_id=RULES)


def _death_script():
    return r"""
import os, signal, sys
import ate_sim.persistence_session as ps
from ate_sim.core import World
destination, rules, phase = sys.argv[1:4]
def kill(current):
    if current == phase:
        os.kill(os.getpid(), signal.SIGKILL)
ps._bootstrap_phase = kill
ps.write_cold_snapshot(World(771), destination, rules_id=rules)
"""


@pytest.mark.parametrize(
    "phase,should_exist",
    [("before_publication", False), ("after_publication_link", True)],
)
def test_subprocess_death_leaves_absent_or_complete_publication(
    tmp_path, phase, should_exist
):
    destination = tmp_path / f"death-{phase}.sqlite"
    env = dict(os.environ)
    root = Path(__file__).parents[2]
    env["PYTHONPATH"] = (
        str(root) + os.pathsep + str(root / "simulation")
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _death_script(),
            str(destination),
            RULES,
            phase,
        ],
        env=env,
    )
    assert proc.returncode != 0
    assert destination.exists() is should_exist
    if should_exist:
        store, capture = capture_cold(destination)
        try:
            store.verify_all()
            capture.prefix.verify_full()
        finally:
            capture.prefix.close()
            store.close()


def test_independent_unbound_continuation_matches_for_ten_years(tmp_path):
    seed = 99001
    source = Simulation(generate_world(seed, mature=False)).run(2)
    control = Simulation(generate_world(seed, mature=False)).run(2)
    assert source.digest() == control.digest()

    source_shared = {"value": 7}
    control_shared = {"value": 7}
    source.currency.wallets[-700] = {
        "a": source_shared, "b": source_shared
    }
    control.currency.wallets[-700] = {
        "a": control_shared, "b": control_shared
    }
    assert source.digest() == control.digest()

    destination = tmp_path / "continuation.sqlite"
    write_cold_snapshot(source, destination, rules_id=RULES)
    store, capture = capture_cold(destination)
    try:
        assert capture.world.digest() == control.digest()
        assert capture.world.currency.wallets[-700]["a"] is (
            capture.world.currency.wallets[-700]["b"]
        )
        Simulation(control).run(10)
        Simulation(capture.world).run(10)
        assert capture.world.digest() == control.digest()
        assert capture.world.next_event == control.next_event
        assert len(capture.world.events) == len(control.events)
        codec = WorldCodec(identity_links_recorded=True)
        for left, right in zip(capture.world.events, control.events):
            assert codec.encode(left) == codec.encode(right)
    finally:
        capture.prefix.close()
        store.close()


def test_bootstrap_transfer_read_and_retention_bounds(tmp_path):
    measurements = []
    for segments in (4, 40, 400):
        world = segmented_world(
            segments,
            tail_count=3,
            seed=7000,
            current_alias=True,
        )
        assert world.events.storage_stats()["pending_cache_segments"] == 0
        source_cache = tuple(world.events._cache)
        source_compressed = sum(len(chunk) for chunk in world.events._chunks)
        gc.collect()

        destination = tmp_path / f"scale-{segments}.sqlite"
        diagnostics = write_cold_snapshot(
            world, destination, rules_id=RULES
        )
        assert tuple(world.events._cache) == source_cache

        expected_events = segments * CHUNK_SIZE
        assert diagnostics["disk_segments"] == segments
        assert diagnostics["disk_events"] == expected_events
        assert diagnostics["transferred_events"] == expected_events
        assert diagnostics["deleted_event_rows"] == expected_events
        assert diagnostics["transfer_commits"] == math.ceil(segments / 4)
        assert diagnostics["largest_transfer_batch_chunks"] <= 4
        assert diagnostics["remaining_suffix_records"] == 3
        assert diagnostics["transfer_io"]["payload_writes"] == (
            segments + math.ceil(segments / 4)
        )

        store, capture = capture_cold(destination)
        try:
            reopen_reads = capture.prefix.diagnostics().segment_reads
            assert reopen_reads == 0
            stats = capture.world.events.storage_stats()
            assert stats["disk_segments"] == segments
            assert stats["pending_sealed_segments"] == 0
            assert stats["pending_cache_segments"] == 0
            assert stats["tail_events"] == 3
            assert len(capture.world.events._years) == 1
            assert len(capture.world.events._offsets) == 1

            keys = [
                key
                for key, _value, _schema in store.read_records(
                    "world.events", expected_record_schema=RECORD_SCHEMA
                )
            ]
            assert sorted(keys) == list(
                range(expected_events, expected_events + 3)
            )
            transfer_receipts = store.db.execute(
                "SELECT COALESCE(SUM(record_deletes),0),"
                "COALESCE(SUM(segment_writes),0) FROM save_receipts "
                "WHERE generation>=2 AND generation<?",
                (diagnostics["final_generation"],),
            ).fetchone()
            assert transfer_receipts[0] == expected_events
            assert transfer_receipts[1] == segments
        finally:
            capture.prefix.close()
            store.close()

        row = {
            "segments": segments,
            "source_compressed_bytes": source_compressed,
            "staging_writes": diagnostics["staging_io"]["payload_writes"],
            "staging_bytes": diagnostics["staging_io"]["payload_write_bytes"],
            "staging_fixed_overhead": (
                diagnostics["staging_io"]["payload_writes"]
                - diagnostics["event_count"]
            ),
            "transfer_reads": diagnostics["transfer_io"]["payload_reads"],
            "transfer_writes": diagnostics["transfer_io"]["payload_writes"],
            "transfer_bytes": diagnostics["transfer_io"]["payload_write_bytes"],
            "validation_reads": diagnostics["validation_io"]["payload_reads"],
            "validation_bytes": diagnostics["validation_io"]["payload_read_bytes"],
            "final_file_bytes": diagnostics["final_file_bytes"],
            "transfer_commits": diagnostics["transfer_commits"],
            "largest_batch": diagnostics["largest_transfer_batch_chunks"],
            "reopen_segment_reads": reopen_reads,
            "tail_events": 3,
            "pending_cache": 0,
        }
        measurements.append(row)
        print(
            "P3B_COLD_BOOTSTRAP_BOUNDS "
            + " ".join(f"{key}={value}" for key, value in row.items())
        )
        del capture, store, world
        gc.collect()

    assert [m["segments"] for m in measurements] == [4, 40, 400]
    assert len({m["staging_fixed_overhead"] for m in measurements}) == 1
    assert len({m["largest_batch"] for m in measurements}) == 1
    assert {m["largest_batch"] for m in measurements} == {4}
    assert all(m["reopen_segment_reads"] == 0 for m in measurements)
    assert all(m["pending_cache"] == 0 for m in measurements)
    assert all(m["tail_events"] == 3 for m in measurements)

    # Tenfold history growth from 40 -> 400 must stay within a small constant
    # factor of ten for every history-sensitive checked-I/O/file metric.
    forty, four_hundred = measurements[1], measurements[2]
    for key in (
        "staging_writes",
        "staging_bytes",
        "transfer_writes",
        "transfer_bytes",
        "validation_reads",
        "validation_bytes",
        "final_file_bytes",
    ):
        assert four_hundred[key] <= forty[key] * 12, (
            key, measurements
        )
