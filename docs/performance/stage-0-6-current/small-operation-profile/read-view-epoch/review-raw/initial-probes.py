"""Independent review probes; diagnostic evidence, not production code."""
from pathlib import Path
import sqlite3
from unittest.mock import patch
import pytest

from ate_sim.incremental_store import StoreError
from ate_sim.persistence_validation_scope import checked_read_operation
from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, CATALOG_NAMESPACE
from ate_sim.persistence_lazy_spill import CheckedSpool
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

OWNER = ('world.skills.skills', (1, 'craft'))

@pytest.mark.parametrize('control', ['isolation-level', 'context-commit', 'context-rollback', 'cursor-script'])
def test_public_controls_permanently_invalidate(tmp_path, control):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st = s.store
        with checked_read_operation(st, s.pin) as scope:
            scope.remember('probe', (), ('accepted',))
            assert scope.lookup('probe', ()) == ('accepted',)
            before = st._world_proof_authority._epoch()
            if control == 'isolation-level':
                original = st.db.isolation_level
                st.db.isolation_level = None
                st.db.isolation_level = original
            elif control == 'context-commit':
                with st.db: pass
            elif control == 'context-rollback':
                try:
                    with st.db: raise RuntimeError('rollback')
                except RuntimeError: pass
            else:
                st.db.cursor().executescript('COMMIT; BEGIN;')
            if not st.db.in_transaction: st.db.execute('BEGIN')
            assert st._world_proof_authority._epoch() == before
            assert not scope.can_reuse(st, s.pin)
            assert scope.lookup('probe', ()) is None
            assert scope.entries == scope.bytes == 0
        assert st._validation_scope is None and not st.db.in_transaction


def test_pending_returning_invalidates_before_total_changes_advances(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st = s.store
        with checked_read_operation(st, s.pin) as scope:
            original = st.db.total_changes
            scope.remember('probe', (), ('accepted',))
            cursor = st.db.execute('UPDATE records SET payload_checksum=payload_checksum RETURNING namespace')
            try:
                assert st.db.total_changes == original
                assert not scope.can_reuse(st, s.pin)
                assert scope.entries == scope.bytes == 0
            finally:
                cursor.close()
                st.db.rollback()
                st.db.execute('BEGIN')
            assert not scope.can_reuse(st, s.pin)
        assert st._validation_scope is None and not st.db.in_transaction


def test_pending_returning_cannot_use_warmed_descriptor_after_autocommit_admission(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st, cat = s.store, s._identity_coordinator.catalog
        cat.read_owner_identity(s.pin, OWNER)
        st.db.isolation_level = None
        cursor = st.db.execute('UPDATE records SET payload_checksum=payload_checksum RETURNING namespace')
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        try:
            cat.read_owner_identity(s.pin, (OWNER[0], (2, 'craft')))
            assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        finally:
            cursor.close()
        assert st._validation_scope is None and not st.db.in_transaction


def test_scope_exit_and_public_iterator_do_not_retain_custody(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st = s.store
        with pytest.raises(RuntimeError):
            with checked_read_operation(st, s.pin) as scope:
                scope.remember('probe', (), ('accepted',))
                raise RuntimeError('operation failed')
        assert scope.entries == scope.bytes == 0
        assert not scope.can_reuse(st, s.pin)
        assert st._validation_scope is None and not st.db.in_transaction
        iterator = st.iter_identity_occurrences_for_owner(s.pin, *OWNER)
        next(iterator)
        assert st._validation_scope is None
        iterator.close()
        assert not st.db.in_transaction
        with checked_read_operation(st, s.pin) as fresh:
            assert fresh is not scope and fresh.can_reuse(st, s.pin)
            assert not scope.can_reuse(st, s.pin)


@pytest.mark.parametrize('fail', [False, True])
def test_zero_transient_budget_and_spilled_owner_ownership(tmp_path, fail):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st = s.store
        # 1 byte forces even the single placement of this owner to spill.
        cat = IdentityCatalog(st, occurrence_limit=1, byte_limit=1)
        observed_scopes, spools = [], []
        original_node, original_init, original_freeze = cat._node, CheckedSpool.__init__, CheckedSpool.freeze
        def node(*args, **kwargs):
            scope = st._validation_scope
            assert scope is not None and scope.byte_limit == 0
            assert scope.entries == scope.bytes == 0
            observed_scopes.append(scope)
            return original_node(*args, **kwargs)
        def init(spool, *args, **kwargs):
            original_init(spool, *args, **kwargs)
            spools.append(spool)
        def freeze(spool):
            if fail: raise RuntimeError('freeze failure after spill')
            return original_freeze(spool)
        with patch.object(cat, '_node', node), patch.object(CheckedSpool, '__init__', init), patch.object(CheckedSpool, 'freeze', freeze):
            if fail:
                with pytest.raises(RuntimeError, match='freeze failure'): cat.read_owner_identity(s.pin, OWNER)
            else:
                result = cat.read_owner_identity(s.pin, OWNER)
                assert result.occurrences.spilled
                assert len(list(result.occurrences)) == 1
                assert Path(result.occurrences.path).is_file()
                result.occurrences.close()
        assert observed_scopes
        assert all(scope.entries == scope.bytes == 0 and not scope._valid for scope in observed_scopes)
        assert all(spool._closed and not Path(spool.path).exists() for spool in spools)
        stats = cat.owner_cache_diagnostics()
        assert stats['bytes'] <= stats['byte_limit'] and stats['entries'] <= stats['entry_limit']
        assert st._validation_scope is None and not st.db.in_transaction


@pytest.mark.parametrize('kind', ['callback-history', 'codec'])
def test_owner_fact_fallback_rechecks_descriptor(tmp_path, kind):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st, cat = s.store, s._identity_coordinator.catalog
        cat.read_owner_identity(s.pin, OWNER)
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        if kind == 'callback-history':
            st.db.set_trace_callback(lambda _: None)
            st.db.set_trace_callback(None)
        else:
            st.codec.decode = lambda _: None
        try:
            with patch.object(cat, '_read', wraps=cat._read) as reads:
                if kind == 'codec':
                    with pytest.raises(StoreError): cat.read_owner_identity(s.pin, (OWNER[0], (2, 'craft')))
                else:
                    cat.read_owner_identity(s.pin, (OWNER[0], (2, 'craft')))
                    assert any(call.args[1] == CATALOG_NAMESPACE for call in reads.call_args_list)
            assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        finally:
            if kind == 'codec': del st.codec.decode


def test_isolation_setter_release_exposes_external_corruption(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st, cat = s.store, s._identity_coordinator.catalog
        with checked_read_operation(st, s.pin) as scope:
            cat.read_owner_identity(s.pin, OWNER)
            st.db.isolation_level = None
            assert not st.db.in_transaction
            with sqlite3.connect(path) as writer:
                writer.execute("UPDATE records SET payload_checksum='external-review-drift' WHERE namespace='world.seed'")
            st.db.execute('BEGIN')
            assert not scope.can_reuse(st, s.pin)
            with pytest.raises(StoreError): cat.read_owner_identity(s.pin, OWNER)
        assert st._validation_scope is None and not st.db.in_transaction
