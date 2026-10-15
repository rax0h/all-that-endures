"""Validation-only construction checkpoints; ordinary World readers never use these.

CI callers must authenticate producing run/job/artifact provenance independently.
Every stage uses disposable writers and publishes only closed, immutable files.
"""
from dataclasses import asdict
from itertools import chain
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time

from simulation import complete_upgrade_checkpoint as old
from ate_sim import persistence_catalog_copy as copy
from ate_sim.persistence_adapters import WorldCodec, SCHEMA
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot, FORMAT_VERSION
from ate_sim.persistence_conversion_workspace import ReplayRows, unpack_change
from ate_sim.incremental_store import RecordChange, StoreIntegrityError
from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY

SCHEMA_NAME = 'ate-validation-construction/1'
ADAPTERS = dict(ordinary='ordinary', versions='version', catalog='version',
    dependencies='version', identity='identity', orders='raw', states='raw')
BASE_KEYS = {'schema','stage','simulation_schema','rules_id','context','producer',
    'source_receipt','source_receipt_sha256','source_generation','files','pin'}


def _hash(value, length=64):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{'+str(length)+'}', value) is not None


def _producer(context):
    if os.environ.get('GITHUB_RUN_ID'):
        return dict(mode='ci', run_id=int(os.environ['GITHUB_RUN_ID']),
            job=os.environ['GITHUB_JOB'], workflow_sha=os.environ['GITHUB_SHA'])
    return dict(mode='local', run_id=0, job='local', workflow_sha=context['harness_sha'])


def _check_producer(value):
    if (not isinstance(value, dict) or set(value) != {'mode','run_id','job','workflow_sha'}
            or value['mode'] not in ('ci','local') or type(value['run_id']) is not int
            or (value['run_id'] <= 0 if value['mode']=='ci' else value['run_id'] != 0)
            or not isinstance(value['job'], str) or not re.fullmatch('[A-Za-z0-9_-]+', value['job'])
            or not _hash(value['workflow_sha'], 40)):
        raise ValueError('construction producer mismatch')


def _file_info(path):
    return {'sha256':old.file_hash(path), 'bytes':Path(path).stat().st_size}


def _finish(stage, bundle, manifest):
    """Link only fsynced closed data, with the manifest last; never overwrite."""
    stage, bundle = Path(stage), Path(bundle)
    for name in manifest['files']:
        with (stage/name).open('rb') as f: os.fsync(f.fileno())
    old._write_new(stage/'manifest.json', manifest)
    bundle.mkdir()
    try:
        for name in (*manifest['files'], 'manifest.json'):
            os.link(stage/name, bundle/name)
        old._fsync_dir(bundle); old._fsync_dir(bundle.parent)
    except BaseException:
        shutil.rmtree(bundle)
        raise
    return manifest


def _check_bundle(bundle, context, stage, files, extra):
    old._context(context)
    bundle = Path(bundle)
    if (bundle.is_symlink() or not bundle.is_dir()
            or {p.name for p in bundle.iterdir()} != set(files)|{'manifest.json'}
            or any(p.is_symlink() or not p.is_file() for p in bundle.iterdir())):
        raise ValueError('unexpected construction bundle members')
    manifest = old._json(bundle/'manifest.json')
    if (not isinstance(manifest, dict) or set(manifest) != BASE_KEYS|set(extra)
            or manifest['schema'] != SCHEMA_NAME or manifest['stage'] != stage
            or manifest['simulation_schema'] != SCHEMA or manifest['context'] != context
            or not isinstance(manifest['rules_id'], str) or not manifest['rules_id']
            or type(manifest['source_generation']) is not int or manifest['source_generation'] < 0):
        raise ValueError('construction manifest stage/lineage mismatch')
    _check_producer(manifest['producer'])
    descriptions = manifest['files']
    if not isinstance(descriptions, dict) or set(descriptions) != set(files):
        raise ValueError('construction file inventory mismatch')
    for name, desc in descriptions.items():
        if (not isinstance(desc, dict) or set(desc) != {'sha256','bytes'}
                or not _hash(desc['sha256']) or type(desc['bytes']) is not int or desc['bytes'] <= 0
                or desc != _file_info(bundle/name)):
            raise ValueError('construction file checksum/size mismatch')
    raw = manifest['source_receipt']
    import hashlib
    if (not isinstance(raw, str) or not _hash(manifest['source_receipt_sha256'])
            or hashlib.sha256(raw.encode()).hexdigest() != manifest['source_receipt_sha256']):
        raise ValueError('construction source receipt mismatch')
    receipt = json.loads(raw)
    if (not isinstance(receipt, dict) or receipt.get('schema') != 1 or receipt.get('stage') != 'lazy'
            or not isinstance(receipt.get('config'), dict)
            or receipt['config'].get('rules_id') != manifest['rules_id']):
        raise ValueError('construction source configuration mismatch')
    pin = manifest['pin']
    if (not isinstance(pin, dict) or set(pin) != {'token','store_identity','captured_head'}
            or any(not isinstance(pin[k], str) or not pin[k] for k in ('token','store_identity'))
            or type(pin['captured_head']) is not int
            or pin['captured_head'] != manifest['source_generation']+(stage=='committed')):
        raise ValueError('construction pin/generation mismatch')
    return manifest


def _commit_args(manifest, codec):
    payload = manifest['commit']
    if not isinstance(payload, str): raise ValueError('invalid typed commit arguments')
    try:
        encoded = bytes.fromhex(payload); value = codec.decode(encoded)
    except (ValueError, TypeError) as exc:
        raise ValueError('invalid typed commit arguments') from exc
    if (codec.encode(value) != encoded or not isinstance(value, dict)
            or set(value) != {'commit_token','next_incarnation_id','required_format_version','metadata'}
            or not _hash(value['commit_token'], 32)
            or type(value['next_incarnation_id']) is not int or value['next_incarnation_id'] <= 0
            or type(value['required_format_version']) is not int or value['required_format_version'] != FORMAT_VERSION
            or not isinstance(value['metadata'], dict)):
        raise ValueError('invalid typed commit arguments')
    return value


def validate_prepared(bundle, *, context):
    """Check transport, typed descriptors and target pin without decoding all rows.

    Actual rows retain their existing per-row/canonical/count/order checks when
    consumed by the original commit or ordinal restoration. CI authenticates
    producer provenance before calling this local validator.
    """
    m = _check_bundle(bundle, context, 'prepared', {'target.sqlite','spool.sqlite'}, {'streams','commit'})
    streams = m['streams']
    if not isinstance(streams, dict) or set(streams) != set(ADAPTERS):
        raise ValueError('construction stream inventory mismatch')
    ids = set()
    for name, adapter in ADAPTERS.items():
        desc = streams[name]
        if (not isinstance(desc, dict) or set(desc) != {'stream','count','seal','adapter'}
                or type(desc['stream']) is not int or desc['stream'] <= 0 or desc['stream'] in ids
                or type(desc['count']) is not int or desc['count'] < 0
                or not _hash(desc['seal']) or desc['adapter'] != adapter):
            raise ValueError('construction stream descriptor mismatch')
        ids.add(desc['stream'])
    with old._open(Path(bundle)/'target.sqlite', m['rules_id']) as store:
        store.db.execute('PRAGMA query_only=ON')
        old._checked_pin(store, m['pin'])
        args = _commit_args(m, store.codec)
        head = store.head_metadata()
        metadata = args['metadata']
        # The private target intentionally starts with only immutable segment
        # namespaces; the original commit installs the captured mutable inventory.
        if (set(metadata) != set(head)
                or any(metadata[k] != head[k] for k in head if k != 'namespaces')
                or type(metadata['namespaces']) is not tuple
                or any(not isinstance(ns,str) or not ns for ns in metadata['namespaces'])
                or not set(head['namespaces']).issubset(metadata['namespaces'])):
            raise ValueError('construction head metadata mismatch')
    return m


class _Spool:
    def __init__(self, path):
        self.codec = WorldCodec(identity_links_recorded=True)
        self.db = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)
        self.db.execute('PRAGMA query_only=ON'); self.db.execute('PRAGMA cache_size=-128')
        self.closed = False

    def ensure_open(self):
        if self.closed: raise RuntimeError('construction spool closed')

    def rows(self, manifest, name):
        d = manifest['streams'][name]
        adapter = d['adapter']
        def decode(value):
            if adapter == 'raw':
                if (type(value) is not tuple or len(value) != 3 or not isinstance(value[0], str)
                        or type(value[2]) is not int or value[2] < 0
                        or (type(value[1]) is not bytes if name=='orders' else type(value[1]) is not int or value[1] < 0)):
                    raise ValueError('invalid construction ordering row')
                return value
            if type(value) is not tuple or not value or value[0] != adapter:
                raise ValueError('construction stream adapter mismatch')
            return unpack_change(value)
        return ReplayRows(self, d['stream'], d['count'], d['seal'], decode)

    def __enter__(self): return self
    def __exit__(self, *args):
        self.closed = True; self.db.close()


def prepare(source, source_receipt, bundle, *, rules_id, context):
    old._context(context)
    source, source_receipt, bundle = Path(source), Path(source_receipt), Path(bundle)
    if bundle.exists(): raise FileExistsError(bundle)
    receipt = old._json(source_receipt)
    source_hash, receipt_hash = old.file_hash(source), old.file_hash(source_receipt)
    if (receipt.get('schema') != 1 or receipt.get('stage') != 'lazy'
            or receipt.get('config',{}).get('rules_id') != rules_id
            or receipt.get('database') != {'name':source.name,'sha256':source_hash}):
        raise ValueError('construction source receipt/database mismatch')
    with old._open(source, rules_id) as store: source_generation = store.generation
    bundle.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.construction-', dir=bundle.parent) as directory:
        pending = Path(directory); captured = None
        original = copy._construction_ready
        class Captured(BaseException): pass
        def ready(target, pin, *, workspace, streams, commit):
            nonlocal captured
            original(target,pin,workspace=workspace,streams=streams,commit=commit)
            if target.db.in_transaction or set(streams) != set(ADAPTERS):
                raise ValueError('unexpected preparation boundary')
            descriptors = {}
            for name, values in streams.items():
                if not isinstance(values, ReplayRows):
                    if name != 'states': raise ValueError('construction stream is not sealed')
                    values = workspace.stage(values)
                if values.workspace is not workspace:
                    raise ValueError('foreign construction workspace')
                descriptors[name] = dict(stream=values.stream,count=values.count,
                    seal=values.seal,adapter=ADAPTERS[name])
            if workspace.db.in_transaction: raise ValueError('construction spool writer still active')
            checked = old._checked_pin(target)
            if checked != pin: raise ValueError('construction captured a foreign pin')
            os.link(target.path, pending/'target.sqlite')
            os.link(workspace.path, pending/'spool.sqlite')
            captured = dict(schema=SCHEMA_NAME, stage='prepared', simulation_schema=SCHEMA,
                rules_id=rules_id, context=context, producer=_producer(context),
                source_receipt=source_receipt.read_text(), source_receipt_sha256=receipt_hash,
                source_generation=source_generation, pin=asdict(pin), streams=descriptors,
                commit=target.codec.encode(commit).hex())
            raise Captured()
        copy._construction_ready = ready
        try:
            try: upgrade_lazy_snapshot(source,pending/'must-not-publish.sqlite',rules_id=rules_id)
            except Captured: pass
            else: raise RuntimeError('converter missed preparation boundary')
        finally: copy._construction_ready = original
        if captured is None: raise RuntimeError('preparation did not retain inputs')
        if old.file_hash(source) != source_hash or old.file_hash(source_receipt) != receipt_hash:
            raise ValueError('source changed during construction preparation')
        captured['files'] = {name:_file_info(pending/name) for name in ('target.sqlite','spool.sqlite')}
        return _finish(pending,bundle,captured)


def commit_prepared(prepared, bundle, *, context):
    prepared, bundle = Path(prepared), Path(bundle)
    if bundle.exists(): raise FileExistsError(bundle)
    m = validate_prepared(prepared,context=context)
    bundle.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.construction-',dir=bundle.parent) as directory:
        pending = Path(directory); private = pending/'target.sqlite'
        shutil.copyfile(prepared/'target.sqlite',private)
        if _file_info(private) != m['files']['target.sqlite']: raise ValueError('construction copy mismatch')
        with old._open(private,m['rules_id']) as store, _Spool(prepared/'spool.sqlite') as spool:
            pin = old._checked_pin(store,m['pin']); args = _commit_args(m,store.codec)
            # Ordering is applied in the next job, but it is part of this exact
            # prepared construction. Reject broken commitments before spending
            # the original commit's work, with bounded streaming residency.
            for name in ('orders','states'):
                for _ in spool.rows(m,name): pass
            token = args['commit_token']
            committed = store.commit(pin,**args,
                changes=chain(spool.rows(m,'ordinary'),(RecordChange(EVENT_STORAGE,
                    COMMIT_DESCRIPTOR_KEY,(1,pin.captured_head+1,token)),)),
                version_changes=chain(spool.rows(m,'versions'),spool.rows(m,'catalog'),spool.rows(m,'dependencies')),
                identity_changes=spool.rows(m,'identity'),new_segments=(),preparation_budget=(4096,2*1024*1024))
            if committed.outcome != 'committed': raise ValueError('construction commit did not commit')
            checked = old._checked_pin(store,asdict(committed.pin))
            result = {k:m[k] for k in BASE_KEYS-{'stage','files','pin','producer'}}
            result.update(stage='committed',producer=_producer(context),pin=asdict(checked),
                prepared_manifest_sha256=old.file_hash(prepared/'manifest.json'))
        result['files'] = {'target.sqlite':_file_info(private)}
        # Authenticated inputs are immutable dependencies, never operational writers.
        if old.file_hash(prepared/'spool.sqlite') != m['files']['spool.sqlite']['sha256']:
            raise ValueError('construction changed prepared spool')
        if old.file_hash(prepared/'target.sqlite') != m['files']['target.sqlite']['sha256']:
            raise ValueError('construction changed prepared target')
        return _finish(pending,bundle,result)


def restore_orders(prepared, committed, candidate, *, context):
    prepared, committed, candidate = Path(prepared), Path(committed), Path(candidate)
    if candidate.exists(): raise FileExistsError(candidate)
    m = validate_prepared(prepared,context=context)
    c = _check_bundle(committed,context,'committed',{'target.sqlite'},{'prepared_manifest_sha256'})
    if (c['prepared_manifest_sha256'] != old.file_hash(prepared/'manifest.json')
            or any(c[k] != m[k] for k in ('rules_id','source_receipt','source_receipt_sha256','source_generation'))
            or c['pin']['token'] != m['pin']['token'] or c['pin']['store_identity'] != m['pin']['store_identity']):
        raise ValueError('committed construction/preparation lineage mismatch')
    candidate.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.construction-',dir=candidate.parent) as directory:
        pending = Path(directory); private = pending/old.DB_NAME
        shutil.copyfile(committed/'target.sqlite',private)
        if _file_info(private) != c['files']['target.sqlite']: raise ValueError('construction copy mismatch')
        with old._open(private,c['rules_id']) as store, _Spool(prepared/'spool.sqlite') as spool:
            pin = old._checked_pin(store,c['pin'])
            copy._restore_copy_ordinals(store,pin.captured_head,spool.rows(m,'orders'),spool.rows(m,'states'))
            old._checked_pin(store,c['pin'])
        manifest = {k:c[k] for k in ('simulation_schema','rules_id','context','source_receipt',
            'source_receipt_sha256','source_generation','pin')}
        manifest.update(schema=old.SCHEMA_NAME,stage='unverified',
            database=dict(name=old.DB_NAME,**_file_info(private)))
        with private.open('rb') as stream: os.fsync(stream.fileno())
        old._write_new(pending/old.MANIFEST_NAME,manifest)
        candidate.mkdir()
        try:
            for name in (old.DB_NAME,old.MANIFEST_NAME): os.link(pending/name,candidate/name)
            old._fsync_dir(candidate); old._fsync_dir(candidate.parent)
        except BaseException:
            shutil.rmtree(candidate); raise
    return manifest


def main(argv=None):
    import argparse, resource
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','commit','orders'])
    parser.add_argument('--context',type=Path,required=True)
    parser.add_argument('--bundle',type=Path,required=True)
    for key in ('source','source-receipt','prepared','committed'): parser.add_argument('--'+key,type=Path)
    parser.add_argument('--rules-id')
    args = parser.parse_args(argv); context = old._json(args.context)
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    def require(*names):
        for name in names:
            if getattr(args,name) is None: parser.error('--'+name.replace('_','-')+' required')
    started = time.monotonic()
    if args.stage=='prepare':
        require('source','source_receipt','rules_id')
        prepare(args.source,args.source_receipt,args.bundle,rules_id=args.rules_id,context=context)
    elif args.stage=='commit':
        require('prepared'); commit_prepared(args.prepared,args.bundle,context=context)
    else:
        require('prepared','committed'); restore_orders(args.prepared,args.committed,args.bundle,context=context)
    print(json.dumps({'construction_stage':args.stage,'seconds':time.monotonic()-started}),flush=True)


if __name__=='__main__': main()
