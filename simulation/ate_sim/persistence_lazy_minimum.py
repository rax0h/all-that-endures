"""Checked ordered minimum buckets over concrete scalar record families."""
from collections import OrderedDict

from .incremental_store import StoreIntegrityError
from .persistence_lazy_nested_history import checked_value
from .persistence_lazy_store import VersionChange, _query_checksum

HEADER_NAMESPACE = 'aux.lazy.minimum.headers'
NODE_NAMESPACE = 'aux.lazy.minimum.nodes'
FIELDS = {
    'world.communities.communities': {
        ('kind', 'origin_settlement'): 'kind_origin',
        ('kind', 'parent', 'origin_settlement'): 'kind_parent_origin',
    },
    'world.metaphysics.resurrection_tokens': {('person', 'consumed_year'): 'person_consumed'},
}


def normalize(value):
    if type(value) in (bool, int) or type(value) is float and value.is_integer():
        return int(value)
    return value


def _exponent_rank(value):
    digits = str(abs(value))
    if value < 0:
        return '0' + '0' * len(digits) + '1' + ''.join(str(9 - int(digit)) for digit in digits)
    return '1' + '1' * len(digits) + '0' + digits


def numeric_rank(value):
    # Exact binary rationals preserve mixed int/float comparisons, including
    # large integers, subnormal floats and equal numeric representatives.
    if type(value) not in (bool, int, float):
        raise TypeError('minimum record ID must be numeric')
    if type(value) is float:
        if value != value:
            raise TypeError('minimum record ID cannot be NaN')
        if value == float('-inf'):
            return '/'
        if value == float('inf'):
            return '3'
        numerator, denominator = value.as_integer_ratio()
    else:
        numerator, denominator = int(value), 1
    if numerator == 0:
        return '1'
    magnitude = abs(numerator)
    exponent = magnitude.bit_length() - denominator.bit_length()
    fraction = format(magnitude, 'b')[1:].rstrip('0')
    body = _exponent_rank(exponent) + ':' + fraction + '/'
    if numerator < 0:
        return '0' + ''.join(chr(127 - ord(character)) for character in body)
    return '2' + body


def scope_name(label, values, codec):
    return 'minimum/v1/' + label + '/' + codec.encode(tuple(normalize(value) for value in values)).hex()


def record_scopes(namespace, record, codec):
    return tuple(scope_name(label, (getattr(record, field) for field in fields), codec)
                 for fields, label in FIELDS[namespace].items())


def membership_tuples(namespace, record, ordinal, codec):
    return (('insertion', 0, ordinal),) + tuple(
        (scope, numeric_rank(record.id), ordinal) for scope in record_scopes(namespace, record, codec))


def initial_changes(records, codec):
    buckets = {}
    for namespace, key, ordinal, record in records:
        for scope in record_scopes(namespace, record, codec):
            buckets.setdefault((namespace, scope), []).append((numeric_rank(record.id), ordinal, key))
    result = []
    for (namespace, scope), items in sorted(buckets.items()):
        items.sort(key=lambda item: item[:2])
        result.append(VersionChange(HEADER_NAMESPACE, (namespace, scope),
            ('minimum-bucket/v1', len(items), (items[0][2],)), record_schema=1))
        for index, (rank, ordinal, key) in enumerate(items):
            previous = (items[index - 1][2],) if index else None
            following = (items[index + 1][2],) if index + 1 < len(items) else None
            result.append(VersionChange(NODE_NAMESPACE, (namespace, scope, key),
                ('minimum-node/v1', rank, ordinal, previous, following), record_schema=1))
    return tuple(result)


def checked_marker(store, generation, namespace, scope, rank, key, ordinal):
    encoded_value, encoded_key = store.codec.encode(rank), store.codec.encode(key)
    rows = store.db.execute(
        'SELECT valid_from,valid_to,row_checksum FROM lazy_query_versions '
        'WHERE namespace=? AND index_name=? AND index_value=? AND record_key=? AND ordinal=? '
        'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) LIMIT 2',
        (namespace, scope, encoded_value, encoded_key, ordinal, generation, generation)).fetchall()
    store._query_rows += len(rows)
    if len(rows) != 1 or rows[0][2] != _query_checksum(namespace, scope, encoded_value,
            encoded_key, ordinal, rows[0][0], rows[0][1]):
        raise StoreIntegrityError('minimum query witness missing or overlapping')
    row = store._visible_record_row(generation, namespace, encoded_key)
    if row is None:
        raise StoreIntegrityError('minimum node lacks visible owner')
    *_, metadata = store._check_record_row(namespace, encoded_key, row, decode=False)
    if (scope, rank, ordinal) not in metadata or ('insertion', 0, ordinal) not in metadata:
        raise StoreIntegrityError('minimum node disagrees with owner metadata')


def rank_neighbor(store, pin, namespace, scope, *, rank=None, ordinal=None, before=False, exclude=()):
    """One checked rank neighbor; SQL ordering uses the existing covering index."""
    generation = store._read_snapshot_start(pin)
    try:
        excluded = tuple(store.codec.encode(key) for key in exclude)
        exclusion = ' AND record_key NOT IN (' + ','.join('?' for _ in excluded) + ')' if excluded else ''
        bound = '' if rank is None else ' AND (index_value,ordinal) ' + ('<' if before else '>') + ' (?,?)'
        args = () if rank is None else (store.codec.encode(rank), ordinal)
        direction = ' DESC' if before else ' ASC'
        ordering = ' ORDER BY index_value' + direction + ',ordinal' + direction + ',record_key' + direction + ' LIMIT 1'
        columns = 'SELECT index_value,record_key,ordinal FROM lazy_query_versions '
        head = store._checked_head_row()[0]
        if generation == head:
            rows = store.db.execute(columns + 'INDEXED BY lazy_query_current WHERE namespace=? AND index_name=? '
                'AND valid_to IS NULL' + bound + exclusion + ordering,
                (namespace, scope) + args + excluded).fetchall()
        else:
            rows = store.db.execute(columns + 'INDEXED BY lazy_query_open_generation WHERE namespace=? AND index_name=? '
                'AND valid_to IS NULL AND valid_from<=?' + bound + exclusion + ordering,
                (namespace, scope, generation) + args + excluded).fetchall()
            rows += store.db.execute(columns + 'INDEXED BY lazy_query_closed_generation WHERE namespace=? AND index_name=? '
                'AND valid_to=?' + bound + exclusion + ordering,
                (namespace, scope, generation + 1) + args + excluded).fetchall()
        store._query_rows += len(rows)
        if not rows:
            return None
        row = sorted(rows, key=lambda item: (item[0], item[2], item[1]), reverse=before)[0]
        rank_value, key = store.codec.decode(row[0]), store.codec.decode(row[1])
        checked_marker(store, generation, namespace, scope, rank_value, key, row[2])
        return rank_value, row[2], key
    finally:
        store._read_snapshot_end()


def _link(value):
    return value is None or type(value) is tuple and len(value) == 1


class MinimumQueries:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._minimum_cache = OrderedDict()
        for namespace in (HEADER_NAMESPACE, NODE_NAMESPACE):
            if self._store._namespace_state_at(namespace, self._pin.captured_head) is None:
                raise StoreIntegrityError('minimum auxiliary namespace authority missing')

    def _aux(self, namespace, key):
        cache_key = (namespace, key)
        if cache_key not in self._minimum_cache:
            value = checked_value(self._store, self._pin, namespace, key)
            self._minimum_cache[cache_key] = value
            while len(self._minimum_cache) > 256:
                self._minimum_cache.popitem(last=False)
        self._minimum_cache.move_to_end(cache_key)
        return self._minimum_cache[cache_key]

    def _header(self, scope):
        key = (self._namespace, scope)
        if not self._store.contains_lazy_key(self._pin, HEADER_NAMESPACE, key):
            if rank_neighbor(self._store, self._pin, self._namespace, scope) is not None:
                raise StoreIntegrityError('minimum bucket header is missing')
            return ('minimum-bucket/v1', 0, None)
        value = self._aux(HEADER_NAMESPACE, key)
        if (type(value) is not tuple or len(value) != 3 or value[0] != 'minimum-bucket/v1'
                or type(value[1]) is not int or value[1] < 0 or not _link(value[2])
                or (value[1] == 0) != (value[2] is None)):
            raise StoreIntegrityError('invalid minimum bucket header')
        return value

    def _node(self, scope, key):
        value = self._aux(NODE_NAMESPACE, (self._namespace, scope, key))
        if (type(value) is not tuple or len(value) != 5 or value[0] != 'minimum-node/v1'
                or type(value[1]) is not str or type(value[2]) is not int or value[2] < 0
                or not _link(value[3]) or not _link(value[4])):
            raise StoreIntegrityError('invalid minimum linked node')
        return value

    def _persisted_ordinal(self, key):
        if key not in self._baseline_ordinal:
            generation = self._store._read_snapshot_start(self._pin)
            try:
                encoded = self._store.codec.encode(key)
                row = self._store._visible_record_row(generation, self._namespace, encoded)
                if row is None:
                    raise StoreIntegrityError('minimum insertion owner absent')
                *_, metadata = self._store._check_record_row(self._namespace, encoded, row, decode=False)
                ordinals = [ordinal for name, value, ordinal in metadata if name == 'insertion' and value == 0]
                if len(ordinals) != 1:
                    raise StoreIntegrityError('minimum insertion authority absent')
                self._baseline_ordinal[key] = ordinals[0]
            finally:
                self._store._read_snapshot_end()
        return self._baseline_ordinal[key]

    def __iter__(self):
        self._ensure()
        touched = self._effective_touched()
        rows = self._store.query_memberships(self._pin, self._namespace, 'insertion', 0, exclude_keys=touched)
        if len(rows) != self._baseline_count - sum(self._baseline_exists(key) for key in touched):
            raise StoreIntegrityError('minimum insertion cardinality mismatch')
        ordered = list(rows) + [(key, self._current_ordinal(key)) for key in touched if self._visible(key)]
        ordered.sort(key=lambda item: item[1])
        return iter([key for key, ordinal in ordered])

    def minimum(self, fields, *values):
        self._ensure()
        fields = (fields,) if isinstance(fields, str) else tuple(fields)
        if fields not in FIELDS[self._namespace] or len(values) != len(fields):
            raise ValueError('unsupported minimum predicate')
        scope = scope_name(FIELDS[self._namespace][fields], values, self._store.codec)
        header = self._header(scope)
        if header[1] == 0 and rank_neighbor(self._store, self._pin, self._namespace, scope) is not None:
            raise StoreIntegrityError('empty minimum bucket retains query authority')
        link, previous, prior_rank = header[2], None, None
        touched, candidate, seen = self._effective_touched(), None, set()
        while link is not None:
            key = link[0]
            if key in seen or len(seen) >= header[1]:
                raise StoreIntegrityError('minimum linked chain cycle or count mismatch')
            seen.add(key)
            node = self._node(scope, key)
            if node[3] != previous or prior_rank is not None and node[1:3] <= prior_rank:
                raise StoreIntegrityError('minimum linked order mismatch')
            if key not in touched:
                generation = self._store._read_snapshot_start(self._pin)
                try:
                    checked_marker(self._store, generation, self._namespace, scope, node[1], key, node[2])
                finally:
                    self._store._read_snapshot_end()
                record = self[key]
                if numeric_rank(record.id) != node[1] or scope not in record_scopes(self._namespace, record, self._store.codec):
                    raise StoreIntegrityError('minimum candidate disagrees with record')
                candidate = (node[1], node[2], record)
                break
            previous, prior_rank, link = link, node[1:3], node[4]
        if link is None and len(seen) != header[1]:
            raise StoreIntegrityError('minimum linked chain truncated')
        for key in touched:
            if self._visible(key):
                record = dict.__getitem__(self, key)
                if scope in record_scopes(self._namespace, record, self._store.codec):
                    proposal = (numeric_rank(record.id), self._current_ordinal(key), record)
                    if candidate is None or proposal[:2] < candidate[:2]:
                        candidate = proposal
        return None if candidate is None else candidate[2]

    def accept_save(self, plan, new_pin):
        super().accept_save(plan, new_pin)
        self._minimum_cache.clear()
        for key in plan.touched_keys:
            self._baseline_ordinal.pop(key, None)

    def prepare_save_changes(self):
        result = super().prepare_save_changes()
        effective = set(result[2])
        for key in tuple(self._dirty - effective):
            if key not in self._new_keys and key not in self._reinserted:
                self._dirty.discard(key)
                self._index_touched_memberships(key, None)
                self._lru[key] = None
        self._evict_clean()
        return result

    def diagnostics(self):
        result = super().diagnostics()
        result['minimum_aux_cache_entries'] = len(self._minimum_cache)
        result['minimum_aux_cache_limit'] = 256
        return result

    def prepare_index_changes(self, changes):
        headers, nodes, baselines, insertions, removals = {}, {}, {}, [], []
        def header(scope):
            if scope not in headers:
                value = self._header(scope)
                headers[scope] = list(value)
                physical_key = (self._namespace, scope)
                exists = self._store.contains_lazy_key(self._pin, HEADER_NAMESPACE, physical_key)
                baselines[(HEADER_NAMESPACE, physical_key)] = value if exists else None
            return headers[scope]
        def node(scope, key):
            marker = (scope, key)
            if marker not in nodes:
                value = self._node(scope, key)
                nodes[marker] = list(value)
                baselines[(NODE_NAMESPACE, (self._namespace, scope, key))] = value
            if nodes[marker] is None:
                raise StoreIntegrityError('minimum neighbor references removed node')
            return nodes[marker]
        for change in changes:
            old = self._store.codec.decode(self._baseline_bytes(change.key)) if self._baseline_exists(change.key) else None
            old_ordinal = self._persisted_ordinal(change.key) if old is not None else None
            old_scopes = record_scopes(self._namespace, old, self._store.codec) if old is not None else ()
            new_scopes = record_scopes(self._namespace, change.value, self._store.codec) if not change.delete else ()
            new_ordinal = next((member.ordinal for member in change.memberships if member.index_name == 'insertion'), None)
            for scope in set(old_scopes) | set(new_scopes):
                old_position = (numeric_rank(old.id), old_ordinal) if scope in old_scopes else None
                new_position = (numeric_rank(change.value.id), new_ordinal) if scope in new_scopes else None
                if old_position == new_position:
                    continue
                if old_position is not None:
                    removals.append((scope, change.key, old_position))
                if new_position is not None:
                    insertions.append((scope, change.key, new_position))
        for scope, key, position in removals:
            bucket, current = header(scope), node(scope, key)
            if tuple(current[1:3]) != position:
                raise StoreIntegrityError('minimum removed node position mismatch')
            previous, following = current[3:5]
            if previous is None:
                if bucket[2] != (key,):
                    raise StoreIntegrityError('minimum head disagrees with removed node')
                bucket[2] = following
            else:
                predecessor = node(scope, previous[0])
                if predecessor[4] != (key,):
                    raise StoreIntegrityError('minimum predecessor gap')
                predecessor[4] = following
            if following is not None:
                successor = node(scope, following[0])
                if successor[3] != (key,):
                    raise StoreIntegrityError('minimum successor gap')
                successor[3] = previous
            nodes[(scope, key)] = None
            bucket[1] -= 1
        excluded = {}
        for scope, key, position in removals + insertions:
            excluded.setdefault(scope, set()).add(key)
        added = {}
        for scope, key, position in insertions:
            bucket = header(scope)
            neighbors = []
            for before in (True, False):
                neighbors.append(rank_neighbor(self._store, self._pin, self._namespace, scope,
                    rank=position[0], ordinal=position[1], before=before, exclude=excluded[scope]))
            preceding, following = neighbors
            for other_position, other_key in added.get(scope, ()):
                if other_position < position and (preceding is None or other_position > preceding[:2]):
                    preceding = (*other_position, other_key)
                if other_position > position and (following is None or other_position < following[:2]):
                    following = (*other_position, other_key)
            previous_link = None if preceding is None else (preceding[2],)
            following_link = None if following is None else (following[2],)
            if previous_link is None:
                if bucket[2] != following_link:
                    raise StoreIntegrityError('minimum insertion head gap')
                bucket[2] = (key,)
            else:
                predecessor = node(scope, previous_link[0])
                if predecessor[4] != following_link:
                    raise StoreIntegrityError('minimum insertion predecessor gap')
                predecessor[4] = (key,)
            if following_link is not None:
                successor = node(scope, following_link[0])
                if successor[3] != previous_link:
                    raise StoreIntegrityError('minimum insertion successor gap')
                successor[3] = (key,)
            physical_key = (self._namespace, scope, key)
            baselines.setdefault((NODE_NAMESPACE, physical_key), None)
            nodes[(scope, key)] = ['minimum-node/v1', *position, previous_link, following_link]
            bucket[1] += 1
            added.setdefault(scope, []).append((position, key))
        result = []
        for scope, value in headers.items():
            key = (self._namespace, scope)
            if value[1] < 0 or (value[1] == 0) != (value[2] is None):
                raise StoreIntegrityError('invalid minimum bucket successor')
            if tuple(value) != baselines[(HEADER_NAMESPACE, key)]:
                result.append(VersionChange(HEADER_NAMESPACE, key, tuple(value), record_schema=1))
        for (scope, key), value in nodes.items():
            physical_key = (self._namespace, scope, key)
            old = baselines[(NODE_NAMESPACE, physical_key)]
            value = None if value is None else tuple(value)
            if value != old:
                result.append(VersionChange(NODE_NAMESPACE, physical_key, value, delete=value is None, record_schema=1))
        return tuple(sorted(result, key=lambda change: (change.namespace, self._store.codec.encode(change.key))))
