from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot


RULES = "p4-13-community-memberships"


def community_world():
    world = World(861001)
    first = world.communities.create("founder_network", 0, 1)
    second = world.communities.create("craft_circle", 0, 1)
    third = world.communities.create("diaspora", 1, 2, parent=first.id)
    world.communities.join(1, first.id, 0.9)
    world.communities.join(1, second.id, 0.4)
    world.communities.join(2, first.id, 0.7)
    world.communities.join(2, third.id, 0.3)
    return world


def converted(tmp_path):
    cold = tmp_path / "communities-cold.sqlite"
    lazy = tmp_path / "communities-lazy.sqlite"
    write_cold_snapshot(community_world(), cold, rules_id=RULES)
    convert_cold_to_lazy(cold, lazy, rules_id=RULES)
    return lazy


def test_community_memberships_open_lazy_and_person_query_is_bounded(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        diag = session.community_memberships.diagnostics()
        assert diag["community_membership_payload_loads"] == 0
        assert session.world.communities.memberships_for(1) == {
            1: 0.9,
            2: 0.4,
        }
        diag = session.community_memberships.diagnostics()
        assert diag["community_membership_payload_loads"] == 2
        assert diag["resident_community_memberships"] == 2


def test_community_membership_overlay_reflects_join_replace_and_delete(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        memberships = session.world.communities.memberships
        session.world.communities.join(1, 3, 0.6)
        session.world.communities.join(1, 1, 0.8)
        del memberships[(1, 2)]
        assert session.world.communities.memberships_for(1) == {
            1: 0.8,
            3: 0.6,
        }
        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.communities.memberships_for(1) == {
            1: 0.8,
            3: 0.6,
        }


def test_community_membership_delete_reinsert_preserves_dict_order(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        memberships = session.world.communities.memberships
        assert list(memberships) == [(1, 1), (1, 2), (2, 1), (2, 3)]
        del memberships[(1, 2)]
        memberships[(1, 2)] = 0.5
        assert list(memberships) == [(1, 1), (2, 1), (2, 3), (1, 2)]
        assert session.world.communities.memberships_for(1) == {
            1: 0.9,
            2: 0.5,
        }
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert list(reopened.world.communities.memberships) == [
            (1, 1),
            (2, 1),
            (2, 3),
            (1, 2),
        ]


def test_community_inherit_uses_lazy_person_query_and_saves(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        inherited = session.world.communities.inherit(4, (1, 2), weight=0.5)
        assert inherited == {1: 0.45, 2: 0.2, 3: 0.15}
        assert session.world.communities.memberships_for(4) == inherited
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.communities.memberships_for(4) == {
            1: 0.45,
            2: 0.2,
            3: 0.15,
        }


def test_community_membership_noop_save_is_free(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        generation = session.pin.captured_head
        assert session.save() == generation


def test_community_membership_materializing_detach_restores_plain_dict(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    session.world.communities.join(1, 3, 0.55)
    detached = session.detach(materialize_history=True)

    assert type(detached.communities.memberships) is dict
    assert detached.communities.memberships_for(1) == {
        1: 0.9,
        2: 0.4,
        3: 0.55,
    }

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.communities.memberships_for(1) == {
        1: 0.9,
        2: 0.4,
        3: 0.55,
    }
