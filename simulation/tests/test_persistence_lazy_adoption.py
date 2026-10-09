import pytest

from ate_sim.core import World
from ate_sim.incremental_store import StoreIntegrityError, StoreError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'adoption-query-gates'
NS = 'world.culture.adoption'


def converted(tmp_path, history=3):
    world = World(843000)
    world.culture.adoption = {(2, key): .001 for key in range(history)}
    world.culture.adoption.update({(1, history + key): .7 for key in range(8)})
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_dormant_adoption_open_query_and_edits_are_bounded(tmp_path, history):
    with open_lazy_world_session(converted(tmp_path, history), rules_id=RULES) as session:
        adoption = session.world.culture.adoption
        assert adoption.diagnostics()['payload_loads'] == 0
        before = session.store.diagnostics()
        assert adoption.items_above(.62, 1) == [((1, history + key), .7) for key in range(8)]
        assert adoption.diagnostics()['payload_loads'] == 8
        assert session.store.diagnostics().query_rows - before.query_rows == 8
        for key in range(8):
            adoption[(1, history + key)] = .6
        assert adoption.items_above(.62, 1) == []
        before_save = session.store.diagnostics()
        session.save()
        after_save = session.store.diagnostics()
        assert after_save.payload_writes - before_save.payload_writes <= 12
        assert after_save.payload_write_bytes - before_save.payload_write_bytes < 4096
        assert adoption.items_above(.62, 1) == []


def test_strict_edges_current_overlay_order_and_frozen_snapshot(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        a = session.world.culture.adoption
        for index, threshold in enumerate((.008, .01, .22, .35, .62)):
            a[(9, index)] = threshold
            a[(9, index + 10)] = threshold + .000001
            matches = a.items_above(threshold, 9)
            assert (9, index) not in dict(matches)
            assert (9, index + 10) in dict(matches)
        del a[(1, 3)]
        a[(1, 3)] = .8
        snapshot = a.items_above(.62, 1)
        assert [key for key, value in snapshot] == [(1, key) for key in range(4, 11)] + [(1, 3)]
        a[(1, 4)] = .1
        assert dict(snapshot)[(1, 4)] == .7
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert [key for key, value in session.world.culture.adoption.items_above(.62, 1)] == [(1, key) for key in range(5, 11)] + [(1, 3)]


def test_missing_query_row_fails_closed(tmp_path):
    with open_lazy_world_session(converted(tmp_path), rules_id=RULES) as session:
        session.store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND record_key=?',
                                (NS, 'settlement-threshold', session.store.codec.encode((1, 3))))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            session.world.culture.adoption.items_above(.62, 1)


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_counts_and_cells_share_frozen_failure_recovery(tmp_path, phase):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        a = session.world.culture.adoption
        a[(1, 3)] = .1
        a[(7, 99)] = .8
        def fail(current):
            if current == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert len(a.items_above(.62, 1)) == 7
        assert a.items_above(.62, 7) == [((7, 99), .8)]
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert len(session.world.culture.adoption.items_above(.62)) == 8


def test_normal_ack_rejects_missing_new_query_membership(tmp_path):
    session = open_lazy_world_session(converted(tmp_path), rules_id=RULES)
    session.world.culture.adoption[(1, 3)] = .8
    def remove_marker(phase):
        if phase == 'after_commit':
            session.store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND record_key=? AND valid_to IS NULL AND index_name=?',
                                    (NS, session.store.codec.encode((1, 3)), 'settlement-threshold'))
            session.store.db.commit()
    session.store._phase_hook = remove_marker
    try:
        with pytest.raises(StoreIntegrityError):
            session.save()
    finally:
        session.store.db.close()


@pytest.mark.parametrize('history', [1000, 10000])
@pytest.mark.parametrize('innovation', [False, True])
def test_real_cultural_step_matches_native_without_dormant_scan(tmp_path, history, innovation):
    from ate_sim.core import Settlement, Cell, LocalState, RNG
    from ate_sim.culture import Practice, cultural_step
    world = World(843000)
    world.settlements[1] = Settlement(1, 0, 0)
    world.cells[(0, 0)] = Cell(0, 0, .5, .5, .5, .5, .5)
    world.local[1] = LocalState()
    world.culture.adoption = {(1, key): .001 for key in range(history)}
    for key in range(history, history + 8):
        world.culture.practices[key] = Practice(key, 'construction', 'probe', 0, 1, {'refinement': .1})
        world.culture.adoption[(1, key)] = .7
    world.culture.next_practice = history + 8
    class ForceInnovation:
        def stream(self, *args): return self
        def uniform(self, low, high): return 0.
        def random(self): return 0.
    def culture_rng(): return ForceInnovation() if innovation else RNG(world.seed)
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    cultural_step(world, world.culture, culture_rng())
    with open_lazy_world_session(path, rules_id=RULES) as session:
        a = session.world.culture.adoption
        def forbidden_scan():
            raise AssertionError('cultural_step scanned complete adoption history')
        a.items = forbidden_scan
        cultural_step(session.world, session.world.culture, culture_rng())
        del a.items
        assert a.diagnostics()['payload_loads'] == 8
        assert session.world.culture.practices.diagnostics()['payload_loads'] == 8
        session.save()
        assert session.world.digest() == world.digest()


def test_old_pin_queries_and_empty_new_settlement_authority(tmp_path):
    path = converted(tmp_path)
    old = open_lazy_world_session(path, rules_id=RULES)
    try:
        with open_lazy_world_session(path, rules_id=RULES) as session:
            session.world.culture.adoption[(1, 3)] = .1
            session.world.culture.adoption[(8, 99)] = .001
            session.save()
            assert session.world.culture.adoption.items_above(.62, 8) == []
        assert len(old.world.culture.adoption.items_above(.62, 1)) == 8
        assert old.world.culture.adoption.items_above(.62, 8) == []
    finally:
        old.close()


@pytest.mark.parametrize('namespace,key', [
    ('aux.lazy.adoption.buckets', (1, .62)),
    ('aux.lazy.adoption.settlements', 1),
])
def test_missing_known_authority_fails_closed(tmp_path, namespace, key):
    with open_lazy_world_session(converted(tmp_path), rules_id=RULES) as session:
        session.store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                                (namespace, session.store.codec.encode(key)))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            session.world.culture.adoption.items_above(.62, 1)


def test_noop_save_clean_sidecars_and_portable_materialization(tmp_path):
    from ate_sim import checkpoint
    session = open_lazy_world_session(converted(tmp_path, 1000), rules_id=RULES)
    a = session.world.culture.adoption
    a.items_above(.62, 1)
    a[(1, 1000)] = .7
    old_generation = session.pin.captured_head
    before = session.store.diagnostics()
    assert session.save() == old_generation
    assert session.store.diagnostics().payload_writes == before.payload_writes
    for key in range(1000):
        a[(2, key)]
    assert a.diagnostics()['resident_records'] <= 256
    assert len(a._baseline_payload) <= 256
    assert len(a._baseline_ordinal) <= 256
    detached = session.detach(materialize_history=True)
    assert type(detached.culture.adoption) is dict
    assert checkpoint.loads(checkpoint.dumps(detached)).digest() == detached.digest()
    with pytest.raises(StoreError, match='closed|detached|active'):
        a.items_above(.62, 1)


def test_unmarked_legacy_adoption_remains_eager_without_open_writes(tmp_path):
    from ate_sim.incremental_store import _record_checksum
    from ate_sim.persistence_adapters import WorldCodec, SCHEMA, META
    from ate_sim.persistence_lazy_store import LazyRecordStore
    from ate_sim.culture import adoption_items_above
    path = converted(tmp_path)
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA, expected_rules_id=RULES) as store:
        rows = store.db.execute('SELECT typed_key,payload,valid_from FROM lazy_record_versions WHERE namespace=? AND valid_to IS NULL', (NS,)).fetchall()
        for key, payload, generation in rows:
            ordinal = store.db.execute('SELECT ordinal FROM lazy_order_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL', (NS, key)).fetchone()[0]
            envelope = store.codec.encode((ordinal, store.codec.decode(payload)))
            checksum = _record_checksum(NS, key, 1, store.codec.version, generation, envelope)
            store.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)', (NS, key, envelope, checksum, store.codec.version, 1, generation))
        for sql_table in ('lazy_record_versions', 'lazy_order_versions', 'lazy_query_versions', 'lazy_namespace_state'):
            store.db.execute('DELETE FROM ' + sql_table + ' WHERE namespace IN (?,?,?)',
                             (NS, 'aux.lazy.adoption.buckets', 'aux.lazy.adoption.settlements'))
        for key, value, schema in store.read_records(META, expected_record_schema=1):
            layout = value if key == 'collections/v1' else value['collections']
            old = layout[NS]
            layout[NS] = (old[0].removesuffix('-scalar/v1'), old[1], old[2])
            typed_key, payload = store.codec.encode(key), store.codec.encode(value)
            generation = store.db.execute('SELECT last_changed_generation FROM records WHERE namespace=? AND typed_key=?', (META, typed_key)).fetchone()[0]
            checksum = _record_checksum(META, typed_key, schema, store.codec.version, generation, payload)
            store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?', (payload, checksum, META, typed_key))
        store.db.commit()
        store.verify_all()
        before = store.db.execute('SELECT namespace,typed_key,payload,payload_checksum FROM records ORDER BY namespace,typed_key').fetchall()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert NS not in session._scalar_tables
        assert len(adoption_items_above(session.world.culture.adoption, .62, 1)) == 8
        assert session.store.db.execute('SELECT namespace,typed_key,payload,payload_checksum FROM records ORDER BY namespace,typed_key').fetchall() == before
