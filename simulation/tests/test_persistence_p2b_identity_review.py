import pytest

from ate_sim.core import World
from ate_sim.persistence_adapters import read_snapshot, write_snapshot
from ate_sim.persistence_tracking import bind_snapshot
from ate_sim.persistence_identity import IdentityOccurrenceIndex
from ate_sim.incremental_store import StoreIntegrityError

RULES = "stage-0.5-p2b-identity-review"


def test_identity_delta_replay_after_double_digit_saves_and_rebind(tmp_path):
    world = World(812)
    world.currency.wallets = {1: {"a": {"value": 1}}}
    path = snap(tmp_path, world, "many-deltas.sqlite")
    # Rebind partway through; the store must replay numeric sequence order both
    # when restoring and when constructing a new incremental session.
    for start, stop in ((0, 12), (12, 24)):
        with bind_snapshot(world, path, rules_id=RULES) as session:
            for i in range(start, stop):
                row = world.currency.wallets[1]
                if i % 2 == 0:
                    row["b"] = row["a"]
                else:
                    del row["b"]
                row["a"]["value"] = i
                session.save()
                restored = read_snapshot(path, rules_id=RULES)
                saved = restored.currency.wallets[1]
                assert saved["a"]["value"] == i
                if i % 2 == 0:
                    assert saved["a"] is saved["b"]
                else:
                    assert "b" not in saved
        world = read_snapshot(path, rules_id=RULES)


@pytest.mark.parametrize("keys", [[1], [0, 0], [0, 2], [-1], [True], ["0"]])
def test_identity_delta_replay_rejects_invalid_sequence(keys):
    from ate_sim.persistence_adapters import _fold_identity_deltas, WorldCodec

    rows = [(key, ("identity-delta/v1", (), ()), 1) for key in keys]
    with pytest.raises(StoreIntegrityError):
        _fold_identity_deltas([], rows, WorldCodec())


def test_structural_saves_do_not_rewrite_bootstrap_aliases(tmp_path):
    from ate_sim.persistence_adapters import META

    sizes = []
    for count in (100, 300, 1000):
        world = World(813)
        for i in range(count):
            shared = {"value": i}
            world.currency.wallets[i] = {"a": shared, "b": shared}
        world.currency.wallets[-1] = {"iron": 1}
        path = snap(tmp_path, world, f"structural-{count}.sqlite")
        with bind_snapshot(world, path, rules_id=RULES) as session:
            before = session.store.read_record(META, "manifest")
            session.reset_diagnostics()
            del world.currency.wallets[-1]
            session.save()
            stats = session.diagnostics()
            assert stats.payload_writes == 1
            sizes.append(stats.payload_write_bytes)
            assert session.store.read_record(META, "manifest") == before
        restored = read_snapshot(path, rules_id=RULES)
        assert -1 not in restored.currency.wallets
        assert restored.currency.wallets[0]["a"] is restored.currency.wallets[0]["b"]
        with bind_snapshot(restored, path, rules_id=RULES) as session:
            restored.currency.wallets[-2] = {"iron": 3}
            session.save()
        final = read_snapshot(path, rules_id=RULES)
        assert list(final.currency.wallets) == list(range(count)) + [-2]
        assert final.currency.wallets[-2] == {"iron": 3}
    # The only size variation is the decimal collection count in fixed-schema
    # layout metadata, independent of the number of bootstrap identity links.
    assert max(sizes) - min(sizes) <= 2
    assert max(sizes) < 10000


def test_invalid_live_collection_layout_is_rejected(tmp_path):
    from ate_sim.persistence_adapters import META, COLLECTION_LAYOUT
    from ate_sim.incremental_store import RecordChange, StoreFormatError

    world = World(814)
    path = snap(tmp_path, world, "invalid-layout.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        world.currency.wallets[1] = {"iron": 1}
        session.save()
        layout = session.store.read_record(META, COLLECTION_LAYOUT)
        del layout["world.currency.wallets"]
        session.store.commit(session.generation,
                             [RecordChange(META, COLLECTION_LAYOUT, layout)], (),
                             session.store.head_metadata())
    with pytest.raises(StoreFormatError):
        read_snapshot(path, rules_id=RULES)
    with pytest.raises(StoreFormatError):
        bind_snapshot(world, path, rules_id=RULES)


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_identity_delta_and_live_layout_commit_together(tmp_path, monkeypatch, phase):
    from ate_sim.persistence_adapters import IDENTITY_DELTAS

    world = World(815)
    world.currency.wallets = {1: {"a": {"value": 1}}}
    path = snap(tmp_path, world, f"atomic-{phase}.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        world.currency.wallets[1]["b"] = world.currency.wallets[1]["a"]
        world.currency.wallets[2] = {"iron": 2}
        original = session.store._phase_hook

        def fail(current):
            if current == phase:
                raise OSError("injected identity commit failure")
            return original(current)

        monkeypatch.setattr(session.store, "_phase_hook", fail)
        if phase == "before_commit":
            with pytest.raises(OSError, match="injected"):
                session.save()
            old = read_snapshot(path, rules_id=RULES)
            assert list(old.currency.wallets) == [1]
            assert "b" not in old.currency.wallets[1]
            monkeypatch.setattr(session.store, "_phase_hook", original)
            assert session.save() == 2
        else:
            assert session.save() == 2  # lost acknowledgement is resolved
            monkeypatch.setattr(session.store, "_phase_hook", original)
        assert session.save() == 2  # no duplicate delta on retry/no-op
        assert len(session.store.read_records(IDENTITY_DELTAS)) == 1
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["a"] is restored.currency.wallets[1]["b"]
    assert restored.currency.wallets[2] == {"iron": 2}


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
