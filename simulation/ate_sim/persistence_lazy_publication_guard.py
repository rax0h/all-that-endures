"""Checked failed-plan release using the existing pin/attempt/receipt protocol.

This module holds no publication authority or replay state. The central writer
supplies its frozen token; participants retain their dirty journals until the
existing store proves that token unpublished at their exact parent generation.
"""
from contextlib import contextmanager

from .incremental_store import StoreConflictError


@contextmanager
def checked_uncommitted_publication(store, pin, commit_token):
    encoded = store.codec.encode(commit_token)
    with store.read_snapshot(pin):
        head = int(store._checked_head_row()[0])
        if head != pin.captured_head:
            raise StoreConflictError('cannot thaw a stale publication parent')
        _pins, _receipts, attempts = store._checked_operational_rows(head)
        attempt = next((row for row in attempts if row[0] == pin.token), None)
        if attempt is None:
            # Preparation can fail before commit registers any attempt.
            yield
            return
        if attempt[1] != encoded:
            if attempt[3] == 'acknowledged' and attempt[4] == pin.captured_head:
                # The previous acknowledged save produced this parent. The
                # newly frozen plan was never registered as an attempt.
                yield
                return
            raise StoreConflictError('failed publication token differs from the latest attempt')
    result = store.resolve_commit(pin, commit_token)
    if (result.outcome != 'not_committed' or result.stale or result.pin != pin
        or result.generation != pin.captured_head):
        raise StoreConflictError('publication is committed, unresolved or stale; keep its frozen plan')
    with store.read_snapshot(pin):
        head = int(store._checked_head_row()[0])
        if head != pin.captured_head:
            raise StoreConflictError('cannot thaw a superseded publication parent')
        _pins, _receipts, attempts = store._checked_operational_rows(head)
        attempt = next((row for row in attempts if row[0] == pin.token), None)
        if attempt is None or attempt[1:5] != (encoded, pin.captured_head, 'not_committed', None):
            raise StoreConflictError('failed publication proof changed before release')
        yield
