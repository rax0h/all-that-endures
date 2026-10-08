import random
import pytest

from ate_sim.incremental_store import TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, initial_list_changes


def opened(tmp_path, values, cls=LazyHistoryList):
    store = LazyRecordStore.create(tmp_path / 'nested.sqlite', codec=TypedCodec(), simulation_schema='8', rules_id='nested-component')
    pin = store.capture_pin()
    result = store.commit(pin, commit_token='initial', changes=(), new_segments=(), version_changes=initial_list_changes(1, values, store.codec),
        next_incarnation_id=2, required_format_version=5,
        metadata={'simulation_position': 0, 'seed': 7, 'next_ids': {}, 'namespaces': ()})
    return store, cls(store, result.pin, 1)


@pytest.mark.parametrize('history', [1000, 10000])
def test_typed_list_append_and_tail_pop_are_bounded(tmp_path, history):
    store, values = opened(tmp_path, range(history))
    try:
        assert values.diagnostics()['page_loads'] == 0
        values.append(history)
        assert values[-1] == history
        changes = values.pending_changes()
        assert len(changes) == 2
        assert values.diagnostics()['page_loads'] <= 1
        assert sum(len(store.codec.encode(change.value)) for change in changes) < 8192
        values.pop()
        assert values.pending_changes() == ()
        for key in range(history):
            assert values[key] == key
        assert values.diagnostics()['cached_pages'] <= 4
        assert values.diagnostics()['cached_values'] <= 512
    finally:
        store.release_pin(values._pin)
        store.close()


def test_typed_list_keeps_equal_but_distinct_numeric_representatives(tmp_path):
    store, values = opened(tmp_path, [1, ('a', 2), None])
    try:
        values[0] = True
        assert len(values.pending_changes()) == 1
        assert type(values[0]) is bool
        values[0] = 1
        assert values.pending_changes() == ()
        assert values == [1.0, ('a', 2), None]
    finally:
        store.release_pin(values._pin)
        store.close()


def test_typed_list_extend_self_snapshots_original_values(tmp_path):
    class GuardedList(LazyHistoryList):
        def __iter__(self):
            for i, value in enumerate(super().__iter__()):
                if i >= 2:
                    raise OSError('unbounded self extension')
                yield value
    store, values = opened(tmp_path, [1, 2], GuardedList)
    try:
        values.extend(values)
        assert values[:] == [1, 2, 1, 2]
    finally:
        store.release_pin(values._pin)
        store.close()


def test_typed_list_iterable_failure_keeps_native_partial_mutation(tmp_path):
    store, values = opened(tmp_path, [1])
    def failing():
        yield 2
        raise OSError('input failed')
    try:
        with pytest.raises(OSError, match='input failed'):
            values.extend(failing())
        assert values[:] == [1, 2]
        iterator = iter(values)
        assert next(iterator) == 1
        values.append(3)
        assert list(iterator) == [2, 3]
    finally:
        store.release_pin(values._pin)
        store.close()


def test_typed_list_mixed_operations_match_native_list(tmp_path):
    store, values = opened(tmp_path, range(130))
    native = list(range(130))
    rng = random.Random(843000)
    try:
        for _ in range(250):
            op = rng.randrange(6)
            if op == 0:
                item = rng.randrange(1000)
                values.append(item); native.append(item)
            elif op == 1 and native:
                index = rng.randrange(-len(native), len(native))
                item = rng.randrange(1000)
                values[index] = item; native[index] = item
            elif op == 2 and native:
                index = rng.randrange(-len(native), len(native))
                assert values.pop(index) == native.pop(index)
            elif op == 3:
                index, item = rng.randrange(-200, 200), rng.randrange(1000)
                values.insert(index, item); native.insert(index, item)
            elif op == 4:
                values.reverse(); native.reverse()
            else:
                values.sort(); native.sort()
            assert values[:] == native
        assert values.materialize({}) == native
        assert values + [True] == native + [True]
        assert [False] + values == [False] + native
    finally:
        store.release_pin(values._pin)
        store.close()


def test_typed_list_event_snapshot_is_independent_and_immutable(tmp_path):
    from ate_sim.event_log import freeze, FrozenList
    store, values = opened(tmp_path, [1, ('owner', 2)])
    try:
        snapshot = freeze(values)
        assert type(snapshot) is FrozenList
        values.append(3)
        assert snapshot == [1, ('owner', 2)]
        with pytest.raises(TypeError):
            snapshot.append(4)
    finally:
        store.release_pin(values._pin)
        store.close()


def test_physical_history_reference_cannot_collide_with_native_tuple(tmp_path):
    from ate_sim.persistence_adapters import WorldCodec
    codec = WorldCodec(identity_links_recorded=True)
    store, values = opened(tmp_path, [1])
    try:
        literal = ('typed-history/v1', 'list', 1)
        assert codec.encode(values.storage_reference()) != codec.encode(literal)
        assert codec.decode(codec.encode(literal)) == literal
    finally:
        store.release_pin(values._pin)
        store.close()


def test_sort_callback_observes_native_empty_list_and_rejects_mutation(tmp_path):
    store, values = opened(tmp_path, [3, 1, 2])
    native = [3, 1, 2]
    def key_for(sequence):
        def key(item):
            if item == 3:
                assert sequence[:] == []
                sequence.append(9)
            return item
        return key
    try:
        with pytest.raises(ValueError, match='list modified during sort'):
            native.sort(key=key_for(native))
        with pytest.raises(ValueError, match='list modified during sort'):
            values.sort(key=key_for(values))
        assert values[:] == native
        assert values.pending_changes()
    finally:
        store.release_pin(values._pin)
        store.close()


def test_typed_list_order_comparisons_match_native_list(tmp_path):
    store, values = opened(tmp_path, [1, 2])
    try:
        assert values < [1, 3]
        assert [1, 1] < values
        assert values <= [1, 2]
        assert values > [0]
        assert values >= [1, 2]
        with pytest.raises(TypeError):
            values < (1, 3)
    finally:
        store.release_pin(values._pin)
        store.close()
