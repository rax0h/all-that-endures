"""Validation-only checkpoints for an expensive complete-format upgrade.

These files are UNVERIFIED until both original verifiers succeed. Callers must
independently authenticate CI artifact origin/digests; JSON is not a certificate.
No ordinary reader accepts this bundle and the production runtime is untouched.
Run one stage per process: capture temporarily intercepts a private copy seam.
"""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time

from ate_sim import persistence_catalog_copy as copy
from ate_sim.persistence_adapters import WorldCodec, SCHEMA, _read_cold_manifest
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot, check_open
from ate_sim.persistence_lazy_store import LazyRecordStore, GenerationPin
from ate_sim.persistence_session import _publish_private_cold_file

SCHEMA_NAME = 'ate-validation-unverified-upgrade/1'
DB_NAME = 'candidate.sqlite'
MANIFEST_NAME = 'manifest.json'


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON member')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs)


def _write_new(path, data):
    """Expose only a complete, fsynced file; never overwrite earlier evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.checkpoint-', dir=path.parent) as directory:
        pending = Path(directory)/'pending'
        with pending.open('w') as stream:
            json.dump(data, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.link(pending, path)
        _fsync_dir(path.parent)


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def _context(context):
    if not isinstance(context, dict) or set(context) != {'runtime_sha', 'harness_sha', 'source_artifact'}:
        raise ValueError('invalid expected lineage')
    for key in ('runtime_sha', 'harness_sha'):
        if not isinstance(context[key], str) or not re.fullmatch('[0-9a-f]{40}', context[key]):
            raise ValueError('invalid expected commit')
    artifact = context['source_artifact']
    if (not isinstance(artifact, dict) or set(artifact) != {'id', 'run_id', 'archive_sha256'}
            or any(type(artifact[key]) is not int or artifact[key] <= 0 for key in ('id', 'run_id'))
            or not isinstance(artifact['archive_sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', artifact['archive_sha256'])):
        raise ValueError('invalid source artifact lineage')


def _open(path, rules_id):
    return LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA, expected_rules_id=rules_id)


def _checked_pin(store, expected=None):
    head = store.checked_head()
    pins, receipts, attempts = store._checked_operational_rows(head.generation)
    if len(pins) != 1 or any(row[3] not in ('committed', 'acknowledged') for row in attempts):
        raise ValueError('candidate must retain exactly one resolved construction pin')
    token, identity, generation, _ = pins[0]
    pin = GenerationPin(token, identity, generation)
    store._require_pin(pin)
    if generation != head.generation or (expected is not None and asdict(pin) != expected):
        raise ValueError('candidate generation/pin mismatch')
    return pin


def capture(source, source_receipt, bundle, *, rules_id, context):
    """Retain the committed, ordinal-restored private copy, without certifying it."""
    _context(context)
    source, source_receipt, bundle = Path(source), Path(source_receipt), Path(bundle)
    if bundle.exists(): raise FileExistsError(bundle)
    receipt = _json(source_receipt)
    source_sha, receipt_sha = file_hash(source), file_hash(source_receipt)
    if (receipt.get('schema') != 1 or receipt.get('stage') != 'lazy'
            or receipt.get('config', {}).get('rules_id') != rules_id
            or receipt.get('database') != {'name': source.name, 'sha256': source_sha}):
        raise ValueError('source receipt/database mismatch')
    with _open(source, rules_id) as store:
        source_generation = store.generation
    bundle.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.unverified-', dir=bundle.parent) as directory:
        stage = Path(directory)
        retained = stage/DB_NAME
        original_phase, original_restore = copy._copy_phase, copy._restore_copy_ordinals
        private_path = None
        captured_pin = None
        class Captured(BaseException): pass
        def phase(name, path):
            nonlocal private_path
            original_phase(name, path)
            if name == 'after_catalog_commit': private_path = Path(path)
        def restore(store, generation, orders, states):
            nonlocal captured_pin
            original_restore(store, generation, orders, states)
            if private_path is None or store.path != private_path or store.db.in_transaction:
                raise ValueError('unexpected capture boundary')
            captured_pin = asdict(_checked_pin(store))
            # Hard link lives beyond converter temporary-directory cleanup. Hash
            # ONLY after the converter unwinds and closes the SQLite writer.
            os.link(private_path, retained)
            raise Captured()
        copy._copy_phase, copy._restore_copy_ordinals = phase, restore
        try:
            try:
                upgrade_lazy_snapshot(source, stage/'must-not-publish.sqlite', rules_id=rules_id)
            except Captured:
                pass
            else:
                raise RuntimeError('converter missed capture boundary')
        finally:
            copy._copy_phase, copy._restore_copy_ordinals = original_phase, original_restore
        if file_hash(source) != source_sha or file_hash(source_receipt) != receipt_sha:
            raise ValueError('source changed during capture')
        with retained.open('rb') as stream: os.fsync(stream.fileno())
        manifest = {'schema': SCHEMA_NAME, 'stage': 'unverified', 'simulation_schema': SCHEMA,
            'rules_id': rules_id, 'context': context, 'source_receipt': source_receipt.read_bytes().decode('utf-8'),
            'source_receipt_sha256': receipt_sha, 'source_generation': source_generation,
            'database': {'name': DB_NAME, 'sha256': file_hash(retained), 'bytes': retained.stat().st_size},
            'pin': captured_pin}
        _write_new(stage/MANIFEST_NAME, manifest)
        # Atomic no-overwrite allocation; manifest is linked last. Any interrupted
        # partial bundle fails validate() and is never consumed as a checkpoint.
        bundle.mkdir()
        try:
            os.link(retained, bundle/DB_NAME)
            os.link(stage/MANIFEST_NAME, bundle/MANIFEST_NAME)
            _fsync_dir(bundle); _fsync_dir(bundle.parent)
        except BaseException:
            shutil.rmtree(bundle)
            raise
    return manifest


def validate(bundle, *, context):
    """Validate local bytes against independently authenticated expected lineage."""
    _context(context)
    bundle = Path(bundle)
    if bundle.is_symlink() or set(p.name for p in bundle.iterdir()) != {DB_NAME, MANIFEST_NAME}:
        raise ValueError('unexpected candidate bundle members')
    if any(p.is_symlink() or not p.is_file() for p in bundle.iterdir()):
        raise ValueError('candidate members must be regular files')
    manifest = _json(bundle/MANIFEST_NAME)
    keys = {'schema', 'stage', 'simulation_schema', 'rules_id', 'context', 'source_receipt',
            'source_receipt_sha256', 'source_generation', 'database', 'pin'}
    if (not isinstance(manifest, dict) or set(manifest) != keys or manifest['schema'] != SCHEMA_NAME
            or manifest['stage'] != 'unverified' or manifest['simulation_schema'] != SCHEMA
            or manifest['context'] != context):
        raise ValueError('candidate manifest/lineage mismatch')
    database = manifest['database']
    if (not isinstance(database, dict) or set(database) != {'name', 'sha256', 'bytes'}
            or database['name'] != DB_NAME or type(database['bytes']) is not int
            or database['bytes'] != (bundle/DB_NAME).stat().st_size
            or database['sha256'] != file_hash(bundle/DB_NAME)):
        raise ValueError('candidate database checksum/size mismatch')
    raw_receipt = manifest['source_receipt']
    if (not isinstance(raw_receipt, str)
            or hashlib.sha256(raw_receipt.encode()).hexdigest() != manifest['source_receipt_sha256']):
        raise ValueError('candidate source receipt checksum mismatch')
    receipt = json.loads(raw_receipt)
    if (not isinstance(receipt, dict) or receipt.get('schema') != 1 or receipt.get('stage') != 'lazy'
            or receipt.get('config', {}).get('rules_id') != manifest['rules_id']):
        raise ValueError('candidate source receipt mismatch')
    pin = manifest['pin']
    if (not isinstance(manifest['rules_id'], str) or not manifest['rules_id']
            or type(manifest['source_generation']) is not int or manifest['source_generation'] < 0
            or not isinstance(pin, dict) or set(pin) != {'token', 'store_identity', 'captured_head'}
            or any(not isinstance(pin[k], str) or not pin[k] for k in ('token', 'store_identity'))
            or type(pin['captured_head']) is not int
            or pin['captured_head'] != manifest['source_generation'] + 1):
        raise ValueError('candidate pin/source generation mismatch')
    with _open(bundle/DB_NAME, manifest['rules_id']) as store:
        store.db.execute('PRAGMA query_only=ON')
        _checked_pin(store, manifest['pin'])
    return manifest


@contextmanager
def _immutable_store(bundle, manifest):
    path = Path(bundle)/DB_NAME
    try:
        with _open(path, manifest['rules_id']) as store:
            store.db.execute('PRAGMA query_only=ON')
            yield store, _checked_pin(store, manifest['pin'])
    finally:
        if file_hash(path) != manifest['database']['sha256']:
            raise ValueError('verification changed retained database')


def _receipt(bundle, manifest, stage, previous=None):
    return {'schema': SCHEMA_NAME, 'stage': stage,
        'manifest_sha256': file_hash(Path(bundle)/MANIFEST_NAME),
        'database': manifest['database'], 'context': manifest['context'],
        'previous_receipt_sha256': file_hash(previous) if previous else None}


def _require_receipt(path, bundle, manifest, stage, previous=None):
    if _json(path) != _receipt(bundle, manifest, stage, previous):
        raise ValueError('verification receipt stage/lineage mismatch')


def verify_storage(bundle, receipt, *, context):
    if Path(receipt).exists(): raise FileExistsError(receipt)
    manifest = validate(bundle, context=context)
    started = time.monotonic()
    with _immutable_store(bundle, manifest) as (store, pin):
        store.verify_all()
    _write_new(receipt, _receipt(bundle, manifest, 'storage-verified'))
    print(json.dumps({'stage': 'storage_verified', 'seconds': time.monotonic()-started}), flush=True)


def verify_catalog(bundle, storage_receipt, receipt, *, context):
    if Path(receipt).exists(): raise FileExistsError(receipt)
    manifest = validate(bundle, context=context)
    _require_receipt(storage_receipt, bundle, manifest, 'storage-verified')
    started = time.monotonic()
    with _immutable_store(bundle, manifest) as (store, pin):
        copy._verify_catalog(store, pin)
    _write_new(receipt, _receipt(bundle, manifest, 'catalog-verified', storage_receipt))
    print(json.dumps({'stage': 'catalog_verified', 'seconds': time.monotonic()-started}), flush=True)


def publish(bundle, storage_receipt, catalog_receipt, destination, *, context):
    """Publish a disposable checked copy; retained candidate remains immutable."""
    destination = Path(destination)
    if destination.exists(): raise FileExistsError(destination)
    manifest = validate(bundle, context=context)
    _require_receipt(storage_receipt, bundle, manifest, 'storage-verified')
    _require_receipt(catalog_receipt, bundle, manifest, 'catalog-verified', storage_receipt)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.verified-upgrade-', dir=destination.parent) as directory:
        private = Path(directory)/'verified.sqlite'
        shutil.copyfile(Path(bundle)/DB_NAME, private)
        if file_hash(private) != manifest['database']['sha256']:
            raise ValueError('publication copy checksum mismatch')
        with _open(private, manifest['rules_id']) as store:
            pin = _checked_pin(store, manifest['pin'])
            check_open(store, pin, store.checked_head(), _read_cold_manifest(store))
            generation, identity = store.generation, store.store_identity
            store.release_pin(pin)
        with private.open('rb') as stream: os.fsync(stream.fileno())
        _publish_private_cold_file(private, destination)
    return {'source_generation': manifest['source_generation'], 'generation': generation,
            'store_identity': identity, 'source_preserved': True, 'complete_format': True}


def publish_p5(bundle, storage_receipt, catalog_receipt, workdir, *, context, workflow_sha):
    """Let the existing P5 runner validate its source and write accepted receipt."""
    import persistence_p5_long_validation as p5
    from ate_sim import persistence_complete_format as complete
    manifest = validate(bundle, context=context)
    workdir = Path(workdir)
    if file_hash(workdir/'checkpoint.json') != manifest['source_receipt_sha256']:
        raise ValueError('P5 source receipt mismatch')
    source_receipt = json.loads(manifest['source_receipt'])
    config = source_receipt['config']
    source = workdir/source_receipt['database']['name']
    if source.name != 'p5-long-lazy.sqlite' or source.parent != workdir:
        raise ValueError('P5 source filename mismatch')
    if file_hash(source) != source_receipt['database']['sha256']:
        raise ValueError('P5 source database mismatch')
    original = complete.upgrade_lazy_snapshot
    def finish(actual_source, destination, *, rules_id):
        if Path(actual_source) != source or rules_id != manifest['rules_id']:
            raise ValueError('P5 publication source mismatch')
        return publish(bundle, storage_receipt, catalog_receipt, destination, context=context)
    complete.upgrade_lazy_snapshot = finish
    try:
        return p5.run(config['seed'], config['milestones'], config['bootstrap_year'], workdir,
            config['rules_id'], context['runtime_sha'], workflow_sha,
            complete_format=True, initialization=config['initialization'],
            stop_after='complete', resume_from='lazy', checkpoint_product_sha=config['product_sha'])
    finally:
        complete.upgrade_lazy_snapshot = original


def main(argv=None):
    import argparse
    import resource
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['capture', 'storage', 'catalog', 'publish', 'p5-publish'])
    for name in ('context', 'bundle'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('source', 'source-receipt', 'receipt', 'storage-receipt',
                 'catalog-receipt', 'destination', 'workdir'):
        parser.add_argument('--'+name, type=Path)
    parser.add_argument('--rules-id')
    parser.add_argument('--workflow-sha')
    args = parser.parse_args(argv)
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    context = _json(args.context)
    def require(*names):
        for name in names:
            if getattr(args, name) is None: parser.error('--'+name.replace('_', '-')+' required')
    started = time.monotonic()
    print(json.dumps({'stage': args.stage+'_started', 'context': context}), flush=True)
    if args.stage == 'capture':
        require('source', 'source_receipt', 'rules_id')
        capture(args.source, args.source_receipt, args.bundle, rules_id=args.rules_id, context=context)
    elif args.stage == 'storage':
        require('receipt'); verify_storage(args.bundle, args.receipt, context=context)
    elif args.stage == 'catalog':
        require('storage_receipt', 'receipt')
        verify_catalog(args.bundle, args.storage_receipt, args.receipt, context=context)
    elif args.stage == 'publish':
        require('storage_receipt', 'catalog_receipt', 'destination')
        publish(args.bundle, args.storage_receipt, args.catalog_receipt, args.destination, context=context)
    else:
        require('storage_receipt', 'catalog_receipt', 'workdir', 'workflow_sha')
        publish_p5(args.bundle, args.storage_receipt, args.catalog_receipt, args.workdir,
                   context=context, workflow_sha=args.workflow_sha)
    print(json.dumps({'stage': args.stage+'_finished', 'seconds': time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main()
