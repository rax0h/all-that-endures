"""Type counters follow exact representatives, overlays and acknowledged plans."""
import pytest

from simulation.ate_sim.persistence_history_types import NAMESPACE, TAG, verify_type_witnesses
from simulation.ate_sim.persistence_lazy_nested_history import HISTORY_CLASSES
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.ate_sim.incremental_store import StoreIntegrityError
from simulation.tests.test_persistence_lazy_store import metadata
from simulation.tests.test_stage_0_5_final_sequence_compat import store_at


def create(store, kind, values):
    history = HISTORY_CLASSES[kind](store, store.capture_pin(), 1, initial_values=values,
        checked_types=True, **({'value_mode': 'native'} if kind == 'sequence' else {}))
    publish(history, 'initial')
    return history


def publish(history, token):
    pin = history._store.commit(history._pin, commit_token=token, changes=(), new_segments=(),
        version_changes=history.pending_changes(), metadata=metadata()).pin
    history.accept_save(pin)
    return pin


@pytest.mark.parametrize('kind', ['list', 'set', 'map', 'sequence'])
def test_counter_changes_and_cancellation_preserve_exact_representatives(tmp_path, kind):
    with store_at(tmp_path / 'types.sqlite') as store:
        values = {True: None, ('person', 2): None, 'other': None} if kind == 'map' else {True, ('person', 2), 'other'} if kind == 'set' else [True, ('person', 2), 'other']
        history = create(store, kind, values)
        assert history._member_types.counts == (0, 1, 2)
        assert verify_type_witnesses(store, history._pin) == 1
        if kind in ('list', 'sequence'):
            history[0] = 1
            assert history._member_types.counts == (1, 1, 1)
            history[0] = True
            assert not any(c.namespace == NAMESPACE for c in history.pending_changes())
            publish(history, 'representative-restored')
            del history[:]
            history.extend([8, 8, 9])
        if kind == 'map':
            # Equal numeric lookup cannot replace the retained bool key.
            history[1.] = None
            assert history._member_types.counts == (0, 1, 2)
            history.clear()
            history.update({8: None, 9: None})
        elif kind == 'set':
            history.add(1.)
            assert history._member_types.counts == (0, 1, 2)
            history.clear()
            history.update({8, 9})
        history._member_types.require_policy(history, 'int')
        publish(history, 'edited')
        assert verify_type_witnesses(store, history._pin) == 1
        assert history._member_types.counts == (len(history), 0, 0)
        reopened = HISTORY_CLASSES[kind](store, history._pin, 1)
        reopened._member_types.require_policy(reopened, 'int')


@pytest.mark.parametrize('kind', ['list', 'set', 'map', 'sequence'])
def test_missing_or_wrong_count_required_witness_fails_without_history_scan(tmp_path, kind):
    with store_at(tmp_path / 'missing.sqlite') as store:
        values = {1: 2} if kind == 'map' else {1} if kind == 'set' else [1]
        history = create(store, kind, values)
        pin = store.commit(history._pin, commit_token='missing', changes=(), new_segments=(),
            version_changes=(VersionChange(NAMESPACE, 1, delete=True),), metadata=metadata()).pin
        with pytest.raises(StoreIntegrityError, match='mandatory'):
            HISTORY_CLASSES[kind](store, pin, 1)
        pin = store.commit(pin, commit_token='wrong-count', changes=(), new_segments=(),
            version_changes=(VersionChange(NAMESPACE, 1, (TAG, kind, (2, 0, 0))),), metadata=metadata()).pin
        with pytest.raises(StoreIntegrityError, match='descriptor count'):
            HISTORY_CLASSES[kind](store, pin, 1)


def test_sequence_validation_failure_rolls_back_type_counter_with_tree(tmp_path, monkeypatch):
    with store_at(tmp_path / 'rollback.sqlite') as store:
        history = create(store, 'sequence', [1, 2])
        baseline = history._member_types.counts
        with pytest.raises(TypeError):
            history[:] = ['allowed native value', []]
        assert list(history) == [1, 2]
        assert history._member_types.counts == baseline
        assert history.pending_changes() == ()
        def fail_write(*args):
            raise OSError('tree write failed after type counter update')
        monkeypatch.setattr(history, '_nwrite', fail_write)
        with pytest.raises(OSError, match='tree write failed'):
            history.append('new native value')
        assert history._member_types.counts == baseline
        assert list(history) == [1, 2]
        assert history.pending_changes() == ()


def test_explicit_scrub_rejects_a_semantically_false_checked_witness(tmp_path):
    with store_at(tmp_path / 'false.sqlite') as store:
        history = create(store, 'list', ['other'])
        pin = store.commit(history._pin, commit_token='false', changes=(), new_segments=(),
            version_changes=(VersionChange(NAMESPACE, 1, (TAG, 'list', (1, 0, 0))),), metadata=metadata()).pin
        with pytest.raises(StoreIntegrityError, match='backing values'):
            verify_type_witnesses(store, pin)


@pytest.mark.parametrize('kind', ['list', 'set', 'map', 'sequence'])
def test_old_pin_reads_the_original_type_witness_and_values(tmp_path, kind):
    with store_at(tmp_path / 'old.sqlite') as store:
        history = create(store, kind, {'bad': None} if kind == 'map' else {'bad'} if kind == 'set' else ['bad'])
        old = store.capture_pin()
        if kind in ('list', 'sequence'):
            history[0] = 8
        elif kind == 'map':
            history.clear()
            history[8] = None
        else:
            history.clear()
            history.add(8)
        publish(history, 'edited')
        reader = HISTORY_CLASSES[kind](store, old, 1)
        assert list(reader) == ['bad']
        assert reader._member_types.counts == (0, 0, 1)
        with pytest.raises(TypeError, match='member'):
            reader._member_types.require_policy(reader, 'int')
        history._member_types.require_policy(history, 'int')
        store.release_pin(old)
