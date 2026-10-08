import sqlite3

import pytest

from ate_sim import Simulation, generate_world
from ate_sim.core import World, Person
from ate_sim.agency import ActionRecord
from ate_sim.persistence_adapters import (
    AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY,
    write_snapshot, read_snapshot,
)
from ate_sim.persistence_tracking import bind_snapshot, TrackedDict, TrackedList, TrackedSet
from ate_sim.incremental_store import StoreError
from ate_sim.magic_resources import MagicResource

RULES = "stage-0.5-p2b-tests"


def snap(tmp_path, world):
    path = tmp_path / "world.sqlite"
    write_snapshot(world, path, rules_id=RULES)
    return path


def test_noop_and_single_nested_wallet_write_only_owner(tmp_path):
    w = World(1)
    w.currency.wallets = {1: {"iron": 3}, 2: {"iron": 4}, 3: {"iron": 5}}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        assert isinstance(w.currency.wallets[1], TrackedDict)
        session.reset_diagnostics()
        generation = session.save()
        assert generation == 1
        assert session.diagnostics().payload_writes == 0

        w.currency.wallets[2]["iron"] += 7
        assert session.dirty == {("world.currency.wallets", 2)}
        session.reset_diagnostics()
        assert session.save() == 2
        stats = session.diagnostics()
        assert stats.payload_writes == 1
        assert stats.payload_reads == 0

    r = read_snapshot(path, rules_id=RULES)
    assert r.currency.wallets[1] == {"iron": 3}
    assert r.currency.wallets[2] == {"iron": 11}
    assert r.currency.wallets[3] == {"iron": 5}


def test_nested_container_operations_and_retained_aliases_are_tracked(tmp_path):
    w = World(2)
    w.currency.wallets = {1: {"iron": 1}}
    w.households[1] = __import__("ate_sim.core", fromlist=["Household"]).Household(1, 1, [1, 2, 3])
    w.genealogy.children = {1: [2, 3]}
    w.social.adjacency = {1: {2, 3}}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        wallet = w.currency.wallets[1]
        members = w.households[1].members
        children = w.genealogy.children[1]
        neighbors = w.social.adjacency[1]

        wallet.setdefault("bronze", 2)
        wallet |= {"silver": 1}
        wallet.pop("bronze")
        members[1:2] = [7, 8]
        members.sort(reverse=True)
        children += [4]
        neighbors.update({4, 5})
        neighbors.difference_update({2})

        assert ("world.currency.wallets", 1) in session.dirty
        assert ("world.households", 1) in session.dirty
        assert ("world.genealogy.children", 1) in session.dirty
        assert ("world.social.adjacency", 1) in session.dirty
        session.save()

    r = read_snapshot(path, rules_id=RULES)
    assert r.currency.wallets[1] == {"iron": 1, "silver": 1}
    assert r.households[1].members == [8, 7, 3, 1]
    assert r.genealogy.children[1] == [2, 3, 4]
    assert r.social.adjacency[1] == {3, 4, 5}


def test_plain_dataclass_scalar_assignment_and_recordtable_notification_coexist(tmp_path):
    w = Simulation(generate_world(11, mature=True)).run(2)
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        pid = next(iter(w.people))
        person = w.people[pid]
        w.people.ids("alive", True)
        person.alive = False
        assert pid not in w.people.ids("alive", True)
        sid = next(iter(w.local))
        w.local[sid].rain += .01
        assert ("world.people", pid) in session.dirty
        assert ("world.local", sid) in session.dirty
        session.save()
    r = read_snapshot(path, rules_id=RULES)
    assert not r.people[pid].alive
    assert r.local[sid].rain == w.local[sid].rain


def test_currency_transfer_dirties_both_wallet_records_atomically(tmp_path):
    w = World(3)
    w.currency.wallets = {1: {"iron": 10}, 2: {"iron": 1}, 3: {"iron": 99}}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        w.currency.transfer(1, 2, {"iron": 4})
        assert session.dirty == {
            ("world.currency.wallets", 1),
            ("world.currency.wallets", 2),
        }
        session.reset_diagnostics()
        session.save()
        assert session.diagnostics().payload_writes == 2
    r = read_snapshot(path, rules_id=RULES)
    assert r.currency.wallets[1]["iron"] == 6
    assert r.currency.wallets[2]["iron"] == 5
    assert r.currency.wallets[3]["iron"] == 99


def test_resource_transfer_tracks_resource_and_both_owner_index_entries(tmp_path):
    w = World(4)
    r = MagicResource(1, "essence", "fire", "Common", 1, "person", 1)
    w.magic_resources.resources = {1: r}
    w.magic_resources.owner_index = {("person", 1): {1}}
    w.magic_resources.next_id = 2
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        w.magic_resources.transfer(1, "person", 2, 77, location=2)
        assert ("world.magic_resources.resources", 1) in session.dirty
        assert ("world.magic_resources.owner_index", ("person", 1)) in session.deleted
        assert ("world.magic_resources.owner_index", ("person", 2)) in session.dirty
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    rr = restored.magic_resources.resources[1]
    assert (rr.owner_kind, rr.owner_id, rr.location, rr.transfers) == ("person", 2, 2, [77])
    assert ("person", 1) not in restored.magic_resources.owner_index
    assert restored.magic_resources.owner_index[("person", 2)] == {1}


def test_root_insertion_deletion_and_order_roundtrip(tmp_path):
    w = World(5)
    w.people = {7: Person(7, 0, 1, 1), 2: Person(2, 0, 1, 1)}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        del w.people[7]
        w.people[9] = Person(9, 1, 1, 1)
        session.save()
    r = read_snapshot(path, rules_id=RULES)
    assert list(r.people) == [2, 9]


def test_new_cross_owner_mutable_alias_is_rejected(tmp_path):
    w = World(6)
    w.currency.wallets = {1: {"iron": 1}, 2: {"iron": 2}}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES):
        with pytest.raises(StoreError, match="shared mutable"):
            w.currency.wallets[2] = w.currency.wallets[1]


def test_existing_shared_identity_mutation_marks_every_owner(tmp_path):
    w = World(7)
    shared = {"iron": 3}
    w.currency.wallets = {1: shared, 2: shared}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        assert w.currency.wallets[1] is w.currency.wallets[2]
        w.currency.wallets[1]["iron"] += 1
        assert session.dirty == {
            ("world.currency.wallets", 1),
            ("world.currency.wallets", 2),
        }
        session.save()
    r = read_snapshot(path, rules_id=RULES)
    assert r.currency.wallets[1] is r.currency.wallets[2]
    assert r.currency.wallets[1]["iron"] == 4


def test_failed_commit_retains_dirtiness_and_retry_succeeds(tmp_path, monkeypatch):
    w = World(8)
    w.currency.wallets = {1: {"iron": 3}}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        w.currency.wallets[1]["iron"] = 8
        original = session.store._phase_hook
        def fail(phase):
            if phase == "before_commit":
                raise OSError("injected")
            return original(phase)
        monkeypatch.setattr(session.store, "_phase_hook", fail)
        with pytest.raises(OSError, match="injected"):
            session.save()
        assert session.dirty == {("world.currency.wallets", 1)}
        monkeypatch.setattr(session.store, "_phase_hook", original)
        session.save()
        assert not session.dirty
    assert read_snapshot(path, rules_id=RULES).currency.wallets[1]["iron"] == 8


def test_lost_ack_is_resolved_without_duplicate_generation(tmp_path, monkeypatch):
    w = World(9)
    w.currency.wallets = {1: {"iron": 3}}
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        w.currency.wallets[1]["iron"] = 9
        original = session.store._phase_hook
        seen = {"raised": False}
        def fail(phase):
            if phase == "after_commit" and not seen["raised"]:
                seen["raised"] = True
                raise OSError("lost ack")
            return original(phase)
        monkeypatch.setattr(session.store, "_phase_hook", fail)
        assert session.save() == 2
        assert session.generation == 2
        assert not session.dirty
        monkeypatch.setattr(session.store, "_phase_hook", original)
        assert session.save() == 2
    assert read_snapshot(path, rules_id=RULES).currency.wallets[1]["iron"] == 9


def test_packed_agency_prefix_trim_is_one_logical_change(tmp_path):
    w = World(10)
    w.agency.actions = [
        ActionRecord(i, i + 1, "work", "wealth", 0.5, None)
        for i in range(12)
    ]
    path = snap(tmp_path, w)
    with bind_snapshot(w, path, rules_id=RULES) as session:
        session.reset_diagnostics()
        del w.agency.actions[:-5]
        assert [a.year for a in w.agency.actions] == [7, 8, 9, 10, 11]
        assert session.dirty == {
            (AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY)
        }
        assert session._changed_member_work == 1
        session.save()

    restored = read_snapshot(path, rules_id=RULES)
    assert [a.year for a in restored.agency.actions] == [7, 8, 9, 10, 11]


def test_one_real_year_incremental_save_restores_identical_world_and_continues(tmp_path):
    w = Simulation(generate_world(843000, mature=True)).run(5)
    path = snap(tmp_path, w)
    session = bind_snapshot(w, path, rules_id=RULES)
    try:
        Simulation(w).run(1)
        before = w.digest()
        assert session.dirty or session.deleted
        session.save()
    finally:
        session.close()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.digest() == before
    assert Simulation(restored).run(2).digest() == Simulation(w).run(2).digest()
