import pytest

from ate_sim.core import World
from ate_sim.persistence_adapters import read_snapshot, write_snapshot
from ate_sim.persistence_tracking import bind_snapshot
from ate_sim.persistence_identity import IdentityOccurrenceIndex

RULES = "stage-0.5-p2b-identity-review"


def snap(tmp_path, world, name):
    path = tmp_path / name
    write_snapshot(world, path, rules_id=RULES)
    return path


@pytest.mark.parametrize("order", [
    ("right", "another"),
    ("another", "right"),
])
def test_i1_parent_and_descendant_sharing_restores_for_key_orders(tmp_path, order):
    world = World(801)
    world.currency.wallets = {1: {"left": {"child": {"value": 1}}}}
    path = snap(tmp_path, world, f"parent-child-{order[0]}.sqlite")

    with bind_snapshot(world, path, rules_id=RULES) as session:
        row = world.currency.wallets[1]
        for key in order:
            if key == "right":
                row["right"] = row["left"]
            else:
                row["another"] = row["left"]["child"]
        session.save()

    restored = read_snapshot(path, rules_id=RULES)
    row = restored.currency.wallets[1]
    assert row["right"] is row["left"]
    assert row["another"] is row["left"]["child"]
    row["another"]["value"] = 7
    assert row["left"]["child"]["value"] == 7
    assert row["right"]["child"]["value"] == 7


def test_i1_parent_descendant_sharing_across_owners_and_two_cycles(tmp_path):
    world = World(802)
    world.currency.wallets = {
        1: {"left": {"child": {"value": 1}}},
        2: {},
        3: {},
    }
    path = snap(tmp_path, world, "across-owners.sqlite")

    with bind_snapshot(world, path, rules_id=RULES) as session:
        world.currency.wallets[2]["parent"] = world.currency.wallets[1]["left"]
        world.currency.wallets[3]["child"] = world.currency.wallets[1]["left"]["child"]
        session.save()

    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[2]["parent"] is restored.currency.wallets[1]["left"]
    assert restored.currency.wallets[3]["child"] is restored.currency.wallets[1]["left"]["child"]

    with bind_snapshot(restored, path, rules_id=RULES) as session:
        restored.currency.wallets[3]["child"]["value"] = 8
        session.save()

    final = read_snapshot(path, rules_id=RULES)
    assert final.currency.wallets[1]["left"]["child"]["value"] == 8
    assert final.currency.wallets[2]["parent"]["child"]["value"] == 8
    assert final.currency.wallets[3]["child"]["value"] == 8


def test_i1_anchor_removal_and_replacement_keep_remaining_graph(tmp_path):
    world = World(803)
    world.currency.wallets = {1: {"left": {"child": {"value": 1}}}}
    path = snap(tmp_path, world, "anchor-change.sqlite")

    with bind_snapshot(world, path, rules_id=RULES) as session:
        row = world.currency.wallets[1]
        row["right"] = row["left"]
        row["another"] = row["left"]["child"]
        session.save()

    restored = read_snapshot(path, rules_id=RULES)
    with bind_snapshot(restored, path, rules_id=RULES) as session:
        row = restored.currency.wallets[1]
        del row["left"]
        row["replacement"] = row["right"]["child"]
        row["another"]["value"] = 11
        session.save()

    final = read_snapshot(path, rules_id=RULES)
    row = final.currency.wallets[1]
    assert "left" not in row
    assert row["replacement"] is row["another"]
    assert row["right"]["child"] is row["another"]
    assert row["another"]["value"] == 11


def test_i1_full_snapshot_parent_descendant_control(tmp_path):
    world = World(804)
    parent = {"child": {"value": 1}}
    world.currency.wallets = {
        1: {"left": parent, "right": parent, "another": parent["child"]}
    }
    path = snap(tmp_path, world, "full-control.sqlite")
    restored = read_snapshot(path, rules_id=RULES)
    row = restored.currency.wallets[1]
    assert row["left"] is row["right"]
    assert row["another"] is row["left"]["child"]


@pytest.mark.parametrize("groups", [100, 300, 1000])
def test_i2_local_alias_change_has_constant_prefix_and_identity_write_work(
    tmp_path, monkeypatch, groups
):
    world = World(810)
    wallets = {}
    for i in range(groups):
        shared = {"value": i}
        wallets[i] = {"a": shared, "b": shared}
    world.currency.wallets = wallets
    path = snap(tmp_path, world, f"scale-{groups}.sqlite")

    with bind_snapshot(world, path, rules_id=RULES) as session:
        calls = {"suffix": 0}
        original = IdentityOccurrenceIndex._suffix

        def counted(path, prefix):
            calls["suffix"] += 1
            return original(path, prefix)

        monkeypatch.setattr(IdentityOccurrenceIndex, "_suffix", staticmethod(counted))
        session.reset_diagnostics()
        world.currency.wallets[0]["c"] = world.currency.wallets[0]["a"]
        session.save()
        stats = session.diagnostics()

        assert calls["suffix"] == 0
        assert stats.payload_writes == 2
        # One wallet envelope plus one small identity-delta record. This must
        # not scale with the unrelated alias groups already in the base manifest.
        assert stats.payload_write_bytes < 20000

    restored = read_snapshot(path, rules_id=RULES)
    row = restored.currency.wallets[0]
    assert row["a"] is row["b"] is row["c"]


@pytest.mark.parametrize("groups", [100, 300, 1000])
def test_i2_local_alias_removal_does_not_touch_unrelated_groups(
    tmp_path, monkeypatch, groups
):
    world = World(811)
    wallets = {}
    for i in range(groups):
        shared = {"value": i}
        wallets[i] = {"a": shared, "b": shared}
    world.currency.wallets = wallets
    path = snap(tmp_path, world, f"remove-{groups}.sqlite")

    with bind_snapshot(world, path, rules_id=RULES) as session:
        calls = {"suffix": 0}
        original = IdentityOccurrenceIndex._suffix

        def counted(path, prefix):
            calls["suffix"] += 1
            return original(path, prefix)

        monkeypatch.setattr(IdentityOccurrenceIndex, "_suffix", staticmethod(counted))
        session.reset_diagnostics()
        del world.currency.wallets[0]["a"]
        session.save()
        stats = session.diagnostics()
        assert calls["suffix"] == 0
        assert stats.payload_writes == 2
        assert stats.payload_write_bytes < 20000

    restored = read_snapshot(path, rules_id=RULES)
    assert "a" not in restored.currency.wallets[0]
    assert restored.currency.wallets[0]["b"]["value"] == 0
    assert restored.currency.wallets[1]["a"] is restored.currency.wallets[1]["b"]
