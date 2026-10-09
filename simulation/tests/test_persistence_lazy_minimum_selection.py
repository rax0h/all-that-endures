import pytest

from ate_sim.core import World
from ate_sim.communities import Community
from ate_sim.metaphysics import ResurrectionToken
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.incremental_store import StoreIntegrityError

RULES = 'minimum-selection-gates'


def converted(tmp_path, history=5, alias=False):
    world = World(843000)
    for key in range(history):
        world.communities.communities[key] = Community(key, 'unrelated', 0, 2)
        world.metaphysics.resurrection_tokens[key] = ResurrectionToken(key, 1, 'god', 'probe', 0, 1, consumed_year=1)
    for offset, ident in enumerate((9, -3, -3, 2, 4, 5, 6, 7)):
        key = history + offset
        world.communities.communities[key] = Community(ident, 'founder_network', 0, 1, active=False)
        world.metaphysics.resurrection_tokens[key] = ResurrectionToken(ident, 1, 'god', str(key), 0, 1)
    if alias:
        world.currency.wallets[11] = {'token': world.metaphysics.resurrection_tokens[history + 1],
                                      'community': world.communities.communities[history + 1]}
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_minimum_loads_one_candidate_independent_of_history(tmp_path, history):
    with open_lazy_world_session(converted(tmp_path, history), rules_id=RULES) as session:
        c, t = session.world.communities.communities, session.world.metaphysics.resurrection_tokens
        assert c.diagnostics()['payload_loads'] == 0
        assert t.diagnostics()['payload_loads'] == 0
        before_query = session.store.diagnostics()
        assert session.world.communities.local_root(1) == -3
        assert session.world.metaphysics.available_token(1).patron_id == str(history + 1)
        assert c.diagnostics()['payload_loads'] == 1
        assert t.diagnostics()['payload_loads'] == 1
        assert session.store.diagnostics().query_rows - before_query.query_rows == 2
        assert len(t._minimum_cache) <= 256
        assert len(c._minimum_cache) <= 256


@pytest.mark.parametrize('history', [1000, 10000])
def test_one_token_consumption_writes_bounded_metadata(tmp_path, history):
    with open_lazy_world_session(converted(tmp_path, history), rules_id=RULES) as session:
        token = session.world.metaphysics.available_token(1)
        token.consumed_year = 2
        before = session.store.diagnostics()
        plan = session._prepare_hybrid_save()
        assert [(unit.namespace, len(unit.version_changes)) for unit in plan.scalar_record_plans if unit.version_changes] == [('world.metaphysics.resurrection_tokens', 1)]
        assert len(plan.scalar_index_version_changes) == 5
        session.save()
        after = session.store.diagnostics()
        # One token, four auxiliary payloads and the two fixed event-storage
        # session markers; the fifth auxiliary change is a deletion.
        assert after.payload_writes - before.payload_writes <= 7
        assert after.payload_write_bytes - before.payload_write_bytes < 4096
        assert session.world.metaphysics.available_token(1).patron_id == str(history + 2)
        assert session.world.metaphysics.resurrection_tokens.diagnostics()['payload_loads'] == 2


def test_old_pin_retains_prior_minimum_and_node_links(tmp_path):
    path = converted(tmp_path)
    old = open_lazy_world_session(path, rules_id=RULES)
    try:
        assert old.world.metaphysics.available_token(1) is old.world.metaphysics.resurrection_tokens[6]
        with open_lazy_world_session(path, rules_id=RULES) as session:
            session.world.metaphysics.resurrection_tokens[6].consumed_year = 2
            session.save()
            assert session.world.metaphysics.available_token(1) is session.world.metaphysics.resurrection_tokens[7]
        assert old.world.metaphysics.available_token(1) is old.world.metaphysics.resurrection_tokens[6]
    finally:
        old.close()


def test_id_ties_reinsertion_and_direct_edits_preserve_native_selection(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        t = session.world.metaphysics.resurrection_tokens
        first = t[6]
        del t[6]
        t[6] = first
        assert session.world.metaphysics.available_token(1) is t[7]
        t[7].consumed_year = 2
        assert session.world.metaphysics.available_token(1) is t[6]
        t[5].id = -8
        assert session.world.metaphysics.available_token(1) is t[5]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.metaphysics.available_token(1) is session.world.metaphysics.resurrection_tokens[5]
        assert tuple(session.world.metaphysics.resurrection_tokens)[-1] == 6


def test_diaspora_uses_minimum_record_id_and_stable_tie(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        c = session.world.communities.communities
        c[80] = Community(-2, 'diaspora', 0, 4, parent=9, active=False)
        c[70] = Community(-2, 'diaspora', 0, 4, parent=9)
        assert session.world.communities.diaspora(9, 4, 8, 77) is c[80]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.communities.diaspora(9, 4, 8, 77) is session.world.communities.communities[80]


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_minimum_metadata_and_records_recover_together(tmp_path, phase):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        t = session.world.metaphysics.resurrection_tokens
        t[6].consumed_year = 2
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
        assert session.world.metaphysics.available_token(1) is t[7]
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.metaphysics.available_token(1) is session.world.metaphysics.resurrection_tokens[7]


def test_normal_ack_rejects_missing_minimum_query_witness(tmp_path):
    session = open_lazy_world_session(converted(tmp_path), rules_id=RULES)
    session.world.metaphysics.resurrection_tokens[6].id = -9
    def remove_marker(phase):
        if phase == 'after_commit':
            session.store.db.execute("DELETE FROM lazy_query_versions WHERE namespace=? AND record_key=? AND index_name LIKE 'minimum/v1/%' AND valid_to IS NULL",
                                    ('world.metaphysics.resurrection_tokens', session.store.codec.encode(6)))
            session.store.db.commit()
    session.store._phase_hook = remove_marker
    try:
        with pytest.raises(StoreIntegrityError):
            session.save()
    finally:
        session.store.db.close()


def test_noop_direct_field_edits_do_not_retain_dirty_history(tmp_path):
    with open_lazy_world_session(converted(tmp_path, 1000), rules_id=RULES) as session:
        c = session.world.communities.communities
        generation = session.pin.captured_head
        for key in range(1000):
            c[key].active = True
            assert session.save() == generation
        assert c.diagnostics()['dirty_records'] == 0
        assert c.diagnostics()['resident_records'] <= 256
        assert c.diagnostics()['touched_membership_buckets'] == 0


@pytest.mark.parametrize('first', ['wallet', 'record'])
def test_shared_records_route_minimum_edits_reopen_and_detach(tmp_path, first):
    from ate_sim import checkpoint
    path = converted(tmp_path, alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        token = session.wallets[11]['token'] if first == 'wallet' else session.world.metaphysics.resurrection_tokens[6]
        assert token is session.world.metaphysics.resurrection_tokens[6]
        token.consumed_year = 2
        assert session.world.metaphysics.available_token(1) is session.world.metaphysics.resurrection_tokens[7]
        community = session.wallets[11]['community']
        assert community is session.world.communities.communities[6]
        community.origin_settlement = 9
        assert session.world.communities.local_root(1) == -3
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.wallets[11]['token'] is session.world.metaphysics.resurrection_tokens[6]
        assert session.wallets[11]['community'] is session.world.communities.communities[6]
        detached = session.detach(materialize_history=True)
        assert detached.currency.wallets[11]['token'] is detached.metaphysics.resurrection_tokens[6]
        assert checkpoint.loads(checkpoint.dumps(detached)).digest() == detached.digest()


def test_rank_encoding_matches_native_integer_order(tmp_path):
    from ate_sim.persistence_lazy_minimum import numeric_rank
    from ate_sim.persistence_adapters import WorldCodec
    values = [float('-inf'), -(10 ** 100), -10001, -1000, -99, -10, -9, -1.5, -1, -.5, 0, 5e-324, .5, 1, 1.25, 1.5, 9, 10, 99, 1000, 10001, 10 ** 100, float('inf')]
    codec = WorldCodec()
    assert sorted(values, key=numeric_rank) == values
    assert sorted(values, key=lambda value: codec.encode(numeric_rank(value))) == values
    assert numeric_rank(True) == numeric_rank(1) == numeric_rank(1.0)
    assert numeric_rank(False) == numeric_rank(0) == numeric_rank(-0.0)
    mixed = [10 ** 100, 1e100, 2 ** 53 + 1, float(2 ** 53), .1, -.1]
    assert sorted(mixed, key=numeric_rank) == sorted(mixed)


def test_numeric_id_representatives_and_stable_equal_ties_survive_reopen(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        tokens = session.world.metaphysics.resurrection_tokens
        tokens[6].id = -.25
        tokens[7].id = -.25
        tokens[5].id = 0
        for key in range(8, 13):
            tokens[key].id = 1
        assert session.world.metaphysics.available_token(1) is tokens[6]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        tokens = session.world.metaphysics.resurrection_tokens
        assert type(tokens[6].id) is float
        assert session.world.metaphysics.available_token(1) is tokens[6]


def test_mixed_minimum_operations_match_native_stable_sort(tmp_path):
    import copy
    import random
    path = converted(tmp_path)
    rr = random.Random(19)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.world.metaphysics.resurrection_tokens
        native = {key: copy.deepcopy(value) for key, value in table.items()}
        for turn in range(100):
            key, operation = rr.randrange(18), rr.randrange(4)
            if operation == 0:
                token = ResurrectionToken(rr.randrange(-5, 6), rr.randrange(1, 3), 'god', str(turn), 0, 1)
                table[key] = copy.deepcopy(token)
                native[key] = token
            elif operation == 1 and key in native:
                del table[key]
                del native[key]
            elif key in native:
                field = 'id' if operation == 2 else 'consumed_year'
                value = rr.randrange(-5, 6) if field == 'id' else rr.choice((None, 3))
                setattr(table[key], field, value)
                setattr(native[key], field, value)
            for person in (1, 2):
                expected = next((token for token in sorted(native.values(), key=lambda token: token.id)
                                 if token.person == person and token.consumed_year is None), None)
                actual = session.world.metaphysics.available_token(person)
                assert (None if actual is None else actual.__getstate__()) == (None if expected is None else expected.__getstate__())
            if turn % 7 == 0:
                session.save()
                assert tuple(table) == tuple(native)
        session.save()


@pytest.mark.parametrize('plane', ['query', 'node', 'header'])
def test_missing_minimum_authority_fails_closed(tmp_path, plane):
    from ate_sim.persistence_lazy_minimum import scope_name, HEADER_NAMESPACE, NODE_NAMESPACE
    with open_lazy_world_session(converted(tmp_path), rules_id=RULES) as session:
        namespace = 'world.metaphysics.resurrection_tokens'
        scope = scope_name('person_consumed', (1, None), session.store.codec)
        if plane == 'query':
            session.store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND record_key=?',
                                    (namespace, scope, session.store.codec.encode(6)))
        else:
            key = (namespace, scope, 6) if plane == 'node' else (namespace, scope)
            target = NODE_NAMESPACE if plane == 'node' else HEADER_NAMESPACE
            session.store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                                    (target, session.store.codec.encode(key)))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            session.world.metaphysics.available_token(1)


def test_unmarked_legacy_minimum_families_keep_native_selection(tmp_path):
    from ate_sim.incremental_store import _record_checksum
    from ate_sim.persistence_adapters import WorldCodec, SCHEMA, META
    from ate_sim.persistence_lazy_store import LazyRecordStore
    from ate_sim.persistence_lazy_minimum import FIELDS, HEADER_NAMESPACE, NODE_NAMESPACE
    path = converted(tmp_path)
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA, expected_rules_id=RULES) as store:
        for namespace in FIELDS:
            rows = store.db.execute('SELECT typed_key,payload,valid_from FROM lazy_record_versions WHERE namespace=? AND valid_to IS NULL', (namespace,)).fetchall()
            for key, payload, generation in rows:
                ordinal = store.db.execute('SELECT ordinal FROM lazy_order_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL', (namespace, key)).fetchone()[0]
                envelope = store.codec.encode((ordinal, store.codec.decode(payload)))
                checksum = _record_checksum(namespace, key, 1, store.codec.version, generation, envelope)
                store.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)', (namespace, key, envelope, checksum, store.codec.version, 1, generation))
        for namespace in (*FIELDS, HEADER_NAMESPACE, NODE_NAMESPACE):
            for sql_table in ('lazy_record_versions', 'lazy_order_versions', 'lazy_query_versions', 'lazy_namespace_state'):
                store.db.execute('DELETE FROM ' + sql_table + ' WHERE namespace=?', (namespace,))
        for key, value, schema in store.read_records(META, expected_record_schema=1):
            layout = value if key == 'collections/v1' else value['collections']
            for namespace in FIELDS:
                old = layout[namespace]
                layout[namespace] = (old[0].removesuffix('-scalar/v1'), old[1], old[2])
            encoded_key, payload = store.codec.encode(key), store.codec.encode(value)
            generation = store.db.execute('SELECT last_changed_generation FROM records WHERE namespace=? AND typed_key=?', (META, encoded_key)).fetchone()[0]
            checksum = _record_checksum(META, encoded_key, schema, store.codec.version, generation, payload)
            store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?', (payload, checksum, META, encoded_key))
        store.db.commit()
        store.verify_all()
        before = store.db.execute('SELECT namespace,typed_key,payload,payload_checksum FROM records ORDER BY namespace,typed_key').fetchall()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert not set(FIELDS) & session._scalar_tables.keys()
        assert session.world.communities.local_root(1) == -3
        assert session.world.metaphysics.available_token(1) is session.world.metaphysics.resurrection_tokens[6]
        assert session.store.db.execute('SELECT namespace,typed_key,payload,payload_checksum FROM records ORDER BY namespace,typed_key').fetchall() == before


def test_failed_detach_keeps_retained_minimum_record_callback(tmp_path, monkeypatch):
    from ate_sim import persistence_lifecycle as lifecycle
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        token = session.world.metaphysics.available_token(1)
        def fail(phase, _session):
            if phase == 'before_publish':
                raise OSError('detach staging')
        monkeypatch.setattr(lifecycle, '_lifecycle_phase', fail)
        with pytest.raises(OSError, match='detach staging'):
            session.detach(materialize_history=True)
        token.consumed_year = 2
        session.save()
        assert session.world.metaphysics.available_token(1) is session.world.metaphysics.resurrection_tokens[7]
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.metaphysics.available_token(1) is session.world.metaphysics.resurrection_tokens[7]


@pytest.mark.parametrize('namespace', ['aux.lazy.minimum.headers', 'aux.lazy.minimum.nodes'])
def test_marked_empty_family_requires_checked_auxiliary_namespace(tmp_path, namespace):
    import sqlite3
    world = World(843000)
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    with sqlite3.connect(path) as db:
        db.execute('DELETE FROM lazy_namespace_state WHERE namespace=?', (namespace,))
    with pytest.raises(StoreIntegrityError, match='minimum auxiliary'):
        open_lazy_world_session(path, rules_id=RULES)
