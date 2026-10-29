"""Opt-in, process-local attribution for disposable performance runs.

Exclusive span times partition a measured phase; inclusive times overlap. Read
keys are a fixed-size recent sample, never an exact distinct-record inventory.
No wrapper is installed during ordinary gameplay or an uninstrumented benchmark.
"""
from collections import OrderedDict
from contextlib import ExitStack, contextmanager
from functools import wraps
import hashlib
import importlib
from pathlib import Path
import time
from unittest.mock import patch


class PerformanceAttribution:
    def __init__(self, *, key_limit=2048):
        if type(key_limit) is not int or not 1 <= key_limit <= 16384:
            raise ValueError('key_limit must be an integer in 1..16384')
        self.key_limit = key_limit
        self._hooks = ExitStack()
        self._active = False
        self._stack = []
        self._reset()

    def _reset(self):
        self._keys = OrderedDict()
        self._reads = {}
        self._spans = {}
        self._status = 'incomplete'
        self._name = None
        self._wall = self._cpu = 0.
        self._io_before = self._io_after = None

    @staticmethod
    def _physical_io():
        try:
            rows = Path('/proc/self/io').read_text().splitlines()
            values = {key: int(value) for key, value in (row.split(':') for row in rows)}
            return {key: values[key] for key in ('read_bytes', 'write_bytes', 'rchar', 'wchar')}
        except (OSError, ValueError, KeyError):
            return None

    @contextmanager
    def span(self, label):
        if self._name is None:
            yield
            return
        frame = [label, time.perf_counter(), time.process_time(), 0., 0.]
        self._stack.append(frame)
        try:
            yield
        finally:
            wall, cpu = time.perf_counter()-frame[1], time.process_time()-frame[2]
            self._stack.pop()
            row = self._spans.setdefault(label, dict(calls=0, inclusive_wall_seconds=0.,
                exclusive_wall_seconds=0., inclusive_cpu_seconds=0., exclusive_cpu_seconds=0.))
            row['calls'] += 1
            row['inclusive_wall_seconds'] += wall
            row['inclusive_cpu_seconds'] += cpu
            row['exclusive_wall_seconds'] += max(0., wall-frame[3])
            row['exclusive_cpu_seconds'] += max(0., cpu-frame[4])
            if self._stack:
                self._stack[-1][3] += wall
                self._stack[-1][4] += cpu

    @contextmanager
    def phase(self, name):
        if self._stack or self._name is not None:
            raise RuntimeError('attribution phases cannot nest')
        self._reset()
        self._name = name
        self._io_before = self._physical_io()
        try:
            with self.span('phase.unattributed'):
                yield
            self._status = 'complete'
        finally:
            self._io_after = self._physical_io()
            phase = self._spans.get('phase.unattributed', {})
            self._wall = phase.get('inclusive_wall_seconds', 0.)
            self._cpu = phase.get('inclusive_cpu_seconds', 0.)
            self._name = None

    def _read(self, store, namespace, key):
        if self._name is None:
            return
        # Hashes are bounded-size observations only, never correctness proofs.
        token = hashlib.sha256(namespace.encode()+b'\0'+store.codec.encode(key)).digest()
        hit = token in self._keys
        if hit:
            self._keys.move_to_end(token)
        else:
            self._keys[token] = None
            if len(self._keys) > self.key_limit:
                self._keys.popitem(last=False)
        name = namespace if namespace in self._reads or len(self._reads) < 256 else '<other>'
        row = self._reads.setdefault(name, dict(requests=0, sample_hits=0, sample_misses=0,
                                               reasons={}))
        row['requests'] += 1
        row['sample_hits' if hit else 'sample_misses'] += 1
        # The outermost non-store scope identifies the rule/save stage, rather
        # than labeling every request merely as a codec or read_version call.
        reason = next((f[0] for f in self._stack if f[0] != 'phase.unattributed'
                       and not f[0].startswith(('store.', 'codec.'))), 'unattributed')
        row['reasons'][reason] = row['reasons'].get(reason, 0)+1

    def _wrap(self, owner, name, label, *, reads=False):
        original = getattr(owner, name)
        @wraps(original)
        def measured(*args, **kwargs):
            with self.span(label):
                if reads:
                    namespace = args[2] if len(args) > 2 else kwargs['namespace']
                    key = args[3] if len(args) > 3 else kwargs['key']
                    self._read(args[0], namespace, key)
                return original(*args, **kwargs)
        self._hooks.enter_context(patch.object(owner, name, measured))

    def __enter__(self):
        if self._active:
            raise RuntimeError('attribution context is already active')
        self._active = True
        try:
            engine = importlib.import_module('ate_sim.engine')
            for name in ('_weather', '_production', '_people', '_demography', '_pressure', '_memory'):
                self._wrap(engine.Simulation, name, 'engine.'+name[1:])
            for name in sorted(vars(engine)):
                if name.endswith('_step') and callable(getattr(engine, name)):
                    self._wrap(engine, name, 'engine.'+name)
            bindings = (
                ('persistence_lazy', 'LazyWorldSession', '_prepare_hybrid_save', 'save.prepare'),
                ('persistence_lazy', 'LazyWorldSession', '_publish_committed_hybrid', 'save.publish'),
                ('persistence_lazy', 'LazyWorldSession', '_shared_object_routes', 'identity.routes'),
                # Proof-world outer operation includes guard/settlement; manifest commit
                # includes checks beyond the inner SQLite store commit.
                ('persistence_proof_world_session', '_WorldProofAuthority', 'execute', 'save.proof_execute'),
                ('persistence_proof_world_session', '_WorldProofAuthority', 'commit', 'save.proof_manifest'),
                ('persistence_lazy_store', 'LazyRecordStore', 'commit', 'save.commit'),
                ('persistence_lazy_store', 'LazyRecordStore', 'read_version', 'store.read_version'),
                ('persistence_lazy_store', 'LazyRecordStore', '_check_record_row', 'store.check_record_row'),
                ('persistence_lazy_store', 'LazyRecordStore', '_checked_operational_rows', 'store.operational_check'),
                ('persistence_lazy_identity_catalog', 'IdentityCatalog', 'read_identity_group', 'identity.group'),
                ('persistence_lazy_identity_catalog', 'IdentityCatalog', 'read_owner_identity', 'identity.owner'),
                ('persistence_lazy_identity_coordinator', 'IdentityCoordinator', 'validate_publication', 'identity.publication'),
                ('persistence_lazy_world_identity', 'WorldIdentityBridge', 'synchronize_lazy_placements', 'identity.synchronize'),
                ('persistence_lazy_world_identity', 'WorldIdentityBridge', '_synchronize_owner', 'identity.owner_projection'),
                ('persistence_adapters', 'WorldCodec', 'encode', 'codec.encode'),
                ('persistence_adapters', 'WorldCodec', 'decode', 'codec.decode'),
            )
            for module, cls, name, label in bindings:
                owner = getattr(importlib.import_module('ate_sim.'+module), cls)
                self._wrap(owner, name, label, reads=label == 'store.read_version')
            return self
        except BaseException:
            self._hooks.close()
            self._active = False
            raise

    def __exit__(self, *exc):
        self._hooks.close()
        self._active = False

    def snapshot(self):
        before, after = self._io_before, self._io_after
        io = {'available': before is not None and after is not None}
        if io['available']:
            io.update({key: after[key]-before[key] for key in before})
        return {'schema': 'ate-performance-attribution/1', 'status': self._status,
                'wall_seconds': self._wall, 'cpu_seconds': self._cpu,
                'spans': {k: dict(v) for k,v in self._spans.items()},
                'reads': {k: dict(v, reasons=dict(v['reasons'])) for k,v in self._reads.items()},
                'key_sample': {'entries': len(self._keys), 'limit': self.key_limit,
                               'meaning': 'bounded recent-key LRU; hits are observed reuse, not exact cardinality'},
                'physical_io': io,
                'timing': 'instrumented; exclusive spans partition phase, inclusive spans overlap'}
