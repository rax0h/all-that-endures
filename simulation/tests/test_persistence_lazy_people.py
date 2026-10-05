import hashlib

import pytest

from ate_sim import Simulation, generate_world
from ate_sim.core import Person, World
from ate_sim.incremental_store import (
    StoreConflictError,
    StoreError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import SCHEMA, WorldCodec
from ate_sim.persistence_lazy import (
    PEOPLE_NAMESPACE,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_session import write_cold_snapshot


RULES = "stage-0.5-p4-lazy-people-tests"


def people_world(count, *, active=8, seed=843000):
    world = World(seed)
    world.year = 11
    for person_id in range(1, count + 1):
        world.people[person_id] = Person(
            id=person_id,
            born=0,
            settlement=1,
            household=1,
            alive=person_id <= active,
            age=11,
            wealth=float(person_id % 13),
        )
    world.next_person = count + 1
    return world


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_p4(path):
    return LazyRecordStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )


def test_cold_to_lazy_conversion_preserves_source_and_current_authority(tmp_path):
    world = people_world(25, active=5)
    source = tmp_path / "cold.sqlite"
    destination = tmp_path / "lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    before = digest_file(source)

    result = convert_cold_to_lazy(source, destination, rules_id=RULES)
    assert digest_file(source) == before
    assert result["source_preserved"] is True
    assert result["people"] == 25
    assert result["destination_format"] == 3

    with TransactionalStore.open(
        source,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    ) as cold, open_p4(destination) as lazy:
        assert cold.checked_head().metadata == lazy.checked_head().metadata
        assert cold.checked_head().namespace_counts == lazy.checked_head().namespace_counts
        assert lazy.db.execute(
            "SELECT COUNT(*) FROM records WHERE namespace=?",
            (PEOPLE_NAMESPACE,),
        ).fetchone() == (0,)
        assert lazy.storage_metrics()["lazy_record_versions"] == 25
        assert lazy.verify_all()["identity_occurrences"] >= 25


def test_open_lazy_world_decodes_zero_people_until_requested(tmp_path):
    source = tmp_path / "cold.sqlite"
    destination = tmp_path / "lazy.sqlite"
    write_cold_snapshot(people_world(300, active=7), source, rules_id=RULES)
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        people = session.world.people
        assert type(people).__name__ == "LazyRecordTable"
        assert len(people) == 300
        assert people.diagnostics()["person_payload_loads"] == 0
        assert people.diagnostics()["resident_people"] == 0

        session.store.reset_diagnostics()
        person = people[200]
        diag = session.store.diagnostics()
        assert person.id == 200
        assert diag.payload_reads == 1
        assert people.diagnostics()["person_payload_loads"] == 1
        assert people.diagnostics()["resident_people"] == 1


def test_lazy_people_iteration_preserves_source_dictionary_order(tmp_path):
    world = people_world(275, active=9)
    source = tmp_path / "cold.sqlite"
    destination = tmp_path / "lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.store.reset_diagnostics()
        keys = tuple(session.world.people)
        assert keys == tuple(world.people)
        diag = session.store.diagnostics()
        assert diag.temporary_keys_peak <= 128
        # Key traversal validates bodies but never decodes Person values.
        assert diag.payload_reads == 0
        assert session.world.people.diagnostics()["person_payload_loads"] == 0


@pytest.mark.parametrize("count", [1000, 10000])
def test_fixed_active_current_people_decodes_only_active_payloads(tmp_path, count):
    active = 8
    source = tmp_path / f"cold-{count}.sqlite"
    destination = tmp_path / f"lazy-{count}.sqlite"
    write_cold_snapshot(
        people_world(count, active=active),
        source,
        rules_id=RULES,
    )
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        assert session.world.people.diagnostics()["person_payload_loads"] == 0

        session.store.reset_diagnostics()
        living = session.world.current_people()
        first = session.store.diagnostics()
        assert tuple(person.id for person in living) == tuple(
            range(1, active + 1)
        )
        assert first.payload_reads == active
        assert first.query_rows == active
        assert first.payload_check_reads == active * 2
        assert session.world.people.diagnostics()["person_payload_loads"] == active
        assert session.world.people.diagnostics()["resident_people"] == active

        session.store.reset_diagnostics()
        living_again = session.world.current_people()
        warm = session.store.diagnostics()
        assert tuple(person.id for person in living_again) == tuple(
            range(1, active + 1)
        )
        assert warm.payload_reads == 0
        assert warm.query_rows == active
        assert session.world.people.diagnostics()["person_payload_loads"] == active
        assert session.world.people.diagnostics()["resident_people"] == active


def test_lazy_people_cache_is_bounded_and_reuses_external_alias_by_incarnation(tmp_path):
    source = tmp_path / "cold.sqlite"
    destination = tmp_path / "lazy.sqlite"
    write_cold_snapshot(people_world(400, active=10), source, rules_id=RULES)
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        retained = session.world.people[1]
        for key in range(2, 400):
            session.world.people[key]
        diag = session.world.people.diagnostics()
        assert diag["clean_cache_entries"] <= 256
        assert diag["resident_people"] <= 256

        # Person 1 was evicted from the table cache, but an external alias keeps
        # its weak-registry incarnation alive and reaccess returns that instance.
        assert session.world.people[1] is retained



def converted_people_store(tmp_path, count=30, *, active=8, name="write"):
    source = tmp_path / f"{name}-cold.sqlite"
    destination = tmp_path / f"{name}-lazy.sqlite"
    write_cold_snapshot(
        people_world(count, active=active),
        source,
        rules_id=RULES,
    )
    convert_cold_to_lazy(source, destination, rules_id=RULES)
    return destination


def test_people_scalar_edit_save_reopen_and_true_noop(tmp_path):
    destination = converted_people_store(tmp_path, 40, active=6)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        start = session.pin.captured_head
        person = session.world.people[20]
        person.wealth += 17.5

        session.store.reset_diagnostics()
        assert session.save() == start + 1
        diag = session.store.diagnostics()
        # One Person payload plus bounded cold descriptor publication; no
        # unrelated Person payload is decoded during publication.
        assert diag.payload_reads <= 7
        assert diag.payload_writes <= 3
        assert session.diagnostics()["state"] == "active"

        # A notification whose final encoded value equals the committed
        # baseline must remain a true no-op.
        person.wealth = person.wealth
        before_person_loads = session.world.people.diagnostics()[
            "person_payload_loads"
        ]
        session.store.reset_diagnostics()
        assert session.save() == start + 1
        no_op = session.store.diagnostics()
        assert no_op.payload_reads <= 3
        assert no_op.payload_writes == 0
        assert session.world.people.diagnostics()[
            "person_payload_loads"
        ] == before_person_loads

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.people.diagnostics()["person_payload_loads"] == 0
        assert reopened.world.people[20].wealth == pytest.approx(
            float(20 % 13) + 17.5
        )


def test_people_delete_reinsert_same_object_preserves_incarnation_and_moves_order(tmp_path):
    destination = converted_people_store(tmp_path, 4, active=4)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        person = session.world.people[1]
        before = session.store.read_identity_occurrence(
            session.pin, PEOPLE_NAMESPACE, 1, ()
        ).incarnation_id
        del session.world.people[1]
        session.world.people[1] = person

        assert tuple(session.world.people) == (2, 3, 4, 1)
        session.save()
        after = session.store.read_identity_occurrence(
            session.pin, PEOPLE_NAMESPACE, 1, ()
        ).incarnation_id
        assert after == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert tuple(reopened.world.people) == (2, 3, 4, 1)
        assert reopened.store.read_identity_occurrence(
            reopened.pin, PEOPLE_NAMESPACE, 1, ()
        ).incarnation_id == before


def test_distinct_equal_replacement_gets_new_incarnation_and_old_alias_detaches(tmp_path):
    destination = converted_people_store(tmp_path, 5, active=5)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        old = session.world.people[2]
        before = session.store.read_identity_occurrence(
            session.pin, PEOPLE_NAMESPACE, 2, ()
        ).incarnation_id
        replacement = Person(
            id=old.id,
            born=old.born,
            settlement=old.settlement,
            household=old.household,
            alive=old.alive,
            age=old.age,
            wealth=old.wealth,
            health=old.health,
            temperament=old.temperament,
            attachment=old.attachment,
            curiosity=old.curiosity,
            inhibition=old.inhibition,
            grief=old.grief,
            fear=old.fear,
            rank=old.rank,
            species=old.species,
            occupation=old.occupation,
            parents=old.parents,
        )
        session.world.people[2] = replacement
        old.wealth += 500.0
        assert session.world.people[2] is replacement
        assert session.world.people[2].wealth != old.wealth
        session.save()
        after = session.store.read_identity_occurrence(
            session.pin, PEOPLE_NAMESPACE, 2, ()
        ).incarnation_id
        assert after != before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        restored = reopened.world.people[2]
        assert restored.wealth == replacement.wealth
        assert reopened.store.read_identity_occurrence(
            reopened.pin, PEOPLE_NAMESPACE, 2, ()
        ).incarnation_id == after


def test_people_insert_delete_updates_manifest_order_and_query_membership(tmp_path):
    destination = converted_people_store(tmp_path, 3, active=2)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.people[4] = Person(
            id=4,
            born=11,
            settlement=1,
            household=1,
            alive=True,
            age=0,
            wealth=2.0,
        )
        session.world.next_person = 5
        del session.world.people[2]
        assert tuple(session.world.people) == (1, 3, 4)
        assert tuple(p.id for p in session.world.current_people()) == (1, 4)
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert len(reopened.world.people) == 3
        assert tuple(reopened.world.people) == (1, 3, 4)
        assert tuple(p.id for p in reopened.world.current_people()) == (1, 4)
        assert reopened.manifest["collections"][PEOPLE_NAMESPACE][1] == 3
        assert reopened.world.next_person == 5


def test_evicted_external_current_person_mutation_rehydrates_owner_and_saves(tmp_path):
    destination = converted_people_store(tmp_path, 400, active=10)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        retained = session.world.people[1]
        for key in range(2, 400):
            session.world.people[key]
        assert not dict.__contains__(session.world.people, 1)

        retained.wealth += 9.0
        assert dict.__contains__(session.world.people, 1)
        assert session.world.people.diagnostics()["dirty_people"] == 1
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.people[1].wealth == pytest.approx(
            float(1 % 13) + 9.0
        )


@pytest.mark.parametrize("count", [1000, 10000])
def test_one_people_edit_write_work_does_not_follow_historical_population(tmp_path, count):
    destination = converted_people_store(
        tmp_path, count, active=8, name=f"write-scale-{count}"
    )
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        person = session.world.people[1]
        person.wealth += 1.0
        session.store.reset_diagnostics()
        session.save()
        diag = session.store.diagnostics()
        assert diag.payload_reads <= 7
        assert diag.payload_writes <= 3
        assert diag.payload_check_reads <= 10
        assert diag.query_rows <= 4
        assert session.world.people.diagnostics()["resident_people"] <= 256


def test_people_save_precommit_failure_resolves_old_and_retries(tmp_path):
    destination = converted_people_store(tmp_path, 25, active=5)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        start = session.pin.captured_head
        person = session.world.people[3]
        person.wealth += 4.0

        def fail(phase):
            if phase == "during_version_writes":
                raise OSError("people publication failed")

        session.store._phase_hook = fail
        with pytest.raises(OSError, match="people publication failed"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"

        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start
        assert session.diagnostics()["state"] == "active"
        assert person.wealth == pytest.approx(float(3 % 13) + 4.0)

        assert session.save() == start + 1

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.people[3].wealth == pytest.approx(
            float(3 % 13) + 4.0
        )


def test_people_lost_ack_resolves_committed_successor_exactly_once(tmp_path):
    destination = converted_people_store(tmp_path, 25, active=5)
    session = open_lazy_world_session(destination, rules_id=RULES)
    try:
        start = session.pin.captured_head
        session.world.people[4].wealth += 6.0

        def lose_ack(phase):
            if phase == "after_commit":
                raise OSError("people acknowledgement lost")

        session.store._phase_hook = lose_ack
        with pytest.raises(OSError, match="people acknowledgement lost"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"

        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start + 1
        assert session.diagnostics()["state"] == "active"
        assert session.resolve_save() == start + 1
    finally:
        session.close()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.people[4].wealth == pytest.approx(
            float(4 % 13) + 6.0
        )


def test_competing_people_writer_marks_loser_stale_and_preflights_future_mutation(tmp_path):
    destination = converted_people_store(tmp_path, 20, active=5)
    first = open_lazy_world_session(destination, rules_id=RULES)
    second = open_lazy_world_session(destination, rules_id=RULES)
    try:
        first.world.people[1].wealth += 1.0
        second_person = second.world.people[2]
        second_person.wealth += 2.0
        assert first.save() == first.pin.captured_head

        with pytest.raises(StoreConflictError):
            second.save()
        assert second.diagnostics()["state"] == "stale"

        before = second_person.wealth
        with pytest.raises(StoreConflictError):
            second_person.wealth += 1.0
        assert second_person.wealth == before
        with pytest.raises(StoreConflictError):
            second.save()
    finally:
        second.close()
        first.close()


def test_hybrid_lazy_session_runs_one_real_step_and_reopens_equal_to_eager_control(tmp_path):
    seed = 918273
    control = generate_world(
        seed, width=8, height=6, settlements=1
    )
    source_world = generate_world(
        seed, width=8, height=6, settlements=1
    )
    # The real-step fixture needs the canonical event-id set to match the
    # generated event stream before entering the already-accepted P3B writer.
    # This isolates the P4 hybrid continuation proof from a pre-existing
    # worldgen/cold-bootstrap event_ids discrepancy.
    control.event_ids = {event.id for event in control.events}
    source_world.event_ids = {
        event.id for event in source_world.events
    }
    source = tmp_path / "hybrid-step-cold.sqlite"
    destination = tmp_path / "hybrid-step-lazy.sqlite"
    write_cold_snapshot(source_world, source, rules_id=RULES)
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    Simulation(control).step()
    expected_digest = control.digest()

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        assert session.world.people.diagnostics()["person_payload_loads"] == 0
        Simulation(session.world).step()
        assert session.world.digest() == expected_digest
        generation = session.save()
        assert generation == session.pin.captured_head
        diag = session.diagnostics()
        assert diag["state"] == "active"
        assert diag["people"]["resident_people"] <= 256

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.digest() == expected_digest


def test_cross_boundary_person_alias_restores_lazily_and_eager_mutation_fails_closed(tmp_path):
    world = people_world(4, active=4)
    shared_person = world.people[1]
    world.currency.wallets[99] = {"person": shared_person}
    source = tmp_path / "cross-cold.sqlite"
    destination = tmp_path / "cross-lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        assert session.world.people.diagnostics()["person_payload_loads"] == 0
        eager_alias = session.world.currency.wallets[99]["person"]
        assert session.diagnostics()["cross_boundary_identity_links"] >= 1
        loaded = session.world.people[1]
        assert loaded is eager_alias
        before = loaded.wealth
        with pytest.raises(StoreError, match="crosses world.people"):
            loaded.wealth += 1.0
        assert loaded.wealth == before
