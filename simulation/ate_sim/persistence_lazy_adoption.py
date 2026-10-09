"""Fixed adoption predicates and independently versioned query cardinality."""
from .incremental_store import Membership, StoreIntegrityError
from .persistence_lazy_nested_history import checked_value
from .persistence_lazy_store import VersionChange

ADOPTION_NAMESPACE = 'world.culture.adoption'
BUCKET_NAMESPACE = 'aux.lazy.adoption.buckets'
SCOPE_NAMESPACE = 'aux.lazy.adoption.settlements'
THRESHOLDS = (.008, .01, .22, .35, .62)


def memberships(key, value, ordinal):
    return (Membership('insertion', 0, ordinal),) + tuple(member for threshold in THRESHOLDS if value > threshold for member in
                 (Membership('threshold', threshold, ordinal),
                  Membership('settlement-threshold', (key[0], threshold), ordinal)))


def initial_buckets(values):
    counts = {(None, threshold): 0 for threshold in THRESHOLDS}
    scopes = set()
    for key, value in values:
        scopes.add(key[0])
        for threshold in THRESHOLDS:
            counts.setdefault((key[0], threshold), 0)
            if value > threshold:
                counts[(None, threshold)] += 1
                counts[(key[0], threshold)] += 1
    return counts, scopes


class AdoptionQueries:
    """Mixin for the concrete scalar map; all current overlays belong to it."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        buckets = self._store._namespace_state_at(BUCKET_NAMESPACE, self._pin.captured_head)
        scopes = self._store._namespace_state_at(SCOPE_NAMESPACE, self._pin.captured_head)
        if buckets is None or scopes is None or buckets[0] != len(THRESHOLDS) * (scopes[0] + 1):
            raise StoreIntegrityError('adoption auxiliary authority missing or inconsistent')

    def _value_memberships(self, key, value, ordinal):
        return memberships(key, value, ordinal)

    def _persisted_ordinal(self, key):
        if key not in self._baseline_ordinal:
            generation = self._store._read_snapshot_start(self._pin)
            try:
                encoded = self._store.codec.encode(key)
                row = self._store._visible_record_row(generation, self._namespace, encoded)
                if row is None:
                    raise StoreIntegrityError('adoption order owner absent')
                *_, metadata = self._store._check_record_row(self._namespace, encoded, row, decode=False)
                ordinals = [ordinal for name, value, ordinal in metadata if name == 'insertion' and value == 0]
                if len(ordinals) != 1:
                    raise StoreIntegrityError('adoption insertion authority absent')
                self._baseline_ordinal[key] = ordinals[0]
            finally:
                self._store._read_snapshot_end()
        return self._baseline_ordinal[key]

    def __iter__(self):
        self._ensure()
        touched = self._effective_touched()
        rows = self._store.query_memberships(self._pin, self._namespace, 'insertion', 0, exclude_keys=touched)
        expected = self._baseline_count - sum(self._baseline_exists(key) for key in touched)
        if len(rows) != expected:
            raise StoreIntegrityError('adoption insertion cardinality mismatch')
        ordered = list(rows) + [(key, self._current_ordinal(key)) for key in touched if self._visible(key)]
        ordered.sort(key=lambda row: row[1])
        return iter([key for key, ordinal in ordered])

    def accept_save(self, plan, new_pin):
        super().accept_save(plan, new_pin)
        for key in plan.touched_keys:
            self._baseline_ordinal.pop(key, None)

    def prepare_save_changes(self):
        result = super().prepare_save_changes()
        effective = set(result[2])
        for key in tuple(self._dirty - effective):
            if key not in self._new_keys and key not in self._reinserted:
                self._dirty.discard(key)
                self._lru[key] = None
        self._evict_clean()
        return result

    def _known_scope(self, sid):
        if sid is None:
            return True
        known = self._store.contains_lazy_key(self._pin, SCOPE_NAMESPACE, sid)
        bucket = self._store.contains_lazy_key(self._pin, BUCKET_NAMESPACE, (sid, THRESHOLDS[0]))
        if known != bucket:
            raise StoreIntegrityError('adoption settlement and bucket authority disagree')
        if not known:
            return False
        if checked_value(self._store, self._pin, SCOPE_NAMESPACE, sid) != ('settlement', sid):
            raise StoreIntegrityError('invalid adoption settlement authority')
        return True

    def _bucket_count(self, sid, threshold):
        if not self._known_scope(sid):
            return 0
        value = checked_value(self._store, self._pin, BUCKET_NAMESPACE, (sid, threshold))
        if type(value) is not int or value < 0:
            raise StoreIntegrityError('invalid adoption bucket count')
        return value

    def _old_value(self, key):
        if not self._baseline_exists(key):
            return None
        return self._store.codec.decode(self._baseline_bytes(key))

    def items_above(self, threshold, settlement=None):
        self._ensure()
        if type(threshold) not in (int, float) or threshold not in THRESHOLDS:
            raise ValueError('unsupported adoption threshold')
        if settlement is not None and type(settlement) is not int:
            raise TypeError('settlement must be an exact int')
        threshold = THRESHOLDS[THRESHOLDS.index(threshold)]
        touched = self._effective_touched()
        expected = self._bucket_count(settlement, threshold)
        for key in touched:
            if settlement is None or key[0] == settlement:
                old = self._old_value(key)
                expected -= int(old is not None and old > threshold)
        rows = self._store.query_memberships(
            self._pin, self._namespace,
            'threshold' if settlement is None else 'settlement-threshold',
            threshold if settlement is None else (settlement, threshold), exclude_keys=touched)
        if len(rows) != expected or len({key for key, ordinal in rows}) != len(rows):
            raise StoreIntegrityError('adoption query cardinality mismatch')
        selected = []
        for key, ordinal in rows:
            value = self[key]
            if not value > threshold or (settlement is not None and key[0] != settlement) or ordinal != self._current_ordinal(key):
                raise StoreIntegrityError('adoption predicate evidence mismatch')
            selected.append((ordinal, key, value))
        for key in touched:
            if self._visible(key) and (settlement is None or key[0] == settlement):
                value = self[key]
                if value > threshold:
                    selected.append((self._current_ordinal(key), key, value))
        selected.sort(key=lambda row: row[0])
        return [(key, value) for ordinal, key, value in selected]

    def prepare_index_changes(self, changes):
        deltas, new_scopes = {}, set()
        for change in changes:
            key = change.key
            old, new = self._old_value(key), None if change.delete else change.value
            if new is not None and not self._known_scope(key[0]):
                new_scopes.add(key[0])
            for threshold in THRESHOLDS:
                delta = int(new is not None and new > threshold) - int(old is not None and old > threshold)
                for sid in (None, key[0]):
                    bucket = (sid, threshold)
                    deltas[bucket] = deltas.get(bucket, 0) + delta
        for sid in new_scopes:
            for threshold in THRESHOLDS:
                deltas.setdefault((sid, threshold), 0)
        result = [VersionChange(SCOPE_NAMESPACE, sid, ('settlement', sid), record_schema=1) for sid in sorted(new_scopes)]
        for (sid, threshold), delta in sorted(deltas.items(), key=lambda item: self._store.codec.encode(item[0])):
            if delta or sid in new_scopes:
                count = self._bucket_count(sid, threshold) + delta
                if count < 0:
                    raise StoreIntegrityError('negative adoption bucket successor')
                result.append(VersionChange(BUCKET_NAMESPACE, (sid, threshold), count, record_schema=1))
        return tuple(result)
