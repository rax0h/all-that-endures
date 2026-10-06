from types import SimpleNamespace

from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.persistence_lazy import (
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.social import Relationship


RULES = "p4-lazy-social-tests"


def social_world():
    world = World(848001)
    world.social.record(
        1, 2, 101, trust=.1, attachment=.2, obligation=.05
    )
    world.social.record(
        1, 3, 102, trust=.2, attachment=.1
    )
    world.social.record(
        4, 5, 103, trust=.3, attachment=.3
    )
    world.social.partner(1, 2, 201)
    world.social.partner(4, 5, 202)
    return world


def converted(tmp_path):
    source = tmp_path / "social-cold.sqlite"
    lazy = tmp_path / "social-lazy.sqlite"
    write_cold_snapshot(social_world(), source, rules_id=RULES)
    convert_cold_to_lazy(source, lazy, rules_id=RULES)
    return lazy


def living(*ids):
    return [SimpleNamespace(id=pid, alive=True) for pid in ids]


def test_social_opens_lazy_and_endpoint_queries_are_bounded(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.social_edges.diagnostics()["social_edge_payload_loads"] == 0
        assert (
            session.social_adjacency.diagnostics()[
                "social_adjacency_payload_loads"
            ]
            == 0
        )
        assert (
            session.social_partnerships.diagnostics()[
                "social_partnership_payload_loads"
            ]
            == 0
        )

        relationships = list(session.world.social.relationships_for(1))
        assert [(r.a, r.b) for r in relationships] == [(1, 2), (1, 3)]
        assert session.social_edges.diagnostics()["social_edge_payload_loads"] == 2

        assert set(session.world.social.neighbors(1)) == {2, 3}
        assert (
            session.social_adjacency.diagnostics()[
                "social_adjacency_payload_loads"
            ]
            == 1
        )

        assert session.world.social.living_partnerships(living(1, 2)) == {
            (1, 2): 201
        }
        assert (
            session.social_partnerships.diagnostics()[
                "social_partnership_payload_loads"
            ]
            == 1
        )


def test_simulation_run_reuses_pinned_social_memberships_and_overlays_unsaved_changes(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        lifetime = session.world.__dict__["_ate_persistence_lifetime"]
        lifetime.begin_run()
        try:
            lifetime.begin_step()
            try:
                first_relationships = [
                    (r.a, r.b)
                    for r in session.world.social.relationships_for(1)
                ]
                first_partnerships = session.world.social.living_partnerships(
                    living(1, 2, 4, 5)
                )
            finally:
                lifetime.end_step()

            assert first_relationships == [(1, 2), (1, 3)]
            assert first_partnerships == {(1, 2): 201, (4, 5): 202}

            session.store.reset_diagnostics()
            lifetime.begin_step()
            try:
                second_relationships = [
                    (r.a, r.b)
                    for r in session.world.social.relationships_for(1)
                ]
                second_partnerships = session.world.social.living_partnerships(
                    living(1, 2, 4, 5)
                )
            finally:
                lifetime.end_step()
            warm = session.store.diagnostics()

            assert second_relationships == first_relationships
            assert second_partnerships == first_partnerships
            assert warm.query_rows == 0

            # Cached baseline membership is not current-state authority.
            # Unsaved local edits are overlaid before query results are exposed.
            session.world.social.record(1, 6, 303, trust=.1)
            session.world.social.partner(1, 6, 304)
            session.store.reset_diagnostics()
            assert [
                (r.a, r.b)
                for r in session.world.social.relationships_for(1)
            ] == [(1, 2), (1, 3), (1, 6)]
            assert session.world.social.living_partnerships(
                living(1, 2, 4, 5, 6)
            ) == {(1, 2): 201, (1, 6): 304, (4, 5): 202}
            assert session.store.diagnostics().query_rows == 0
        finally:
            lifetime.end_run()

        assert len(session.social_edges._person_query_cache) <= 256
        assert len(session.social_partnerships._person_query_cache) <= 256


def test_social_mutation_save_and_reopen(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        edge = session.world.social.get(1, 2)
        edge.trust = .91
        edge.shared_history.append(999)

        neighbors = session.world.social.adjacency[1]
        neighbors.add(9)

        session.world.social.partnerships[(1, 2)] = 777
        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        edge = reopened.world.social.get(1, 2)
        assert edge.trust == .91
        assert edge.shared_history[-1] == 999
        assert set(reopened.world.social.neighbors(1)) == {2, 3, 9}
        assert reopened.world.social.partnerships[(1, 2)] == 777
        assert reopened.world.social.living_partnerships(
            living(1, 2)
        ) == {(1, 2): 777}


def test_social_get_record_creates_edge_and_adjacency_lazily(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        edge = session.world.social.get(6, 7)
        assert isinstance(edge, Relationship)
        assert edge.a == 6 and edge.b == 7
        session.world.social.record(
            6, 7, 888, trust=.15, attachment=.25
        )
        assert set(session.world.social.neighbors(6)) == {7}
        assert set(session.world.social.neighbors(7)) == {6}
        assert [(r.a, r.b) for r in session.world.social.relationships_for(6)] == [
            (6, 7)
        ]
        session.world.social.partner(6, 7, 889)
        assert session.world.social.living_partnerships(
            living(6, 7)
        ) == {(6, 7): 889}
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        edge = reopened.world.social.get(6, 7)
        assert edge.shared_history == [888]
        assert edge.trust == .65
        assert edge.attachment == .25
        assert set(reopened.world.social.neighbors(6)) == {7}
        assert reopened.world.social.living_partnerships(
            living(6, 7)
        ) == {(6, 7): 889}


def test_social_noop_and_materializing_detach_are_portable(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    generation = session.pin.captured_head
    assert session.save() == generation

    retained = session.world.social.get(1, 2)
    retained_history = retained.shared_history
    detached = session.detach(materialize_history=True)

    assert type(detached.social.edges) is dict
    assert type(detached.social.adjacency) is dict
    assert type(detached.social.partnerships) is dict
    assert type(detached.social.edges[(1, 2)].shared_history) is list
    assert detached.social.edges[(1, 2)] is retained
    assert detached.social.edges[(1, 2)].shared_history is not retained_history
    assert detached.social.living_partnerships(living(1, 2)) == {
        (1, 2): 201
    }

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.social.living_partnerships(living(1, 2)) == {
        (1, 2): 201
    }
