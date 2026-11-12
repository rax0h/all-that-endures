"""Only an owned closed proof read can reuse its validated snapshot facts."""
import sqlite3

import pytest

from ate_sim.incremental_store import StoreError
from ate_sim.persistence_validation_scope import checked_read_operation
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

OWNER = ('world.skills.skills', (1, 'craft'))
PATH = (('field', 'provenance'),)


def test_group_read_uses_bounded_epoch_sql_without_skipping_membership(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        sql = []
        st.db.set_trace_callback(sql.append)
        try:
            group = session._identity_coordinator.catalog.read_identity_group(session.pin, inc)
        finally:
            st.db.set_trace_callback(None)
        assert (OWNER[0], OWNER[1], PATH) in group.occurrences
        assert len(group.occurrences) == 2
        assert sum(x.lower().startswith('pragma data_version') for x in sql) <= 8
        assert not st.db.in_transaction


@pytest.mark.parametrize('command', [
    'UPDATE records SET payload_checksum=payload_checksum',
    'CREATE TEMP TABLE shadow(value)', 'COMMIT', 'ROLLBACK', 'SAVEPOINT change',
    'PRAGMA writable_schema=ON', "ATTACH ':memory:' AS extra",
])
def test_closed_scope_refuses_every_write_or_transaction_control(tmp_path, command):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        with pytest.raises((StoreError, sqlite3.Error)):
            with checked_read_operation(st, session.pin, _proof_group=True) as scope:
                assert scope.can_reuse(st, session.pin)
                try:
                    st.db.execute(command)
                except sqlite3.Error:
                    pass  # A swallowed denial may never leave a valid certificate.
                scope.can_reuse(st, session.pin)
        assert not st.db.in_transaction
        assert getattr(st.db, '_native_write_guard', None) is None
        assert st.db._known_authorizer is None


def test_closed_scope_reuses_immutable_facts_only_within_its_operation(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        with checked_read_operation(st, session.pin, _proof_group=True) as scope:
            scope.remember('fixture', b'key', (1, b'proof'))
            assert scope.lookup('fixture', b'key') == (1, b'proof')
            assert scope.entries == 1
            assert scope.bytes <= scope.byte_limit
        assert scope.entries == scope.bytes == 0
        assert not scope.can_reuse(st, session.pin)
        with checked_read_operation(st, session.pin, _proof_group=True) as next_scope:
            assert next_scope is not scope
            assert next_scope.lookup('fixture', b'key') is None


@pytest.mark.parametrize('drift', ['codec', 'hook', 'factory', 'callback-write'])
def test_closed_scope_rejects_context_changes_and_callback_writes(tmp_path, drift):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        original_codec, original_hook = st.codec, st._phase_hook
        with pytest.raises((StoreError, sqlite3.Error)):
            with checked_read_operation(st, session.pin, _proof_group=True) as scope:
                if drift == 'codec':
                    st.codec = object()
                elif drift == 'hook':
                    st._phase_hook = lambda _: None
                elif drift == 'factory':
                    st.db.row_factory = lambda cursor, row: row
                else:
                    st.db.set_trace_callback(lambda _: st.db.execute('DELETE FROM records'))
                scope.can_reuse(st, session.pin)
        st.codec, st._phase_hook = original_codec, original_hook
        st.db.set_trace_callback(None)
        assert not st.db.in_transaction


def test_borrowed_snapshot_never_mints_closed_proof_certificate(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        with st.read_snapshot(session.pin):
            with checked_read_operation(st, session.pin, _proof_group=True) as scope:
                assert type(scope).__name__ == 'ValidationScope'
                assert not scope.can_reuse(st, session.pin)
        assert not st.db.in_transaction


def test_preexisting_callback_cannot_write_through_a_closed_read(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        before = st.db.execute('SELECT count(*) FROM records').fetchone()[0]
        def trace(sql):
            if 'closed_read_attack' in sql:
                st.db.execute('DELETE FROM records')
        st.db.set_trace_callback(trace)
        try:
            with pytest.raises((StoreError, sqlite3.Error)):
                with checked_read_operation(st, session.pin, _proof_group=True):
                    st.db.execute("SELECT 'closed_read_attack'").fetchone()
        finally:
            st.db.set_trace_callback(None)
        assert st.db.execute('SELECT count(*) FROM records').fetchone()[0] == before
        assert not st.db.in_transaction


def test_closed_scope_cache_respects_existing_entry_and_byte_limits(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        with checked_read_operation(st, session.pin, _proof_group=True, byte_limit=1024) as scope:
            for i in range(600):
                scope.remember('fixture', i, (i, b'small-proof'))
            scope.remember('fixture', 'oversized', b'x' * 2048)
            assert scope.entries <= 256 and scope.bytes <= 1024
            assert scope.lookup('fixture', 'oversized') is None
