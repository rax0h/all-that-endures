"""Read-only timing of the existing engine; never part of persisted world state."""
from collections import defaultdict
from contextlib import ExitStack
from functools import wraps
from time import perf_counter
from unittest.mock import patch
import ate_sim.engine as engine
import gc

BUCKET_ENDS = (100, 250, 500, 750, 1000)

def bucket_end(year):
    return next((end for end in BUCKET_ENDS if year <= end), ((year - 1) // 250 + 1) * 250)

class ScalingTelemetry:
    def __init__(self, world):
        self.world = world
        self.seconds = defaultdict(lambda: defaultdict(float))
        self.calls = defaultdict(lambda: defaultdict(int))
        self.stack = ExitStack()
        self.gc_seconds = defaultdict(float)
        self.gc_collections = defaultdict(int)
        self.gc_start = {}

    def _wrap(self, name, function):
        @wraps(function)
        def timed(*args, **kwargs):
            start = perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                bucket = bucket_end(self.world.year)
                self.seconds[bucket][name] += perf_counter() - start
                self.calls[bucket][name] += 1
        return timed

    def _gc_callback(self, phase, info):
        generation = info["generation"]
        if phase == "start":
            self.gc_start[generation] = perf_counter()
        elif generation in self.gc_start:
            bucket = bucket_end(self.world.year)
            self.gc_seconds[bucket] += perf_counter() - self.gc_start.pop(generation)
            self.gc_collections[(bucket,generation)] += 1

    def __enter__(self):
        gc.callbacks.append(self._gc_callback)
        self.stack.callback(gc.callbacks.remove, self._gc_callback)
        # Wrap the call sites used by Simulation.step without duplicating its order.
        for name in ("_weather", "_production", "_people", "_demography", "_pressure", "_memory"):
            self.stack.enter_context(patch.object(engine.Simulation, name, self._wrap(name, getattr(engine.Simulation, name))))
        for name, function in list(vars(engine).items()):
            if name.endswith("_step") and callable(function):
                self.stack.enter_context(patch.object(engine, name, self._wrap(name, function)))
        return self

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)

    def report(self, start_year, elapsed):
        w = self.world
        bucket = bucket_end(w.year)
        return {
            "record": "scaling_bucket", "first_year": start_year, "last_year": w.year,
            "simulation_seconds": elapsed, "seconds_per_year": elapsed / (w.year - start_year + 1),
            "subsystem_seconds": dict(sorted(self.seconds[bucket].items(), key=lambda item: -item[1])),
            "subsystem_calls": dict(self.calls[bucket]),
            "gc_seconds_including_diagnostics": self.gc_seconds[bucket],
            "gc_collections": {str(g):self.gc_collections[(bucket,g)] for g in range(3)},
            "collections": {
                "people": len(w.people), "living": sum(p.alive for p in w.people.values()),
                "households": len(w.households), "events": len(w.events),
                "relationships": len(w.social.edges), "partnerships": len(w.social.partnerships),
                "material_lots": len(w.materials.lots), "items": len(w.materials.items),
                "active_material_lots": sum(len(ids) for ids in w.materials.active_lot_index.values()),
                "settlement_magic_stock": sum(len(ids) for (kind, owner), ids in w.magic_resources.owner_index.items() if kind=="settlement"),
                "magic_resources": len(w.magic_resources.resources),
                "available_magic_resources": sum(r.consumed_year is None for r in w.magic_resources.resources.values()),
                "resource_owner_buckets": len(w.magic_resources.owner_index),
                "paths": len(w.advancement.paths), "applications": len(w.institutions.applications),
            },
        }
