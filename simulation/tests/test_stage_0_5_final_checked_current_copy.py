"""Already-backed catalog copies preserve current identity authority verbatim."""
import pytest
from ate_sim.agency import ActionRecord
from ate_sim.core import Event, Layer
from ate_sim.persistence_lazy_nested_history import LazyFrozenHistoryMap
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, opened, sha, module, RULES
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate


def backed_source(tmp_path):
    legacy = legacy_lazy(tmp_path)
    source = tmp_path / 'catalog.sqlite'
    module()._copy_with_checked_catalog(legacy, source, rules_id=RULES)
    with open_bridge(source, rules_id=RULES) as session:
        activate(session)
        action = ActionRecord(1, 2, 'work', 'wealth', .5)
        event = Event(1, 0, 'memory', Layer.SOCIETY, data={'action': action, 'values': [1]})
        snapshot = Event(17, 0, 'snapshot', Layer.SOCIETY, data={'values': [8]})
        snapshot.seal()
        session.skills[1, 'craft'].provenance = [event, action, event.data, snapshot, snapshot.data]
        session.skills[2, 'craft'].provenance = session.skills[1, 'craft'].provenance
        session.world.events.append(event)
        session.world.event_ids.add(1); session.world.next_event = 2
        session.save()
    return source


def test_checked_current_copy_preserves_native_graph_and_incarnations(tmp_path):
    source = backed_source(tmp_path)
    before = sha(source)
    with opened(source) as store:
        identity, generation = store.store_identity, store.generation
        source_rows = tuple(store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id '
            'FROM lazy_identity_occurrence_versions WHERE valid_to IS NULL ORDER BY 1,2,3'))
    target = tmp_path / 'copied.sqlite'
    result = module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert sha(source) == before
    assert result['source_generation'] == generation and result['generation'] == generation + 1
    assert result['complete_format'] is False
    with opened(target) as store:
        assert store.store_identity != identity
        assert tuple(store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id '
            'FROM lazy_identity_occurrence_versions WHERE valid_to IS NULL ORDER BY 1,2,3')) == source_rows
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root is session.skills[2, 'craft'].provenance
        assert root[0] is session.world.events[0]
        assert root[0].data is root[2] and root[0].data['action'] is root[1]
        assert root[3].data is root[4] and type(root[4]) is LazyFrozenHistoryMap
        assert root[1].strength == .5 and list(root[4]['values']) == [8]
        root[1].strength = .75
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[1].strength == .75


@pytest.mark.parametrize('defect', ['owner-node', 'retired-node', 'unindexed-link'])
def test_checked_copy_rejects_unreachable_catalog_metadata(tmp_path, defect):
    from ate_sim.persistence_lazy_identity_catalog import (
        OWNER_TREE_NAMESPACE, GROUP_NAMESPACE, LINK_NAMESPACE,
    )
    from ate_sim.persistence_lazy_identity_retired import NODE_NAMESPACE as RETIRED_NODES
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.incremental_store import StoreIntegrityError
    from simulation.tests.test_stage_0_5_final_copy_graph_integrity import change_source
    source = backed_source(tmp_path)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            inc = next(iter(store.iter_keys(pin, GROUP_NAMESPACE)))
        finally: store.release_pin(pin)
    if defect == 'owner-node':
        changed = VersionChange(OWNER_TREE_NAMESPACE,
            ('world.skills.skills', (1, 'craft'), b'X' * 32),
            ('owner-leaf/v1', (('field', 'provenance'),), inc))
        message = 'extra/missing identity owner tree'
    elif defect == 'retired-node':
        changed = VersionChange(RETIRED_NODES, inc, ('retired-range/v1', inc, inc, None, None))
        message = 'extra/missing retired interval nodes'
    else:
        changed = VersionChange(LINK_NAMESPACE, (('field', 'unindexed-copy-link'),),
            ('identity-link/v1', inc, (('field', 'anchor'),)))
        message = 'identity link inventory'
    change_source(source, (changed,))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match=message):
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_checked_copy_clears_only_destination_dependency_tokens_and_keeps_source_overlay(tmp_path):
    from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES, _checked_value
    source = backed_source(tmp_path)
    target = tmp_path / 'copy.sqlite'
    with open_bridge(source, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        action = root[1]
        action.strength = .9
        pin = session.pin
        before = sha(source)
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
        assert sha(source) == before and session.pin is pin
        assert session.skills[1, 'craft'].provenance is root and root[1] is action
        assert action.strength == .9 and session.world.events[0].data['action'] is action
        with opened(target) as store:
            captured = store.capture_pin()
            try:
                assert all(_checked_value(store, captured, inc)[2] == ()
                    for inc in store.iter_keys(captured, DEPENDENCIES))
            finally: store.release_pin(captured)
        with open_bridge(target, rules_id=RULES) as copied:
            activate(copied)
            assert copied.skills[1, 'craft'].provenance[1].strength == .5


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_checked_copy_commit_fault_preserves_source_and_exact_retry(tmp_path, monkeypatch, phase):
    from ate_sim.persistence_lazy_store import LazyRecordStore
    source = backed_source(tmp_path)
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    original = LazyRecordStore.commit
    def injected(store, *args, **kwargs):
        if store.path.name == 'destination.sqlite':
            def fail(at):
                if at == phase: raise OSError('checked current copy fault')
            store._phase_hook = fail
        return original(store, *args, **kwargs)
    monkeypatch.setattr(LazyRecordStore, 'commit', injected)
    with pytest.raises(OSError, match='checked current copy fault'):
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before
    assert not tuple(tmp_path.glob('.ate-checked-current-copy-*'))
    monkeypatch.setattr(LazyRecordStore, 'commit', original)
    module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert sha(source) == before


def test_checked_copy_rejects_legacy_source_without_bootstrapping_it(tmp_path):
    from ate_sim.incremental_store import StoreFormatError
    source = legacy_lazy(tmp_path)
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreFormatError, match='existing checked catalog'):
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_checked_copy_missing_dependency_roster_is_corruption(tmp_path):
    from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.incremental_store import StoreIntegrityError
    from simulation.tests.test_stage_0_5_final_copy_graph_integrity import change_source
    source = backed_source(tmp_path)
    with opened(source) as store:
        pin = store.capture_pin()
        try: inc = next(iter(store.iter_keys(pin, DEPENDENCIES)))
        finally: store.release_pin(pin)
    change_source(source, (VersionChange(DEPENDENCIES, inc, delete=True),))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match='roster inventory'):
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_checked_copy_source_advance_after_capture_cannot_mix_native_graphs(tmp_path, monkeypatch):
    source = backed_source(tmp_path)
    with opened(source) as store: captured = store.generation
    def advance(phase, _path):
        if phase == 'after_private_copy':
            with open_bridge(source, rules_id=RULES) as session:
                activate(session)
                session.skills[1, 'craft'].provenance[1].strength = .9
                session.save()
    monkeypatch.setattr(module(), '_copy_phase', advance)
    target = tmp_path / 'copy.sqlite'
    result = module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert result['source_generation'] == captured
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[1].strength == .5
    with open_bridge(source, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[1].strength == .9


def test_checked_copy_competing_destination_is_not_overwritten(tmp_path, monkeypatch):
    source = backed_source(tmp_path)
    target = tmp_path / 'copy.sqlite'
    def race(phase, _path):
        if phase == 'before_publish': target.write_bytes(b'competing destination')
    monkeypatch.setattr(module(), '_copy_phase', race)
    with pytest.raises(FileExistsError):
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert target.read_bytes() == b'competing destination'


def test_checked_copy_preserves_compact_retired_ranges_without_recreating_group_rows(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, GROUP_NAMESPACE, CATALOG_NAMESPACE
    from ate_sim.persistence_lazy_identity_retired import RetiredIdentityRanges
    from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    from ate_sim.incremental_store import RecordChange
    source = backed_source(tmp_path)
    with opened(source) as store:
        pin = store.capture_pin()
        catalog = IdentityCatalog(store)
        old_next = store.read_identity_state(pin)
        delta = catalog.prepare_delta(pin, (), (), next_incarnation_id=old_next + 32)
        for step in range(3):
            token = str(step + 1) * 32
            versions, ordinary, placements = delta.decode(store.codec)
            pin = store.commit(pin, commit_token=token, version_changes=versions,
                identity_changes=placements, next_incarnation_id=old_next + 32,
                changes=ordinary + (RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
                    (1, pin.captured_head + 1, token)),),
                new_segments=(), metadata=store.head_metadata()).pin
            delta = catalog.prepare_delta(pin, (), (), next_incarnation_id=old_next + 32,
                retirement_row_budget=256 if step else 0)
        # The final prepared compaction becomes authority in one existing commit.
        token = '4' * 32
        versions, ordinary, placements = delta.decode(store.codec)
        pin = store.commit(pin, commit_token=token, version_changes=versions,
            identity_changes=placements, next_incarnation_id=old_next + 32,
            changes=ordinary + (RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
                (1, pin.captured_head + 1, token)),),
            new_segments=(), metadata=store.head_metadata()).pin
        ranges = RetiredIdentityRanges(store, pin).intervals()
        descriptor = store.read_version(pin, CATALOG_NAMESPACE, 0, expected_record_schema=1).value
        groups = tuple(store.iter_keys(pin, GROUP_NAMESPACE))
        assert ranges and all(any(lo <= inc <= hi for lo, hi in ranges) for inc in range(old_next, old_next + 32))
        assert not any(inc in groups for inc in range(old_next, old_next + 32))
        store.release_pin(pin)
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert sha(source) == before
    with opened(target) as store:
        pin = store.capture_pin()
        try:
            assert tuple(store.iter_keys(pin, GROUP_NAMESPACE)) == groups
            assert RetiredIdentityRanges(store, pin).intervals() == ranges
            assert store.read_version(pin, CATALOG_NAMESPACE, 0, expected_record_schema=1).value == descriptor
        finally: store.release_pin(pin)


def test_checked_copy_requires_empty_physical_owner_witness_too(tmp_path):
    from ate_sim.persistence_lazy_identity_catalog import OWNER_NAMESPACE
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.incremental_store import StoreIntegrityError
    from simulation.tests.test_stage_0_5_final_copy_graph_integrity import change_source
    source = backed_source(tmp_path)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            owner = next(owner for owner in store.iter_keys(pin, OWNER_NAMESPACE)
                if owner[0] == PAGE_NAMESPACE and
                   store.read_version(pin, OWNER_NAMESPACE, owner, expected_record_schema=1).value[7] == 0)
        finally: store.release_pin(pin)
    change_source(source, (VersionChange(OWNER_NAMESPACE, owner, delete=True),))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match='identity owner witness inventory'):
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


@pytest.mark.parametrize('phase,expected', [('before_commit', .5), ('after_commit', .9)])
def test_checked_copy_captures_committed_head_while_source_acknowledgement_is_unresolved(tmp_path, phase, expected):
    source = backed_source(tmp_path)
    target = tmp_path / 'copy.sqlite'
    with open_bridge(source, rules_id=RULES) as original:
        activate(original)
        action = original.skills[1, 'craft'].provenance[1]
        action.strength = .9
        def fail(at):
            if at == phase: raise OSError('source acknowledgement fault')
        original.store._phase_hook = fail
        with pytest.raises(OSError, match='source acknowledgement fault'): original.save()
        pin, pending, before = original.pin, original._pending_save, sha(source)
        module()._copy_current_checked_catalog(source, target, rules_id=RULES)
        assert original.pin is pin and original._pending_save is pending and sha(source) == before
        with open_bridge(target, rules_id=RULES) as copied:
            activate(copied)
            assert copied.skills[1, 'craft'].provenance[1].strength == expected
        original.store._phase_hook = lambda _: None
        original.resolve_save()
        if phase == 'before_commit': original.save()
        assert original.skills[1, 'craft'].provenance[1] is action and action.strength == .9
