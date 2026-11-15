"""Tiny direct-entry probes; no generated-year construction or timing claims."""
import shutil
from unittest.mock import patch

import pytest

from simulation.tests.test_persistence_lazy_store import make_store
from simulation.tests.test_stage_0_5_final_identity_catalog import groups, catalog, NS


@pytest.mark.parametrize('case', ['new-owner', 'missing-source', 'missing-witness',
    'missing-both', 'missing-forward', 'collision', 'borrowed', 'read-transaction',
    'rollback', 'released-pin', 'exception', 'zero-cache'])
def test_generic_direct_entry(tmp_path, case):
    from simulation.ate_sim.incremental_store import StoreError, StoreIntegrityError
    from simulation.ate_sim.persistence_validation_scope import checked_read_operation
    with make_store(tmp_path/'generic.sqlite') as st:
        pin = groups(st)
        cat = catalog().IdentityCatalog(st, byte_limit=1 if case == 'zero-cache' else 2*1024*1024)
        owner = (NS, 1)
        assert cat.read_identity_membership(pin, owner, ()) == 1
        if case == 'new-owner':
            assert cat.read_identity_membership(pin, (NS, 999), ()) is None
        elif case in ('missing-source', 'missing-witness', 'missing-both', 'missing-forward'):
            if case in ('missing-source', 'missing-both'):
                st.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?', (NS, st.codec.encode(1)))
            if case in ('missing-witness', 'missing-both'):
                st.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?', (catalog().OWNER_NAMESPACE, st.codec.encode(owner)))
            if case == 'missing-forward':
                st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?', (NS, st.codec.encode(1)))
            st.db.commit()
            with pytest.raises(StoreError):cat.read_identity_membership(pin, owner, ())
        elif case == 'collision':
            wanted = catalog().path_hash(st.codec, ())
            with patch.object(catalog(), 'path_hash', return_value=wanted):
                with pytest.raises(StoreIntegrityError, match='hash collision'):
                    cat.read_identity_membership(pin, owner, (('field', 'absent'),))
        elif case in ('borrowed', 'read-transaction'):
            outer = st.read_snapshot(pin) if case == 'borrowed' else st.read_transaction()
            observed = []
            original = cat._owner
            def owner_read(*args):
                observed.append(st._validation_scope.can_reuse(st, pin))
                return original(*args)
            with outer:
                with patch.object(cat, '_owner', owner_read):
                    assert cat.read_identity_membership(pin, owner, ()) == 1
                assert st.db.in_transaction
            assert observed == [False]
        elif case == 'rollback':
            with checked_read_operation(st, pin) as scope:
                assert cat.read_identity_membership(pin, owner, ()) == 1
                st.db.execute('SAVEPOINT review')
                st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?', (NS, st.codec.encode(1)))
                with pytest.raises(StoreIntegrityError):cat.read_identity_membership(pin, owner, ())
                st.db.execute('ROLLBACK TO review');st.db.execute('RELEASE review')
                assert not scope.can_reuse(st, pin)
                assert cat.read_identity_membership(pin, owner, ()) == 1
        elif case == 'released-pin':
            st.release_pin(pin)
            with pytest.raises(StoreError):cat.read_identity_membership(pin, owner, ())
        elif case == 'exception':
            with patch.object(cat, '_node', side_effect=RuntimeError('injected')):
                with pytest.raises(RuntimeError, match='injected'):cat.read_identity_membership(pin, owner, ())
            assert cat.read_identity_membership(pin, owner, ()) == 1
        else:
            observed = []
            original = cat._owner
            def owner_read(*args):
                scope = st._validation_scope
                observed.append((scope.byte_limit, scope.bytes))
                return original(*args)
            with patch.object(cat, '_owner', owner_read):
                assert cat.read_identity_membership(pin, owner, ()) == 1
            assert observed == [(0, 0)]
        assert getattr(st, '_validation_scope', None) is None
        assert not st.db.in_transaction


@pytest.fixture(scope='module')
def native_seed(tmp_path_factory):
    from simulation.tests.test_stage_0_6_proof_open import ranked_fixture
    return ranked_fixture(tmp_path_factory.mktemp('seed'), size=4)


@pytest.mark.parametrize('case', ['absent', 'new-owner', 'borrowed', 'callback-history',
    'codec', 'lease', 'rollback', 'missing-all', 'forward-loss', 'exception'])
def test_native_direct_entry(tmp_path, native_seed, case):
    from ate_sim.incremental_store import StoreError
    from ate_sim.persistence_lazy_identity_catalog import OWNER_NAMESPACE
    from simulation.tests.test_stage_0_6_proof_open import fast_open
    source, pair = native_seed
    target = tmp_path/'native.sqlite'
    shutil.copyfile(source, target)
    session = fast_open(target, pair)
    st, cat, pin = session.store, session._identity_coordinator.catalog, session.pin
    owner, member = ('world.skills.skills', (1, 'craft')), (('field', 'provenance'),)
    try:
        expected = cat.read_identity_membership(pin, owner, member)
        assert type(expected) is int
        if case in ('absent', 'new-owner'):
            selected = owner if case == 'absent' else (owner[0], (999, 'craft'))
            assert cat.read_identity_membership(pin, selected, (('field', 'absent'),)) is None
        elif case in ('borrowed', 'callback-history'):
            from contextlib import nullcontext
            if case == 'callback-history':
                st.db.set_trace_callback(lambda _: None);st.db.set_trace_callback(None)
            observed = []
            original = cat._owner
            def owner_read(*args):
                observed.append(st._validation_scope._native_custody)
                return original(*args)
            with st.read_snapshot(pin) if case == 'borrowed' else nullcontext():
                with patch.object(cat, '_owner', owner_read):
                    assert cat.read_identity_membership(pin, owner, member) == expected
            assert observed == [None]
        elif case == 'exception':
            with patch.object(cat, '_node', side_effect=RuntimeError('injected')):
                with pytest.raises(RuntimeError):cat.read_identity_membership(pin, owner, member)
            assert cat.read_identity_membership(pin, owner, member) == expected
        else:
            if case == 'codec':st.codec.decode = lambda _: None
            elif case == 'lease':
                st.db.execute('DELETE FROM generation_pins WHERE token=?', (pin.token,));st.db.commit()
            elif case == 'rollback':
                st.db.execute('SAVEPOINT review')
                st.db.execute("UPDATE records SET payload_checksum='changed' WHERE namespace='world.seed'")
                st.db.execute('ROLLBACK TO review');st.db.execute('RELEASE review')
            elif case == 'missing-all':
                st.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?', (owner[0], st.codec.encode(owner[1])))
                st.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?', (OWNER_NAMESPACE, st.codec.encode(owner)))
                st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?', (owner[0], st.codec.encode(owner[1])))
                st.db.commit()
                st._world_proof_authority.epoch = st._world_proof_authority._epoch()
            else:
                st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?', (owner[0], st.codec.encode(owner[1])))
                st.db.commit()
                st._world_proof_authority.epoch = st._world_proof_authority._epoch()
            with pytest.raises(StoreError):cat.read_identity_membership(pin, owner, member)
        assert getattr(st, '_validation_scope', None) is None
        assert not st.db.in_transaction
    finally:
        if case == 'codec':del st.codec.decode
        st.close()
