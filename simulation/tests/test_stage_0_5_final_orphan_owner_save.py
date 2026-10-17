"""A removed history owner cannot publish its private child placement edits."""
from dataclasses import replace

import pytest

from ate_sim.core import Ref
from ate_sim.advancement import EssencePath
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES
from simulation.tests.test_stage_0_5_final_identity_only_headers import complete


@pytest.mark.parametrize('kind', ['list', 'map'])
@pytest.mark.parametrize('remove', ['replace', 'delete'])
def test_changed_orphan_keeps_saved_projection_and_revives_private_child(tmp_path, kind, remove):
    path = complete(tmp_path)
    key = (1, 'craft') if kind == 'list' else Ref('person', 1)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        if kind == 'list':
            table = session.skills
            table[key].provenance = [[1]]
            root = table[key].provenance
            namespace, slot = PAGE_NAMESPACE, 0
        else:
            table = session.wallets
            table[key] = {'child': [1]}
            root = table[key]
            namespace, slot = ENTRY_NAMESPACE, 'child'
        session.save()
        physical_key = (root._incarnation, slot)
        if kind == 'map':
            physical_key = next(key for key in session.store.iter_keys(session.pin, namespace)
                                if key[0] == root._incarnation)
        original = session.store.read_version(session.pin, namespace, physical_key,
                                             expected_record_schema=1).value
        original_group = session._identity_coordinator.catalog.read_owner_identity(
            session.pin, (namespace, physical_key))
        try:
            original_placements = tuple(original_group.occurrences)
        finally:
            if hasattr(original_group.occurrences, 'close'):
                original_group.occurrences.close()
        root[0 if kind == 'list' else 'child'] = [2]
        private_child = root[0 if kind == 'list' else 'child']
        child_incarnation = session._registry.incarnation_for_object(private_child)
        if remove == 'delete':
            del table[key]
        elif kind == 'list':
            table[key].provenance = []
        else:
            table[key] = {}
        before = session.pin.captured_head
        assert session.save() == before + 1
        assert session.store.read_version(session.pin, namespace, physical_key,
                                          expected_record_schema=1).value == original
        checked = session._identity_coordinator.catalog.read_owner_identity(
            session.pin, (namespace, physical_key))
        try:
            assert tuple(checked.occurrences) == original_placements
        finally:
            if hasattr(checked.occurrences, 'close'):
                checked.occurrences.close()
        assert root[0 if kind == 'list' else 'child'] is private_child
        private_child.append(3)
        if kind == 'list':
            if remove == 'delete':
                session.skills[key] = replace(session.skills[2, 'craft'], person=1)
            session.skills[key].provenance = root
        else:
            session.wallets[key] = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        root = session.skills[key].provenance if kind == 'list' else session.wallets[key]
        child = root[0 if kind == 'list' else 'child']
        assert list(child) == [2, 3]
        assert session._registry.incarnation_for_object(child) == child_incarnation


@pytest.mark.parametrize('phase', [None, 'before_transaction', 'after_commit'])
def test_orphan_record_replacement_is_recoverable_and_keeps_its_private_child(tmp_path, phase):
    from ate_sim.persistence_record_headers import NAMESPACE
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.advancement_paths[1] = EssencePath(base_essences=['Fire'])
        root = session.advancement_paths[1]
        incarnation = session._registry.incarnation_for_object(root)
        session.save()
        key = incarnation.value, 0
        original = session.store.read_version(session.pin, NAMESPACE, key,
                                             expected_record_schema=1).value
        root.base_essences = ['Water']
        child = root.base_essences
        del session.advancement_paths[1]
        before = session.pin.captured_head
        if phase is not None:
            def fault(at):
                if at == phase:
                    raise OSError('orphan publication fault')
            session.store._phase_hook = fault
            with pytest.raises(OSError, match='orphan publication fault'):
                session.save()
            session.store._phase_hook = lambda at: None
            assert session.resolve_save() == before + int(phase == 'after_commit')
        assert session.save() == before + 1
        assert session.store.read_version(session.pin, NAMESPACE, key,
                                          expected_record_schema=1).value == original
        assert list(root.base_essences) == ['Water']
        child.append('Life')
        session.advancement_paths[1] = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        root = session.advancement_paths[1]
        assert session._registry.incarnation_for_object(root) == incarnation
        assert list(root.base_essences) == ['Water', 'Life']


@pytest.mark.parametrize('remove', ['replace', 'delete'])
def test_counted_orphan_preserves_saved_leaf_and_reattaches_private_child(tmp_path, remove):
    from ate_sim.core import Household, Settlement
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    from ate_sim.persistence_lazy_sequence import NODE_NAMESPACE, LazyOrderedSequence
    from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy
    def configure(world):
        world.households[1] = Household(1, 1, members=[1])
        world.settlements[1] = Settlement(1, 0, 0, households=[1])
    source = legacy_lazy(tmp_path, configure=configure)
    path = tmp_path / 'complete.sqlite'
    upgrade_lazy_snapshot(source, path, rules_id=RULES)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.skills[1, 'craft'].provenance = [[1]]
        root = session.skills[1, 'craft'].provenance
        session.world.households[1].members = root
        assert type(root) is LazyOrderedSequence
        session.save()
        leaves = {key: session.store.read_version(session.pin, NODE_NAMESPACE, key,
                                                expected_record_schema=1).value
                  for key in session.store.iter_keys(session.pin, NODE_NAMESPACE)
                  if key[0] == root._incarnation}
        root[0] = [2]
        private_child = root[0]
        child_incarnation = session._registry.incarnation_for_object(private_child)
        session.world.households[1].members = []
        if remove == 'replace':
            session.skills[1, 'craft'].provenance = []
        else:
            del session.skills[1, 'craft']
        session.save()
        for key, value in leaves.items():
            assert session.store.read_version(session.pin, NODE_NAMESPACE, key,
                                              expected_record_schema=1).value == value
        assert root[0] is private_child
        private_child.append(3)
        session.world.households[1].members = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        child = session.world.households[1].members[0]
        assert list(child) == [2, 3]
        assert session._registry.incarnation_for_object(child) == child_incarnation


def test_published_orphan_retains_private_descendants_until_reattachment(tmp_path):
    import gc
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.skills[1, 'craft'].provenance = [[1]]
        root = session.skills[1, 'craft'].provenance
        session.save()
        root[0] = {'child': [[2]]}
        child_incarnation = session._registry.incarnation_for_object(root[0]['child'][0])
        session.skills[1, 'craft'].provenance = []
        session.save()
        gc.collect()
        assert list(root[0]['child'][0]) == [2]
        root[0]['child'][0].append(3)
        session.skills[1, 'craft'].provenance = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        child = session.skills[1, 'craft'].provenance[0]['child'][0]
        assert list(child) == [2, 3]
        assert session._registry.incarnation_for_object(child) == child_incarnation


@pytest.mark.parametrize('kind', ['list', 'map'])
def test_held_orphan_can_replace_child_again_after_a_saved_removal(tmp_path, kind):
    path = complete(tmp_path)
    key = (1, 'craft') if kind == 'list' else Ref('person', 1)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        if kind == 'list':
            session.skills[key].provenance = [[1]]
            root, slot = session.skills[key].provenance, 0
        else:
            session.wallets[key] = {'child': [1]}
            root, slot = session.wallets[key], 'child'
        session.save()
        root[slot] = [2]
        if kind == 'list':
            session.skills[key].provenance = []
        else:
            session.wallets[key] = {}
        session.save()
        root[slot] = [3]
        child_incarnation = session._registry.incarnation_for_object(root[slot])
        session.save()
        assert list(root[slot]) == [3]
        if kind == 'list':
            session.skills[key].provenance = root
        else:
            session.wallets[key] = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        root = session.skills[key].provenance if kind == 'list' else session.wallets[key]
        assert list(root[slot]) == [3]
        assert session._registry.incarnation_for_object(root[slot]) == child_incarnation


def test_orphan_can_retain_a_clean_shared_child_after_its_cached_body_is_collected(tmp_path):
    import gc
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.skills[1, 'craft'].provenance = [[1]]
        session.skills[2, 'craft'].provenance = [[2]]
        root = session.skills[1, 'craft'].provenance
        peer = session.skills[2, 'craft'].provenance
        session.save()
        child_incarnation = session._registry.incarnation_for_object(peer[0])
        root[0] = peer[0]
        session.skills[1, 'craft'].provenance = []
        root._clear_cache()
        peer._clear_cache()
        gc.collect()
        session.save()
        assert list(root[0]) == [2]
        assert root[0] is peer[0]
        root[0].append(3)
        session.skills[1, 'craft'].provenance = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        root = session.skills[1, 'craft'].provenance
        peer = session.skills[2, 'craft'].provenance
        assert root[0] is peer[0]
        assert list(root[0]) == [2, 3]
        assert session._registry.incarnation_for_object(root[0]) == child_incarnation


@pytest.mark.parametrize('shared', [False, True])
def test_orphan_replacement_does_not_mask_dirty_original_child(tmp_path, shared):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.skills[1, 'craft'].provenance = [[1]]
        root = session.skills[1, 'craft'].provenance
        old = root[0]
        if shared:
            session.wallets[Ref('person', 1)] = {'shared': old}
        session.save()
        old.append(9)
        root[0] = [2]
        session.skills[1, 'craft'].provenance = []
        session.save()
        assert list(root[0]) == [2]
        assert list(old) == [1, 9]
        session.skills[1, 'craft'].provenance = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert list(session.skills[1, 'craft'].provenance[0]) == [2]
        if shared:
            assert list(session.wallets[Ref('person', 1)]['shared']) == [1, 9]


@pytest.mark.parametrize('kind', ['list', 'map'])
def test_private_child_swap_keeps_checked_saved_routing_separate(tmp_path, kind):
    path = complete(tmp_path)
    key = (1, 'craft') if kind == 'list' else Ref('person', 1)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        if kind == 'list':
            session.skills[key].provenance = [[1], [2]]
            root = session.skills[key].provenance
            first, second = 0, 1
        else:
            session.wallets[key] = {'a': [1], 'b': [2]}
            root = session.wallets[key]
            first, second = 'a', 'b'
        a, b = root[first], root[second]
        session.save()
        a.append(9)
        root[first], root[second] = b, a
        if kind == 'list':
            session.skills[key].provenance = []
        else:
            session.wallets[key] = {}
        session.save()
        assert root[first] is b and root[second] is a
        assert list(root[second]) == [1, 9]
        if kind == 'list':
            session.skills[key].provenance = root
        else:
            session.wallets[key] = root
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        root = session.skills[key].provenance if kind == 'list' else session.wallets[key]
        assert list(root[first]) == [2]
        assert list(root[second]) == [1, 9]


def test_omitted_changed_physical_page_cannot_use_an_unchanged_header_witness(tmp_path, monkeypatch):
    from ate_sim import persistence_lazy_participants as participants
    from ate_sim.incremental_store import StoreIntegrityError
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.skills[1, 'craft'].provenance = [[1], 0]
        root = session.skills[1, 'craft'].provenance
        child = root[0]
        session.save()
        root[1] = 7
        child.append(2)
        freeze = participants.freeze_hybrid_publication
        def omit_page(store, pin, plan, **kwargs):
            changes = tuple(c for c in plan.nested_history_version_changes
                            if not (c.namespace == PAGE_NAMESPACE and c.key[0] == root._incarnation))
            assert len(changes) < len(plan.nested_history_version_changes)
            return freeze(store, pin, replace(plan, nested_history_version_changes=changes), **kwargs)
        monkeypatch.setattr(participants, 'freeze_hybrid_publication', omit_page)
        before = session.pin.captured_head
        with pytest.raises(StoreIntegrityError):
            session.save()
        assert session.store.generation == before
        assert session._identity_coordinator._prepared is None
        assert session._backing_dependencies._prepared is None
        monkeypatch.setattr(participants, 'freeze_hybrid_publication', freeze)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        root = session.skills[1, 'craft'].provenance
        assert list(root[0]) == [1, 2] and root[1] == 7
