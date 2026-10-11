"""Frozen snapshot roles reuse existing backings with mandatory readonly flags."""
import json
import pytest
from ate_sim.event_log import FrozenDict, FrozenList
from ate_sim.incremental_store import CodecError, StoreIntegrityError
from ate_sim.persistence_lazy_nested_history import (
    HistoryReference, LazyHistoryList, LazyHistoryMap, LazyFrozenHistoryList,
    LazyFrozenHistoryMap, DESCRIPTOR_NAMESPACE,
)
from ate_sim.persistence_adapters import WorldCodec, SCHEMA
from ate_sim.persistence_lazy_store import LazyRecordStore


def opened(path):
    return LazyRecordStore.create(path, codec=WorldCodec(identity_links_recorded=True),
        simulation_schema=SCHEMA, rules_id='frozen-histories')


def commit(store, proxy):
    return store.commit(proxy._pin, commit_token='frozen-history', changes=(),
        version_changes=proxy.pending_changes(), next_incarnation_id=2, new_segments=(),
        required_format_version=5, metadata={'simulation_position':1, 'seed':7,
            'next_ids':{}, 'namespaces':()}).pin


@pytest.mark.parametrize('kind,cls,values,native', [
    ('frozen-list', LazyFrozenHistoryList, [1, 2], FrozenList),
    ('frozen-map', LazyFrozenHistoryMap, {'a':1, 'b':2}, FrozenDict),
])
def test_frozen_history_has_checked_reference_descriptor_and_portable_native_type(tmp_path, kind, cls, values, native):
    with opened(tmp_path / 'frozen.sqlite') as store:
        proxy = cls(store, store.capture_pin(), 1, initial_values=values, recursive=True)
        assert proxy.storage_reference() == HistoryReference(kind, 1)
        assert store.codec.decode(store.codec.encode(proxy.storage_reference())) == proxy.storage_reference()
        pin = commit(store, proxy)
        proxy.accept_save(pin)
        assert store.read_version(pin, DESCRIPTOR_NAMESPACE, 1, expected_record_schema=1).value[0] == kind
        restored = cls(store, pin, 1, recursive=True)
        plain = restored.materialize()
        assert type(plain) is native and plain == values
        assert type(store.codec.decode(store.codec.encode(restored))) is native
        with pytest.raises(StoreIntegrityError):
            (LazyHistoryList if kind == 'frozen-list' else LazyHistoryMap)(store, pin, 1, recursive=True)
        store.release_pin(pin)


@pytest.mark.parametrize('kind', ['frozen-list', 'frozen-map'])
def test_frozen_role_cannot_be_restored_from_mutable_descriptor(tmp_path, kind):
    with opened(tmp_path / 'mutable.sqlite') as store:
        base = LazyHistoryList if kind == 'frozen-list' else LazyHistoryMap
        frozen = LazyFrozenHistoryList if kind == 'frozen-list' else LazyFrozenHistoryMap
        proxy = base(store, store.capture_pin(), 1, initial_values=[1] if kind == 'frozen-list' else {'a':1})
        pin = commit(store, proxy)
        with pytest.raises(StoreIntegrityError): frozen(store, pin, 1)
        store.release_pin(pin)


@pytest.mark.parametrize('operation', ['extend', 'slice', 'update', 'set'])
def test_frozen_mutation_rejects_before_consuming_input(tmp_path, operation):
    with opened(tmp_path / 'guard.sqlite') as store:
        is_list = operation in ('extend', 'slice')
        cls = LazyFrozenHistoryList if is_list else LazyFrozenHistoryMap
        proxy = cls(store, store.capture_pin(), 1, initial_values=[1] if is_list else {'a':1})
        consumed = []
        def values():
            consumed.append(True)
            yield 2 if is_list else ('b', 2)
        with pytest.raises(TypeError, match='immutable'):
            if operation == 'extend': proxy.extend(values())
            elif operation == 'slice': proxy[:] = values()
            elif operation == 'update': proxy.update(values())
            else: proxy['b'] = 2
        assert not consumed
        store.release_pin(proxy._pin)


@pytest.mark.parametrize('node', [
    ['typed-history/v1','frozen-list',0],
    ['typed-history/v1','frozen-map',True],
    ['typed-history/v1','foreign-frozen-kind',1],
])
def test_frozen_reference_wire_enum_and_incarnation_are_closed(node):
    with pytest.raises(CodecError): WorldCodec().decode(json.dumps(node).encode())


def test_recursive_frozen_graph_preserves_roles_aliases_and_world_publisher(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES
    from ate_sim.persistence_history_dependencies import active_backing_dependencies
    from ate_sim.persistence_history_types import verify_type_witnesses
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = FrozenList([1, 2])
        source = FrozenDict({'a':shared, 'b':shared})
        session.skills[1, 'craft'].provenance = [source, source]
        root = session.skills[1, 'craft'].provenance
        frozen = root[0]
        assert type(frozen) is LazyFrozenHistoryMap
        assert root[1] is frozen and frozen['a'] is frozen['b']
        assert type(frozen['a']) is LazyFrozenHistoryList
        session.save()
        assert active_backing_dependencies(session.store, session.pin, frozen._incarnation) == (session.pin.token,)
        assert verify_type_witnesses(session.store, session.pin) > 0
        assert session.save() == session.pin.captured_head
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        frozen = root[0]
        assert root[1] is frozen and frozen['a'] is frozen['b']
        with pytest.raises(TypeError): frozen['a'].append(3)
        plain = session.detach(materialize_history=True)
    root = plain.skills.skills[1, 'craft'].provenance
    assert type(root[0]) is FrozenDict and type(root[0]['a']) is FrozenList
    assert root[0] is root[1] and root[0]['a'] is root[0]['b']


@pytest.mark.parametrize('kind,cls', [('frozen-list', LazyFrozenHistoryList), ('frozen-map', LazyFrozenHistoryMap)])
def test_frozen_point_read_at_old_pin_has_fixed_payload_work(tmp_path, kind, cls, record_property):
    metrics = []
    for size in (1000, 10000):
        with opened(tmp_path / f'{kind}-{size}.sqlite') as store:
            values = list(range(size)) if kind == 'frozen-list' else {i:i for i in range(size)}
            proxy = cls(store, store.capture_pin(), 1, initial_values=values, recursive=True)
            writer = commit(store, proxy)
            old = store.capture_pin()
            current = store.commit(writer, commit_token='later', changes=(), version_changes=(),
                new_segments=(), metadata={'simulation_position':2, 'seed':7, 'next_ids':{}, 'namespaces':()}).pin
            store.reset_diagnostics()
            restored = cls(store, old, 1, recursive=True)
            assert restored[size - 1] == size - 1
            now = store.diagnostics()
            metric = now.payload_reads, now.metadata_rows
            metrics.append(metric)
            for label, count in zip(('payload_reads', 'metadata_rows'), metric):
                record_property(f'{kind}_H{size}_{label}', count)
            store.release_pin(current)
            store.release_pin(old)
    assert metrics[0] == metrics[1]


@pytest.mark.parametrize('kind', ['record', 'frozen-list', 'frozen-map'])
def test_legacy_retirement_cannot_claim_new_backing_roles(kind):
    from ate_sim.persistence_history_retirement import _scopes
    with pytest.raises(StoreIntegrityError, match='legacy retirement'):
        _scopes(('history-retirement/v1', kind, 0, 1, False))
