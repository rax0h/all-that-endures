"""Paged event histories retain their legacy integer mutation contract."""
import pytest

from ate_sim.core import World
from ate_sim.magic_resources import MagicResource
from ate_sim.materials import MaterialLot
from ate_sim.social import Relationship
from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, PAGE_NAMESPACE

RULES = 'final-event-histories'


def converted(tmp_path, size=1000, *, cross_scalar=True):
    world = World(843000)
    history = list(range(size))
    world.magic_resources.resources[1] = MagicResource(1, 'essence', 'fire', 'common', 1, 'person', 1, 0, None, transfers=history)
    world.materials.lots[1] = MaterialLot(1, 'ore', 10., .5, 1, 1, 0, 1, 'person', 1, transfers=history)
    world.social.edges[1, 2] = Relationship(1, 2, shared_history=history)
    if cross_scalar:
        world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=history)
        world.currency.wallets[1] = {'history': history}
    source, target = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


@pytest.mark.parametrize('size', [1000, 10000])
@pytest.mark.parametrize('family,field,scalar,value', [
    ('resources', 'transfers', 'location', 2),
    ('material_lots', 'transfers', 'quantity', 12.),
    ('social_edges', 'shared_history', 'trust', .75),
])
def test_scalar_save_reads_no_event_history_pages(tmp_path, size, family, field, scalar, value):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = getattr(session, family)
        key = (1, 2) if family == 'social_edges' else 1
        record = table[key]
        history = getattr(record, field)
        assert isinstance(history, LazyHistoryList)
        setattr(record, scalar, value)
        session.save()
        assert history.diagnostics()['page_loads'] == 0
        assert len(table._baseline_payload[key]) < 2048
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert getattr(getattr(session, family)[key], scalar) == value


def test_cross_family_append_keeps_one_proxy_and_one_tail_write(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.wallets[1]['history']
        assert isinstance(history, LazyHistoryList)
        history.append(1000)
        assert history is session.resources[1].transfers
        assert history is session.material_lots[1].transfers
        assert history is session.social_edges[1, 2].shared_history
        assert history is session.skills[1, 'craft'].provenance
        plan = session._prepare_hybrid_save()
        assert len([c for c in plan.nested_history_version_changes if c.namespace == PAGE_NAMESPACE]) == 1
        assert history.diagnostics()['page_loads'] == 1
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.resources[1].transfers
        assert len(history) == 1001 and history[-1] == 1000
        assert history is session.material_lots[1].transfers
        assert history is session.social_edges[1, 2].shared_history


@pytest.mark.parametrize('operation', [
    lambda h: h.append(True), lambda h: h.insert(0, 1.),
    lambda h: h.__setitem__(0, 'bad'),
    lambda h: h.__setitem__(slice(0, 1), [1, False]),
    lambda h: h.extend(iter([2000, 2.])),
    lambda h: h.__iadd__([2000, 'bad']),
])
def test_integer_validation_through_unloaded_shared_alias_is_atomic(tmp_path, operation):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.wallets[1]['history']
        with pytest.raises(TypeError, match='integer event IDs'):
            operation(history)
        assert len(history) == 1000 and history[0] == 0 and history[-1] == 999
        assert not history.pending_changes()


def test_retired_integer_owners_do_not_constrain_remaining_skill_alias(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.wallets[1]['history']
        del session.resources[1]
        del session.material_lots[1]
        del session.social_edges[1, 2]
        history.append('skill provenance')
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].provenance[-1] == 'skill provenance'


def test_detach_materializes_every_shared_event_history_once(tmp_path):
    path = converted(tmp_path, 4)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        detached = session.detach(materialize_history=True)
        history = detached.magic_resources.resources[1].transfers
        assert type(history) is list
        assert history is detached.materials.lots[1].transfers
        assert history is detached.social.edges[1, 2].shared_history
        assert history is detached.skills.skills[1, 'craft'].provenance
        assert history is detached.currency.wallets[1]['history']


@pytest.mark.parametrize('phase', ['during_version_writes', 'before_commit'])
def test_shared_event_history_rollback_preserves_dirty_retry(tmp_path, phase):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.resources[1].transfers
        history.append(1000)
        generation = session.pin.captured_head
        def fail(at):
            if at == phase:
                raise OSError('event history rollback')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='event history rollback'):
            session.save()
        session.store._phase_hook = lambda _at: None
        assert session.resolve_save() == generation
        assert history.pending_changes() and history[-1] == 1000
        assert session.save() == generation + 1
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.social_edges[1, 2].shared_history[-1] == 1000


def test_shared_event_history_lost_acknowledgement_resolves_once(tmp_path, monkeypatch):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.material_lots[1].transfers
        history.append(1000)
        generation = session.pin.captured_head
        original = session._publish_committed_hybrid
        def lost(*_args):
            raise OSError('event history acknowledgement lost')
        monkeypatch.setattr(session, '_publish_committed_hybrid', lost)
        with pytest.raises(OSError, match='acknowledgement lost'):
            session.save()
        with pytest.raises(StoreError):
            history.append(1001)
        monkeypatch.setattr(session, '_publish_committed_hybrid', original)
        assert session.resolve_save() == generation + 1
        assert len(history) == 1001
        assert session.save() == generation + 1


def test_genuine_legacy_event_histories_remain_resident_without_open_migration(tmp_path, monkeypatch):
    import ate_sim.persistence_lazy as module
    families = dict(module.NESTED_RECORD_FIELDS)
    for namespace in ('world.magic_resources.resources', 'world.materials.lots', 'world.social.edges', 'world.skills.skills'):
        families.pop(namespace)
    with monkeypatch.context() as context:
        context.setattr(module, 'NESTED_RECORD_FIELDS', families)
        path = converted(tmp_path, 4, cross_scalar=False)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.resources[1].transfers
        assert isinstance(history, list)
        assert session.material_lots[1].transfers is history
        assert session.social_edges[1, 2].shared_history is history
        generation = session.pin.captured_head
        assert session.save() == generation
        history.append(4)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.resources[1].transfers == [0, 1, 2, 3, 4]
        assert isinstance(session.resources[1].transfers, list)
