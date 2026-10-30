"""Bind retained Stage 0.6 transport to the original accepted year-1001 authority.

No historical producer reference is replaced: the pinned retained ZIP is only
an alternate carrier of the original candidate and accepted-year receipts.
"""
import os
from pathlib import Path
import shutil

from simulation import continuation_receipts as r
from simulation import continuation_checkpoint as checkpoint
from simulation.stage_0_6_retained_producer import PIN
from simulation.stage_0_6_retained_transport import download_retained


def _original_transport_matches(proof, ref):
    if not isinstance(proof, dict) or any(proof.get(key) != expected for key, expected in {
        'artifact_id': ref.artifact_id,
        'run_id': ref.run_id,
        'workflow_sha': ref.workflow_sha,
        'archive_sha256': ref.archive_sha256,
        'archive_bytes': ref.archive_bytes,
        'producer_job': ref.producer_job,
    }.items()):
        raise ValueError('retained historical transport does not match original artifact pin')


def authenticate_staged(staged, config, identity, source, accepted, database, authority):
    """Authenticate staged bytes and all original source/acceptance bindings."""
    staged = Path(staged)
    saved, hashes = checkpoint._read_saved(staged/'source', authority, source)
    receipt = r.load_receipt(staged/'accepted/year-verified.json')
    r.validate_year_acceptance(receipt, authority)
    r.match_producer(accepted, receipt['producer'], authority)
    if (not r.same(database, saved['database'])
            or saved['year'] != config['world']['year']
            or not r.same(receipt['binding'], r.saved_binding(saved, source, hashes['save.json']))):
        raise ValueError('retained source is not the exact original accepted year1001')
    performance = dict(
        schema='ate-performance-source/1',
        database={key: database[key] for key in ('sha256', 'bytes')},
        rules_id=authority.source_config['rules_id'],
        pin=dict(token=None, store_identity=saved['store_identity'], captured_head=saved['generation']),
        world=dict(seed=authority.source_config['seed'], year=saved['year']),
        provenance=dict(kind='authenticated-accepted-saved-artifact',
                        artifact=source.to_dict(), acceptance=accepted.to_dict(),
                        save_sha256=hashes['save.json'],
                        source_lease='closed retained artifact; measured sessions record actual lease'))
    if (not r.same(performance['world'], config['world'])
            or any(performance['pin'][key] != config['pin'][key]
                   for key in ('store_identity', 'captured_head'))):
        raise ValueError('accepted source world/pin differs from launch')
    previous_authority = r.load_receipt(staged/'evidence/source-authority.json')
    previous_transport = r.load_receipt(staged/'evidence/source-transport.json')
    if not r.same(previous_authority, performance):
        raise ValueError('retained source authority differs from independently reconstructed authority')
    if (not isinstance(previous_transport, dict)
            or not r.same(previous_transport.get('saved_manifest'), saved)
            or not r.same(previous_transport.get('accepted_binding'), receipt['binding'])):
        raise ValueError('retained source transport receipt differs from accepted source')
    _original_transport_matches(previous_transport.get('source'), source)
    _original_transport_matches(previous_transport.get('acceptance'), accepted)
    previous_producer = previous_transport.get('producer')
    previous_runtime = previous_transport.get('runtime')
    if (not isinstance(previous_producer, dict)
            or previous_producer.get('run_id') != str(PIN.run_id)
            or previous_producer.get('sha') != PIN.head_sha
            or not isinstance(previous_runtime, dict)
            or previous_runtime.get('head') != PIN.head_sha
            or previous_runtime.get('committed_tree') != PIN.runtime_tree):
        raise ValueError('retained source transport provenance differs from producing run/runtime')
    return performance, previous_transport


def prepare_retained(root, config, identity, source, accepted, database, authority):
    """Download once, authenticate before publishing, preserve original provenance."""
    root = Path(root)
    staged = root/'.stage06-retained-input'
    if any(path.exists() or path.is_symlink()
           for path in (staged, root/'source', root/'accepted')):
        raise FileExistsError('retained input destination already exists')
    try:
        retained_transport = download_retained(
            staged, database_bytes=database['bytes'], metadata_max_bytes=r.METADATA_MAX_BYTES)
        performance, historical = authenticate_staged(
            staged, config, identity, source, accepted, database, authority)
        moved = []
        try:
            for name in ('source', 'accepted'):
                os.rename(staged/name, root/name)
                moved.append(name)
        except BaseException:
            for name in reversed(moved):
                os.rename(root/name, staged/name)
            raise
        return performance, dict(
            retained=retained_transport,
            source=historical['source'], acceptance=historical['acceptance'],
            saved_manifest=historical['saved_manifest'],
            accepted_binding=historical['accepted_binding'],
            runtime=identity,
            historical_producer=historical['producer'])
    finally:
        if staged.exists() and not staged.is_symlink():
            shutil.rmtree(staged)
