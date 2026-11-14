"""Retain authenticated original ZIP bytes; never open or regenerate the world."""
import hashlib
import os
from pathlib import Path
import shutil
import urllib.error
import urllib.parse
import urllib.request

from simulation import checkpoint_artifacts as artifacts
from simulation import construction_mature_continuation_stages as stages
from simulation import continuation_receipts as r


def copy_archive(stream, target, expected_bytes, expected_sha256):
    target = Path(target)
    pending = target.with_suffix(target.suffix+'.partial')
    count, digest = 0, hashlib.sha256()
    # A killed process may leave .partial, which the upload glob excludes.
    # Publication creates a new name atomically, never replacing retained bytes.
    with pending.open('xb') as output:
        try:
            while chunk := stream.read(min(1024**2, expected_bytes-count+1)):
                count += len(chunk)
                if count > expected_bytes: raise ValueError('archive exceeds pinned size')
                digest.update(chunk)
                output.write(chunk)
            if count != expected_bytes or digest.hexdigest() != expected_sha256:
                raise ValueError('archive checksum/size mismatch')
        except BaseException:
            output.close()
            pending.unlink()
            raise
    try:
        os.link(pending, target)
    finally:
        pending.unlink()


def retain_archive(ref, directory):
    metadata = stages.authenticate_ref(ref, max_archive_bytes=ref.archive_bytes)
    evidence = dict(original=ref.to_dict(), file=f'{ref.artifact_id}.zip', metadata=metadata,
        run=artifacts._api(f'/actions/runs/{ref.run_id}'),
        jobs=artifacts._pages(f'/actions/runs/{ref.run_id}/jobs?filter=all', 'jobs'))
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    request = urllib.request.Request(
        f'https://api.github.com/repos/{artifacts.REPOSITORY}/actions/artifacts/{ref.artifact_id}/zip',
        headers={'Authorization': 'Bearer '+os.environ['GH_TOKEN']})
    try:
        urllib.request.build_opener(NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code != 302: raise
        redirect = error.headers['Location']
    else:
        raise ValueError('expected signed archive redirect')
    parsed = urllib.parse.urlsplit(redirect)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('unsafe archive redirect')
    target = directory/f'{ref.artifact_id}.zip'
    # Send no GitHub credentials to the signed cross-origin URL.
    with urllib.request.urlopen(redirect, timeout=120) as stream:
        copy_archive(stream, target, ref.archive_bytes, ref.archive_sha256)
    r.publish_receipt(directory/f'{ref.artifact_id}.json', evidence)
    return evidence


def main():
    launch = r.load_receipt('simulation/stage_0_5_save1002_preflight.json')
    refs = {role: r.ArtifactRef.from_dict(launch['inputs'][role])
            for role in ('candidate', 'previous')}
    directory = Path('retained-mature-inputs')
    directory.mkdir(exist_ok=False)
    if shutil.disk_usage(directory).free < sum(ref.archive_bytes for ref in refs.values()) + 1024**3:
        raise ValueError('insufficient archive retention space')
    manifest = dict(schema='ate-retained-mature-inputs/1', status='partial',
        candidate_database=launch['candidate_database'], inputs={},
        producer=dict(run_id=int(os.environ['GITHUB_RUN_ID']), head=os.environ['GITHUB_SHA']),
        contract='Original ZIP bytes, original producer provenance. Mirror is transport only; no new simulation acceptance.')
    try:
        for role, ref in refs.items():
            manifest['inputs'][role] = retain_archive(ref, directory)
        manifest['status'] = 'complete'
    except Exception as exc:
        manifest['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        r.publish_receipt(directory/'manifest.json', manifest)


if __name__ == '__main__': main()
