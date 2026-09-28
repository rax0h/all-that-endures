import dataclasses
import json
import sqlite3
import struct
import subprocess
import sys
from time import perf_counter

import pytest

from ate_sim import Simulation, generate_world
from ate_sim import checkpoint
from ate_sim.core import World, Person, Event, Layer, Ref
from ate_sim.event_log import EventLog, FrozenDict, FrozenList
from ate_sim.record_index import RecordTable, indexed
from ate_sim.history_archive import export_archive, HistoryArchive
from ate_sim.resource_offers import ordered_resource_offers
from ate_sim.persistence_adapters import (
    WorldCodec, write_snapshot, read_snapshot, validate_schema, SCHEMA, META,
    IDENTITY_LINKS,
)
from ate_sim.persistence_schema import RECORD_FIELDS, ROOT_FIELDS, ROOT_TYPES
from ate_sim.incremental_store import (
    TransactionalStore, RecordChange, CodecError, StoreError, StoreFormatError, StoreIntegrityError,
)

RULES = 'stage-0.5-p2a-tests'


def open_store(path):
    return TransactionalStore.open(path, codec=WorldCodec(), expected_simulation_schema=SCHEMA,
                                   expected_rules_id=RULES)


def same(a, b):
    """Unlike digest equality, also check concrete containers and iteration order."""
    assert type(a) is type(b)
    if dataclasses.is_dataclass(a):
        for f in dataclasses.fields(a):
            same(getattr(a, f.name), getattr(b, f.name))
        if type(a) is Event:
            assert ('_sealed' in vars(a), vars(a).get('_sealed')) == ('_sealed' in vars(b), vars(b).get('_sealed'))
    elif isinstance(a, dict):
        assert list(a) == list(b)
        for k in a:
            same(a[k], b[k])
    elif isinstance(a, (list, tuple, EventLog)):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            same(x, y)
        if type(a) is EventLog:
            assert len(a._chunks) == len(b._chunks)
            assert len(a._tail) == len(b._tail)
            assert a._years == b._years and a._offsets == b._offsets
    elif type(a) is float:
        assert struct.pack('>d', a) == struct.pack('>d', b)
    else:
        assert a == b


def warm(w):
    for sid, people in w.living_by_settlement().items():
        ordered_resource_offers(w, sid, people)
        w.materials.best_available(sid)
        w.materials.magical_available_count(sid)
        w.materials.selection_ids(sid)
        w.materials.best_at_rank(sid, 1)
        w.materials.crafting_capacity(sid, 3)
        for p in people:
            tuple(w.social.relationships_for(p.id))
            w.communities.memberships_for(p.id)
            w.advancement.rank(p.id)
    w.active_households()


@pytest.mark.parametrize('mature,years', [(False, 0), (False, 12), (True, 30)])
def test_real_world_roundtrip_and_continuation(tmp_path, mature, years):
    w = Simulation(generate_world(843000, mature=mature)).run(years)
    warm(w)
    before = w.digest()
    legacy = checkpoint.loads(checkpoint.dumps(w))
    path = tmp_path/'world.sqlite'
    start = perf_counter()
    counters = write_snapshot(w, path, rules_id=RULES)
    write_seconds = perf_counter() - start
    start = perf_counter()
    restored = read_snapshot(path, rules_id=RULES)
    read_seconds = perf_counter() - start
    assert w.digest() == before == legacy.digest() == restored.digest()
    same(w, restored)
    if mature:
        # Real training evidence aliases its still-mutable objective event.
        from ate_sim.persistence_adapters import _at_path
        with open_store(path) as store:
            links = [
                (target, owner)
                for target, owner, _schema in store.read_records(IDENTITY_LINKS)
            ]
        assert links
        for target, owner in links:
            assert _at_path(w, target) is _at_path(w, owner)
            assert _at_path(restored, target) is _at_path(restored, owner)
            assert _at_path(restored, owner) is not _at_path(w, owner)
    # Rebuilt caches reference the restored records, not clones or the source.
    warm(restored)
    for pid in restored.people:
        for rel in restored.social.relationships_for(pid):
            assert rel is restored.social.edges[restored.social.key(rel.a, rel.b)]
    after = [Simulation(x).run(5).digest() for x in (w, legacy, restored)]
    assert len(set(after)) == 1
    print(json.dumps({'mature': mature, 'years': years, 'before': before, 'continued': after[0],
                      'write_seconds': write_seconds, 'read_seconds': read_seconds,
                      'file_bytes': path.stat().st_size, 'payload_bytes': counters.payload_write_bytes,
                      'records': counters.payload_writes, 'events_after_continue': len(w.events)}))


def test_empty_world_defaults_and_all_declared_fields(tmp_path):
    validate_schema()
    assert set(ROOT_FIELDS) == set(ROOT_TYPES)
    for cls, names in RECORD_FIELDS.items():
        assert names == tuple(f.name for f in dataclasses.fields(cls))
    w = World(4)
    write_snapshot(w, tmp_path/'w', rules_id=RULES)
    restored = read_snapshot(tmp_path/'w', rules_id=RULES)
    same(w, restored)
    assert len(RECORD_FIELDS) >= 60


def test_every_registered_record_field_roundtrips_without_defaults():
    # Synthetic values isolate field/codec coverage, including record classes
    # whose rare creation events need not occur in the short history fixtures.
    codec = WorldCodec()
    for cls, names in RECORD_FIELDS.items():
        value = object.__new__(cls)
        for index, name in enumerate(names):
            object.__setattr__(value, name, (name, index, -0.0, {'typed': [index]}))
        same(value, codec.decode(codec.encode(value)))


def test_unclassified_fields_types_and_hidden_state_fail(tmp_path, monkeypatch):
    w = World(2)
    with monkeypatch.context() as m:
        m.setitem(RECORD_FIELDS, World, RECORD_FIELDS[World][:-1])
        with pytest.raises(CodecError, match='unclassified fields'):
            write_snapshot(w, tmp_path/'bad', rules_id=RULES)
    @dataclasses.dataclass
    class Unknown:
        value: int = 1
    w.people[1] = Unknown()
    with pytest.raises(CodecError, match='unregistered'):
        write_snapshot(w, tmp_path/'bad', rules_id=RULES)
    w.people.clear()
    w.hidden_authority = 1
    with pytest.raises(CodecError, match='non-field'):
        write_snapshot(w, tmp_path/'bad', rules_id=RULES)
    assert not (tmp_path/'bad').exists()


def test_shared_mutable_children_preserved_and_cycles_rejected(tmp_path):
    w = World(1)
    shared = {'iron': 3}
    w.currency.wallets = {1: shared, 2: shared}
    write_snapshot(w, tmp_path/'shared', rules_id=RULES)
    r = read_snapshot(tmp_path/'shared', rules_id=RULES)
    assert r.currency.wallets[1] is r.currency.wallets[2]
    assert r.currency.wallets[1] is not shared
    r.currency.wallets[1]['iron'] += 1
    assert r.currency.wallets[2]['iron'] == 4 and shared['iron'] == 3
    w.currency.wallets = {1: {}}
    w.currency.wallets[1]['loop'] = w.currency.wallets
    with pytest.raises(CodecError, match='cycle'):
        write_snapshot(w, tmp_path/'bad', rules_id=RULES)
    assert not (tmp_path/'bad').exists()


def test_detached_identity_and_record_table_notifications(tmp_path):
    w = Simulation(generate_world(11, mature=True)).run(3)
    w.currency.wallets[1] = {'iron': 3}
    write_snapshot(w, tmp_path/'w', rules_id=RULES)
    r = read_snapshot(tmp_path/'w', rules_id=RULES)
    pid = next(iter(r.people))
    p = r.people[pid]
    assert type(r.people) is RecordTable
    assert p._index_table() is r.people
    r.people.ids('alive', True)
    p.alive = False
    assert pid not in r.people.ids('alive', True)
    assert w.people[pid].alive
    hid = next(iter(r.households))
    r.households.ids('alive', True)
    r.households[hid].alive = False
    assert hid not in r.households.ids('alive', True)
    assert w.households[hid].alive
    # Nested wallet, path and relationship identity remain independent.
    wallet_pid = next(iter(r.currency.wallets))
    original_wallet = dict(w.currency.wallets[wallet_pid])
    r.currency.wallets[wallet_pid]['iron'] = 999
    assert w.currency.wallets[wallet_pid] == original_wallet
    path_pid = next(iter(r.advancement.paths))
    r.advancement.paths[path_pid].abilities[0].progress += 0.25
    assert r.advancement.paths[path_pid].abilities[0].progress != w.advancement.paths[path_pid].abilities[0].progress
    key = next(iter(r.social.edges))
    r.social.edges[key].trust += .2
    assert r.social.edges[key].trust != w.social.edges[key].trust


def test_order_typed_keys_and_special_numeric_values(tmp_path):
    w = World(1)
    w.people = RecordTable({7: Person(7, 0, 1, 1), 2: Person(2, 0, 1, 1)})
    w.currency.wallets = {7: {'silver': -0.0, 'iron': float('inf'), 'gold': float('nan')}}
    w.genealogy.parents = {7: (2, 1), 2: ()}
    w.knowledge.beliefs = {(7, 2): .75, (2, 1): .125}
    ref = Ref('person', 7)
    w.emit('repeated immutable ref', Layer.REALITY, (ref, ref))
    write_snapshot(w, tmp_path/'w', rules_id=RULES)
    r = read_snapshot(tmp_path/'w', rules_id=RULES)
    same(w, r)
    assert list(r.people) == [7, 2]
    assert list(r.knowledge.beliefs) == [(7, 2), (2, 1)]


def test_cold_events_and_mutable_tail_exactly_preserved(tmp_path):
    w = World(1)
    for i in range(4300):
        w.year = i // 20
        w.emit('record', Layer.REALITY, (Ref('person', 1),), causes=() if i == 0 else (i,),
               nested={'text': ['é', i]})
    w.events = EventLog(w.events)
    w.events.seal_before(w.year - 2)
    # Deliberately sealed tail event is preserved without sealing its neighbors.
    w.events[-2].seal()
    w.events[-1]._sealed = False
    before_cache = list(w.events._cache)
    write_snapshot(w, tmp_path/'w', rules_id=RULES)
    assert list(w.events._cache) == before_cache
    r = read_snapshot(tmp_path/'w', rules_id=RULES)
    same(w, r)
    assert w.digest() == r.digest()
    assert len(r.events._chunks) == 2
    assert type(r.events[0].data) is FrozenDict
    assert type(r.events[0].data['nested']['text']) is FrozenList
    for event in (r.events[0], r.events[-2]):
        with pytest.raises(TypeError):
            event.kind = 'rewrite'
        with pytest.raises(TypeError):
            event.data['nested']['text'].append('rewrite')
    r.events[-1].data['nested']['text'].append('allowed')
    assert w.events[-1].data['nested']['text'][-1] != 'allowed'
    for x in (w, r):
        x.emit('next', Layer.REALITY, causes=(1,))
    assert w.events[-1] == r.events[-1]
    assert w.events_between(210, 211) == r.events_between(210, 211)


def test_event_indexes_not_silently_repaired(tmp_path):
    w = World(1)
    w.emit('test', Layer.REALITY)
    w.events = EventLog(w.events)
    w.events._offsets[0] = 10
    with pytest.raises(CodecError, match='index disagrees'):
        write_snapshot(w, tmp_path/'bad', rules_id=RULES)


def test_archive_linked_history_equal(tmp_path):
    w = Simulation(generate_world(843000, mature=True)).run(15)
    write_snapshot(w, tmp_path/'w', rules_id=RULES)
    r = read_snapshot(tmp_path/'w', rules_id=RULES)
    a, b = [export_archive(x, tmp_path/name) for x, name in ((w, 'a'), (r, 'b'))]
    assert a['logical_sha256'] == b['logical_sha256']
    with HistoryArchive(tmp_path/'a') as original, HistoryArchive(tmp_path/'b') as restored:
        pid = next(iter(w.people))
        assert original.person(pid) == restored.person(pid)
        resource = next(iter(w.magic_resources.resources.values()))
        assert original.provenance('magic_resource', resource.id) == restored.provenance('magic_resource', resource.id)
        assert original.causal_chain(resource.origin_event) == restored.causal_chain(resource.origin_event)


@pytest.mark.parametrize('damage', ['missing_root', 'extra_root', 'missing_row', 'ordinal', 'schema', 'version', 'namespace', 'identity'])
def test_committed_but_invalid_adapter_records_rejected(tmp_path, damage):
    w = World(1)
    w.people = {7: Person(7, 0, 1, 1), 2: Person(2, 0, 1, 1)}
    if damage == 'identity':
        w.currency.wallets = {
            1: {'a': {'value': 1}, 'b': {'value': 2}},
        }
    path = tmp_path/'w'
    write_snapshot(w, path, rules_id=RULES)
    with open_store(path) as store:
        manifest = store.read_record(META, 'manifest')
        head = store.head_metadata()
        changes = []
        if damage == 'missing_root': del manifest['collections']['world.cells']
        elif damage == 'extra_root': manifest['collections']['world.unknown'] = ('dict', 0, 0)
        elif damage == 'version': manifest['schema'] = 'unknown'
        elif damage == 'missing_row': changes.append(RecordChange('world.people', 7, delete=True))
        elif damage == 'ordinal': changes.append(RecordChange('world.people', 2, (0, w.people[2])))
        elif damage == 'schema': changes.append(RecordChange('world.people', 2, (1, w.people[2]), record_schema=2))
        elif damage == 'namespace': head['namespaces'] += ('unknown',)
        elif damage == 'identity':
            target = (
                ('field', 'currency'), ('field', 'wallets'),
                ('key', 1), ('key', 'a'),
            )
            owner = (
                ('field', 'currency'), ('field', 'wallets'),
                ('key', 1), ('key', 'b'),
            )
            changes.append(RecordChange(IDENTITY_LINKS, target, owner))
        changes.append(RecordChange(META, 'manifest', manifest))
        store.commit(store.generation, changes, (), head)
    with pytest.raises((StoreFormatError, StoreIntegrityError)):
        read_snapshot(path, rules_id=RULES)


def test_wrong_rules_and_unpublished_store_rejected(tmp_path):
    write_snapshot(World(1), tmp_path/'w', rules_id=RULES)
    with pytest.raises(StoreFormatError): read_snapshot(tmp_path/'w', rules_id='other')
    with TransactionalStore.create(tmp_path/'empty', simulation_schema=SCHEMA, rules_id=RULES, codec=WorldCodec()):
        pass
    with pytest.raises((KeyError, StoreFormatError)):
        read_snapshot(tmp_path/'empty', rules_id=RULES)
    with pytest.raises(FileExistsError): write_snapshot(World(2), tmp_path/'w', rules_id=RULES)
    assert read_snapshot(tmp_path/'w', rules_id=RULES).seed == 1


def test_failed_bootstrap_does_not_publish(tmp_path, monkeypatch):
    def fail(*args, **kwargs): raise RuntimeError('injected commit failure')
    monkeypatch.setattr(TransactionalStore, 'commit', fail)
    with pytest.raises(RuntimeError, match='injected'):
        write_snapshot(World(1), tmp_path/'w', rules_id=RULES)
    assert not (tmp_path/'w').exists()
    assert list(tmp_path.iterdir()) == []


def test_schema_checked_reads_and_pinned_generation(tmp_path):
    path = tmp_path/'w'
    write_snapshot(World(1), path, rules_id=RULES)
    with open_store(path) as reader, open_store(path) as writer:
        writer.db.execute('PRAGMA busy_timeout=0')
        with reader.read_transaction() as generation:
            before = reader.read_records('world.seed', expected_record_schema=1)
            with pytest.raises(StoreError):
                with reader.read_transaction(): pass
            with pytest.raises(StoreError):
                reader.commit(generation, (), (), reader.head_metadata())
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                writer.commit(generation, [RecordChange('world.seed', 0, (0, 9))], (), writer.head_metadata())
            assert reader.generation == generation
            assert reader.read_records('world.seed', expected_record_schema=1) == before
        writer.commit(generation, [RecordChange('world.seed', 0, (0, 9), record_schema=2)], (), writer.head_metadata())
        assert reader.generation == generation + 1
        with pytest.raises(StoreFormatError): reader.read_records('world.seed', expected_record_schema=1)
        with pytest.raises(StoreFormatError): reader.read_record('world.seed', 0, expected_record_schema=1)
        with pytest.raises(RuntimeError):
            with reader.read_transaction(): raise RuntimeError('body failed')
        assert not reader.db.in_transaction


def test_no_creation_hooks_and_both_supported_import_paths(tmp_path, monkeypatch):
    from ate_sim.advancement import AbilityProgress
    w = Simulation(generate_world(19, mature=True)).run(2)
    write_snapshot(w, tmp_path/'w', rules_id=RULES)
    def forbidden(*args): pytest.fail('creation hook called during restore')
    monkeypatch.setattr(AbilityProgress, '__post_init__', forbidden)
    assert read_snapshot(tmp_path/'w', rules_id=RULES).digest() == w.digest()
    code = '''
from simulation.ate_sim.persistence_adapters import read_snapshot
import sys
print(read_snapshot(sys.argv[1], rules_id=sys.argv[2]).digest())
'''
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path/'w'), RULES], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == w.digest()
