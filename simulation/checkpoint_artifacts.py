"""Authenticated GitHub artifact transport for checkpoint validation jobs."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPOSITORY = 'rax0h/all-that-endures'


def authenticate(artifact, run, jobs, *, run_id, workflow_sha, name, job, workflow_path):
    digest = artifact.get('digest', '')
    origin = artifact.get('workflow_run', {})
    if (artifact.get('name') != name or artifact.get('expired') is not False
            or origin.get('id') != run_id or origin.get('head_sha') != workflow_sha
            or run.get('id') != run_id or run.get('head_sha') != workflow_sha
            or run.get('path') != workflow_path
            or not re.fullmatch('sha256:[0-9a-f]{64}', digest)):
        raise ValueError('artifact run/workflow/commit/name/digest mismatch')
    created = artifact.get('created_at', '')
    producers = [row for row in jobs if row.get('name') == job
        and row.get('conclusion') == 'success' and row.get('started_at') and row.get('completed_at')
        and row['started_at'] <= created <= row['completed_at']]
    if len(producers) != 1:
        raise ValueError('artifact lacks exactly one successful producing job')
    return digest.removeprefix('sha256:')


def extract(archive, destination, members):
    """Exact regular-file ZIP only; reject all extras before creating output."""
    destination = Path(destination)
    if destination.exists(): raise FileExistsError(destination)
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        if (len(entries) != len(members) or {entry.filename for entry in entries} != set(members)
                or any(Path(name).name != name or name in ('.', '..') for name in members)
                or any(entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16) for entry in entries)
                or sum(entry.file_size for entry in entries) > 100*1024**3):
            raise ValueError('unexpected or unsafe artifact members')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.artifact-', dir=destination.parent) as directory:
            pending = Path(directory)/'files'; pending.mkdir()
            for entry in entries:
                with zipped.open(entry) as source, (pending/entry.filename).open('xb') as target:
                    shutil.copyfileobj(source, target, length=1024*1024)
            destination.mkdir()
            try:
                for entry in entries: os.link(pending/entry.filename, destination/entry.filename)
            except BaseException:
                shutil.rmtree(destination)
                raise


def _api(path):
    request = urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+path,
        headers={'Authorization': 'Bearer '+os.environ['GH_TOKEN'],
                 'Accept':'application/vnd.github+json', 'X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _pages(path, key):
    rows = []
    for page in range(1, 101):
        result = _api(path+('&' if '?' in path else '?')+f'per_page=100&page={page}')[key]
        rows.extend(result)
        if len(result) < 100: return rows
    raise ValueError('artifact/job pagination limit exceeded')


def download(destination, *, run_id, workflow_sha, name, job, workflow_path, members,
             artifact_id=None, expected_digest=None):
    """Authenticate the producer and ZIP digest, without forwarding credentials."""
    started = time.monotonic()
    if Path(destination).exists(): raise FileExistsError(destination)
    artifacts = _pages(f'/actions/runs/{run_id}/artifacts', 'artifacts')
    matches = [a for a in artifacts if a.get('name') == name
               and (artifact_id is None or a.get('id') == artifact_id)]
    if len(matches) != 1: raise ValueError('artifact name/id is missing or ambiguous')
    artifact = matches[0]
    run = _api(f'/actions/runs/{run_id}')
    jobs = _pages(f'/actions/runs/{run_id}/jobs?filter=all', 'jobs')
    digest = authenticate(artifact, run, jobs, run_id=run_id, workflow_sha=workflow_sha,
                          name=name, job=job, workflow_path=workflow_path)
    if expected_digest is not None and digest != expected_digest:
        raise ValueError('artifact differs from pinned digest')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    request = urllib.request.Request(
        f'https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip',
        headers={'Authorization':'Bearer '+os.environ['GH_TOKEN']})
    try:
        urllib.request.build_opener(NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code != 302: raise
        redirect = error.headers['Location']
    else:
        raise ValueError('expected signed artifact redirect')
    parsed = urllib.parse.urlsplit(redirect)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('unsafe artifact redirect')
    destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.download-', dir=destination.parent) as directory:
        archive = Path(directory)/'artifact.zip'
        # No Authorization header on the signed cross-origin request.
        with urllib.request.urlopen(redirect, timeout=120) as response, archive.open('xb') as target:
            shutil.copyfileobj(response, target, length=1024*1024)
        with archive.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != digest or archive.stat().st_size != artifact['size_in_bytes']:
            raise ValueError('artifact archive checksum/size mismatch')
        extract(archive, destination, members)
    proof = {'artifact_id':artifact['id'], 'run_id':run_id, 'workflow_sha':workflow_sha,
             'archive_sha256':digest, 'archive_bytes':artifact['size_in_bytes'],
             'producer_job':job, 'seconds':time.monotonic()-started}
    print(json.dumps({'artifact_download_verified':proof}), flush=True)
    return proof


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--workflow-sha', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--workflow-path', default='.github/workflows/checkpointed-upgrade-validation.yml')
    parser.add_argument('--members', nargs='+', required=True)
    parser.add_argument('--artifact-id', type=int)
    parser.add_argument('--expected-digest')
    args = parser.parse_args()
    download(**vars(args))


if __name__ == '__main__': main()
