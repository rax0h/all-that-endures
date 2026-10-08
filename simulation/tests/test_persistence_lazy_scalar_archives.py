from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.transmission import Transmission
from ate_sim.agency import MotiveState
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import (
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.record_index import RecordTable


RULES = "p4-lazy-scalar-archive-tests"


def archive_world():
    world = World(848001)
    world.transmission.records[1] = Transmission(
        1, 1, "teaching", "skill", 7,
        "person", 1, "person", 2, 11, .9, .01,
    )
    world.transmission.records[2] = Transmission(
        2, 2, "teaching", "skill", 7,
        "person", 2, "person", 3, 12, .8, .02,
    )
    world.transmission.records[3] = Transmission(
        3, 3, "institutional_record", "magic_registration", 4,
        "person", 3, "institution_branch", 1, 13, 1.0, 0.0,
    )
    world.transmission.next_id = 4

    world.agency.motives[1] = MotiveState(
        .1, .2, .3, .4, .5, .6, .7, .8
    )
    world.agency.motives[2] = MotiveState(
        .2, .3, .4, .5, .6, .7, .8, .9
    )
    return world


def converted(tmp_path):
    source = tmp_path / "scalar-cold.sqlite"
    lazy = tmp_path / "scalar-lazy.sqlite"
    write_cold_snapshot(archive_world(), source, rules_id=RULES)
    convert_cold_to_lazy(source, lazy, rules_id=RULES)
    return lazy


def test_scalar_archives_open_and_query_lazily(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.transmissions.diagnostics()["payload_loads"] == 0
        assert session.motives.diagnostics()["payload_loads"] == 0

        history = session.world.transmission.history("skill", 7)
        assert [row.id for row in history] == [1, 2]
        assert session.transmissions.diagnostics()["payload_loads"] == 2

        motive = session.world.agency.motives[2]
        assert motive.status == .9
        assert session.motives.diagnostics()["payload_loads"] == 1


def test_scalar_archive_direct_edits_save_and_reopen(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        transmission = session.world.transmission.records[1]
        transmission.reliability = .55
        transmission.item_id = 9

        motive = session.world.agency.motives[1]
        motive.wealth = .95

        assert session.world.transmission.history("skill", 7)[0].id == 2
        assert [row.id for row in session.world.transmission.history("skill", 9)] == [1]

        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.transmission.records[1].reliability == .55
        assert [row.id for row in reopened.world.transmission.history("skill", 7)] == [2]
        assert [row.id for row in reopened.world.transmission.history("skill", 9)] == [1]
        assert reopened.world.agency.motives[1].wealth == .95


def test_scalar_archive_delete_reinsert_order(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        motives = session.world.agency.motives
        assert tuple(motives) == (1, 2)
        del motives[1]
        motives[1] = MotiveState(.9, .8, .7, .6, .5, .4, .3, .2)
        assert tuple(motives) == (2, 1)
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert tuple(reopened.world.agency.motives) == (2, 1)
        assert reopened.world.agency.motives[1].hunger == .9


def test_scalar_archive_noop_and_detach_are_portable(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    generation = session.pin.captured_head
    assert session.save() == generation

    detached = session.detach(materialize_history=True)
    assert isinstance(detached.transmission.records, RecordTable)
    assert isinstance(detached.agency.motives, RecordTable)
    assert [row.id for row in detached.transmission.history("skill", 7)] == [1, 2]

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert [row.id for row in restored.transmission.history("skill", 7)] == [1, 2]
