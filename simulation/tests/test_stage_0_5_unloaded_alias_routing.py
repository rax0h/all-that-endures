"""A loaded alias must publish through every current, including cold, owner."""

from dataclasses import replace

import pytest

from ate_sim.core import Person, World
from ate_sim.persistence_lazy import (
    LAZY_WALLET_SCHEMA,
    WALLET_NAMESPACE,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot


@pytest.mark.parametrize("edited_owner", [1, 2])
@pytest.mark.parametrize("first_reopened_owner", [1, 2])
def test_shared_wallet_mutation_publishes_unloaded_current_owner(
    tmp_path, edited_owner, first_reopened_owner
):
    rules = "stage-0-5-unloaded-alias-routing"
    world = World(123)
    shared = {"iron": 1}
    world.currency.wallets[1] = shared
    world.currency.wallets[2] = shared
    source, path = tmp_path / "cold.sqlite", tmp_path / "lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=rules)
    convert_cold_to_lazy(source, path, rules_id=rules)

    with open_lazy_world_session(path, rules_id=rules) as session:
        edited = session.wallets[edited_owner]
        assert dict.__len__(session.wallets) == 1
        edited["iron"] = 9
        session.save()
        for key in (1, 2):
            stored = session.store.read_version(
                session.pin, WALLET_NAMESPACE, key,
                expected_record_schema=LAZY_WALLET_SCHEMA,
            )
            assert stored.value["iron"] == 9

    with open_lazy_world_session(path, rules_id=rules) as session:
        first = session.wallets[first_reopened_owner]
        second = session.wallets[3 - first_reopened_owner]
        assert first is second
        assert first["iron"] == 9


def _person_wallet_store(tmp_path):
    rules = "stage-0-5-nested-person-routing"
    world = World(123)
    person = Person(id=1, born=0, settlement=1, household=1, wealth=1.0)
    world.people[1] = person
    world.next_person = 2
    world.currency.wallets[99] = {"person": person}
    source, path = tmp_path / "cold.sqlite", tmp_path / "lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=rules)
    convert_cold_to_lazy(source, path, rules_id=rules)
    return path, rules


@pytest.mark.parametrize("edited_side", ["people", "wallet"])
@pytest.mark.parametrize("first_reopened_side", ["people", "wallet"])
def test_person_edit_publishes_every_containing_payload_owner(
    tmp_path, edited_side, first_reopened_side
):
    path, rules = _person_wallet_store(tmp_path)
    with open_lazy_world_session(path, rules_id=rules) as session:
        person = (
            session.people[1] if edited_side == "people"
            else session.wallets[99]["person"]
        )
        person.wealth = 4.0
        session.save()
        stored_wallet = session.store.read_version(
            session.pin, WALLET_NAMESPACE, 99,
            expected_record_schema=LAZY_WALLET_SCHEMA,
        )
        assert stored_wallet.value["person"].wealth == 4.0

    with open_lazy_world_session(path, rules_id=rules) as session:
        if first_reopened_side == "people":
            first, second = session.people[1], session.wallets[99]["person"]
        else:
            first, second = session.wallets[99]["person"], session.people[1]
        assert first is second
        assert first.wealth == 4.0


@pytest.mark.parametrize("operation", ["assign", "update"])
@pytest.mark.parametrize("first_reopened_side", ["people", "wallet"])
def test_equal_distinct_nested_replacement_publishes_identity_split(
    tmp_path, operation, first_reopened_side
):
    path, rules = _person_wallet_store(tmp_path)
    with open_lazy_world_session(path, rules_id=rules) as session:
        wallet = session.wallets[99]
        old = wallet["person"]
        replacement = replace(old)
        assert replacement == old and replacement is not old
        if operation == "assign":
            wallet["person"] = replacement
        else:
            wallet.update(person=replacement)
        before = session.pin.captured_head
        session.save()
        assert session.pin.captured_head == before + 1

    with open_lazy_world_session(path, rules_id=rules) as session:
        if first_reopened_side == "people":
            first, second = session.people[1], session.wallets[99]["person"]
        else:
            first, second = session.wallets[99]["person"], session.people[1]
        assert first == second and first is not second


@pytest.mark.parametrize("operation", ["assign", "update"])
def test_retained_person_after_wallet_replacement_does_not_mutate_replacement(
    tmp_path, operation
):
    path, rules = _person_wallet_store(tmp_path)
    with open_lazy_world_session(path, rules_id=rules) as session:
        wallet = session.wallets[99]
        retained = wallet["person"]
        replacement = replace(retained)
        if operation == "assign":
            wallet["person"] = replacement
        else:
            wallet.update(person=replacement)
        retained.wealth = 7.0
        assert replacement.wealth == 1.0
        session.save()

    with open_lazy_world_session(path, rules_id=rules) as session:
        assert session.wallets[99]["person"].wealth == 1.0
        assert session.people[1].wealth == 7.0
        assert session.wallets[99]["person"] is not session.people[1]


@pytest.mark.parametrize("phase", ["during_version_writes", "before_commit", "after_commit"])
def test_shared_wallet_failure_resolves_one_generation_and_preserves_both_owners(
    tmp_path, phase
):
    rules = "stage-0-5-shared-owner-recovery"
    world = World(123)
    world.currency.wallets[1] = world.currency.wallets[2] = {"iron": 1}
    source, path = tmp_path / "cold.sqlite", tmp_path / "lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=rules)
    convert_cold_to_lazy(source, path, rules_id=rules)
    with open_lazy_world_session(path, rules_id=rules) as session:
        before = session.pin.captured_head
        session.wallets[1]["iron"] = 9

        def fail(current_phase):
            if current_phase == phase:
                raise OSError("shared owner publication fault")

        session.store._phase_hook = fail
        with pytest.raises(OSError, match="shared owner publication fault"):
            session.save()
        session.store._phase_hook = lambda current_phase: None
        resolved = session.resolve_save()
        if phase == "after_commit":
            assert resolved == before + 1
        else:
            assert resolved == before
            for key in (1, 2):
                stored = session.store.read_version(
                    session.pin, WALLET_NAMESPACE, key,
                    expected_record_schema=LAZY_WALLET_SCHEMA,
                )
                assert stored.value["iron"] == 1
            assert session.save() == before + 1
        for key in (1, 2):
            stored = session.store.read_version(
                session.pin, WALLET_NAMESPACE, key,
                expected_record_schema=LAZY_WALLET_SCHEMA,
            )
            assert stored.value["iron"] == 9

    with open_lazy_world_session(path, rules_id=rules) as session:
        assert session.wallets[2] is session.wallets[1]
        assert session.wallets[2]["iron"] == 9


@pytest.mark.parametrize("history", [1_000, 10_000])
def test_shared_wallet_mutation_routes_only_its_two_owners(tmp_path, history):
    rules = "stage-0-5-owner-route-scaling"
    world = World(123)
    world.currency.wallets[1] = world.currency.wallets[2] = {"iron": 1}
    for key in range(3, history + 3):
        world.currency.wallets[key] = {"iron": 1}
    source, path = tmp_path / "cold.sqlite", tmp_path / "lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=rules)
    convert_cold_to_lazy(source, path, rules_id=rules)
    with open_lazy_world_session(path, rules_id=rules) as session:
        shared = session.wallets[1]
        assert session.wallets._loads == 1
        original = session._registry.live_bindings

        def forbidden():
            raise AssertionError("mutation routed through every live incarnation")

        session._registry.live_bindings = forbidden
        shared["iron"] = 9
        session._registry.live_bindings = original
        assert session.wallets._loads == 2
        assert session.wallets._dirty == {1, 2}
        assert dict.__len__(session.wallets) == 2
        before = session.store.diagnostics()
        session.save()
        after = session.store.diagnostics()
        assert after.payload_writes - before.payload_writes <= 8
        assert after.payload_write_bytes - before.payload_write_bytes < 16_384
