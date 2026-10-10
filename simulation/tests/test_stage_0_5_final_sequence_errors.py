"""Native partial list writes remain checked across counted tree publication."""
import pytest

from simulation.ate_sim.incremental_store import StoreConflictError, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_sequence import LazyOrderedSequence, MEMBER_NAMESPACE
from simulation.tests.test_persistence_lazy_store import make_store
from simulation.tests.test_stage_0_5_final_sequence import sequence, publish


def test_failing_extend_preserves_native_partial_prefix_and_old_pin(tmp_path):
    with make_store(tmp_path / 'partial.sqlite') as store:
        seq = sequence(store, [1, 2, 2])
        old = LazyOrderedSequence(store, store.capture_pin(), 1)
        expected = [1, 2, 2]
        changes = []
        seq.bind(None, lambda: changes.append(tuple(seq)))
        def broken():
            yield 3
            yield 2
            raise ValueError('iterator failed')
        for value in (expected, seq):
            with pytest.raises(ValueError, match='iterator failed'):
                value.extend(broken())
        assert list(seq) == expected
        assert changes and changes[-1] == tuple(expected)
        seq.scrub()
        publish(seq, 'partial')
        assert list(old) == [1, 2, 2]
        reopened = LazyOrderedSequence(store, seq._pin, 1)
        assert list(reopened) == expected
        assert reopened.occurrences(2) == (1, 2, 4)
        reopened.scrub()


def test_extend_iterator_observes_prior_appends_like_native_list(tmp_path):
    with make_store(tmp_path / 'observed.sqlite') as store:
        seq = sequence(store, [1])
        def values():
            yield 2
            assert list(seq) == [1, 2]
            yield 3
        seq.extend(values())
        assert list(seq) == [1, 2, 3]


def test_extend_frozen_plan_rejects_before_consuming_input(tmp_path):
    with make_store(tmp_path / 'frozen.sqlite') as store:
        seq = sequence(store, [1])
        seq.append(2)
        prepared = seq.prepare_delta()
        visits = []
        def values():
            visits.append('consumed')
            yield 3
        with pytest.raises(StoreConflictError):
            seq.extend(values())
        assert not visits
        assert seq.prepare_delta() == prepared


def test_self_extension_snapshots_original_occurrences_once(tmp_path):
    with make_store(tmp_path / 'self.sqlite') as store:
        seq = sequence(store, [1, 2, 1])
        seq.extend(seq)
        assert list(seq) == [1, 2, 1, 1, 2, 1]
        publish(seq, 'self')
        seq.scrub()


def test_extend_later_corrupt_member_path_rolls_back_all_tree_writes(tmp_path):
    with make_store(tmp_path / 'corrupt-prefix.sqlite') as store:
        initial = [4, 2, 2] * 60
        seq = sequence(store, initial)
        with store.read_snapshot(seq._pin):
            member = seq._dget(4)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                         (MEMBER_NAMESPACE, store.codec.encode((1, member[0]))))
        store.db.commit()
        seq = LazyOrderedSequence(store, seq._pin, 1)
        descriptor = seq._descriptor()
        with pytest.raises(StoreIntegrityError):
            seq.extend([2, 4])
        assert seq._descriptor() == descriptor
        assert not seq._dirty and not seq._baseline
        assert list(seq) == initial


def test_extend_input_cannot_freeze_an_incomplete_save_plan(tmp_path):
    with make_store(tmp_path / 'mid-extend-save.sqlite') as store:
        seq = sequence(store, [1])
        def values():
            yield 2
            seq.prepare_delta()
            yield 3
        with pytest.raises(StoreConflictError, match='mutation'):
            seq.extend(values())
        assert list(seq) == [1, 2]
        assert seq._prepared is None
        publish(seq, 'checked-prefix')
        seq.scrub()


def test_mutation_guard_cannot_freeze_then_change_the_frozen_plan(tmp_path):
    with make_store(tmp_path / 'guard-freeze.sqlite') as store:
        seq = sequence(store, [1])
        seq.append(2)
        seq.bind(lambda: seq.prepare_delta(), None)
        with pytest.raises(StoreConflictError, match='mutation'):
            seq.append(3)
        assert list(seq) == [1, 2]
        assert seq._prepared is None
        seq.bind(None, None)
        publish(seq, 'checked-guard')
        seq.scrub()
