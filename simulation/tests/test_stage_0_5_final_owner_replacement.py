"""Owner/subtree replacement journals only checked affected placements."""
from contextlib import nullcontext
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from simulation.ate_sim.incremental_store import RecordChange, StoreConflictError, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_identity import LazyIdentityRegistry, IncarnationId, Occurrence
from simulation.ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta, GROUP_NAMESPACE, OWNER_NAMESPACE
from simulation.ate_sim.persistence_lazy_identity_coordinator import IdentityCoordinator
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata

NS = 'world.households'
LEFT = (('field', 'left'),)
RIGHT = (('field', 'right'),)


@dataclass
class Child:
    value: int


@dataclass
class Header:
    left: Child
    right: Child


def setup(store):
    store.codec.register_record('ReplacementChild', Child)
    store.codec.register_record('ReplacementHeader', Header)
    versions = tuple(VersionChange(NS, k, Header(Child(7), Child(8))) for k in (1, 2))
    placements = tuple(IdentityOccurrenceChange(NS, key, path, inc)
        for key, path, inc in ((1, (), 1), (1, LEFT, 2), (1, RIGHT, 3),
                               (2, (), 4), (2, LEFT, 2), (2, RIGHT, 5)))
    delta = initial_catalog_delta(store.codec, versions, placements,
                                  next_incarnation_id=6, generation=1)
    pin = store.commit(store.capture_pin(), commit_token='initial',
        version_changes=versions + delta.decode(store.codec)[0], changes=(), new_segments=(),
        identity_changes=placements, next_incarnation_id=6,
        metadata=metadata(1, (NS, 'world_identity_links'))).pin
    registry = LazyIdentityRegistry(store.store_identity, next_incarnation=6)
    registry.live_bindings = lambda: pytest.fail('global registry walk')
    owners, loads, dirty, installations = {}, [], set(), []
    def load(owner):
        if owner not in owners:
            loads.append(owner)
            owners[owner] = store.read_version(coord.pin, *owner, expected_record_schema=1).value
        return owners[owner]
    def install(owner, path, obj):
        installations.append((owner, path))
        if not path:
            owners[owner] = obj
        else:
            object.__setattr__(owners[owner], path[0][1], obj)
    coord = IdentityCoordinator(store, pin, registry, load_owner=load,
        resolve_path=lambda value, path: value if not path else getattr(value, path[0][1]),
        install_path=install, mark_dirty=dirty.add, preflight=lambda: None)
    original = load((NS, 1)).left
    registry.bind(original, Occurrence(NS, 1, LEFT),
                  incarnation=IncarnationId(store.store_identity, 2))
    return coord, registry, owners, loads, dirty, installations, original


def test_owner_replacement_retires_all_old_paths_and_preserves_peer_alias(tmp_path):
    with make_store(tmp_path / 'owner.sqlite') as store:
        coord, registry, owners, loads, dirty, installed, original = setup(store)
        old = store.capture_pin()
        replacement = Header(Child(10), Child(11))
        coord.replace_owner((NS, 1), ((RIGHT, replacement.right),
                                     (LEFT, replacement.left), ((), replacement)))
        assert owners[NS, 1] is replacement
        assert set(coord.routes_for_mutation(original)) == {(NS, 2)}
        assert owners[NS, 2].left is original
        original.value = 12
        payloads = tuple(VersionChange(*owner, owners[owner]) for owner in sorted(dirty))
        prepared = coord.prepare_delta(payloads)
        versions, ordinary, placements = prepared.decode(store.codec)
        successor = store.commit(coord.pin, commit_token='replacement',
            version_changes=payloads + versions, changes=ordinary, new_segments=(),
            identity_changes=placements, next_incarnation_id=registry.next_incarnation,
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        coord.accept_delta(prepared, successor)
        assert store.read_identity_group(old, 2).occurrences == ((NS, 1, LEFT), (NS, 2, LEFT))
        assert store.read_identity_group(successor, 2).occurrences == ((NS, 2, LEFT),)
        assert registry.object_for_incarnation(registry.incarnation_for_object(replacement)) is replacement
        assert not coord.placement_overlay and not coord.dirty_owners


def test_subtree_replacement_preserves_other_field_and_root_placements(tmp_path):
    with make_store(tmp_path / 'subtree.sqlite') as store:
        coord, registry, owners, loads, dirty, installed, original = setup(store)
        replacement = Child(10)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, replacement),))
        assert owners[NS, 1].left is replacement
        assert set(c.occurrence_path for c in coord.placement_overlay.values()) == {LEFT}
        assert coord.catalog.read_identity_membership(coord.pin, (NS, 1), RIGHT) == 3
        assert coord.catalog.read_identity_membership(coord.pin, (NS, 1), ()) == 1
        assert set(coord.routes_for_mutation(original)) == {(NS, 2)}


@pytest.mark.parametrize('failure', ['duplicate', 'outside_subtree', 'bad_group'])
def test_invalid_replacement_is_rejected_before_installation_or_detachment(tmp_path, failure):
    with make_store(tmp_path / 'invalid.sqlite') as store:
        coord, registry, owners, loads, dirty, installed, original = setup(store)
        before_allocator = registry.next_incarnation
        replacement = Child(10)
        if failure == 'duplicate':
            call = lambda: coord.replace_owner((NS, 1), ((LEFT, replacement), (LEFT, Child(11))))
            error = ValueError
        elif failure == 'outside_subtree':
            call = lambda: coord.replace_subtree((NS, 1), LEFT, ((RIGHT, replacement),))
            error = ValueError
        else:
            store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                             (GROUP_NAMESPACE, store.codec.encode(3)))
            store.db.commit()
            call = lambda: coord.replace_owner((NS, 1), ((LEFT, replacement),))
            error = StoreIntegrityError
        with pytest.raises(error):
            call()
        assert not dirty and not installed and not coord.placement_overlay
        assert registry.next_incarnation == before_allocator
        assert registry.incarnation_for_occurrence(Occurrence(NS, 1, LEFT)).value == 2


def test_input_cannot_freeze_a_reentrant_replacement_plan(tmp_path):
    with make_store(tmp_path / 'reentrant.sqlite') as store:
        coord, registry, owners, loads, dirty, installed, original = setup(store)
        def values():
            yield LEFT, Child(10)
            coord.prepare_delta(())
        with pytest.raises(StoreConflictError, match='mutation'):
            coord.replace_owner((NS, 1), values())
        assert coord._prepared is None
        assert not dirty and not installed and not coord.placement_overlay


def test_new_owner_then_retirement_cancels_paths_without_reusing_incarnations(tmp_path):
    with make_store(tmp_path / 'new-owner.sqlite') as store:
        coord, registry, owners, loads, dirty, installed, original = setup(store)
        created = Header(Child(20), Child(21))
        coord.replace_owner((NS, 3), (((), created), (LEFT, created.left), (RIGHT, created.right)))
        reserved = tuple(registry.incarnation_for_object(value).value
                         for value in (created, created.left, created.right))
        coord.load_owner = lambda owner: pytest.fail('deleted new owner loaded')
        coord.retire_owner((NS, 3))
        assert not coord.placement_overlay
        assert coord.routes_for_mutation(created.left) == ()
        prepared = coord.prepare_delta(())
        versions, ordinary, placements = prepared.decode(store.codec)
        successor = store.commit(coord.pin, commit_token='cancel-new',
            version_changes=versions, changes=ordinary, new_segments=(), identity_changes=placements,
            next_incarnation_id=registry.next_incarnation,
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        coord.accept_delta(prepared, successor)
        assert all(store.read_identity_group(successor, inc).occurrences == () for inc in reserved)
        assert registry.bind(Child(30)).value > max(reserved)


@pytest.mark.parametrize('borrowed', [False, True])
def test_owner_absence_uses_one_checked_witness_lookup(tmp_path, borrowed):
    with make_store(tmp_path / 'absent.sqlite') as store:
        coord, *_ = setup(store)
        owner = (NS, 3)
        witness_key = store.codec.encode(owner)
        scope = store.read_snapshot(coord.pin) if borrowed else nullcontext()
        with scope, patch.object(store, '_visible_record_row', wraps=store._visible_record_row) as visible, \
                patch.object(coord.catalog, '_has_source', wraps=coord.catalog._has_source) as source:
            assert coord._owner_changes(owner, ()) == {}
            witness_calls = [row for row in visible.call_args_list if row.args[1:] == (OWNER_NAMESPACE, witness_key)]
            assert len(witness_calls) == 1
            source.assert_called_once_with(coord.pin, owner)
            assert store.db.in_transaction is borrowed
        with pytest.raises(StoreIntegrityError, match='missing required identity authority'):
            coord.catalog.read_owner_identity(coord.pin, owner)
        assert coord.catalog.read_identity_membership(coord.pin, owner, ()) is None
        assert not store.db.in_transaction


def drop_witness(store, owner):
    key = store.codec.encode(owner)
    for table, column in (('lazy_record_versions', 'typed_key'), ('lazy_order_versions', 'typed_key'),
                          ('lazy_query_versions', 'record_key')):
        store.db.execute(f'DELETE FROM {table} WHERE namespace=? AND {column}=?', (OWNER_NAMESPACE, key))


@pytest.mark.parametrize('remaining', ['witness', 'body', 'placement'])
def test_owner_requires_all_persisted_authority_before_replacement(tmp_path, remaining):
    with make_store(tmp_path / 'partial.sqlite') as store:
        coord, registry, _, _, dirty, installed, _ = setup(store)
        owner = (NS, 1)
        if remaining != 'witness':
            drop_witness(store, owner)
        if remaining != 'body':
            store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                             (NS, store.codec.encode(owner[1])))
        if remaining != 'placement':
            store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?',
                             (NS, store.codec.encode(owner[1])))
        store.db.commit()

        next_incarnation = registry.next_incarnation
        with patch.object(coord.catalog, '_has_source', wraps=coord.catalog._has_source) as source, \
                pytest.raises(StoreIntegrityError):
            coord.replace_owner(owner, (((), Header(Child(9), Child(10))),))
        assert source.call_count == (0 if remaining == 'witness' else 1)
        assert not dirty and not installed and not coord.placement_overlay
        assert registry.next_incarnation == next_incarnation
        assert not store.db.in_transaction


def test_owner_requires_valid_witness_when_its_decoder_raises_key_error(tmp_path):
    with make_store(tmp_path / 'decoder.sqlite') as store:
        coord, *_ = setup(store)
        owner = (NS, 1)
        witness_key = store.codec.encode(owner)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                         (NS, store.codec.encode(owner[1])))
        store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=?',
                         (NS, store.codec.encode(owner[1])))
        store.db.commit()
        check = store._check_record_row

        def broken_witness(namespace, key, row, *, decode):
            if (namespace, key) == (OWNER_NAMESPACE, witness_key):
                raise KeyError('invalid witness body')
            return check(namespace, key, row, decode=decode)

        with patch.object(store, '_check_record_row', side_effect=broken_witness):
            with pytest.raises(StoreIntegrityError, match='missing required identity authority'):
                coord._owner_changes(owner, ())
        assert not store.db.in_transaction


def test_owner_requires_witness_for_an_ordinary_body_without_placements(tmp_path):
    with make_store(tmp_path / 'ordinary.sqlite') as store:
        coord, registry, *_ = setup(store)
        owner = ('world.currency.minted', 'copper')
        changes = (RecordChange(*owner, (0, 7)),)
        allocator = registry.next_incarnation
        delta = coord.catalog.prepare_delta(coord.pin, (), (), ordinary_changes=changes,
                                            next_incarnation_id=allocator)
        coord.pin = store.commit(coord.pin, commit_token='ordinary-body', changes=changes,
            version_changes=delta.decode(store.codec)[0], identity_changes=(), new_segments=(),
            next_incarnation_id=allocator, metadata=metadata(2, (NS, owner[0], 'world_identity_links'))).pin
        assert coord._owner_changes(owner, ()) == {}
        drop_witness(store, owner)
        store.db.commit()

        with patch.object(coord.catalog, '_has_source', wraps=coord.catalog._has_source) as source, \
                pytest.raises(StoreIntegrityError, match='missing required identity authority'):
            coord._owner_changes(owner, ())
        source.assert_called_once_with(coord.pin, owner)
        assert registry.next_incarnation == allocator and not coord.placement_overlay
        assert not store.db.in_transaction


def test_peer_loading_cannot_freeze_an_intermediate_routing_plan(tmp_path):
    with make_store(tmp_path / 'routing-freeze.sqlite') as store:
        coord, registry, owners, loads, dirty, installed, original = setup(store)
        load = coord.load_owner
        def reentrant(owner):
            if owner == (NS, 2):
                coord.prepare_delta(())
            return load(owner)
        coord.load_owner = reentrant
        with pytest.raises(StoreConflictError, match='mutation'):
            coord.routes_for_mutation(original)
        assert coord._prepared is None
        assert not dirty and not installed and not coord.placement_overlay
