"""An exact point read shares metadata, preserving root/forward source checks."""
from unittest.mock import patch

import pytest

from simulation.tests.test_persistence_lazy_store import make_store
from simulation.tests.test_stage_0_5_final_identity_catalog import groups, catalog, NS
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open


def test_generic_membership_checks_operational_rows_once(tmp_path):
    with make_store(tmp_path/'point.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        for path, expected in [((), 1), ((('field', 'absent'),), None)]:
            with patch.object(store, '_checked_operational_rows', wraps=store._checked_operational_rows) as checks:
                assert cat.read_identity_membership(pin, (NS, 1), path) == expected
                assert checks.call_count == 1
            assert getattr(store, '_validation_scope', None) is None
            assert not store.db.in_transaction


def test_native_membership_bounds_head_checks(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    owner = ('world.skills.skills', (1, 'craft'))
    member = (('field', 'provenance'),)
    with fast_open(path, pair) as session:
        store = session.store
        expected = store.read_identity_occurrence(session.pin, *owner, member).incarnation_id
        cat = session._identity_coordinator.catalog
        with patch.object(store, '_checked_head_row', wraps=store._checked_head_row) as checks:
            assert cat.read_identity_membership(session.pin, owner, member) == expected
            assert checks.call_count <= 2
        assert store._validation_scope is None and not store.db.in_transaction


def test_native_owner_absence_keeps_one_authenticated_witness_lookup(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import OWNER_NAMESPACE

    path, pair = ranked_fixture(tmp_path, size=4)
    owner = ('world.skills.skills', (1000, 'craft'))
    with fast_open(path, pair) as session:
        store = session.store
        coord = session._identity_coordinator
        witness_key = store.codec.encode(owner)
        with patch.object(store, '_visible_record_row', wraps=store._visible_record_row) as visible:
            assert coord._owner_changes(owner, ()) == {}
        witness_calls = [row for row in visible.call_args_list if row.args[1:] == (OWNER_NAMESPACE, witness_key)]
        assert len(witness_calls) == 1
        assert store._validation_scope is None and not store.db.in_transaction


def test_membership_scope_honors_small_catalog_budget(tmp_path, monkeypatch):
    from simulation.ate_sim.persistence_validation_scope import ValidationScope
    with make_store(tmp_path/'budget.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store, byte_limit=128)
        seen = []
        original = ValidationScope.remember
        def remember(scope, *args, **kwargs):
            result = original(scope, *args, **kwargs)
            seen.append((scope.byte_limit, scope.bytes))
            return result
        monkeypatch.setattr(ValidationScope, 'remember', remember)
        assert cat.read_identity_membership(pin, (NS, 1), ()) == 1
        assert seen and all(limit <= 21 and retained <= limit for limit, retained in seen)
        assert store._validation_scope is None and not store.db.in_transaction


def test_membership_rechecks_corruption_after_previous_success(tmp_path):
    from simulation.ate_sim.incremental_store import StoreIntegrityError
    with make_store(tmp_path/'corrupt.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        assert cat.read_identity_membership(pin, (NS, 1), ()) == 1
        store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?',
                         (b'corrupt', catalog().OWNER_TREE_NAMESPACE))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            cat.read_identity_membership(pin, (NS, 1), ())
        assert getattr(store, '_validation_scope', None) is None
        assert not store.db.in_transaction
