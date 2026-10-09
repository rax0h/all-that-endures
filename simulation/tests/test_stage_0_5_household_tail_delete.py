"""Tail member deletion and native first-match removal should not repage history.

These are narrow fast paths only. Deleting a middle occurrence remains an
explicit full-sequence transformation until the sparse rank pager lands.
"""
import pytest

from ate_sim.persistence_lazy_household_members import (
    LazyHouseholdMembers, LENGTH_NAMESPACE, PAGE_NAMESPACE,
)
from simulation.tests.test_stage_0_5_household_sequence import make_store


@pytest.mark.parametrize("history", [1000, 10000])
def test_native_pop_last_only_reads_and_writes_a_bounded_tail(tmp_path, history):
    store = make_store(tmp_path, history)
    pin = store.capture_pin()
    old_pin = store.capture_pin()
    try:
        old = LazyHouseholdMembers(store, old_pin, 1)
        seq = LazyHouseholdMembers(store, pin, 1)
        store.reset_diagnostics()
        assert seq.pop() == history
        assert len(seq) == history - 1
        assert seq[-1] == history - 1
        before = store.diagnostics()
        assert before.payload_reads <= 3
        assert before.payload_read_bytes < 8000
        changes = seq.pending_changes()
        assert {change.namespace for change in changes} == {
            LENGTH_NAMESPACE, PAGE_NAMESPACE
        }
        assert len(changes) == 2
        result = store.commit(
            pin, commit_token=("tail-pop", history),
            version_changes=changes, changes=(), new_segments=(),
            metadata=store.checked_head().metadata,
        )
        assert result.outcome == "committed"
        seq.accept_save(result.pin)
        assert old[-1] == history
        assert len(old) == history
        assert seq[-1] == history - 1
        fresh = LazyHouseholdMembers(store, result.pin, 1)
        assert fresh[-1] == history - 1
        assert len(fresh) == history - 1
        assert store.verify_all()
    finally:
        store.release_pin(old_pin)
        store.close()


@pytest.mark.parametrize("history", [1000, 10000])
def test_remove_unique_last_member_uses_checked_index(tmp_path, history):
    store = make_store(tmp_path, history)
    pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, pin, 1)
        store.reset_diagnostics()
        seq.remove(history)
        assert len(seq) == history - 1
        assert seq[-1] == history - 1
        io = store.diagnostics()
        assert io.payload_reads <= 3
        assert io.payload_read_bytes < 8000
        assert len(seq.pending_changes()) == 2
    finally:
        store.release_pin(pin)
        store.close()


def test_first_duplicate_is_removed_not_last_and_dirty_pages_override_index(tmp_path):
    store = make_store(tmp_path, members=[4, 9, 4, 2, 4])
    pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, pin, 1)
        seq.remove(4)
        assert list(seq) == [9, 4, 2, 4]
        seq.remove(4)
        assert list(seq) == [9, 2, 4]
        seq.remove(4)
        assert list(seq) == [9, 2]
        with pytest.raises(ValueError):
            seq.remove(4)
        with pytest.raises(ValueError):
            seq.remove(100)
        # bool/float equality retains Python list semantics.
        seq.remove(9.0)
        assert list(seq) == [2]
    finally:
        store.release_pin(pin)
        store.close()


def test_appended_tail_then_popped_back_to_baseline_is_a_noop(tmp_path):
    store = make_store(tmp_path, 128)
    pin = store.capture_pin()
    try:
        seq = LazyHouseholdMembers(store, pin, 1)
        seq.append(129)
        assert seq.pop() == 129
        assert seq.pending_changes() == ()
        assert list(seq) == list(range(1, 129))
    finally:
        store.release_pin(pin)
        store.close()
