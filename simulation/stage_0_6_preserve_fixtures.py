"""Preserve original fixture ZIPs as authenticated, draft-only release assets.

Transport completion never certifies a World or bypasses source/acceptance checks.
No SQLite extraction, simulation, public release, asset overwrite or deletion.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import tempfile

from simulation import checkpoint_artifacts as github
from simulation.stage_0_6_retained_producer import PIN, inspect_retained_producer
from simulation.stage_0_6_retained_transport import _signed_url, _stream_archive

REPOSITORY = 'rax0h/all-that-endures'
TAG = 'ate-stage-0-6-fixtures-2026-11'
CHUNK = 512 * 1024**2
RESERVE = 2 * 1024**3
RETRY_SLOTS = 8


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path, value):
    path = Path(path)
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')
    temporary.replace(path)


def check_asset(asset, name, size, digest):
    if (type(asset.get('id')) is not int or asset['id'] < 1
            or asset.get('name') not in [name]+[name+f'.retry-{n}' for n in range(1,RETRY_SLOTS+1)]
            or asset.get('size') != size
            or asset.get('state') != 'uploaded'
            or asset.get('digest') not in (None, 'sha256:'+digest)):
        raise ValueError('release asset identity, size or digest differs')


def preserve_file(api, release, source, identity, output, *, chunk_bytes=CHUNK):
    source, output = Path(source), Path(output)
    if type(release) is not dict or type(identity) is not dict:
        raise ValueError('invalid preservation identity')
    size, digest, key = (identity[k] for k in ('archive_bytes','archive_sha256','key'))
    if (release.get('draft') is not True or type(release.get('id')) is not int or release['id'] < 1
            or type(size) is not int or size < 1
            or type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest)
            or type(key) is not str or not re.fullmatch('[a-z0-9-]{1,64}', key)
            or type(chunk_bytes) is not int or not 1 <= chunk_bytes <= CHUNK
            or source.is_symlink() or not source.is_file()
            or source.stat().st_size != size or sha(source) != digest):
        raise ValueError('draft, archive or split contract differs')
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema='ate-preserved-fixture/1', repository=REPOSITORY,
        release_id=release['id'], original=identity, parts=[])
    prefix = key+'-'+digest[:16]
    round_trip = hashlib.sha256()
    original = hashlib.sha256()
    offset = 0
    with tempfile.TemporaryDirectory(prefix='.preserve-parts-', dir=output) as temporary:
        with source.open('rb') as stream:
            while offset < size:
                name = prefix+f'.part-{len(manifest["parts"]):04d}'
                part, verified = Path(temporary)/name, Path(temporary)/'verified'
                wanted = min(chunk_bytes, size-offset)
                with part.open('xb') as target:
                    remaining = wanted
                    while remaining:
                        chunk = stream.read(min(1024**2, remaining))
                        if not chunk:
                            raise ValueError('source truncated while splitting')
                        target.write(chunk); original.update(chunk); remaining -= len(chunk)
                part_sha = sha(part)
                asset = api.put(release, part)
                check_asset(asset, name, wanted, part_sha)
                api.download(asset, verified)
                if (verified.is_symlink() or verified.stat().st_size != wanted
                        or sha(verified) != part_sha):
                    raise ValueError('downloaded release asset differs from original part')
                with verified.open('rb') as downloaded:
                    while chunk := downloaded.read(1024**2):
                        round_trip.update(chunk)
                manifest['parts'].append(dict(id=asset['id'], name=asset['name'], bytes=wanted,
                    sha256=part_sha, offset=offset))
                offset += wanted
                record(output/'progress.json', dict(status='running', **manifest))
                part.unlink(); verified.unlink()
            if stream.read(1) or original.hexdigest() != digest or round_trip.hexdigest() != digest:
                raise ValueError('complete original/round-trip archive digest differs')
        manifest['verified_archive_sha256'] = round_trip.hexdigest()
        record(output/'manifest.json', manifest)
        publish = Path(temporary)/(prefix+'.manifest.json')
        shutil.copyfile(output/'manifest.json', publish)
        manifest_sha = sha(publish)
        asset = api.put(release, publish)
        check_asset(asset, publish.name, publish.stat().st_size, manifest_sha)
        api.download(asset, verified)
        if verified.stat().st_size != publish.stat().st_size or sha(verified) != manifest_sha:
            raise ValueError('published manifest round trip differs')
    result = dict(status='complete', release_id=release['id'], draft=True,
        manifest_id=asset['id'], manifest_name=asset['name'], manifest_sha256=manifest_sha,
        archive_bytes=size, archive_sha256=digest, parts=len(manifest['parts']))
    record(output/'complete.json', result)
    return result


def restore_file(api, manifest, destination, *, expected_bytes, expected_sha256):
    """Restore from pinned asset IDs; the caller supplies independent archive authority."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if (type(manifest) is not dict or manifest.get('schema') != 'ate-preserved-fixture/1'
            or manifest.get('repository') != REPOSITORY
            or type(manifest.get('release_id')) is not int or manifest['release_id'] < 1
            or type(expected_bytes) is not int or expected_bytes < 1
            or manifest.get('original', {}).get('archive_bytes') != expected_bytes
            or manifest.get('original', {}).get('archive_sha256') != expected_sha256
            or manifest.get('verified_archive_sha256') != expected_sha256
            or not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256)):
        raise ValueError('restore manifest differs from independent archive authority')
    parts = manifest.get('parts')
    if type(parts) is not list or not 1 <= len(parts) <= 1000:
        raise ValueError('invalid restored part inventory')
    offset = 0
    identifiers, names = set(), set()
    for part in parts:
        if (type(part) is not dict or type(part.get('id')) is not int or part['id'] < 1
                or part['id'] in identifiers or type(part.get('name')) is not str
                or part['name'] in names or part.get('offset') != offset
                or type(part.get('bytes')) is not int or not 1 <= part['bytes'] <= CHUNK
                or type(part.get('sha256')) is not str or not re.fullmatch('[0-9a-f]{64}', part['sha256'])):
            raise ValueError('restored part order/identity/size differs')
        offset += part['bytes']; identifiers.add(part['id']); names.add(part['name'])
    if offset != expected_bytes:
        raise ValueError('restored total size differs')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.restore-parts-', dir=destination.parent) as temporary:
        staged, downloaded = Path(temporary)/'archive', Path(temporary)/'part'
        digest = hashlib.sha256()
        with staged.open('xb') as target:
            for part in parts:
                api.download(dict(id=part['id'],name=part['name'],size=part['bytes']), downloaded)
                if (downloaded.is_symlink() or downloaded.stat().st_size != part['bytes']
                        or sha(downloaded) != part['sha256']):
                    raise ValueError('restored asset bytes differ')
                with downloaded.open('rb') as stream:
                    while chunk := stream.read(1024**2):
                        target.write(chunk); digest.update(chunk)
                downloaded.unlink()
        if staged.stat().st_size != expected_bytes or digest.hexdigest() != expected_sha256:
            raise ValueError('restored complete archive differs')
        os.link(staged, destination)  # Atomic no-overwrite publication on this filesystem.
    return dict(bytes=expected_bytes, sha256=expected_sha256, status='complete')


def command(arguments, *, output=None, ceiling=None, seconds=600):
    """Fixed CLI arguments only; credentials stay in the runner environment."""
    def bounds():
        if ceiling is not None:
            resource.setrlimit(resource.RLIMIT_FSIZE, (ceiling+1, ceiling+1))
    def terminate(signum, frame):
        # GNU timeout signals this Python process; gh owns a separate session.
        # Turn that signal into stack unwinding so its whole transfer group dies.
        raise SystemExit(128+signum)
    previous=signal.signal(signal.SIGTERM,terminate)
    proc=None
    try:
        with tempfile.TemporaryFile() as errors:
            try:
                proc = subprocess.Popen(['gh', *arguments], stdout=output or subprocess.DEVNULL,
                    stderr=errors, start_new_session=True, preexec_fn=bounds if ceiling is not None else None)
                code = proc.wait(timeout=seconds)
            except BaseException:
                if proc is not None:
                    try: os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError: pass
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired: pass
                    # A reaped gh parent does not prove all descendants exited.
                    try: os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    proc.wait(timeout=5)
                raise
            if ceiling is not None and os.fstat(output.fileno()).st_size>ceiling:
                raise RuntimeError('GitHub CLI output exceeds its byte allowance')
            if code:
                # Do not echo signed redirects, HTTP authorization or command output.
                raise RuntimeError('GitHub CLI operation failed, exit '+str(code))
    finally:signal.signal(signal.SIGTERM,previous)


class ReleaseAPI:
    def listing(self,path):
        rows=[]
        for page in range(1,101):
            batch=github._api(path+f'?per_page=100&page={page}')
            rows.extend(batch)
            if len(batch)<100:return rows
        raise ValueError('release inventory exceeds bounded pagination')

    def draft(self):
        matches = [r for r in self.listing('/releases') if r.get('tag_name') == TAG]
        if not matches:
            command(['release','create',TAG,'--repo',REPOSITORY,'--draft',
                '--target',os.environ['GITHUB_SHA'],'--title','Stage0.6 authenticated fixture archive',
                '--notes','Private draft transport archive. Do not publish or delete; original byte/provenance manifests remain authoritative.'])
            matches = [r for r in self.listing('/releases') if r.get('tag_name') == TAG]
        if len(matches) != 1 or matches[0].get('draft') is not True:
            raise ValueError('preservation requires one private draft release')
        return matches[0]

    def put(self, release, path):
        current = github._api(f'/releases/{release["id"]}')
        if current.get('draft') is not True or current.get('tag_name') != TAG:
            raise ValueError('draft release visibility changed')
        for attempt in range(RETRY_SLOTS+1):
            name=path.name+(f'.retry-{attempt}' if attempt else '')
            def find():
                return [a for a in self.listing(f'/releases/{release["id"]}/assets')
                        if a.get('name') == name]
            matches=find()
            if not matches:
                with tempfile.TemporaryDirectory(prefix='.asset-retry-',dir=path.parent) as directory:
                    upload=Path(directory)/name
                    os.link(path,upload)
                    command(['release','upload',TAG,str(upload),'--repo',REPOSITORY])
                matches=find()
            if len(matches)!=1:raise ValueError('release asset name is missing or ambiguous')
            if matches[0].get('state')=='starter':continue
            # Uploaded conflicts are returned for strict size/digest checks;
            # only incomplete starter assets permit a non-destructive new name.
            return matches[0]
        raise ValueError('incomplete upload retry slots exhausted; retain existing assets and review a new archive namespace')

    def download(self, asset, destination):
        with Path(destination).open('xb') as output:
            command(['api',f'/repos/{REPOSITORY}/releases/assets/{asset["id"]}',
                '-H','Accept: application/octet-stream'],output=output,ceiling=asset['size'])


def sources(root):
    small = json.loads((Path(root)/'docs/performance/stage-0-6-current/small-operation-profile/input.json').read_text())['data_ref']
    return [dict(key='small-year1', archive_bytes=small['archive_bytes'],
        archive_sha256=small['archive_sha256'], source=dict(artifact_id=small['artifact_id'],
            run_id=small['run_id'], head_sha=small['head_sha'], name=small['name'],
            job=small['job'], workflow='.github/workflows/stage-0-6-resumable-proof-genesis.yml')),
        dict(key='mature-year1001', archive_bytes=PIN.archive_bytes, archive_sha256=PIN.archive_sha256,
            source=dict(artifact_id=PIN.artifact_id,run_id=PIN.run_id,head_sha=PIN.head_sha,
                name=PIN.artifact_name,job=PIN.job,workflow=PIN.workflow))]


def authenticate_source(value):
    source=value['source']
    artifact=github._api(f'/actions/artifacts/{source["artifact_id"]}')
    run=github._api(f'/actions/runs/{source["run_id"]}')
    jobs=github._pages(f'/actions/runs/{source["run_id"]}/jobs?filter=all','jobs')
    expected=github.authenticate(artifact,run,jobs,run_id=source['run_id'],
        workflow_sha=source['head_sha'],name=source['name'],job=source['job'],workflow_path=source['workflow'])
    expires=datetime.fromisoformat(artifact['expires_at'].replace('Z','+00:00'))
    if (artifact['id']!=source['artifact_id'] or artifact['size_in_bytes']!=value['archive_bytes']
            or expected!=value['archive_sha256'] or expires<=datetime.now(timezone.utc)):
        raise ValueError('fixture archive/expiry differs from original pin')
    if source['artifact_id']==PIN.artifact_id:
        inspect_retained_producer()
    return dict(artifact=artifact,producer=run,jobs=jobs)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['smoke','preserve','restore'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--expected-sha256')
    parser.add_argument('--expected-bytes',type=int)
    args=parser.parse_args(); root=Path.cwd().resolve();out=args.output.resolve()
    if os.environ.get('GITHUB_REPOSITORY',REPOSITORY)!=REPOSITORY:
        raise ValueError('preservation is restricted to the authorized repository')
    client=ReleaseAPI()
    if args.mode=='restore':
        if not args.manifest or not args.expected_sha256 or not args.expected_bytes:
            parser.error('restore requires manifest and independent expected archive hash/size')
        result=restore_file(client,json.loads(args.manifest.read_text()),out,
            expected_bytes=args.expected_bytes,expected_sha256=args.expected_sha256)
        print(json.dumps(result));return
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    release=client.draft()
    if args.mode=='smoke':
        source=out/'smoke.zip';source.write_bytes(b'ATE fixture transport smoke v1\n'*100)
        identity=dict(key='transport-smoke-v1',archive_bytes=source.stat().st_size,
            archive_sha256=sha(source),source=dict(kind='synthetic-transport-smoke'))
        result=preserve_file(client,release,source,identity,out/'roundtrip',chunk_bytes=1024)
        restored=restore_file(client,json.loads((out/'roundtrip/manifest.json').read_text()),out/'restored.zip',
            expected_bytes=identity['archive_bytes'],expected_sha256=identity['archive_sha256'])
        result['restored']=restored
        record(out/'result.json',result);return
    completed=[]
    for value in sources(root):
        if shutil.disk_usage(out).free<value['archive_bytes']+2*CHUNK+RESERVE:
            raise ValueError('insufficient bounded preservation disk headroom')
        proof=authenticate_source(value)
        record(out/(value['key']+'-producer.json'),proof)
        record(out/'result.json',dict(status='downloading',active=value['key'],completed=completed))
        with tempfile.TemporaryDirectory(prefix='.original-zip-',dir=out) as directory:
            archive=Path(directory)/'original.zip'
            _stream_archive(_signed_url(value['source']['artifact_id']),archive,
                archive_sha256=value['archive_sha256'],archive_bytes=value['archive_bytes'])
            result=preserve_file(client,release,archive,value,out/value['key'])
            archive.unlink()  # Disposable downloaded copy; the authenticated original is untouched.
            result['restored']=restore_file(client,json.loads((out/value['key']/'manifest.json').read_text()),
                Path(directory)/'restored.zip',expected_bytes=value['archive_bytes'],
                expected_sha256=value['archive_sha256'])
            completed.append(result)
            record(out/'result.json',dict(status='running',completed=completed))
    current=github._api(f'/releases/{release["id"]}')
    if current.get('draft') is not True or current.get('tag_name') != TAG:
        raise ValueError('draft release visibility changed before completion')
    record(out/'result.json',dict(status='complete',completed=completed,draft=True,release_id=release['id']))


if __name__=='__main__': main()
