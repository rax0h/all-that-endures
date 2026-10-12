"""Closed graph pointer to the existing World Event-ID facade authority.

This value owns no members, descriptor, lease or publication. The checked
World owner-zero placement and native facade supply its sole incarnation.
"""
from dataclasses import dataclass

REFERENCE_TAG = 'typed-event-id-authority/v1'


@dataclass(frozen=True, slots=True)
class EventIdReference:
    incarnation: int

    def __post_init__(self):
        if type(self.incarnation) is not int or self.incarnation <= 0:
            raise ValueError('invalid typed Event-ID authority reference')


def event_id_reference(value):
    return type(value) is EventIdReference and type(value.incarnation) is int and value.incarnation > 0


def check_compact_authority(value):
    """Validate the sole root descriptor, without reading its member history."""
    from .persistence_event_ids import RANGE_TAG, EXCEPTION_TAG
    from .incremental_store import StoreIntegrityError
    if (type(value) is tuple and len(value) == 2 and value[0] == RANGE_TAG
            and type(value[1]) is int and value[1] >= 0):
        return
    if type(value) is tuple and value and value[0] == EXCEPTION_TAG:
        from .persistence_event_id_exceptions import checked_descriptor
        checked_descriptor(value)
        return
    raise StoreIntegrityError('Event-ID graph reference has an invalid compact root authority')
