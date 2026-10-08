"""P4 checked, generation-pinned household member sequence authority.

This is an auxiliary storage primitive. The canonical Household.members value
remains an ordered mutable sequence, never an abbreviated logical history.
Pages are bounded independently of historical household size; only explicit
whole-sequence operations traverse the complete history.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import MutableSequence
from .incremental_store import Membership, StoreError, StoreIntegrityError, StoreFormatError
from .persistence_lazy_store import (
    VersionChange, _namespace_checksum, _order_checksum, _query_checksum, _version_checksum,
)
from .incremental_store import _framed_sha

LENGTH_NAMESPACE = "aux.lazy.household.member_lengths"
PAGE_NAMESPACE = "aux.lazy.household.member_pages"
BACKING_NAMESPACE = "aux.lazy.household.member_backings"
BACKING_TAG = "paged-members/v1"
RECORD_SCHEMA = 1
PAGE_SIZE = 128
CACHE_PAGES = 4


def backing_token(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and value[0] == BACKING_TAG
            and type(value[1]) is int and value[1] > 0)


def read_backing(store, pin, incarnation, *, required=False):
    """Read within the caller's checked open snapshot, or a checked read API."""
    if getattr(store, "_active_read_transaction", False):
        if store._require_pin(pin) != pin.captured_head:
            raise StoreIntegrityError("household backing pin moved")
        key = store.codec.encode(incarnation)
        row = store._visible_record_row(pin.captured_head, BACKING_NAMESPACE, key)
        if row is None:
            if required:
                raise StoreIntegrityError("household member backing is absent")
            return None
        value, schema, *_ = store._check_record_row(BACKING_NAMESPACE, key, row, decode=True)
        if schema != RECORD_SCHEMA:
            raise StoreFormatError("household member backing schema mismatch")
    else:
        try:
            value = store.read_version(pin, BACKING_NAMESPACE, incarnation,
                                       expected_record_schema=RECORD_SCHEMA).value
        except KeyError as exc:
            if required:
                raise StoreIntegrityError("household member backing is absent") from exc
            return None
    if not (type(value) is int and value > 0) and not backing_token(value):
        raise StoreFormatError("invalid household member backing")
    return value


def stored_members(sequence):
    if sequence._detached_values is not None:
        return list(sequence)
    if not (sequence._descriptor_present or sequence._descriptor_pending):
        return []
    return [BACKING_TAG, sequence._incarnation_value]


def _member_id(value):
    if type(value) is not int or value <= 0:
        raise TypeError("household member IDs must be positive integers")
    return value


def _insert_version(store, generation, namespace, key, value, ordinal):
    codec = store.codec
    typed_key = codec.encode(key)
    payload = codec.encode(value)
    page_members = (
        tuple(("member", member_id, offset)
              for offset, member_id in enumerate(value))
        if namespace == PAGE_NAMESPACE else ()
    )
    memberships = codec.encode(page_members)
    store.db.execute(
        "INSERT INTO lazy_record_versions("
        "namespace,typed_key,valid_from,valid_to,payload,payload_checksum,"
        "codec_version,record_schema,memberships,row_checksum"
        ") VALUES (?,?,?,NULL,?,?,?,?,?,?)",
        (namespace, typed_key, generation, payload,
         _framed_sha(b"lazy-payload-v1", payload), codec.version, RECORD_SCHEMA,
         memberships, _version_checksum(
             namespace, typed_key, RECORD_SCHEMA, codec.version,
             generation, None, memberships, payload,
         )),
    )
    store.db.execute(
        "INSERT INTO lazy_order_versions("
        "namespace,typed_key,ordinal,valid_from,valid_to,row_checksum"
        ") VALUES (?,?,?,?,NULL,?)",
        (namespace, typed_key, ordinal, generation,
         _order_checksum(namespace, typed_key, ordinal, generation, None)),
    )
    for index_name, member, offset in page_members:
        encoded_value = codec.encode(member)
        store.db.execute(
            "INSERT INTO lazy_query_versions("
            "namespace,index_name,index_value,record_key,ordinal,"
            "valid_from,valid_to,row_checksum"
            ") VALUES (?,?,?,?,?,?,NULL,?)",
            (namespace, index_name, encoded_value, typed_key, offset,
             generation, _query_checksum(
                 namespace, index_name, encoded_value, typed_key,
                 offset, generation, None
             )),
        )


def bootstrap_household_members(store, generation, owners):
    """Insert into a private, active conversion transaction only.

    owners: ordered pairs (household_id, ordered member IDs). This is an
    explicit O(history) conversion, never an ordinary open or save path.
    """
    length_rows = []
    page_rows = []
    seen = set()
    for owner, members in owners:
        _member_id(owner)
        if owner in seen:
            raise StoreIntegrityError("duplicate household member owner")
        seen.add(owner)
        size = len(members)
        _insert_version(
            store, generation, LENGTH_NAMESPACE, owner, size,
            len(length_rows),
        )
        length_rows.append(owner)
        for offset in range(0, size, PAGE_SIZE):
            page = tuple(_member_id(x) for x in members[offset:offset+PAGE_SIZE])
            key = (owner, offset // PAGE_SIZE)
            _insert_version(store, generation, PAGE_NAMESPACE, key,
                            page, len(page_rows))
            page_rows.append(key)
    for namespace, rows in (
        (LENGTH_NAMESPACE, length_rows), (PAGE_NAMESPACE, page_rows)
    ):
        store.db.execute(
            "INSERT INTO lazy_namespace_state("
            "namespace,valid_from,valid_to,member_count,next_ordinal,row_checksum"
            ") VALUES (?,?,NULL,?,?,?)",
            (namespace, generation, len(rows), len(rows),
             _namespace_checksum(namespace, len(rows), len(rows),
                                 generation, None)),
        )


class LazyHouseholdMembers(MutableSequence):
    _ate_household_page_sequence = True

    """Mutable list semantics backed by checked, bounded-size versioned pages.

    A retained instance preserves the caller's alias. An owner guard is
    supplied by World/session integration; it must reject obsolete ownership
    and active lifecycle operations before any mutation.
    """

    def __init__(self, store, pin, owner, *, guard=None, cache_pages=CACHE_PAGES, initial_values=None, baseline_length=None):
        if not (type(owner) is int and owner > 0) and not (
            type(owner) is tuple and len(owner) == 2
            and owner[0] == BACKING_TAG and type(owner[1]) is int and owner[1] > 0
        ):
            raise ValueError("invalid household member backing key")
        self._store = store
        self._pin = pin
        self._owner = owner
        self._guard = guard
        self._cache_pages = cache_pages
        if type(cache_pages) is not int or cache_pages <= 0:
            raise ValueError("cache_pages must be positive")
        self._cache = OrderedDict()
        self._dirty_pages = {}
        # P2C current links, not this set, are the sharing authority.
        # This is the derived set of owners currently sharing one live list.
        self._related_owners = {owner}
        self._detached_values = None
        self._new_owner = initial_values is not None and baseline_length is None
        if initial_values is not None:
            if baseline_length is not None and (
                type(baseline_length) is not int or baseline_length < 0
            ):
                raise ValueError("invalid replacement baseline length")
            self._length = 0
            self._base_length = 0 if baseline_length is None else baseline_length
            if baseline_length is None:
                for value in tuple(_member_id(v) for v in initial_values):
                    self._append(value)
            else:
                self._replace_all(initial_values)
            return
        if getattr(store, "_active_read_transaction", False):
            # The P4 open already owns a checked, generation-matched snapshot.
            # Do not start a nested SQLite BEGIN while binding proxies.
            if store._require_pin(pin) != pin.captured_head:
                raise StoreIntegrityError("household member open pin moved")
            typed_key = store.codec.encode(owner)
            row = store._visible_record_row(
                pin.captured_head, LENGTH_NAMESPACE, typed_key
            )
            if row is None:
                raise StoreIntegrityError("household member length is absent")
            length, schema, *_ = store._check_record_row(
                LENGTH_NAMESPACE, typed_key, row, decode=True
            )
            if schema != RECORD_SCHEMA:
                raise StoreFormatError("household member length schema mismatch")
        else:
            checked = store.read_version(
                pin, LENGTH_NAMESPACE, owner, expected_record_schema=RECORD_SCHEMA
            )
            length = checked.value
        if type(length) is not int or length < 0:
            raise StoreFormatError("invalid household member sequence length")
        self._length = length
        self._base_length = length

    def _ensure(self):
        if self._detached_values is None:
            self._store._ensure_open()

    def detach_to_memory(self):
        """Keep a formerly canonical external alias independent of its owner."""
        if self._detached_values is not None:
            return
        values = list(self)
        self._detached_values = values
        self._dirty_pages.clear()
        self._cache.clear()
        self._guard = None
        self._length = len(values)

    def deleted_owner_changes(self, owner=None):
        """Explicit whole-owner deletion may touch its entire page history."""
        if self._new_owner:
            return ()
        key = self._owner if owner is None else owner
        return (
            VersionChange(
                LENGTH_NAMESPACE, key, delete=True,
                record_schema=RECORD_SCHEMA,
            ),
        ) + tuple(
            VersionChange(
                PAGE_NAMESPACE, (key, page), delete=True,
                record_schema=RECORD_SCHEMA,
            )
            for page in range((self._base_length + PAGE_SIZE - 1) // PAGE_SIZE)
        )

    def retire_related_owner(self, key):
        """Retire one sharing path without detaching remaining current aliases."""
        self._related_owners.discard(key)
        if not self._related_owners:
            self.detach_to_memory()
        elif self._owner == key:
            self._owner = min(self._related_owners)
            self._cache.clear()

    def _mutation(self):
        self._ensure()
        if self._guard is not None:
            self._guard()

    def _normalize(self, index):
        if type(index) is not int:
            raise TypeError("household member index must be int")
        if index < 0:
            index += self._length
        if not 0 <= index < self._length:
            raise IndexError("household member index out of range")
        return index

    def _read_page(self, number):
        if number in self._dirty_pages:
            return self._dirty_pages[number]
        if number in self._cache:
            self._cache.move_to_end(number)
            return self._cache[number]
        checked = self._store.read_version(
            self._pin, PAGE_NAMESPACE, (self._owner, number),
            expected_record_schema=RECORD_SCHEMA,
        )
        value = checked.value
        expected = min(PAGE_SIZE, max(0, self._base_length - PAGE_SIZE * number))
        if (type(value) is not tuple or len(value) != expected
                or any(type(x) is not int or x <= 0 for x in value)):
            raise StoreIntegrityError("invalid household member sequence page")
        self._cache[number] = value
        while len(self._cache) > self._cache_pages:
            self._cache.popitem(last=False)
        return value

    def _page(self, number):
        if number in self._dirty_pages:
            return self._dirty_pages[number]
        if number * PAGE_SIZE >= self._base_length:
            page = []
        else:
            page = list(self._read_page(number))
        self._dirty_pages[number] = page
        return page

    def __len__(self):
        self._ensure()
        return len(self._detached_values) if self._detached_values is not None else self._length

    def __getitem__(self, index):
        self._ensure()
        if self._detached_values is not None:
            return self._detached_values[index]
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self._length))]
        index = self._normalize(index)
        return self._read_page(index // PAGE_SIZE)[index % PAGE_SIZE]

    def __contains__(self, value):
        self._ensure()
        if self._detached_values is not None:
            return value in self._detached_values
        if type(value) is not int or value <= 0:
            # Preserve Python list equality, e.g. 1.0 or True matching
            # stored ID 1. Such unusual probes are explicit full operations.
            return any(member == value for member in self)
        for page in self._dirty_pages.values():
            if value in page:
                return True
        # A checked index query scales with actual occurrences, not with
        # all historical member IDs. Dirty pages override their old snapshot
        # memberships, so skip those candidates.
        for owner, number in self._store.query_keys(
            self._pin, PAGE_NAMESPACE, "member", value
        ):
            if owner == self._owner and number not in self._dirty_pages:
                return True
        return False

    def __setitem__(self, index, value):
        self._mutation()
        if self._detached_values is not None:
            if isinstance(index, slice):
                self._detached_values[index] = [_member_id(x) for x in value]
            else:
                self._detached_values[index] = _member_id(value)
            self._length = len(self._detached_values)
            return
        if isinstance(index, slice):
            new = list(self)
            replacement = [_member_id(x) for x in value]
            new[index] = replacement
            self._replace_all(new)
            return
        index = self._normalize(index)
        self._page(index // PAGE_SIZE)[index % PAGE_SIZE] = _member_id(value)

    def __delitem__(self, index):
        self._mutation()
        if self._detached_values is not None:
            del self._detached_values[index]
            self._length = len(self._detached_values)
            return
        if isinstance(index, slice):
            new = list(self)
            del new[index]
            self._replace_all(new)
            return
        index = self._normalize(index)
        self._replace_all(list(self[:index]) + list(self[index+1:]))

    def insert(self, index, value):
        self._mutation()
        _member_id(value)
        if self._detached_values is not None:
            self._detached_values.insert(index, value)
            self._length = len(self._detached_values)
            return
        if type(index) is not int:
            raise TypeError("household member insertion index must be int")
        if index < 0:
            index = max(0, index + self._length)
        if index >= self._length:
            self._append(value)
            return
        self._replace_all(list(self[:index]) + [value] + list(self[index:]))

    def _append(self, value):
        if self._detached_values is not None:
            self._detached_values.append(value)
            self._length = len(self._detached_values)
            return
        page_index = self._length // PAGE_SIZE
        page = self._page(page_index)
        if len(page) != self._length % PAGE_SIZE:
            raise StoreIntegrityError("household member append page is inconsistent")
        page.append(value)
        self._length += 1

    def append(self, value):
        self._mutation()
        self._append(_member_id(value))

    def extend(self, values):
        self._mutation()
        # Consume iterables before modifying the sequence; failed input
        # validation must not partially publish a caller mutation.
        values = tuple(_member_id(v) for v in values)
        for value in values:
            self._append(value)

    def _replace_all(self, values):
        values = tuple(_member_id(v) for v in values)
        if self._detached_values is not None:
            self._detached_values[:] = values
            self._length = len(values)
            return
        previous_page_count = (max(self._length, self._base_length) + PAGE_SIZE - 1) // PAGE_SIZE
        next_page_count = (len(values) + PAGE_SIZE - 1) // PAGE_SIZE
        for number in range(max(previous_page_count, next_page_count)):
            start = number * PAGE_SIZE
            self._dirty_pages[number] = list(values[start:start+PAGE_SIZE])
        self._length = len(values)
        self._cache.clear()

    def reverse(self):
        self._mutation()
        self._replace_all(list(reversed(list(self))))

    def sort(self, *, key=None, reverse=False):
        self._mutation()
        self._replace_all(sorted(self, key=key, reverse=reverse))

    def copy(self):
        return list(self)

    def __iter__(self):
        # One checked page at a time. No implicit archive-sized tuple.
        for index in range(len(self)):
            yield self[index]

    def __eq__(self, other):
        if isinstance(other, (list, LazyHouseholdMembers)):
            return list(self) == list(other)
        return NotImplemented

    def __add__(self, other):
        if not isinstance(other, (list, LazyHouseholdMembers)):
            return NotImplemented
        return list(self) + list(other)

    def __radd__(self, other):
        if not isinstance(other, list):
            return NotImplemented
        return other + list(self)

    def __mul__(self, count):
        return list(self) * count

    __rmul__ = __mul__

    def __imul__(self, count):
        self._mutation()
        self._replace_all(list(self) * count)
        return self

    def __repr__(self):
        return f"LazyHouseholdMembers(owner={self._owner}, length={self._length})"

    def pending_changes(self):
        """Return only changed bounded pages and length, never all history."""
        self._ensure()
        if self._detached_values is not None:
            return ()
        result = []
        base_pages = (self._base_length + PAGE_SIZE - 1) // PAGE_SIZE
        final_pages = (self._length + PAGE_SIZE - 1) // PAGE_SIZE
        if self._new_owner or self._length != self._base_length:
            result.append(VersionChange(
                LENGTH_NAMESPACE, self._owner, self._length,
                record_schema=RECORD_SCHEMA,
            ))
        for number, page in sorted(self._dirty_pages.items()):
            key = (self._owner, number)
            if number >= final_pages:
                if number < base_pages:
                    result.append(VersionChange(
                        PAGE_NAMESPACE, key, delete=True,
                        record_schema=RECORD_SCHEMA,
                    ))
                continue
            value = tuple(page)
            expected_len = min(PAGE_SIZE, self._length - number * PAGE_SIZE)
            if len(value) != expected_len:
                raise StoreIntegrityError("incomplete household member page")
            if number < base_pages and value == tuple(self._read_baseline_page(number)):
                continue
            result.append(VersionChange(
                PAGE_NAMESPACE, key, value, record_schema=RECORD_SCHEMA,
                memberships=tuple(
                    Membership("member", member, offset)
                    for offset, member in enumerate(value)
                ),
            ))
        # A P2C sharing group has one live list and a checked owner-local
        # physical projection for every linked household. Replicate only
        # the changed bounded pages to every current owner.
        # Session-owned sequences have one stable physical authority. Legacy
        # standalone sequences retain the original projection behavior.
        if hasattr(self, "_incarnation_value"):
            return tuple(result)
        owners = tuple(sorted(self._related_owners))
        if owners == (self._owner,):
            return tuple(result)
        expanded = []
        for change in result:
            for owner in owners:
                if change.namespace == LENGTH_NAMESPACE:
                    key = owner
                else:
                    key = (owner, change.key[1])
                expanded.append(VersionChange(
                    change.namespace, key, change.value,
                    record_schema=change.record_schema,
                    delete=change.delete,
                    memberships=change.memberships,
                ))
        return tuple(expanded)

    def _read_baseline_page(self, number):
        checked = self._store.read_version(
            self._pin, PAGE_NAMESPACE, (self._owner, number),
            expected_record_schema=RECORD_SCHEMA,
        )
        return checked.value

    def accept_save(self, pin):
        """Advance to the committed generation only after combined publication."""
        if self._detached_values is not None:
            return
        self._pin = pin
        self._base_length = self._length
        self._new_owner = False
        self._dirty_pages.clear()
        self._cache.clear()

    def diagnostics(self):
        return {
            "owner": self._owner, "length": self._length,
            "base_length": self._base_length, "resident_cached_pages": len(self._cache),
            "dirty_pages": len(self._dirty_pages),
            "cached_member_ids": sum(len(p) for p in self._cache.values()),
            "dirty_member_ids": sum(len(p) for p in self._dirty_pages.values()),
        }

