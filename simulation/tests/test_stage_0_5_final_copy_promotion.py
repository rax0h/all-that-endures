"""Persisted list promotion is an explicit copy operation, never a hot scan."""
import pytest
from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE, PAGE_NAMESPACE, LazyHistoryList
from ate_sim.persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as COUNTED, LazyOrderedSequence
from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES, dependency_value
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, opened, sha, module, RULES, NS
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
from ate_sim.incremental_store import StoreIntegrityError, RecordChange
from ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange


def incarnation(source, person=1):
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            return store.read_version(pin, NS, (person, 'craft'), expected_record_schema=1).value.provenance.incarnation
        finally: store.release_pin(pin)


def test_persisted_append_copy_promotes_same_incarnation_and_shared_aliases(tmp_path):
    source = legacy_lazy(tmp_path, size=257)
    inc = incarnation(source)
    before = sha(source)
    target = tmp_path / 'promoted.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    assert sha(source) == before
    with opened(target) as store:
        pin = store.capture_pin()
        try:
            assert not store.contains_lazy_key(pin, DESCRIPTOR_NAMESPACE, inc)
            assert store.contains_lazy_key(pin, COUNTED, inc)
            assert all(key[0] != inc for key in store.iter_keys(pin, PAGE_NAMESPACE))
            assert store.read_version(pin, DEPENDENCIES, inc, expected_record_schema=1).value == dependency_value('sequence')
        finally: store.release_pin(pin)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        alias = s.skills[1, 'craft'].provenance
        assert type(alias) is LazyOrderedSequence and alias._incarnation == inc
        assert s.skills[2, 'craft'].provenance is alias
        assert list(alias) == list(range(257))
        alias.pop(128)
        alias.insert(3, 999)
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        expected = list(range(257)); expected.pop(128); expected.insert(3, 999)
        assert list(s.skills[1, 'craft'].provenance) == expected
        assert s.skills[1, 'craft'].provenance is s.skills[2, 'craft'].provenance


@pytest.mark.parametrize('size', [0, 1, 128, 129])
def test_copy_promotion_handles_empty_and_leaf_boundaries(tmp_path, size):
    source = legacy_lazy(tmp_path, size=size)
    inc = incarnation(source)
    target = tmp_path / 'promoted.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        alias = s.skills[1, 'craft'].provenance
        assert type(alias) is LazyOrderedSequence and list(alias) == list(range(size))
        alias.append(77)
        assert s.skills[2, 'craft'].provenance is alias
        s.save()


@pytest.mark.parametrize('selected', [(True,), (0,), (-1,), (1, 1), ('1',)])
def test_invalid_promotion_selection_does_not_touch_source_or_destination(tmp_path, selected):
    source = legacy_lazy(tmp_path)
    before = sha(source)
    target = tmp_path / 'promoted.sqlite'
    with pytest.raises(ValueError):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=selected)
    assert sha(source) == before and not target.exists()


def test_missing_selected_backing_is_not_an_empty_list(tmp_path):
    source = legacy_lazy(tmp_path)
    target = tmp_path / 'promoted.sqlite'
    with pytest.raises(StoreIntegrityError, match='no append backing'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(99999,))
    assert not target.exists()


def test_separate_equal_lists_keep_different_incarnations_after_copy(tmp_path):
    from ate_sim.skills import SkillHistory
    def configure(world):
        world.skills.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=list(range(32)))
    source = legacy_lazy(tmp_path, configure=configure)
    a, b = incarnation(source), incarnation(source, 3)
    assert a != b
    target = tmp_path / 'promoted.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(a, b))
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        first, second = s.skills[1, 'craft'].provenance, s.skills[3, 'craft'].provenance
        assert first is not second and list(first) == list(second)
        assert (first._incarnation, second._incarnation) == (a, b)
        first.append(77)
        assert len(second) == 32
        s.save()


def test_promoted_persisted_list_can_join_counted_household_without_archive_conversion(tmp_path):
    from ate_sim.core import Household
    def configure(world): world.households[1] = Household(1, 1, members=[1])
    source = legacy_lazy(tmp_path, configure=configure)
    inc = incarnation(source)
    target = tmp_path / 'promoted.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        alias = s.skills[1, 'craft'].provenance
        alias._nread = lambda *_: pytest.fail('counted owner assignment walked source sequence')
        s.world.households[1].members = alias
        assert s.world.households[1].members is s.skills[2, 'craft'].provenance is alias
        s.save()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_promotion_commit_fault_keeps_source_and_retry_exact(tmp_path, monkeypatch, phase):
    from ate_sim.persistence_lazy_store import LazyRecordStore
    source = legacy_lazy(tmp_path)
    inc = incarnation(source)
    before = sha(source)
    target = tmp_path / 'promoted.sqlite'
    original = LazyRecordStore.commit
    def injected(store, *args, **kwargs):
        if store.path.name == 'destination.sqlite':
            def fail(at):
                if at == phase: raise OSError('copy promotion fault')
            store._phase_hook = fail
        return original(store, *args, **kwargs)
    monkeypatch.setattr(LazyRecordStore, 'commit', injected)
    with pytest.raises(OSError, match='promotion fault'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    assert not target.exists() and sha(source) == before
    monkeypatch.setattr(LazyRecordStore, 'commit', original)
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    assert sha(source) == before


def test_recursive_page_placement_becomes_permanent_sequence_leaf_placement(tmp_path):
    from ate_sim.persistence_lazy_nested_history import HistoryReference
    from ate_sim.persistence_history_types import NAMESPACE as TYPES, TAG
    from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    from ate_sim.persistence_lazy_sequence import NODE_NAMESPACE
    from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
    source = legacy_lazy(tmp_path)
    parent = incarnation(source)
    with opened(source) as store:
        pin = store.capture_pin()
        child = store.read_version(pin, NS, (1, 'craft'), expected_record_schema=1).value.teachers.incarnation
        page = store.read_version(pin, PAGE_NAMESPACE, (parent, 0), expected_record_schema=1).value
        token = 'f' * 32
        result = store.commit(pin, commit_token=token,
            version_changes=(VersionChange(PAGE_NAMESPACE, (parent, 0), (HistoryReference('list', child),) + page[1:]),
                             VersionChange(TYPES, parent, (TAG, 'list', (31, 0, 1)))),
            identity_changes=(IdentityOccurrenceChange(PAGE_NAMESPACE, (parent, 0), (('index', 0),), child),),
            changes=(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token)),),
            new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
    target = tmp_path / 'promoted.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(parent, child))
    with opened(target) as store:
        pin = store.capture_pin()
        try:
            group = IdentityCatalog(store).read_identity_group(pin, child)
            try:
                rows = tuple(group.occurrences)
                assert any(ns == NODE_NAMESPACE and key[0] == parent and path[0][0] == 'key' for ns, key, path in rows)
                assert not any(ns == PAGE_NAMESPACE and key[0] == parent for ns, key, _path in rows)
            finally:
                if hasattr(group.occurrences, 'close'): group.occurrences.close()
                if hasattr(group.links, 'close'): group.links.close()
        finally: store.release_pin(pin)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        nested = s.skills[1, 'craft'].provenance[0]
        assert nested is s.skills[1, 'craft'].teachers
        assert type(nested) is LazyOrderedSequence
        nested.append(9)
        s.save()


def test_copy_rejects_extra_promoted_sequence_locator_before_publication(tmp_path, monkeypatch):
    from ate_sim.persistence_lazy_sequence import LOCATOR_NAMESPACE
    source = legacy_lazy(tmp_path)
    inc = incarnation(source)
    before = sha(source)
    target = tmp_path / 'promoted.sqlite'
    original = LazyOrderedSequence.pending_changes
    def corrupt(builder):
        return tuple(original(builder)) + (VersionChange(LOCATOR_NAMESPACE, (inc, 99999), (1, 0)),)
    monkeypatch.setattr(LazyOrderedSequence, 'pending_changes', corrupt)
    with pytest.raises(StoreIntegrityError, match='extra/missing sequence authority'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    assert not target.exists() and sha(source) == before


def test_selected_map_is_not_silently_promoted_as_list(tmp_path):
    from ate_sim.metaphysics import SoulState
    def configure(world): world.metaphysics.souls[1] = SoulState(1, cosmic_links={'a': 1.0})
    source = legacy_lazy(tmp_path, configure=configure)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            inc = next(key for key in store.iter_keys(pin, DESCRIPTOR_NAMESPACE)
                if store.read_version(pin, DESCRIPTOR_NAMESPACE, key, expected_record_schema=1).value[0] == 'map')
        finally: store.release_pin(pin)
    target = tmp_path / 'promoted.sqlite'
    with pytest.raises(StoreIntegrityError, match='not a mutable append list'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    assert not target.exists()


def test_selected_retiring_list_cannot_be_promoted(tmp_path):
    from ate_sim.incremental_store import StoreConflictError
    from ate_sim.persistence_history_retirement import initial_retirement_change
    from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    source = legacy_lazy(tmp_path)
    inc = incarnation(source)
    with opened(source) as store:
        pin = store.capture_pin()
        token = 'e' * 32
        result = store.commit(pin, commit_token=token,
            version_changes=(initial_retirement_change('list', inc, generation=pin.captured_head + 1),),
            changes=(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token)),),
            new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
    before = sha(source)
    target = tmp_path / 'promoted.sqlite'
    with pytest.raises(StoreConflictError, match='retiring append backing'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
    assert not target.exists() and sha(source) == before


def test_selected_source_alias_keeps_its_original_class_pin_and_pending_overlay(tmp_path):
    from ate_sim.persistence_lazy import open_lazy_world_session
    source = legacy_lazy(tmp_path)
    inc = incarnation(source)
    target = tmp_path / 'promoted.sqlite'
    with open_lazy_world_session(source, rules_id=RULES) as original:
        alias = original.skills[1, 'craft'].provenance
        alias.append(77)
        generation = original.pin.captured_head
        before = sha(source)
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, promote_lists=(inc,))
        assert sha(source) == before and original.pin.captured_head == generation
        assert type(alias) is LazyHistoryList
        assert original.skills[1, 'craft'].provenance is original.skills[2, 'craft'].provenance is alias
        assert list(alias) == list(range(32)) + [77]
        with open_bridge(target, rules_id=RULES) as copied:
            activate(copied)
            assert type(copied.skills[1, 'craft'].provenance) is LazyOrderedSequence
            assert list(copied.skills[1, 'craft'].provenance) == list(range(32))
