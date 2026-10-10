"""Physical history owners share the checked catalog; logical ranks are not paths."""
import pytest
from dataclasses import replace

from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreFormatError, RecordChange, Membership
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta, IdentityCatalog, placement_path
from simulation.ate_sim.persistence_lazy_nested_history import (
    PAGE_NAMESPACE, ENTRY_NAMESPACE, DESCRIPTOR_NAMESPACE, HistoryReference,
    LazyHistoryList, initial_list_changes,
)
from simulation.ate_sim.persistence_lazy_sequence import NODE_NAMESPACE
from simulation.tests.test_persistence_lazy_store import make_store, metadata


PAGE_PATH = (('index', 0),)
ENTRY_PATH = (('index', 2),)
LEAF_PATH = (('key', 71),)
NAMESPACES = (PAGE_NAMESPACE, ENTRY_NAMESPACE, NODE_NAMESPACE, DESCRIPTOR_NAMESPACE, 'world.people', 'world_identity_links')


def sources():
    return (
        VersionChange(PAGE_NAMESPACE, (2, 0), (HistoryReference('list', 1),)),
        VersionChange(ENTRY_NAMESPACE, (3, 'child'), (0, 'child', HistoryReference('list', 1)),
                      memberships=(Membership('incarnation', 3, 0),)),
        VersionChange(NODE_NAMESPACE, (4, 4), ('leaf', ((71, HistoryReference('list', 1)),))),
    )


def bootstrap(store, *, extra=0):
    store.codec.register_record('HistoryReference', HistoryReference)
    child_versions = initial_list_changes(1, [3], store.codec)
    versions = sources() + tuple(VersionChange('world.people', i, {'value': i}) for i in range(extra))
    placements = tuple(IdentityOccurrenceChange(v.namespace, v.key, p, 1)
                       for v, p in zip(sources(), (PAGE_PATH, ENTRY_PATH, LEAF_PATH)))
    delta = initial_catalog_delta(store.codec, versions, placements, next_incarnation_id=5, generation=1)
    pin = store.commit(store.capture_pin(), commit_token='physical-owners',
        version_changes=versions + child_versions + delta.decode(store.codec)[0], identity_changes=placements,
        next_incarnation_id=5, changes=(), new_segments=(), metadata=metadata(1, NAMESPACES)).pin
    return pin


def test_all_concrete_physical_owner_families_have_checked_group_and_source(tmp_path):
    with make_store(tmp_path / 'owners.sqlite') as store:
        pin = bootstrap(store)
        cat = IdentityCatalog(store)
        group = cat.read_identity_group(pin, 1)
        expected = {(v.namespace, v.key, p) for v, p in zip(sources(), (PAGE_PATH, ENTRY_PATH, LEAF_PATH))}
        assert set(group.occurrences) == expected
        assert len({placement_path(*row) for row in expected}) == 3
        for source, path in zip(sources(), (PAGE_PATH, ENTRY_PATH, LEAF_PATH)):
            owner = cat.read_owner_identity(pin, (source.namespace, source.key))
            assert owner.occurrences == ((path, 1),)
            assert owner.storage_kind == 'lazy'


@pytest.mark.parametrize('namespace,key,path', [
    (PAGE_NAMESPACE, (0, 0), PAGE_PATH),
    (PAGE_NAMESPACE, (True, 0), PAGE_PATH),
    (PAGE_NAMESPACE, (1, -1), PAGE_PATH),
    (PAGE_NAMESPACE, (1, 0), (('index', 128),)),
    (ENTRY_NAMESPACE, (1, 'key'), (('index', 1),)),
    (NODE_NAMESPACE, (1, 0), LEAF_PATH),
    (NODE_NAMESPACE, (1, 2), (('index', 0),)),
    (NODE_NAMESPACE, (1, 2), (('key', True),)),
])
def test_invalid_physical_owner_keys_and_member_paths_are_rejected(namespace, key, path):
    with pytest.raises(StoreIntegrityError):
        placement_path(namespace, key, path)


def test_other_auxiliary_authorities_are_not_identity_owners():
    with pytest.raises(StoreFormatError, match='not registered'):
        placement_path('aux.lazy.sequence.occurrences', (1, 71), ())


@pytest.mark.parametrize('source', [
    VersionChange(PAGE_NAMESPACE, (1, 0), tuple(range(129))),
    VersionChange(ENTRY_NAMESPACE, (1, 'key'), (0, 'key')),
    VersionChange(NODE_NAMESPACE, (1, 2), ('branch', ())),
    VersionChange(NODE_NAMESPACE, (1, 2), ('leaf', ((71, 1), (71, 2)))),
    VersionChange(PAGE_NAMESPACE, (1, 0), (), record_schema=2),
])
def test_invalid_physical_source_cannot_acquire_an_owner_witness(tmp_path, source):
    with make_store(tmp_path / 'bad.sqlite') as store:
        with pytest.raises(StoreIntegrityError):
            initial_catalog_delta(store.codec, (source,), (), next_incarnation_id=1, generation=1)


def test_physical_history_owner_cannot_be_an_ordinary_record(tmp_path):
    with make_store(tmp_path / 'ordinary.sqlite') as store:
        source = RecordChange(PAGE_NAMESPACE, (1, 0), ())
        with pytest.raises(StoreIntegrityError):
            initial_catalog_delta(store.codec, (), (), ordinary_changes=(source,),
                                  next_incarnation_id=1, generation=1)


def test_sequence_path_follows_occurrence_identity_through_leaf_reordering():
    from simulation.ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    adapter = AUXILIARY_OWNER_FAMILIES[NODE_NAMESPACE]
    before = ('leaf', ((71, 'first'), (92, 'second')))
    after = ('leaf', ((92, 'second'), (71, 'first')))
    assert adapter.resolve_path(before, LEAF_PATH) == adapter.resolve_path(after, LEAF_PATH) == 'first'
    assert adapter.replace_path(after, LEAF_PATH, 'changed') == ('leaf', ((92, 'second'), (71, 'changed')))
    with pytest.raises(StoreIntegrityError, match='occurrence'):
        adapter.resolve_path(before, (('key', 93),))


@pytest.mark.parametrize('history', [1000, 10000])
def test_leaf_move_only_changes_its_two_physical_owner_witnesses(tmp_path, history):
    with make_store(tmp_path / 'move.sqlite') as store:
        pin = bootstrap(store, extra=history)
        old = store.capture_pin()
        changes = (VersionChange(NODE_NAMESPACE, (4, 4), ('leaf', ())),
                   VersionChange(NODE_NAMESPACE, (4, 5), ('leaf', ((71, HistoryReference('list', 1)),))))
        placements = (IdentityOccurrenceChange(NODE_NAMESPACE, (4, 4), LEAF_PATH, None, delete=True),
                      IdentityOccurrenceChange(NODE_NAMESPACE, (4, 5), LEAF_PATH, 1))
        cat = IdentityCatalog(store)
        before = store.diagnostics()
        delta = cat.prepare_delta(pin, changes, placements, next_incarnation_id=5)
        versions = delta.decode(store.codec)[0]
        assert len(versions) < 20
        assert store.diagnostics().payload_reads - before.payload_reads < 40
        pin = store.commit(pin, commit_token='move', version_changes=changes + versions,
            identity_changes=placements, next_incarnation_id=5, changes=(), new_segments=(), metadata=metadata(2, NAMESPACES)).pin
        cat.validate_publication(delta, pin)
        assert (NODE_NAMESPACE, (4, 4), LEAF_PATH) in cat.read_identity_group(old, 1).occurrences
        assert (NODE_NAMESPACE, (4, 5), LEAF_PATH) in cat.read_identity_group(pin, 1).occurrences
        assert cat.read_owner_identity(pin, (NODE_NAMESPACE, (4, 4))).occurrences == ()


@pytest.mark.parametrize('placements', [(), (IdentityOccurrenceChange(PAGE_NAMESPACE, (2, 0), PAGE_PATH, 2),)])
def test_new_source_references_require_exact_complete_placements(tmp_path, placements):
    with make_store(tmp_path / 'projection.sqlite') as store:
        store.codec.register_record('HistoryReference', HistoryReference)
        with pytest.raises(StoreIntegrityError, match='references disagree'):
            initial_catalog_delta(store.codec, sources()[:1], placements,
                                  next_incarnation_id=5, generation=1)


def test_changed_reference_requires_payload_and_matching_placement(tmp_path):
    with make_store(tmp_path / 'changed-reference.sqlite') as store:
        pin = bootstrap(store)
        cat = IdentityCatalog(store)
        change = IdentityOccurrenceChange(PAGE_NAMESPACE, (2, 0), PAGE_PATH, 2)
        with pytest.raises(StoreIntegrityError, match='requires its payload'):
            cat.prepare_delta(pin, (), (change,), next_incarnation_id=5)
        changed_source = VersionChange(PAGE_NAMESPACE, (2, 0), (HistoryReference('list', 2),))
        with pytest.raises(StoreIntegrityError, match='references disagree'):
            cat.prepare_delta(pin, (changed_source,), (), next_incarnation_id=5)


def physical_coordinator(store, pin):
    from simulation.ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    from simulation.ate_sim.persistence_lazy_identity import LazyIdentityRegistry
    from simulation.ate_sim.persistence_lazy_identity_coordinator import IdentityCoordinator
    registry = LazyIdentityRegistry(store.store_identity, next_incarnation=5, prune_dead_occurrences=True)
    registry.live_bindings = lambda: pytest.fail('global live registry scan')
    owners, dirty, loads = {}, set(), []
    def load(owner):
        if owner not in owners:
            loads.append(owner)
            adapter = AUXILIARY_OWNER_FAMILIES[owner[0]]
            value = store.read_version(coord.pin, *owner, expected_record_schema=1).value
            for path, inc in adapter.reference_placements(value):
                value = adapter.replace_path(value, path, LazyHistoryList(store, coord.pin, inc))
            owners[owner] = value
        return owners[owner]
    def resolve(value, path):
        # The value shape identifies the concrete contract in this component
        # harness; production dispatch uses the physical owner's namespace.
        kind = NODE_NAMESPACE if value[0] == 'leaf' else ENTRY_NAMESPACE if len(value) == 3 else PAGE_NAMESPACE
        return AUXILIARY_OWNER_FAMILIES[kind].resolve_path(value, path)
    def install(owner, path, obj):
        owners[owner] = AUXILIARY_OWNER_FAMILIES[owner[0]].replace_path(load(owner), path, obj)
    def header(owner):
        return VersionChange(*owner, store.read_version(coord.pin, *owner, expected_record_schema=1).value,
            memberships=(Membership('incarnation', 3, 0),) if owner[0] == ENTRY_NAMESPACE else ())
    coord = IdentityCoordinator(store, pin, registry, load_owner=load, resolve_path=resolve,
        install_path=install, mark_dirty=dirty.add, preflight=lambda: None,
        encode_placement=lambda owner, path, obj: store.codec.encode(obj.storage_reference()),
        prepare_owner_header=header)
    return coord, registry, owners, dirty, loads, load


def test_child_value_edit_forces_each_unchanged_physical_reference_header(tmp_path):
    from simulation.ate_sim.persistence_lazy_identity import IncarnationId, Occurrence
    with make_store(tmp_path / 'forced.sqlite') as store:
        pin = bootstrap(store)
        old = store.capture_pin()
        coord, registry, owners, dirty, loads, load = physical_coordinator(store, pin)
        owner = (PAGE_NAMESPACE, (2, 0))
        child = load(owner)[0]
        registry.bind(child, Occurrence(*owner, PAGE_PATH), incarnation=IncarnationId(store.store_identity, 1))
        child.bind(lambda: coord.routes_for_mutation(child), lambda: None)
        child.append(9)
        assert len(loads) == 3 and len(dirty) == 3
        assert owners[ENTRY_NAMESPACE, (3, 'child')][2] is child
        assert owners[NODE_NAMESPACE, (4, 4)][1][0][1] is child
        delta = coord.prepare_delta((), value_changed_incarnations=(1,))
        versions, ordinary, placements = delta.decode(store.codec)
        assert not ordinary and not placements
        assert {(v.namespace, v.key) for v in versions if v.namespace in (PAGE_NAMESPACE, ENTRY_NAMESPACE, NODE_NAMESPACE)} == set(dirty)
        successor = store.commit(pin, commit_token='child-edit', version_changes=versions + child.pending_changes(),
            identity_changes=placements, next_incarnation_id=5, changes=(), new_segments=(), metadata=metadata(2, NAMESPACES)).pin
        coord.accept_delta(delta, successor)
        child.accept_save(successor)
        assert list(child) == [3, 9]
        assert list(LazyHistoryList(store, old, 1)) == [3]
        for physical in dirty:
            assert IdentityCatalog(store).read_owner_identity(successor, physical).payload_revision == successor.captured_head
        assert coord.prepare_delta(()).decode(store.codec) == ((), (), ())


def test_retiring_physical_parent_reanchors_child_without_loading_payload(tmp_path):
    with make_store(tmp_path / 'retire-parent.sqlite') as store:
        pin = bootstrap(store)
        old = store.capture_pin()
        coord, registry, owners, dirty, loads, load = physical_coordinator(store, pin)
        owner = (PAGE_NAMESPACE, (2, 0))
        coord.retire_owner(owner)
        assert loads == []
        source = VersionChange(*owner, delete=True)
        delta = coord.prepare_delta((source,))
        versions, ordinary, placements = delta.decode(store.codec)
        successor = store.commit(pin, commit_token='retire-parent', version_changes=(source,) + versions,
            identity_changes=placements, next_incarnation_id=5, changes=(), new_segments=(), metadata=metadata(2, NAMESPACES)).pin
        coord.accept_delta(delta, successor)
        assert len(IdentityCatalog(store).read_identity_group(successor, 1).occurrences) == 2
        assert len(IdentityCatalog(store).read_identity_group(old, 1).occurrences) == 3
        assert not IdentityCatalog(store).read_owner_identity(successor, owner).exists


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_physical_owners_join_exact_central_publication_and_fault_recovery(tmp_path, phase):
    from simulation.ate_sim.persistence_lazy_identity import IncarnationId, Occurrence
    from simulation.ate_sim.persistence_lazy_participants import VERSION_FIELDS, IDENTITY_FIELDS, freeze_hybrid_publication
    from simulation.tests.test_stage_0_5_final_catalog_publication import Plan, ColdPlan, acknowledge
    with make_store(tmp_path / 'central.sqlite') as store:
        pin = bootstrap(store)
        coord, registry, owners, dirty, loads, load = physical_coordinator(store, pin)
        owner = (PAGE_NAMESPACE, (2, 0))
        child = load(owner)[0]
        registry.bind(child, Occurrence(*owner, PAGE_PATH), incarnation=IncarnationId(store.store_identity, 1))
        child.bind(lambda: coord.routes_for_mutation(child), lambda: None)
        child.append(9)
        values = {field: () for field in (*VERSION_FIELDS, *IDENTITY_FIELDS)}
        values['nested_history_version_changes'] = child.pending_changes()
        plan = Plan(**values, scalar_record_plans=(), layout_value=None,
            cold_plan=ColdPlan('physical-central', (), (), metadata(2, NAMESPACES)),
            token='physical-central', target_generation=2, publication=None)
        publication = freeze_hybrid_publication(store, pin, plan, next_incarnation=5,
            required_format_version=3, identity_coordinator=coord)
        arguments = publication.commit_arguments(plan)
        def fail(at):
            if at == phase:
                raise OSError('physical publication fault')
        store._phase_hook = fail
        with pytest.raises(OSError, match='physical publication fault'):
            store.commit(pin, **arguments)
        assert coord._prepared is not None and not any(unit.accepted for unit in publication.participants)
        store._phase_hook = lambda _: None
        result = store.resolve_commit(pin, plan.token)
        if phase == 'before_commit':
            assert result.outcome == 'not_committed'
            assert list(LazyHistoryList(store, pin, 1)) == [3]
            # The existing publisher releases the checked failed freeze, retains
            # all journals, then creates a new token for its next attempt.
            publication.abort_uncommitted()
            plan = replace(plan, token='physical-central-retry',
                           cold_plan=replace(plan.cold_plan, token='physical-central-retry'))
            publication = freeze_hybrid_publication(store, pin, plan, next_incarnation=5,
                required_format_version=3, identity_coordinator=coord)
            result = store.commit(pin, **publication.commit_arguments(plan))
        acknowledge(publication, plan, result)
        acknowledge(publication, plan, result)
        assert all(unit.accepted for unit in publication.participants)
        child.accept_save(result.pin)
        assert list(child) == [3, 9]
        assert not coord.dirty_owners and coord.pin == result.pin
        assert coord.catalog.read_owner_identity(result.pin, owner).payload_revision == 2
        # Scalar backing writes are not an ordinary-open/bootstrap permission.
        from simulation.ate_sim.persistence_lazy_identity_catalog import OWNER_NAMESPACE
        assert store._visible_record_row(2, OWNER_NAMESPACE, store.codec.encode((PAGE_NAMESPACE, (1, 0)))) is None


def test_corrupt_recursive_group_is_rejected_before_child_value_changes(tmp_path):
    from simulation.ate_sim.persistence_lazy_identity import IncarnationId, Occurrence
    with make_store(tmp_path / 'corrupt-group.sqlite') as store:
        pin = bootstrap(store)
        coord, registry, owners, dirty, loads, load = physical_coordinator(store, pin)
        owner = (PAGE_NAMESPACE, (2, 0))
        child = load(owner)[0]
        registry.bind(child, Occurrence(*owner, PAGE_PATH), incarnation=IncarnationId(store.store_identity, 1))
        child.bind(lambda: coord.routes_for_mutation(child), lambda: None)
        store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=?', (ENTRY_NAMESPACE,))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            child.append(9)
        assert list(child) == [3] and not dirty and not child.pending_changes()
