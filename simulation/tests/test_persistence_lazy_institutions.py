from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.institutions import (
    MagicUserRecord,
    AdventureNotice,
    SocietyApplication,
)
from ate_sim.persistence_lazy import (
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.record_index import RecordTable


RULES = "p4-lazy-institution-record-tests"


def institution_world():
    world = World(846001)
    world.institutions.magic_records[1] = MagicUserRecord(
        1, 10, 1, 2, ("fire",), "c-a", "A",
        ("ability-a",), ("Ability A",), "full", 11,
    )
    world.institutions.magic_records[2] = MagicUserRecord(
        2, 10, 1, 3, ("water",), "c-b", "B",
        ("ability-b",), ("Ability B",), "essences", 12,
    )
    world.institutions.magic_records[3] = MagicUserRecord(
        3, 11, 1, 1, (), None, None, (), (), "identity", 13,
    )

    world.institutions.notices[1] = AdventureNotice(
        1, 1, 2, "danger", 1, 101, status="open",
    )
    world.institutions.notices[2] = AdventureNotice(
        2, 1, 2, "danger", 1, 102, status="assigned", assigned_to=10,
    )
    world.institutions.notices[3] = AdventureNotice(
        3, 1, 1, "danger", 1, 103, status="resolved", resolved_event=104,
    )

    world.institutions.applications[1] = SocietyApplication(
        1, "magic_society", 10, 1, 2, True,
        stage="screening", passed=None, origin_event=201,
    )
    world.institutions.applications[2] = SocietyApplication(
        2, "magic_society", 10, 1, 1, True,
        stage="passed", passed=True, origin_event=202, resolved_event=203,
    )
    world.institutions.applications[3] = SocietyApplication(
        3, "adventure_society", 11, 1, 1, True,
        stage="failed", passed=False, origin_event=204, resolved_event=205,
    )
    world.institutions.next_record = 4
    world.institutions.next_notice = 4
    world.institutions.next_application = 4
    return world


def converted(tmp_path):
    source = tmp_path / "institutions-cold.sqlite"
    lazy = tmp_path / "institutions-lazy.sqlite"
    write_cold_snapshot(institution_world(), source, rules_id=RULES)
    convert_cold_to_lazy(source, lazy, rules_id=RULES)
    return lazy


def test_institution_records_open_and_query_lazily(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.institution_magic_records.diagnostics()["payload_loads"] == 0
        assert session.institution_notices.diagnostics()["payload_loads"] == 0
        assert session.institution_applications.diagnostics()["payload_loads"] == 0

        record = session.world.institutions.magic_records[1]
        assert record.person == 10
        assert session.institution_magic_records.diagnostics()["payload_loads"] == 1

        records = session.world.institutions.records_for_person(10)
        assert [row.id for row in records] == [1, 2]
        assert session.institution_magic_records.diagnostics()["payload_loads"] == 2

        notices = session.world.institutions.active_notices()
        assert [row.id for row in notices] == [1, 2]
        assert session.institution_notices.diagnostics()["payload_loads"] == 2

        assert session.world.institutions.has_application(
            10, "magic_society"
        )
        latest = session.world.institutions.latest_application(
            10, "magic_society"
        )
        assert latest.id == 2
        assert session.institution_applications.diagnostics()["payload_loads"] == 1


def test_institution_membership_overlay_save_and_reopen(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        notice = session.world.institutions.notices[1]
        notice.status = "resolved"
        assert [row.id for row in session.world.institutions.active_notices()] == [2]

        application = session.world.institutions.applications[1]
        application.passed = True
        application.stage = "passed"
        assert session.world.institutions.has_application(
            10, "magic_society", qualified=True
        )

        record = session.world.institutions.magic_records[3]
        record.person = 10
        assert [row.id for row in session.world.institutions.records_for_person(10)] == [3, 1, 2]

        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.institutions.notices[1].status == "resolved"
        assert [row.id for row in reopened.world.institutions.active_notices()] == [2]
        assert reopened.world.institutions.applications[1].passed is True
        assert reopened.world.institutions.has_application(
            10, "magic_society", qualified=True
        )
        assert [
            row.id
            for row in reopened.world.institutions.records_for_person(10)
        ] == [3, 1, 2]


def test_institution_insert_delete_reinsert_preserves_dict_order(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.world.institutions.notices
        assert tuple(table) == (1, 2, 3)
        del table[2]
        table[2] = AdventureNotice(
            2, 1, 4, "new-danger", 1, 222, status="open"
        )
        assert tuple(table) == (1, 3, 2)
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert tuple(reopened.world.institutions.notices) == (1, 3, 2)
        assert reopened.world.institutions.notices[2].cause_event == 222
        assert [row.id for row in reopened.world.institutions.active_notices()] == [1, 2]


def test_institution_noop_and_materializing_detach_are_portable(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    generation = session.pin.captured_head
    assert session.save() == generation

    detached = session.detach(materialize_history=True)
    assert isinstance(detached.institutions.magic_records, RecordTable)
    assert isinstance(detached.institutions.notices, RecordTable)
    assert isinstance(detached.institutions.applications, RecordTable)
    assert [row.id for row in detached.institutions.active_notices()] == [1, 2]
    assert [row.id for row in detached.institutions.records_for_person(10)] == [1, 2]

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert [row.id for row in restored.institutions.active_notices()] == [1, 2]
