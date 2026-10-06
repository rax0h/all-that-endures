from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot


RULES = "p4-12a-genealogy-parent-tests"


def genealogy_world():
    world = World(851001)
    world.genealogy.birth(3, (1, 2))
    world.genealogy.birth(4, (2, 3))
    world.genealogy.birth(5, (4,))
    return world


def converted(tmp_path):
    cold = tmp_path / "genealogy-cold.sqlite"
    lazy = tmp_path / "genealogy-lazy.sqlite"
    write_cold_snapshot(genealogy_world(), cold, rules_id=RULES)
    convert_cold_to_lazy(cold, lazy, rules_id=RULES)
    return lazy


def test_genealogy_parents_open_lazy_and_ancestors_are_point_bounded(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        diag = session.genealogy_parents.diagnostics()
        assert diag["genealogy_parent_payload_loads"] == 0
        assert session.world.genealogy.ancestors(5) == {1, 2, 3, 4}
        diag = session.genealogy_parents.diagnostics()
        assert diag["genealogy_parent_payload_loads"] == 3
        assert diag["resident_genealogy_parents"] == 3


def test_genealogy_birth_saves_lazy_parents_and_eager_children_together(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.genealogy.birth(6, (3, 4))
        assert session.world.genealogy.parents[6] == (3, 4)
        assert 6 in session.world.genealogy.children[3]
        assert 6 in session.world.genealogy.children[4]
        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.genealogy.parents[6] == (3, 4)
        assert 6 in reopened.world.genealogy.children[3]
        assert 6 in reopened.world.genealogy.children[4]


def test_genealogy_parent_replace_save_reopen_and_noop(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.genealogy.parents[5] = (3,)
        generation = session.pin.captured_head
        assert session.save() == generation + 1
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.genealogy.parents[5] == (3,)


def test_genealogy_parent_delete_reinsert_preserves_dict_order(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert list(session.world.genealogy.parents) == [3, 4, 5]
        del session.world.genealogy.parents[4]
        session.world.genealogy.parents[4] = (1,)
        assert list(session.world.genealogy.parents) == [3, 5, 4]
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert list(reopened.world.genealogy.parents) == [3, 5, 4]
        assert reopened.world.genealogy.parents[4] == (1,)


def test_genealogy_parent_materializing_detach_restores_plain_dict(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    detached = session.detach(materialize_history=True)
    assert type(detached.genealogy.parents) is dict
    assert detached.genealogy.ancestors(5) == {1, 2, 3, 4}

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.genealogy.ancestors(5) == {1, 2, 3, 4}



def test_genealogy_children_open_lazy_and_point_lookup(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        diag = session.genealogy_children.diagnostics()
        assert diag["bucket_payload_loads"] == 0
        assert session.world.genealogy.children[2] == [3, 4]
        diag = session.genealogy_children.diagnostics()
        assert diag["bucket_payload_loads"] == 1
        assert diag["resident_buckets"] == 1


def test_genealogy_birth_updates_parents_and_children_atomically(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.genealogy.birth(6, (3, 4))
        assert session.world.genealogy.parents[6] == (3, 4)
        assert session.world.genealogy.children[3][-1] == 6
        assert session.world.genealogy.children[4][-1] == 6
        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.genealogy.parents[6] == (3, 4)
        assert reopened.world.genealogy.children[3][-1] == 6
        assert reopened.world.genealogy.children[4][-1] == 6


def test_genealogy_children_shared_alias_survives_save_reopen_and_detach(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        shared = session.world.genealogy.children[2]
        session.world.genealogy.children[9] = shared
        shared.append(10)
        assert session.world.genealogy.children[9] is shared
        session.save()

    session = open_lazy_world_session(path, rules_id=RULES)
    first = session.world.genealogy.children[2]
    second = session.world.genealogy.children[9]
    assert first is second
    assert first[-1] == 10

    detached = session.detach(materialize_history=True)
    assert type(detached.genealogy.children) is dict
    assert detached.genealogy.children[2] is detached.genealogy.children[9]
    assert detached.genealogy.children[2][-1] == 10
