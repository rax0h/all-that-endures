"""Nested graph buckets retain compact headers and bounded point writes."""
import pytest

from ate_sim.core import World
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, LazyHistorySet, ENTRY_NAMESPACE, PAGE_NAMESPACE
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-native-graph-buckets'
FAMILIES = ['genealogy_children', 'owner_index', 'social_adjacency', 'lineage_children', 'material_lot_index', 'material_active_index']


def converted(tmp_path, family, size):
    world = World(843000)
    if family == 'genealogy_children':
        root, key, values = world.genealogy.children, 1, list(range(size))
    elif family == 'owner_index':
        root, key, values = world.magic_resources.owner_index, ('person', 1), set(range(size))
    elif family == 'social_adjacency':
        root, key, values = world.social.adjacency, 1, set(range(size))
    elif family == 'lineage_children':
        root, key, values = world.lineage.children, ('person', 1), {('person', n) for n in range(size)}
    elif family == 'material_lot_index':
        root, key, values = world.materials.lot_index, ('ore', 1), list(range(size))
    else:
        root, key, values = world.materials.active_lot_index, 1, set(range(size))
    root[key] = values
    world.currency.wallets[1] = {'bucket': values}
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
    return target, key


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('size', [1000, 10000])
def test_one_graph_bucket_addition_writes_only_one_page_or_entry(tmp_path, family, size):
    path, key = converted(tmp_path, family, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = getattr(session, family)
        bucket = table[key]
        assert isinstance(bucket, (LazyHistoryList, LazyHistorySet))
        assert len(bucket) == size
        assert session.wallets[1]['bucket'] is bucket
        value = ('person', size) if family == 'lineage_children' else size
        (bucket.append if isinstance(bucket, LazyHistoryList) else bucket.add)(value)
        plan = session._prepare_hybrid_save()
        edits = [c for c in plan.nested_history_version_changes if c.namespace in (PAGE_NAMESPACE, ENTRY_NAMESPACE)]
        assert len(edits) == 1
        assert sum(len(session.store.codec.encode(c.value)) for c in edits) < 8192
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bucket = getattr(session, family)[key]
        assert len(bucket) == size + 1 and value in bucket
        assert session.wallets[1]['bucket'] is bucket
        world = session.detach(materialize_history=True)
    assert type(world.currency.wallets[1]['bucket']) in (list, set)


@pytest.mark.parametrize('family', FAMILIES)
def test_bucket_type_guard_through_alias_and_after_owner_retirement(tmp_path, family):
    path, key = converted(tmp_path, family, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bucket = session.wallets[1]['bucket']
        add = bucket.append if isinstance(bucket, LazyHistoryList) else bucket.add
        with pytest.raises(TypeError):
            add('invalid graph member')
        assert len(bucket) == 16
        batch = bucket.extend if isinstance(bucket, LazyHistoryList) else bucket.update
        value = ('person', 17) if family == 'lineage_children' else 17
        with pytest.raises(TypeError):
            batch([value, 'invalid graph member'])
        assert len(bucket) == 16
        del getattr(session, family)[key]
        add('unconstrained wallet value')
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert key not in getattr(session, family)
        assert 'unconstrained wallet value' in session.wallets[1]['bucket']


@pytest.mark.parametrize('family', FAMILIES)
def test_bucket_unowned_overlay_reattaches_without_resurrecting_owner(tmp_path, family):
    path, key = converted(tmp_path, family, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bucket = getattr(session, family)[key]
        incarnation = bucket._incarnation
        del getattr(session, family)[key]
        del session.wallets[1]
        session.save()
        value = ('person', 17) if family == 'lineage_children' else 17
        (bucket.append if isinstance(bucket, LazyHistoryList) else bucket.add)(value)
        session.world.year += 1
        session.save()
        getattr(session, family)[key] = bucket
        session.save()
        assert bucket._incarnation == incarnation
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert value in getattr(session, family)[key]
        assert 1 not in session.wallets


@pytest.mark.parametrize('family', ['genealogy_children', 'lineage_children'])
@pytest.mark.parametrize('phase', ['during_version_writes', 'before_commit'])
def test_native_bucket_rollback_preserves_dirty_pages_and_alias(tmp_path, family, phase):
    path, key = converted(tmp_path, family, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bucket = getattr(session, family)[key]
        value = ('person', 17) if family == 'lineage_children' else 17
        (bucket.append if isinstance(bucket, LazyHistoryList) else bucket.add)(value)
        generation = session.pin.captured_head
        def fail(at):
            if at == phase:
                raise OSError('graph bucket rollback')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='rollback'):
            session.save()
        session.store._phase_hook = lambda _at: None
        assert session.resolve_save() == generation
        assert session.wallets[1]['bucket'] is bucket
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert value in getattr(session, family)[key]


def test_counted_history_shared_across_graph_record_and_eager_fields(tmp_path):
    from ate_sim.core import Household, Settlement
    from ate_sim.magic_resources import MagicResource
    from ate_sim.skills import SkillHistory
    from ate_sim.persistence_lazy_sequence import LazyOrderedSequence, NODE_NAMESPACE
    world = World(843000)
    values = list(range(1, 1001))
    world.households[1] = Household(1, 1, members=values)
    world.magic_resources.resources[1] = MagicResource(1, 'essence', 'fire', 'common', 1, transfers=values)
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=values)
    world.genealogy.children[1] = values
    world.settlements[1] = Settlement(1, 0, 0, memory={'history': values})
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        resource = session.resources[1]
        history = resource.transfers
        assert isinstance(history, LazyOrderedSequence)
        resource.location = 2
        session.save()
        assert not any(namespace == NODE_NAMESPACE for namespace, _key in history._cache)
        history.insert(3, 7)
        assert session.genealogy_children[1] is history
        assert session.skills[1, 'craft'].provenance is history
        assert session.world.households[1].members is history
        assert session.world.settlements[1].memory['history'] is history
        session.save()
        world = session.detach(materialize_history=True)
    assert world.genealogy.children[1] is world.households[1].members
    assert world.magic_resources.resources[1].transfers is world.households[1].members


@pytest.mark.parametrize('family', FAMILIES)
def test_graph_bucket_shared_with_eager_settlement_memory(tmp_path, family):
    from ate_sim.core import Settlement
    path, key = converted(tmp_path, family, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bucket = getattr(session, family)[key]
        session.world.settlements[1] = Settlement(1, 0, 0, memory={'bucket': bucket})
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.settlements[1].memory['bucket'] is getattr(session, family)[key]
        world = session.detach(materialize_history=True)
    root = world
    from ate_sim.persistence_lazy_graph_buckets import BUCKET_SPECS
    namespace = next(ns for ns, spec in BUCKET_SPECS.items() if spec[1] == family)
    for field in namespace.split('.')[1:]:
        root = getattr(root, field)
    assert world.settlements[1].memory['bucket'] is root[key]
