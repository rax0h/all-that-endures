"""P4 runtime incarnation identity primitives.

This module is intentionally independent of World/session integration.  P2C
current identity links remain sharing authority; this registry only gives live
mutable object incarnations stable runtime identity and current occurrence
placement without archive-sized strong retention.
"""
from __future__ import annotations

from dataclasses import dataclass
import sys
import weakref
from typing import Any, Iterable


class IdentityRegistryError(RuntimeError):
    pass


@dataclass(frozen=True, order=True)
class IncarnationId:
    store_identity: str
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.store_identity, str) or not self.store_identity:
            raise ValueError("store_identity must be non-empty text")
        if type(self.value) is not int or self.value <= 0:
            raise ValueError("incarnation value must be a positive int")


@dataclass(frozen=True)
class Occurrence:
    owner_namespace: str
    owner_key: Any
    path: tuple[Any, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.owner_namespace, str)
            or not self.owner_namespace
            or "\x00" in self.owner_namespace
        ):
            raise ValueError("owner_namespace must be non-empty text")
        if type(self.path) is not tuple:
            raise TypeError("occurrence path must be a tuple")
        try:
            hash(self.owner_key)
            hash(self.path)
        except TypeError as exc:
            raise TypeError("occurrence owner key and path must be hashable") from exc

    @property
    def owner(self) -> tuple[str, Any]:
        return self.owner_namespace, self.owner_key


class IncarnationAllocator:
    """Deterministic storage-local monotonic allocator; never consumes sim RNG."""

    def __init__(self, store_identity: str, next_value: int = 1):
        if not isinstance(store_identity, str) or not store_identity:
            raise ValueError("store_identity must be non-empty text")
        if type(next_value) is not int or next_value <= 0:
            raise ValueError("next_value must be a positive int")
        self.store_identity = store_identity
        self.next_value = next_value

    def allocate(self) -> IncarnationId:
        value = IncarnationId(self.store_identity, self.next_value)
        self.next_value += 1
        return value

    def observe(self, incarnation: IncarnationId) -> None:
        self._check(incarnation)
        if incarnation.value >= self.next_value:
            self.next_value = incarnation.value + 1

    def _check(self, incarnation: IncarnationId) -> None:
        if not isinstance(incarnation, IncarnationId):
            raise TypeError("expected IncarnationId")
        if incarnation.store_identity != self.store_identity:
            raise IdentityRegistryError("incarnation belongs to another store")


class LazyIdentityRegistry:
    """Weak live-object registry plus current occurrence placement.

    The registry never owns registered mutable objects strongly.  Occurrence
    placement stores only IncarnationId values.  A live object can therefore
    outlive every canonical occurrence through an external alias without being
    silently rebound to a later object at the old occurrence.
    """

    def __init__(
        self,
        store_identity: str,
        *,
        next_incarnation: int = 1,
    ):
        self.store_identity = store_identity
        self.allocator = IncarnationAllocator(store_identity, next_incarnation)
        self._by_incarnation: dict[IncarnationId, weakref.ReferenceType[Any]] = {}
        self._by_object_id: dict[
            int, tuple[weakref.ReferenceType[Any], IncarnationId, int]
        ] = {}
        self._occurrences: dict[Occurrence, IncarnationId] = {}
        self._occurrences_by_incarnation: dict[IncarnationId, set[Occurrence]] = {}
        self._next_runtime_token = 1
        self._closed = False

    @property
    def next_incarnation(self) -> int:
        return self.allocator.next_value

    def _ensure_open(self) -> None:
        if self._closed:
            raise IdentityRegistryError("identity registry is closed")

    def _check_incarnation(self, incarnation: IncarnationId) -> None:
        self.allocator._check(incarnation)

    def _cleanup(
        self,
        object_id: int,
        incarnation: IncarnationId,
        token: int,
        reference: weakref.ReferenceType[Any],
    ) -> None:
        """Weakref callback with token/reference checks against id reuse."""
        reverse = self._by_object_id.get(object_id)
        if (
            reverse is not None
            and reverse[0] is reference
            and reverse[1] == incarnation
            and reverse[2] == token
        ):
            self._by_object_id.pop(object_id, None)
        forward = self._by_incarnation.get(incarnation)
        if forward is reference:
            self._by_incarnation.pop(incarnation, None)

    def _install(
        self, obj: Any, incarnation: IncarnationId
    ) -> IncarnationId:
        self._check_incarnation(incarnation)
        object_id = id(obj)
        current = self._by_object_id.get(object_id)
        if current is not None:
            current_obj = current[0]()
            if current_obj is obj:
                if current[1] != incarnation:
                    raise IdentityRegistryError(
                        "one live object cannot have two incarnations"
                    )
                return incarnation
            if current_obj is not None:
                raise IdentityRegistryError(
                    "live object-id collision in identity registry"
                )
            self._by_object_id.pop(object_id, None)

        forward = self._by_incarnation.get(incarnation)
        if forward is not None:
            live = forward()
            if live is obj:
                return incarnation
            if live is not None:
                raise IdentityRegistryError(
                    "incarnation already has a different live mutable object"
                )
            self._by_incarnation.pop(incarnation, None)

        token = self._next_runtime_token
        self._next_runtime_token += 1
        registry_ref = weakref.ref(self)

        def cleanup(reference, *, _id=object_id, _inc=incarnation, _token=token):
            registry = registry_ref()
            if registry is not None:
                registry._cleanup(_id, _inc, _token, reference)

        try:
            reference = weakref.ref(obj, cleanup)
        except TypeError as exc:
            raise TypeError(
                "persistable mutable objects must support weak references"
            ) from exc
        self._by_object_id[object_id] = (reference, incarnation, token)
        self._by_incarnation[incarnation] = reference
        self.allocator.observe(incarnation)
        return incarnation

    def bind(
        self,
        obj: Any,
        occurrence: Occurrence | None = None,
        *,
        incarnation: IncarnationId | None = None,
    ) -> IncarnationId:
        self._ensure_open()
        existing = self.incarnation_for_object(obj)
        if existing is not None:
            if incarnation is not None and incarnation != existing:
                raise IdentityRegistryError(
                    "live object is already bound to another incarnation"
                )
            chosen = existing
        else:
            chosen = incarnation if incarnation is not None else self.allocator.allocate()
            self._install(obj, chosen)
        if occurrence is not None:
            self.attach_occurrence(obj, occurrence)
        return chosen

    def incarnation_for_object(self, obj: Any) -> IncarnationId | None:
        self._ensure_open()
        row = self._by_object_id.get(id(obj))
        if row is None:
            return None
        live = row[0]()
        if live is obj:
            return row[1]
        if live is None:
            self._by_object_id.pop(id(obj), None)
            return None
        raise IdentityRegistryError("object-id collision in identity registry")

    def object_for_incarnation(self, incarnation: IncarnationId) -> Any | None:
        self._ensure_open()
        self._check_incarnation(incarnation)
        reference = self._by_incarnation.get(incarnation)
        if reference is None:
            return None
        value = reference()
        if value is None:
            self._by_incarnation.pop(incarnation, None)
        return value

    def attach_occurrence(
        self, obj: Any, occurrence: Occurrence
    ) -> IncarnationId:
        self._ensure_open()
        if not isinstance(occurrence, Occurrence):
            raise TypeError("expected Occurrence")
        incarnation = self.incarnation_for_object(obj)
        if incarnation is None:
            incarnation = self.bind(obj)
        previous = self._occurrences.get(occurrence)
        if previous == incarnation:
            return incarnation
        if previous is not None:
            old_set = self._occurrences_by_incarnation.get(previous)
            if old_set is not None:
                old_set.discard(occurrence)
                if not old_set:
                    self._occurrences_by_incarnation.pop(previous, None)
        self._occurrences[occurrence] = incarnation
        self._occurrences_by_incarnation.setdefault(incarnation, set()).add(
            occurrence
        )
        return incarnation

    def attach_existing(
        self,
        incarnation: IncarnationId,
        occurrence: Occurrence,
    ) -> None:
        """Attach checked persisted placement even if the object is not loaded."""
        self._ensure_open()
        self._check_incarnation(incarnation)
        if not isinstance(occurrence, Occurrence):
            raise TypeError("expected Occurrence")
        previous = self._occurrences.get(occurrence)
        if previous == incarnation:
            self.allocator.observe(incarnation)
            return
        if previous is not None:
            old_set = self._occurrences_by_incarnation.get(previous)
            if old_set is not None:
                old_set.discard(occurrence)
                if not old_set:
                    self._occurrences_by_incarnation.pop(previous, None)
        self._occurrences[occurrence] = incarnation
        self._occurrences_by_incarnation.setdefault(incarnation, set()).add(
            occurrence
        )
        self.allocator.observe(incarnation)

    def detach_occurrence(
        self,
        occurrence: Occurrence,
        *,
        expected: IncarnationId | None = None,
    ) -> IncarnationId | None:
        self._ensure_open()
        current = self._occurrences.get(occurrence)
        if current is None:
            return None
        if expected is not None and current != expected:
            raise IdentityRegistryError(
                "occurrence no longer belongs to expected incarnation"
            )
        self._occurrences.pop(occurrence, None)
        entries = self._occurrences_by_incarnation.get(current)
        if entries is not None:
            entries.discard(occurrence)
            if not entries:
                self._occurrences_by_incarnation.pop(current, None)
        return current

    def move(
        self,
        obj: Any,
        old: Occurrence,
        new: Occurrence,
    ) -> IncarnationId:
        self._ensure_open()
        incarnation = self.incarnation_for_object(obj)
        if incarnation is None:
            raise IdentityRegistryError("object is not registered")
        if self._occurrences.get(old) != incarnation:
            raise IdentityRegistryError(
                "old occurrence does not belong to object incarnation"
            )
        self.detach_occurrence(old, expected=incarnation)
        self.attach_occurrence(obj, new)
        return incarnation

    def incarnation_for_occurrence(
        self, occurrence: Occurrence
    ) -> IncarnationId | None:
        self._ensure_open()
        return self._occurrences.get(occurrence)

    def occurrences_for_incarnation(
        self, incarnation: IncarnationId
    ) -> tuple[Occurrence, ...]:
        self._ensure_open()
        self._check_incarnation(incarnation)
        return tuple(
            sorted(
                self._occurrences_by_incarnation.get(incarnation, ()),
                key=repr,
            )
        )

    def is_detached(self, obj: Any) -> bool:
        incarnation = self.incarnation_for_object(obj)
        if incarnation is None:
            raise IdentityRegistryError("object is not registered")
        return not self._occurrences_by_incarnation.get(incarnation)

    def derived_owner_groups(self) -> tuple[frozenset[tuple[str, Any]], ...]:
        """Connected owner components induced by shared incarnation occurrences."""
        self._ensure_open()
        adjacency: dict[tuple[str, Any], set[tuple[str, Any]]] = {}
        for occurrences in self._occurrences_by_incarnation.values():
            owners = {occ.owner for occ in occurrences}
            for owner in owners:
                adjacency.setdefault(owner, set()).update(owners - {owner})
        groups = []
        seen = set()
        for owner in sorted(adjacency, key=repr):
            if owner in seen:
                continue
            stack = [owner]
            component = set()
            while stack:
                item = stack.pop()
                if item in component:
                    continue
                component.add(item)
                stack.extend(adjacency.get(item, ()))
            seen.update(component)
            groups.append(frozenset(component))
        return tuple(groups)

    def live_bindings(self):
        """Return currently live incarnation/object pairs without retaining them."""
        self._ensure_open()
        rows = []
        for incarnation, reference in tuple(self._by_incarnation.items()):
            obj = reference()
            if obj is None:
                self._by_incarnation.pop(incarnation, None)
                continue
            rows.append((incarnation, obj))
        rows.sort(key=lambda item: item[0])
        return tuple(rows)

    def diagnostics(self) -> dict[str, int]:
        self._ensure_open()
        live = sum(1 for reference in self._by_incarnation.values() if reference() is not None)
        groups = self.derived_owner_groups()
        max_group = max((len(group) for group in groups), default=0)
        metadata_bytes = (
            sys.getsizeof(self._by_incarnation)
            + sys.getsizeof(self._by_object_id)
            + sys.getsizeof(self._occurrences)
            + sys.getsizeof(self._occurrences_by_incarnation)
        )
        return {
            "live_incarnations": live,
            "weak_forward_entries": len(self._by_incarnation),
            "weak_reverse_entries": len(self._by_object_id),
            "occurrences": len(self._occurrences),
            "incarnations_with_occurrences": len(self._occurrences_by_incarnation),
            "owner_groups": len(groups),
            "max_owner_group_size": max_group,
            "metadata_container_bytes": metadata_bytes,
            "strong_object_roots": 0,
            "next_incarnation": self.next_incarnation,
        }

    def close(self) -> None:
        if self._closed:
            return
        self._by_incarnation.clear()
        self._by_object_id.clear()
        self._occurrences.clear()
        self._occurrences_by_incarnation.clear()
        self._closed = True
