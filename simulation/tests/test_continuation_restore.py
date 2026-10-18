"""Restore independently observes actual reopened values and digest."""
import copy
from dataclasses import replace

import pytest

from simulation import continuation_receipts as r
from simulation.tests.test_continuation_checkpoint import publication,module,hashes,forbidden
from simulation.tests.test_continuation_verifiers import saved_template,api
from simulation.tests.test_continuation_acceptance import verified_template,accept_pair
from simulation.tests.test_continuation_receipts import producer


@pytest.fixture(scope='module')
def continuation_template(tmp_path_factory,verified_template):
    first=accept_pair(verified_template);source,a,saved,candidate,*_=verified_template
    root=tmp_path_factory.mktemp('actual-restore')
    first_ref=replace(candidate,artifact_id=13,name='accept1',producer_job='accept1')
    predecessor=dict(kind='year-verified',artifact=first_ref.to_dict(),receipt_sha256=r.receipt_hash(first),receipt=first)
    m=api();saved2=m.save_year(source,root/'saved2',authority=a,year=2,
        predecessor=predecessor,producer=producer('save','save2'))
    ref2=replace(candidate,artifact_id=20,name='saved2',producer_job='save2')
    audit=m.audit_year(root/'saved2',root/'audit2.json',authority=a,candidate=ref2,producer=producer('audit','audit2'))
    digest=m.digest_year(root/'saved2',root/'digest2.json',authority=a,candidate=ref2,producer=producer('digest','digest2'))
    second=r.accept_year(saved2,audit,digest,authority=a,candidate=ref2,
        audit_proof=replace(ref2,artifact_id=21,name='audit2',producer_job='audit2'),
        digest_proof=replace(ref2,artifact_id=22,name='digest2',producer_job='digest2'),
        previous_acceptance=first,producer=producer('accept-year','accept2'))
    continued=r.accept_continuation(first,second,authority=a,producer=producer('accept-continuation','continued'))
    return root/'saved2',a,ref2,continued


def restore_api():
    m=api();assert hasattr(m,'restore_values') and hasattr(m,'restore_digest'), 'independent restore stage missing'
    return m


def test_restore_opens_copies_and_compares_actual_values_digest_and_counters(tmp_path,continuation_template,monkeypatch):
    m=restore_api();saved,a,candidate,continued=continuation_template;before=hashes(saved)
    monkeypatch.setattr(m.Simulation,'run',forbidden)
    actual=m.open_lazy_world_session;opened=[]
    def observe(path,**kw):
        assert path!=saved/'candidate.sqlite';opened.append(path)
        return actual(path,**kw)
    monkeypatch.setattr(m,'open_lazy_world_session',observe)
    values=m.restore_values(saved,tmp_path/'values.json',authority=a,candidate=candidate,
        continuation=continued,producer=producer('restore-values','values'))
    digest=m.restore_digest(saved,tmp_path/'digest.json',authority=a,candidate=candidate,
        continuation=continued,producer=producer('restore-digest','restore-digest'))
    assert len(opened)==2 and opened[0]!=opened[1]
    control=r.original_from_text(continued['original_checkpoint'],a)['state']['controls']['2']
    assert values['observation']['snapshot']==control['audit']['snapshot']
    assert digest['observation']['digest']==control['digest']
    assert values['observation']['counters']==digest['observation']['counters']==control['counters']
    refs=dict(values=replace(candidate,artifact_id=31,name='values',producer_job='values'),
        digest=replace(candidate,artifact_id=32,name='restore-digest',producer_job='restore-digest'),
        continuation=replace(candidate,artifact_id=30,name='continued',producer_job='continued'))
    result=r.accept_restore(values,digest,continuation=continued,proofs=refs,producer=producer('accept-restore','restored'))
    assert result['stage']=='restore-verified' and result['stage_0_5_accepted'] is False
    assert result['binding']['year']==2 and hashes(saved)==before


@pytest.mark.parametrize('damage',['stand-in','candidate','control','runtime','year','generation'])
def test_restore_rejects_foreign_authority_before_open(tmp_path,continuation_template,monkeypatch,damage):
    m=restore_api();saved,a,candidate,continued=continuation_template;continued=copy.deepcopy(continued)
    if damage=='stand-in':continued=continued['second']
    elif damage=='candidate':candidate=replace(candidate,artifact_id=99)
    elif damage=='control':continued['original_checkpoint']='{}'
    elif damage=='runtime':continued['authority']['execution_runtime_sha']='9'*40
    elif damage=='year':continued['final_binding']['year']=True
    else:continued['final_binding']['generation']=999
    monkeypatch.setattr(m,'open_lazy_world_session',forbidden)
    with pytest.raises(ValueError):m.restore_values(saved,tmp_path/'out.json',authority=a,
        candidate=candidate,continuation=continued,producer=producer('restore-values','values'))
    assert not (tmp_path/'out.json').exists()


def test_actual_wrong_restored_snapshot_is_rejected(tmp_path,continuation_template,monkeypatch):
    m=restore_api();saved,a,candidate,continued=continuation_template
    actual=m.p5.snapshot
    def wrong(world,**kw):
        result=actual(world,**kw);result['magic_access']['treasuries'][1]['iron']+=1
        return result
    monkeypatch.setattr(m.p5,'snapshot',wrong)
    with pytest.raises(ValueError,match='control'):m.restore_values(saved,tmp_path/'wrong.json',
        authority=a,candidate=candidate,continuation=continued,producer=producer('restore-values','values'))
    assert not (tmp_path/'wrong.json').exists()
