from dataclasses import replace
import pytest
from ate_sim import persistence_history_retirement as producer
from ate_sim import persistence_proof_world as world
from ate_sim import persistence_proof_world_retirement as validator
from ate_sim.persistence_record_runtime import record_backing
from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
from ate_sim.persistence_lazy_store import _version_checksum
from ate_sim.incremental_store import StoreIntegrityError,_framed_sha
from ate_sim.mastery_training import ResponseModel
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,fast_open


def test_partial_valid_and_malformed_cursor(tmp_path,monkeypatch):
    def config(w):
        configure(w)
        w.advancement.path(1).abilities[0].response_model.samples=list(range(512))
    path,pair=ranked_fixture(tmp_path,size=4,configure=config)
    with fast_open(path,pair) as s:
        s.world.advancement.path(1).abilities[0].response_model=ResponseModel()
        s.save();pair=s.proof_manifest
    original=producer.prepare_retirement_delta
    seen=[]
    def bounded(store,pin,**kw):
        kw['row_budget']=4
        return original(store,pin,**kw)
    for step in range(8):
        with fast_open(path,pair) as s:
            s.world.people[1].wealth+=.125
            with monkeypatch.context() as m:
                m.setattr(producer,'prepare_retirement_delta',bounded)
                m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('partial maintenance ran full audit'))
                s.save()
            pair=s.proof_manifest
            for inc in s.store.iter_keys(s.pin,producer.NAMESPACE):
                job=producer._job(s.store,s.pin,inc)
                if job[1]=='list' and job[2]==0 and job[4] and producer._scope_keys(s.store,s.pin,producer.SCOPES['list'][0],inc,limit=1):
                    seen.append(inc)
        if seen:break
    assert seen,'did not construct a true within-scope partial cleanup'
    with open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=pair[1]):pass
    original_audit=validator.audit_jobs
    def malformed(store,pin):
        inc=seen[0];ns=producer.NAMESPACE;typed=store.codec.encode(inc)
        row=store.db.execute('select record_schema,codec_version,valid_from,valid_to,memberships,payload from lazy_record_versions where namespace=? and typed_key=? and valid_to is null',(ns,typed)).fetchone()
        schema,codec,start,end,members,old=row
        job=list(store.codec.decode(old));job[2]=1;payload=store.codec.encode(tuple(job))
        checksum=_version_checksum(ns,typed,schema,codec,start,end,members,payload)
        store.db.execute('update lazy_record_versions set payload=?,payload_checksum=?,row_checksum=? where namespace=? and typed_key=? and valid_to is null',(payload,_framed_sha(b'lazy-payload-v1',payload),checksum,ns,typed))
        original_audit(store,pin)
    with monkeypatch.context() as m:
        m.setattr(validator,'audit_jobs',malformed)
        with pytest.raises(StoreIntegrityError,match='cursor passed surviving physical authority'):
            open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=pair[1])
    with open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=pair[1]):pass
