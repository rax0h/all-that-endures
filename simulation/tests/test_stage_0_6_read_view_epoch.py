"""One owned read view may reuse its admitted epoch, never a released view."""
import sqlite3
from unittest.mock import patch

import pytest

from ate_sim.incremental_store import StoreError
from ate_sim.persistence_validation_scope import checked_read_operation
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

OWNER = ('world.skills.skills', (1, 'craft'))
PATH = (('field', 'provenance'),)


def group(session):
    inc = session.store.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
    return session._identity_coordinator.catalog, inc


def test_nested_physical_group_checks_do_not_repeat_epoch_sql(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        cat, inc = group(session)
        sql = []
        execute = type(st.db).execute
        def observed(db, statement, *args, **kwargs):
            sql.append(statement)
            return execute(db, statement, *args, **kwargs)
        with patch.object(type(st.db), 'execute', observed):
            with checked_read_operation(st, session.pin) as scope:
                before = len(sql)
                for _ in range(8):
                    assert len(cat.read_identity_group(session.pin, inc).occurrences) == 2
                pragmas = [s for s in sql[before:] if s.upper().startswith('PRAGMA ')]
                assert len(pragmas) <= 12
                assert scope.can_reuse(st, session.pin)
        assert st._validation_scope is None and not st.db.in_transaction
        assert st.db._known_authorizer is None


@pytest.mark.parametrize('control', ['commit', 'rollback', 'sql-commit', 'sql-rollback',
                                    'callback', 'custom-cursor', 'blob', 'schema-reset', 'autocommit'])
def test_equal_coarse_epoch_cannot_restore_closed_scope_custody(tmp_path, control):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        with checked_read_operation(st, session.pin) as scope:
            assert scope.can_reuse(st, session.pin)
            before = st._world_proof_authority._epoch()
            if control in ('commit', 'rollback'):
                getattr(st.db, control)()
                st.db.execute('BEGIN')
            elif control == 'autocommit':
                st.db.autocommit = True
                st.db.autocommit = False
                st.db.autocommit = sqlite3.LEGACY_TRANSACTION_CONTROL
            elif control.startswith('sql-'):
                st.db.execute(control[4:].upper())
                st.db.execute('BEGIN')
            elif control == 'callback':
                st.db.set_trace_callback(lambda _: None)
                st.db.set_trace_callback(None)
            elif control == 'custom-cursor':
                class CallerCursor(sqlite3.Cursor):pass
                st.db.cursor(factory=CallerCursor).close()
            elif control == 'blob':
                row = st.db.execute("SELECT rowid FROM store_metadata WHERE key='format_version'").fetchone()[0]
                st.db.blobopen('store_metadata', 'value', row).close()
            else:
                st.db.execute('CREATE TABLE custody_probe(x)')
                st.db.execute('DROP TABLE custody_probe')
                st.db.execute('PRAGMA schema_version=' + str(before[4]))
            assert st._world_proof_authority._epoch() == before
            assert not scope.can_reuse(st, session.pin)
            assert scope.entries == 0
        assert st._validation_scope is None and not st.db.in_transaction


def test_released_view_cannot_hide_external_change_before_reopen(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        cat, inc = group(session)
        with checked_read_operation(st, session.pin) as scope:
            cat.read_identity_group(session.pin, inc)
            st.db.rollback()
            with sqlite3.connect(path) as writer:
                writer.execute("UPDATE records SET payload_checksum='external-drift' WHERE namespace='world.seed'")
            st.db.execute('BEGIN')
            assert not scope.can_reuse(st, session.pin)
            with pytest.raises(StoreError):cat.read_identity_group(session.pin, inc)
        assert not st.db.in_transaction


def test_borrowed_view_keeps_full_epoch_checks(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        with st.read_snapshot(session.pin):
            with checked_read_operation(st, session.pin) as scope:
                assert not scope.can_reuse(st, session.pin)


def test_distinct_standalone_owner_reads_reuse_checked_descriptor(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import CATALOG_NAMESPACE
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        cat = session._identity_coordinator.catalog
        first = cat.read_owner_identity(session.pin, OWNER)
        assert first.exists
        with patch.object(cat, '_read', wraps=cat._read) as reads:
            second = cat.read_owner_identity(session.pin, (OWNER[0], (2, 'craft')))
        assert second.exists and second.owner != first.owner
        assert not [call for call in reads.call_args_list if call.args[1] == CATALOG_NAMESPACE]
        assert cat.owner_cache_diagnostics()['descriptor_entries'] == 1
        assert not session.store.db.in_transaction


@pytest.mark.parametrize('context', ['borrowed', 'callback', 'busy', 'audited'])
def test_owner_scope_selection_preserves_original_fallbacks(tmp_path, context):
    from contextlib import nullcontext
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
    path, pair = ranked_fixture(tmp_path, size=4)
    opened = (open_audited_proof_world_session(path, rules_id='private-catalog-copy', expected_commitment=pair[1])
              if context == 'audited' else fast_open(path, pair))
    with opened as session:
        st = session.store
        if context == 'callback':
            st.db.set_trace_callback(lambda _: None)
            st.db.set_trace_callback(None)
        authority = st._world_proof_authority
        original = authority.busy
        if context == 'busy':authority.busy = True
        try:
            outer = st.read_snapshot(session.pin) if context == 'borrowed' else nullcontext()
            with outer:
                with patch('ate_sim.persistence_validation_scope.checked_read_operation',
                           side_effect=AssertionError('fallback selected new scope')):
                    assert session._identity_coordinator.catalog.read_owner_identity(session.pin, OWNER).exists
        finally:
            authority.busy = original
