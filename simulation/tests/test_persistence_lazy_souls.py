import pytest

from ate_sim import checkpoint
from ate_sim.core import Person, World
from ate_sim.engine import Simulation
from ate_sim.incremental_store import StoreConflictError
from ate_sim.metaphysics import attempt_transcendence, grant_resurrection_token
from ate_sim.persistence_lazy import (
    SOUL_NAMESPACE,
    LazySoulTable,
    LazySoulTrackedList,
    LazySoulTrackedSet,
    LazyTrackedDict,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot


RULES = "stage-0.5-p4-lazy-soul-tests"
AUTH_PATH = (("field", "authorities"),)
MARK_PATH = (("field", "marks"),)
LINK_PATH = (("field", "cosmic_links"),)
TRANSFORM_PATH = (("field", "transformations"),)


def soul_world(count, *, shared_marks=False):
    world = World(843000)
    shared = {"shared"} if shared_marks else None
    for pid in range(1, count + 1):
        soul = world.metaphysics.soul(pid)
        soul.origin_world = f"world-{pid % 7}"
        soul.death_count = pid % 5
        soul.authorities.add(f"authority:{pid % 11}")
        soul.marks.add(f"mark:{pid % 13}")
        soul.cosmic_links[f"link:{pid % 17}"] = (pid % 10) / 10
        soul.transformations.append(pid)
        if shared_marks and pid in (1, 2):
            soul.marks = shared
    return world


def converted(tmp_path, count, *, shared_marks=False, name="souls"):
    source = tmp_path / f"{name}-cold.sqlite"
    destination = tmp_path / f"{name}-lazy.sqlite"
    write_cold_snapshot(
        soul_world(count, shared_marks=shared_marks),
        source,
        rules_id=RULES,
    )
    result = convert_cold_to_lazy(
        source, destination, rules_id=RULES
    )
    assert result["source_preserved"] is True
    assert result["souls"] == count
    assert source.exists()
    return destination


def identity_labels(session, key):
    return {
        path: session.store.read_identity_occurrence(
            session.pin, SOUL_NAMESPACE, key, path
        ).incarnation_id
        for path in ((), AUTH_PATH, MARK_PATH, LINK_PATH, TRANSFORM_PATH)
    }


def test_soul_open_loads_zero_payloads_and_point_access_is_bounded(tmp_path):
    destination = converted(tmp_path, 400)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        souls = session.world.metaphysics.souls
        assert isinstance(souls, LazySoulTable)
        diag = souls.diagnostics()
        assert diag["soul_payload_loads"] == 0
        assert diag["resident_souls"] == 0
        assert len(souls) == 400
        soul = souls[300]
        assert soul.person == 300
        assert souls.diagnostics()["soul_payload_loads"] == 1
        assert souls.diagnostics()["resident_souls"] == 1


def test_scalar_and_all_nested_soul_mutations_save_and_reopen(tmp_path):
    destination = converted(tmp_path, 10, name="mutations")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        soul = session.world.metaphysics.souls[3]
        soul.death_count += 1
        soul.authorities.add("astral:test")
        soul.marks.add("changed")
        soul.cosmic_links["moon"] = .75
        soul.transformations.append(999)
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        soul = reopened.world.metaphysics.souls[3]
        assert soul.death_count == (3 % 5) + 1
        assert "astral:test" in soul.authorities
        assert "changed" in soul.marks
        assert soul.cosmic_links["moon"] == .75
        assert soul.transformations[-1] == 999


def test_retained_nested_aliases_rehydrate_evicted_soul_owner(tmp_path):
    destination = converted(tmp_path, 400, name="retained")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        souls = session.world.metaphysics.souls
        soul = souls[1]
        authorities = soul.authorities
        marks = soul.marks
        links = soul.cosmic_links
        transformations = soul.transformations
        for pid in range(2, 401):
            souls[pid]
        assert not dict.__contains__(souls, 1)
        authorities.add("retained-authority")
        marks.add("retained-mark")
        links["retained-link"] = .9
        transformations.append(7001)
        assert dict.__contains__(souls, 1)
        assert souls[1].authorities is authorities
        assert souls[1].marks is marks
        assert souls[1].cosmic_links is links
        assert souls[1].transformations is transformations
        assert souls.diagnostics()["dirty_souls"] == 1
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        soul = reopened.world.metaphysics.souls[1]
        assert "retained-authority" in soul.authorities
        assert "retained-mark" in soul.marks
        assert soul.cosmic_links["retained-link"] == .9
        assert soul.transformations[-1] == 7001


def test_nested_soul_incarnations_survive_save_and_reopen(tmp_path):
    destination = converted(tmp_path, 8, name="identity")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        soul = session.world.metaphysics.souls[4]
        before = identity_labels(session, 4)
        soul.marks.add("identity-proof")
        soul.cosmic_links["identity"] = .5
        session.save()
        assert identity_labels(session, 4) == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        soul = reopened.world.metaphysics.souls[4]
        assert identity_labels(reopened, 4) == before
        assert isinstance(soul.authorities, LazySoulTrackedSet)
        assert isinstance(soul.marks, LazySoulTrackedSet)
        assert isinstance(soul.cosmic_links, LazyTrackedDict)
        assert isinstance(soul.transformations, LazySoulTrackedList)


def test_shared_nested_soul_identity_is_one_live_object(tmp_path):
    destination = converted(
        tmp_path, 10, shared_marks=True, name="shared-nested"
    )
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        souls = session.world.metaphysics.souls
        first = souls[1]
        second = souls[2]
        assert first.marks is second.marks
        first.marks.add("shared-change")
        assert "shared-change" in second.marks
        assert souls.diagnostics()["dirty_souls"] == 2
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        first = reopened.world.metaphysics.souls[1]
        second = reopened.world.metaphysics.souls[2]
        assert first.marks is second.marks
        assert "shared-change" in second.marks


def test_soul_delete_reinsert_preserves_order_and_all_incarnations(tmp_path):
    destination = converted(tmp_path, 4, name="reinsert")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        souls = session.world.metaphysics.souls
        soul = souls[1]
        before = identity_labels(session, 1)
        del souls[1]
        souls[1] = soul
        assert tuple(souls) == (2, 3, 4, 1)
        session.save()
        assert identity_labels(session, 1) == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert tuple(reopened.world.metaphysics.souls) == (2, 3, 4, 1)
        assert identity_labels(reopened, 1) == before


def test_real_death_resurrection_mark_and_transform_paths_persist(tmp_path):
    world = World(843000)
    world.people[1] = Person(
        id=1,
        born=-25,
        settlement=1,
        household=1,
        alive=True,
        age=25,
        wealth=0.0,
        health=1.0,
    )
    soul = world.metaphysics.soul(1)
    soul.marks.add("astral_throne_claimed")
    soul.authorities.add("astral:domain")
    grant_resurrection_token(
        world, 1, "test-patron", "phoenix", ()
    )
    source = tmp_path / "real-paths-cold.sqlite"
    destination = tmp_path / "real-paths-lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.metaphysics.mark(
            1, "moon-mark", "moon-link", .8
        )
        Simulation(session.world)._die(
            session.world.people[1], "persistence-test"
        )
        transformed = attempt_transcendence(
            session.world,
            1,
            "astral_king",
            ("astral:domain",),
        )
        assert transformed is not None
        assert session.world.people[1].alive
        soul = session.world.metaphysics.souls[1]
        assert soul.death_count == 1
        assert soul.resurrection_count == 1
        assert soul.body_generation == 2
        assert soul.ontology == "astral_king"
        assert "resurrected" in soul.marks
        assert "moon-mark" in soul.marks
        assert soul.cosmic_links["moon-link"] == .8
        assert soul.transformations
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        soul = reopened.world.metaphysics.souls[1]
        assert soul.death_count == 1
        assert soul.resurrection_count == 1
        assert soul.body_generation == 2
        assert soul.ontology == "astral_king"
        assert "transcendent" in soul.marks
        assert reopened.world.people[1].alive


def test_soul_noop_save_writes_zero_payloads(tmp_path):
    destination = converted(tmp_path, 30, name="noop")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.metaphysics.souls[7]
        start = session.pin.captured_head
        session.store.reset_diagnostics()
        assert session.save() == start
        assert session.store.diagnostics().payload_writes == 0


def test_soul_precommit_failure_resolves_old_and_retries(tmp_path):
    destination = converted(tmp_path, 20, name="precommit")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        start = session.pin.captured_head
        soul = session.world.metaphysics.souls[3]
        soul.marks.add("precommit")

        def fail(phase):
            if phase == "during_version_writes":
                raise OSError("soul publication failed")

        session.store._phase_hook = fail
        with pytest.raises(OSError, match="soul publication failed"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"
        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start
        assert session.diagnostics()["state"] == "active"
        assert "precommit" in soul.marks
        assert session.save() == start + 1

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert "precommit" in reopened.world.metaphysics.souls[3].marks


def test_soul_lost_ack_resolves_exactly_once(tmp_path):
    destination = converted(tmp_path, 20, name="lost-ack")
    session = open_lazy_world_session(destination, rules_id=RULES)
    try:
        start = session.pin.captured_head
        session.world.metaphysics.souls[4].marks.add("lost-ack")

        def lose_ack(phase):
            if phase == "after_commit":
                raise OSError("soul acknowledgement lost")

        session.store._phase_hook = lose_ack
        with pytest.raises(OSError, match="soul acknowledgement lost"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"
        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start + 1
        assert session.resolve_save() == start + 1
    finally:
        session.close()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert "lost-ack" in reopened.world.metaphysics.souls[4].marks


def test_soul_stale_writer_rejects_future_mutation(tmp_path):
    destination = converted(tmp_path, 12, name="stale")
    first = open_lazy_world_session(destination, rules_id=RULES)
    second = open_lazy_world_session(destination, rules_id=RULES)
    try:
        first.world.metaphysics.souls[1].marks.add("winner")
        second_soul = second.world.metaphysics.souls[2]
        second_soul.marks.add("loser")
        first.save()
        with pytest.raises(StoreConflictError):
            second.save()
        before = second_soul.death_count
        with pytest.raises(StoreConflictError):
            second_soul.death_count += 1
        assert second_soul.death_count == before
    finally:
        second.close()
        first.close()


def test_soul_materializing_detach_preserves_nested_identity_and_checkpoint(
    tmp_path,
):
    destination = converted(
        tmp_path, 300, shared_marks=True, name="detach"
    )
    session = open_lazy_world_session(destination, rules_id=RULES)
    soul1 = session.world.metaphysics.souls[1]
    soul2 = session.world.metaphysics.souls[2]
    shared = soul1.marks
    assert soul2.marks is shared
    for pid in range(3, 301):
        session.world.metaphysics.souls[pid]
    shared.add("detached-shared")

    detached = session.detach(materialize_history=True)
    assert type(detached.metaphysics.souls) is dict
    assert type(detached.metaphysics.souls[1].authorities) is set
    assert type(detached.metaphysics.souls[1].marks) is set
    assert type(detached.metaphysics.souls[1].cosmic_links) is dict
    assert type(detached.metaphysics.souls[1].transformations) is list
    assert detached.metaphysics.souls[1].marks is (
        detached.metaphysics.souls[2].marks
    )
    assert "detached-shared" in detached.metaphysics.souls[2].marks

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.metaphysics.souls[1].marks is (
        restored.metaphysics.souls[2].marks
    )


@pytest.mark.parametrize("count", [1000, 10000])
def test_soul_history_scaling_is_bounded_by_requested_access(tmp_path, count):
    destination = converted(
        tmp_path, count, name=f"scale-{count}"
    )
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        souls = session.world.metaphysics.souls
        open_store = session.store.diagnostics()
        assert souls.diagnostics()["soul_payload_loads"] == 0
        assert souls.diagnostics()["resident_souls"] == 0

        before_reads = session.store.diagnostics()
        soul = souls[7]
        after_reads = session.store.diagnostics()
        assert soul.person == 7
        assert souls.diagnostics()["soul_payload_loads"] == 1
        assert souls.diagnostics()["resident_souls"] == 1

        soul.death_count += 1
        session.store.reset_diagnostics()
        session.save()
        write_diag = session.store.diagnostics()
        identity = session.diagnostics()["identity"]
        soul_diag = souls.diagnostics()

        print(
            "SOUL_METRIC",
            count,
            {
                "open_payload_reads": open_store.payload_reads,
                "open_payload_bytes": open_store.payload_read_bytes,
                "point_payload_reads": (
                    after_reads.payload_reads - before_reads.payload_reads
                ),
                "point_payload_bytes": (
                    after_reads.payload_read_bytes
                    - before_reads.payload_read_bytes
                ),
                "save_payload_writes": write_diag.payload_writes,
                "save_payload_write_bytes": write_diag.payload_write_bytes,
                "resident_souls": soul_diag["resident_souls"],
                "clean_cache_entries": soul_diag["clean_cache_entries"],
                "live_incarnations": identity["live_incarnations"],
                "owner_groups": identity["owner_groups"],
                "pin_rows": write_diag.pin_rows,
            },
        )
        assert (
            after_reads.payload_reads - before_reads.payload_reads
        ) <= 1
        assert soul_diag["resident_souls"] <= 256
        assert write_diag.payload_writes <= 3
