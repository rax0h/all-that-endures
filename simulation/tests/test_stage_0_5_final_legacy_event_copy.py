"""Raw legacy Event graphs are normalized only by explicit checked copy."""
import pytest
from ate_sim.core import Event, Layer
from ate_sim.persistence_lazy_nested_history import LazyHistoryMap, LazyHistoryList, PAGE_NAMESPACE, ENTRY_NAMESPACE
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, opened, sha, module, RULES
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate


def event_source(tmp_path, *, record=None, sealed=False, share_history=False):
    def configure(world):
        values = world.skills.skills[1, 'craft'].provenance if share_history else [1]
        data = {'a': values, 'b': values}
        if record is not None: data['record'] = record
        first, second = Event(1, 0, 'legacy', Layer.SOCIETY, data=data), Event(2, 0, 'legacy', Layer.SOCIETY, data=data)
        if sealed: first.seal(); second.seal()
        world.events.extend((first, second)); world.event_ids.update((1, 2)); world.next_event = 3
    return legacy_lazy(tmp_path, configure=configure)


def test_raw_shared_event_data_copy_keeps_incarnations_and_physical_child_routes(tmp_path):
    source = event_source(tmp_path)
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            labels = dict(store.identity_occurrences_for_owner(pin, 'world.events', 0))
            data_inc = labels[(('field', 'data'),)]
            child_inc = labels[(('field', 'data'), ('key', 'a'))]
        finally: store.release_pin(pin)
    before = sha(source)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source) == before
    with opened(target) as store:
        pin = store.capture_pin()
        try:
            rows = dict(store.identity_occurrences_for_owner(pin, 'world.events', 0))
            assert rows[(('field', 'data'),)] == data_inc
            assert (('field', 'data'), ('key', 'a')) not in rows
            group = store.read_identity_group(pin, child_inc)
            try:
                assert all(ns == ENTRY_NAMESPACE and key[0] == data_inc for ns, key, path in group.occurrences)
                assert len(group.occurrences) == 2
            finally:
                for items in (group.occurrences, group.links):
                    if hasattr(items, 'close'): items.close()
        finally: store.release_pin(pin)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        first, second = session.world.events
        assert type(first.data) is LazyHistoryMap and first.data is second.data
        assert type(first.data['a']) is LazyHistoryList and first.data['a'] is first.data['b']
        assert first.data._incarnation == data_inc and first.data['a']._incarnation == child_inc
        first.data['a'].append(2)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data is session.world.events[1].data
        assert list(session.world.events[0].data['b']) == [1, 2]


@pytest.mark.parametrize('disagreement', ['event-data', 'action-root'])
def test_normalized_copy_rejects_conflicting_legacy_alias_bodies_before_publish(tmp_path, disagreement):
    from ate_sim.agency import ActionRecord
    from ate_sim.incremental_store import RecordChange, StoreIntegrityError
    from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    if disagreement == 'action-root':
        action = ActionRecord(1, 2, 'work', 'wealth', .5)
        def configure(world):
            world.agency.actions.append(action)
            world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'action': action}))
            world.event_ids.add(1); world.next_event = 2
        source = legacy_lazy(tmp_path, configure=configure)
        namespace, key = 'world.agency.actions', 0
    else:
        source = event_source(tmp_path)
        namespace, key = 'world.events', 1
    with opened(source) as store:
        pin = store.capture_pin()
        ordinal, value = store.read_record(namespace, key)
        if disagreement == 'action-root': value.strength = .75
        else: value.data['a'].append(99)
        token = 'e' * 32
        result = store.commit(pin, commit_token=token, changes=(RecordChange(namespace, key, (ordinal, value)),
            RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token))),
            version_changes=(), new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
    before = sha(source)
    target = tmp_path / 'normalized.sqlite'
    with pytest.raises(StoreIntegrityError, match='aliases disagree'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source) == before and not target.exists()


def test_normalized_event_child_retains_existing_skill_history_alias(tmp_path):
    source = event_source(tmp_path, share_history=True)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        history = session.skills[1, 'craft'].provenance
        assert session.world.events[0].data['a'] is session.world.events[1].data['b'] is history
        history.append(77)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['b'] is session.skills[2, 'craft'].provenance
        assert session.skills[1, 'craft'].provenance[-1] == 77


def test_normalized_native_record_shared_by_event_payloads_mutates_and_reopens(tmp_path):
    from ate_sim.agency import ActionRecord
    source = event_source(tmp_path, record=ActionRecord(1, 2, 'work', 'wealth', .5))
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        action = session.world.events[0].data['record']
        assert type(action) is ActionRecord and session.world.events[1].data['record'] is action
        action.strength = .75
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['record'].strength == .75


def test_sealed_native_event_value_graph_allocates_readonly_backings_in_copy(tmp_path):
    from ate_sim.persistence_lazy_nested_history import LazyFrozenHistoryMap, LazyFrozenHistoryList
    from ate_sim.event_log import FrozenDict, FrozenList
    source = event_source(tmp_path, sealed=True)
    before = sha(source)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source) == before
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.world.events[0]
        assert type(event.data) is LazyFrozenHistoryMap and event.data._deep_immutable
        assert type(event.data['a']) is LazyFrozenHistoryList
        assert event.data['a'] is not event.data['b']  # Native seal copies each container.
        with pytest.raises(TypeError): event.data['a'].append(2)
        session.save()
        plain = session.detach(materialize_history=True)
    assert type(plain.events[0].data) is FrozenDict and type(plain.events[0].data['a']) is FrozenList


@pytest.mark.parametrize('read_event_first', [True, False])
def test_record_normalized_from_event_data_reuses_related_eager_action_root(tmp_path, read_event_first):
    from ate_sim.agency import ActionRecord
    action = ActionRecord(1, 2, 'work', 'wealth', .5)
    def configure(world):
        world.agency.actions.append(action)
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'action': action}))
        world.event_ids.add(1); world.next_event = 2
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        if read_event_first:
            assert session.world.events[0].data['action'] is session.world.agency.actions[0]
        session.world.agency.actions[0].strength = .75
        assert session.world.events[0].data['action'] is session.world.agency.actions[0]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['action'] is session.world.agency.actions[0]
        assert session.world.agency.actions[0].strength == .75


@pytest.mark.parametrize('read_event_first', [True, False])
def test_normalized_skill_record_keeps_one_body_when_native_root_edits_first(tmp_path, read_event_first):
    def configure(world):
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'skill': world.skills.skills[1, 'craft']}))
        world.event_ids.add(1); world.next_event = 2
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        skill = session.world.skills.skills[1, 'craft']
        if read_event_first:
            assert session.world.events[0].data['skill'] is skill
        skill.level = 7
        assert session.world.events[0].data['skill'] is skill
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        skill = session.world.skills.skills[1, 'craft']
        assert session.world.events[0].data['skill'] is skill
        assert skill.level == 7


def test_sealed_event_shared_by_mutable_payloads_has_one_readonly_body(tmp_path):
    def configure(world):
        sealed = Event(1, 0, 'snapshot', Layer.SOCIETY, data={'values': [8]})
        sealed.seal()
        first = Event(1, 0, 'first', Layer.SOCIETY, data={'snapshot': sealed})
        second = Event(2, 0, 'second', Layer.SOCIETY, data={'snapshot': sealed})
        world.events.extend((first, second)); world.event_ids.update((1, 2)); world.next_event = 3
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        first, second = session.world.events
        sealed = first.data['snapshot']
        assert second.data['snapshot'] is sealed
        assert second.data['snapshot'].data is sealed.data
        assert list(sealed.data['values']) == [8]
        session.save()


@pytest.mark.parametrize('phase', ['before_catalog_commit', 'after_catalog_commit', 'before_publish'])
def test_normalized_event_copy_fault_discards_private_graph_and_can_retry(tmp_path, monkeypatch, phase):
    source = event_source(tmp_path, sealed=True)
    before = sha(source)
    target = tmp_path / 'normalized.sqlite'
    mod = module()
    def fail(at, _path):
        if at == phase: raise OSError('normalized Event copy fault')
    monkeypatch.setattr(mod, '_copy_phase', fail)
    with pytest.raises(OSError, match='normalized Event copy fault'):
        mod._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source) == before and not target.exists()
    assert not tuple(tmp_path.glob('.ate-catalog-copy-*'))
    monkeypatch.setattr(mod, '_copy_phase', lambda *_: None)
    mod._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert list(session.world.events[0].data['a']) == [1]


def test_normalized_copy_preserves_held_source_pin_and_pending_overlays(tmp_path):
    from ate_sim.persistence_lazy import open_lazy_world_session
    source = event_source(tmp_path, share_history=True)
    target = tmp_path / 'normalized.sqlite'
    with open_lazy_world_session(source, rules_id=RULES) as original:
        event, history, pin = original.world.events[0], original.skills[1, 'craft'].provenance, original.pin
        event.kind = 'pending'
        history.append(77)
        before = sha(source)
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
        assert sha(source) == before and original.pin == pin
        assert original.world.events[0] is event and event.kind == 'pending' and history[-1] == 77
        with open_bridge(target, rules_id=RULES) as copied:
            activate(copied)
            assert copied.world.events[0].kind == 'legacy'
            assert list(copied.world.events[0].data['a']) == list(range(32))
            assert copied.world.events[0].data['a'] is copied.skills[1, 'craft'].provenance
        original.save()
        assert original.world.events[0] is event and history[-1] == 77
