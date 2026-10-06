import pytest

from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.incremental_store import StoreConflictError
from ate_sim.persistence_lazy import (
    ADVANCEMENT_NAMESPACE,
    LazyAdvancementPathTable,
    LazySoulTrackedList,
    LazyTrackedDict,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot


RULES = "stage-0.5-p4-lazy-advancement-tests"


def advancement_world(count):
    world = World(843000)
    for pid in range(1, count + 1):
        world.advancement.absorb_essence(
            pid,
            "fire",
            0,
            ("worker", "neutral", f"person-{pid}"),
        )
        world.advancement.awaken_skill(
            pid,
            "eyes",
            1,
            ("worker", pid),
            target_essence="fire",
        )
    return world


def converted(tmp_path, count, *, name="advancement"):
    source = tmp_path / f"{name}-cold.sqlite"
    destination = tmp_path / f"{name}-lazy.sqlite"
    write_cold_snapshot(
        advancement_world(count), source, rules_id=RULES
    )
    result = convert_cold_to_lazy(
        source, destination, rules_id=RULES
    )
    assert result["source_preserved"] is True
    assert result["advancement_paths"] == count
    assert source.exists()
    return destination


def identity_labels(session, key):
    return dict(
        session.store.identity_occurrences_for_owner(
            session.pin, ADVANCEMENT_NAMESPACE, key
        )
    )


def test_advancement_open_zero_payloads_and_point_access_one_path(tmp_path):
    destination = converted(tmp_path, 300)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        paths = session.world.advancement.paths
        assert isinstance(paths, LazyAdvancementPathTable)
        assert paths.diagnostics()["advancement_payload_loads"] == 0
        assert paths.diagnostics()["resident_advancement_paths"] == 0
        assert len(paths) == 300
        path = session.world.advancement.path(200)
        assert path is paths[200]
        assert paths.diagnostics()["advancement_payload_loads"] == 1
        assert paths.diagnostics()["resident_advancement_paths"] == 1


def test_advancement_nested_mutations_save_and_reopen(tmp_path):
    destination = converted(tmp_path, 8, name="nested")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        path = session.world.advancement.path(3)
        ability = path.abilities[0]
        path.core_fraction = .25
        ability.rank = 2
        ability.understanding.integration = .75
        ability.understanding.evidence["use:test"] = 3
        ability.understanding.transfers.append(
            {"event": 7, "difficulty": 2}
        )
        ability.response_model.samples.append(
            {"event": 8, "inputs": [1.0, .5], "response": .7}
        )
        ability.response_model.coefficients.extend([.1, .2])
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        path = reopened.world.advancement.path(3)
        ability = path.abilities[0]
        assert path.core_fraction == .25
        assert ability.rank == 2
        assert ability.understanding.integration == .75
        assert ability.understanding.evidence["use:test"] == 3
        assert ability.understanding.transfers[-1]["event"] == 7
        assert ability.response_model.samples[-1]["event"] == 8
        assert list(ability.response_model.coefficients) == [.1, .2]


def test_retained_advancement_child_rehydrates_evicted_owner(tmp_path):
    destination = converted(tmp_path, 320, name="retained")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        paths = session.world.advancement.paths
        path = paths[1]
        evidence = path.abilities[0].understanding.evidence
        for pid in range(2, 321):
            paths[pid]
        assert not dict.__contains__(paths, 1)
        evidence["retained"] = 9
        assert dict.__contains__(paths, 1)
        assert (
            paths[1].abilities[0].understanding.evidence
            is evidence
        )
        assert paths.diagnostics()["dirty_advancement_paths"] == 1
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert (
            reopened.world.advancement.path(1)
            .abilities[0].understanding.evidence["retained"]
            == 9
        )


def test_shared_advancement_nested_identity_survives_save_reopen(tmp_path):
    destination = converted(tmp_path, 6, name="shared")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        first = session.world.advancement.path(1)
        second = session.world.advancement.path(2)
        shared = first.abilities
        second.abilities = shared
        shared[0].understanding.evidence["shared"] = 1
        assert first.abilities is second.abilities
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        first = reopened.world.advancement.path(1)
        second = reopened.world.advancement.path(2)
        assert first.abilities is second.abilities
        assert first.abilities[0].understanding.evidence["shared"] == 1


def test_advancement_same_path_delete_reinsert_preserves_identity_and_order(
    tmp_path,
):
    destination = converted(tmp_path, 4, name="reinsert")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        paths = session.world.advancement.paths
        path = paths[1]
        before = identity_labels(session, 1)
        del paths[1]
        paths[1] = path
        assert tuple(paths) == (2, 3, 4, 1)
        session.save()
        assert identity_labels(session, 1) == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert tuple(reopened.world.advancement.paths) == (2, 3, 4, 1)
        assert identity_labels(reopened, 1) == before


def test_real_advancement_creation_awaken_and_practice_persist(tmp_path):
    destination = converted(tmp_path, 3, name="real-api")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        path, created = session.world.advancement.absorb_essence(
            99, "fire", 2, ("smith", "neutral", "smith")
        )
        assert created
        ability = session.world.advancement.awaken_skill(
            99, "eyes", 3, ("smith",), target_essence="fire"
        )
        assert ability is not None
        session.world.advancement.practice(
            99, 0, meaningful_use=1.0, reflection=.2
        )
        assert session.world.advancement.essence_user(99)
        assert session.world.advancement.path(99) is path
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        path = reopened.world.advancement.path(99)
        assert path is not None
        assert path.base_essences == ["fire"]
        assert len(path.abilities) == 2
        assert path.abilities[0].progress > 0


def test_advancement_noop_save_writes_zero_payloads(tmp_path):
    destination = converted(tmp_path, 20, name="noop")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.advancement.path(7)
        start = session.pin.captured_head
        session.store.reset_diagnostics()
        assert session.save() == start
        assert session.store.diagnostics().payload_writes == 0


def test_advancement_precommit_failure_resolves_old_and_retries(tmp_path):
    destination = converted(tmp_path, 12, name="precommit")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        start = session.pin.captured_head
        path = session.world.advancement.path(3)
        path.abilities[0].understanding.evidence["precommit"] = 1

        def fail(phase):
            if phase == "during_version_writes":
                raise OSError("advancement publication failed")

        session.store._phase_hook = fail
        with pytest.raises(OSError, match="advancement publication failed"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"
        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start
        assert session.diagnostics()["state"] == "active"
        assert session.save() == start + 1

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert (
            reopened.world.advancement.path(3)
            .abilities[0].understanding.evidence["precommit"]
            == 1
        )


def test_advancement_lost_ack_resolves_exactly_once(tmp_path):
    destination = converted(tmp_path, 12, name="lost-ack")
    session = open_lazy_world_session(destination, rules_id=RULES)
    try:
        start = session.pin.captured_head
        session.world.advancement.path(4).core_fraction = .33

        def lose_ack(phase):
            if phase == "after_commit":
                raise OSError("advancement acknowledgement lost")

        session.store._phase_hook = lose_ack
        with pytest.raises(OSError, match="advancement acknowledgement lost"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"
        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start + 1
        assert session.resolve_save() == start + 1
    finally:
        session.close()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.advancement.path(4).core_fraction == .33


def test_advancement_stale_writer_rejects_future_nested_mutation(tmp_path):
    destination = converted(tmp_path, 10, name="stale")
    first = open_lazy_world_session(destination, rules_id=RULES)
    second = open_lazy_world_session(destination, rules_id=RULES)
    try:
        first.world.advancement.path(1).core_fraction = .2
        loser = second.world.advancement.path(2)
        loser.core_fraction = .3
        first.save()
        with pytest.raises(StoreConflictError):
            second.save()
        before = loser.core_fraction
        with pytest.raises(StoreConflictError):
            loser.core_fraction += .1
        assert loser.core_fraction == before
    finally:
        second.close()
        first.close()


def test_advancement_materializing_detach_preserves_sharing_and_checkpoint(
    tmp_path,
):
    destination = converted(tmp_path, 280, name="detach")
    session = open_lazy_world_session(destination, rules_id=RULES)
    first = session.world.advancement.path(1)
    second = session.world.advancement.path(2)
    second.abilities = first.abilities
    shared = first.abilities
    for pid in range(3, 281):
        session.world.advancement.path(pid)
    shared[0].understanding.evidence["detached"] = 1

    detached = session.detach(materialize_history=True)
    assert type(detached.advancement.paths) is dict
    assert type(detached.advancement.path(1).abilities) is list
    assert type(
        detached.advancement.path(1).abilities[0].understanding.evidence
    ) is dict
    assert detached.advancement.path(1).abilities is (
        detached.advancement.path(2).abilities
    )
    assert (
        detached.advancement.path(2)
        .abilities[0].understanding.evidence["detached"]
        == 1
    )

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.advancement.path(1).abilities is (
        restored.advancement.path(2).abilities
    )
