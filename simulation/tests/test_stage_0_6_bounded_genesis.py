"""Construction inventories must stream real checked rows, including failures."""
from contextlib import nullcontext
import hashlib
import pytest

from ate_sim import persistence_lazy_store as lazy
from ate_sim import persistence_proof_world_copy as copy_api
from ate_sim.persistence_sqlite_guard import _NativeGuardCursor
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, opened
from simulation.tests.test_stage_0_5_final_complete_format import upgraded


def prohibit_bulk_rows(monkeypatch):
    execute, fetchall = _NativeGuardCursor.execute, _NativeGuardCursor.fetchall
    seen = []
    def track(self, sql, *args, **kwargs):
        self._construction_test_sql = sql.lower()
        return execute(self, sql, *args, **kwargs)
    def check(self):
        sql = getattr(self, '_construction_test_sql', '')
        if sql.startswith('select ') and any('from '+t in sql for t in (
                'lazy_record_versions', 'lazy_order_versions', 'lazy_query_versions',
                'lazy_identity_occurrence_versions', 'records', 'segments')):
            point = any('where namespace=? and '+key+'=?' in sql for key in ('typed_key', 'record_key'))
            point |= 'where owner_namespace=? and owner_key=? and occurrence_path=?' in sql
            if not point and 'limit ' not in sql and 'count(' not in sql and 'distinct namespace' not in sql:
                seen.append(sql)
                raise AssertionError('unbounded construction fetchall: '+sql)
        return fetchall(self)
    monkeypatch.setattr(_NativeGuardCursor, 'execute', track)
    monkeypatch.setattr(_NativeGuardCursor, 'fetchall', check)
    return seen


def test_guard_negative_control(monkeypatch, tmp_path):
    source = upgraded(tmp_path)
    prohibit_bulk_rows(monkeypatch)
    with opened(source) as store, pytest.raises(AssertionError, match='unbounded'):
        store.db.execute('SELECT payload FROM lazy_record_versions').fetchall()


def test_genesis_streams_real_complete_world_and_preserves_source(monkeypatch, tmp_path):
    source = upgraded(tmp_path)
    before = hashlib.sha256(source.read_bytes()).digest()
    seen = prohibit_bulk_rows(monkeypatch)
    dest = tmp_path/'proof.sqlite'
    result = copy_api.copy_world_with_proofs(source, dest, rules_id=RULES, rank_proofs=True)
    assert not seen
    assert hashlib.sha256(source.read_bytes()).digest() == before
    assert result.manifest.generation == 0 and len(result.manifest.roots) == 7
    with opened(dest) as store:
        with lazy._bounded_conversion_audits():
            store.verify_all()
    assert not tuple(tmp_path.glob('.ate-proof-genesis-*'))


@pytest.mark.parametrize('phase', ['after_source_capture', 'before_publish'])
def test_copy_cancellation_discards_private_file(monkeypatch, tmp_path, phase):
    source = upgraded(tmp_path)
    before = hashlib.sha256(source.read_bytes()).digest()
    class Cancelled(BaseException): pass
    def fail(at):
        if at == phase: raise Cancelled('cancel construction')
    monkeypatch.setattr(lazy.LazyRecordStore, '_copy_phase_hook', staticmethod(fail))
    with pytest.raises(Cancelled):
        lazy.LazyRecordStore.copy_current_head(source, tmp_path/'failed.sqlite',
            codec=lazy_codec(), expected_simulation_schema='ate-world-p2a/1', expected_rules_id=RULES)
    assert not (tmp_path/'failed.sqlite').exists()
    assert not tuple(tmp_path.glob('.ate-current-copy-*'))
    assert hashlib.sha256(source.read_bytes()).digest() == before


def lazy_codec():
    from ate_sim.persistence_adapters import WorldCodec
    return WorldCodec(identity_links_recorded=True)


def archive(path, count=130):
    from ate_sim.incremental_store import TypedCodec, Membership, RecordChange, NewSegment
    store = lazy.LazyRecordStore.create(path, codec=TypedCodec(), simulation_schema='test', rules_id='test')
    pin = store.capture_pin()
    for generation in (1, 2):
        pin = store.commit(pin, commit_token=str(generation),
            version_changes=(lazy.VersionChange('people', key, 'x'*1024,
                memberships=(Membership('bucket', 'x', key),)) for key in range(count)),
            identity_changes=(lazy.IdentityOccurrenceChange('people', key, (), key+1) for key in range(count)),
            next_incarnation_id=count+1,
            changes=(RecordChange('ordinary', 0, ('body', generation)),),
            new_segments=(NewSegment('events', generation-1, (generation,), generation, generation, 1),),
            metadata=dict(simulation_position=generation, seed=7, next_ids={'person':count+1},
                          namespaces=('people','ordinary','events')),
            preparation_budget=(64,65536)).pin
    store.release_pin(pin)
    return store


def test_bounded_and_default_full_audits_agree_and_scope_restores(tmp_path):
    with archive(tmp_path/'archive.sqlite') as store:
        expected = store.verify_all()
        assert not lazy._CONVERSION_AUDITS.get()
        with lazy._bounded_conversion_audits():
            assert store.verify_all() == expected
            with lazy._bounded_conversion_audits():
                assert lazy._CONVERSION_AUDITS.get()
            assert lazy._CONVERSION_AUDITS.get()
        assert not lazy._CONVERSION_AUDITS.get()


@pytest.mark.parametrize('damage', ['record','order','query','missing-query','extra-query',
                                   'duplicate-ordinal','identity','allocator'])
def test_bounded_audit_rejects_same_corrupt_authority(tmp_path, damage):
    from ate_sim.incremental_store import StoreIntegrityError
    with archive(tmp_path/'archive.sqlite', 3) as store:
        db = store.db
        if damage == 'record':
            db.execute("UPDATE lazy_record_versions SET payload=X'00' WHERE valid_to IS NULL")
        elif damage == 'order':
            db.execute("UPDATE lazy_order_versions SET row_checksum='bad' WHERE valid_to IS NULL")
        elif damage == 'query':
            db.execute("UPDATE lazy_query_versions SET row_checksum='bad' WHERE valid_to IS NULL")
        elif damage == 'missing-query':
            db.execute('DELETE FROM lazy_query_versions WHERE valid_to IS NULL AND record_key=?', (store.codec.encode(0),))
        elif damage == 'extra-query':
            value, key = store.codec.encode('extra'), store.codec.encode(0)
            db.execute('INSERT INTO lazy_query_versions VALUES (?,?,?,?,?,?,?,?)',
                ('people','bucket',value,key,0,2,None,lazy._query_checksum('people','bucket',value,key,0,2,None)))
        elif damage == 'duplicate-ordinal':
            key = store.codec.encode(1)
            db.execute('UPDATE lazy_order_versions SET ordinal=0,row_checksum=? WHERE typed_key=? AND valid_to IS NULL',
                (lazy._order_checksum('people',key,0,1,None),key))
        elif damage == 'identity':
            db.execute("UPDATE lazy_identity_occurrence_versions SET row_checksum='bad' WHERE valid_to IS NULL")
        else:
            db.execute('UPDATE lazy_identity_state SET next_incarnation_id=1,row_checksum=? WHERE valid_to IS NULL',
                (lazy._identity_state_checksum(1,1,None),))
        db.commit()
        for bounded in (False, True):
            with lazy._bounded_conversion_audits() if bounded else nullcontext():
                with pytest.raises(StoreIntegrityError):
                    store.verify_all()


def test_rebase_crosses_multiple_locator_batches_without_losing_rows(tmp_path, monkeypatch):
    with archive(tmp_path/'archive.sqlite') as store:
        before = store.verify_all()
        prohibit_bulk_rows(monkeypatch)
        with lazy._bounded_conversion_audits():
            copy_api._rebase_private_snapshot(store)
            after = store.verify_all()
        assert store.generation == 0
        assert after['lazy_records'] == before['lazy_records']
        pin = store.capture_pin()
        assert len(tuple(store.iter_keys(pin,'people'))) == 130
        assert sorted(key for key,_ordinal in store.iter_query_memberships(pin,'people','bucket','x')) == list(range(130))
        assert store.read_identity_state(pin) == 131
        assert [row[0] for row in store.db.execute('SELECT DISTINCT valid_from FROM lazy_record_versions')] == [0]


def test_disk_lookup_and_roster_graph_reject_corruption_and_cycles(tmp_path):
    from ate_sim.persistence_conversion_workspace import ConversionWorkspace, DiskLookup
    from ate_sim.incremental_store import StoreError, TypedCodec
    from ate_sim.persistence_catalog_copy import _check_backing_graph, _check_reference_targets
    from ate_sim.persistence_history_dependencies import NAMESPACE, dependency_value
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, HistoryReference
    codec = TypedCodec()
    with ConversionWorkspace(codec,directory=tmp_path) as workspace:
        lookup = DiskLookup(workspace, ((1,'list'),(2,'map')))
        assert lookup.get(1) == 'list' and lookup.get(3) is None and 2 in lookup
        workspace.db.execute("UPDATE conversion_lookup SET value=? WHERE stream=? AND key=?",
                             (codec.encode('set'),lookup.stream,codec.encode(1)))
        with pytest.raises(StoreError, match='checksum'): lookup.get(1)
        with pytest.raises(StoreError, match='checksum'): lookup.validate()
    # Real WorldCodec is required for typed references; the physical adapter
    # validates each edge before the existing disk Kahn traversal checks cycles.
    codec = lazy_codec()
    deps = (lazy.VersionChange(NAMESPACE,1,dependency_value('list')),)
    with ConversionWorkspace(codec,directory=tmp_path) as workspace:
        with pytest.raises(StoreError, match='wrong-kind'):
            _check_reference_targets((HistoryReference('map',1),),deps,workspace=workspace)
        changes = (lazy.VersionChange(PAGE_NAMESPACE,(1,0),(HistoryReference('list',1),)),)
        with pytest.raises(StoreError, match='cyclic'):
            _check_backing_graph(codec,changes,deps,workspace=workspace)


def test_mid_rebase_cancellation_rolls_back_every_table(tmp_path,monkeypatch):
    with archive(tmp_path/'archive.sqlite') as store:
        before=store.verify_all()
        digest=hashlib.sha256(store.path.read_bytes()).digest()
        execute=_NativeGuardCursor.execute
        class Cancelled(BaseException): pass
        seen=0
        def fail(self,sql,*args,**kwargs):
            nonlocal seen
            if sql.startswith('UPDATE lazy_record_versions SET payload='):
                seen+=1
                if seen==5:raise Cancelled('mid-rebase')
            return execute(self,sql,*args,**kwargs)
        with monkeypatch.context() as fault:
            fault.setattr(_NativeGuardCursor,'execute',fail)
            with lazy._bounded_conversion_audits(),pytest.raises(Cancelled,match='mid-rebase'):
                copy_api._rebase_private_snapshot(store)
        assert seen==5 and not store.db.in_transaction
        assert store.verify_all()==before and hashlib.sha256(store.path.read_bytes()).digest()==digest


def test_rebase_preserves_multiple_query_positions_for_one_owner(tmp_path):
    from ate_sim.incremental_store import Membership
    with archive(tmp_path/'archive.sqlite',1) as store:
        pin=store.capture_pin()
        pin=store.commit(pin,commit_token='two-positions',
            version_changes=(lazy.VersionChange('people',0,'two positions',
                memberships=(Membership('bucket','x',5),Membership('bucket','x',9))),),
            changes=(),new_segments=(),metadata=store.head_metadata()).pin
        assert store.query_memberships(pin,'people','bucket','x') == ((0,5),(0,9))
        store.release_pin(pin)
        with lazy._bounded_conversion_audits():
            copy_api._rebase_private_snapshot(store)
            store.verify_all()
        pin=store.capture_pin()
        assert store.query_memberships(pin,'people','bucket','x') == ((0,5),(0,9))


def test_frozen_map_certification_streams_checked_entries(tmp_path,monkeypatch):
    from simulation.tests.test_stage_0_5_final_frozen_histories import opened, commit
    from ate_sim.persistence_lazy_nested_history import LazyFrozenHistoryMap
    from ate_sim.persistence_frozen_snapshots import verify_frozen_certification
    from ate_sim.incremental_store import StoreIntegrityError
    with opened(tmp_path/'frozen.sqlite') as store:
        proxy=LazyFrozenHistoryMap(store,store.capture_pin(),1,
            initial_values={k:k+1 for k in range(1000)},recursive=True)
        pin=commit(store,proxy);proxy.accept_save(pin)
        verify_frozen_certification(proxy)
        monkeypatch.setattr(proxy,'_ordered_entries',lambda:pytest.fail('frozen certification retained all entries'))
        with lazy._bounded_conversion_audits():
            verify_frozen_certification(proxy)
            assert list(proxy)==list(range(1000))
            proxy._deep_immutable=False
            with pytest.raises(StoreIntegrityError,match='certification'):
                verify_frozen_certification(proxy)


def test_shared_spills_avoid_one_file_per_tiny_history(tmp_path,monkeypatch):
    from simulation.tests.test_stage_0_5_final_frozen_histories import opened, commit
    from ate_sim.persistence_lazy_nested_history import LazyFrozenHistoryMap
    from ate_sim.persistence_frozen_snapshots import verify_frozen_certification
    from ate_sim.persistence_conversion_audit import construction_spills
    from ate_sim.persistence_conversion_workspace import ConversionWorkspace
    import tempfile
    with opened(tmp_path/'frozen.sqlite') as store:
        proxy=LazyFrozenHistoryMap(store,store.capture_pin(),1,initial_values={},recursive=True)
        pin=commit(store,proxy);proxy.accept_save(pin)
        with ConversionWorkspace(store.codec,directory=tmp_path) as spill:
            monkeypatch.setattr(tempfile,'mkstemp',lambda *a,**k:pytest.fail('tiny history allocated another file'))
            with construction_spills(spill),lazy._bounded_conversion_audits():
                for _ in range(100):verify_frozen_certification(proxy)
            assert spill.db.execute('SELECT count(*) FROM membership_order').fetchone()==(0,)


def test_audited_open_outside_construction_keeps_original_audits(tmp_path,monkeypatch):
    from ate_sim import persistence_conversion_audit as bounded_audit
    from ate_sim import persistence_conversion_sequence_audit as sequence_audit
    from ate_sim import persistence_catalog_copy as catalog_copy
    from ate_sim.persistence_lazy_identity_retired import RetiredIdentityRanges
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
    source=upgraded(tmp_path);dest=tmp_path/'proof.sqlite'
    result=copy_api.copy_world_with_proofs(source,dest,rules_id=RULES,rank_proofs=True)
    def forbidden(*a,**k):pytest.fail('ordinary audited opener selected a conversion audit')
    monkeypatch.setattr(bounded_audit,'verify_lazy_generation',forbidden)
    monkeypatch.setattr(sequence_audit,'scrub',forbidden)
    original_types=catalog_copy.verify_type_witnesses
    original_retired=RetiredIdentityRanges.scrub
    def types(*a,**k):
        assert k.get('workspace') is None
        return original_types(*a,**k)
    def retired(*a,**k):
        assert k.get('workspace') is None
        return original_retired(*a,**k)
    monkeypatch.setattr(catalog_copy,'verify_type_witnesses',types)
    monkeypatch.setattr(RetiredIdentityRanges,'scrub',retired)
    with open_audited_proof_world_session(dest,rules_id=RULES,expected_commitment=result.commitment) as session:
        assert session.world.year==0


def test_world_audit_failure_keeps_primary_error_and_discards_output(tmp_path, monkeypatch):
    source = upgraded(tmp_path)
    before = hashlib.sha256(source.read_bytes()).digest()
    class Cancelled(BaseException): pass
    execute, fetchall = _NativeGuardCursor.execute, _NativeGuardCursor.fetchall
    def track(self, sql, *args, **kwargs):
        self._audit_fault_sql = sql
        return execute(self,sql,*args,**kwargs)
    def fail(self):
        if getattr(self,'_audit_fault_sql','').startswith('SELECT incarnation_id FROM lazy_identity_occurrence_versions WHERE owner_namespace='):
            raise Cancelled('primary World audit cancellation')
        return fetchall(self)
    monkeypatch.setattr(_NativeGuardCursor,'execute',track)
    monkeypatch.setattr(_NativeGuardCursor,'fetchall',fail)
    dest = tmp_path/'cancelled.sqlite'
    with pytest.raises(Cancelled,match='primary World audit cancellation'):
        copy_api.copy_world_with_proofs(source,dest,rules_id=RULES,rank_proofs=True)
    assert not dest.exists() and hashlib.sha256(source.read_bytes()).digest() == before
    assert not tuple(tmp_path.glob('.ate-proof-genesis-*'))
