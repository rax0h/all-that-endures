from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot


RULES = "p4-11a-lineage-tests"


def lineage_world():
    world = World(849001)
    world.lineage.register("practice", 1, (), 101, 1)
    world.lineage.register(
        "practice", 2, (("practice", 1),), 102, 2
    )
    world.lineage.register(
        "practice", 3, (("practice", 2),), 103, 3
    )
    return world


def converted(tmp_path):
    cold = tmp_path / "lineage-cold.sqlite"
    lazy = tmp_path / "lineage-lazy.sqlite"
    write_cold_snapshot(lineage_world(), cold, rules_id=RULES)
    convert_cold_to_lazy(cold, lazy, rules_id=RULES)
    return lazy


def test_lineage_nodes_open_lazy_and_ancestor_walk_is_point_bounded(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.lineage_nodes.diagnostics()["payload_loads"] == 0
        ancestors = session.world.lineage.ancestors("practice", 3)
        assert ancestors == {("practice", 1), ("practice", 2)}
        assert session.lineage_nodes.diagnostics()["payload_loads"] == 3
        assert session.lineage_nodes.diagnostics()["resident_records"] == 3


def test_lineage_register_saves_node_and_eager_children_together(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.lineage.register(
            "practice", 4, (("practice", 3),), 104, 4
        )
        assert ("practice", 4) in session.world.lineage.children[
            ("practice", 3)
        ]
        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        node = reopened.world.lineage.nodes[("practice", 4)]
        assert node.parents == (("practice", 3),)
        assert node.origin_event == 104
        assert ("practice", 4) in reopened.world.lineage.children[
            ("practice", 3)
        ]


def test_lineage_direct_edit_save_reopen_and_noop(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        node = session.world.lineage.nodes[("practice", 2)]
        node.origin_year = 22
        generation = session.pin.captured_head
        assert session.save() == generation + 1
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.lineage.nodes[
            ("practice", 2)
        ].origin_year == 22


def test_lineage_materializing_detach_restores_plain_nodes(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    detached = session.detach(materialize_history=True)
    assert type(detached.lineage.nodes) is dict
    assert detached.lineage.ancestors("practice", 3) == {
        ("practice", 1),
        ("practice", 2),
    }

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.lineage.ancestors("practice", 3) == {
        ("practice", 1),
        ("practice", 2),
    }
