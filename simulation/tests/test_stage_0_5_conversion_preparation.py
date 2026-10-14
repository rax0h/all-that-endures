"""Opt-in disk preparation retains the existing commit/recovery authority."""
from dataclasses import replace
import pytest
from simulation.ate_sim.incremental_store import Membership, RecordChange, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata


def inventory(store):
    return {table: tuple(store.db.execute('SELECT * FROM ' + table + ' ORDER BY 1,2')) for table in
        ('lazy_record_versions', 'lazy_order_versions', 'lazy_namespace_state', 'lazy_query_versions',
         'lazy_identity_occurrence_versions', 'lazy_identity_state', 'records', 'query_membership')}


def save(store, pin, token, versions=(), ordinary=(), placements=(), budget=None, position=1):
    kwargs = {} if budget is None else {'preparation_budget': budget}
    return store.commit(pin, commit_token=token, version_changes=iter(versions), changes=iter(ordinary),
        identity_changes=iter(placements), next_incarnation_id=10, new_segments=(),
        metadata=metadata(position, ('people', 'other', 'ordinary')), **kwargs)


def test_prepared_stream_matches_ordinary_commit_delete_reinsert_and_memberships(tmp_path):
    with make_store(tmp_path/'normal.sqlite') as normal, make_store(tmp_path/'spill.sqlite') as spill:
        pins = [s.capture_pin() for s in (normal, spill)]
        for position, versions, ordinary, placements in (
            (1, [VersionChange('people', 1, [1], memberships=(Membership('a', 1, 2),)),
                 VersionChange('other', 1, 'peer'), VersionChange('people', 2, [2])],
                 [RecordChange('ordinary', 1, {'v':1}, memberships=(Membership('q', 2, 3),))],
                 [IdentityOccurrenceChange('people', 1, (), 1)]),
            (2, [VersionChange('people', 1, delete=True)], [RecordChange('ordinary',1,delete=True)],
                 [IdentityOccurrenceChange('people',1,(),delete=True)]),
            (3, [VersionChange('people', 1, [3]), VersionChange('people', 2, [4], reinsertion=True)], [RecordChange('ordinary',1,{'v':3})],
                 [IdentityOccurrenceChange('people',1,(),2)])):
            for i, store in enumerate((normal, spill)):
                result = save(store,pins[i],str(position),versions,ordinary,placements,
                              budget=(4,1024) if i else None,position=position)
                assert result.outcome == 'committed'
                pins[i] = result.pin
            assert inventory(normal) == inventory(spill)
        for i,store in enumerate((normal,spill)):
            result = save(store,pins[i],'noop',budget=(4,1024) if i else None,position=3)
            assert result.outcome == 'not_committed'
        assert not list(tmp_path.glob('conversion-*'))


@pytest.mark.parametrize('kind', ['version', 'identity', 'ordinary', 'membership'])
def test_invalid_preparation_rejects_before_attempt_and_cleans_scratch(tmp_path,kind):
    with make_store(tmp_path/'spill.sqlite') as store:
        pin=store.capture_pin();before=inventory(store)
        v=VersionChange('people',1,[1]);o=RecordChange('ordinary',1,[1]);p=IdentityOccurrenceChange('people',1,(),1)
        versions=[v,v] if kind=='version' else [replace(v,memberships=(Membership('a',1,-1),))] if kind=='membership' else ()
        with pytest.raises(ValueError):
            save(store,pin,'invalid',versions,[o,o] if kind=='ordinary' else (),[p,p] if kind=='identity' else (),budget=(4,1024))
        assert inventory(store)==before
        assert not tuple(store.db.execute('SELECT * FROM pin_attempts'))
        assert not list(tmp_path.glob('conversion-*'))


@pytest.mark.parametrize('phase', ['before_transaction','during_version_writes','during_identity_writes','before_commit','after_commit'])
def test_preparation_cleanup_and_existing_recovery_outcome(tmp_path,phase):
    with make_store(tmp_path/'spill.sqlite') as store:
        pin=store.capture_pin()
        def fault(at):
            if at==phase:raise OSError('injected')
        store._phase_hook=fault
        with pytest.raises(OSError,match='injected'):
            save(store,pin,'fault',[VersionChange('people',1,[1])],placements=[IdentityOccurrenceChange('people',1,(),1)],budget=(4,1024))
        assert not list(tmp_path.glob('conversion-*'))
        store._phase_hook=lambda at:None
        resolved=store.resolve_commit(pin,'fault')
        assert resolved.outcome==('committed' if phase=='after_commit' else 'not_committed')


def test_mutation_after_preparation_cannot_change_committed_values(tmp_path):
    with make_store(tmp_path/'spill.sqlite') as store:
        pin=store.capture_pin();value=[1]
        def mutate(at):
            if at=='before_transaction':value.append(99)
        store._phase_hook=mutate
        result=save(store,pin,'snapshot',[VersionChange('people',1,value)],budget=(4,1024))
        assert value==[1,99]
        assert store.read_version(result.pin,'people',1,expected_record_schema=1).value==[1]
        assert not list(tmp_path.glob('conversion-*'))


def test_stale_prepared_save_closes_scratch_without_new_attempt(tmp_path):
    with make_store(tmp_path/'spill.sqlite') as store:
        stale=store.capture_pin();pin=store.capture_pin()
        result=save(store,pin,'first',[VersionChange('people',1,[1])],budget=(4,1024))
        result=save(store,stale,'stale',[VersionChange('people',2,[2])],budget=(4,1024))
        assert result.outcome=='conflict'
        assert not list(tmp_path.glob('conversion-*'))


def test_staging_corruption_rejects_before_registering_attempt(tmp_path,monkeypatch):
    from simulation.ate_sim.persistence_conversion_workspace import ConversionWorkspace
    original=ConversionWorkspace.stage
    def corrupt(workspace,*args,**kwargs):
        rows=original(workspace,*args,**kwargs)
        if len(rows):
            workspace.db.execute("UPDATE replay_rows SET payload=x'00' WHERE stream=? AND ordinal=0",(rows.stream,))
        return rows
    monkeypatch.setattr(ConversionWorkspace,'stage',corrupt)
    with make_store(tmp_path/'spill.sqlite') as store:
        pin=store.capture_pin();before=inventory(store)
        with pytest.raises(StoreIntegrityError):
            save(store,pin,'corrupt',[VersionChange('people',1,[1])],budget=(4,1024))
        assert inventory(store)==before
        assert not tuple(store.db.execute('SELECT * FROM pin_attempts'))
        assert not list(tmp_path.glob('conversion-*'))


def test_disk_write_failure_during_preflight_preserves_source_and_cleans_scratch(tmp_path,monkeypatch):
    import sqlite3
    from simulation.ate_sim.persistence_conversion_workspace import ConversionWorkspace
    original=ConversionWorkspace.__init__
    class FullDisk:
        def __init__(self,db):self.db=db;self.writes=0
        def __getattr__(self,name):return getattr(self.db,name)
        def execute(self,sql,*args):
            if sql.startswith('INSERT INTO replay_rows'):
                self.writes+=1
                if self.writes==2:raise sqlite3.OperationalError('database or disk is full')
            return self.db.execute(sql,*args)
    def init(workspace,*args,**kwargs):
        original(workspace,*args,**kwargs);workspace.db=FullDisk(workspace.db)
    monkeypatch.setattr(ConversionWorkspace,'__init__',init)
    with make_store(tmp_path/'spill.sqlite') as store:
        pin=store.capture_pin();before=inventory(store)
        with pytest.raises(sqlite3.OperationalError,match='disk is full'):
            save(store,pin,'full',[VersionChange('people',i,[i]) for i in range(8)],budget=(4,1024))
        assert inventory(store)==before
        assert not tuple(store.db.execute('SELECT * FROM pin_attempts'))
        assert not list(tmp_path.glob('conversion-*'))
