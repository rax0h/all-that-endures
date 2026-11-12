"""Independent probes for fresh-admission immutable descriptor facts."""

import pytest

from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

OWNER = ('world.skills.skills', (1, 'craft'))
PATH = (('field', 'provenance'),)

def warmed(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    session = fast_open(path, pair)
    st, cat = session.store, session._identity_coordinator.catalog
    inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
    cat.read_identity_group(session.pin, inc)
    assert cat.owner_cache_diagnostics()['descriptor_entries'] == 1
    return session, cat, inc

def test_trace_registry_mutation_and_unregister_never_hit_old_fact(tmp_path):
    session, cat, inc = warmed(tmp_path)
    with session:
        st = session.store
        registry = st.codec._record_by_name
        original = registry['core.Ref/v1']
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        attacked = []
        def trace(sql):
            if attacked or 'SELECT 1 FROM sqlite_temp_schema' not in sql:
                return
            registry['core.Ref/v1'] = object
            attacked.append(sql)
        st.db.set_trace_callback(trace)
        try:
            try:
                cat.read_identity_group(session.pin, inc)
            except StoreError:
                pass
            assert attacked
            assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        finally:
            registry['core.Ref/v1'] = original
            st.db.set_trace_callback(None)
        cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        assert cat.owner_cache_diagnostics()['descriptor_entries'] == 0
        assert not st.db.in_transaction

def test_released_pin_cannot_use_warmed_descriptor(tmp_path):
    session, cat, inc = warmed(tmp_path)
    with session:
        st = session.store
        st.release_pin(session.pin)
        with pytest.raises(StoreError):
            cat.read_identity_group(session.pin, inc)
        assert not st.db.in_transaction

def test_physical_descriptor_corruption_fails_even_after_epoch_acknowledgement(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import CATALOG_NAMESPACE
    session, cat, inc = warmed(tmp_path)
    with session:
        st = session.store
        changed = st.db.execute(
            'UPDATE lazy_record_versions SET payload=? WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
            (b'broken-descriptor', CATALOG_NAMESPACE, st.codec.encode(0))).rowcount
        assert changed == 1
        st.db.commit()
        authority = st._world_proof_authority
        authority.epoch = authority._epoch()
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        with pytest.raises(StoreError):
            cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        assert not st.db.in_transaction

def test_ddl_replacement_with_restored_schema_epoch_cannot_hit_warmed_fact(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import CATALOG_NAMESPACE
    session, cat, inc = warmed(tmp_path)
    with session:
        st = session.store
        before = st._world_proof_authority._epoch()
        indexes = [row[0] for row in st.db.execute(
            "SELECT sql FROM sqlite_schema WHERE tbl_name='lazy_record_versions' AND type='index' AND sql IS NOT NULL")]
        columns = [row[1] for row in st.db.execute('PRAGMA table_info(lazy_record_versions)')]
        # Metadata discovery may itself conservatively advance the public SQL
        # revision. Rewarm afterwards so only the attack can invalidate it.
        cat.read_identity_group(session.pin, inc)
        assert cat.owner_cache_diagnostics()['descriptor_entries'] == 1
        before = st._world_proof_authority._epoch()
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

def test_descriptor_fact_and_owner_entries_compete_within_one_entry(tmp_path):
    session, _cat, inc = warmed(tmp_path)
    with session:
        st = session.store
        cat = IdentityCatalog(st, occurrence_limit=1, byte_limit=65536)
        group = cat.read_identity_group(session.pin, inc)
        try:
            assert len(group.occurrences) == 2
            first = cat.owner_cache_diagnostics()
            assert first['descriptor_entries'] == 1
            assert first['entries'] <= 1 and first['bytes'] <= 65536
            owner = cat.read_owner_identity(session.pin, OWNER)
            if hasattr(owner.occurrences, 'close'):
                owner.occurrences.close()
            stats = cat.owner_cache_diagnostics()
            assert stats['entries'] <= stats['entry_limit'] == 1
            assert stats['bytes'] <= stats['byte_limit'] == 65536
            assert cat._descriptor_fact_bytes + cat._owner_cache_bytes == stats['bytes']
        finally:
            for value in (group.occurrences, group.links):
                if hasattr(value, 'close'):
                    value.close()

def test_callback_runs_on_full_fallback_without_new_guard(tmp_path):
    session, cat, inc = warmed(tmp_path)
    with session:
        st = session.store
        seen = []
        st.db.set_trace_callback(seen.append)
        before = cat.owner_cache_diagnostics()['descriptor_hits']
        second = cat.read_identity_group(session.pin, inc)
        st.db.set_trace_callback(None)
        assert len(second.occurrences) == 2
        assert cat.owner_cache_diagnostics()['descriptor_hits'] == before
        assert any(sql.lower().startswith('pragma data_version') for sql in seen)
        assert getattr(st.db, '_native_write_guard', None) is None
        assert st.db._known_authorizer is None
        assert not st.db.in_transaction
