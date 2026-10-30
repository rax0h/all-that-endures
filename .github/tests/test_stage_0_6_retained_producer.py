"""Offline pinned producer authentication regressions (no mature fixture required)."""
from copy import deepcopy
from datetime import datetime, timezone
import pytest
from simulation.stage_0_6_retained_producer import PIN, authenticate_retained_producer


NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)


def evidence():
    artifact = dict(id=PIN.artifact_id, name=PIN.artifact_name, expired=False,
                    size_in_bytes=PIN.archive_bytes, digest='sha256:' + PIN.archive_sha256,
                    created_at='2026-10-28T20:25:51Z', expires_at='2026-11-27T20:23:25Z',
                    workflow_run=dict(id=PIN.run_id, head_sha=PIN.head_sha, head_branch=PIN.branch))
    run = dict(id=PIN.run_id, head_sha=PIN.head_sha, head_branch=PIN.branch,
               path=PIN.workflow, event='push', run_attempt=1,
               status='completed', conclusion='success')
    jobs = [dict(name=PIN.job, head_sha=PIN.head_sha, status='completed',
                 conclusion='success', started_at='2026-10-28T20:10:50Z',
                 completed_at='2026-10-28T20:39:15Z')]
    return artifact, run, jobs


def test_exact_pinned_retained_producer():
    artifact, run, jobs = evidence()
    receipt = authenticate_retained_producer(artifact, run, jobs, now=NOW)
    assert receipt['archive_bytes'] == PIN.archive_bytes
    assert receipt['archive_sha256'] == PIN.archive_sha256


@pytest.mark.parametrize('part,key,value', [
    ('artifact', 'id', 1), ('artifact', 'name', 'substitute'),
    ('artifact', 'size_in_bytes', PIN.archive_bytes+1),
    ('artifact', 'digest', 'sha256:'+'0'*64), ('artifact', 'expired', True),
    ('artifact', 'expires_at', '2026-10-29T00:00:00Z'),
    ('run', 'head_sha', '0'*40), ('run', 'path', 'wrong.yml'),
    ('run', 'head_branch', 'main'), ('run', 'conclusion', 'failure'),
    ('run', 'run_attempt', 2), ('run', 'event', 'workflow_dispatch'),
    ('job', 'name', 'measure'), ('job', 'conclusion', 'failure'),
    ('job', 'head_sha', '0'*40), ('job', 'started_at', '2026-10-28T20:30:00Z'),
])
def test_reject_wrong_pinned_producer(part, key, value):
    artifact, run, jobs = evidence()
    if part == 'artifact': artifact[key] = value
    elif part == 'run': run[key] = value
    else: jobs[0][key] = value
    with pytest.raises(ValueError): authenticate_retained_producer(artifact, run, jobs, now=NOW)


def test_reject_expired_even_when_expired_flag_is_false():
    artifact, run, jobs = evidence()
    with pytest.raises(ValueError):
        authenticate_retained_producer(artifact, run, jobs,
            now=datetime(2026, 11, 28, tzinfo=timezone.utc))


def test_reject_duplicate_successful_producer():
    artifact, run, jobs = evidence()
    jobs.append(deepcopy(jobs[0]))
    with pytest.raises(ValueError): authenticate_retained_producer(artifact, run, jobs, now=NOW)


def test_reject_unqualified_timestamps():
    artifact, run, jobs = evidence()
    artifact['created_at'] = '2026-10-28T20:25:51'
    with pytest.raises(ValueError): authenticate_retained_producer(artifact, run, jobs, now=NOW)
