import pytest

from ate_sim.incremental_store import TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore


def opened(tmp_path, kind, values):
    from ate_sim.persistence_lazy_nested_history import LazyHistoryMap, LazyHistorySet, initial_scalar_changes
    store = LazyRecordStore.create(tmp_path / 'scalar.sqlite', codec=TypedCodec(), simulation_schema='8', rules_id='nested-scalar')
    pin = store.capture_pin()
    result = store.commit(pin, commit_token='initial', changes=(), new_segments=(), version_changes=initial_scalar_changes(1, kind, values, store.codec),
        next_incarnation_id=2, required_format_version=5,
        metadata={'simulation_position': 0, 'seed': 7, 'next_ids': {}, 'namespaces': ()})
    cls = LazyHistoryMap if kind == 'map' else LazyHistorySet
    return store, cls(store, result.pin, 1)


@pytest.mark.parametrize('history', [1000, 10000])
def test_nested_map_eight_point_edits_are_bounded(tmp_path, history):
    store, values = opened(tmp_path, 'map', {key: .1 for key in range(history)})
    try:
        assert values.diagnostics()['entry_loads'] == 0
        for key in range(8):
            values[key] = values.get(key, 0.) + .01
        changes = values.pending_changes()
        assert len(changes) == 8
        assert values.diagnostics()['entry_loads'] == 8
        assert sum(len(store.codec.encode(change.value)) for change in changes) < 4096
        for key in range(history):
            assert values[key] >= .1
        assert values.diagnostics()['cached_entries'] <= 256
    finally:
        store.release_pin(values._pin)
        store.close()


def test_nested_map_retains_equal_key_representative_and_native_order(tmp_path):
    store, values = opened(tmp_path, 'map', {True: 1, ('key', 2): 3})
    try:
        values[1.] = False
        assert type(next(iter(values))) is bool
        assert type(values[1]) is bool
        values[1] = 1
        assert values.pending_changes() == ()
        del values[True]
        values[1.] = 4
        assert list(values) == [('key', 2), 1.]
        assert type(list(values)[-1]) is float
        assert values.setdefault(1, 9) == 4
        assert values.pop(('key', 2)) == 3
        assert values.pop('missing', 12) == 12
        assert values == {1: 4}
    finally:
        store.release_pin(values._pin)
        store.close()


def test_nested_map_failed_update_keeps_native_partial_change_and_iterator_guard(tmp_path):
    store, values = opened(tmp_path, 'map', {1: 2})
    def failing():
        yield 3, 4
        raise OSError('input failed')
    try:
        with pytest.raises(OSError, match='input failed'):
            values.update(failing())
        assert values == {1: 2, 3: 4}
        iterator = iter(values)
        next(iterator)
        values[5] = 6
        with pytest.raises(RuntimeError):
            next(iterator)
    finally:
        store.release_pin(values._pin)
        store.close()


@pytest.mark.parametrize('history', [1000, 10000])
def test_nested_set_candidate_intersection_reads_only_candidates(tmp_path, history):
    store, values = opened(tmp_path, 'set', set(range(history)))
    try:
        assert values.diagnostics()['entry_loads'] == 0
        assert values & set(range(8)) == set(range(8))
        assert values.diagnostics()['entry_loads'] == 8
        values.add(1.)
        values.discard(history + 1)
        assert values.pending_changes() == ()
        values.add(history + 2)
        assert values.remove(history + 2) is None
        assert values.pending_changes() == ()
    finally:
        store.release_pin(values._pin)
        store.close()


@pytest.mark.parametrize('kind,operation', [
    ('map', lambda value: value.update({})),
    ('map', lambda value: value.pop('missing', 12)),
    ('map', lambda value: value.setdefault(1, 12)),
    ('set', lambda value: value.clear()),
    ('set', lambda value: value.__ior__(set())),
])
def test_native_mutating_protocol_calls_guard_even_without_changes(tmp_path, kind, operation):
    store, values = opened(tmp_path, kind, {1: 2} if kind == 'map' else set())
    def guarded():
        raise OSError('blocked mutation')
    values.bind(guarded, lambda: None)
    try:
        with pytest.raises(OSError, match='blocked mutation'):
            operation(values)
    finally:
        store.release_pin(values._pin)
        store.close()


def test_set_intersection_keeps_native_representatives(tmp_path):
    store, values = opened(tmp_path, 'set', {True})
    try:
        result = values & {1., 2.}
        assert type(next(iter(result))) is bool
        assert type(next(iter(values & {1.}))) is float
    finally:
        store.release_pin(values._pin)
        store.close()


@pytest.mark.parametrize('kind,initial', [('map', {1: 2}), ('set', {1})])
def test_iterator_delete_reinsert_at_same_size_matches_native(tmp_path, kind, initial):
    store, values = opened(tmp_path, kind, initial)
    native = dict(initial) if kind == 'map' else set(initial)
    try:
        ours, control = iter(values), iter(native)
        if kind == 'map':
            del values[1]; del native[1]
            values[1.] = 3; native[1.] = 3
        else:
            values.remove(1); native.remove(1)
            values.add(1.); native.add(1.)
        assert list(ours) == list(control)
    finally:
        store.release_pin(values._pin)
        store.close()


def test_reverse_map_iterator_checks_size_changes(tmp_path):
    store, values = opened(tmp_path, 'map', {1: 2})
    try:
        iterator = reversed(values)
        values[3] = 4
        with pytest.raises(RuntimeError):
            next(iterator)
    finally:
        store.release_pin(values._pin)
        store.close()


@pytest.mark.parametrize('kind,initial', [('map', {True: .1}), ('set', {True})])
def test_scalar_history_codec_identity_leaf_and_event_snapshot(tmp_path, kind, initial):
    from ate_sim.event_log import freeze, FrozenDict
    from ate_sim.persistence_adapters import WorldCodec
    from ate_sim.persistence_identity import IdentityOccurrenceIndex
    from ate_sim.persistence_schema import RECORD_FIELDS
    store, values = opened(tmp_path, kind, initial)
    try:
        codec = WorldCodec(identity_links_recorded=True)
        index = IdentityOccurrenceIndex(codec, RECORD_FIELDS)
        index.bootstrap([(('world.currency.wallets', 1), values, (("field", "currency"), ("field", "wallets"), ("key", 1)))])
        assert values.diagnostics()['entry_loads'] == 0
        decoded = codec.decode(codec.encode(values))
        assert type(decoded) is (dict if kind == 'map' else set)
        assert decoded == initial
        assert type(next(iter(decoded))) is bool
        snapshot = freeze(values)
        assert type(snapshot) is (FrozenDict if kind == 'map' else frozenset)
        if kind == 'map':
            values[9] = .5
        else:
            values.add(9)
        assert 9 not in snapshot
        physical = values.storage_reference()
        assert codec.decode(codec.encode(physical)) == physical
    finally:
        store.release_pin(values._pin)
        store.close()
