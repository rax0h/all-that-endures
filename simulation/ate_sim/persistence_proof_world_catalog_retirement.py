"""Bounded proposed retirements joined to accepted empty groups and queries.

Selection is a maintenance choice. The existing catalog compactor still checks
retention floor, pending backing jobs, range edits and the exact resulting delta.
"""
from .incremental_store import StoreIntegrityError
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_lazy_identity_catalog as catalog
from . import persistence_proof_scope as scope
from .persistence_proof_world_new_backings import Unsupported
from .persistence_lazy_store import _query_checksum

ROW_BUDGET = 32


def candidates(store, request, rows, predecessor, affected):
    codec, sa = store.codec, request.pairs[1][0]
    result = []
    for (ns, typed), item in rows.items():
        if ns != catalog.GROUP_NAMESPACE:
            continue
        inc = codec.decode(typed)
        if type(inc) is not int or not 0 < inc < sa.next_incarnation_id or inc in affected:
            continue
        ok, old = predecessor(ns, typed)
        if not ok:
            raise Unsupported()
        if old is None or old.memberships != codec.encode((('retired', True, old.valid_from),)):
            continue
        if not item['change'].delete:
            raise Unsupported()  # Pending-job rotations retain the checked path.
        if len(result) >= ROW_BUDGET:
            raise Unsupported()
        if scope._resolve(store, sa, scope.GroupScope(inc)).count:
            raise StoreIntegrityError('catalog retirement has accepted live placements')
        physical = store._interval_rows('lazy_query_versions',
            "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
            "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
            "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END",
            ('namespace', 'index_name', 'index_value', 'record_key', 'ordinal'),
            (ns, 'retired', codec.encode(True), typed, old.valid_from),
            request.pin.captured_head, 'lazy_query_interval', limit=2)
        if (len(physical) != 1 or physical[0][2] not in ('null', 'integer')
                or physical[0][2] == 'integer' and type(physical[0][1]) is not int
                or not scope._interval_ok(physical[0][0], physical[0][1], request.pin.captured_head)
                or physical[0][3] != _query_checksum(ns, 'retired', codec.encode(True), typed,
                    old.valid_from, physical[0][0], physical[0][1])):
            raise StoreIntegrityError('catalog retirement physical query differs')
        selected = scope.QueryScope(ns, 'retired', codec.encode(True))
        root = scope._resolve(store, sa, selected)
        seek = OrderedSeekMap(store.db, scope._seek_domain(store, selected))
        wanted = scope.query_member(scope.query_domain(store.store_identity, codec.version, selected), typed, old.valid_from)
        if seek.get(root, scope.query_order_key(old.valid_from, typed)) != wanted:
            raise StoreIntegrityError('catalog retirement lacks accepted retired query membership')
        result.append((inc, old.valid_from))
    return tuple(sorted(result, key=lambda pair: (pair[1], codec.encode(pair[0]))))
