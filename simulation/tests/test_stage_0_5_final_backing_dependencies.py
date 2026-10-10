"""Backing protection follows a publisher token, not an older snapshot pin."""
import gc
import importlib

import pytest

from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreConflictError
from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList
from simulation.ate_sim.persistence_lazy_store import VersionChange, GenerationPressureError
from simulation.tests.test_persistence_lazy_store import make_store, metadata


def module():
    return importlib.import_module('simulation.ate_sim.persistence_history_dependencies')


def publish(pool, *, changes=(), token='save'):
    delta = pool.prepare_delta()
    result = pool.store.commit(pool.pin, commit_token=token,
        version_changes=tuple(changes) + delta.decode(pool.store.codec)[0],
        changes=(), new_segments=(), metadata=metadata(pool.pin.captured_head + 1, ()))
    pool.validate_publication(delta, result.pin)
    pool.accept_delta(delta, result.pin)
    return result.pin


@pytest.mark.parametrize('history', [1000, 10000])
def test_private_orphan_survives_many_saves_without_old_snapshot_pressure(tmp_path, history):
    mod = module()
    with make_store(tmp_path / 'orphan.sqlite') as store:
        pool = mod.BackingDependencyPool(store, store.capture_pin())
        alias = LazyHistoryList(store, pool.pin, 1, initial_values=range(history))
        pool.acquire(alias)
        pin = publish(pool, changes=alias.pending_changes(), token='initial')
        alias.accept_save(pin)
        alias[0] = -1  # Private state deliberately excluded from World writes.
        for number in range(12):
            pin = publish(pool, token=f'unrelated-{number}')
            alias._pin = pin
            alias._clear_cache()
            assert alias[0] == -1 and alias[-1] == history - 1
            assert mod.active_backing_dependencies(store, pin, 1) == (pool.token,)
            assert store.db.execute('SELECT COUNT(*) FROM generation_pins').fetchone()[0] == 1
        persisted = LazyHistoryList(store, pin, 1)
        assert persisted[0] == 0
        assert len(alias.pending_changes()) <= 1
        assert pool.diagnostics()['dependencies'] == 1


def test_weak_collection_defers_one_central_publication_and_reacquire_coalesces(tmp_path):
    mod = module()
    with make_store(tmp_path / 'gc.sqlite') as store:
        pool = mod.BackingDependencyPool(store, store.capture_pin())
        alias = LazyHistoryList(store, pool.pin, 1, initial_values=[1])
        pool.acquire(alias)
        pin = publish(pool, changes=alias.pending_changes(), token='initial')
        alias.accept_save(pin)
        del alias
        gc.collect()
        assert mod.active_backing_dependencies(store, pin, 1) == (pool.token,)
        alias = LazyHistoryList(store, pin, 1)
        pool.acquire(alias)
        assert not pool.prepare_delta().decode(store.codec)[0]
        pool.abort_delta()
        del alias
        gc.collect()
        delta = pool.prepare_delta()
        changes = delta.decode(store.codec)[0]
        assert len(changes) == 1 and changes[0].value == mod.dependency_value('list')
        pool.abort_delta()
        pin = publish(pool, token='collected')
        assert mod.active_backing_dependencies(store, pin, 1) == ()


def test_failed_commit_preserves_frozen_dependencies_and_exact_retry(tmp_path):
    mod = module()
    with make_store(tmp_path / 'fault.sqlite') as store:
        pool = mod.BackingDependencyPool(store, store.capture_pin())
        alias = LazyHistoryList(store, pool.pin, 1, initial_values=[1])
        pool.acquire(alias)
        delta = pool.prepare_delta()
        versions = alias.pending_changes() + delta.decode(store.codec)[0]
        def fail(phase):
            if phase == 'before_commit':
                raise OSError('before_commit')
        store._phase_hook = fail
        with pytest.raises(OSError):
            store.commit(pool.pin, commit_token='failed', version_changes=versions,
                changes=(), new_segments=(), metadata=metadata(1, ()))
        assert pool.prepare_delta() is delta
        with pytest.raises(StoreConflictError, match='current frozen'):
            pool.close(abandon_stale=True)
        assert not pool.closed and pool.prepare_delta() is delta
        with pytest.raises(StoreConflictError, match='frozen'):
            pool.acquire(LazyHistoryList(store, pool.pin, 2, initial_values=[]))
        store._phase_hook = lambda _: None
        # The central receipt must resolve the failed attempt before retry.
        store.resolve_commit(pool.pin, 'failed')
        pool.abort_delta()
        pin = publish(pool, changes=alias.pending_changes(), token='retry')
        assert mod.active_backing_dependencies(store, pin, 1) == (pool.token,)


def test_missing_dependency_after_publication_fails_before_acknowledgement(tmp_path):
    mod = module()
    with make_store(tmp_path / 'missing.sqlite') as store:
        pool = mod.BackingDependencyPool(store, store.capture_pin())
        alias = LazyHistoryList(store, pool.pin, 1, initial_values=[1])
        pool.acquire(alias)
        delta = pool.prepare_delta()
        result = store.commit(pool.pin, commit_token='initial',
            version_changes=alias.pending_changes() + delta.decode(store.codec)[0],
            changes=(), new_segments=(), metadata=metadata(1, ()))
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (mod.NAMESPACE,))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            pool.validate_publication(delta, result.pin)
        assert pool.prepare_delta() is delta


def test_releasing_publisher_pin_expires_dependency_without_another_generation(tmp_path):
    mod = module()
    with make_store(tmp_path / 'close.sqlite') as store:
        pool = mod.BackingDependencyPool(store, store.capture_pin())
        alias = LazyHistoryList(store, pool.pin, 1, initial_values=[1])
        pool.acquire(alias)
        pin = publish(pool, changes=alias.pending_changes(), token='initial')
        generation = pin.captured_head
        def fail(phase):
            if phase == 'before_pin_release_commit':
                raise OSError('release')
        store._phase_hook = fail
        with pytest.raises(OSError):
            pool.close()
        assert not pool.closed and mod.active_backing_dependencies(store, pin, 1)
        store._phase_hook = lambda _: None
        pool.close()
        assert pool.closed and store.generation == generation
        current = store.capture_pin()
        assert mod.active_backing_dependencies(store, current, 1) == ()
        assert len(mod.expired_backing_dependency_changes(store, current, 1)) == 1
        store.release_pin(current)


def test_unpublished_collection_drops_metadata_and_foreign_leases_are_rejected(tmp_path):
    mod = module()
    with make_store(tmp_path / 'left.sqlite') as left, make_store(tmp_path / 'right.sqlite') as right:
        pool = mod.BackingDependencyPool(left, left.capture_pin())
        for inc in range(1, 101):
            alias = LazyHistoryList(left, pool.pin, inc, initial_values=[])
            pool.acquire(alias)
        del alias
        gc.collect()
        assert not pool._new and pool.diagnostics()['dependencies'] == 0
        assert not pool.prepare_delta().version_bytes
        pool.abort_delta()
        foreign = LazyHistoryList(right, right.capture_pin(), 101, initial_values=[])
        with pytest.raises(StoreConflictError, match='publisher lease'):
            pool.acquire(foreign)


def test_dependency_roster_is_reused_across_publisher_close_and_reopen(tmp_path):
    mod = module()
    with make_store(tmp_path / 'churn.sqlite') as store:
        pool = mod.BackingDependencyPool(store, store.capture_pin())
        alias = LazyHistoryList(store, pool.pin, 1, initial_values=[1])
        pool.acquire(alias)
        pin = publish(pool, changes=alias.pending_changes(), token='initial')
        alias.accept_save(pin)
        pool.close()
        for n in range(12):
            pool = mod.BackingDependencyPool(store, store.capture_pin())
            alias = LazyHistoryList(store, pool.pin, 1)
            pool.acquire(alias)
            pin = publish(pool, token=f'churn-{n}')
            alias.accept_save(pin)
            assert mod.active_backing_dependencies(store, pin, 1) == (pool.token,)
            assert store.namespace_size(pin, mod.NAMESPACE) == 1
            pool.close()


def test_multiple_publishers_keep_the_existing_snapshot_pressure_contract(tmp_path):
    mod = module()
    with make_store(tmp_path / 'readers.sqlite') as store:
        first = mod.BackingDependencyPool(store, store.capture_pin())
        left = LazyHistoryList(store, first.pin, 1, initial_values=[1, 2])
        first.acquire(left)
        pin = publish(first, changes=left.pending_changes(), token='initial')
        left.accept_save(pin)
        second = mod.BackingDependencyPool(store, store.capture_pin())
        right = LazyHistoryList(store, second.pin, 1)
        second.acquire(right)
        pin = publish(second, token='second')
        right.accept_save(pin)
        assert set(mod.active_backing_dependencies(store, pin, 1)) == {first.token, second.token}
        assert list(left) == [1, 2]
        delta = second.prepare_delta()
        with pytest.raises(GenerationPressureError):
            store.commit(pin, commit_token='blocked', version_changes=delta.decode(store.codec)[0],
                changes=(), new_segments=(), metadata=metadata(3, ()))
        second.abort_delta()
        first.close()
        assert mod.active_backing_dependencies(store, pin, 1) == (second.token,)
        publish(second, token='unblocked')


def test_missing_or_malformed_required_dependency_authority_is_corruption(tmp_path):
    mod = module()
    with make_store(tmp_path / 'bad.sqlite') as store:
        pin = store.capture_pin()
        with pytest.raises(StoreIntegrityError, match='mandatory'):
            mod.active_backing_dependencies(store, pin, 1)
        pin = store.commit(pin, commit_token='bad-roster',
            version_changes=(VersionChange(mod.NAMESPACE, 1, (mod.TAG, 'list', (1,))),),
            changes=(), new_segments=(), metadata=metadata(1, ())).pin
        with pytest.raises(StoreIntegrityError, match='authority'):
            mod.active_backing_dependencies(store, pin, 1)


def test_collection_during_frozen_preparation_is_deferred_and_abort_reclaims_metadata(tmp_path):
    mod = module()
    with make_store(tmp_path / 'frozen-gc.sqlite') as store:
        pool = mod.BackingDependencyPool(store, store.capture_pin())
        alias = LazyHistoryList(store, pool.pin, 1, initial_values=[])
        pool.acquire(alias)
        delta = pool.prepare_delta()
        del alias
        gc.collect()
        assert pool.prepare_delta() is delta and len(delta.version_bytes) == 1
        pool.abort_delta()
        assert not pool._new and not pool.prepare_delta().version_bytes
