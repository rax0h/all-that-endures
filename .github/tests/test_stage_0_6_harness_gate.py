"""Expensive jobs require the complete quick harness before transport/compute."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def workflow(name):
    return yaml.safe_load((ROOT/'.github/workflows'/name).read_text())


def commands(job):
    return '\n'.join(step.get('run', '') for step in job['steps'])


def test_full_engine_jobs_require_quick_harness_and_skip_harness_only_pushes():
    value=workflow('stage-0-5-proof-map-validation.yml')
    gate=value['jobs']['harness']
    assert gate['timeout-minutes']==15
    assert '10m python -m pytest -q .github/tests ' in commands(gate)
    assert any(s.get('if')=='always()' and 'upload-artifact@' in s.get('uses','') for s in gate['steps'])
    assert '.github/tests/**' in value['on']['push']['paths']
    for name in ('proof-map', 'full-suite'):
        job=value['jobs'][name]
        assert set(job['needs'])=={'harness','mature-genesis-request'}
        expected="needs.mature-genesis-request.outputs.engine_changed == 'true'"
        if name=='proof-map':expected+=" || needs.mature-genesis-request.outputs.proof_changed == 'true'"
        assert job['if']==expected
        assert not job.get('continue-on-error',False)
    assert value['jobs']['mature-genesis']['if'] is False
    steps=gate['steps']
    smoke=next(n for n,s in enumerate(steps) if 'preserved_transport --key small-year1' in s.get('run',''))
    tests=next(n for n,s in enumerate(steps) if 'pytest -q .github/tests ' in s.get('run',''))
    assert tests<smoke


def test_complete_harness_precedes_every_mature_source_transport():
    for name, jobs in (
        ('stage-0-6-resumable-proof-genesis.yml', ('gate',)),
        ('stage-0-6-current-mature-performance.yml', ('measure','retain')),
        ('stage-0-6-proof-mature-preflight.yml', ('inventory',)),
        ('stage-0-6-fixture-preservation.yml', ('smoke',)),
    ):
        value=workflow(name)
        if name=='stage-0-6-resumable-proof-genesis.yml':
            assert value['on']['push']['paths']==['simulation/stage_0_6_genesis_resume_request.json']
        for key in jobs:
            steps=value['jobs'][key]['steps']
            tests=[n for n,s in enumerate(steps) if 'python -m pytest -q .github/tests ' in s.get('run','')]
            assert len(tests)==1, (name,key)
            assert '10m ' in steps[tests[0]]['run']
            transport=[n for n,s in enumerate(steps) if any(fragment in s.get('run','') for fragment in (
                'genesis_resume gate ', 'benchmark_launch prepare ', 'proof_mature_preflight run ',
                'preserve_fixtures smoke '))]
            assert transport and tests[0]<min(transport), (name,key)
            assert not steps[tests[0]].get('continue-on-error',False)
