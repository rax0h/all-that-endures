"""Authenticate the pinned Stage 0.6 retained transport producer.

This establishes only GitHub artifact provenance. It does not validate ZIP bytes,
accepted-year authority, source bindings, or grant permission to run a benchmark.
"""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RetainedPin:
    run_id: int = 40760930962
    artifact_id: int = 12849181590
    head_sha: str = 'b524bbe2ff1b697f79d7fcbf3c8a3b7d9c82efdf'
    branch: str = 'sol/durable-proof-map'
    workflow: str = '.github/workflows/stage-0-6-current-mature-performance.yml'
    job: str = 'retain'
    artifact_name: str = 'stage-0-6-authenticated-input-b524bbe2ff1b697f79d7fcbf3c8a3b7d9c82efdf'
    archive_sha256: str = '4f040569fb91cef482bd5706230bcada058788a747278b99df7cca2c137d373f'
    archive_bytes: int = 4419106896


PIN = RetainedPin()


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError('missing GitHub timestamp')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('invalid GitHub timestamp') from error
    if result.tzinfo is None:
        raise ValueError('unqualified GitHub timestamp')
    return result.astimezone(timezone.utc)


def authenticate_retained_producer(artifact, run, jobs, *, now=None, pin=PIN):
    """Require one successful exact producer and unexpired pinned artifact metadata."""
    if not isinstance(artifact, dict) or not isinstance(run, dict) or not isinstance(jobs, list):
        raise ValueError('missing producer metadata')
    if (run.get('id') != pin.run_id or run.get('head_sha') != pin.head_sha
            or run.get('head_branch') != pin.branch or run.get('path') != pin.workflow
            or run.get('event') != 'push' or run.get('run_attempt') != 1
            or run.get('status') != 'completed' or run.get('conclusion') != 'success'):
        raise ValueError('retained producing run differs from pin')
    origin = artifact.get('workflow_run')
    if (artifact.get('id') != pin.artifact_id or artifact.get('name') != pin.artifact_name
            or artifact.get('expired') is not False
            or type(artifact.get('size_in_bytes')) is not int
            or artifact['size_in_bytes'] != pin.archive_bytes
            or artifact.get('digest') != 'sha256:' + pin.archive_sha256
            or not isinstance(origin, dict) or origin.get('id') != pin.run_id
            or origin.get('head_sha') != pin.head_sha or origin.get('head_branch') != pin.branch):
        raise ValueError('retained artifact identity differs from pin')
    created = _timestamp(artifact.get('created_at'))
    expires = _timestamp(artifact.get('expires_at'))
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError('unqualified current time')
    if not created < expires or not now.astimezone(timezone.utc) < expires:
        raise ValueError('retained artifact has expired')
    matching = [job for job in jobs if isinstance(job, dict)
                and job.get('name') == pin.job
                and job.get('head_sha') == pin.head_sha
                and job.get('status') == 'completed'
                and job.get('conclusion') == 'success']
    if len(matching) != 1:
        raise ValueError('retained artifact lacks unique successful producer job')
    job = matching[0]
    if not _timestamp(job.get('started_at')) <= created <= _timestamp(job.get('completed_at')):
        raise ValueError('retained artifact was not created within producing job')
    return {'artifact_id': pin.artifact_id, 'run_id': pin.run_id,
            'workflow_sha': pin.head_sha, 'producer_job': pin.job,
            'archive_sha256': pin.archive_sha256, 'archive_bytes': pin.archive_bytes,
            'expires_at': expires.isoformat()}


def inspect_retained_producer():
    """Fetch live metadata through the existing authenticated GitHub API seam."""
    from simulation import checkpoint_artifacts as artifacts
    rows = artifacts._pages(f'/actions/runs/{PIN.run_id}/artifacts', 'artifacts')
    matches = [row for row in rows if row.get('id') == PIN.artifact_id]
    if len(matches) != 1:
        raise ValueError('pinned retained artifact missing or ambiguous')
    run = artifacts._api(f'/actions/runs/{PIN.run_id}')
    jobs = artifacts._pages(f'/actions/runs/{PIN.run_id}/jobs?filter=all', 'jobs')
    return authenticate_retained_producer(matches[0], run, jobs)
