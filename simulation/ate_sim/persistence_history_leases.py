"""Weak alias leases share one checked independent pin per generation.

Weak callbacks only queue release. Database writes occur at explicit safe
session boundaries, never during arbitrary collection or checked reads.
"""
import weakref

from .incremental_store import StoreError
from .persistence_lazy_budget import resident_bytes


class HistoryLeasePool:
    def __init__(self, store):
        self.store = store
        self._generations = {}
        self._aliases = {}
        self._pending_release = set()
        self.closed = False

    def pin_for(self, alias):
        row = self._aliases.get(id(alias))
        if row is None or row[0]() is not alias:
            return None
        return self._generations[row[1]][0]

    def acquire(self, alias, source_pin):
        if self.closed:
            raise StoreError('history lease pool is closed')
        existing = self.pin_for(alias)
        if existing is not None:
            return existing
        generation = source_pin.captured_head
        self.store._require_pin(source_pin)
        marker = id(alias)
        pool_ref = weakref.ref(self)
        def collected(ref):
            pool = pool_ref()
            if pool is not None and not pool.closed:
                pool._forget(marker, ref)
        ref = weakref.ref(alias, collected)
        row = self._generations.get(generation)
        if row is None:
            row = self.store.capture_pin(source_pin=source_pin), set()
            self._generations[generation] = row
        row[1].add(marker)
        self._aliases[marker] = ref, generation
        self._pending_release.discard(generation)
        return row[0]

    def _forget(self, marker, expected):
        row = self._aliases.get(marker)
        if row is None or row[0] is not expected:
            return
        del self._aliases[marker]
        generation = row[1]
        group = self._generations[generation]
        group[1].discard(marker)
        if not group[1]:
            self._pending_release.add(generation)

    def release(self, alias):
        row = self._aliases.get(id(alias))
        if row is not None and row[0]() is alias:
            self._forget(id(alias), row[0])

    def drain(self):
        if self.closed:
            return
        generations = tuple(sorted(generation for generation in self._pending_release
                                   if not self._generations[generation][1]))
        # Releasing many leases must not multiply ordinary maintenance by256.
        self.store.release_pins(tuple(self._generations[generation][0] for generation in generations), cleanup_budget=0)
        for generation in generations:
            del self._generations[generation]
            self._pending_release.discard(generation)

    def close_with(self, publisher_pin):
        if self.closed:
            return
        pins = tuple(row[0] for row in self._generations.values()) + (publisher_pin,)
        self.store.release_pins(pins)
        self.closed = True
        self._generations.clear()
        self._aliases.clear()
        self._pending_release.clear()

    def diagnostics(self):
        return {'generations': len(self._generations), 'aliases': len(self._aliases),
                'pending_releases': len(self._pending_release),
                'metadata_python_bytes': resident_bytes((self._generations, self._aliases, self._pending_release))}
