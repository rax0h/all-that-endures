from dataclasses import replace
import pytest
from ate_sim import persistence_proof_manifest_publish as manifests
from ate_sim import persistence_history_retirement as retirement
from ate_sim import persistence_proof_world as world
from ate_sim.mastery_training import ResponseModel
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,fast_open
from ate_sim.persistence_proof_world_session import open_audited_proof_world_session

@pytest.mark.parametrize('field,replacement',[(2,False),(3,1.0),(4,0)])
def test_initial_job_exact_types(tmp_path,monkeypatch,field,replacement):
    path,pair=ranked_fixture(tmp_path,size=4,configure=configure)
    with fast_open(path,pair) as s:
        a=s.world.advancement.path(1).abilities[0]
        a.response_model=ResponseModel()
        original=retirement.prepare_world_retirement_delta
        changed=[]
        def corrupt(*args,**kw):
            delta=original(*args,**kw)
            versions,ordinary,identities=delta.decode(args[0].codec)
            rows=[]
            for c in versions:
                if c.namespace==retirement.NAMESPACE and not c.delete and not changed:
                    v=list(c.value);v[field]=replacement
                    c=replace(c,value=tuple(v));changed.append(c)
                rows.append(c)
            from ate_sim.persistence_lazy_families import ParticipantDelta
            return ParticipantDelta.freeze(args[0].codec,'history-retirement',version_changes=rows,ordinary_changes=ordinary,identity_changes=identities)
        with monkeypatch.context() as m:
            m.setattr(retirement,'prepare_world_retirement_delta',corrupt)
            m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('unexpected full audit'))
            s.save()
        assert changed
        pair=s.proof_manifest
    with open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=pair[1]):
        pass
