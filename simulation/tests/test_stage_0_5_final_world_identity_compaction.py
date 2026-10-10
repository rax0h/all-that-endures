"""Real World saves compact eligible identity groups without a second writer."""
import gc
import pytest

from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy_identity_catalog import GROUP_NAMESPACE, CATALOG_NAMESPACES
from ate_sim.persistence_history_retirement import pending_retirement, NAMESPACE as RETIREMENT, SCOPES
from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


def test_world_compacts_groups_after_backing_retirement_on_real_saves(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        session.save()
        del child
        gc.collect()
        commit, batches = session.store.commit, []
        def record(*args, **kwargs):
            batches.append(kwargs['version_changes'])
            assert kwargs['cleanup_budget'] == 128
            return commit(*args, **kwargs)
        session.store.commit = record
        for _ in range(24):
            session.world.year += 1
            before = session.store.diagnostics().maintenance_removed_rows
            session.save()
            catalog_rows = sum(c.namespace in CATALOG_NAMESPACES for c in batches[-1])
            backing_rows = sum(c.namespace in {RETIREMENT, DEPENDENCIES,
                *(ns for scopes in SCOPES.values() for ns in scopes)} for c in batches[-1])
            assert catalog_rows <= 32 and backing_rows <= 96
            removed = session.store.diagnostics().maintenance_removed_rows - before
            assert catalog_rows + backing_rows + removed <= 256
            if not session.store.contains_lazy_key(session.pin, GROUP_NAMESPACE, inc):
                break
        else:
            raise AssertionError('real World saves never compacted the retired group')
        assert not pending_retirement(session.store, session.pin, inc)
        assert coord.catalog.read_identity_group(session.pin, inc).occurrences == ()
        session.store.verify_all()
        pin = session.pin
        assert session.save() == pin.captured_head
        assert session.pin == pin


def test_world_keeps_retained_history_group_then_can_reattach_same_identity(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        session.save()
        for _ in range(6):
            session.world.year += 1
            session.save()
            assert session.store.contains_lazy_key(session.pin, GROUP_NAMESPACE, inc)
        session.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=child)
        child.append(99)
        session.save()
        assert session.skills[3, 'craft'].provenance is child
        assert coord.catalog.read_identity_group(session.pin, inc).occurrences == (
            ('world.skills.skills', (3, 'craft'), (('field', 'provenance'),)),)


def test_world_revives_retained_record_from_compacted_range_in_joint_publication(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        record = session.skills[1, 'craft']
        inc = session._registry.incarnation_for_object(record).value
        child = record.provenance
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        session.save()
        for _ in range(8):
            session.world.year += 1
            session.save()
            if not session.store.contains_lazy_key(session.pin, GROUP_NAMESPACE, inc):
                break
        else:
            raise AssertionError('retained record group was not compacted')
        assert child[-1] == 31
        session.skills[1, 'craft'] = record
        child.append(99)
        session.save()
        assert session._registry.incarnation_for_object(record).value == inc
        assert coord.catalog.read_identity_group(session.pin, inc).occurrences == (
            ('world.skills.skills', (1, 'craft'), ()),)
        session.store.verify_all()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[-1] == 99


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_world_identity_compaction_joins_exact_save_recovery(tmp_path, phase):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        record = session.skills[1, 'craft']
        inc = session._registry.incarnation_for_object(record).value
        del session.skills[1, 'craft']
        session.save()
        del record
        gc.collect()
        # Advance the retention floor without assuming it can move past pins.
        session.world.year += 1
        session.save()
        session.world.year += 1
        def fail(at):
            if at == phase:
                raise OSError('identity compaction fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='identity compaction fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert not session.store.contains_lazy_key(session.pin, GROUP_NAMESPACE, inc)
        assert coord.catalog.read_identity_group(session.pin, inc).occurrences == ()
        assert coord.pin == session.pin
