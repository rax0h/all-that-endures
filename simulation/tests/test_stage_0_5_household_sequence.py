"""R3 standalone versioned member sequence proofs before World integration."""
import gc
import sys

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError
from ate_sim.persistence_adapters import WorldCodec, SCHEMA
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_lazy_household_members import (
    PAGE_SIZE, PAGE_NAMESPACE, LENGTH_NAMESPACE,
    LazyHouseholdMembers, bootstrap_household_members,
)

RULES = "stage-0.5-r3-household-pages"


def make_store(tmp_path, count=0, *, members=None):
    path = tmp_path / "r3.sqlite"
    store = LazyRecordStore.create(
        path, codec=WorldCodec(identity_links_recorded=True),
        simulation_schema=SCHEMA, rules_id=RULES,
    )
    store.db.execute("BEGIN IMMEDIATE")
    try:
        bootstrap_household_members(
            store, 0, [(1, list(range(1, count+1)) if members is None else members)]
        )
        store.db.commit()
    except:
        store.db.rollback()
        store.close()
        raise
    return store


@pytest.mark.parametrize("count", [1000, 10000])
def test_checked_pages_are_bounded_by_history_with_exact_order(tmp_path, count):
    store = make_store(tmp_path, count)
    pin = store.capture_pin()
    try:
        sequence = LazyHouseholdMembers(store, pin, 1)
        assert len(sequence) == count
        assert sequence[0] == 1
        assert sequence[-1] == count
        assert sequence[127] == 128
        assert sequence[128] == 129
        assert sequence[:5] == [1, 2, 3, 4, 5]
        assert sum(1 for _ in sequence) == count
        gc.collect()
        stats = sequence.diagnostics()
        assert stats["resident_cached_pages"] <= 4
        assert stats["cached_member_ids"] <= PAGE_SIZE * 4
        assert stats["dirty_member_ids"] == 0
        assert sequence.pending_changes() == ()
        print("R3 read bound", count, stats)
    finally:
        store.release_pin(pin)
        store.close()


@pytest.mark.parametrize("count", [1000, 10000])
def test_one_append_changes_length_plus_at_most_one_bounded_page(tmp_path, count):
    store = make_store(tmp_path, count)
    pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, pin, 1)
        seq.append(count + 1)
        changes = seq.pending_changes()
        assert len(changes) == 2
        assert {change.namespace for change in changes} == {
            LENGTH_NAMESPACE, PAGE_NAMESPACE
        }
        assert len(next(c.value for c in changes if c.namespace == PAGE_NAMESPACE)) <= PAGE_SIZE
        store.reset_diagnostics()
        result = store.commit(
            pin, commit_token=("append", count),
            version_changes=changes, changes=(), new_segments=(),
            metadata=store.checked_head().metadata,
        )
        assert result.outcome == "committed"
        writes = store.diagnostics().payload_writes
        print("R3 writes", count, writes, store.diagnostics().payload_write_bytes)
        assert writes == 2
        pin = result.pin
        seq.accept_save(pin)
        assert seq.pending_changes() == ()
        assert seq[-1] == count + 1
        assert seq[:3] == [1, 2, 3]
        assert seq[-3:] == [count-1, count, count+1]
        check = LazyHouseholdMembers(store, pin, 1)
        assert check == seq
        assert len(check) == count + 1
        assert len(check._cache) == 4 or len(check._cache) <= 4
        assert store.verify_all()
    finally:
        store.release_pin(pin)
        store.close()


def test_duplicate_edit_slice_insert_delete_reverse_sort_and_alias(tmp_path):
    store = make_store(tmp_path, members=[5, 1, 1, 4])
    pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, pin, 1)
        alias = seq
        seq[0] = 8
        seq.append(3)
        seq.insert(2, 7)
        del seq[-1]
        seq[1:3] = [2, 2, 2]
        seq.reverse()
        seq.sort()
        assert seq == [1, 2, 2, 2, 4, 8]
        assert alias is seq
        assert len(seq.pending_changes()) <= 2
        with pytest.raises(TypeError):
            seq.append("bad")
        assert alias == [1, 2, 2, 2, 4, 8]
        with pytest.raises(TypeError):
            seq[1:3] = [6, "bad"]
        assert seq == [1, 2, 2, 2, 4, 8]
    finally:
        store.release_pin(pin)
        store.close()


def test_guard_and_corruption_reject_before_mutating(tmp_path):
    store = make_store(tmp_path, members=[1, 2])
    pin = store.capture_pin()
    active = False
    try:
        def guard():
            if not active:
                raise StoreError("lifecycle guard")
        seq = LazyHouseholdMembers(store, pin, 1, guard=guard)
        with pytest.raises(StoreError, match="lifecycle guard"):
            seq.append(3)
        assert len(seq) == 2
        store.db.execute("UPDATE lazy_record_versions SET payload=? WHERE namespace=?", (b"bad", PAGE_NAMESPACE))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            seq[0]
    finally:
        store.release_pin(pin)
        store.close()


def test_transaction_failure_keeps_old_page_and_dirty_overlay(tmp_path, monkeypatch):
    store = make_store(tmp_path, members=[1, 2, 3])
    pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, pin, 1)
        seq.append(4)
        changes = seq.pending_changes()
        def fail(phase):
            if phase == "before_commit":
                raise RuntimeError("before-commit fault")
        monkeypatch.setattr(store, "_phase_hook", fail)
        with pytest.raises(RuntimeError, match="before-commit fault"):
            store.commit(
                pin, commit_token="attempt-before-commit",
                version_changes=changes, changes=(), new_segments=(),
                metadata=store.checked_head().metadata,
            )
        # The original pin still selects the durable pre-save sequence;
        # the user's mutable overlay has not silently vanished.
        assert LazyHouseholdMembers(store, pin, 1) == [1, 2, 3]
        assert seq == [1, 2, 3, 4]
        assert seq.pending_changes() == changes
        monkeypatch.setattr(store, "_phase_hook", lambda _phase: None)
        resolved = store.resolve_commit(pin, "attempt-before-commit")
        assert resolved.outcome == "not_committed"
        result = store.commit(
            pin, commit_token="retry-after-rollback",
            version_changes=seq.pending_changes(), changes=(), new_segments=(),
            metadata=store.checked_head().metadata,
        )
        assert result.outcome == "committed"
        pin = result.pin
        seq.accept_save(pin)
        assert LazyHouseholdMembers(store, pin, 1) == [1, 2, 3, 4]
    finally:
        store.release_pin(pin)
        store.close()


def test_old_pin_reads_old_members_after_new_publication(tmp_path):
    store = make_store(tmp_path, members=[1, 1, 3])
    old_pin = store.capture_pin()
    writer_pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, writer_pin, 1)
        seq.append(4)
        result = store.commit(
            writer_pin, commit_token="new-member-epoch",
            version_changes=seq.pending_changes(), changes=(), new_segments=(),
            metadata=store.checked_head().metadata,
        )
        assert result.outcome == "committed"
        writer_pin = result.pin
        seq.accept_save(writer_pin)
        assert LazyHouseholdMembers(store, old_pin, 1) == [1, 1, 3]
        assert LazyHouseholdMembers(store, writer_pin, 1) == [1, 1, 3, 4]
    finally:
        store.release_pin(old_pin)
        store.release_pin(writer_pin)
        store.close()


def test_shrink_deletes_expired_pages_and_reopen(tmp_path):
    store = make_store(tmp_path, count=260)
    pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, pin, 1)
        del seq[1:]
        assert seq == [1]
        changes = seq.pending_changes()
        assert any(c.delete for c in changes)
        result = store.commit(
            pin, commit_token="shrink",
            version_changes=changes, changes=(), new_segments=(),
            metadata=store.checked_head().metadata,
        )
        pin = result.pin
        seq.accept_save(pin)
        assert LazyHouseholdMembers(store, pin, 1) == [1]
        assert not store.contains_lazy_key(pin, PAGE_NAMESPACE, (1, 1))
        assert not store.contains_lazy_key(pin, PAGE_NAMESPACE, (1, 2))
    finally:
        store.release_pin(pin)
        store.close()
