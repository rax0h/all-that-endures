"""A completed job alone cannot authenticate a retained publication."""
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=ROOT/'docs/performance/stage-0-6-current/proof-source-audit-repair'


@pytest.mark.parametrize('artifact_id',[None,14267625292,14260383532,14261110486,'duplicate-publication'])
def test_retained_proof_input_requires_unique_successful_publication(tmp_path,artifact_id):
    with zipfile.ZipFile(PACKAGE/'failure.zip') as archive:archive.extractall(tmp_path)
    if artifact_id is not None:
        path=tmp_path/'metadata.json';raw=json.loads(path.read_text())
        if artifact_id=='duplicate-publication':
            raw['jobs']['jobs'].append(next(j for j in raw['jobs']['jobs'] if j['name']=='after-digest'))
        else:
            artifact=next(a for a in raw['artifacts']['artifacts'] if a['id']==artifact_id)
            job_name='after-digest' if artifact_id==14267625292 else 'rebase'
            job=next(j for j in raw['jobs']['jobs'] if j['name']==job_name)
            artifact['created_at']=job['started_at']
        path.write_text(json.dumps(raw))
    result=subprocess.run([sys.executable,str(PACKAGE/'authenticate-retained.py'),str(ROOT),str(tmp_path)],capture_output=True,text=True)
    if artifact_id is None:
        assert result.returncode==0,result.stderr
        assert json.loads(result.stdout)['new_engine_admitted'] is False
    else:
        assert result.returncode!=0,'invalid or ambiguous artifact publication was accepted'
