"""Preserved archive authority requires draft-only byte-for-byte round trips."""
import hashlib
import importlib
import json
from pathlib import Path

import pytest


def api():
    return importlib.import_module('simulation.stage_0_6_preserve_fixtures')


class Assets:
    def __init__(self):
        self.rows = {}
        self.uploads = 0
        self.damage = False
        self.fail_at = None

    def put(self, release, path):
        data = path.read_bytes()
        if path.name not in self.rows:
            if self.fail_at == self.uploads:
                raise OSError('injected transfer failure')
            self.uploads += 1
            self.rows[path.name] = dict(id=self.uploads, name=path.name, size=len(data),
                state='uploaded', digest='sha256:'+hashlib.sha256(data).hexdigest(), data=data)
        row = self.rows[path.name]
        return {k:v for k,v in row.items() if k!='data'}

    def download(self, asset, destination):
        row = next(r for r in self.rows.values() if r['id']==asset['id'])
        destination.write_bytes(row['data']+(b'bad' if self.damage else b''))


def fixture(tmp_path):
    data = b'abcdefghij'
    source = tmp_path/'archive.zip';source.write_bytes(data)
    identity = dict(key='source-7', archive_bytes=10,
        archive_sha256=hashlib.sha256(data).hexdigest(), source=dict(artifact_id=7))
    return source, identity


def test_split_round_trip_manifest_reconstructs_exact_original(tmp_path):
    source, identity = fixture(tmp_path); remote=Assets()
    result=api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'out',chunk_bytes=4)
    manifest=json.loads((tmp_path/'out/manifest.json').read_text())
    assert [p['bytes'] for p in manifest['parts']]==[4,4,2]
    assert [p['offset'] for p in manifest['parts']]==[0,4,8]
    assert manifest['verified_archive_sha256']==identity['archive_sha256']
    assert result['manifest_sha256']==hashlib.sha256((tmp_path/'out/manifest.json').read_bytes()).hexdigest()
    assert b''.join(remote.rows[p['name']]['data'] for p in manifest['parts'])==b'abcdefghij'
    assert source.read_bytes()==b'abcdefghij'


@pytest.mark.parametrize('problem',['public','hash','size','symlink','empty'])
def test_invalid_source_or_visibility_rejected_before_upload(tmp_path,problem):
    source,identity=fixture(tmp_path);release=dict(id=3,draft=problem!='public');remote=Assets()
    if problem=='hash':identity['archive_sha256']='0'*64
    elif problem=='size':identity['archive_bytes']=11
    elif problem=='symlink':
        link=tmp_path/'link.zip';link.symlink_to(source);source=link
    elif problem=='empty':source.write_bytes(b'');identity['archive_bytes']=0
    with pytest.raises((ValueError,FileExistsError)):
        api().preserve_file(remote,release,source,identity,tmp_path/'out',chunk_bytes=4)
    assert remote.uploads==0


def test_corrupt_round_trip_never_publishes_completed_manifest(tmp_path):
    source,identity=fixture(tmp_path);remote=Assets();remote.damage=True
    with pytest.raises(ValueError):
        api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'out',chunk_bytes=4)
    assert not (tmp_path/'out/manifest.json').exists()
    assert not any(name.endswith('manifest.json') for name in remote.rows)


def test_retry_reuses_uploaded_closed_parts_without_overwrite(tmp_path):
    source,identity=fixture(tmp_path);remote=Assets();remote.fail_at=1
    with pytest.raises(OSError):
        api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'first',chunk_bytes=4)
    original=remote.rows.copy();remote.fail_at=None
    api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'retry',chunk_bytes=4)
    assert remote.uploads==4  # Three data parts and final manifest, not a duplicate first part.
    assert remote.rows[next(iter(original))]==next(iter(original.values()))


def test_conflicting_existing_asset_is_not_replaced(tmp_path):
    source,identity=fixture(tmp_path);remote=Assets()
    api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'first',chunk_bytes=4)
    key=next(iter(remote.rows));remote.rows[key]['digest']='sha256:'+'0'*64
    before=remote.uploads
    with pytest.raises(ValueError):
        api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'retry',chunk_bytes=4)
    assert remote.uploads==before


def test_restore_from_manifest_rechecks_every_part_and_publishes_atomically(tmp_path):
    source,identity=fixture(tmp_path);remote=Assets()
    api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'out',chunk_bytes=4)
    manifest=json.loads((tmp_path/'out/manifest.json').read_text())
    destination=tmp_path/'restored.zip'
    result=api().restore_file(remote,manifest,destination,expected_bytes=10,
        expected_sha256=identity['archive_sha256'])
    assert destination.read_bytes()==b'abcdefghij'
    assert result['sha256']==identity['archive_sha256']
    with pytest.raises(FileExistsError):
        api().restore_file(remote,manifest,destination,expected_bytes=10,
            expected_sha256=identity['archive_sha256'])
    destination.unlink();remote.damage=True
    with pytest.raises(ValueError):
        api().restore_file(remote,manifest,destination,expected_bytes=10,
            expected_sha256=identity['archive_sha256'])
    assert not destination.exists()


@pytest.mark.parametrize('damage',['reorder','offset','duplicate','hash','release','repository'])
def test_restore_refuses_unbound_or_malformed_manifest(tmp_path,damage):
    source,identity=fixture(tmp_path);remote=Assets()
    api().preserve_file(remote,dict(id=3,draft=True),source,identity,tmp_path/'out',chunk_bytes=4)
    manifest=json.loads((tmp_path/'out/manifest.json').read_text())
    if damage=='reorder':manifest['parts'].reverse()
    elif damage=='offset':manifest['parts'][1]['offset']=0
    elif damage=='duplicate':manifest['parts'][1]['id']=manifest['parts'][0]['id']
    elif damage=='hash':manifest['original']['archive_sha256']='0'*64
    elif damage=='release':manifest['release_id']=0
    else:manifest['repository']='unrelated/repo'
    destination=tmp_path/'restored.zip'
    with pytest.raises(ValueError):
        api().restore_file(remote,manifest,destination,expected_bytes=10,
            expected_sha256=identity['archive_sha256'])
    assert not destination.exists()


@pytest.mark.parametrize('damage',['none','id','size','hash','expired','job'])
def test_source_producer_digest_size_and_expiry_are_all_bound(tmp_path,monkeypatch,damage):
    module=api();source,identity=fixture(tmp_path)
    identity['source']=dict(artifact_id=7,run_id=9,head_sha='a'*40,name='input',job='producer',workflow='workflow.yml')
    artifact=dict(id=7,size_in_bytes=10,name='input',expired=False,
        expires_at='2030-01-01T00:00:00Z',created_at='2026-01-01T00:00:05Z',
        digest='sha256:'+identity['archive_sha256'],workflow_run=dict(id=9,head_sha='a'*40))
    run=dict(id=9,head_sha='a'*40,path='workflow.yml')
    jobs=[dict(name='producer',conclusion='success',started_at='2026-01-01T00:00:00Z',completed_at='2026-01-01T00:00:10Z')]
    if damage=='id':artifact['id']=8
    elif damage=='size':artifact['size_in_bytes']=11
    elif damage=='hash':artifact['digest']='sha256:'+'0'*64
    elif damage=='expired':artifact['expires_at']='2020-01-01T00:00:00Z'
    elif damage=='job':jobs[0]['conclusion']='failure'
    monkeypatch.setattr(module.github,'_api',lambda path:artifact if '/artifacts/' in path else run)
    monkeypatch.setattr(module.github,'_pages',lambda *args:jobs)
    if damage=='none':assert module.authenticate_source(identity)['artifact']['id']==7
    else:
        with pytest.raises(ValueError):module.authenticate_source(identity)


def test_preservation_workflow_requires_real_smoke_before_large_copy():
    import yaml
    workflow=yaml.safe_load((Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-6-fixture-preservation.yml').read_text())
    assert set(workflow['on'])=={'push','workflow_dispatch'}
    assert workflow['on']['push']==dict(branches=['sol/durable-proof-map'],paths=['simulation/stage_0_6_fixture_preservation_request.json'])
    assert workflow['jobs']['preserve']['needs']=='smoke'
    assert workflow['permissions']==dict(contents='write',actions='read')
    assert workflow['concurrency']['cancel-in-progress'] is False
    for job in workflow['jobs'].values():
        for step in job['steps']:
            if 'uses' in step:assert len(step['uses'].split('@')[1])==40
    uploads=[s for s in workflow['jobs']['preserve']['steps'] if 'uses' in s and 'upload-artifact' in s['uses']]
    assert uploads[0]['if']=='always()'
    assert uploads[0]['with']['path']=='preservation-evidence/**/*.json'


def test_cli_timeout_and_download_byte_ceiling_are_real_process_bounds(tmp_path,monkeypatch):
    import os,subprocess
    executable=tmp_path/'gh'
    executable.write_text('#!/usr/bin/env python3\nimport sys,time\nif sys.argv[1]=="write":\n sys.stdout.write("x"*4096);sys.stdout.flush()\nelse: time.sleep(30)\n')
    executable.chmod(0o755)
    monkeypatch.setenv('PATH',str(tmp_path)+os.pathsep+os.environ['PATH'])
    with pytest.raises(subprocess.TimeoutExpired):api().command(['hang'],seconds=.1)
    output=tmp_path/'download'
    with output.open('xb') as target:
        with pytest.raises(RuntimeError):api().command(['write'],output=target,ceiling=20,seconds=5)
    assert output.stat().st_size<=21


def test_outer_timeout_stops_transfer_and_its_descendants(tmp_path):
    import os, signal, subprocess, sys

    executable=tmp_path/'gh';pids=tmp_path/'pids'
    executable.write_text('#!'+sys.executable+'\nimport os,subprocess,sys,time\n'
        'child=subprocess.Popen([sys.executable,"-c",'
        '"import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"])\n'
        'open(os.environ["PROBE_PIDS"],"w").write(str(os.getpid())+" "+str(child.pid))\n'
        'time.sleep(60)\n')
    executable.chmod(0o755)
    def running(pid):
        path=Path('/proc')/str(pid)/'stat'
        return path.exists() and path.read_text().split()[2] != 'Z'
    try:
        result=subprocess.run(['timeout','--signal=TERM','--kill-after=8s','2s',sys.executable,
            '-c','from simulation.stage_0_6_preserve_fixtures import command;command(["hang"])'],
            cwd=Path(__file__).resolve().parents[2],env=dict(os.environ,
                PATH=str(tmp_path)+os.pathsep+os.environ['PATH'],PROBE_PIDS=str(pids)),
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=12)
        assert result.returncode==124
        assert pids.exists(), 'probe must start the real transfer process'
        assert not any(running(int(pid)) for pid in pids.read_text().split())
    finally:
        if pids.exists():
            for pid in pids.read_text().split():
                if running(int(pid)):os.kill(int(pid),signal.SIGKILL)


def test_incomplete_starter_asset_uses_non_destructive_retry_name(tmp_path,monkeypatch):
    module=api();source,identity=fixture(tmp_path)
    rows=[dict(id=1,name=source.name,state='starter',size=0)]
    uploads=[]
    def remote(path):
        if '/assets?' in path:return rows
        return dict(id=3,draft=True,tag_name=module.TAG)
    def upload(arguments,**kwargs):
        uploads.append(arguments)
        path=Path(arguments[3])
        rows.append(dict(id=len(rows)+1,name=path.name,state='uploaded',size=path.stat().st_size,
            digest='sha256:'+module.sha(path)))
    monkeypatch.setattr(module.github,'_api',remote)
    monkeypatch.setattr(module,'command',upload)
    client=module.ReleaseAPI()
    result=client.put(dict(id=3,draft=True),source)
    assert result['name']==source.name+'.retry-1'
    assert result['state']=='uploaded' and rows[0]['state']=='starter'
    assert len(uploads)==1 and '--clobber' not in uploads[0]
    assert client.put(dict(id=3,draft=True),source)==result
    assert len(uploads)==1


def test_starter_retry_names_survive_manifest_roundtrip_and_restore(tmp_path,monkeypatch):
    module=api();source,identity=fixture(tmp_path);remote=Assets()
    prefix=identity['key']+'-'+identity['archive_sha256'][:16]
    for name in (prefix+'.part-0000',prefix+'.manifest.json'):
        remote.rows[name]=dict(id=len(remote.rows)+1,name=name,state='starter',size=0,data=b'')
    remote.uploads=2
    client=module.ReleaseAPI()
    monkeypatch.setattr(module.github,'_api',lambda path:list(remote.rows.values()) if '/assets?' in path
        else dict(id=3,draft=True,tag_name=module.TAG))
    monkeypatch.setattr(module,'command',lambda args,**kw:remote.put(dict(id=3,draft=True),Path(args[3])))
    monkeypatch.setattr(client,'download',remote.download)
    result=module.preserve_file(client,dict(id=3,draft=True),source,identity,tmp_path/'out',chunk_bytes=4)
    manifest=json.loads((tmp_path/'out/manifest.json').read_text())
    assert manifest['parts'][0]['name'].endswith('.retry-1')
    assert result['manifest_name'].endswith('.retry-1')
    module.restore_file(client,manifest,tmp_path/'restored',expected_bytes=10,
        expected_sha256=identity['archive_sha256'])
    assert (tmp_path/'restored').read_bytes()==source.read_bytes()
    count=remote.uploads
    module.preserve_file(client,dict(id=3,draft=True),source,identity,tmp_path/'retry',chunk_bytes=4)
    assert remote.uploads==count


def test_starter_retry_limit_fails_closed_without_deleting_assets(tmp_path,monkeypatch):
    module=api();source,identity=fixture(tmp_path);commands=[]
    rows=[dict(id=n+1,name=source.name+(f'.retry-{n}' if n else ''),state='starter',size=0)
        for n in range(module.RETRY_SLOTS+1)]
    monkeypatch.setattr(module.github,'_api',lambda path:rows if '/assets?' in path
        else dict(id=3,draft=True,tag_name=module.TAG))
    monkeypatch.setattr(module,'command',lambda *args,**kw:commands.append(args))
    with pytest.raises(ValueError,match='retry slots exhausted'):
        module.ReleaseAPI().put(dict(id=3,draft=True),source)
    assert not commands and len(rows)==module.RETRY_SLOTS+1
