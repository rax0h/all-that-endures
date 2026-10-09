"""Shared ordinary GC bounds, checked old pins and SQL work with a backlog."""
import pytest

from simulation.ate_sim.incremental_store import Membership, StoreIntegrityError, _framed_sha
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange, INTERVAL_INDEXES
from simulation.tests.test_persistence_lazy_store import make_store, metadata, open_store

TABLES = ('lazy_query_versions', 'lazy_order_versions', 'lazy_record_versions',
          'lazy_namespace_state', 'lazy_identity_occurrence_versions', 'lazy_identity_state')


def eligible(store, floor):
    return sum(store.db.execute(f'SELECT count(*) FROM {table} WHERE valid_to<=?', (floor,)).fetchone()[0]
               for table in TABLES)


def bulk_generation(store, pin, generation, count=400):
    versions = tuple(VersionChange('people', n, (generation, n), reinsertion=generation > 1,
        memberships=(Membership('group', 0, n), Membership('all', True, n))) for n in range(1, count + 1))
    identities = tuple(IdentityOccurrenceChange('people', n, (), n + (generation - 1) * count)
                       for n in range(1, count + 1))
    return store.commit(pin, commit_token=f'g{generation}', version_changes=versions,
        identity_changes=identities, next_incarnation_id=count * generation + 1,
        changes=(), new_segments=(), metadata=metadata(generation, ('people',))).pin


def test_release_pin_reclaims_at_most_256_rows_total_and_reports_backlog(tmp_path):
    with make_store(tmp_path / 'release.sqlite') as store:
        pin = bulk_generation(store, store.capture_pin(), 1)
        old = store.capture_pin()
        pin = bulk_generation(store, pin, 2)
        assert store.read_version(old, 'people', 1, expected_record_schema=1).value == (1, 1)
        before = eligible(store, 2)
        assert before > 1000
        store.release_pin(old)
        after = eligible(store, 2)
        assert 0 < before - after <= 256
        report = store.verify_all()
        assert report['expired_rows_pending_maintenance'] == after
        assert store.read_version(pin, 'people', 1, expected_record_schema=1).value == (2, 1)
        assert store.read_identity_occurrence(pin, 'people', 1, ()).incarnation_id == 401


def test_commit_reclaims_at_most_256_and_explicit_maintenance_makes_progress(tmp_path):
    with make_store(tmp_path / 'commit.sqlite') as store:
        pin = bulk_generation(store, store.capture_pin(), 1)
        before = eligible(store, 2)
        pin = bulk_generation(store, pin, 2)
        # The new generation creates exactly these obsolete rows.
        total_closed = eligible(store, 2)
        assert total_closed > 1000
        before = total_closed
        pin = store.commit(pin, commit_token='ordinary', version_changes=(), changes=(), new_segments=(),
            metadata=metadata(3, ('people',))).pin
        assert before - eligible(store, 3) <= 256
        iterations = 0
        while eligible(store, 3):
            before = eligible(store, 3)
            removed = store.maintenance(row_budget=64)
            assert 0 < removed <= 64
            assert before - eligible(store, 3) == removed
            iterations += 1
            assert iterations < 40
        store.verify_all()


def test_explicit_maintenance_preserves_pin_receipt_and_old_payloads(tmp_path):
    with make_store(tmp_path / 'pins.sqlite') as store:
        pin = bulk_generation(store, store.capture_pin(), 1, count=20)
        old = store.capture_pin()
        pin = bulk_generation(store, pin, 2, count=20)
        assert store.maintenance(row_budget=256) == 0
        assert store.read_version(old, 'people', 1, expected_record_schema=1).value == (1, 1)
        assert store.resolve_commit(pin, 'g2').pin == pin
        store.release_pin(old)
        assert store.read_version(pin, 'people', 1, expected_record_schema=1).value == (2, 1)


def vm_steps(store, query):
    steps = 0
    def tick():
        nonlocal steps
        steps += 1
        return 0
    store.db.set_progress_handler(tick, 1)
    try: result = query()
    finally: store.db.set_progress_handler(None, 0)
    return steps, result


@pytest.mark.parametrize('history', [1000, 10000])
def test_point_and_reverse_reads_do_not_scan_expired_backlog(tmp_path, history):
    with make_store(tmp_path / 'backlog.sqlite') as store:
        pin = store.capture_pin()
        # Build genuine checksummed versions; suspend reclamation only in this
        # fixture to isolate read work from the maintenance schedule.
        actual_cleanup = store._cleanup_expired
        store._cleanup_expired = lambda floor, **kw: 0
        for year in range(1, history + 1):
            pin = store.commit(pin, commit_token=year,
                version_changes=(VersionChange('people', 1, year, reinsertion=year > 1,
                    memberships=(Membership('fixed', True, 0),)),),
                identity_changes=(IdentityOccurrenceChange('people', 1, (), year % 2 + 1),),
                next_incarnation_id=year + 3, changes=(), new_segments=(),
                metadata=metadata(year, ('people',))).pin
        key = store.codec.encode(1)
        path = store.codec.encode(())
        with store.read_snapshot(pin):
            queries = (
                lambda: store._visible_record_row(history, 'people', key),
                lambda: store._visible_order('people', key, history),
                lambda: store._namespace_state_at('people', history),
                lambda: store._identity_state_at(history),
                lambda: store._visible_identity_occurrence(history, 'people', key, path),
                lambda: store.identity_occurrences_for_incarnation(pin, 1),
                lambda: store.identity_occurrences_for_owner(pin, 'people', 1),
                lambda: store.query_memberships(pin, 'people', 'fixed', True, limit=1),
            )
            for query in queries:
                steps, result = vm_steps(store, query)
                assert result is not None
                # SQLite VM work is measured independently of returned rows.
                assert steps < 2000, (history, steps)
        store._cleanup_expired = actual_cleanup
        steps, result = vm_steps(store, lambda: store.commit(pin, commit_token='scalar',
            version_changes=(VersionChange('people', 1, history + 1,
                memberships=(Membership('fixed', True, 0),)),), changes=(), new_segments=(),
            metadata=metadata(history + 1, ('people',))))
        assert result.outcome == 'committed'
        # No archive namespace-history inventory during an ordinary save.
        assert steps < 30000, (history, steps)


def test_invalid_maintenance_budget_is_rejected(tmp_path):
    with make_store(tmp_path / 'budget.sqlite') as store:
        for budget in (-1, 257, True, 1.0):
            with pytest.raises(ValueError): store.maintenance(row_budget=budget)


def test_eager_owner_witness_source_probe_does_not_scan_lazy_payload_versions(tmp_path):
    from simulation.ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, OWNER_NAMESPACE
    with make_store(tmp_path / 'owner-backlog.sqlite') as store:
        pin = store.capture_pin()
        store._cleanup_expired = lambda floor, **kw: 0
        for year in range(1, 1001):
            pin = store.commit(pin, commit_token=year,
                version_changes=(VersionChange('world.people', 1, year),),
                changes=(), new_segments=(), metadata=metadata(year, ('world.people',))).pin
        payload_commit = _framed_sha(b'lazy-payload-v1', store.codec.encode(1000))
        header = ('identity-owner/v1', True, 'lazy', 1000, 1, payload_commit,
                  None, 0, _framed_sha(b'identity-owner-empty-v1'))
        pin = store.commit(pin, commit_token='witness',
            version_changes=(VersionChange(OWNER_NAMESPACE, ('world.people', 1), header),),
            changes=(), new_segments=(), metadata=metadata(1001, ('world.people',))).pin
        store.reset_diagnostics()
        steps, actual = vm_steps(store, lambda: IdentityCatalog(store)._owner(pin, ('world.people', 1)))
        assert actual == header
        assert steps < 2000, steps
        assert store.diagnostics().payload_reads == 1  # The compact owner witness only.


def test_legacy_index_layout_is_not_upgraded_on_open(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    with make_store(path) as store:
        pin = bulk_generation(store, store.capture_pin(), 1, count=2)
        for name in INTERVAL_INDEXES: store.db.execute(f'DROP INDEX {name}')
        store.db.commit()
        before = store.db.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
    with open_store(path) as store:
        assert not store._interval_indexes
        pin = store.capture_pin()
        assert store.read_version(pin, 'people', 1, expected_record_schema=1).value == (1, 1)
        assert store.identity_occurrences_for_incarnation(pin, 1) == (('people', 1, ()),)
        assert before == store.db.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall()
        store.verify_all()


def test_explicit_maintenance_rollback_keeps_rows_and_operational_receipts(tmp_path):
    with make_store(tmp_path / 'rollback.sqlite') as store:
        pin = bulk_generation(store, store.capture_pin(), 1)
        pin = bulk_generation(store, pin, 2)
        before = eligible(store, 2)
        assert before > 256
        original = store._commit_sqlite
        store._commit_sqlite = lambda: (_ for _ in ()).throw(OSError('maintenance commit failure'))
        with pytest.raises(OSError, match='maintenance commit failure'):
            store.maintenance(row_budget=64)
        store._commit_sqlite = original
        assert eligible(store, 2) == before
        assert store.resolve_commit(pin, 'g2').pin == pin
        assert store.maintenance(row_budget=64) == 64
        assert eligible(store, 2) == before - 64
        store.verify_all()


def test_full_verification_checks_expired_payload_checksums_in_backlog(tmp_path):
    with make_store(tmp_path / 'expired-corruption.sqlite') as store:
        pin = bulk_generation(store, store.capture_pin(), 1)
        pin = bulk_generation(store, pin, 2)
        rowid = store.db.execute('SELECT rowid FROM lazy_record_versions WHERE valid_to<=2 LIMIT 1').fetchone()[0]
        store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE rowid=?', (b'corrupt', rowid))
        store.db.commit()
        with pytest.raises(StoreIntegrityError): store.verify_all()


def test_ordinary_fixed_work_churn_makes_bounded_reclamation_progress(tmp_path):
    with make_store(tmp_path / 'churn.sqlite') as store:
        pin = bulk_generation(store, store.capture_pin(), 1)
        pin = bulk_generation(store, pin, 2)
        previous = eligible(store, 2)
        assert previous > 1000
        for generation in range(3, 15):
            before = store.diagnostics().maintenance_removed_rows
            pin = store.commit(pin, commit_token=f'fixed-{generation}',
                version_changes=(VersionChange('people', 1, generation,
                    memberships=(Membership('group', 0, 1), Membership('all', True, 1))),),
                changes=(), new_segments=(), metadata=metadata(generation, ('people',))).pin
            assert store.diagnostics().maintenance_removed_rows - before <= 256
            remaining = eligible(store, generation)
            assert remaining < previous
            assert store.read_version(pin, 'people', 1, expected_record_schema=1).value == generation
            previous = remaining
            if remaining == 0: break
        assert previous == 0
        store.verify_all()
