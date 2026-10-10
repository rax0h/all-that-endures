"""Only changed backing groups force suppressed owner headers; plans stay exact."""
from dataclasses import replace

import pytest

from simulation.ate_sim.incremental_store import Membership, StoreIntegrityError, StoreConflictError, StoreFormatError, RecordChange
from simulation.ate_sim.core import Settlement
from simulation.ate_sim.persistence_lazy import _relative_get, _relative_set
from simulation.ate_sim.skills import SkillHistory
from simulation.ate_sim.persistence_lazy_identity import LazyIdentityRegistry, IncarnationId, Occurrence
from simulation.ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta
from simulation.ate_sim.persistence_lazy_identity_coordinator import IdentityCoordinator
from simulation.ate_sim.persistence_lazy_families import FAMILIES
from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList, HistoryReference
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
from simulation.tests.test_persistence_lazy_store import metadata

NS = 'world.skills.skills'
PATH = (('field', 'provenance'),)


def fixture(store, *, callback=True, mixed=False, history_size=None):
    pin = store.capture_pin()
    child = LazyHistoryList(store, pin, 1,
        initial_values=[7] if history_size is None else range(history_size), checked_types=True)
    versions = tuple(VersionChange(NS, (key, 'craft'), SkillHistory(key, 'craft', provenance=HistoryReference('list', 1)),
        memberships=(Membership('person', key, key),)) for key in (1, 2))
    placements = tuple(IdentityOccurrenceChange(NS, (key, 'craft'), PATH, 1) for key in (1, 2))
    ordinary = ()
    if mixed:
        versions = versions[:1]
        ordinary = (RecordChange('world.settlements', 2, Settlement(2, 0, 0, memory={'history': child.storage_reference()}),
            memberships=(Membership('fixture', 2, 2),)),)
        placements = placements[:1] + (IdentityOccurrenceChange('world.settlements', 2,
            (('field', 'memory'), ('key', 'history')), 1),)
    initial = initial_catalog_delta(store.codec, versions, placements, ordinary_changes=ordinary,
        next_incarnation_id=2, generation=1)
    pin = store.commit(pin, commit_token='initial', changes=ordinary, new_segments=(),
        version_changes=versions + child.pending_changes() + initial.decode(store.codec)[0],
        identity_changes=placements, next_incarnation_id=2,
        metadata=metadata(1, (NS, 'world_identity_links', *(('world.settlements',) if mixed else ())))).pin
    child.accept_save(pin)
    registry = LazyIdentityRegistry(store.store_identity, next_incarnation=2)
    registry.bind(child, Occurrence(NS, (1, 'craft'), PATH), incarnation=IncarnationId(store.store_identity, 1))
    owners, calls, dirty = {}, [], set()
    def load(owner):
        if owner not in owners:
            owners[owner] = (store.read_record(*owner, expected_record_schema=1) if owner[0] == 'world.settlements'
                else store.read_version(coord.pin, *owner, expected_record_schema=1).value)
        return owners[owner]
    def header(owner):
        calls.append(owner)
        if owner[0] == 'world.settlements':
            return RecordChange(*owner, replace(load(owner), memory={'history': child.storage_reference()}),
                memberships=(Membership('fixture', 2, 2),))
        return VersionChange(*owner, replace(load(owner), provenance=child.storage_reference()),
            memberships=(Membership('person', owner[1][0], owner[1][0]),))
    coord = IdentityCoordinator(store, pin, registry, load_owner=load,
        resolve_path=_relative_get,
        install_path=lambda owner, path, value: _relative_set(load(owner), path, value),
        mark_dirty=dirty.add, preflight=lambda: None,
        encode_placement=lambda owner, path, value: FAMILIES[NS].identity_payload_bytes(store, coord.pin, value, path),
        prepare_owner_header=header if callback else None)
    child.bind(lambda: coord.routes_for_mutation(child), lambda: None)
    return coord, child, calls


def test_backing_write_forces_both_physical_headers_and_preserves_queries(tmp_path):
    with store_at(tmp_path / 'headers.sqlite') as store:
        coord, child, calls = fixture(store)
        child.append(8)
        delta = coord.prepare_delta((), value_changed_incarnations=(1,))
        versions, ordinary, placements = delta.decode(store.codec)
        headers = tuple(c for c in versions if c.namespace == NS)
        assert {c.key for c in headers} == {(1, 'craft'), (2, 'craft')}
        assert len(calls) == 2 and ordinary == placements == ()
        assert coord.prepare_delta((), value_changed_incarnations=(1,)) is delta
        assert len(calls) == 2
        pin = store.commit(coord.pin, commit_token='changed-child', changes=ordinary, new_segments=(),
            version_changes=versions + child.pending_changes(), identity_changes=placements,
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        coord.accept_delta(delta, pin)
        child.accept_save(pin)
        for key in (1, 2):
            assert store.read_version(pin, NS, (key, 'craft'), expected_record_schema=1).valid_from == 2
            assert store.query_memberships(pin, NS, 'person', key) == (((key, 'craft'), key),)
        assert LazyHistoryList(store, pin, 1) == [7, 8]


def test_provided_header_is_not_added_again_and_noop_never_calls_provider(tmp_path):
    with store_at(tmp_path / 'provided.sqlite') as store:
        coord, child, calls = fixture(store)
        coord.routes_for_mutation(child)  # A guarded operation that did not edit.
        delta = coord.prepare_delta(())
        assert delta.decode(store.codec) == ((), (), ()) and not calls
    with store_at(tmp_path / 'provided-2.sqlite') as store:
        coord, child, calls = fixture(store)
        child.append(8)
        provided = VersionChange(NS, (1, 'craft'), SkillHistory(1, 'craft', provenance=child.storage_reference()),
            memberships=(Membership('person', 1, 1),))
        delta = coord.prepare_delta((provided,), value_changed_incarnations=(1,))
        headers = tuple(c for c in delta.decode(store.codec)[0] if c.namespace == NS)
        assert tuple(c.key for c in headers) == ((2, 'craft'),)
        assert calls == [(NS, (2, 'craft'))]


def test_missing_header_provider_fails_before_freezing_or_clearing_dirty_state(tmp_path):
    with store_at(tmp_path / 'missing.sqlite') as store:
        coord, child, calls = fixture(store, callback=False)
        child.append(8)
        with pytest.raises(StoreIntegrityError, match='physical owner header'):
            coord.prepare_delta((), value_changed_incarnations=(1,))
        assert coord._prepared is None and coord.dirty_owners
        assert child[-1] == 8


@pytest.mark.parametrize('action', ['save', 'mutation'])
def test_provider_cannot_reenter_preparation_or_mutate_the_group(tmp_path, action):
    with store_at(tmp_path / 'reentrant.sqlite') as store:
        coord, child, calls = fixture(store)
        child.append(8)
        coord.prepare_owner_header = (lambda owner: coord.prepare_delta(())) if action == 'save' else (lambda owner: child.append(9))
        with pytest.raises(StoreConflictError, match='preparation'):
            coord.prepare_delta((), value_changed_incarnations=(1,))
        assert coord._prepared is None and coord.dirty_owners
        assert list(child) == [7, 8]


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_forced_header_plan_retries_or_resolves_exactly_once(tmp_path, phase):
    with store_at(tmp_path / 'fault.sqlite') as store:
        coord, child, calls = fixture(store)
        child.append(8)
        delta = coord.prepare_delta((), value_changed_incarnations=(1,))
        versions, ordinary, placements = delta.decode(store.codec)
        child_changes = child.pending_changes()
        def fail(at):
            if at == phase:
                raise OSError('forced header commit failed')
        store._phase_hook = fail
        with pytest.raises(OSError):
            store.commit(coord.pin, commit_token='forced-header', changes=ordinary, new_segments=(),
                version_changes=versions + child_changes, identity_changes=placements,
                metadata=metadata(2, (NS, 'world_identity_links')))
        store._phase_hook = lambda at: None
        assert coord.prepare_delta((), value_changed_incarnations=(1,)) is delta
        assert len(calls) == 2
        result = store.resolve_commit(coord.pin, 'forced-header')
        if phase == 'before_commit':
            assert result.outcome == 'not_committed'
            result = store.commit(coord.pin, commit_token='forced-header-retry', changes=ordinary, new_segments=(),
                version_changes=versions + child_changes, identity_changes=placements,
                metadata=metadata(2, (NS, 'world_identity_links')))
        coord.accept_delta(delta, result.pin)
        coord.accept_delta(delta, result.pin)
        child.accept_save(result.pin)
        assert list(child) == [7, 8]
        assert result.pin.captured_head == 2 and not coord.dirty_owners


def test_missing_physical_header_rejects_ack_and_keeps_frozen_plan(tmp_path):
    with store_at(tmp_path / 'missing-row.sqlite') as store:
        coord, child, calls = fixture(store)
        child.append(8)
        delta = coord.prepare_delta((), value_changed_incarnations=(1,))
        versions, ordinary, placements = delta.decode(store.codec)
        # Publish the catalog and child while deliberately omitting one of the
        # exact physical headers. The catalog's generation commitment catches it.
        broken = tuple(c for c in versions if not (c.namespace == NS and c.key == (2, 'craft')))
        pin = store.commit(coord.pin, commit_token='missing-header', changes=ordinary, new_segments=(),
            version_changes=broken + child.pending_changes(), identity_changes=placements,
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        with pytest.raises(StoreIntegrityError, match='commitment'):
            coord.accept_delta(delta, pin)
        assert coord._prepared.delta is delta and coord.dirty_owners


def test_forced_header_ack_checks_its_exact_query_projection(tmp_path):
    with store_at(tmp_path / 'query-ack.sqlite') as store:
        coord, child, calls = fixture(store)
        child.append(8)
        delta = coord.prepare_delta((), value_changed_incarnations=(1,))
        versions, ordinary, placements = delta.decode(store.codec)
        pin = store.commit(coord.pin, commit_token='query-ack', changes=ordinary, new_segments=(),
            version_changes=versions + child.pending_changes(), identity_changes=placements,
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND record_key=? AND valid_to IS NULL',
            (NS, store.codec.encode((2, 'craft'))))
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match='query membership'):
            coord.accept_delta(delta, pin)
        assert coord._prepared.delta is delta


@pytest.mark.parametrize('size', [1000, 10000])
def test_eager_forced_header_checks_complete_bounded_query_projection(tmp_path, size):
    with store_at(tmp_path / 'eager-queries.sqlite') as store:
        coord, child, calls = fixture(store, mixed=True)
        child.append(8)
        delta = coord.prepare_delta((), value_changed_incarnations=(1,))
        versions, ordinary, placements = delta.decode(store.codec)
        assert len(ordinary) == 1 and ordinary[0].namespace == 'world.settlements'
        pin = store.commit(coord.pin, commit_token='mixed-query', changes=ordinary, new_segments=(),
            version_changes=versions + child.pending_changes(), identity_changes=placements,
            metadata=metadata(2, (NS, 'world.settlements', 'world_identity_links'))).pin
        # A body commitment alone cannot detect an extra eager query row.
        store.db.executemany('INSERT INTO query_membership VALUES (?,?,?,?,?,?)',
            (('world.settlements', 'extra', store.codec.encode(n), store.codec.encode(2), n, 2) for n in range(size)))
        store.db.commit()
        before = store.diagnostics().query_rows
        with pytest.raises(StoreIntegrityError, match='ordinary.*query'):
            coord.accept_delta(delta, pin)
        assert coord._prepared.delta is delta
        assert store.diagnostics().query_rows - before == 3  # One lazy and two eager projection rows.
        plan = store.db.execute('EXPLAIN QUERY PLAN SELECT index_name,index_value,ordinal,generation '
            'FROM query_membership INDEXED BY ordinary_query_owner WHERE namespace=? AND record_key=? LIMIT ?',
            ('world.settlements', store.codec.encode(2), 2)).fetchall()
        assert any('SEARCH' in row[3] and 'ordinary_query_owner' in row[3] for row in plan)
        assert not any('TEMP B-TREE' in row[3] for row in plan)


def test_legacy_eager_header_scope_requires_copy_upgrade_without_migrating(tmp_path):
    with store_at(tmp_path / 'legacy-eager.sqlite') as store:
        coord, child, calls = fixture(store, mixed=True)
        store.db.execute('DROP INDEX ordinary_query_owner')
        store.db.commit()
        child.append(8)
        delta = coord.prepare_delta((), value_changed_incarnations=(1,))
        versions, ordinary, placements = delta.decode(store.codec)
        pin = store.commit(coord.pin, commit_token='legacy-query', changes=ordinary, new_segments=(),
            version_changes=versions + child.pending_changes(), identity_changes=placements,
            metadata=metadata(2, (NS, 'world.settlements', 'world_identity_links'))).pin
        with pytest.raises(StoreFormatError, match='explicit indexed copy upgrade'):
            coord.accept_delta(delta, pin)
        assert coord._prepared.delta is delta
        assert store.db.execute('SELECT 1 FROM sqlite_master WHERE name=?', ('ordinary_query_owner',)).fetchone() is None
