"""Numeric equality aliases use checked occurrence order, not history scans."""
import pytest

from simulation.ate_sim.incremental_store import StoreIntegrityError
from simulation.ate_sim.persistence_lazy_sequence import LazyOrderedSequence, MEMBER_NAMESPACE
from simulation.tests.test_stage_0_5_final_sequence_compat import native, store_at
from simulation.tests.test_stage_0_5_final_sequence import publish


@pytest.mark.parametrize('lookup', [True, 1.0])
def test_numeric_alias_first_removal_uses_checked_tree(tmp_path, monkeypatch, lookup):
    with store_at(tmp_path / 'numeric.sqlite') as store:
        seq = native(store, [2] * 1000 + [True, 1.0, 1, 3])
        old = store.capture_pin()
        with monkeypatch.context() as patch:
            patch.setattr(LazyOrderedSequence, '__iter__',
                lambda self: pytest.fail('numeric lookup scanned history'))
            assert seq.occurrences(lookup) == (1000, 1001, 1002)
            assert seq.candidate_positions([lookup]) == (1000, 1001, 1002)
            seq.remove(lookup)
            assert seq.occurrences(lookup) == (1000, 1001)
            assert seq.occurrences(9.0) == ()
            with pytest.raises(ValueError):
                seq.remove(9.0)
        assert type(seq[1000]) is float
        publish(seq, 'removed')
        assert type(LazyOrderedSequence(store, old, 1)[1000]) is bool
        seq.scrub()


@pytest.mark.parametrize('lookup', [True, 1.0])
def test_numeric_alias_rejects_missing_required_member_tree(tmp_path, lookup):
    with store_at(tmp_path / 'corrupt.sqlite') as store:
        seq = native(store, [True, 1.0, 1])
        root = seq._dget(1)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                         (MEMBER_NAMESPACE, store.codec.encode((1, root[0]))))
        store.db.commit()
        seq = LazyOrderedSequence(store, seq._pin, 1)
        with pytest.raises(StoreIntegrityError):
            seq.occurrences(lookup)
        with pytest.raises(StoreIntegrityError):
            seq.remove(lookup)
        assert len(seq) == 3 and not seq._dirty
