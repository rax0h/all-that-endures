"""Exact ordered pressure arithmetic with complete conservative revisions.

A cold miss streams all household occurrences, including extinct households
and duplicates. It is O(H) time with bounded clean record/history residency.
Cache entries contain only a scalar and revision witnesses, never subtotals.
"""
from collections import OrderedDict
import weakref

from .persistence_lazy_budget import resident_bytes
from .persistence_lazy_sequence import LazyOrderedSequence


def household_preparedness_mean(world, settlement):
    lifetime = world.__dict__.get('_ate_persistence_lifetime')
    session = None if lifetime is None else lifetime._session_ref()
    cache = None if session is None else getattr(session, '_pressure_cache', None)
    if cache is not None:
        return cache.mean(settlement)
    return sum(world.households[hid].preparedness for hid in settlement.households) / max(1, len(settlement.households))


class ExactPressureCache:
    def __init__(self, session, entry_limit=64, byte_limit=65536):
        self._session_ref = weakref.ref(session)
        self._entries = OrderedDict()
        self._entry_limit = entry_limit
        self._byte_limit = byte_limit
        self._hits = self._misses = self._occurrence_visits = 0

    def mean(self, settlement):
        session = self._session_ref()
        session._ensure_people_mutation_allowed()
        households = session.world.households
        members = settlement.households
        # Only counted membership plus the concrete household writer journal
        # supplies complete revisions. Other storage uses the exact fallback.
        key = None
        if type(members) is LazyOrderedSequence and hasattr(households, 'preparedness_revision'):
            members._ensure()
            key = (session.pin.captured_head, households.preparedness_revision,
                   members._incarnation, members._revision, len(members))
        if key is not None and key in self._entries:
            self._hits += 1
            result = self._entries.pop(key)
            self._entries[key] = result
            return result
        self._misses += 1
        scalar_reader = getattr(households, 'checked_preparedness', None)
        def values():
            for hid in members:
                self._occurrence_visits += 1
                yield scalar_reader(hid) if scalar_reader is not None else households[hid].preparedness
        result = sum(values()) / max(1, len(members))
        if key is not None:
            self._entries[key] = result
            while len(self._entries) > self._entry_limit or resident_bytes(self._entries) > self._byte_limit:
                self._entries.popitem(last=False)
        return result

    def clear(self):
        self._entries.clear()

    def diagnostics(self):
        return {'entries': len(self._entries), 'entry_limit': self._entry_limit,
                'byte_limit': self._byte_limit,
                'python_bytes': resident_bytes(self._entries), 'hits': self._hits,
                'misses': self._misses, 'occurrence_visits': self._occurrence_visits,
                'cold_miss_time_bound': 'O(all household occurrences)'}
