"""Accepted ordinary namespace completeness; no body or physical-row cache."""
from .incremental_store import StoreError,StoreIntegrityError,_namespace_counts
from .persistence_proof_projection import _ProjectionCodec

MAX_METADATA_BYTES=1048576


def expected_count(store,authority,manifest,namespace):
    cache=getattr(store,'_validation_scope',None);key=(authority.pair[1],)
    summary=None if cache is None else cache.lookup('native-ordinary-counts',key)
    if summary is None:
        blob=manifest.head.namespace_counts
        if type(blob) is not bytes or len(blob)>MAX_METADATA_BYTES:
            raise StoreError('accepted ordinary source counts exceed metadata budget')
        counts=_namespace_counts(_ProjectionCodec(metadata=True),blob)
        summary=tuple(sorted(counts.items()))
        if cache is not None:cache.remember('native-ordinary-counts',key,summary)
    return dict(summary).get(namespace,(0,0))[0]


def check_count(store,authority,manifest,namespace):
    expected=expected_count(store,authority,manifest,namespace)
    # The records PK starts with namespace. This counts this complete selected
    # namespace only; it is not constant first-body work or an archive scan.
    actual=store.db.execute('SELECT count(*) FROM records WHERE namespace=?',(namespace,)).fetchone()
    store._metadata_rows+=1
    if actual is None or type(actual[0]) is not int or actual[0]!=expected:
        raise StoreIntegrityError('native ordinary source roster count differs from accepted manifest')
    return expected
