"""Immutable descriptor facts require fresh owned native proof admission."""
import cProfile
import pstats
import sqlite3

import pytest

from ate_sim.incremental_store import StoreError
from ate_sim.persistence_validation_scope import checked_read_operation
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

OWNER = ('world.skills.skills', (1, 'craft'))
PATH = (('field', 'provenance'),)


def test_repeated_group_reads_reuse_descriptor_but_check_actual_group(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        cat = session._identity_coordinator.catalog
        inc = session.store.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        first = cat.read_identity_group(session.pin, inc)
        profile = cProfile.Profile()
        profile.enable()
        try:
            second = cat.read_identity_group(session.pin, inc)
        finally:
            profile.disable()
        assert second == first
        assert len(second.occurrences) == 2
        reads = 0
        for (file, _, name), value in pstats.Stats(profile).stats.items():
            if file.endswith('/persistence_lazy_identity_catalog.py') and name == '_read':
                reads += sum(v[1] for (_, _, caller), v in value[4].items() if caller == '_descriptor')
        assert reads == 0
        assert not session.store.db.in_transaction


@pytest.mark.parametrize('fault', ['local', 'external', 'rollback', 'temp-shadow', 'codec', 'registry', 'hook'])
def test_warmed_fact_does_not_bypass_context_drift(tmp_path, fault):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st, cat = session.store, session._identity_coordinator.catalog
        inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        cat.read_identity_group(session.pin, inc)
        if fault in ('local', 'external', 'rollback'):
            db = sqlite3.connect(path) if fault == 'external' else st.db
            if fault == 'rollback':db.execute('SAVEPOINT trial')
            db.execute("UPDATE records SET payload_checksum='descriptor-drift' WHERE namespace='world.seed'")
            if fault == 'rollback':db.execute('ROLLBACK TO trial');db.execute('RELEASE trial')
            else:db.commit()
            if db is not st.db:db.close()
        elif fault == 'temp-shadow':
            st.db.execute('CREATE TEMP TABLE lazy_record_versions(payload)')
        elif fault == 'codec':
            st.codec.decode = lambda _: None
        elif fault == 'registry':
            st.codec._record_by_name['core.Ref/v1'] = object
            before = cat.owner_cache_diagnostics()['descriptor_hits']
            cat.read_identity_group(session.pin, inc)
            assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
            from ate_sim.core import Ref
            st.codec._record_by_name['core.Ref/v1'] = Ref
            return
        else:
            original = st._phase_hook
            st._phase_hook = lambda _: None
            before = cat.owner_cache_diagnostics()['descriptor_hits']
            cat.read_identity_group(session.pin, inc)
            assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
            st._phase_hook = original
            return
        try:
            with pytest.raises(StoreError):cat.read_identity_group(session.pin, inc)
        finally:
            if fault == 'codec':del st.codec.decode
            if fault == 'registry':
                from ate_sim.core import Ref
                st.codec._record_by_name['core.Ref/v1'] = Ref
            if fault == 'temp-shadow':st.db.execute('DROP TABLE temp.lazy_record_versions')
        assert not st.db.in_transaction


def test_borrowed_and_audited_reads_do_not_use_descriptor_fact(tmp_path):
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st, cat = session.store, session._identity_coordinator.catalog
        inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        cat.read_identity_group(session.pin, inc)
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        with st.read_snapshot(session.pin):cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
    with open_audited_proof_world_session(path, rules_id='private-catalog-copy', expected_commitment=pair[1]) as session:
        cat = session._identity_coordinator.catalog
        inc = session.store.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_entries'] == 0


def test_descriptor_and_owner_facts_share_existing_limits_and_follow_save(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st, cat = session.store, session._identity_coordinator.catalog
        inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        cat.read_identity_group(session.pin, inc)
        stats = cat.owner_cache_diagnostics()
        assert stats['descriptor_entries'] == 1
        assert 0 < stats['descriptor_bytes'] <= 32768
        assert stats['bytes'] <= stats['byte_limit'] and stats['entries'] <= stats['entry_limit']
        session.skills[1, 'craft'].level = .5
        session.save()
        cat.read_identity_group(session.pin, inc)
        assert cat._descriptor_fact[0][3] == session.pin
        stats = cat.owner_cache_diagnostics()
        assert stats['bytes'] <= stats['byte_limit'] and stats['entries'] <= stats['entry_limit']


@pytest.mark.parametrize('method', ['blob', 'deserialize', 'enable-extension', 'load-extension'])
def test_opaque_connection_mutation_apis_disable_fact_reuse(tmp_path, method):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st, cat = session.store, session._identity_coordinator.catalog
        inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        cat.read_identity_group(session.pin, inc)
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        if method == 'blob':
            row = st.db.execute("SELECT rowid FROM store_metadata WHERE key='format_version'").fetchone()[0]
            with st.db.blobopen('store_metadata', 'value', row) as blob:
                assert blob.read() == b'7'
        elif method == 'deserialize':
            st.db.deserialize(st.db.serialize())
        elif method == 'enable-extension':
            st.db.enable_load_extension(True)
            st.db.enable_load_extension(False)
        else:
            with pytest.raises(sqlite3.Error):st.db.load_extension('/missing-ate-extension')
        cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        assert cat.owner_cache_diagnostics()['descriptor_entries'] == 0


def test_ddl_replacement_with_restored_schema_epoch_cannot_hit_warmed_fact(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import CATALOG_NAMESPACE
    path, pair = ranked_fixture(tmp_path, size=4)
    session = fast_open(path, pair)
    cat = session._identity_coordinator.catalog
    inc = session.store.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
    with session:
        st = session.store
        before = st._world_proof_authority._epoch()
        indexes = [row[0] for row in st.db.execute(
            "SELECT sql FROM sqlite_schema WHERE tbl_name='lazy_record_versions' AND type='index' AND sql IS NOT NULL")]
        columns = [row[1] for row in st.db.execute('PRAGMA table_info(lazy_record_versions)')]
        cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_entries'] == 1
        projection = ','.join(
            "CASE WHEN namespace='" + CATALOG_NAMESPACE + "' THEN X'00' ELSE payload END AS payload"
            if column == 'payload' else column for column in columns)
        st.db.execute('CREATE TABLE review_replacement AS SELECT ' + projection + ' FROM lazy_record_versions')
        st.db.execute('DROP TABLE lazy_record_versions')
        st.db.execute('ALTER TABLE review_replacement RENAME TO lazy_record_versions')
        for statement in indexes:
            st.db.execute(statement)
        st.db.execute('PRAGMA schema_version=' + str(before[4]))
        assert st._world_proof_authority._epoch() == before
        cached_accepted = False
        try:
            cat.read_identity_group(session.pin, inc)
            cached_accepted = True
        except StoreError:
            pass
        cat._descriptor_fact = None
        cat._descriptor_fact_bytes = 0
        with pytest.raises(StoreError):
            cat.read_identity_group(session.pin, inc)
        assert not cached_accepted, 'warmed descriptor skipped corruption despite equal coarse epoch'



def test_custom_cursor_history_disables_fact_reuse(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        cat = session._identity_coordinator.catalog
        inc = session.store.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        cat.read_identity_group(session.pin, inc)
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        class CallerCursor(sqlite3.Cursor):pass
        session.store.db.cursor(factory=CallerCursor).close()
        cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        assert cat.owner_cache_diagnostics()['descriptor_entries'] == 0


@pytest.mark.parametrize('sql, advances', [
    ('SELECT 1', False),
    ('WITH c(x) AS (VALUES(1)) SELECT x FROM c', False),
    ('WITH RECURSIVE c(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM c WHERE x<3) SELECT * FROM c', False),
    ('with c AS (SELECT 1) SELECT * FROM c', True),
    ('/* caller */ WITH c AS (SELECT 1) SELECT * FROM c', True),
    ('WITH c AS (SELECT 1) uPdAtE t SET x=2 WHERE 0 RETURNING x', True),
    ('WITH c AS (SELECT 1) INSERT INTO t SELECT 2 WHERE 0', True),
    ('WITH c AS (SELECT 1) DELETE FROM t WHERE 0 RETURNING x', True),
    ('WITH c AS (SELECT 1) REPLACE INTO t SELECT 2 WHERE 0', True),
    ("WITH c AS (SELECT 1) SELECT 'UPDATE'", True),
    ('WITH c AS (SELECT 1) SELECT 1 /* DELETE */', True),
    ('PRAGMA schema_version=1', True),
])
def test_public_sql_revision_conservatively_handles_ctes_and_comments(sql, advances):
    from ate_sim.persistence_sqlite_guard import GuardedConnection
    with sqlite3.connect(':memory:', factory=GuardedConnection) as db:
        db.execute('CREATE TABLE t(x)')
        db.execute('INSERT INTO t VALUES(1)')
        before = db._schema_statement_generation
        list(db.execute(sql))
        assert (db._schema_statement_generation > before) is advances
        assert db.execute('SELECT x FROM t').fetchall() == [(1,)]


def test_cursor_scripts_always_advance_revision_including_failed_scripts():
    from ate_sim.persistence_sqlite_guard import GuardedConnection
    with sqlite3.connect(':memory:', factory=GuardedConnection) as db:
        cursor = db.cursor()
        before = db._schema_statement_generation
        cursor.executescript('SELECT 1; SELECT 2;')
        assert db._schema_statement_generation > before
        before = db._schema_statement_generation
        with pytest.raises(sqlite3.Error):cursor.executescript('not valid sql')
        assert db._schema_statement_generation > before
