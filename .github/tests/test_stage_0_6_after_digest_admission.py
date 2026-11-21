"""An exact historical after-digest may cross only the new proofs boundary."""
import copy
import importlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile

import pytest
from simulation import continuation_receipts as r
from simulation import stage_0_6_genesis_checkpoint as c

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/performance/stage-0-6-current'
CONTRACT='simulation/stage_0_6_after_digest_admission.json'


def old_after(mode='smoke'):
    aid=14252280082 if mode=='smoke' else 14267625292
    with zipfile.ZipFile(BASE/'after-digest-admission/inputs.zip') as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read(str(aid)+'.zip'))) as z:
            return json.loads(z.read('checkpoint.json'))


def successor(parent):
    ctx=copy.deepcopy(parent['context'])
    ctx.update(runtime_tree='5464caa49acc4c27f24c247b60ee639afd9d150d',critical_blobs={'candidate.py':'a'*40})
    return ctx


def marker(parent,ctx):
    return dict(schema='ate-after-digest-runtime-admission/1',parent_sha256=c.receipt_hash(parent),
        parent_database=copy.deepcopy(parent['database']),from_context_sha256=c.receipt_hash(parent['context']),
        to_context_sha256=c.receipt_hash(ctx),contract_sha256=c.file_hash(ROOT/CONTRACT))


def proved(parent,ctx,stamp):
    return c.record('proofs',ctx,{**parent['database'],'format':7,'sha256':'e'*64},
        dict(run_id=2,head_sha='d'*40,job='proofs',attempt=1),parent=parent,
        proof_commitment='f'*64,metrics={'proofs_admission':stamp})


def api():
    name='simulation.stage_0_6_after_digest_admission'
    assert importlib.util.find_spec(name) is not None,'exact retained after-digest admission is not implemented'
    return importlib.import_module(name)


def test_proofs_cut_preserves_both_original_contexts_and_parent_chain():
    parent=old_after();original=copy.deepcopy(parent);ctx=successor(parent)
    row=proved(parent,ctx,marker(parent,ctx))
    assert row['parent']['receipt']==original and parent==original
    assert row['parent']['receipt']['parent']['receipt']['metrics']['catalog_admission']
    saved=c.record('measure',ctx,{**row['database'],'generation':1,'year':2,'sha256':'b'*64},
        dict(run_id=2,head_sha='d'*40,job='measure',attempt=1),parent=row,proof_commitment='c'*64)
    assert c.validate(saved)['parent']['receipt']['parent']['receipt']==original


@pytest.mark.parametrize('field',['source','rules_id','rank_proofs','expected_saved_digest','execution_runtime'])
def test_proofs_cut_cannot_change_world_or_software_authority(field):
    parent=old_after();ctx=successor(parent)
    if field=='source':ctx[field]['sha256']='0'*64
    elif field=='rank_proofs':ctx[field]=False
    elif field=='execution_runtime':ctx[field]['signature']='0'*64
    else:ctx[field]='0'*64
    with pytest.raises(ValueError):proved(parent,ctx,marker(parent,ctx))


@pytest.mark.parametrize('field',['parent_sha256','parent_database','from_context_sha256','to_context_sha256','schema'])
def test_proofs_marker_rejects_rebinding(field):
    parent=old_after();ctx=successor(parent);stamp=marker(parent,ctx)
    if field=='parent_database':stamp[field]['sha256']='0'*64
    else:stamp[field]='0'*64
    with pytest.raises(ValueError):proved(parent,ctx,stamp)


def recorded_service(monkeypatch):
    from simulation import checkpoint_artifacts as github
    from simulation import stage_0_6_genesis_resume as m
    metas=[]
    with zipfile.ZipFile(BASE/'after-digest-admission/inputs.zip') as z:
        metas.extend(json.loads(z.read(mode+'-metadata.json')) for mode in ('smoke','mature'))
    for path,member in [('forensic-repair/smoke-43778758497-evidence.zip','hosted-metadata.json'),('rebase-locator-repair/evidence.zip','hosted/failed-run-metadata.json')]:
        with zipfile.ZipFile(BASE/path) as z:metas.append(json.loads(z.read(member)))
    artifacts={a['id']:a for meta in metas for a in meta['artifacts']['artifacts']}
    runs={meta['run']['id']:meta for meta in metas}
    def fetch(path):
        if path.startswith('/actions/artifacts/'):return artifacts[int(path.rsplit('/',1)[1])]
        if path.startswith('/actions/runs/'):return runs[int(path.rsplit('/',1)[1])]['run']
        raise AssertionError(path)
    def pages(path,key):
        assert key=='jobs' and path.endswith('/jobs?filter=all')
        return runs[int(path.split('/')[3])]['jobs']['jobs']
    monkeypatch.setattr(github,'_api',fetch);monkeypatch.setattr(github,'_pages',pages)
    return artifacts,runs


def execution(monkeypatch,parent):
    from simulation import stage_0_6_genesis_resume as m
    contract=json.loads((ROOT/CONTRACT).read_text());ctx=successor(parent)
    monkeypatch.setattr(m,'RUNTIME',contract['target_engine_tree'])
    monkeypatch.setattr(m,'GREEN_SHA',contract['target_green_commit'])
    monkeypatch.setattr(m,'fence',lambda root:(ctx['runtime_tree'],ctx['critical_blobs']))
    monkeypatch.setattr(m,'runtime_description',lambda:(ctx['execution_runtime'],{}))
    return ctx


def candidate_execution(monkeypatch,parent):
    from simulation import stage_0_6_genesis_resume as m
    ctx=successor(parent)
    ctx['runtime_tree']='6ce0a33711f4fb10b30e13d67df1eaaace9a2e35'
    monkeypatch.setattr(m,'RUNTIME',ctx['runtime_tree'])
    monkeypatch.setattr(m,'GREEN_SHA','7a2c84065ab03118256e9cf551f7de1b483db524')
    monkeypatch.setattr(m,'fence',lambda root:(ctx['runtime_tree'],ctx['critical_blobs']))
    monkeypatch.setattr(m,'runtime_description',lambda:(ctx['execution_runtime'],{}))
    return ctx


@pytest.mark.parametrize('mode',['smoke','mature'])
def test_successor_admission_preserves_exact_predecessors(monkeypatch,mode):
    parent=old_after(mode);original=copy.deepcopy(parent)
    ctx=candidate_execution(monkeypatch,parent)
    artifacts,_=recorded_service(monkeypatch)
    proof=api();stamp=proof.attest(ROOT,parent,ctx)
    assert stamp['contract_sha256']==c.file_hash(ROOT/'simulation/stage_0_6_after_digest_successor.json')
    row=proved(parent,ctx,stamp)
    assert proof.validate_chain(ROOT,row)['receipt_sha256']==c.receipt_hash(original)
    assert parent==original
    for aid in (14252280082,14252085073,14188030345,14187731783) if mode=='smoke' else (
        14267625292,14261110486,14197005279,14195829058):
        with monkeypatch.context() as change:
            change.setitem(artifacts[aid],'expired',True)
            with pytest.raises(ValueError):proof.validate_chain(ROOT,row)
    with pytest.raises(ValueError,match='attestation'):
        proof.validate_chain(ROOT,proved(parent,ctx,marker(parent,ctx)))


@pytest.mark.parametrize('damage',['before_blob','after_blob','omitted_path','base_sha256','canonical_sha256'])
def test_successor_admission_rejects_a_changed_edge(monkeypatch,damage):
    parent=old_after();ctx=candidate_execution(monkeypatch,parent)
    load=r.load_receipt
    def damaged(path):
        value=load(path)
        if Path(path).name!='stage_0_6_after_digest_successor.json':return value
        if damage=='omitted_path':value['engine_delta'].pop()
        elif damage in ('before_blob','after_blob'):value['engine_delta'][0][damage]='0'*40
        else:value[damage]='0'*64
        return value
    monkeypatch.setattr(r,'load_receipt',damaged)
    with pytest.raises(ValueError,match='successor'):api().attest(ROOT,parent,ctx)


@pytest.mark.parametrize('mode',['smoke','mature'])
def test_exact_original_after_digest_is_admitted_under_new_qualified_context(monkeypatch,mode):
    parent=old_after(mode);ctx=execution(monkeypatch,parent);recorded_service(monkeypatch)
    stamp=api().attest(ROOT,parent,ctx);row=proved(parent,ctx,stamp)
    pair=api().validate_chain(ROOT,row)
    assert pair['receipt_sha256']==c.receipt_hash(parent)
    assert parent==old_after(mode)


@pytest.mark.parametrize('aid',[14252280082,14252085073,14188030345,14187731783])
def test_every_new_and_inherited_input_is_reauthenticated(monkeypatch,aid):
    parent=old_after();ctx=execution(monkeypatch,parent);artifacts,runs=recorded_service(monkeypatch)
    row=proved(parent,ctx,api().attest(ROOT,parent,ctx));artifacts[aid]['expired']=True
    with pytest.raises(ValueError):api().validate_chain(ROOT,row)


@pytest.mark.parametrize('damage',['receipt','context','database','data-ref','source-control','contract'])
def test_stamps_cannot_grant_unpinned_historical_authority(monkeypatch,damage):
    parent=old_after('mature');ctx=execution(monkeypatch,parent);recorded_service(monkeypatch)
    if damage=='receipt':parent['metrics']['extra']='tamper'
    elif damage=='context':parent['context']['critical_blobs']['injected.py']='1'*40
    elif damage=='database':parent['database']['sha256']='0'*64
    elif damage=='data-ref':parent['data_ref']['artifact_id']+=1
    elif damage=='source-control':
        row=parent
        while row['stage']!='source_digest':row=row['parent']['receipt']
        row['metrics']['source_control']['digest']='0'*64
    else:
        row=proved(parent,ctx,api().attest(ROOT,parent,ctx));row['metrics']['proofs_admission']['contract_sha256']='0'*64
        with pytest.raises(ValueError):api().validate_chain(ROOT,row)
        return
    with pytest.raises(ValueError):api().attest(ROOT,parent,ctx)


def test_current_control_consumption_keeps_inherited_catalog_historical(monkeypatch):
    from simulation import stage_0_6_catalog_admission as legacy
    from simulation import stage_0_6_genesis_source_control as controls
    parent=old_after('mature');ctx=execution(monkeypatch,parent);recorded_service(monkeypatch)
    row=proved(parent,ctx,api().attest(ROOT,parent,ctx))
    monkeypatch.setattr(legacy,'validate_chain',lambda *a:pytest.fail('inherited cut was reinterpreted under current target'))
    controls.validate_control_chain(ROOT,row,current_runtime_tree=ctx['runtime_tree'])


def test_gate_selects_after_digest_without_completed_prefix_replay(tmp_path,monkeypatch,capsys):
    from simulation import stage_0_6_genesis_resume as m
    parent=old_after();ctx=execution(monkeypatch,parent);pair=api().contract(ROOT)['after_digests']['smoke']
    monkeypatch.setattr(m,'inspect_green',lambda root:{'qualified':True})
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    def restore(root,mode,run_id,artifact_id,destination):
        assert mode=='smoke' and run_id==43916382557 and artifact_id==14252280082
        return pair['metadata'],parent
    monkeypatch.setattr(api(),'restore_prior',restore)
    monkeypatch.setattr(m,'discover',lambda *a,**k:pytest.fail('ordinary discovery replayed a completed prefix'))
    m.gate(ROOT,tmp_path/'gate',input_mode='smoke',input_resume_run=43916382557)
    output=json.loads(capsys.readouterr().out)
    assert output['resume_index']==4 and output['resume_artifact_id']==14252280082 and output['fresh']=='false'


def test_real_proof_stage_keeps_original_after_digest_and_state(tmp_path):
    from test_stage_0_6_genesis_stages import setup_source,advance,producer
    from simulation import stage_0_6_genesis_stages as stages
    from ate_sim.persistence_proof_world_session import open_proof_world_session
    source,row=setup_source(tmp_path);path=source
    for stage in ('source_digest','capture','catalog','rebase','after_digest'):
        row,path=advance(stages,tmp_path,row,path,stage)
    before=c.file_hash(path);original=copy.deepcopy(row);ctx=successor(row);stamp=marker(row,ctx)
    out=tmp_path/'new-proofs'
    phases=[]
    result=stages.run_stage('proofs',row,path,out,producer=producer('proofs'),budget=120,
        successor_context=ctx,proofs_admission=stamp,progress=phases.append)
    assert c.file_hash(path)==before and row==original
    assert result['parent']['receipt']==original and result['metrics']['proofs_admission']==stamp
    assert 'audit.World.start' in phases and 'audit.sources.start' in phases and 'audit.sources.complete' in phases
    assert 'audit.World.complete' in phases and 'audit.scope_roots.start' in phases and 'audit.catalog.start' in phases
    with open_proof_world_session(out/'candidate.sqlite',rules_id=ctx['rules_id'],expected_commitment=bytes.fromhex(result['proof_commitment'])) as session:
        assert session.world.digest()==row['baseline_digest']


def test_mid_proof_process_exit_preserves_after_digest_for_ordinary_retry(tmp_path):
    import subprocess
    import sys
    from test_stage_0_6_genesis_stages import setup_source,advance,producer
    from simulation import stage_0_6_genesis_stages as stages
    spec=importlib.util.spec_from_file_location('proof_drill',ROOT/'.github/tests/run_genesis_recovery_drill.py')
    drill=importlib.util.module_from_spec(spec);spec.loader.exec_module(drill)
    assert hasattr(drill,'PROOF_CHILD'),'mid-proof hosted crash/recovery hook is missing'
    source,row=setup_source(tmp_path);path=source
    for stage in ('source_digest','capture','catalog','rebase','after_digest'):
        row,path=advance(stages,tmp_path,row,path,stage)
    before=c.file_hash(path);ctx=successor(row);stamp=marker(row,ctx)
    control=tmp_path/'control.json';control.write_text(json.dumps(dict(row=row,context=ctx,stamp=stamp,producer=producer('proofs'))))
    program="""
import json,sys
from pathlib import Path
from simulation import stage_0_6_genesis_resume as launcher
from simulation import stage_0_6_genesis_stages as stages
value=json.loads(Path(sys.argv[1]).read_text())
def local_main():
 stages.run_stage('proofs',value['row'],Path(sys.argv[2]),Path(sys.argv[3]),producer=value['producer'],budget=60,
   successor_context=value['context'],proofs_admission=value['stamp'])
launcher.main=local_main
"""+drill.PROOF_CHILD
    result=subprocess.run([sys.executable,'-c',program,str(control),str(path),str(tmp_path/'crashed')],capture_output=True,text=True,timeout=90)
    assert result.returncode==77,result.stderr
    assert c.file_hash(path)==before and not (tmp_path/'crashed').exists()
    retried=stages.run_stage('proofs',row,path,tmp_path/'retried',producer=producer('proofs'),budget=120,
        successor_context=ctx,proofs_admission=stamp)
    assert retried['stage']=='proofs' and c.file_hash(path)==before


def test_hosted_proof_crash_drill_uses_exact_after_digest_input():
    import yaml
    workflow=yaml.safe_load((ROOT/c.WORKFLOW).read_text())
    drill=next(s for s in workflow['jobs']['proofs']['steps'] if s.get('id')=='recovery-drill')
    worker=next(s for s in workflow['jobs']['proofs']['steps'] if s.get('id')=='run')
    assert drill['if']=="needs.gate.outputs.mode == 'smoke'" and drill['timeout-minutes']==5
    assert drill['env']==worker['env'] and 'run_genesis_recovery_drill.py' in drill['run']
