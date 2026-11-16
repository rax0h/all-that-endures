"""An exact old catalog can cross only the reviewed rebase admission cut."""
import copy
import importlib
import json
from pathlib import Path
import zipfile

import pytest

from simulation import stage_0_6_genesis_checkpoint as c

ROOT = Path(__file__).resolve().parents[2]


def old_catalog(mode='smoke'):
    archive=('forensic-repair/smoke-43778758497-evidence.zip' if mode=='smoke'
             else 'rebase-locator-repair/evidence.zip')
    member='original-artifacts/14188030345.zip' if mode=='smoke' else 'hosted/original-catalog-metadata.zip'
    with zipfile.ZipFile(ROOT/'docs/performance/stage-0-6-current'/archive) as outer:
        import io
        with zipfile.ZipFile(io.BytesIO(outer.read(member))) as z:
            return json.loads(z.read('checkpoint.json'))


def successor(parent):
    ctx=copy.deepcopy(parent['context'])
    ctx.update(runtime_tree='0d9dab5d4b36c89814dac6cb5904d589db4b8902',critical_blobs={'successor.py':'a'*40})
    return ctx


def marker(parent,ctx):
    return dict(schema='ate-catalog-runtime-admission/1',parent_sha256=c.receipt_hash(parent),
                parent_database=copy.deepcopy(parent['database']),
                from_context_sha256=c.receipt_hash(parent['context']),
                to_context_sha256=c.receipt_hash(ctx),contract_sha256='c'*64)


def rebased(parent,ctx,stamp):
    return c.record('rebase',ctx,{**parent['database'],'generation':0,'sha256':'d'*64},
                    dict(run_id=2,head_sha='e'*40,job='rebase',attempt=1),
                    parent=parent,metrics={'catalog_admission':stamp})


def test_rebase_preserves_original_chain_across_explicit_context_cut():
    parent=old_catalog();before=copy.deepcopy(parent);ctx=successor(parent)
    row=rebased(parent,ctx,marker(parent,ctx))
    assert row['parent']['receipt']==before and parent==before
    child=c.record('after_digest',ctx,row['database'],dict(run_id=2,head_sha='e'*40,job='after-digest',attempt=1),parent=row)
    assert c.validate(child)['parent']['receipt']['parent']['receipt']==before


@pytest.mark.parametrize('field',['source','rules_id','rank_proofs','expected_saved_digest','execution_runtime'])
def test_context_cut_cannot_change_any_world_or_hosted_authority(field):
    parent=old_catalog();ctx=successor(parent)
    if field=='source':ctx[field]['year']+=1
    elif field=='execution_runtime':ctx[field]['signature']='f'*64
    elif field=='rank_proofs':ctx[field]=False
    else:ctx[field]='f'*64
    with pytest.raises(ValueError):rebased(parent,ctx,marker(parent,ctx))


@pytest.mark.parametrize('field',['parent_sha256','from_context_sha256','to_context_sha256','parent_database','schema'])
def test_structural_admission_rejects_rebound_marker(field):
    parent=old_catalog();ctx=successor(parent);stamp=marker(parent,ctx)
    if field=='parent_database':stamp[field]['sha256']='f'*64
    else:stamp[field]='f'*64
    with pytest.raises(ValueError):rebased(parent,ctx,stamp)


def test_unmarked_context_change_remains_forbidden():
    parent=old_catalog();ctx=successor(parent)
    with pytest.raises(ValueError):rebased(parent,ctx,None)


def api():
    return importlib.import_module('simulation.stage_0_6_catalog_admission')


def execution(monkeypatch,parent):
    from simulation import stage_0_6_genesis_resume as m
    ctx=successor(parent);observed=copy.deepcopy(ctx)
    monkeypatch.setattr(m,'fence',lambda root:(observed['runtime_tree'],observed['critical_blobs']))
    monkeypatch.setattr(m,'runtime_description',lambda:(observed['execution_runtime'],{}))
    return ctx


@pytest.mark.parametrize('mode,artifact',[('smoke',14188030345),('mature',14197005279)])
def test_pinned_contract_authenticates_exact_old_chain_and_current_execution(monkeypatch,mode,artifact):
    a=api();parent=old_catalog(mode);ctx=execution(monkeypatch,parent)
    recorded_service(monkeypatch,snapshot(mode))
    stamp=a.attest(ROOT,parent,ctx);row=rebased(parent,ctx,stamp)
    assert a.validate_chain(ROOT,row)['metadata']['artifact_id']==artifact
    if mode=='smoke':assert a.require_small_cut(ROOT,row)['receipt_sha256']==c.receipt_hash(parent)
    else:
        from simulation import stage_0_6_genesis_source_control as controls
        controls.validate_control_chain(ROOT,row,current_runtime_tree=ctx['runtime_tree'])
        assert row['baseline_digest']=='57f60fdf49e221af24ffc0a1f2d5a3885dd37c07db00d153171adcb91c579eed'
        with pytest.raises(ValueError,match='small'):a.require_small_cut(ROOT,row)


@pytest.mark.parametrize('damage',['old_receipt','target_engine','current_blobs','contract_hash','source_runtime'])
def test_structural_marker_cannot_grant_unpinned_execution_authority(monkeypatch,damage):
    a=api();parent=old_catalog();ctx=execution(monkeypatch,parent);stamp=a.attest(ROOT,parent,ctx)
    if damage=='old_receipt':parent['metrics']['forged']=True
    elif damage=='target_engine':ctx['runtime_tree']='f'*40
    elif damage=='current_blobs':ctx['critical_blobs']={'wrong.py':'f'*40}
    elif damage=='source_runtime':
        parent['context']['execution_runtime']['signature']='f'*64
        ctx['execution_runtime']['signature']='f'*64
    stamp=marker(parent,ctx)
    stamp['contract_sha256']=c.file_hash(ROOT/a.CONTRACT) if damage!='contract_hash' else 'f'*64
    with pytest.raises(ValueError):a.validate_chain(ROOT,rebased(parent,ctx,stamp))


def test_admission_marker_cannot_appear_outside_rebase():
    parent=old_catalog();ctx=successor(parent);row=rebased(parent,ctx,marker(parent,ctx))
    child=c.record('after_digest',ctx,row['database'],dict(run_id=2,head_sha='e'*40,job='after-digest',attempt=1),parent=row)
    child['metrics']['catalog_admission']=marker(parent,ctx)
    with pytest.raises(ValueError):c.validate(child)


def test_real_rebase_cut_keeps_source_and_aliases_without_prefix_replay(tmp_path,monkeypatch):
    from test_stage_0_6_genesis_stages import setup_source,advance,producer,api as stages_api
    from ate_sim import persistence_catalog_copy as catalog,persistence_lazy_store as lazy
    from ate_sim.persistence_lazy import open_lazy_world_session
    from unittest.mock import patch
    stages=stages_api();path,parent=setup_source(tmp_path)
    for phase in ('source_digest','capture','catalog'):parent,path=advance(stages,tmp_path,parent,path,phase)
    saved=copy.deepcopy(parent);source_hash=c.file_hash(path);ctx=successor(parent);stamp=marker(parent,ctx)
    def prohibit(*a,**k):raise AssertionError('completed prefix replayed')
    monkeypatch.setattr(catalog,'_copy_current_checked_catalog',prohibit)
    monkeypatch.setattr(lazy.LazyRecordStore,'copy_current_head',prohibit)
    with patch.object(lazy.LazyRecordStore,'_verify_all_in_snapshot',autospec=True,
                      side_effect=lazy.LazyRecordStore._verify_all_in_snapshot) as audits:
        row=stages.run_stage('rebase',parent,path,tmp_path/'admitted',producer=producer('rebase'),budget=120,
                            successor_context=ctx,catalog_admission=stamp)
        assert audits.call_count>=1
    assert parent==saved and row['parent']['receipt']==saved and c.file_hash(path)==source_hash
    row,newpath=advance(stages,tmp_path,row,tmp_path/'admitted/candidate.sqlite','after_digest')
    assert row['baseline_digest']==saved['baseline_digest']
    with open_lazy_world_session(newpath,rules_id=ctx['rules_id']) as session:
        assert session.world.digest()==saved['baseline_digest']
        assert session.skills[1,'craft'].provenance is session.skills[2,'craft'].provenance


def test_unqualified_cut_cannot_be_requested_at_another_stage(tmp_path):
    from simulation import stage_0_6_genesis_stages as stages
    parent=old_catalog();ctx=successor(parent)
    with pytest.raises(ValueError,match='rebase'):
        stages.run_stage('after_digest',parent,tmp_path/'absent',tmp_path/'out',
                         producer=dict(run_id=2,head_sha='e'*40,job='after-digest',attempt=1),budget=120,
                         successor_context=ctx,catalog_admission=marker(parent,ctx))
    assert not (tmp_path/'out').exists()


def snapshot(mode='smoke'):
    archive=('forensic-repair/smoke-43778758497-evidence.zip' if mode=='smoke'
             else 'rebase-locator-repair/evidence.zip')
    member='hosted-metadata.json' if mode=='smoke' else 'hosted/failed-run-metadata.json'
    with zipfile.ZipFile(ROOT/'docs/performance/stage-0-6-current'/archive) as z:
        return json.loads(z.read(member))


def recorded_service(monkeypatch,meta):
    from simulation import checkpoint_artifacts as github
    artifacts={x['id']:x for x in meta['artifacts']['artifacts']}
    def fetch(path):
        if path.startswith('/actions/artifacts/'):return artifacts[int(path.rsplit('/',1)[1])]
        if path==f"/actions/runs/{meta['run']['id']}":return meta['run']
        raise AssertionError(path)
    def pages(path,key):
        assert path==f"/actions/runs/{meta['run']['id']}/jobs?filter=all" and key=='jobs'
        return meta['jobs']['jobs']
    monkeypatch.setattr(github,'_api',fetch);monkeypatch.setattr(github,'_pages',pages)


def test_old_catalog_metadata_and_data_require_real_completed_producers(monkeypatch):
    a=api();parent=old_catalog();execution(monkeypatch,parent);meta=snapshot();recorded_service(monkeypatch,meta)
    actual=a.inspect_prior(ROOT,'smoke',43778758497,14188030345)
    assert actual==a.contract(ROOT)['catalogs']['smoke']['metadata']


@pytest.mark.parametrize('damage',['metadata_hash','data_hash','data_bytes','expired','producer_head','incomplete_upload'])
def test_old_transport_cannot_borrow_an_unverified_reference(monkeypatch,damage):
    a=api();execution(monkeypatch,old_catalog());meta=snapshot()
    artifacts={x['id']:x for x in meta['artifacts']['artifacts']};metadata=artifacts[14188030345];data=artifacts[14187731783]
    if damage=='metadata_hash':metadata['digest']='sha256:'+'f'*64
    elif damage=='data_hash':data['digest']='sha256:'+'f'*64
    elif damage=='data_bytes':data['size_in_bytes']+=1
    elif damage=='expired':data['expires_at']='2000-01-01T00:00:00Z'
    else:
        job=next(j for j in meta['jobs']['jobs'] if j['name']=='catalog')
        if damage=='producer_head':job['head_sha']='f'*40
        else:next(s for s in job['steps'] if s['name']=='Publish sealed checkpoint metadata')['conclusion']='failure'
    recorded_service(monkeypatch,meta)
    with pytest.raises(ValueError):a.inspect_prior(ROOT,'smoke',43778758497,14188030345)


@pytest.mark.parametrize('mode,run,artifact',[('mature',43778758497,14188030345),('smoke',1,14188030345),('smoke',43778758497,1)])
def test_nonadmitted_resume_refuses_before_download(tmp_path,mode,run,artifact):
    with pytest.raises(ValueError):api().restore_prior(ROOT,mode,run,artifact,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_ordinary_smoke_without_admission_cannot_qualify_mature_reuse():
    with pytest.raises(ValueError,match='lacks'):api().require_small_cut(ROOT,old_catalog())


@pytest.mark.parametrize('boundary',['chain','control','seal','restore','require-small'])
def test_every_consumption_reauthenticates_old_catalog_authority(tmp_path,monkeypatch,boundary):
    from simulation import stage_0_6_genesis_resume as m,stage_0_6_genesis_source_control as controls
    from simulation import checkpoint_artifacts as github
    a=api();parent=old_catalog();ctx=execution(monkeypatch,parent)
    row=rebased(parent,ctx,a.attest(ROOT,parent,ctx));row['data_ref']=copy.deepcopy(parent['data_ref'])
    calls=[]
    def unavailable(path):
        calls.append(path)
        raise ValueError('old catalog artifact unavailable or expired')
    monkeypatch.setattr(github,'_api',unavailable)
    if boundary=='seal':
        c.publish(tmp_path/'out',row)
        for key,val in dict(GITHUB_RUN_ID='2',GITHUB_SHA='e'*40,GITHUB_JOB='rebase',GITHUB_RUN_ATTEMPT='1').items():monkeypatch.setenv(key,val)
        before=(tmp_path/'out/checkpoint.json').read_bytes()
    if boundary=='restore':
        # The current producer download succeeds; its old admission must still
        # be checked instead of borrowing authority from current transport.
        monkeypatch.setattr(m.t,'restore',lambda ref,destination,**kw:c.publish(destination,row))
    with pytest.raises(ValueError,match='old catalog artifact'):
        if boundary=='chain':a.validate_chain(ROOT,row)
        elif boundary=='control':controls.validate_control_chain(ROOT,row,current_runtime_tree=ctx['runtime_tree'])
        elif boundary=='seal':m.seal(ROOT,tmp_path)
        elif boundary=='restore':m.restore_receipt(ROOT,row['data_ref'],tmp_path/'restored',mode='smoke',stage='rebase')
        else:a.require_small_cut(ROOT,row)
    assert calls
    if boundary=='seal':assert (tmp_path/'out/checkpoint.json').read_bytes()==before
