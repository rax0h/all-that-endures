"""Compact schema encoding for checked identity placement comparisons.

The ordinary WorldCodec remains the portable materializing codec. This private
comparison codec retains its closed schema and encodes checked history leases
as references. References do not replace the catalog's owner/group witnesses.
"""
from .incremental_store import StoreConflictError
from .persistence_adapters import WorldCodec
from .persistence_lazy_nested_history import HISTORY_TYPES


class _IdentityHeaderCodec(WorldCodec):
    def __init__(self, store, pin):
        store._ensure_open()
        store._require_pin(pin)
        super().__init__(identity_links_recorded=store.codec.identity_links_recorded)
        self._store, self._pin = store, pin

    def _encode_value(self, value, active, seen_mutable):
        if type(value) in HISTORY_TYPES:
            if (value._store is not self._store
                    or value._pin.captured_head != self._pin.captured_head):
                raise StoreConflictError('identity history has a different backing lease')
            self._store._require_pin(value._pin)
            value._ensure()
            value = value.storage_reference()
        return super()._encode_value(value, active, seen_mutable)


def encode_identity_header(store, pin, value):
    """Encode a schema value without traversing any checked history child."""
    return _IdentityHeaderCodec(store, pin).encode(value)
