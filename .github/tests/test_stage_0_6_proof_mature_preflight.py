"""Real SQLite metadata inventory; transport authority remains independently tested."""
import copy
import importlib
import sqlite3
import json
import shutil
from types import SimpleNamespace
from pathlib import Path
import pytest
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture
from simulation.tests.test_stage_0_5_performance_runner import source_authority


def mod():return importlib.import_module('simulation.stage_0_6_proof_mature_preflight')


@pytest.fixture
def source(tmp_path):
    path=fixture(tmp_path,16)
    return path,source_authority(path)


def test_real_inventory_aggregates_lengths_without_decoding_or_changes(source,tmp_path,monkeypatch):
    from ate_sim.incremental_store import TypedCodec
    path,authority=source
    db=sqlite3.connect(path)
    try:expected=db.execute('SELECT count(*),sum(length(payload)),max(length(payload)) FROM records').fetchone()
    finally:db.close()
    def forbidden(*a,**k):raise AssertionError('preflight decoded World data')
    monkeypatch.setattr(TypedCodec,'decode',forbidden)
    result=mod().inspect_database(path,authority,output=tmp_path/'inventory.json')
    assert result['status']=='complete' and result['source_unchanged']
    assert result['acceptance']=='not-run'
    rows=result['tables']['records']['namespaces']
    assert sum(r['rows'] for r in rows)==expected[0]
    assert sum(r['payload_bytes'] for r in rows)==expected[1]
    assert max(r['max_payload_bytes'] for r in rows)==expected[2]
    assert result['metadata']['store_uuid']==authority['pin']['store_identity']
    assert result['head_generation']==authority['pin']['captured_head']
    assert result['tables']['lazy_record_versions']['rows']>=result['tables']['lazy_record_versions']['visible_rows']
    assert mod().r.file_hash(path)==authority['database']['sha256']


@pytest.mark.parametrize('field',['hash','size','pin','rules','generation','seed'])
def test_wrong_source_binding_cannot_complete_inventory(source,tmp_path,field):
    path,authority=source;bad=copy.deepcopy(authority)
    if field=='hash':bad['database']['sha256']='0'*64
    elif field=='size':bad['database']['bytes']+=1
    elif field=='pin':bad['pin']['store_identity']='other'
    elif field=='rules':bad['rules_id']='other'
    elif field=='generation':bad['pin']['captured_head']+=1
    else:bad['world']['seed']+=1
    output=tmp_path/'failure.json'
    with pytest.raises(ValueError):mod().inspect_database(path,bad,output=output)
    result=mod().r.load_receipt(output)
    assert result['status']=='error' and result['acceptance']=='not-run'


@pytest.mark.parametrize('kind',['symlink','journal','wal','shm'])
def test_live_or_indirect_source_is_rejected(source,tmp_path,kind):
    path,authority=source
    if kind=='symlink':
        alias=tmp_path/'alias.sqlite';alias.symlink_to(path);path=alias
    else:Path(str(path)+'-'+kind).write_bytes(b'not standalone')
    with pytest.raises(ValueError):mod().inspect_database(path,authority)


def test_namespace_budget_fails_closed(source,tmp_path,monkeypatch):
    path,authority=source;monkeypatch.setattr(mod(),'MAX_NAMESPACES',1)
    with pytest.raises(ValueError,match='namespace budget'):
        mod().inspect_database(path,authority,output=tmp_path/'budget.json')
    assert mod().r.load_receipt(tmp_path/'budget.json')['status']=='error'


def test_expired_inventory_is_not_complete(source,tmp_path):
    path,authority=source
    with pytest.raises(TimeoutError):
        mod().inspect_database(path,authority,budget_seconds=1e-9,output=tmp_path/'timeout.json')
    result=mod().r.load_receipt(tmp_path/'timeout.json')
    assert result['status']=='timeout' and result['censored'] and result['acceptance']=='not-run'


def test_output_cannot_replace_source_or_existing_evidence(source,tmp_path):
    path,authority=source;digest=mod().r.file_hash(path)
    with pytest.raises(ValueError):mod().inspect_database(path,authority,output=path)
    output=tmp_path/'existing.json';output.write_text('preserved')
    with pytest.raises(FileExistsError):mod().inspect_database(path,authority,output=output)
    assert output.read_text()=='preserved' and mod().r.file_hash(path)==digest


def test_missing_table_cannot_be_reported_complete(source,tmp_path):
    path,authority=source;db=sqlite3.connect(path);db.execute('DROP TABLE segments');db.commit();db.close()
    authority['database']=dict(bytes=path.stat().st_size,sha256=mod().r.file_hash(path))
    with pytest.raises(ValueError,match='missing inventory tables'):
        mod().inspect_database(path,authority,output=tmp_path/'missing.json')


def config():
    value=json.loads(Path('simulation/stage_0_6_benchmark_launch.json').read_text())
    value.update(schema='ate-stage06-proof-preflight-request/1',operation='inventory-only',
        green_commit='b9196f9885fed0323c473bcc148f6b9dad9da9eb',
        runtime_tree='6ca23be5208e8c198081c73b40806b42a4eb8626',fingerprints={},inventory_budget_seconds=900)
    return value


@pytest.mark.parametrize('bad',['source','database','disk','rerun'])
def test_launch_rejects_before_transport(tmp_path,monkeypatch,bad):
    m=mod();c=config();called=[];monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(m,'prepare_retained',lambda *a,**k:called.append(True),raising=False)
    if bad!='source':monkeypatch.setattr(m,'check_source',lambda *a:dict(head='a'*40),raising=False)
    if bad=='database':c['database']['sha256']='0'*64
    if bad=='disk':monkeypatch.setattr(m.shutil,'disk_usage',lambda p:SimpleNamespace(free=1))
    if bad=='rerun':monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2')
    with pytest.raises(ValueError):m.launch(tmp_path,c,expected_sha='a'*40)
    assert not called


def test_launch_reuses_transport_and_actual_readonly_inventory(source,tmp_path,monkeypatch):
    from simulation import construction_mature_continuation_stages as stages
    path,authority=source;m=mod();c=config();root=tmp_path/'job';root.mkdir()
    c.update(database=dict(name='candidate.sqlite',**authority['database']),world=authority['world'],
        pin={k:authority['pin'][k] for k in ('store_identity','captured_head')})
    original=json.loads(Path('simulation/stage_0_5_save1002_preflight.json').read_text())
    original.update(candidate_database=c['database'],expected_previous_year=c['world']['year'],
        expected_previous_generation=c['pin']['captured_head'])
    legacy=tmp_path/'original.json';legacy.write_text(json.dumps(original))
    monkeypatch.setattr(stages,'mature_authority',lambda:SimpleNamespace(
        source_config=dict(seed=c['world']['seed']),store_identity=c['pin']['store_identity']))
    monkeypatch.setattr(m,'ORIGINAL_LAUNCH',legacy,raising=False)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(m,'check_source',lambda *a:dict(head='a'*40),raising=False)
    monkeypatch.setattr(m.shutil,'disk_usage',lambda p:SimpleNamespace(free=100*1024**3))
    calls=[]
    def transport(destination,*args):
        calls.append(args);(destination/'source').mkdir();shutil.copyfile(path,destination/'source/candidate.sqlite')
        return authority,{'transport':'isolated authenticated seam'}
    monkeypatch.setattr(m,'prepare_retained',transport,raising=False)
    result=m.launch(root,c,expected_sha='a'*40)
    assert len(calls)==1 and result['status']=='complete' and result['acceptance']=='not-run'
    assert m.r.load_receipt(root/'evidence/source-authority.json')==authority
    assert result['execution']['head']=='a'*40


def test_command_timeout_does_not_fabricate_inventory(tmp_path):
    row=mod().record_exit(tmp_path,124)
    assert row['status']=='timeout' and row['censored'] and row['acceptance']=='not-run'
    assert not (tmp_path/'evidence/result.json').exists()


def test_successful_command_requires_complete_inventory(tmp_path):
    with pytest.raises(ValueError):mod().record_exit(tmp_path,0)


def test_sql_timeout_is_censored_and_closes_its_connection(source,tmp_path,monkeypatch):
    path,authority=source;m=mod();original=sqlite3.connect;clock=m.time.monotonic;armed=[];handles=[]
    class Observed(sqlite3.Connection):
        def execute(self,sql,*args):
            if 'FROM main.records GROUP BY' in sql:armed.append(True)
            return super().execute(sql,*args)
        def set_progress_handler(self,callback,n):
            # Increase observation frequency on the same real SQL statement.
            return super().set_progress_handler(callback,1)
    def connect(*a,**k):
        k['factory']=Observed;db=original(*a,**k);handles.append(db);return db
    monkeypatch.setattr(m.sqlite3,'connect',connect)
    monkeypatch.setattr(m,'time',SimpleNamespace(monotonic=lambda:clock()+(10000 if armed else 0)))
    with pytest.raises(TimeoutError,match='SQL budget'):
        m.inspect_database(path,authority,output=tmp_path/'sql-timeout.json')
    result=m.r.load_receipt(tmp_path/'sql-timeout.json')
    assert result['status']=='timeout' and result['censored'] and 'records' not in result['tables']
    with pytest.raises(sqlite3.ProgrammingError,match='closed'):handles[0].execute('SELECT 1')


@pytest.mark.parametrize('budget',[0,True,901])
def test_bad_inventory_budget_rejects_before_transport(tmp_path,monkeypatch,budget):
    m=mod();c=config();c['inventory_budget_seconds']=budget;calls=[]
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(m,'check_source',lambda *a:dict(head='a'*40))
    monkeypatch.setattr(m.shutil,'disk_usage',lambda p:SimpleNamespace(free=100*1024**3))
    monkeypatch.setattr(m,'prepare_retained',lambda *a:calls.append(True))
    with pytest.raises(ValueError,match='budget'):m.launch(tmp_path,c,expected_sha='a'*40)
    assert not calls


@pytest.mark.parametrize('bad',['seed','year','store','head','missing_seed','missing_head',
    'missing_world','missing_pin','extra_world','year_type','head_type'])
def test_world_pin_request_rejects_before_transport(tmp_path,monkeypatch,bad):
    m=mod();c=config();calls=[]
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(m,'check_source',lambda *a:dict(head='a'*40))
    monkeypatch.setattr(m.shutil,'disk_usage',lambda p:SimpleNamespace(free=100*1024**3))
    def transport(*a):calls.append(True);raise AssertionError('large transport reached')
    monkeypatch.setattr(m,'prepare_retained',transport)
    if bad=='seed':c['world']['seed']+=1
    elif bad=='year':c['world']['year']+=1
    elif bad=='store':c['pin']['store_identity']='other'
    elif bad=='head':c['pin']['captured_head']+=1
    elif bad=='missing_seed':del c['world']['seed']
    elif bad=='missing_head':del c['pin']['captured_head']
    elif bad=='missing_world':del c['world']
    elif bad=='missing_pin':del c['pin']
    elif bad=='extra_world':c['world']['unexpected']=1
    elif bad=='year_type':c['world']['year']=float(c['world']['year'])
    else:c['pin']['captured_head']=float(c['pin']['captured_head'])
    with pytest.raises(ValueError,match='world/pin'):m.launch(tmp_path,c,expected_sha='a'*40)
    assert not calls
