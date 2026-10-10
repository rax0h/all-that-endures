"""Compact schema encoding for checked identity placement comparisons.

The ordinary WorldCodec remains the portable materializing codec. This private
comparison codec retains its closed schema and encodes checked history leases
as references. References do not replace the catalog's owner/group witnesses.
"""
from .incremental_store import StoreConflictError
from .persistence_adapters import WorldCodec
from .persistence_lazy_nested_history import HISTORY_TYPES
from .persistence_event_ids import EventIdSet


class _IdentityHeaderCodec(WorldCodec):
    def __init__(self, store, pin, *, event_id_root=False):
        store._ensure_open()
        store._require_pin(pin)
        super().__init__(identity_links_recorded=store.codec.identity_links_recorded)
        self._store, self._pin = store, pin
        self._event_id_root = event_id_root

    def _check_event_authority(self, value):
        reference = getattr(value, '_persistence_tracker_ref', None)
        tracker = reference() if reference is not None else None
        if (tracker is None or not tracker._active
                or tracker.store is not self._store
                or tracker._cold_head is None
                or tracker._cold_head.generation != self._pin.captured_head
                or tracker._root_containers.get('world.event_ids') is not value):
            raise StoreConflictError('event ID has a different or closed authority lease')

    def encode(self, value):
        if self._event_id_root and type(value) is EventIdSet:
            self._check_event_authority(value)
            descriptor = value.descriptor()
            if descriptor is not None:
                value = descriptor
            else:
                # Exact resident legacy states retain their accepted portable
                # comparison. This is not a paged equality-directory claim.
                return WorldCodec(identity_links_recorded=self._store.codec.identity_links_recorded).encode(value)
        return super().encode(value)

    def _encode_value(self, value, active, seen_mutable):
        if type(value) is EventIdSet:
            self._check_event_authority(value)
            value = value.storage_reference()
        if type(value) in HISTORY_TYPES:
            if (value._store is not self._store
                    or value._pin.captured_head != self._pin.captured_head):
                raise StoreConflictError('identity history has a different backing lease')
            self._store._require_pin(value._pin)
            value._ensure()
            value = value.storage_reference()
        return super()._encode_value(value, active, seen_mutable)


def encode_identity_header(store, pin, value, *, event_id_root=False):
    """Encode a schema value without traversing any checked history child."""
    return _IdentityHeaderCodec(store, pin, event_id_root=event_id_root).encode(value)
