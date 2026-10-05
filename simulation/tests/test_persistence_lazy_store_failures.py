import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from simulation.ate_sim.incremental_store import Membership, NewSegment, RecordChange, StoreConflictError, StoreIntegrityError, TypedCodec
from simulation.ate_sim.persistence_lazy_store import (
    GenerationPin,
    GenerationPressureError,
    LazyRecordStore,
    VersionChange,
)


def codec():
    return TypedCodec()


def metadata(position=0, namespaces=("people", "ordinary", "events")):
    return {
        "simulation_position": position,
        "seed": 7,
        "next_ids": {"person": position + 2, "event": position + 3},
        "namespaces": namespaces,
    }


def make_store(path):
    return LazyRecordStore.create(path, codec=codec(), simulation_schema="8", rules_id="stage-0.5")


def open_store(path):
    return LazyRecordStore.open(
        path,
        codec=codec(),
        expected_simulation_schema="8",
        expected_rules_id="stage-0.5",
    )


def full_commit(store, pin, token, value, position):
    return store.commit(
        pin,
        commit_token=token,
        version_changes=(VersionChange("people", 1, value, memberships=(Membership("alive", True, 0),)),),
        changes=(RecordChange("ordinary", 1, {"value": value}),),
        new_segments=(NewSegment("events", position - 1, (value,), 1, position, position),),
        metadata=metadata(position),
    )


@pytest.mark.parametrize(
    "phase",
    [
        "before_transaction",
        "during_version_writes",
        "during_ordinary_writes",
        "during_segment_writes",
        "before_head",
        "before_commit",
    ],
)
def test_injected_precommit_failures_leave_single_old_generation(phase, tmp_path):
    path = tmp_path / f"{phase}.sqlite"
    with make_store(path) as store:
        pin = store.capture_pin()
        store._phase_hook = lambda p: (_ for _ in ()).throw(OSError(phase)) if p == phase else None
        with pytest.raises(OSError, match=phase):
            full_commit(store, pin, "token", 9, 1)
        store._phase_hook = lambda p: None
        assert store.generation == 0
        assert store.db.execute("SELECT COUNT(*) FROM lazy_record_versions").fetchone()[0] == 0
        assert store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
        assert store.db.execute("SELECT COUNT(*) FROM segments").fetchone()[0] == 0
        assert store.db.execute("SELECT generation FROM generation_pins WHERE token=?", (pin.token,)).fetchone() == (0,)
        assert store.resolve_commit(pin, "token").outcome == "not_committed"
        store.verify_all()


def test_after_commit_exception_requires_resolution_and_is_durable(tmp_path):
    path = tmp_path / "lost-ack.sqlite"
    store = make_store(path)
    pin = store.capture_pin()
    store._phase_hook = lambda p: (_ for _ in ()).throw(OSError("ack lost")) if p == "after_commit" else None
    with pytest.raises(OSError, match="ack lost"):
        full_commit(store, pin, "token-1", 9, 1)
    with pytest.raises(StoreConflictError, match="unresolved"):
        full_commit(store, pin, "token-2", 10, 2)
    with pytest.raises(StoreConflictError, match="unresolved"):
        store.release_pin(pin)
    store.close()

    with open_store(path) as recovered:
        result = recovered.resolve_commit(pin, "token-1")
        assert result.outcome == "committed" and result.generation == 1 and not result.stale
        assert recovered.read_version(result.pin, "people", 1, expected_record_schema=1).value == 9
        assert recovered.db.execute("SELECT payload FROM records WHERE namespace='ordinary'").fetchone() is not None
        assert recovered.db.execute("SELECT COUNT(*) FROM segments").fetchone()[0] == 1
        recovered.verify_all()


def test_lost_ack_resolves_after_one_competitor_advance_and_blocks_the_next(tmp_path):
    path = tmp_path / "lost-ack-advance.sqlite"
    first = make_store(path)
    old_pin = first.capture_pin()
    first._phase_hook = lambda p: (_ for _ in ()).throw(OSError("ack lost")) if p == "after_commit" else None
    with pytest.raises(OSError):
        first.commit(
            old_pin,
            commit_token="writer-g1",
            version_changes=(VersionChange("people", 1, 1),),
            changes=(),
            new_segments=(),
            metadata=metadata(1, ("people",)),
        )
    first.close()

    with open_store(path) as competitor:
        competitor_pin = competitor.capture_pin()
        r2 = competitor.commit(
            competitor_pin,
            commit_token="competitor-g2",
            version_changes=(VersionChange("people", 1, 2),),
            changes=(),
            new_segments=(),
            metadata=metadata(2, ("people",)),
        )
        competitor_pin = r2.pin
        assert r2.generation == 2
        with pytest.raises(GenerationPressureError):
            competitor.commit(
                competitor_pin,
                commit_token="competitor-g3-blocked",
                version_changes=(VersionChange("people", 1, 3),),
                changes=(),
                new_segments=(),
                metadata=metadata(3, ("people",)),
            )

        resolved = competitor.resolve_commit(old_pin, "writer-g1")
        assert resolved.outcome == "committed" and resolved.generation == 1 and resolved.stale
        again = competitor.resolve_commit(old_pin, "writer-g1")
        assert again == resolved
        competitor.release_pin(resolved.pin)
        r3 = competitor.commit(
            competitor_pin,
            commit_token="competitor-g3",
            version_changes=(VersionChange("people", 1, 3),),
            changes=(),
            new_segments=(),
            metadata=metadata(3, ("people",)),
        )
        assert r3.generation == 3


def test_only_latest_receipt_per_pin_is_resolvable(tmp_path):
    with make_store(tmp_path / "save.sqlite") as store:
        pin0 = store.capture_pin()
        r1 = store.commit(
            pin0,
            commit_token="one",
            version_changes=(VersionChange("people", 1, 1),),
            changes=(),
            new_segments=(),
            metadata=metadata(1, ("people",)),
        )
        assert store.resolve_commit(pin0, "one").generation == 1
        r2 = store.commit(
            r1.pin,
            commit_token="two",
            version_changes=(VersionChange("people", 1, 2),),
            changes=(),
            new_segments=(),
            metadata=metadata(2, ("people",)),
        )
        assert r2.generation == 2
        with pytest.raises(StoreConflictError, match="latest attempt"):
            store.resolve_commit(pin0, "one")
        assert store.resolve_commit(r1.pin, "two").generation == 2
        assert store.db.execute("SELECT COUNT(*) FROM pin_receipts").fetchone()[0] == 1


def test_pin_capture_capacity_and_capture_release_failures_are_atomic(tmp_path):
    path = tmp_path / "pins.sqlite"
    with make_store(path) as store:
        store._phase_hook = lambda p: (_ for _ in ()).throw(OSError("capture fail")) if p == "before_pin_capture_commit" else None
        with pytest.raises(OSError, match="capture fail"):
            store.capture_pin()
        store._phase_hook = lambda p: None
        assert store.db.execute("SELECT COUNT(*) FROM generation_pins").fetchone()[0] == 0

        pins = [store.capture_pin() for _ in range(64)]
        with pytest.raises(GenerationPressureError):
            store.capture_pin()
        assert store.db.execute("SELECT COUNT(*) FROM generation_pins").fetchone()[0] == 64

        victim = pins.pop()
        store._phase_hook = lambda p: (_ for _ in ()).throw(OSError("release fail")) if p == "before_pin_release_commit" else None
        with pytest.raises(OSError, match="release fail"):
            store.release_pin(victim)
        store._phase_hook = lambda p: None
        assert store.db.execute("SELECT COUNT(*) FROM generation_pins WHERE token=?", (victim.token,)).fetchone()[0] == 1
        store.release_pin(victim)
        store.release_pin(victim)
        assert store.db.execute("SELECT COUNT(*) FROM generation_pins").fetchone()[0] == 63
        for pin in pins:
            store.release_pin(pin)


def test_foreign_and_stale_pin_fail_without_mutation(tmp_path):
    with make_store(tmp_path / "a.sqlite") as a, make_store(tmp_path / "b.sqlite") as b:
        a_pin = a.capture_pin()
        b_pin = b.capture_pin()
        before = b.generation
        with pytest.raises(StoreConflictError, match="another store"):
            b.commit(
                a_pin,
                commit_token="foreign",
                version_changes=(VersionChange("people", 1, 1),),
                changes=(),
                new_segments=(),
                metadata=metadata(1, ("people",)),
            )
        assert b.generation == before
        with pytest.raises(StoreConflictError):
            b.resolve_commit(a_pin, "foreign")
        assert b_pin.captured_head == 0


def test_capture_racing_commit_cleanup_returns_only_valid_snapshot(tmp_path):
    path = tmp_path / "race.sqlite"
    seed = make_store(path)
    writer = seed.capture_pin()
    writer = seed.commit(
        writer,
        commit_token="g1",
        version_changes=(VersionChange("people", 1, "one"),),
        changes=(),
        new_segments=(),
        metadata=metadata(1, ("people",)),
    ).pin
    seed.close()

    barrier = threading.Barrier(2)
    captured = []
    committed = []
    errors = []

    def capture_worker():
        try:
            with open_store(path) as s:
                barrier.wait()
                captured.append(s.capture_pin())
        except Exception as exc:
            errors.append(exc)

    def commit_worker():
        try:
            with open_store(path) as s:
                barrier.wait()
                committed.append(
                    s.commit(
                        writer,
                        commit_token="g2",
                        version_changes=(VersionChange("people", 1, "two"),),
                        changes=(),
                        new_segments=(),
                        metadata=metadata(2, ("people",)),
                    )
                )
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=capture_worker)
    t2 = threading.Thread(target=commit_worker)
    t1.start(); t2.start(); t1.join(); t2.join()
    assert not errors
    assert len(captured) == len(committed) == 1
    with open_store(path) as check:
        cap = captured[0]
        value = check.read_version(cap, "people", 1, expected_record_schema=1).value
        assert (cap.captured_head, value) in ((1, "one"), (2, "two"))
        check.verify_all()
        check.release_pin(cap)
        check.release_pin(committed[0].pin)


def _crash_script():
    return r'''
import json, os, signal, sys
from simulation.ate_sim.incremental_store import NewSegment, RecordChange, TypedCodec
from simulation.ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange
path, info, phase = sys.argv[1], sys.argv[2], sys.argv[3]
s = LazyRecordStore.open(path, codec=TypedCodec(), expected_simulation_schema="8", expected_rules_id="stage-0.5")
pin = s.capture_pin()
open(info, "w").write(json.dumps({"token": pin.token, "store_identity": pin.store_identity, "head": pin.captured_head}))
s._phase_hook = lambda p: os.kill(os.getpid(), signal.SIGKILL) if p == phase else None
s.commit(pin, commit_token="crash-token", version_changes=(VersionChange("people", 1, 9),), changes=(RecordChange("ordinary", 1, 9),), new_segments=(NewSegment("events", 0, (9,), 1, 1, 1),), metadata={"simulation_position":1,"seed":7,"next_ids":{},"namespaces":("people","ordinary","events")})
'''


@pytest.mark.parametrize(
    "phase,expected_generation",
    [("before_transaction", 0), ("during_ordinary_writes", 0), ("after_commit", 1)],
)
def test_process_death_recovers_old_or_new_and_after_commit_resolves(tmp_path, phase, expected_generation):
    path = tmp_path / f"crash-{phase}.sqlite"
    info = tmp_path / f"crash-{phase}.json"
    make_store(path).close()
    env = dict(os.environ)
    root = Path(__file__).parents[2]
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run([sys.executable, "-c", _crash_script(), str(path), str(info), phase], env=env)
    assert p.returncode != 0
    payload = json.loads(info.read_text())
    old_pin = GenerationPin(payload["token"], payload["store_identity"], payload["head"])
    with open_store(path) as recovered:
        assert recovered.generation == expected_generation
        recovered.verify_all()
        if expected_generation == 0:
            assert recovered.resolve_commit(old_pin, "crash-token").outcome == "not_committed"
        else:
            resolved = recovered.resolve_commit(old_pin, "crash-token")
            assert resolved.outcome == "committed" and resolved.generation == 1
            assert recovered.read_version(resolved.pin, "people", 1, expected_record_schema=1).value == 9


def test_backup_preserves_operational_metadata_and_relocation(tmp_path):
    source = tmp_path / "source.sqlite"
    backup = tmp_path / "elsewhere" / "backup.sqlite"
    with make_store(source) as store:
        pin = store.capture_pin()
        pin = store.commit(
            pin,
            commit_token="g1",
            version_changes=(VersionChange("people", 1, "Ada"),),
            changes=(),
            new_segments=(),
            metadata=metadata(1, ("people",)),
        ).pin
        extra = store.capture_pin()
        store.backup(backup)
        source_identity = store.store_identity
        assert extra.captured_head == 1
    source.unlink()
    with open_store(backup) as relocated:
        assert relocated.store_identity == source_identity
        assert relocated.db.execute("SELECT COUNT(*) FROM generation_pins").fetchone()[0] == 2
        assert relocated.db.execute("SELECT COUNT(*) FROM pin_receipts").fetchone()[0] == 1
        relocated.verify_all()


def test_copy_current_head_clears_only_new_operational_state_and_source_is_unchanged(tmp_path):
    source = tmp_path / "source.sqlite"
    destination = tmp_path / "copy.sqlite"
    with make_store(source) as store:
        writer = store.capture_pin()
        writer = store.commit(
            writer,
            commit_token="g1",
            version_changes=(VersionChange("people", 1, "one", memberships=(Membership("bucket", "x", 0),)),),
            changes=(RecordChange("ordinary", 1, "ordinary"),),
            new_segments=(NewSegment("events", 0, (1,), 1, 1, 1),),
            metadata=metadata(1),
        ).pin
        old = store.capture_pin()
        writer = store.commit(
            writer,
            commit_token="g2",
            version_changes=(VersionChange("people", 1, "two", memberships=(Membership("bucket", "x", 0),)),),
            changes=(),
            new_segments=(),
            metadata=metadata(2),
        ).pin
        source_identity = store.store_identity
        source_versions = store.storage_metrics()["lazy_record_versions"]
        assert source_versions == 2
        with pytest.raises(GenerationPressureError):
            store.commit(
                writer,
                commit_token="g3-blocked",
                version_changes=(VersionChange("people", 1, "three"),),
                changes=(),
                new_segments=(),
                metadata=metadata(3),
            )

        copied = LazyRecordStore.copy_current_head(
            source,
            destination,
            codec=codec(),
            expected_simulation_schema="8",
            expected_rules_id="stage-0.5",
        )
        assert copied.generation == 2
        assert copied.store_identity != source_identity
        assert store.store_identity == source_identity
        assert store.storage_metrics()["lazy_record_versions"] == source_versions
        assert store.db.execute("SELECT COUNT(*) FROM generation_pins").fetchone()[0] == 2
        assert store.read_version(old, "people", 1, expected_record_schema=1).value == "one"

    with open_store(destination) as fresh:
        metrics = fresh.storage_metrics()
        assert metrics["pins"] == 0 and metrics["receipts"] == 0
        assert metrics["lazy_record_versions"] == 1
        pin = fresh.capture_pin()
        assert fresh.read_version(pin, "people", 1, expected_record_schema=1).value == "two"
        assert fresh.query_keys(pin, "people", "bucket", "x") == (1,)
        r3 = fresh.commit(
            pin,
            commit_token="g3",
            version_changes=(VersionChange("people", 1, "three"),),
            changes=(),
            new_segments=(),
            metadata=metadata(3),
        )
        assert r3.generation == 3
        fresh.verify_all()


def test_copy_current_head_no_overwrite_failure_cleanup_and_corruption_rejection(tmp_path):
    source = tmp_path / "source.sqlite"
    with make_store(source) as store:
        pin = store.capture_pin()
        pin = store.commit(
            pin,
            commit_token="g1",
            version_changes=(VersionChange("people", 1, "one"),),
            changes=(),
            new_segments=(),
            metadata=metadata(1, ("people",)),
        ).pin

    existing = tmp_path / "existing.sqlite"
    existing.write_text("keep")
    with pytest.raises(FileExistsError):
        LazyRecordStore.copy_current_head(
            source,
            existing,
            codec=codec(),
            expected_simulation_schema="8",
            expected_rules_id="stage-0.5",
        )
    assert existing.read_text() == "keep"

    failed = tmp_path / "failed.sqlite"
    LazyRecordStore._copy_phase_hook = staticmethod(
        lambda phase: (_ for _ in ()).throw(OSError("publish fail")) if phase == "before_publish" else None
    )
    try:
        with pytest.raises(OSError, match="publish fail"):
            LazyRecordStore.copy_current_head(
                source,
                failed,
                codec=codec(),
                expected_simulation_schema="8",
                expected_rules_id="stage-0.5",
            )
    finally:
        LazyRecordStore._copy_phase_hook = staticmethod(lambda phase: None)
    assert not failed.exists()
    with open_store(source) as check:
        check.verify_all()

    corrupt = tmp_path / "corrupt.sqlite"
    with open_store(source) as store:
        store.db.execute("UPDATE lazy_record_versions SET payload=?", (b"bad",))
        store.db.commit()
    with pytest.raises(StoreIntegrityError):
        LazyRecordStore.copy_current_head(
            source,
            corrupt,
            codec=codec(),
            expected_simulation_schema="8",
            expected_rules_id="stage-0.5",
        )
    assert not corrupt.exists()



def test_release_old_pin_transactionally_reclaims_then_verify_backup_copy_and_reopen(tmp_path):
    source = tmp_path / "release-source.sqlite"
    backup = tmp_path / "release-backup.sqlite"
    copied = tmp_path / "release-copy.sqlite"
    with make_store(source) as store:
        writer = store.capture_pin()
        writer = full_commit(store, writer, "g1", "one", 1).pin
        old = store.capture_pin()
        writer = full_commit(store, writer, "g2", "two", 2).pin
        assert store.storage_metrics()["lazy_record_versions"] == 2

        store.release_pin(old)
        assert store.storage_metrics()["lazy_record_versions"] == 1
        assert store.verify_all()["generation"] == 2
        store.backup(backup)
        result = LazyRecordStore.copy_current_head(
            source,
            copied,
            codec=codec(),
            expected_simulation_schema="8",
            expected_rules_id="stage-0.5",
        )
        assert result.generation == 2
        assert store.verify_all()["generation"] == 2

    with open_store(backup) as reopened:
        assert reopened.verify_all()["generation"] == 2
    with open_store(copied) as recovered:
        assert recovered.verify_all()["generation"] == 2


def test_release_cleanup_failure_rolls_back_pin_and_reclamation_and_last_pin_release_is_healthy(tmp_path):
    path = tmp_path / "release-fault.sqlite"
    with make_store(path) as store:
        writer = store.capture_pin()
        writer = full_commit(store, writer, "g1", "one", 1).pin
        old = store.capture_pin()
        writer = full_commit(store, writer, "g2", "two", 2).pin
        before = store.storage_metrics()["lazy_record_versions"]

        store._phase_hook = lambda phase: (
            (_ for _ in ()).throw(OSError("cleanup fail"))
            if phase == "during_pin_release_cleanup"
            else None
        )
        with pytest.raises(OSError, match="cleanup fail"):
            store.release_pin(old)
        store._phase_hook = lambda phase: None
        assert store.db.execute(
            "SELECT COUNT(*) FROM generation_pins WHERE token=?", (old.token,)
        ).fetchone() == (1,)
        assert store.storage_metrics()["lazy_record_versions"] == before
        store.verify_all()

        store.release_pin(old)
        store.verify_all()
        store.release_pin(writer)
        assert store.verify_all()["pins"] == 0
        assert store.storage_metrics()["lazy_record_versions"] == 1


def test_corrupt_operational_metadata_cannot_drive_release_reclamation(tmp_path):
    path = tmp_path / "corrupt-pin.sqlite"
    with make_store(path) as store:
        writer = store.capture_pin()
        writer = full_commit(store, writer, "g1", "one", 1).pin
        old = store.capture_pin()
        writer = full_commit(store, writer, "g2", "two", 2).pin
        before = store.storage_metrics()["lazy_record_versions"]
        store.db.execute(
            "UPDATE generation_pins SET row_checksum='bad' WHERE token=?", (writer.token,)
        )
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match="pin checksum"):
            store.release_pin(old)
        assert store.storage_metrics()["lazy_record_versions"] == before
        assert store.db.execute(
            "SELECT COUNT(*) FROM generation_pins WHERE token=?", (old.token,)
        ).fetchone() == (1,)


def test_failed_later_attempt_resolves_against_attempt_not_older_receipt_and_can_retry(tmp_path):
    path = tmp_path / "attempt-after-success.sqlite"
    with make_store(path) as store:
        pin0 = store.capture_pin()
        first = full_commit(store, pin0, "old-success", "one", 1)
        pin = first.pin

        store._phase_hook = lambda phase: (
            (_ for _ in ()).throw(OSError("new failed"))
            if phase == "before_commit"
            else None
        )
        with pytest.raises(OSError, match="new failed"):
            full_commit(store, pin, "new-attempt", "two", 2)
        store._phase_hook = lambda phase: None

        result = store.resolve_commit(pin, "new-attempt")
        assert result.outcome == "not_committed"
        assert result.generation == 1
        assert store.resolve_commit(pin, "new-attempt") == result
        with pytest.raises(StoreConflictError, match="latest attempt"):
            store.resolve_commit(pin0, "old-success")
        with pytest.raises(StoreConflictError, match="latest attempt"):
            store.resolve_commit(pin, "unknown")

        later = full_commit(store, pin, "later-success", "three", 3)
        assert later.outcome == "committed"
        assert later.generation == 2
        assert store.read_version(
            later.pin, "people", 1, expected_record_schema=1
        ).value == "three"


def test_failed_attempt_then_competing_winner_resolves_conflict_without_guessing(tmp_path):
    path = tmp_path / "attempt-competitor.sqlite"
    seed = make_store(path)
    pin = seed.capture_pin()
    pin = full_commit(seed, pin, "old-success", "one", 1).pin
    competitor_pin = seed.capture_pin()
    seed._phase_hook = lambda phase: (
        (_ for _ in ()).throw(OSError("failed before commit"))
        if phase == "before_commit"
        else None
    )
    with pytest.raises(OSError):
        full_commit(seed, pin, "failed-new", "two", 2)
    seed._phase_hook = lambda phase: None
    seed.close()

    with open_store(path) as competitor:
        winner = full_commit(competitor, competitor_pin, "winner", "winner", 2)
        resolved = competitor.resolve_commit(pin, "failed-new")
        assert resolved.outcome == "conflict"
        assert resolved.stale
        assert resolved.generation == 2
        with pytest.raises(GenerationPressureError):
            full_commit(competitor, winner.pin, "blocked", "later", 3)


def test_actual_commit_then_sqlite_error_is_resolved_as_committed(tmp_path):
    path = tmp_path / "ambiguous-sqlite-commit.sqlite"
    store = make_store(path)
    pin = store.capture_pin()
    original = store._commit_sqlite

    def commit_then_raise():
        original()
        raise sqlite3.OperationalError("simulated ambiguous sqlite acknowledgement")

    store._commit_sqlite = commit_then_raise
    with pytest.raises(sqlite3.OperationalError, match="ambiguous"):
        full_commit(store, pin, "ambiguous", "new", 1)
    with pytest.raises(StoreConflictError, match="unresolved"):
        store.release_pin(pin)
    store.close()

    with open_store(path) as recovered:
        result = recovered.resolve_commit(pin, "ambiguous")
        assert result.outcome == "committed"
        assert result.generation == 1
        assert recovered.read_version(
            result.pin, "people", 1, expected_record_schema=1
        ).value == "new"
        recovered.verify_all()


def test_sqlite_commit_error_before_commit_resolves_not_committed(tmp_path):
    path = tmp_path / "sqlite-commit-fail.sqlite"
    store = make_store(path)
    pin = store.capture_pin()

    def fail_commit():
        raise sqlite3.OperationalError("simulated sqlite commit failure")

    store._commit_sqlite = fail_commit
    with pytest.raises(sqlite3.OperationalError, match="commit failure"):
        full_commit(store, pin, "failed", "new", 1)
    store._commit_sqlite = store.db.commit
    result = store.resolve_commit(pin, "failed")
    assert result.outcome == "not_committed"
    assert result.generation == 0
    assert store.generation == 0
    store.verify_all()
    store.close()


def test_verify_all_reuses_owned_snapshot_and_standalone_leaves_no_transaction(tmp_path):
    path = tmp_path / "verify-snapshot.sqlite"
    with make_store(path) as store:
        pin = store.capture_pin()
        pin = full_commit(store, pin, "g1", "one", 1).pin
        assert not store.db.in_transaction
        store.verify_all()
        assert not store.db.in_transaction

        store.db.execute("BEGIN")
        assert store.db.in_transaction
        store.verify_all()
        assert store.db.in_transaction
        store.db.rollback()
        assert not store.db.in_transaction
