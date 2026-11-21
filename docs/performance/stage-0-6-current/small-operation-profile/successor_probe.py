"""Profile the current small save and warm year on a disposable exact copy."""

import cProfile
import os
from pathlib import Path
import pstats
import shutil
import sys
import time
from unittest.mock import patch


REQUEST = Path(__file__).with_name('successor-probe-request.json')


def profile_measure(recorder, output):
    measure = recorder.measure

    def measured(self, name, operation):
        if name not in ('save', 'warm_step'):
            return measure(self, name, operation)
        profile = cProfile.Profile()
        try:
            return measure(self, name, lambda: profile.runcall(operation))
        finally:
            if profile.getstats():
                profile.dump_stats(output / (name + '.prof'))
                with (output / (name + '-calls.txt')).open('w', encoding='utf-8') as stream:
                    stats = pstats.Stats(profile, stream=stream)
                    for sort in ('cumulative', 'time'):
                        stats.sort_stats(sort).print_stats(64)

    return patch.object(recorder, 'measure', measured)


def run(root, output, scratch):
    import ate_sim
    from simulation import continuation_receipts as receipts
    from simulation import stage_0_6_genesis_checkpoint as checkpoint
    from simulation import stage_0_6_genesis_resume as resume
    from simulation import stage_0_6_genesis_stages as stages
    from simulation import stage_0_6_genesis_transport as transport

    head = resume.git(root, 'rev-parse', 'HEAD')
    if head != os.environ['GITHUB_SHA'] or Path(ate_sim.__file__).resolve().parent != root / 'simulation/ate_sim':
        raise ValueError('operation probe imported a different checkout')
    request = receipts.load_receipt(REQUEST)
    checkpoint.exact(request, {'request_id', 'smoke_run_id', 'proofs_artifact_id'}, 'operation probe request')
    run_id = request['smoke_run_id']
    proof_id = request['proofs_artifact_id']
    checkpoint.integer(run_id, 'accepted smoke run', 1)
    checkpoint.integer(proof_id, 'closed proofs artifact', 1)
    green = resume.inspect_green(root)
    fresh_ref = resume.require_smoke(root, run_id, scratch / 'accepted')
    fresh = resume.restore_receipt(root, fresh_ref, scratch / 'fresh', mode='smoke', stage='fresh_restore')
    proof_ref = resume.find_reference(root, run_id, proof_id, mode='smoke', stage='proofs')
    proof = resume.restore_receipt(root, proof_ref, scratch / 'proofs', mode='smoke', stage='proofs')
    if fresh['parent']['receipt']['parent']['receipt'] != proof:
        raise ValueError('requested proof is not the accepted smoke ancestor')
    descriptor = proof['database']
    if descriptor['bytes'] > 64 * 1024 * 1024 or descriptor['year'] != 1 or descriptor['generation'] != 0:
        raise ValueError('operation probe requires the small generation-zero baseline')
    restored = scratch / 'input'
    transport.restore(proof['data_ref'], restored, member='candidate.sqlite',
                      member_bytes=descriptor['bytes'], compatible=lambda head: resume.compatible(root, head))
    original = restored / 'candidate.sqlite'
    checkpoint.verify_database(original, descriptor)
    if shutil.disk_usage(scratch).free < 2 * descriptor['bytes'] + 64 * 1024 * 1024:
        raise ValueError('insufficient operation probe copy/journal headroom')
    software, fingerprint = resume.runtime_description()
    receipts.publish_receipt(output / 'input.json', dict(
        request=request, head=head, green=green, fresh_ref=fresh_ref, proof_ref=proof_ref,
        proof_receipt_sha256=checkpoint.receipt_hash(proof), data_ref=proof['data_ref'],
        database=descriptor, runtime=software, fingerprint=fingerprint,
    ))
    working = scratch / 'working.sqlite'
    try:
        with profile_measure(stages.Recorder, output):
            observations = stages._measure(original, working, proof, output / 'operations', time.monotonic() + 120)
        saved = dict(context=proof['context'], proof_commitment=observations['saved_commitment'])
        exact = stages.restore_in_fresh_process(working, saved, 45)
    finally:
        checkpoint.verify_database(original, descriptor)
    receipts.publish_receipt(output / 'result.json', dict(
        kind='instrumented function attribution', restored=exact, original_verified=True,
        phases=observations['phases'], saved_commitment=observations['saved_commitment'],
        profiled_phases=['save', 'warm_step'],
    ))


if __name__ == '__main__':
    import tempfile

    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='ate-small-operation-', dir=Path.cwd()) as directory:
        run(Path.cwd(), output, Path(directory))
