"""Mature construction must use the pinned source and stop at unverified capture."""
import importlib
import hashlib
import json
from pathlib import Path
import pytest
from simulation.tests.test_checkpointed_upgrade_validation import inputs, CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.checkpoint_mature_capture'), 'mature capture wiring missing'
    return importlib.import_module('simulation.checkpoint_mature_capture')


def test_source_receipt_requires_every_original_configuration_field(tmp_path):
    m=module()
    database=tmp_path/'p5-long-lazy.sqlite';database.write_bytes(b'source')
    receipt={'schema':1,'stage':'lazy','workflow_sha':m.SOURCE_WORKFLOW_SHA,
        'config':m.SOURCE_CONFIG,'database':{'name':database.name,'sha256':sha(database)}}
    path=tmp_path/'checkpoint.json';path.write_text(json.dumps(receipt))
    m.check_source(tmp_path)
    for field in m.SOURCE_CONFIG:
        broken=json.loads(json.dumps(receipt));broken['config'][field]='foreign'
        path.write_text(json.dumps(broken))
        with pytest.raises(ValueError):m.check_source(tmp_path)
    path.write_text(json.dumps(receipt));database.write_bytes(b'corrupt')
    with pytest.raises(ValueError):m.check_source(tmp_path)


def test_mature_run_reuses_core_capture_without_full_verification(tmp_path,monkeypatch):
    from simulation import complete_upgrade_checkpoint as core
    from ate_sim import persistence_catalog_copy as copy
    source,receipt=inputs(tmp_path);before=sha(source)
    m=module();restored=[];original=copy._restore_copy_ordinals
    def ordinals(*args):
        result=original(*args);restored.append(True);return result
    monkeypatch.setattr(copy,'_restore_copy_ordinals',ordinals)
    verify=copy.LazyRecordStore.verify_all
    def checked(store):
        assert not restored,'mature capture invoked post-commit verification'
        return verify(store)
    monkeypatch.setattr(copy.LazyRecordStore,'verify_all',checked)
    m.run_capture(source,receipt,tmp_path/'candidate',rules_id=RULES,context=CONTEXT)
    assert sha(source)==before and restored==[True]
    manifest=core.validate(tmp_path/'candidate',context=CONTEXT)
    assert manifest['stage']=='unverified'
    assert not (tmp_path/'complete.sqlite').exists()


def test_mature_workflow_does_not_run_verifiers_or_continuation():
    p=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-capture.yml'
    assert p.exists(),'mature capture workflow missing'
    text=p.read_text()
    assert '300m python -m simulation.checkpoint_mature_capture' in text
    assert 'timeout-minutes: 360' in text
    assert 'checkpoint_mature_capture' in text
    assert 'verify_storage' not in text and 'verify_catalog' not in text
    assert text.index('if: always()') < text.index('name: Retain unverified candidate')
    assert 'continue-on-error: true' in text
    assert 'overwrite: true' not in text


def test_mature_capture_uses_dedicated_branch():
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-capture.yml'
    text=path.read_text()
    assert 'sol/stage-0-5-mature-checkpoint-validation' in text
    assert 'sol/stage-0-5-final-release-validation' not in text


@pytest.mark.parametrize('condition',['run-failed','foreign-commit','missing-job','restore-failed'])
def test_proof_gate_rejects_incomplete_or_foreign_evidence(tmp_path,monkeypatch,condition):
    m=module();monkeypatch.setattr(m,'ROOT',tmp_path)
    run={'conclusion':'failure' if condition=='run-failed' else 'success',
         'head_sha':'foreign' if condition=='foreign-commit' else '25a88883aff2c494481fee40ab0a29afed28a878'}
    names={'harness-tests','source','capture','storage','interrupt','catalog','publish','continue','restore'}
    if condition=='missing-job':names.remove('restore')
    monkeypatch.setattr(m.artifacts,'_api',lambda path:run)
    monkeypatch.setattr(m.artifacts,'_pages',lambda *args:[{'name':name,'conclusion':'success'} for name in names])
    def download(destination,**kwargs):
        destination.mkdir()
        (destination/'restore.json').write_text(json.dumps({'passed':False,'year':2,'retained_original_unchanged':True}))
    monkeypatch.setattr(m.artifacts,'download',download)
    with pytest.raises(ValueError):m.proof_gate()
