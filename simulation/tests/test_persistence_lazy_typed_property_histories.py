import pytest

from ate_sim.core import World
from ate_sim.economy import Property
from ate_sim.infrastructure import Infrastructure
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session

RULES = 'typed-property-history-gates'


def converted(tmp_path, history, alias=False, eager_alias=False, property_count=1, record_alias=False):
    world = World(843000)
    world.economy.property[1] = Property(1, 'farm', 1, 'household', 1, 10., 3,
        list(range(1, history + 1)), [(year, 'household', 1, year + 1) for year in range(history)])
    world.infrastructure.assets[1] = Infrastructure(1, 'farm', (1,), .8, 1., 0,
        provenance=list(range(1, history + 1)))
    for key in range(2, property_count + 1):
        world.economy.property[key] = Property(key, 'farm', 1, 'household', 1 if key <= 8 else key, 10., 3)
    if alias:
        world.infrastructure.assets[1].provenance = world.economy.property[1].provenance
        world.currency.wallets[11] = {'history': world.economy.property[1].provenance}
    if record_alias:
        world.currency.wallets[11] = {'property': world.economy.property[1]}
    if eager_alias:
        from ate_sim.divinity import God
        world.divinity.gods['knowledge'] = God('knowledge', 'Knowledge', ('knowledge',),
            manifestations=world.economy.property[1].provenance)
        world.currency.wallets[12] = {'literal': ('typed-history/v1', 'list', 999)}
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_property_transfer_has_bounded_history_pages_and_bytes(tmp_path, history):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        prop = session.world.economy.property[1]
        assert prop.provenance.diagnostics()['page_loads'] == 0
        assert prop.ownership.diagnostics()['page_loads'] == 0
        before = session.store.diagnostics()
        session.world.economy.transfer(1, 'person', 4, history + 2)
        assert prop.provenance.diagnostics()['page_loads'] <= 1
        assert prop.ownership.diagnostics()['page_loads'] <= 1
        session.save()
        after = session.store.diagnostics()
        assert after.payload_write_bytes - before.payload_write_bytes < 32768
        assert len(prop.provenance) == history + 1
        assert prop.provenance[-1] == history + 2
        assert prop.ownership[-1] == (3, 'person', 4, history + 2)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        prop = session.world.economy.property[1]
        assert prop.owner_kind == 'person' and prop.owner_id == 4
        assert prop.provenance[-1] == history + 2
        assert prop.ownership[-1] == (3, 'person', 4, history + 2)


@pytest.mark.parametrize('history', [1000, 10000])
def test_property_owner_query_reads_only_eight_headers_and_no_pages(tmp_path, history):
    path = converted(tmp_path, history, property_count=history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.world.economy.property
        assert table.diagnostics()['payload_loads'] == 0
        props = session.world.economy.owned('household', 1)
        assert [prop.id for prop in props] == list(range(1, 9))
        assert table.diagnostics()['payload_loads'] == 8
        assert all(prop.provenance.diagnostics()['page_loads'] == 0 for prop in props)
        assert all(prop.ownership.diagnostics()['page_loads'] == 0 for prop in props)


@pytest.mark.parametrize('history', [1000, 10000])
def test_infrastructure_condition_edit_does_not_read_history(tmp_path, history):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        asset = session.world.infrastructure.assets[1]
        assert asset.provenance.diagnostics()['page_loads'] == 0
        before = session.store.diagnostics()
        session.world.infrastructure.maintain(1, .1)
        session.save()
        after = session.store.diagnostics()
        assert asset.provenance.diagnostics()['page_loads'] == 0
        assert after.payload_write_bytes - before.payload_write_bytes < 16384
        session.world.infrastructure.maintain(1, .1, history + 2)
        assert asset.provenance.diagnostics()['page_loads'] <= 1
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.infrastructure.assets[1].provenance[-1] == history + 2


@pytest.mark.parametrize('first', ['wallet', 'property'])
def test_typed_history_raw_shared_copies_relink_and_detach_once(tmp_path, first):
    from ate_sim import checkpoint
    path = converted(tmp_path, 1000, alias=True)
    session = open_lazy_world_session(path, rules_id=RULES)
    if first == 'wallet':
        history = session.wallets[11]['history']
    else:
        history = session.world.economy.property[1].provenance
    assert history is session.world.economy.property[1].provenance
    assert history is session.world.infrastructure.assets[1].provenance
    assert history is session.wallets[11]['history']
    history.append(1002)
    session.save()
    session.close()
    session = open_lazy_world_session(path, rules_id=RULES)
    assert session.wallets[11]['history'] is session.world.economy.property[1].provenance
    assert session.world.infrastructure.assets[1].provenance[-1] == 1002
    detached = session.detach(materialize_history=True)
    assert detached.economy.property[1].provenance is detached.currency.wallets[11]['history']
    assert detached.infrastructure.assets[1].provenance is detached.currency.wallets[11]['history']
    assert checkpoint.loads(checkpoint.dumps(detached)).digest() == detached.digest()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_typed_history_save_failure_keeps_frozen_plan_and_resolves(tmp_path, phase):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        prop = session.world.economy.property[1]
        session.world.economy.transfer(1, 'person', 4, 1002)
        def fail(current):
            if current == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        with pytest.raises(StoreError):
            prop.provenance.append(1003)
        with pytest.raises(StoreError):
            prop.provenance[-1]
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.economy.property[1].provenance[-1] == 1002


def test_history_replacement_splits_alias_and_old_child_cannot_dirty_replacement(tmp_path):
    path = converted(tmp_path, 5, alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        prop = session.world.economy.property[1]
        old = prop.provenance
        prop.provenance = [10, 11]
        old.append(12)
        assert prop.provenance[:] == [10, 11]
        assert session.world.infrastructure.assets[1].provenance[-1] == 12
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.economy.property[1].provenance[:] == [10, 11]
        assert session.world.infrastructure.assets[1].provenance[-1] == 12


def test_typed_history_failed_detach_preserves_mutation_routes(tmp_path, monkeypatch):
    from ate_sim import persistence_lifecycle as lifecycle
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.world.economy.property[1].provenance
        def fail(phase, _session):
            if phase == 'before_publish':
                raise OSError('failed detach')
        monkeypatch.setattr(lifecycle, '_lifecycle_phase', fail)
        with pytest.raises(OSError, match='failed detach'):
            session.detach(materialize_history=True)
        history.append(10)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.economy.property[1].provenance[-1] == 10


def test_checked_descriptor_cannot_silently_drop_complete_tail_page(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError, _framed_sha
    from ate_sim.persistence_adapters import WorldCodec, SCHEMA
    from ate_sim.persistence_lazy_store import LazyRecordStore, _version_checksum
    path = converted(tmp_path, 256)
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA, expected_rules_id=RULES) as store:
        key, schema, codec, start, end, members = store.db.execute("SELECT typed_key,record_schema,codec_version,valid_from,valid_to,memberships FROM lazy_record_versions WHERE namespace='aux.lazy.nested.descriptors' ORDER BY typed_key LIMIT 1").fetchone()
        payload = store.codec.encode(('list', 128, 128))
        checksum = _version_checksum('aux.lazy.nested.descriptors', key, schema, codec, start, end, members, payload)
        store.db.execute("UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace='aux.lazy.nested.descriptors' AND typed_key=?", (payload, _framed_sha(b'lazy-payload-v1', payload), checksum, key))
        store.db.commit()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        with pytest.raises(StoreIntegrityError, match='nested list page extent'):
            list(session.world.economy.property.values())


def test_typed_history_eager_alias_survives_removal_of_all_lazy_placements(tmp_path):
    path = converted(tmp_path, 1000, eager_alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.world.divinity.gods['knowledge'].manifestations
        assert session.wallets[12]['literal'] == ('typed-history/v1', 'list', 999)
        assert history is session.world.economy.property[1].provenance
        session.world.economy.property[1].provenance = [9]
        history.append(1002)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.world.divinity.gods['knowledge'].manifestations
        assert history[-1] == 1002
        assert history.diagnostics()['page_loads'] == 1
        history.append(1003)
        session.save()
        detached = session.detach(materialize_history=True)
        assert type(detached.divinity.gods['knowledge'].manifestations) is list
        assert detached.divinity.gods['knowledge'].manifestations[-1] == 1003
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.divinity.gods['knowledge'].manifestations[-1] == 1003


def test_replaced_eager_history_does_not_dirty_replacement(tmp_path):
    path = converted(tmp_path, 5, eager_alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        god = session.world.divinity.gods['knowledge']
        old = god.manifestations
        god.manifestations = [20]
        session.save()
        old.append(30)
        assert god.manifestations == [20]
        assert ('world.divinity.gods', 'knowledge') not in session._eager_tracker._dirty
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.divinity.gods['knowledge'].manifestations == [20]
        assert session.world.economy.property[1].provenance[-1] == 30


def test_typed_history_old_pin_noop_and_retained_child_after_owner_eviction(tmp_path):
    path = converted(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES) as writer:
        for key in range(2, 302):
            writer.world.economy.property[key] = Property(key, 'farm', 1, 'household', 1, 10., 3)
        writer.save()
    with open_lazy_world_session(path, rules_id=RULES) as writer, open_lazy_world_session(path, rules_id=RULES) as reader:
        prop = writer.world.economy.property[1]
        history = prop.provenance
        old = reader.world.economy.property[1].provenance
        for key in range(2, 302):
            writer.world.economy.property[key]
        assert len(dict.keys(writer.world.economy.property)) <= 256
        generation = writer.pin.captured_head
        history.append(1002)
        history.pop()
        assert writer.save() == generation
        assert writer._nested_dirty == {}
        assert history.diagnostics()['dirty_pages'] == 0
        history.append(1003)
        writer.save()
        assert len(old) == 1000 and old[-1] == 1000
        assert writer.world.economy.property[1].provenance is history
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.economy.property[1].provenance[-1] == 1003


def test_eager_history_introduced_after_open_has_checked_labels_on_reopen(tmp_path):
    from ate_sim.divinity import God
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.world.economy.property[1].provenance
        session.world.divinity.gods['knowledge'] = God('knowledge', 'Knowledge', ('knowledge',), manifestations=history)
        history.append(10)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.divinity.gods['knowledge'].manifestations is session.world.economy.property[1].provenance
        assert session.world.divinity.gods['knowledge'].manifestations[-1] == 10


def test_normal_acknowledgement_checks_exact_nested_page_evidence(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError, _framed_sha
    from ate_sim.persistence_lazy_store import _version_checksum
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.economy.property[1].provenance.append(10)
        original = []
        def corrupt(phase):
            if phase != 'after_commit':
                return
            row = session.store.db.execute("SELECT typed_key,record_schema,codec_version,valid_from,valid_to,memberships,payload,payload_checksum,row_checksum FROM lazy_record_versions WHERE namespace='aux.lazy.nested.list_pages' AND valid_to IS NULL ORDER BY valid_from DESC LIMIT 1").fetchone()
            original.append(row)
            key, schema, codec, start, end, members, *_ = row
            payload = session.store.codec.encode((1, 2, 3, 4, 5, 99))
            checksum = _version_checksum('aux.lazy.nested.list_pages', key, schema, codec, start, end, members, payload)
            session.store.db.execute("UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace='aux.lazy.nested.list_pages' AND typed_key=? AND valid_from=?", (payload, _framed_sha(b'lazy-payload-v1', payload), checksum, key, start))
            session.store.db.commit()
        session.store._phase_hook = corrupt
        with pytest.raises(StoreIntegrityError, match='saved nested authority evidence mismatch'):
            session.save()
        assert session._nested_dirty
        row = original[0]
        session.store.db.execute("UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace='aux.lazy.nested.list_pages' AND typed_key=? AND valid_from=?", (*row[6:], row[0], row[3]))
        session.store.db.commit()
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        assert not session._nested_dirty
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.economy.property[1].provenance[-1] == 10


def test_eager_only_history_missing_occurrence_fails_closed(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim.persistence_adapters import WorldCodec, SCHEMA
    from ate_sim.persistence_lazy_store import LazyRecordStore
    path = converted(tmp_path, 5, eager_alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.economy.property[1].provenance = [9]
        session.save()
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA, expected_rules_id=RULES) as store:
        store.db.execute("DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace='world.divinity.gods' AND occurrence_path=?", (store.codec.encode((("field", "manifestations"),)),))
        store.db.commit()
    with pytest.raises(StoreIntegrityError, match='eager nested reference lacks matching incarnation label'):
        open_lazy_world_session(path, rules_id=RULES)


@pytest.mark.parametrize('first', ['wallet', 'property'])
def test_shared_property_record_routes_header_and_child_edits_from_either_owner(tmp_path, first):
    path = converted(tmp_path, 5, record_alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        prop = session.wallets[11]['property'] if first == 'wallet' else session.world.economy.property[1]
        prop.owner_id = 9
        prop.provenance.append(10)
        assert prop is session.world.economy.property[1]
        assert prop is session.wallets[11]['property']
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.wallets[11]['property'] is session.world.economy.property[1]
        assert session.wallets[11]['property'].owner_id == 9
        assert session.wallets[11]['property'].provenance[-1] == 10
