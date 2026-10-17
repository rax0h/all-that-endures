"""Equal payload replacements must publish their distinct checked identities."""
from dataclasses import replace

import pytest

from ate_sim.agency import MotiveState
from ate_sim.core import Person
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.magic_resources import MagicAspiration
from ate_sim.metaphysics import SoulState
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, RULES


def complete(tmp_path):
    def configure(world):
        world.people[1] = Person(1, 0, 1, 1)
        world.agency.motives[1] = MotiveState(safety=.25)
        world.magic_resources.aspirations[1] = MagicAspiration(.5, 3, 20, 'curiosity', 0)
        world.metaphysics.souls[1] = SoulState(1)
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'complete.sqlite'
    upgrade_lazy_snapshot(source, target, rules_id=RULES)
    return target


@pytest.mark.parametrize('family,key', [
    ('people', 1), ('motives', 1), ('aspirations', 1),
    ('souls', 1), ('skills', (1, 'craft')),
])
def test_equal_replacement_saves_new_identity_and_reopens(tmp_path, family, key):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = getattr(session, family)
        original = table[key]
        old_inc = session._registry.incarnation_for_object(original)
        replacement = replace(original)
        table[key] = replacement
        new_inc = session._registry.incarnation_for_object(replacement)
        assert new_inc != old_inc
        expected_payload = session.store.codec.encode(replacement)
        generation = session.pin.captured_head
        assert session.save() == generation + 1
        assert table[key] is replacement
        assert session.save() == generation + 1
    with open_lazy_world_session(path, rules_id=RULES) as session:
        restored = getattr(session, family)[key]
        assert session._registry.incarnation_for_object(restored) == new_inc
        assert session.store.codec.encode(restored) == expected_payload
        if family == 'people':
            assert session.store.query_memberships(session.pin, 'world.people', 'alive', True) == ((1, 0),)


@pytest.mark.parametrize('phase', ['before_transaction', 'after_commit'])
def test_identity_only_replacement_retries_or_resolves_without_losing_peer_alias(tmp_path, phase):
    def configure(world):
        shared = MotiveState(safety=.25)
        world.agency.motives.update({1: shared, 2: shared})
    source = legacy_lazy(tmp_path, configure=configure)
    path = tmp_path / 'complete.sqlite'
    upgrade_lazy_snapshot(source, path, rules_id=RULES)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        old = session.motives[1]
        assert session.motives[2] is old
        replacement = replace(old)
        session.motives[1] = replacement
        before = session.pin.captured_head
        def fail(at):
            if at == phase:
                raise OSError('identity-only fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='identity-only fault'):
            session.save()
        assert session.store.generation == before + int(phase == 'after_commit')
        session.store._phase_hook = lambda at: None
        assert session.resolve_save() == before + int(phase == 'after_commit')
        assert session.save() == before + 1
        assert session.motives[1] is replacement
        assert session.motives[2] is old
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.motives[1] is not session.motives[2]
        assert session.motives[1].safety == session.motives[2].safety == .25
        session.motives[2].safety = .75
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.motives[1].safety == .25
        assert session.motives[2].safety == .75


def test_suppressed_changed_payload_still_rejects_before_commit(tmp_path, monkeypatch):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.motives[1] = MotiveState(safety=.75)
        original = session.motives.prepare_save_changes
        def omit_payload():
            versions, identities, *rest = original()
            assert versions
            return (), identities, *rest
        monkeypatch.setattr(session.motives, 'prepare_save_changes', omit_payload)
        before = session.pin.captured_head
        with pytest.raises(StoreIntegrityError):
            session.save()
        assert session.store.generation == before
        assert session._identity_coordinator._prepared is None
        assert session._backing_dependencies._prepared is None
        monkeypatch.setattr(session.motives, 'prepare_save_changes', original)
        assert session.save() == before + 1


def test_normal_agency_assessment_can_replace_an_equal_motive(tmp_path):
    from ate_sim.persistence_lazy import convert_cold_to_lazy
    from ate_sim.persistence_session import write_cold_snapshot
    from ate_sim.worldgen import generate_world
    world = generate_world(843000, width=6, height=6, settlements=1)
    pid = next(iter(world.people))
    world.agency.assess(world, world.people[pid], attachment=.5, dependents=0)
    cold, source, target = (tmp_path / name for name in ('cold.sqlite', 'lazy.sqlite', 'complete.sqlite'))
    write_cold_snapshot(world, cold, rules_id=RULES)
    convert_cold_to_lazy(cold, source, rules_id=RULES, native_graph_buckets=True)
    upgrade_lazy_snapshot(source, target, rules_id=RULES)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        before = session.motives[pid]
        after = session.world.agency.assess(session.world, session.people[pid], attachment=.5, dependents=0)
        expected = session.store.codec.encode(before)
        assert after is not before and session.store.codec.encode(after) == expected
        incarnation = session._registry.incarnation_for_object(after)
        session.save()
    with open_lazy_world_session(target, rules_id=RULES) as session:
        assert session._registry.incarnation_for_object(session.motives[pid]) == incarnation
        assert session.store.codec.encode(session.motives[pid]) == expected


def test_missing_recursive_page_and_child_payload_cannot_be_reconstructed(tmp_path, monkeypatch):
    from ate_sim import persistence_lazy_participants as participants
    from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.skills[1, 'craft'].provenance = [MotiveState(safety=.25)]
        session.save()
        root = session.skills[1, 'craft'].provenance
        root[0] = replace(root[0], safety=.75)
        freeze = participants.freeze_hybrid_publication
        def omit_payloads(store, pin, plan, **kwargs):
            changes = tuple(c for c in plan.nested_history_version_changes
                            if c.namespace not in AUXILIARY_OWNER_FAMILIES)
            assert len(changes) < len(plan.nested_history_version_changes)
            return freeze(store, pin, replace(plan, nested_history_version_changes=changes), **kwargs)
        monkeypatch.setattr(participants, 'freeze_hybrid_publication', omit_payloads)
        before = session.pin.captured_head
        with pytest.raises(StoreIntegrityError, match='omits a touched identity owner payload') as rejected:
            session.save()
        assert 'aux.lazy.nested.list_pages' in str(rejected.value)
        assert session.store.generation == before
        assert session._identity_coordinator._prepared is None
        assert session._backing_dependencies._prepared is None
        monkeypatch.setattr(participants, 'freeze_hybrid_publication', freeze)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].provenance[0].safety == .75
