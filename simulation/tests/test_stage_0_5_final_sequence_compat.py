"""Native settlement values, compact references and portable sharing."""
import pytest

from simulation.ate_sim.event_log import FrozenList, freeze
from simulation.ate_sim.persistence_adapters import WorldCodec
from simulation.ate_sim.persistence_lazy_nested_history import HistoryReference, HISTORY_CLASSES, HISTORY_TYPES
from simulation.ate_sim.persistence_lazy_sequence import LazyOrderedSequence
from simulation.ate_sim.persistence_lazy_store import LazyRecordStore
from simulation.tests.test_persistence_lazy_store import metadata
from simulation.tests.test_stage_0_5_final_sequence import publish


def native(store, values):
    seq = LazyOrderedSequence(store, store.capture_pin(), 1, initial_values=values, value_mode='native')
    publish(seq, 'initial')
    return seq


def store_at(path):
    return LazyRecordStore.create(path, codec=WorldCodec(), simulation_schema='8', rules_id='stage-0.5')


def test_native_numeric_representatives_and_first_equal_removal(tmp_path):
    with store_at(tmp_path / 'numeric.sqlite') as store:
        seq = native(store, [True, 1.0, 1, False, 0.0, 0, -2, 4.5, '1', (1, 2)])
        assert seq.occurrences(1) == (0, 1, 2)
        assert seq.candidate_positions([1]) == (0, 1, 2)
        seq.remove(1)
        assert type(seq[0]) is float
        seq[0] = 1
        assert type(seq[0]) is int
        seq[0] = True
        assert type(seq[0]) is bool
        publish(seq, 'representatives')
        seq = LazyOrderedSequence(store, seq._pin, 1)
        assert type(seq[0]) is bool
        assert seq.occurrences(1.0) == (0, 1)
        assert seq.occurrences(False) == (2, 3, 4)
        seq.remove(0)
        assert type(seq[2]) is float
        seq.scrub()


def test_native_unindexed_values_and_infinities_survive_without_integer_index(tmp_path):
    with store_at(tmp_path / 'unindexed.sqlite') as store:
        expected = [None, 'value', -5, 0, False, 4.5, float('inf'), float('-inf'), (2, 8), frozenset((4, 5))]
        seq = native(store, expected)
        assert list(seq) == expected
        assert seq.occurrences(3) == ()
        seq.remove((2, 8))
        expected.remove((2, 8))
        publish(seq, 'tuple')
        seq.scrub()
        assert list(seq) == expected
        with pytest.raises(TypeError): seq.append([])


def test_typed_reference_is_compact_and_proxy_snapshot_is_plain(tmp_path):
    with store_at(tmp_path / 'reference.sqlite') as store:
        seq = native(store, range(1000))
        before = store.diagnostics()
        ref = seq.storage_reference()
        assert ref == HistoryReference('sequence', 1)
        assert store.codec.decode(store.codec.encode(ref)) == ref
        assert store.diagnostics().payload_reads == before.payload_reads
        assert len(store.codec.encode(ref)) < 128
        assert type(seq) in HISTORY_TYPES and HISTORY_CLASSES['sequence'] is type(seq)
        assert store.codec.decode(store.codec.encode(seq)) == list(range(1000))


def test_freeze_and_materializing_detach_preserve_value_and_sharing(tmp_path):
    with store_at(tmp_path / 'portable.sqlite') as store:
        seq = native(store, [True, 1.0, 2])
        memo = {}
        plain = seq.materialize(memo)
        assert seq.materialize(memo) is plain
        assert [type(v) for v in plain] == [bool, float, int]
        frozen = freeze(seq)
        assert isinstance(frozen, FrozenList) and frozen == plain
        with pytest.raises(TypeError): frozen.append(3)
        seq.append(4)
        assert frozen == [True, 1.0, 2]


def test_pending_changes_shim_acknowledges_exact_plan_and_clean_pin_advance(tmp_path):
    with store_at(tmp_path / 'participant.sqlite') as store:
        seq = native(store, [1, 2])
        seq.insert(1, 3)
        versions = seq.pending_changes()
        pin = store.commit(seq._pin, commit_token='participant', version_changes=versions,
            changes=(), new_segments=(), metadata=metadata(2, ())).pin
        # Existing frozen hybrid publisher advances the lease before acceptance.
        seq._pin = pin
        seq.accept_save(pin)
        assert not seq.pending_changes()
        pin = store.commit(pin, commit_token='clean', version_changes=(), changes=(), new_segments=(),
            metadata=metadata(3, ())).pin
        seq.accept_save(pin)
        assert list(seq) == [1, 3, 2]
