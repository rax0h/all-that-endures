"""Exact threshold-counter deltas for accepted native adoption scopes."""
from collections import Counter

from .incremental_store import StoreIntegrityError
from .persistence_proof_content import version_key
from .persistence_lazy_adoption import ADOPTION_NAMESPACE, BUCKET_NAMESPACE, SCOPE_NAMESPACE, THRESHOLDS
from .persistence_proof_world_new_backings import Unsupported
from . import persistence_proof_publication as content
from . import persistence_proof_world as world

MAX_BYTES = 4 * 1048576
MAX_READS = 512


def prepare(store, request, versions):
    request.adoption_rows = frozenset()
    if len(versions) > 512:
        return
    try:
        result = _prepare(store, request, versions)
    except Unsupported:
        return
    request.adoption_rows = frozenset(result)


def _prepare(store, request, versions):
    codec, g = store.codec, request.pin.captured_head
    consumed = sum(len(i['namespace'].encode()) + len(i['typed_key']) + len(i['payload'] or b'') +
                   len(i['memberships_blob']) for i in versions)
    if consumed > MAX_BYTES:
        raise Unsupported()
    cache = {}
    def read(ns, typed):
        nonlocal consumed
        marker = ns, typed
        if marker in cache:
            return cache[marker]
        if len(cache) >= MAX_READS:
            raise Unsupported()
        sizes = store._interval_rows('lazy_record_versions', 'length(payload)+length(memberships)',
            ('namespace', 'typed_key'), marker, g, 'lazy_record_interval', limit=2)
        if len(sizes) > 1:
            raise StoreIntegrityError('overlapping adoption predecessor versions')
        consumed += len(ns.encode()) + len(typed)
        if sizes:
            if type(sizes[0][0]) is not int:
                raise StoreIntegrityError('invalid adoption predecessor size')
            consumed += sizes[0][0]
        if consumed > MAX_BYTES:
            raise Unsupported()
        old = content._source_version(store, g, ns, typed, max_bytes=MAX_BYTES)
        wanted = None if old is None else content._version_value(ns, typed, old, codec.version)
        if content._map(store).get(request.pairs[0][0].versions, version_key(ns, typed)) != wanted:
            raise StoreIntegrityError('adoption predecessor lacks accepted content')
        cache[marker] = old
        return old
    deltas = Counter()
    sources = set()
    for item in versions:
        if item['namespace'] != ADOPTION_NAMESPACE:
            continue
        sources.add((ADOPTION_NAMESPACE, item['typed_key']))
        if item['change'].delete or item['change'].reinsertion or item['change'].record_schema != 1:
            raise Unsupported()
        key, after = codec.decode(item['typed_key']), codec.decode(item['payload'])
        world._check_family_value(store, ADOPTION_NAMESPACE, key, after)
        old = read(ADOPTION_NAMESPACE, item['typed_key'])
        before = None if old is None else codec.decode(old.payload)
        if old is not None:
            if old.record_schema != 1:
                raise Unsupported()
            world._check_family_value(store, ADOPTION_NAMESPACE, key, before)
        scope = read(SCOPE_NAMESPACE, codec.encode(key[0]))
        if scope is None:
            raise Unsupported()  # A new settlement's complete counter set is separate.
        if scope.record_schema != 1 or scope.memberships != codec.encode(()) or scope.payload != codec.encode(('settlement', key[0])):
            raise StoreIntegrityError('adoption predecessor scope disagrees')
        for threshold in THRESHOLDS:
            delta = int(after > threshold) - int(before is not None and before > threshold)
            for sid in (None, key[0]):deltas[sid, threshold] += delta
    expected = {}
    for key, delta in deltas.items():
        if not delta:
            continue
        typed = codec.encode(key)
        old = read(BUCKET_NAMESPACE, typed)
        if old is None or old.record_schema != 1 or old.memberships != codec.encode(()):
            raise StoreIntegrityError('adoption bucket lacks its accepted predecessor')
        count = codec.decode(old.payload)
        if type(count) is not int or count < 0 or count+delta < 0:
            raise StoreIntegrityError('adoption bucket count disagrees')
        expected[BUCKET_NAMESPACE, typed] = codec.encode(count+delta)
    actual = set()
    for item in versions:
        if item['namespace'] != BUCKET_NAMESPACE:
            continue
        marker = BUCKET_NAMESPACE, item['typed_key']
        wanted = expected.get(marker)
        if wanted is None:
            old = read(*marker)
            wanted = None if old is None else old.payload
        if (item['change'].delete or item['change'].reinsertion or item['change'].record_schema != 1
                or item['memberships_blob'] != codec.encode(()) or item['payload'] != wanted):
            raise StoreIntegrityError('adoption bucket differs from exact source delta')
        actual.add(marker)
    if not set(expected) <= actual:
        raise StoreIntegrityError('adoption source delta lacks a bucket update')
    return actual | sources


def audit(store, pin):
    """Reconcile all threshold counts, including retained empty settlements.

    This is deliberately a full-audit operation. A declined bounded certificate
    cannot turn the auxiliary counts into unchecked publication authority.
    """
    codec, g = store.codec, pin.captured_head
    namespaces = (ADOPTION_NAMESPACE, BUCKET_NAMESPACE, SCOPE_NAMESPACE)
    declared = tuple(store._namespace_state_at(ns, g) is not None for ns in namespaces)
    if not any(declared):
        return
    if not all(declared):
        raise StoreIntegrityError('adoption auxiliary namespaces are incomplete')

    def rows(ns):
        for key in store.iter_keys(pin, ns):
            row = content._source_version(store, g, ns, codec.encode(key))
            if row is None or row.record_schema != 1:
                raise StoreIntegrityError('adoption source schema disagrees')
            yield key, row

    counts = {(None, threshold): 0 for threshold in THRESHOLDS}
    scopes = set()
    for sid, row in rows(SCOPE_NAMESPACE):
        if (type(sid) is not int or row.payload != codec.encode(('settlement', sid))
                or row.memberships != codec.encode(())):
            raise StoreIntegrityError('adoption settlement authority disagrees')
        scopes.add(sid)
        counts.update({(sid, threshold): 0 for threshold in THRESHOLDS})
    for key, row in rows(ADOPTION_NAMESPACE):
        value = codec.decode(row.payload)
        world._check_family_value(store, ADOPTION_NAMESPACE, key, value)
        if key[0] not in scopes:
            raise StoreIntegrityError('adoption source lacks settlement authority')
        for threshold in THRESHOLDS:
            if value > threshold:
                counts[None, threshold] += 1
                counts[key[0], threshold] += 1
    for key, row in rows(BUCKET_NAMESPACE):
        value = codec.decode(row.payload)
        if (type(key) is not tuple or len(key) != 2
                or (key[0] is not None and type(key[0]) is not int)
                or type(key[1]) is not float or key not in counts
                or type(value) is not int or value != counts.pop(key)
                or row.memberships != codec.encode(())):
            raise StoreIntegrityError('adoption bucket differs from complete source counts')
    if counts:
        raise StoreIntegrityError('adoption source counts lack buckets')
