"""Concrete owner callbacks use family roots and compact identity headers."""
import pytest

from ate_sim.core import World, Settlement
from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.incremental_store import StoreError, StoreFormatError

RULES = 'final-concrete-owner-binders'


def converted(tmp_path):
    world = World(843000)
    history = list(range(1000))
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=history)
    world.settlements[1] = Settlement(1, 0, 0, memory={'history': history})
    source, target = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


def test_concrete_owner_loading_and_encoding_do_not_expand_history(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bindings = session._family_bindings
        assert dict.__len__(session.skills) == 0
        record = bindings.load_owner(('world.skills.skills', (1, 'craft')))
        history = bindings.resolve_path(record, (('field', 'provenance'),))
        eager = bindings.load_owner(('world.settlements', 1))
        assert eager.memory['history'] is history
        encoded = bindings.encode_placement(('world.skills.skills', (1, 'craft')), (), record)
        assert len(encoded) < 2048
        assert history.diagnostics()['page_loads'] == 0
        assert not session.skills._dirty


def test_installation_stitches_eager_path_without_user_notification(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bindings = session._family_bindings
        history = session.skills[1, 'craft'].provenance
        eager = session.world.settlements[1]
        # Bypass user hooks to simulate an independently decoded equal copy.
        dict.__setitem__(eager.memory, 'history', list(range(1000)))
        session._eager_tracker._dirty.clear()
        bindings.install_path(('world.settlements', 1), (('field', 'memory'), ('key', 'history')), history)
        assert eager.memory['history'] is history
        assert not session._eager_tracker._dirty
        bindings.mark_dirty(('world.settlements', 1))
        assert ('world.settlements', 1) in session._eager_tracker._dirty
        assert history.diagnostics()['page_loads'] == 0


def test_dirty_callback_marks_only_requested_lazy_owner(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bindings = session._family_bindings
        bindings.load_owner(('world.skills.skills', (1, 'craft')))
        bindings.mark_dirty(('world.skills.skills', (1, 'craft')))
        assert session.skills._dirty == {(1, 'craft')}
        assert not session._eager_tracker._dirty


def test_owner_callbacks_reject_unknown_families_and_closed_sessions(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    bindings = session._family_bindings
    with pytest.raises(StoreFormatError):
        bindings.load_owner(('world.unknown', 1))
    session.close()
    with pytest.raises(StoreError):
        bindings.load_owner(('world.skills.skills', (1, 'craft')))


def test_installation_rebuilds_immutable_tuple_path_without_notifications(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.skills[1, 'craft'].provenance
        eager = session.world.settlements[1]
        dict.__setitem__(eager.memory, 'tuple', ('fixed', [1]))
        session._eager_tracker._dirty.clear()
        session._family_bindings.install_path(('world.settlements', 1),
            (('field', 'memory'), ('key', 'tuple'), ('index', 1)), history)
        assert eager.memory['tuple'][0] == 'fixed'
        assert eager.memory['tuple'][1] is history
        assert not session._eager_tracker._dirty
        assert history.diagnostics()['page_loads'] == 0
