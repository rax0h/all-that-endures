"""Real rank-up child replacements use bounded publication and retirement."""
from copy import deepcopy
from dataclasses import replace
import json
import random
import subprocess
import sys

import pytest

from ate_sim import persistence_proof_world as proof
from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
from ate_sim.persistence_record_runtime import record_backing
from ate_sim.mastery_training import ResponseModel
from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES
from ate_sim import persistence_proof_publication as content
from ate_sim import persistence_history_retirement as retirement
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_lazy_families import ParticipantDelta
from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
from ate_sim.agency import _practice_path
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open


def forbidden_audit(*args, **kwargs):
    raise AssertionError('rank-up or retirement scanned full World')


@pytest.mark.parametrize('body', [False, True])
def test_rank_up_saves_reopens_and_maintains_without_full_world_audit(tmp_path, monkeypatch, body):
    expected = []
    def setup(world):
        configure(world)
        abilities = world.advancement.path(1).abilities
        for ability in abilities:
            ability.level = 9
            ability.progress = .99
            if body:
                ability.function = 'creation'
                ability.rank = 2
                ability.level = 0
                ability.progress = 0.
        if body:
            abilities[19].rank = 1
            abilities[19].level = 9
            abilities[19].progress = .99
        expected.append(deepcopy(world))
    path, pair = ranked_fixture(tmp_path, size=4, configure=setup)
    eager = expected.pop()
    _practice_path(eager, eager.people[1], random.Random(32), 'work', .5)
    session = fast_open(path, pair)
    try:
        _practice_path(session.world, session.world.people[1], random.Random(32), 'work', .5)
        assert session.world.digest() == eager.digest()
        with monkeypatch.context() as patch:
            patch.setattr(proof, '_audit_world', forbidden_audit)
            session.save()
        pair = session.proof_manifest
    except BaseException:
        if session._state == 'recovery-required':
            session.resolve_save()
        raise
    finally:
        session.close()
    with open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=pair[1]) as audited:
        assert audited.world.digest() == eager.digest()
    for step in range(8):
        with fast_open(path, pair) as session:
            assert session.world.digest() == eager.digest()
            session.world.people[1].wealth += .125
            eager.people[1].wealth += .125
            with monkeypatch.context() as patch:
                patch.setattr(proof, '_audit_world', forbidden_audit)
                session.save()
            pair = session.proof_manifest
        if step == 3:
            with open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=pair[1]) as audited:
                assert audited.world.digest() == eager.digest()
    with fast_open(path, pair) as restored:
        assert restored.world.digest() == eager.digest()
    _practice_path(eager,eager.people[1],random.Random(33),'work',.5)
    code = '''
import json,random,sys
from ate_sim.agency import _practice_path
from ate_sim.persistence_proof_world_session import open_proof_world_session
with open_proof_world_session(sys.argv[1],rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(sys.argv[2])) as s:
 _practice_path(s.world,s.world.people[1],random.Random(33),'work',.5)
 print(json.dumps(s.world.digest()))
'''
    result = subprocess.run([sys.executable,'-c',code,str(path),pair[1].hex()],
        check=True,capture_output=True,text=True,timeout=30)
    assert json.loads(result.stdout) == eager.digest()


def test_private_unpublished_child_survives_without_orphan_dependency_publication(tmp_path):
    path,pair = ranked_fixture(tmp_path,size=4,configure=configure)
    with fast_open(path,pair) as session:
        ability = session.world.advancement.path(1).abilities[0]
        original = ability.response_model
        ability.response_model = ResponseModel()
        private = ability.response_model
        inc = record_backing(private)._incarnation
        ability.response_model = original
        session.world.people[1].wealth += .125
        session.save()
        with pytest.raises(KeyError):
            session.store.read_version(session.pin,DEPENDENCIES,inc,expected_record_schema=1)
        private.trials = 7
        ability.response_model = private
        session.save()
        assert ability.response_model is private and private.trials == 7
        saved = session.proof_manifest
    with fast_open(path,saved) as restored:
        assert restored.world.advancement.path(1).abilities[0].response_model.trials == 7


@pytest.mark.parametrize('phase',['before_commit','after_commit'])
def test_rank_up_joint_failure_recovers_exact_state_and_preserves_old_private_alias(tmp_path,phase):
    def setup(world):
        configure(world)
        for ability in world.advancement.path(1).abilities:
            ability.level=9
            ability.progress=.99
    path,pair = ranked_fixture(tmp_path,size=4,configure=setup)
    with fast_open(path,pair) as session:
        abilities = tuple(session.world.advancement.path(1).abilities)
        old = tuple(a.response_model for a in abilities)
        _practice_path(session.world,session.world.people[1],random.Random(32),'work',.5)
        expected = session.world.digest()
        private = next(model for model,a in zip(old,abilities) if model is not a.response_model)
        private.trials = 19
        assert session.world.digest() == expected
        def fault(at):
            if at==phase:
                raise OSError('rank-up publication interrupted')
        session.store._phase_hook=fault
        with pytest.raises(OSError,match='rank-up publication interrupted'):
            session.save()
        session.store._phase_hook=lambda _:None
        resolved=session.resolve_save()
        assert resolved==(0 if phase=='before_commit' else 1)
        if not resolved:
            with monkeypatch_audit_forbidden():
                session.save()
        assert private.trials==19 and session.world.digest()==expected
        saved=session.proof_manifest
    with fast_open(path,saved) as restored:
        assert restored.world.digest()==expected


def monkeypatch_audit_forbidden():
    from unittest.mock import patch
    return patch.object(proof,'_audit_world',forbidden_audit)


def test_rank_up_and_retirement_never_read_unrelated_history_bodies(tmp_path,monkeypatch):
    def setup(world):
        configure(world)
        for ability in world.advancement.path(1).abilities:
            ability.level=9
            ability.progress=.99
    path,pair=ranked_fixture(tmp_path,size=10000,configure=setup)
    with fast_open(path,pair) as session:
        unrelated=session.store.read_identity_occurrence(session.pin,'world.skills.skills',
            (1,'craft'),(('field','provenance'),)).incarnation_id
        original=content._source_version
        def checked(store,generation,namespace,typed,*args,**kwargs):
            if namespace in (PAGE_NAMESPACE,ENTRY_NAMESPACE):
                assert store.codec.decode(typed)[0]!=unrelated,'rank-up read unrelated history'
            return original(store,generation,namespace,typed,*args,**kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(content,'_source_version',checked)
            patch.setattr(proof,'_audit_world',forbidden_audit)
            _practice_path(session.world,session.world.people[1],random.Random(32),'work',.5)
            session.save()
            for _ in range(8):
                session.world.people[1].wealth+=.125
                session.save()


@pytest.mark.parametrize('field,value',[(2,False),(3,1.0),(4,0)])
def test_noncanonical_initial_job_is_rejected_before_commit_and_can_retry(tmp_path,monkeypatch,field,value):
    path,pair=ranked_fixture(tmp_path,size=4,configure=configure)
    with fast_open(path,pair) as session:
        session.world.advancement.path(1).abilities[0].response_model=ResponseModel()
        original=retirement.prepare_world_retirement_delta
        changed=[]
        def corrupt(store,*args,**kwargs):
            delta=original(store,*args,**kwargs)
            versions,ordinary,identities=delta.decode(store.codec)
            rows=[]
            for change in versions:
                if change.namespace==retirement.NAMESPACE and not change.delete and not changed:
                    invalid=list(change.value)
                    invalid[field]=value
                    change=replace(change,value=tuple(invalid))
                    changed.append(change)
                rows.append(change)
            return ParticipantDelta.freeze(store.codec,'history-retirement',version_changes=rows,
                ordinary_changes=ordinary,identity_changes=identities)
        with monkeypatch.context() as patch:
            patch.setattr(retirement,'prepare_world_retirement_delta',corrupt)
            patch.setattr(proof,'_audit_world',forbidden_audit)
            with pytest.raises(StoreIntegrityError):
                session.save()
        assert changed and session.resolve_save()==pair[0].generation
        assert session.proof_manifest==pair
        with monkeypatch_audit_forbidden():
            session.save()
