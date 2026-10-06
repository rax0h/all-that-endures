from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.persistence_lazy import (
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.skills import SkillHistory


RULES = "p4-lazy-skill-tests"


def skill_world():
    world = World(849001)
    world.skills.skills[(1, "craft")] = SkillHistory(
        1, "craft", level=.25, practice=2.0,
        teachers=[9], provenance=[101, 102],
    )
    world.skills.skills[(2, "craft")] = SkillHistory(
        2, "craft", level=.10, practice=.5,
        teachers=[], provenance=[103],
    )
    world.skills.skills[(3, "agriculture")] = SkillHistory(
        3, "agriculture", level=.4, practice=4.0,
        teachers=[8], provenance=[104],
    )
    return world


def converted(tmp_path):
    source = tmp_path / "skills-cold.sqlite"
    lazy = tmp_path / "skills-lazy.sqlite"
    write_cold_snapshot(skill_world(), source, rules_id=RULES)
    convert_cold_to_lazy(source, lazy, rules_id=RULES)
    return lazy


def test_skills_open_lazy_and_point_get_is_bounded(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills.diagnostics()["skill_payload_loads"] == 0
        skill = session.world.skills.get(1, "craft")
        assert skill.level == .25
        assert skill.teachers == [9]
        assert skill.provenance == [101, 102]
        assert session.skills.diagnostics()["skill_payload_loads"] == 1


def test_skill_practice_and_teach_save_reopen(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        practiced = session.world.skills.practice(
            1, "craft", 1.5, event_id=201
        )
        taught = session.world.skills.teach(
            1, 2, "craft", .8, event_id=202
        )
        assert practiced > .25
        assert taught > .10
        assert 1 in session.world.skills.get(2, "craft").teachers
        assert session.world.skills.get(1, "craft").provenance[-1] == 201
        assert session.world.skills.get(2, "craft").provenance[-1] == 202
        generation = session.pin.captured_head
        assert session.save() == generation + 1

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        one = reopened.world.skills.get(1, "craft")
        two = reopened.world.skills.get(2, "craft")
        assert one.level == practiced
        assert one.provenance[-1] == 201
        assert two.level == taught
        assert 1 in two.teachers
        assert two.provenance[-1] == 202


def test_skill_direct_scalar_and_nested_replacement_persist(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        skill = session.world.skills.get(1, "craft")
        skill.level = .91
        old_teachers = skill.teachers
        skill.teachers = [7, 8]
        skill.provenance.append(303)
        assert old_teachers is not skill.teachers
        session.save()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        skill = reopened.world.skills.get(1, "craft")
        assert skill.level == .91
        assert skill.teachers == [7, 8]
        assert skill.provenance == [101, 102, 303]


def test_skill_noop_and_materializing_detach_are_portable(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    generation = session.pin.captured_head
    assert session.save() == generation

    retained = session.world.skills.get(1, "craft")
    retained_teachers = retained.teachers
    detached = session.detach(materialize_history=True)

    assert type(detached.skills.skills) is dict
    assert type(detached.skills.skills[(1, "craft")].teachers) is list
    assert type(detached.skills.skills[(1, "craft")].provenance) is list
    assert detached.skills.skills[(1, "craft")] is retained
    assert detached.skills.skills[(1, "craft")].teachers is not retained_teachers

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.skills.get(1, "craft").teachers == [9]
