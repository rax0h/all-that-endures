"""Persisted certificates may be reused, never dirty placements or stale proof."""
import sqlite3

import pytest

from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreConflictError, StoreError
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.tests.test_persistence_lazy_store import make_store
from simulation.tests.test_stage_0_5_final_identity_catalog import catalog, groups, publish_delta, NS


def test_repeated_owner_read_reuses_proof_but_still_checks_pin(tmp_path):
    with make_store(tmp_path / 'reuse.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        first = cat.read_owner_identity(pin, (NS, 1))
        assert first.occurrences == (((), 1),)
        store.reset_diagnostics()
        for _ in range(5):
            assert cat.read_owner_identity(pin, (NS, 1)) == first
        diag = store.diagnostics()
        assert diag.payload_reads == 0
        assert diag.pin_rows >= 5


@pytest.mark.parametrize('external', [False, True])
@pytest.mark.parametrize('table,where', [
    ('lazy_identity_occurrence_versions', 'owner_namespace'),
    ('lazy_record_versions', 'namespace'),
    ('lazy_namespace_state', 'namespace'),
])
def test_warmed_owner_proof_detects_authority_loss(tmp_path, external, table, where):
    path = tmp_path / 'corrupt.sqlite'
    with make_store(path) as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        assert cat.read_owner_identity(pin, (NS, 1)).occurrences == (((), 1),)
        namespace = NS if table == 'lazy_identity_occurrence_versions' else catalog().OWNER_NAMESPACE
        db = sqlite3.connect(path) if external else store.db
        try:
            db.execute(f'DELETE FROM {table} WHERE {where}=?', (namespace,))
            db.commit()
        finally:
            if external: db.close()
        with pytest.raises((StoreIntegrityError, StoreError)):
            cat.read_owner_identity(pin, (NS, 1))


def test_warm_read_rejects_released_foreign_and_closed_store(tmp_path):
    with make_store(tmp_path / 'one.sqlite') as store, make_store(tmp_path / 'two.sqlite') as other:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        cat.read_owner_identity(pin, (NS, 1))
        foreign = groups(other)
        with pytest.raises(StoreConflictError): cat.read_owner_identity(foreign, (NS, 1))
        store.release_pin(pin)
        with pytest.raises(StoreConflictError): cat.read_owner_identity(pin, (NS, 1))
    with pytest.raises(StoreError): cat.read_owner_identity(pin, (NS, 1))


def test_warm_owner_reads_keep_old_and_successor_generations_distinct(tmp_path):
    with make_store(tmp_path / 'generation.sqlite') as store:
        writer = groups(store)
        old = store.capture_pin()
        cat = catalog().IdentityCatalog(store)
        assert cat.read_owner_identity(writer, (NS, 1)).occurrences == (((), 1),)
        writer = publish_delta(store, writer, (VersionChange(NS, 1, {'value': 'new'}),),
            (IdentityOccurrenceChange(NS, 1, (), 3),), 4)
        assert cat.read_owner_identity(writer, (NS, 1)).occurrences == (((), 3),)
        assert cat.read_owner_identity(old, (NS, 1)).occurrences == (((), 1),)
        assert cat.read_owner_identity(writer, (NS, 1)).occurrences == (((), 3),)


def test_nested_read_and_rollback_do_not_leak_cached_proof(tmp_path):
    with make_store(tmp_path / 'rollback.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        cat.read_owner_identity(pin, (NS, 1))
        with store.read_snapshot(pin):
            store.reset_diagnostics()
            assert cat.read_owner_identity(pin, (NS, 1)).occurrences == (((), 1),)
            assert store.diagnostics().payload_reads > 0  # borrowed snapshot bypasses
            store.db.execute('SAVEPOINT corrupt')
            store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=?', (NS,))
            with pytest.raises(StoreIntegrityError): cat.read_owner_identity(pin, (NS, 1))
            store.db.execute('ROLLBACK TO corrupt')
            store.db.execute('RELEASE corrupt')
            assert cat.read_owner_identity(pin, (NS, 1)).occurrences == (((), 1),)
        store.reset_diagnostics()
        assert cat.read_owner_identity(pin, (NS, 1)).occurrences == (((), 1),)
        assert store.diagnostics().payload_reads > 0  # no borrowed certificate escapes


def test_owner_cache_has_entry_occurrence_and_byte_bounds(tmp_path):
    with make_store(tmp_path / 'bounded.sqlite') as store:
        pin = groups(store, 180)
        cat = catalog().IdentityCatalog(store, occurrence_limit=3, byte_limit=8192)
        for key in range(1, 361):
            assert cat.read_owner_identity(pin, (NS, key)).occurrences == (((), (key + 1) // 2),)
            diag = cat.owner_cache_diagnostics()
            assert diag['entries'] <= 3 and diag['occurrences'] <= 3
            assert diag['bytes'] <= diag['byte_limit'] <= 8192
        store.reset_diagnostics()
        cat.read_owner_identity(pin, (NS, 1))
        assert store.diagnostics().payload_reads > 0  # earliest owner evicted


def test_oversize_owner_proof_is_not_retained(tmp_path):
    with make_store(tmp_path / 'oversize.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store, byte_limit=128)
        for _ in range(2):
            proof = cat.read_owner_identity(pin, (NS, 1))
            try: assert tuple(proof.occurrences) == (((), 1),)
            finally:
                if hasattr(proof.occurrences, 'close'): proof.occurrences.close()
        assert cat.owner_cache_diagnostics()['entries'] == 0


@pytest.mark.parametrize('external', [False, True])
def test_warmed_owner_proof_detects_payload_corruption(tmp_path, external):
    path = tmp_path / 'payload.sqlite'
    with make_store(path) as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        cat.read_owner_identity(pin, (NS, 1))
        db = sqlite3.connect(path) if external else store.db
        try:
            db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?',
                       (b'corrupt', catalog().OWNER_NAMESPACE))
            db.commit()
        finally:
            if external: db.close()
        with pytest.raises(StoreIntegrityError): cat.read_owner_identity(pin, (NS, 1))


def test_connection_and_codec_replacement_invalidate_warm_proof(tmp_path):
    path = tmp_path / 'connection.sqlite'
    with make_store(path) as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        cat.read_owner_identity(pin, (NS, 1))
        # Match SQLite counters deliberately: identity must independently qualify reuse.
        previous = store.db
        replacement = sqlite3.connect(path)
        replacement.execute('CREATE TEMP TABLE cache_counter(value)')
        replacement.executemany('INSERT INTO cache_counter VALUES (?)',
                                [(0,)] * previous.total_changes)
        replacement.commit()
        assert replacement.total_changes == previous.total_changes
        assert replacement.execute('PRAGMA data_version').fetchone() == previous.execute('PRAGMA data_version').fetchone()
        store.db = replacement
        try:
            store.reset_diagnostics()
            cat.read_owner_identity(pin, (NS, 1))
            assert store.diagnostics().payload_reads > 0
            cat.codec = type(cat.codec)()
            store.reset_diagnostics()
            cat.read_owner_identity(pin, (NS, 1))
            assert store.diagnostics().payload_reads > 0
        finally:
            store.db = previous
            replacement.close()


def test_store_decoder_replacement_invalidates_warm_proof(tmp_path):
    with make_store(tmp_path / 'decoder.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        cat.read_owner_identity(pin, (NS, 1))
        store.codec = type(store.codec)()
        store.reset_diagnostics()
        cat.read_owner_identity(pin, (NS, 1))
        assert store.diagnostics().payload_reads > 0


@pytest.mark.parametrize('table', ['lazy_identity_occurrence_versions', 'lazy_record_versions'])
def test_warmed_owner_proof_rejects_dropped_authority_table(tmp_path, table):
    with make_store(tmp_path / 'schema.sqlite') as store:
        pin = groups(store)
        cat = catalog().IdentityCatalog(store)
        cat.read_owner_identity(pin, (NS, 1))
        changes = store.db.total_changes
        version = store.db.execute('PRAGMA data_version').fetchone()
        store.db.execute(f'DROP TABLE {table}')
        store.db.commit()
        assert store.db.total_changes == changes
        assert store.db.execute('PRAGMA data_version').fetchone() == version
        with pytest.raises((StoreError, sqlite3.DatabaseError)):
            cat.read_owner_identity(pin, (NS, 1))
