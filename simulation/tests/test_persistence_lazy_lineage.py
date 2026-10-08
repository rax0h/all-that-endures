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


def test_lineage_children_open_lazy_and_bucket_payload_is_small(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        diag = session.lineage_children.diagnostics()
        assert diag["lineage_child_bucket_payload_loads"] == 0
        session.store.reset_diagnostics()
        bucket = session.world.lineage.children[("practice", 1)]
        store_diag = session.store.diagnostics()
        assert bucket == {("practice", 2)}
        assert store_diag.payload_reads == 1
        assert session.lineage_children.diagnostics()[
            "lineage_child_bucket_payload_loads"
        ] == 1


def test_lineage_register_adds_sharded_child_without_loading_parent_bucket(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.lineage_children.diagnostics()[
            "lineage_child_bucket_payload_loads"
        ] == 0
        generation = session.pin.captured_head
        session.world.lineage.register(
            "practice", 4, (("practice", 1),), 104, 4
        )
        assert session.lineage_children.diagnostics()[
            "lineage_child_bucket_payload_loads"
        ] == 0
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert ("practice", 4) in reopened.world.lineage.children[
            ("practice", 1)
        ]
        assert reopened.world.lineage.nodes[
            ("practice", 4)
        ].parents == (("practice", 1),)


def test_lineage_child_remove_save_reopen(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        bucket = session.world.lineage.children[("practice", 1)]
        bucket.remove(("practice", 2))
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.lineage.children[("practice", 1)] == set()


def test_lineage_child_shared_alias_survives_save_reopen_and_mutation(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        shared = session.world.lineage.children[("practice", 1)]
        session.world.lineage.children[("practice", 9)] = shared
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as session:
        first = session.world.lineage.children[("practice", 1)]
        second = session.world.lineage.children[("practice", 9)]
        assert first is second
        first.add(("practice", 8))
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        first = reopened.world.lineage.children[("practice", 1)]
        second = reopened.world.lineage.children[("practice", 9)]
        assert first is second
        assert ("practice", 8) in first
        assert ("practice", 8) in second


def test_lineage_child_materializing_detach_restores_plain_shared_sets(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    shared = session.world.lineage.children[("practice", 1)]
    session.world.lineage.children[("practice", 9)] = shared

    detached = session.detach(materialize_history=True)
    assert type(detached.lineage.children) is dict
    assert type(detached.lineage.children[("practice", 1)]) is set
    assert (
        detached.lineage.children[("practice", 1)]
        is detached.lineage.children[("practice", 9)]
    )

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert (
        restored.lineage.children[("practice", 1)]
        is restored.lineage.children[("practice", 9)]
    )


def test_lineage_children_noop_save_is_free(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        generation = session.pin.captured_head
        assert session.save() == generation


def test_lineage_add_to_unloaded_bucket_can_be_read_before_save(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.lineage_children.diagnostics()[
            "lineage_child_bucket_payload_loads"
        ] == 0
        session.world.lineage.register(
            "practice", 4, (("practice", 1),), 104, 4
        )
        assert session.lineage_children.diagnostics()[
            "lineage_child_bucket_payload_loads"
        ] == 0
        assert session.world.lineage.children[("practice", 1)] == {
            ("practice", 2),
            ("practice", 4),
        }
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.lineage.children[("practice", 1)] == {
            ("practice", 2),
            ("practice", 4),
        }
