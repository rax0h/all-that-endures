"""Both independent proofs must bind one exact candidate before advancing."""
import copy
from dataclasses import replace
from pathlib import Path
import shutil

import pytest

from simulation import continuation_receipts as r
from simulation.tests.test_continuation_checkpoint import publication,module,hashes,forbidden
from simulation.tests.test_continuation_verifiers import saved_template,saved_inputs,api
from simulation.tests.test_continuation_receipts import producer


@pytest.fixture(scope='module')
def verified_template(tmp_path_factory,saved_template):
    m=api();source,a,saved,candidate=saved_template
    root=tmp_path_factory.mktemp('verification-pair')
    audit=m.audit_year(source,root/'audit.json',authority=a,candidate=candidate,producer=producer('audit','audit1'))
    digest=m.digest_year(source,root/'digest.json',authority=a,candidate=candidate,producer=producer('digest','digest1'))
    audit_ref=replace(candidate,artifact_id=11,name='audit1',producer_job='audit1')
    digest_ref=replace(candidate,artifact_id=12,name='digest1',producer_job='digest1')
    return source,a,saved,candidate,audit,digest,audit_ref,digest_ref


def accept_pair(template,**changes):
    assert hasattr(r,'accept_year'), 'candidate acceptance boundary missing'
    source,a,saved,candidate,audit,digest,audit_ref,digest_ref=template
    args=dict(authority=a,candidate=candidate,audit_proof=audit_ref,digest_proof=digest_ref,
        previous_acceptance=None,producer=producer('accept-year','accept1'))
    args.update(changes)
    return r.accept_year(saved,audit,digest,**args)


def changed_values(template):
    values=list(template)
    for index in (2,4,5):values[index]=copy.deepcopy(values[index])
    return values


def test_matching_proofs_accept_only_the_year_and_retain_exact_member_hashes(verified_template,monkeypatch):
    m=api();monkeypatch.setattr(m,'open_lazy_world_session',forbidden)
    row=accept_pair(verified_template)
    assert row['stage']=='year-verified' and row['stage_0_5_accepted'] is False
    assert row['binding']['year']==1
    assert row['proofs']['audit']['receipt_sha256']==r.receipt_hash(verified_template[4])
    assert row['proofs']['digest']['receipt_sha256']==r.receipt_hash(verified_template[5])
    assert row['binding']['candidate']['artifact_id']==10


@pytest.mark.parametrize('field,value',[
    ('year',2),('generation',99),('store_identity','foreign'),('save_sha256','9'*64),
    ('checkpoint_sha256','8'*64),('runtime_sha','1'*40),('runtime_tree','2'*40),
])
def test_mixed_binding_cannot_approve_a_candidate(verified_template,field,value):
    values=changed_values(verified_template);values[4]['binding'][field]=value
    with pytest.raises(ValueError):accept_pair(values)


def test_same_year_equal_digest_with_different_candidate_artifact_rejects(verified_template):
    values=changed_values(verified_template);values[5]['binding']['candidate']['artifact_id']=99
    with pytest.raises(ValueError):accept_pair(values)


@pytest.mark.parametrize('damage',['audit','digest','original','authority','producer','manifest','counter','extra'])
def test_forged_or_altered_receipt_fields_reject(verified_template,damage):
    values=changed_values(verified_template);audit=values[4]
    if damage=='audit':audit['observation']['audit']['snapshot']['year']=999
    elif damage=='digest':values[5]['observation']['digest']='0'*64
    elif damage=='original':audit['original_checkpoint']='{}'
    elif damage=='authority':audit['authority']['context']['runtime_sha']='0'*40
    elif damage=='producer':audit['producer']['job']='foreign'
    elif damage=='manifest':values[2]['database']['sha256']='1'*64
    elif damage=='counter':audit['observation']['counters']['next_person']+=1
    else:audit['extra']=True
    with pytest.raises(ValueError):accept_pair(values)


def test_second_year_requires_and_binds_the_first_acceptance(tmp_path,verified_template):
    first=accept_pair(verified_template);source,a,saved,candidate,*_=verified_template
    m=api();first_ref=replace(candidate,artifact_id=13,name='accept1',producer_job='accept1')
    predecessor=dict(kind='year-verified',artifact=first_ref.to_dict(),receipt_sha256=r.receipt_hash(first),receipt=first)
    output=tmp_path/'saved2'
    second_saved=m.save_year(source,output,authority=a,year=2,predecessor=predecessor,producer=producer('save','save2'))
    second_ref=replace(candidate,artifact_id=20,name='saved2',producer_job='save2')
    audit=m.audit_year(output,tmp_path/'audit2.json',authority=a,candidate=second_ref,producer=producer('audit','audit2'))
    digest=m.digest_year(output,tmp_path/'digest2.json',authority=a,candidate=second_ref,producer=producer('digest','digest2'))
    kwargs=dict(authority=a,candidate=second_ref,audit_proof=replace(second_ref,artifact_id=21,name='audit2',producer_job='audit2'),
        digest_proof=replace(second_ref,artifact_id=22,name='digest2',producer_job='digest2'),producer=producer('accept-year','accept2'))
    with pytest.raises(ValueError):r.accept_year(second_saved,audit,digest,previous_acceptance=None,**kwargs)
    second=r.accept_year(second_saved,audit,digest,previous_acceptance=first,**kwargs)
    result=r.accept_continuation(first,second,authority=a,producer=producer('accept-continuation','continued'))
    assert result['stage']=='continuation-verified' and result['stage_0_5_accepted'] is False
    assert result['final_binding']['candidate']['artifact_id']==20
    assert result['final_binding']['generation']==a.bootstrap_generation+2
    assert hashes(output)['candidate.sqlite']==result['final_binding']['database']['sha256']
    foreign=copy.deepcopy(first);foreign['binding']['candidate']['artifact_id']=99
    with pytest.raises(ValueError):r.accept_continuation(foreign,second,authority=a,producer=producer('accept-continuation','continued'))
