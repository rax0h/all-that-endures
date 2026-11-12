"""Independent closed-read trust-boundary probes; no production mutation."""
import inspect
import sqlite3
from pathlib import Path

import pytest

from ate_sim.incremental_store import StoreError
from ate_sim.persistence_proof_read_scope import ClosedProofReadScope
from ate_sim.persistence_validation_scope import checked_read_operation
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

OWNER = ('world.skills.skills', (1, 'craft'))
PATH = (('field', 'provenance'),)

@pytest.mark.parametrize('sql', ['COMMIT', 'ROLLBACK', 'SAVEPOINT prior'])
def test_prepared_transaction_statements_are_reauthorized(tmp_path, sql):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        st.db.execute('BEGIN')
        st.db.execute(sql)
        if st.db.in_transaction:
            st.db.rollback()
        with pytest.raises(StoreError):
            with checked_read_operation(st, session.pin, _proof_group=True) as scope:
                assert type(scope) is ClosedProofReadScope
                with pytest.raises(sqlite3.DatabaseError):
                    st.db.execute(sql)
                scope.lookup('absent', ())
        assert not st.db.in_transaction
        assert st.db._native_write_guard is None

def test_previous_authorizer_restored_on_success_and_exception(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        seen = []
        def authorize(*args):
            seen.append(args[0])
            return sqlite3.SQLITE_OK
        st.db.set_authorizer(authorize)
        for fail in (False, True):
            try:
                with checked_read_operation(st, session.pin, _proof_group=True) as scope:
                    assert type(scope) is ClosedProofReadScope
                    st.db.execute('SELECT 739').fetchone()
                    if fail:
                        raise LookupError('controlled body exception')
            except LookupError:
                assert fail
            assert st.db._known_authorizer is authorize
            assert st.db._native_write_guard is None
            assert st._validation_scope is None
            assert not st.db.in_transaction
        assert sqlite3.SQLITE_SELECT in seen
        st.db.set_authorizer(None)

def test_swallowed_trace_registry_mutation_poisons_scope(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        registry = st.codec._record_by_name
        def trace(sql):
            if 'mutation_probe' in sql:
                registry['review-only'] = object
        st.db.set_trace_callback(trace)
        try:
            with pytest.raises(StoreError):
                with checked_read_operation(st, session.pin, _proof_group=True) as scope:
                    st.db.execute("SELECT 'mutation_probe'").fetchone()
                    registry.pop('review-only', None)
                    scope.lookup('absent', ())
        finally:
            registry.pop('review-only', None)
            st.db.set_trace_callback(None)
        assert not st.db.in_transaction

def test_external_commit_cannot_change_current_view_or_next_admission(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        external = sqlite3.connect(path, timeout=0.05)
        try:
            with checked_read_operation(st, session.pin, _proof_group=True) as scope:
                assert type(scope) is ClosedProofReadScope
                before = st.db.execute('SELECT count(*) FROM records').fetchone()[0]
                external.execute('DELETE FROM records')
                with pytest.raises(sqlite3.OperationalError, match='locked'):
                    external.commit()
                assert st.db.execute('SELECT count(*) FROM records').fetchone()[0] == before
                assert scope.can_reuse(st, session.pin)
            external.commit()
            with pytest.raises(StoreError):
                with checked_read_operation(st, session.pin, _proof_group=True):
                    pytest.fail('stale external epoch admitted')
        finally:
            external.close()

def test_specialized_metadata_and_facts_share_the_declared_limit(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        with checked_read_operation(st, session.pin, _proof_group=True, byte_limit=32768) as scope:
            assert type(scope) is ClosedProofReadScope
            assert scope.metadata_bytes > 0
            for i in range(600):
                scope.remember('review', i, (i, b'x' * 200))
                assert scope.bytes + scope.metadata_bytes <= scope.byte_limit
                assert scope.entries <= 256
            assert scope.entries > 0
            assert scope.lookup('review', 599) == (599, b'x' * 200)
            assert scope.lookup('review', 0) is None
        assert scope.bytes == scope.entries == 0

def test_interrupted_guard_activation_restores_connection(tmp_path, monkeypatch):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        original_activate = ClosedProofReadScope.activate
        def interrupted(self):
            original_activate(self)
            raise RuntimeError('controlled activation interruption')
        monkeypatch.setattr(ClosedProofReadScope, 'activate', interrupted)
        try:
            with pytest.raises((RuntimeError, sqlite3.Error)):
                with checked_read_operation(st, session.pin, _proof_group=True):
                    pytest.fail('interrupted setup yielded')
            assert st.db._native_write_guard is None
            assert st.db._known_authorizer is None
            assert not st.db.in_transaction
        finally:
            guard = getattr(st.db, '_native_write_guard', None)
            if guard is not None:
                guard.release()
            if st.db.in_transaction:
                st.db.rollback()

def test_final_custody_rejection_closes_unreturned_spills(tmp_path, monkeypatch):
    from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
    from ate_sim.persistence_lazy_spill import CheckedSpool
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        spools = []
        original_init = CheckedSpool.__init__
        original_check = ClosedProofReadScope.check
        def capture(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            spools.append(self)
        def fail_at_exit(self):
            frame = inspect.currentframe().f_back
            if frame.f_code.co_name == 'checked_read_operation':
                self.reject('controlled final custody rejection')
            return original_check(self)
        monkeypatch.setattr(CheckedSpool, '__init__', capture)
        monkeypatch.setattr(ClosedProofReadScope, 'check', fail_at_exit)
        try:
            with pytest.raises(StoreError):
                IdentityCatalog(st, occurrence_limit=1).read_identity_group(session.pin, inc)
            assert any(spool.spilled for spool in spools)
            assert all(spool._closed for spool in spools)
            assert all(not Path(spool.path).exists() for spool in spools if spool.path)
        finally:
            for spool in spools:
                spool.close()
