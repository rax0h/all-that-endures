import pytest

from ate_sim.core import World, Layer, _canonical
from ate_sim.incremental_store import StoreError, StoreIntegrityError, _record_checksum
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_event_ids import EventIdSet, RANGE_TAG
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'event-id-compact-integration'
NS = 'world.event_ids'


def converted(tmp_path, values, *, events=0):
    world = World(843000)
    for _ in range(events):
        world.emit('probe', Layer.REALITY)
    world.event_ids = set(values)
    source, destination = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    before = source.read_bytes()
    result = convert_cold_to_lazy(source, destination, rules_id=RULES)
    if type(values) is range:
        assert result['destination_format'] == 5
    assert source.read_bytes() == before
    return destination


@pytest.mark.parametrize('history', [0, 1000, 10000])
def test_range_open_and_save_keep_one_checked_authority(tmp_path, history):
    path = converted(tmp_path, range(1, history + 1))
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        assert type(ids) is EventIdSet
        assert ids.range_end == history
        tracker = session._eager_tracker
        assert tracker._baseline_ordinals.get(NS, {}) == {}
        assert tracker._cold_persisted_keys[NS] == {0}
        assert ids.diagnostics()['member_visits'] == 0
        ids.add(history + 1)
        assert session.save() == session.pin.captured_head
        assert ids.diagnostics()['member_visits'] == 0
        assert not tracker._dirty and not tracker._deleted
        rows = session.store.read_records(NS, expected_record_schema=1)
        assert rows == ((0, (0, (RANGE_TAG, history + 1)), 1),)
        assert session.manifest['collections'][NS] == (RANGE_TAG, history + 1, 0)
        assert session.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0] == '5'
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.event_ids.range_end == history + 1


def test_emit_fallback_retains_facade_and_reopens_exact_values(tmp_path):
    path = converted(tmp_path, range(1, 5), events=4)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        assert type(ids) is EventIdSet
        ids.remove(2)
        session.world.event_ids |= {99}
        assert session.world.event_ids is ids
        event = session.world.emit('probe', Layer.REALITY, causes=(1, 4))
        assert event.id == 5
        with pytest.raises(ValueError, match='cause'):
            session.world.emit('probe', Layer.REALITY, causes=(2,))
        session.save()
        assert set(ids) == {1, 3, 4, 5, 99}
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert type(session.world.event_ids) is EventIdSet
        assert set(session.world.event_ids) == {1, 3, 4, 5, 99}
        session.world.event_ids.add(100)
        assert len(session._eager_tracker._dirty) == 1
        session.save()


@pytest.mark.parametrize('values', [{True, 2}, {1.0, 2}, {1, 3}, {0, 1}, {-1, 1}])
def test_conversion_proves_actual_representatives(tmp_path, values):
    path = converted(tmp_path, values)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        assert type(ids) is EventIdSet
        assert ids.range_end is None
        assert {(type(v), repr(v)) for v in ids} == {(type(v), repr(v)) for v in values}


def test_codec_canonical_and_detach_are_portable_native_set(tmp_path):
    path = converted(tmp_path, range(1, 13))
    session = open_lazy_world_session(path, rules_id=RULES)
    ids = session.world.event_ids
    assert type(ids) is EventIdSet
    assert _canonical(ids) == _canonical(set(range(1, 13)))
    assert WorldCodec().decode(WorldCodec().encode(ids)) == set(range(1, 13))
    world = session.detach(materialize_history=True)
    assert type(world.event_ids) is set
    assert world.event_ids == set(range(1, 13))
    with pytest.raises(StoreError):
        ids.add(13)


def replace_authority(store, envelope):
    key = store.codec.encode(0)
    payload = store.codec.encode(envelope)
    generation = store.generation
    checksum = _record_checksum(NS, key, 1, store.codec.version, generation, payload)
    store.db.execute('UPDATE records SET payload=?,payload_checksum=?,last_changed_generation=? WHERE namespace=? AND typed_key=?', (payload, checksum, generation, NS, key))


def test_normal_acknowledgement_checks_compact_successor_payload(tmp_path):
    path = converted(tmp_path, range(1, 5), events=4)
    session = open_lazy_world_session(path, rules_id=RULES)
    session.world.emit('probe', Layer.REALITY)
    def corrupt(phase):
        if phase == 'after_commit':
            replace_authority(session.store, (0, (RANGE_TAG, 6)))
            session.store.db.commit()
    session.store._phase_hook = corrupt
    try:
        with pytest.raises(StoreIntegrityError, match='event_ids|successor'):
            session.save()
        assert (NS, 0) in session._eager_tracker._dirty
    finally:
        session.store._phase_hook = lambda phase: None
        replace_authority(session.store, (0, (RANGE_TAG, 5)))
        session.store.db.commit()
        if session._pending_save is not None:
            session.resolve_save()
        session.close()


@pytest.mark.parametrize('phase', ['during_ordinary_writes', 'before_head', 'before_commit', 'after_commit'])
@pytest.mark.parametrize('fallback', [False, True])
def test_descriptor_and_event_log_resolve_atomically(tmp_path, phase, fallback):
    path = converted(tmp_path, range(1, 5), events=4)
    session = open_lazy_world_session(path, rules_id=RULES)
    ids = session.world.event_ids
    before = session.pin.captured_head
    if fallback:
        ids.remove(2)
    session.world.emit('probe', Layer.REALITY, causes=(1,))
    def fail(current):
        if current == phase:
            raise OSError(phase)
    session.store._phase_hook = fail
    with pytest.raises(OSError, match=phase):
        session.save()
    session.store._phase_hook = lambda phase: None
    resolved = session.resolve_save()
    if phase == 'after_commit':
        assert resolved == before + 1
    else:
        assert resolved == before
        assert session._eager_tracker._dirty
        session.save()
    assert session.world.event_ids is ids
    session.close()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert len(session.world.events) == 5
        assert set(session.world.event_ids) == ({1, 3, 4, 5} if fallback else {1, 2, 3, 4, 5})


def test_sealing_event_data_freezes_event_id_facade(tmp_path):
    from ate_sim.event_log import freeze
    ids = EventIdSet.from_range_descriptor(4)
    frozen = freeze({'ids': ids})
    assert type(frozen['ids']) is frozenset
    ids.add(5)
    assert frozen['ids'] == frozenset(range(1, 5))


@pytest.mark.parametrize('envelope', [
    (0, (RANGE_TAG, True)), (True, (RANGE_TAG, 4)),
    (0, (RANGE_TAG, -1)), (0, ('unknown/v1', 4)),
    (0, (RANGE_TAG, 5)), [0, (RANGE_TAG, 4)],
])
def test_checked_malformed_descriptor_fails_on_open(tmp_path, envelope):
    from ate_sim.persistence_adapters import SCHEMA
    from ate_sim.persistence_lazy_store import LazyRecordStore
    path = converted(tmp_path, range(1, 5))
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA, expected_rules_id=RULES) as store:
        replace_authority(store, envelope)
        store.db.commit()
    with pytest.raises(StoreError, match='event-ID'):
        open_lazy_world_session(path, rules_id=RULES)


@pytest.mark.parametrize('values', [{1, 2, 3, 4}, {1, 3, 4}])
def test_shared_event_ids_remain_one_mutable_object(tmp_path, values):
    world = World(843000)
    world.event_ids = values
    world.currency.wallets[1] = {'ids': world.event_ids}
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        assert session.wallets[1]['ids'] is ids
        ids.add(5)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.wallets[1]['ids'] is session.world.event_ids
        assert 5 in session.wallets[1]['ids']
        world = session.detach(materialize_history=True)
        assert type(world.event_ids) is set
        assert world.currency.wallets[1]['ids'] is world.event_ids


def test_eager_record_event_id_alias_uses_compact_authority(tmp_path):
    from ate_sim.institutions import Institution
    world = World(843000)
    world.event_ids = {1, 2, 3, 4}
    record = Institution(1, 'probe', 'probe', 0, None)
    record.members = world.event_ids
    world.institutions.institutions[1] = record
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.institutions.institutions[1].members is session.world.event_ids
        session.world.event_ids.add(5)
        session.save()
        assert session.world.event_ids.diagnostics()['member_visits'] == 0
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.institutions.institutions[1].members is session.world.event_ids
        assert 5 in session.world.institutions.institutions[1].members


def test_detach_preserves_shared_nested_wallet_reference(tmp_path):
    world = World(843000)
    world.event_ids = {1, 2, 3}
    shared = {'ids': world.event_ids}
    world.currency.wallets[1] = {'shared': shared}
    world.currency.wallets[2] = {'shared': shared}
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        world = session.detach(materialize_history=True)
        assert world.currency.wallets[1]['shared'] is world.currency.wallets[2]['shared']
        assert world.currency.wallets[1]['shared']['ids'] is world.event_ids


@pytest.mark.parametrize('history', [2048, 20480])
def test_sealed_history_emit_save_uses_one_small_descriptor(tmp_path, history):
    import sys
    from ate_sim.event_log import EventLog
    world = World(843000)
    for _ in range(history):
        world.emit('probe', Layer.REALITY)
    world.events = EventLog(world.events)
    world.events.seal_before(1)
    world.year = 1
    for _ in range(3):
        world.emit('probe', Layer.REALITY, causes=(1, history))
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        assert session.world.events._disk_count == history
        assert ids.diagnostics()['resident_members'] == 0
        assert ids.diagnostics()['member_visits'] == 0
        resident = sys.getsizeof(ids) + sys.getsizeof(vars(ids))
        assert resident <= 8192
        before = len(session.store.codec.encode((0, ids.descriptor())))
        actions = []
        def inspect(phase):
            if phase == 'before_transaction':
                actions.extend(change for change in session._pending_save.cold_plan.changes if change.namespace == NS)
        session.store._phase_hook = inspect
        session.world.emit('probe', Layer.REALITY, causes=(1, history))
        session.save()
        assert len(actions) == 1
        assert len(session.store.codec.encode(actions[0].value)) - before <= 32
        assert ids.diagnostics()['member_visits'] == 0
        assert ids.diagnostics()['resident_members'] == 0
        assert session._eager_tracker._cold_persisted_keys[NS] == {0}
        assert not session._eager_tracker._dirty
        visits = ids.diagnostics()['member_visits']
    assert ids.diagnostics()['member_visits'] == visits


def test_fallback_can_recompact_without_duplicate_row_actions(tmp_path):
    path = converted(tmp_path, range(1, 5))
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        ids.remove(2)
        session.save()
        ids.update({2})
        assert ids.range_end == 4
        session.save()
        assert session.store.read_records(NS, expected_record_schema=1) == ((0, (0, (RANGE_TAG, 4)), 1),)
        assert session._eager_tracker._cold_persisted_keys[NS] == {0}


def test_normal_acknowledgement_rejects_extra_checked_authority_row(tmp_path):
    path = converted(tmp_path, range(1, 5))
    session = open_lazy_world_session(path, rules_id=RULES)
    session.world.event_ids.add(5)
    encoded_key = session.store.codec.encode(1)
    def corrupt(phase):
        if phase == 'after_commit':
            payload = session.store.codec.encode((1, (RANGE_TAG, 5)))
            generation = session.store.generation
            checksum = _record_checksum(NS, encoded_key, 1, session.store.codec.version, generation, payload)
            session.store.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)', (NS, encoded_key, payload, checksum, session.store.codec.version, 1, generation))
            session.store.db.commit()
    session.store._phase_hook = corrupt
    try:
        with pytest.raises(StoreIntegrityError, match='authority'):
            session.save()
        assert session._eager_tracker._dirty
    finally:
        session.store.db.execute('DELETE FROM records WHERE namespace=? AND typed_key=?', (NS, encoded_key))
        session.store.db.commit()
        session.store._phase_hook = lambda phase: None
        if session._pending_save is not None:
            session.resolve_save()
        session.close()
