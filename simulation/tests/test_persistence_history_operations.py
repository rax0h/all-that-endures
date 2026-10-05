import sqlite3
import tracemalloc

import pytest

from ate_sim.core import World
from ate_sim.history_archive import HistoryArchive, export_archive
from ate_sim.incremental_store import StoreError, StoreIntegrityError
from ate_sim.persistence_events import SEALED_EVENTS
from ate_sim.persistence_session import open_world_session
import ate_sim.history_archive as history_archive

from simulation.tests.test_persistence_session_open import (
    RULES,
    build_cold_path,
)


def test_verify_history_rereads_warm_prefix_and_reports_suffix(tmp_path):
    path, expected = build_cold_path(
        tmp_path, disk_segments=3, pending_chunks=1, tail_count=3
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        assert log[0].id == 1
        assert log._disk_prefix.resident_segments == 1

        result = session.verify_history()
        assert result["captured_generation"] == session.generation
        assert result["disk_events"] == expected["D"]
        assert result["disk_segments"] == 3
        assert result["pending_sealed_events"] == (
            expected["F"] - expected["D"]
        )
        assert result["tail_events"] == expected["N"] - expected["F"]
        assert result["checked_segment_reads"] == 3
        assert result["checked_segment_read_bytes"] > 0
        assert result["inspected_suffix_events"] == (
            expected["N"] - expected["D"]
        )
        assert log._disk_prefix.resident_segments <= 4
    finally:
        session.close()


def test_verify_history_warm_cache_cannot_hide_segment_corruption(tmp_path):
    path, _ = build_cold_path(
        tmp_path, disk_segments=2, pending_chunks=0, tail_count=1
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        assert log[0].id == 1
        assert log._disk_prefix.resident_segments == 1
        session.store.db.execute(
            "UPDATE segments SET payload=? WHERE namespace=? AND ordinal=?",
            (b"corrupt", SEALED_EVENTS, 0),
        )
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            session.verify_history()
        assert session.cold_state == "active"
    finally:
        session.close()


def test_cold_digest_and_archive_match_explicit_detached_world(tmp_path):
    path, _ = build_cold_path(
        tmp_path, disk_segments=2, pending_chunks=1, tail_count=3
    )
    session = open_world_session(path, rules_id=RULES)
    cold_archive = tmp_path / "cold-history.sqlite"
    detached_archive = tmp_path / "detached-history.sqlite"

    cold_digest = session.world.digest()
    cold_result = export_archive(session.world, cold_archive)
    world = session.detach(materialize_history=True)
    detached_digest = world.digest()
    detached_result = export_archive(world, detached_archive)

    assert cold_digest == detached_digest
    assert cold_result["logical_sha256"] == detached_result["logical_sha256"]
    with HistoryArchive(cold_archive) as left, HistoryArchive(
        detached_archive
    ) as right:
        assert left.metadata()["world_digest"] == cold_digest
        assert right.metadata()["world_digest"] == detached_digest
        assert left.metadata()["world_digest"] == right.metadata()["world_digest"]


def test_archive_guard_blocks_callback_mutation_and_releases(tmp_path, monkeypatch):
    path, _ = build_cold_path(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=2,
        wallets={1: {"values": [1]}},
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        alias = session.world.currency.wallets[1]["values"]
        original = history_archive.encode
        attempted = {"value": False}

        def guarded_encode(value):
            if not attempted["value"]:
                attempted["value"] = True
                with pytest.raises(StoreError):
                    alias.append(2)
            return original(value)

        monkeypatch.setattr(history_archive, "encode", guarded_encode)
        target = tmp_path / "guarded-archive.sqlite"
        export_archive(session.world, target)
        assert target.exists()
        assert alias == [1]

        alias.append(2)
        assert alias == [1, 2]
    finally:
        session.close()


def test_supplied_archive_digest_does_not_bypass_closed_preflight(
    tmp_path,
):
    path, _ = build_cold_path(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    session = open_world_session(path, rules_id=RULES)
    world = session.world
    session.close()

    target = tmp_path / "closed-archive.sqlite"
    with pytest.raises(StoreError):
        export_archive(world, target, digest="caller-supplied")
    assert not target.exists()


@pytest.mark.parametrize("segments", [4, 40, 400])
def test_streaming_history_bounds_and_detach_cost_are_measured(
    tmp_path, segments
):
    path, expected = build_cold_path(
        tmp_path / f"history-{segments}",
        disk_segments=segments,
        pending_chunks=1,
        tail_count=2,
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        prefix = log._disk_prefix

        tracemalloc.start()
        tracemalloc.reset_peak()
        verify_base = tracemalloc.get_traced_memory()[0]
        verified = session.verify_history()
        verify_current, verify_peak_abs = tracemalloc.get_traced_memory()
        verify_peak = max(0, verify_peak_abs - verify_base)
        verify_retained = max(0, verify_current - verify_base)
        tracemalloc.stop()
        assert verified["checked_segment_reads"] == segments
        assert prefix.resident_segments <= 4

        prefix.reset_diagnostics()
        tracemalloc.start()
        tracemalloc.reset_peak()
        digest_base = tracemalloc.get_traced_memory()[0]
        digest = session.world.digest()
        digest_current, digest_peak_abs = tracemalloc.get_traced_memory()
        digest_peak = max(0, digest_peak_abs - digest_base)
        digest_retained = max(0, digest_current - digest_base)
        tracemalloc.stop()
        digest_reads = prefix.diagnostics().segment_reads
        assert digest_reads == segments
        assert prefix.resident_segments <= 4

        archive_path = tmp_path / f"stream-{segments}.sqlite"
        prefix.reset_diagnostics()
        tracemalloc.start()
        tracemalloc.reset_peak()
        archive_base = tracemalloc.get_traced_memory()[0]
        archived = export_archive(
            session.world, archive_path, digest=digest
        )
        archive_current, archive_peak_abs = tracemalloc.get_traced_memory()
        archive_peak = max(0, archive_peak_abs - archive_base)
        archive_retained = max(0, archive_current - archive_base)
        tracemalloc.stop()
        archive_reads = prefix.diagnostics().segment_reads
        # Archive makes two streaming event passes: nodes then causal edges.
        assert archive_reads == segments * 2
        assert prefix.resident_segments <= 4

        tracemalloc.start()
        tracemalloc.reset_peak()
        detach_base = tracemalloc.get_traced_memory()[0]
        world = session.detach(materialize_history=True)
        detach_current, detach_peak_abs = tracemalloc.get_traced_memory()
        detach_peak = max(0, detach_peak_abs - detach_base)
        detach_retained = max(0, detach_current - detach_base)
        tracemalloc.stop()

        compressed_bytes = sum(len(chunk) for chunk in world.events._chunks)
        assert world.events._disk_prefix is None
        assert world.events.pending_sealed_event_count == expected["F"]
        assert archived["archive_bytes"] > 0
        print(
            "P3B_LIFECYCLE_BOUNDS "
            f"segments={segments} "
            f"verify_reads={verified['checked_segment_reads']} "
            f"verify_bytes={verified['checked_segment_read_bytes']} "
            f"verify_peak={verify_peak} "
            f"verify_retained={verify_retained} "
            f"digest_reads={digest_reads} "
            f"digest_peak={digest_peak} "
            f"digest_retained={digest_retained} "
            f"archive_reads={archive_reads} "
            f"archive_peak={archive_peak} "
            f"archive_retained={archive_retained} "
            f"detach_compressed_bytes={compressed_bytes} "
            f"detach_peak={detach_peak} "
            f"detach_retained={detach_retained}"
        )
    finally:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        session.close()
