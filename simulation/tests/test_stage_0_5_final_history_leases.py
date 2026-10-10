"""Independent child leases pin history across publisher advances."""
import gc
import pytest

from simulation.ate_sim.incremental_store import StoreConflictError
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.tests.test_persistence_lazy_store import make_store, commit


class Alias:
    pass


def store_fixture(tmp_path):
    store = make_store(tmp_path / 'leases.sqlite')
    pin = store.capture_pin()
    result = commit(store, pin, 'initial', (VersionChange('history', 1, 'old'),), namespaces=('history',))
    return store, result.pin


def test_independent_lease_clones_a_checked_old_generation_and_releases_atomically(tmp_path):
    store, publisher = store_fixture(tmp_path)
    try:
        old = store.capture_pin(source_pin=publisher)
        result = commit(store, publisher, 'advance', (VersionChange('history', 1, 'new'),), position=2, namespaces=('history',))
        publisher = result.pin
        other = store.capture_pin(source_pin=old)
        assert old.token != other.token != publisher.token
        assert old.captured_head == other.captured_head < publisher.captured_head
        assert store.read_version(other, 'history', 1, expected_record_schema=1).value == 'old'
        def fail(at):
            if at == 'before_pin_release_commit':
                raise OSError('release rollback')
        store._phase_hook = fail
        with pytest.raises(OSError, match='rollback'):
            store.release_pins((old, other, publisher))
        store._phase_hook = lambda _at: None
        assert store.read_version(other, 'history', 1, expected_record_schema=1).value == 'old'
        assert store.read_version(publisher, 'history', 1, expected_record_schema=1).value == 'new'
        store.release_pins((old, other, publisher))
        assert store.db.execute('SELECT count(*) FROM generation_pins').fetchone()[0] == 0
    finally:
        store.close()


def test_pool_shares_one_generation_pin_and_defers_gc_database_work(tmp_path):
    from simulation.ate_sim.persistence_history_leases import HistoryLeasePool
    store, publisher = store_fixture(tmp_path)
    try:
        pool = HistoryLeasePool(store)
        aliases = [Alias() for _ in range(100)]
        for alias in aliases:
            assert pool.acquire(alias, publisher).captured_head == publisher.captured_head
        assert pool.diagnostics()['generations'] == 1
        assert pool.diagnostics()['aliases'] == 100
        assert store.db.execute('SELECT count(*) FROM generation_pins').fetchone()[0] == 2
        del alias
        aliases.clear()
        gc.collect()
        assert pool.diagnostics()['aliases'] == 0
        # Weak callbacks queue release; no transaction in arbitrary GC context.
        assert store.db.execute('SELECT count(*) FROM generation_pins').fetchone()[0] == 2
        pool.drain()
        assert store.db.execute('SELECT count(*) FROM generation_pins').fetchone()[0] == 1
        assert pool.diagnostics()['generations'] == 0
        pool.close_with(publisher)
        assert store.db.execute('SELECT count(*) FROM generation_pins').fetchone()[0] == 0
    finally:
        store.close()


def test_pool_revival_releases_only_alias_pin_and_keeps_other_aliases(tmp_path):
    from simulation.ate_sim.persistence_history_leases import HistoryLeasePool
    store, publisher = store_fixture(tmp_path)
    try:
        pool = HistoryLeasePool(store)
        first, second = Alias(), Alias()
        pin = pool.acquire(first, publisher)
        assert pool.acquire(second, publisher) == pin
        pool.release(first)
        assert pool.pin_for(first) is None
        assert pool.pin_for(second) == pin
        pool.release(second)
        pool.drain()
        assert pool.diagnostics()['generations'] == 0
        assert store.read_version(publisher, 'history', 1, expected_record_schema=1).value == 'old'
        with pytest.raises(StoreConflictError):
            store.capture_pin(source_pin=pin)
        pool.close_with(publisher)
    finally:
        store.close()


def test_group_release_uses_one_maintenance_budget_for_all_pins(tmp_path):
    store = make_store(tmp_path / 'budget.sqlite')
    try:
        publisher = store.capture_pin()
        publisher = commit(store, publisher, 'first',
            tuple(VersionChange('history', key, 'old') for key in range(600)), namespaces=('history',)).pin
        old = store.capture_pin(source_pin=publisher)
        publisher = commit(store, publisher, 'second',
            tuple(VersionChange('history', key, 'new') for key in range(600)), position=2, namespaces=('history',)).pin
        other = store.capture_pin()
        before = store.diagnostics().maintenance_removed_rows
        store.release_pins((old, other, publisher))
        removed = store.diagnostics().maintenance_removed_rows - before
        assert 0 < removed <= 256
        assert store.db.execute('SELECT count(*) FROM generation_pins').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM lazy_record_versions WHERE valid_to IS NOT NULL').fetchone()[0] > 0
    finally:
        store.close()


def test_snapshot_pool_preserves_existing_generation_pressure_contract(tmp_path):
    from simulation.ate_sim.persistence_history_leases import HistoryLeasePool
    from simulation.ate_sim.persistence_lazy_store import GenerationPressureError
    store, publisher = store_fixture(tmp_path)
    try:
        pool = HistoryLeasePool(store)
        alias = Alias()
        pool.acquire(alias, publisher)
        publisher = commit(store, publisher, 'second', (VersionChange('history', 1, 'new'),),
                           position=2, namespaces=('history',)).pin
        with pytest.raises(GenerationPressureError):
            commit(store, publisher, 'third', (VersionChange('history', 1, 'third'),),
                   position=3, namespaces=('history',))
        assert store.read_version(publisher, 'history', 1, expected_record_schema=1).value == 'new'
        pool.release(alias)
        pool.drain()
        publisher = commit(store, publisher, 'third-after-release', (VersionChange('history', 1, 'third'),),
                           position=3, namespaces=('history',)).pin
        pool.close_with(publisher)
    finally:
        store.close()
