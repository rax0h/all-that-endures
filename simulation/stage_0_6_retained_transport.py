"""Bounded signed download for the pinned Stage 0.6 retained fixture.

Transport alone grants no original candidate or acceptance authority. Callers must
validate the staged source, acceptance, and retention receipts separately.
"""
import hashlib
from pathlib import Path
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from simulation import checkpoint_artifacts
from simulation.stage_0_6_retained_archive import extract_retained
from simulation.stage_0_6_retained_producer import PIN, inspect_retained_producer


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _signed_url(artifact_id):
    """Request a GitHub-signed redirect without forwarding the bearer token."""
    from os import environ
    request = urllib.request.Request(
        f'https://api.github.com/repos/{checkpoint_artifacts.REPOSITORY}/actions/artifacts/{artifact_id}/zip',
        headers={'Authorization': 'Bearer ' + environ['GH_TOKEN']})
    try:
        response = urllib.request.build_opener(_NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code != 302:
            raise
        redirect = error.headers.get('Location')
    else:
        response.close()
        raise ValueError('expected GitHub signed artifact redirect')
    if not isinstance(redirect, str):
        raise ValueError('missing signed artifact URL')
    parsed = urllib.parse.urlsplit(redirect)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError('unsafe signed artifact URL')
    return redirect


def _stream_archive(url, archive, *, archive_sha256, archive_bytes):
    """Download with a hard byte ceiling, hashing as bytes arrive."""
    digest = hashlib.sha256()
    copied = 0
    with urllib.request.urlopen(url, timeout=120) as response, Path(archive).open('xb') as target:
        if urllib.parse.urlsplit(response.geturl()).scheme != 'https':
            raise ValueError('signed artifact redirected to insecure URL')
        while True:
            chunk = response.read(min(1024 * 1024, archive_bytes - copied + 1))
            if not chunk:
                break
            copied += len(chunk)
            if copied > archive_bytes:
                raise ValueError('retained download exceeds pinned archive size')
            digest.update(chunk)
            target.write(chunk)
    if copied != archive_bytes or digest.hexdigest() != archive_sha256:
        raise ValueError('retained download checksum or size differs')
    return copied


def download_retained(destination, *, database_bytes, metadata_max_bytes):
    """Authenticate live producer, stream pinned ZIP, and stage exact six members."""
    started = time.monotonic()
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    proof = inspect_retained_producer()
    if (proof['artifact_id'] != PIN.artifact_id or proof['archive_sha256'] != PIN.archive_sha256
            or proof['archive_bytes'] != PIN.archive_bytes):
        raise ValueError('producer authentication did not match immutable pin')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.stage06-download-', dir=destination.parent) as directory:
        archive = Path(directory) / 'retained.zip'
        _stream_archive(_signed_url(PIN.artifact_id), archive,
                        archive_sha256=PIN.archive_sha256, archive_bytes=PIN.archive_bytes)
        extracted = extract_retained(archive, destination,
                                    archive_sha256=PIN.archive_sha256,
                                    archive_bytes=PIN.archive_bytes,
                                    database_bytes=database_bytes,
                                    metadata_max_bytes=metadata_max_bytes)
    return dict(producer=proof, extraction=extracted, download_seconds=time.monotonic()-started)
