import hashlib

import pytest

from ate_sim.core import Person, World
from ate_sim.incremental_store import TransactionalStore
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
