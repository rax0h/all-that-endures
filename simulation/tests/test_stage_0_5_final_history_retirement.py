"""Backing retirement is indexed, incremental and protected by checked leases."""
import importlib

import pytest

from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList, HistoryReference, PAGE_NAMESPACE, HISTORY_CLASSES
from simulation.ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, initial_catalog_delta, GROUP_NAMESPACE
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.ate_sim.persistence_history_dependencies import BackingDependencyPool, NAMESPACE as DEPENDENCIES
from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
from simulation.tests.test_persistence_lazy_store import metadata
from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreConflictError

NS = 'world.currency.wallets'
PATH = (('key', 'history'),)


def module():
    return importlib.import_module('simulation.ate_sim.persistence_history_retirement')


def fixture(store, size, kind='list'):
    mod = module()
    pool = BackingDependencyPool(store, store.capture_pin())
    values = {key: key for key in range(size)} if kind == 'map' else range(size)
    alias = HISTORY_CLASSES[kind](store, pool.pin, 1, initial_values=values,
                                  **({'value_mode': 'native'} if kind == 'sequence' else {}))
    pool.acquire(alias)
    owner = VersionChange(NS, 1, {'history': HistoryReference(kind, 1)})
    placement = IdentityOccurrenceChange(NS, 1, PATH, 1)
    initial = initial_catalog_delta(store.codec, (owner,), (placement,), next_incarnation_id=2, generation=1)
    lease = pool.prepare_delta()
    pin = store.commit(pool.pin, commit_token='initial',
        version_changes=(owner,) + alias.pending_changes() + initial.decode(store.codec)[0] + lease.decode(store.codec)[0],
        identity_changes=(placement,), next_incarnation_id=2, changes=(), new_segments=(), metadata=metadata(1, (NS, 'world_identity_links'))).pin
    pool.accept_delta(lease, pin)
    alias.accept_save(pin)
    old = store.capture_pin()
    deleted = VersionChange(NS, 1, delete=True)
    placement = IdentityOccurrenceChange(NS, 1, PATH, delete=True)
    cat = IdentityCatalog(store)
    delta = cat.prepare_delta(pin, (deleted,), (placement,), next_incarnation_id=2)
    lease = pool.prepare_delta()
    job = mod.initial_retirement_change(kind, 1, generation=2)
    pin = store.commit(pin, commit_token='owner-deleted',
        version_changes=(deleted, job) + delta.decode(store.codec)[0] + lease.decode(store.codec)[0],
        identity_changes=(placement,), changes=(), new_segments=(), metadata=metadata(2, (NS, 'world_identity_links'))).pin
    pool.accept_delta(lease, pin)
    alias._pin = pin
    return pin, pool, alias, old


def step(store, pin, token, budget=8):
    mod = module()
    delta = mod.prepare_retirement_delta(store, pin, row_budget=budget)
    assert len(delta.decode(store.codec)[0]) <= budget
    pin = store.commit(pin, commit_token=token, version_changes=delta.decode(store.codec)[0],
        changes=(), new_segments=(), metadata=metadata(pin.captured_head + 1, (NS, 'world_identity_links'))).pin
    mod.validate_publication(store, delta, pin)
    return pin, delta


@pytest.mark.parametrize('size', [1000, 10000])
def test_old_pin_and_live_alias_block_reclamation_then_batches_make_progress(tmp_path, size):
    mod = module()
    with store_at(tmp_path / 'retire.sqlite') as store:
        pin, pool, alias, old = fixture(store, size)
        before = store.diagnostics()
        held = mod.prepare_retirement_delta(store, pin, row_budget=8)
        assert not any(v.namespace == PAGE_NAMESPACE for v in held.decode(store.codec)[0])
        assert store.diagnostics().payload_reads - before.payload_reads < 20
        assert LazyHistoryList(store, old, 1)[-1] == size - 1
        store.release_pin(old)
        assert not any(v.namespace == PAGE_NAMESPACE for v in
                       mod.prepare_retirement_delta(store, pin, row_budget=8).decode(store.codec)[0])
        pool.close()  # Sole publisher token's checked release expires its lease.
        pin = store.capture_pin()
        rounds = 0
        while store.contains_lazy_key(pin, mod.NAMESPACE, 1):
            pin, delta = step(store, pin, f'batch-{rounds}')
            rounds += 1
            assert rounds < 30
            assert not any(v.namespace == GROUP_NAMESPACE for v in delta.decode(store.codec)[0])
        assert rounds >= (size + 127) // 128 // 7
        assert store.namespace_size(pin, PAGE_NAMESPACE) == 0
        assert not store.contains_lazy_key(pin, DEPENDENCIES, 1)
        store.verify_all()


def test_catalog_does_not_compact_a_group_while_its_backing_job_is_pending(tmp_path):
    mod = module()
    with store_at(tmp_path / 'catalog.sqlite') as store:
        pin, pool, alias, old = fixture(store, 1000)
        store.release_pin(old)
        cat = IdentityCatalog(store)
        delta = cat.prepare_retirement_delta(pin)
        assert not any(v.namespace == GROUP_NAMESPACE and v.delete for v in delta.decode(store.codec)[0])
        assert store.contains_lazy_key(pin, mod.NAMESPACE, 1)


@pytest.mark.parametrize('kind', ['list', 'map', 'set', 'sequence'])
def test_all_backing_scopes_finish_then_catalog_header_can_compact(tmp_path, kind):
    mod = module()
    with store_at(tmp_path / 'kinds.sqlite') as store:
        pin, pool, alias, old = fixture(store, 8, kind)
        store.release_pin(old)
        pool.close()
        pin = store.capture_pin()
        for n in range(40):
            pin, delta = step(store, pin, f'kind-{n}', budget=4)
            if not store.contains_lazy_key(pin, mod.NAMESPACE, 1):
                break
        else:
            pytest.fail('backing retirement did not finish')
        assert all(store.namespace_size(pin, ns) == 0 for ns in mod.SCOPES[kind])
        cat = IdentityCatalog(store)
        delta = cat.prepare_retirement_delta(pin)
        assert any(v.namespace == GROUP_NAMESPACE and v.delete for v in delta.decode(store.codec)[0])
        pin = store.commit(pin, commit_token='compact', version_changes=delta.decode(store.codec)[0],
            changes=(), new_segments=(), metadata=metadata(pin.captured_head + 1, (NS, 'world_identity_links'))).pin
        cat.validate_publication(delta, pin)
        store.verify_all()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_frozen_retirement_batch_resolves_exactly_once(tmp_path, phase):
    mod = module()
    with store_at(tmp_path / 'fault.sqlite') as store:
        pin, pool, alias, old = fixture(store, 1000)
        store.release_pin(old)
        pool.close()
        pin = store.capture_pin()
        delta = mod.prepare_retirement_delta(store, pin, row_budget=4)
        versions = delta.decode(store.codec)[0]
        old_count = store.namespace_size(pin, PAGE_NAMESPACE)
        def fail(at):
            if at == phase:
                raise OSError(phase)
        store._phase_hook = fail
        with pytest.raises(OSError):
            store.commit(pin, commit_token='fault', version_changes=versions,
                changes=(), new_segments=(), metadata=metadata(pin.captured_head + 1, (NS, 'world_identity_links')))
        store._phase_hook = lambda _: None
        resolved = store.resolve_commit(pin, 'fault')
        if phase == 'before_commit':
            assert store.namespace_size(pin, PAGE_NAMESPACE) == old_count
            pin = store.commit(pin, commit_token='retry', version_changes=versions,
                changes=(), new_segments=(), metadata=metadata(pin.captured_head + 1, (NS, 'world_identity_links'))).pin
        else:
            pin = resolved.pin
        mod.validate_publication(store, delta, pin)
        assert store.namespace_size(pin, PAGE_NAMESPACE) == old_count - 3
        store.verify_all()


def test_scope_range_is_indexed_and_cannot_select_another_incarnation(tmp_path):
    mod = module()
    from simulation.ate_sim.persistence_lazy_nested_history import initial_list_changes
    with store_at(tmp_path / 'scope.sqlite') as store:
        pin = store.commit(store.capture_pin(), commit_token='initial',
            version_changes=initial_list_changes(1, range(1000), store.codec) +
                            initial_list_changes(11, range(10000), store.codec),
            changes=(), new_segments=(), metadata=metadata(1, ())).pin
        with store.read_snapshot(pin):
            keys = mod._scope_keys(store, pin, PAGE_NAMESPACE, 1, limit=4)
            assert len(keys) == 4 and all(key[0] == 1 for key in keys)
            prefix = store.codec.encode((1,))[:-2] + b','
            plan = store.db.execute(f'EXPLAIN QUERY PLAN SELECT typed_key FROM lazy_record_versions INDEXED BY {mod.SCOPE_INDEX} '
                'WHERE namespace=? AND valid_to IS NULL AND typed_key>=? AND typed_key<? ORDER BY typed_key LIMIT ?',
                (PAGE_NAMESPACE, prefix, prefix + b'\xff', 4)).fetchall()
            assert any(mod.SCOPE_INDEX in row[3] and 'SEARCH' in row[3] for row in plan)
            assert not any('TEMP' in row[3] for row in plan)


def test_retirement_rejects_stale_writer_and_missing_dependency_authority(tmp_path):
    mod = module()
    with store_at(tmp_path / 'bad.sqlite') as store:
        pin, pool, alias, old = fixture(store, 1000)
        with pytest.raises(StoreConflictError, match='current writer'):
            mod.prepare_retirement_delta(store, old)
        store.release_pin(old)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (DEPENDENCIES,))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            mod.prepare_retirement_delta(store, pin)
