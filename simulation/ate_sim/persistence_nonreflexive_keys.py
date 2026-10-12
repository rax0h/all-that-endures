"""Closed immutable NaN bodies for the existing identity/storage architecture.

These primitives do not enable recursive key admission or a new World format.
Native object identity belongs to LazyIdentityRegistry, not this module.
"""
from dataclasses import dataclass
import math
import struct

from .incremental_store import StoreIntegrityError

NAMESPACE = 'aux.lazy.keys.nan_atoms'
TAG = 'native-nan-key/v1'
REFERENCE_TAG = 'typed-nan-key/v1'
SCHEMA = 1


@dataclass(frozen=True, slots=True)
class NonreflexiveKeyReference:
    incarnation: int

    def __post_init__(self):
        if type(self.incarnation) is not int or self.incarnation <= 0:
            raise ValueError('invalid native NaN key reference')


def nonreflexive_key_reference(value):
    return (type(value) is NonreflexiveKeyReference
            and type(value.incarnation) is int and value.incarnation > 0)


def nonreflexive_key_header(value):
    if type(value) is not float or not math.isnan(value):
        raise TypeError('nonreflexive key body requires a native NaN')
    # One fixed-size authority preserves the native sign and NaN payload bits.
    return TAG, struct.pack('>d', value)


def checked_nonreflexive_key_header(value):
    if (type(value) is not tuple or len(value) != 2 or value[0] != TAG
            or type(value[1]) is not bytes or len(value[1]) != 8
            or not math.isnan(struct.unpack('>d', value[1])[0])):
        raise StoreIntegrityError('invalid native NaN key body')
    return value[1]


def restore_nonreflexive_key_header(value):
    return struct.unpack('>d', checked_nonreflexive_key_header(value))[0]


def read_nonreflexive_key_header(store, pin, incarnation):
    if type(incarnation) is not int or incarnation <= 0:
        raise ValueError('invalid native NaN key incarnation')
    try:
        value = store.read_version(pin, NAMESPACE, (incarnation, 0),
                                   expected_record_schema=SCHEMA).value
    except KeyError as exc:
        raise StoreIntegrityError('mandatory native NaN key body is absent') from exc
    checked_nonreflexive_key_header(value)
    return value
