"""Explicit copy rejects checksum-valid defects in the existing backing graph."""
import pytest
from ate_sim.incremental_store import RecordChange, StoreIntegrityError
from ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE, PAGE_NAMESPACE, HistoryReference
from ate_sim.persistence_history_types import NAMESPACE as TYPES, TAG
from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, opened, sha, module, RULES, NS
from simulation.tests.test_stage_0_5_final_copy_promotion import incarnation


def change_source(source, versions, placements=(), *, next_incarnation_id=None):
    with opened(source) as store:
        pin = store.capture_pin()
        token = 'd' * 32
        result = store.commit(pin, commit_token=token, version_changes=versions,
            identity_changes=placements, next_incarnation_id=next_incarnation_id,
            changes=(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
                (1, pin.captured_head + 1, token)),),
            new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)


@pytest.mark.parametrize('cycle', ['self', 'two'])
def test_copy_rejects_cyclic_compact_backings_before_publication(tmp_path, cycle):
    source = legacy_lazy(tmp_path)
    parent = incarnation(source)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            child = store.read_version(pin, NS, (1, 'craft'), expected_record_schema=1).value.teachers.incarnation
            page = store.read_version(pin, PAGE_NAMESPACE, (parent, 0), expected_record_schema=1).value
        finally: store.release_pin(pin)
    target_inc = parent if cycle == 'self' else child
    versions = [VersionChange(PAGE_NAMESPACE, (parent, 0), (HistoryReference('list', target_inc),) + page[1:]),
        VersionChange(TYPES, parent, (TAG, 'list', (31, 0, 1)))]
    placements = [IdentityOccurrenceChange(PAGE_NAMESPACE, (parent, 0), (('index', 0),), target_inc)]
    if cycle == 'two':
        versions += [VersionChange(DESCRIPTOR_NAMESPACE, child, ('list', 1, 1)),
            VersionChange(PAGE_NAMESPACE, (child, 0), (HistoryReference('list', parent),)),
            VersionChange(TYPES, child, (TAG, 'list', (0, 0, 1)))]
        placements.append(IdentityOccurrenceChange(PAGE_NAMESPACE, (child, 0), (('index', 0),), parent))
    change_source(source, tuple(versions), tuple(placements))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match='cyclic copy backing'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_copy_keeps_shared_acyclic_backing_diamond(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    source = legacy_lazy(tmp_path)
    parent = incarnation(source)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            a, b = (store.read_version(pin, NS, (person, 'craft'), expected_record_schema=1).value.teachers.incarnation
                for person in (1, 2))
            shared = store.read_identity_state(pin)
            page = store.read_version(pin, PAGE_NAMESPACE, (parent, 0), expected_record_schema=1).value
        finally: store.release_pin(pin)
    versions = [VersionChange(PAGE_NAMESPACE, (parent, 0),
        (HistoryReference('list', a), HistoryReference('list', b)) + page[2:]),
        VersionChange(TYPES, parent, (TAG, 'list', (30, 0, 2)))]
    placements = [IdentityOccurrenceChange(PAGE_NAMESPACE, (parent, 0), (('index', slot),), child)
        for slot, child in enumerate((a, b))]
    for child in (a, b, shared):
        values = (7,) if child == shared else (HistoryReference('list', shared),)
        versions += [VersionChange(DESCRIPTOR_NAMESPACE, child, ('list', 1, 1)),
            VersionChange(PAGE_NAMESPACE, (child, 0), values),
            VersionChange(TYPES, child, (TAG, 'list', (1, 0, 0) if child == shared else (0, 0, 1)))]
        if child != shared:
            placements.append(IdentityOccurrenceChange(PAGE_NAMESPACE, (child, 0), (('index', 0),), shared))
    change_source(source, tuple(versions), tuple(placements), next_incarnation_id=shared + 1)
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert sha(source) == before
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0] is session.skills[1, 'craft'].teachers
        assert root[1] is session.skills[2, 'craft'].teachers
        assert root[0][0] is root[1][0]
        assert list(root[0][0]) == [7]


def test_copy_rejects_empty_physical_page_without_its_backing_descriptor(tmp_path):
    source = legacy_lazy(tmp_path)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            backings = set(store.iter_keys(pin, DESCRIPTOR_NAMESPACE))
            inc = next(inc for inc in range(1, store.read_identity_state(pin)) if inc not in backings)
        finally: store.release_pin(pin)
    change_source(source, (VersionChange(PAGE_NAMESPACE, (inc, 0), ()),))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match='physical owner has missing or wrong-kind backing'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_copy_scrubs_preexisting_counted_backing_not_only_new_promotions(tmp_path):
    from ate_sim.core import Household
    from ate_sim.persistence_lazy_sequence import LOCATOR_NAMESPACE
    def configure(world): world.households[1] = Household(1, 1, members=[1, 2])
    source = legacy_lazy(tmp_path, configure=configure)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            inc = store.read_version(pin, 'world.households', 1, expected_record_schema=1).value.members.incarnation
        finally: store.release_pin(pin)
    change_source(source, (VersionChange(LOCATOR_NAMESPACE, (inc, 99999), (1, 0)),))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match='extra/missing sequence authority'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


@pytest.mark.parametrize('namespace', ['aux.lazy.sequence.parents', 'aux.lazy.sequence.occurrences',
    'aux.lazy.sequence.members', 'aux.lazy.sequence.member_directory'])
def test_copy_rejects_orphan_sequence_projection_without_descriptor(tmp_path, namespace):
    source = legacy_lazy(tmp_path)
    inc = incarnation(source)  # Existing append descriptor cannot own sequence indexes.
    part = b'' if namespace.endswith('member_directory') else 99999
    change_source(source, (VersionChange(namespace, (inc, part), ()),))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match='physical owner has missing or wrong-kind backing'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before
