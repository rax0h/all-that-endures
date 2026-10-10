"""Unowned history overlays survive unrelated acknowledgements and reattachment."""
import pytest

from ate_sim.core import World, Settlement
from ate_sim.magic_resources import MagicResource
from ate_sim.metaphysics import SoulState
from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-history-reattachment'


def converted(tmp_path, kind):
    world = World(843000)
    world.magic_resources.resources[1] = MagicResource(1, 'essence', 'fire', 'common', 1)
    world.currency.wallets[2] = {'old': 0}
    world.settlements[2] = Settlement(2, 0, 0, memory={'old': 0})
    if kind == 'list':
        world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=list(range(1000)))
    elif kind == 'set':
        world.metaphysics.souls[1] = SoulState(1, marks={f'mark-{i}' for i in range(1000)})
    else:
        world.metaphysics.souls[1] = SoulState(1, cosmic_links={f'link-{i}': float(i) for i in range(1000)})
    source, target = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


def retained(session, kind):
    return (session.skills[1, 'craft'].provenance if kind == 'list' else
            session.souls[1].marks if kind == 'set' else session.souls[1].cosmic_links)


def remove_owner(session, kind):
    if kind == 'list':
        del session.skills[1, 'craft']
    else:
        del session.souls[1]


def edit(history, kind):
    if kind == 'list':
        history.append(1000)
    elif kind == 'set':
        history.add('new')
    else:
        history['new'] = 2.5


def check(history, kind):
    assert len(history) == 1001
    if kind == 'list':
        assert history[-1] == 1000
    elif kind == 'set':
        assert 'new' in history
    else:
        assert history['new'] == 2.5


def attach(session, history, kind, destination='native'):
    if destination == 'eager':
        session.world.settlements[2] = Settlement(2, 0, 0, memory={'history': history})
    elif destination == 'eager_existing':
        session.world.settlements[2].memory['history'] = history
    elif destination == 'wallet':
        session.wallets[2] = {'history': history}
    elif destination == 'wallet_existing':
        session.wallets[2]['history'] = history
    elif kind == 'list':
        session.skills[2, 'craft'] = SkillHistory(2, 'craft', provenance=history)
    elif kind == 'set':
        session.souls[2] = SoulState(2, marks=history)
    else:
        session.souls[2] = SoulState(2, cosmic_links=history)


def attached_history(session, kind, destination='native'):
    if destination in ('eager', 'eager_existing'):
        return session.world.settlements[2].memory['history']
    if destination in ('wallet', 'wallet_existing'):
        return session.wallets[2]['history']
    return (session.skills[2, 'craft'].provenance if kind == 'list' else
            session.souls[2].marks if kind == 'set' else session.souls[2].cosmic_links)


@pytest.mark.parametrize('kind', ['list', 'set', 'map'])
@pytest.mark.parametrize('save_unrelated', [False, True])
@pytest.mark.parametrize('destination', ['native', 'eager', 'eager_existing', 'wallet', 'wallet_existing'])
def test_retained_private_history_publishes_on_reattachment(tmp_path, kind, save_unrelated, destination):
    path = converted(tmp_path, kind)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = retained(session, kind)
        remove_owner(session, kind)
        session.save()
        incarnation = session._registry.incarnation_for_object(history)
        assert not session._registry.occurrences_for_incarnation(incarnation)
        edit(history, kind)
        if save_unrelated:
            session.resources[1].location = 2
            session.save()
        check(history, kind)
        assert not session._registry.occurrences_for_incarnation(incarnation)
        assert history.pending_changes()
        attach(session, history, kind, destination)
        assert session._registry.incarnation_for_object(history) == incarnation
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = attached_history(session, kind, destination)
        check(history, kind)


@pytest.mark.parametrize('kind', ['list', 'set', 'map'])
def test_new_unpublished_private_history_survives_reattachment(tmp_path, kind):
    path = converted(tmp_path, kind)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        if kind == 'list':
            session.skills[1, 'craft'].provenance = list(range(1000))
        elif kind == 'set':
            session.souls[1].marks = {f'mark-{i}' for i in range(1000)}
        else:
            session.souls[1].cosmic_links = {f'link-{i}': float(i) for i in range(1000)}
        history = retained(session, kind)
        remove_owner(session, kind)
        edit(history, kind)
        session.resources[1].location = 2
        session.save()
        check(history, kind)
        attach(session, history, kind)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = attached_history(session, kind)
        check(history, kind)


@pytest.mark.parametrize('kind', ['list', 'set', 'map'])
def test_unrelated_lost_ack_keeps_private_overlay_for_reattachment(tmp_path, kind, monkeypatch):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path, kind)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = retained(session, kind)
        remove_owner(session, kind)
        session.save()
        edit(history, kind)
        session.resources[1].location = 2
        generation = session.pin.captured_head
        original = session._publish_committed_hybrid
        def lost(*_args):
            raise OSError('private overlay acknowledgement lost')
        monkeypatch.setattr(session, '_publish_committed_hybrid', lost)
        with pytest.raises(OSError, match='acknowledgement lost'):
            session.save()
        with pytest.raises(StoreError):
            len(history)
        monkeypatch.setattr(session, '_publish_committed_hybrid', original)
        assert session.resolve_save() == generation + 1
        assert session.resolve_save() == generation + 1
        check(history, kind)
        attach(session, history, kind, 'wallet_existing')
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        check(attached_history(session, kind, 'wallet_existing'), kind)
