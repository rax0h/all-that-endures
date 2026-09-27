"""Bootstrap-built mutable identity occurrence index for P2B.

The index is allowed to walk the whole live World only at explicit binding
bootstrap. Later refreshes scan only the persistence owners reported changed by
the mutation tracker. Unrelated EventLog history is never rediscovered on save.
"""
from dataclasses import is_dataclass

from .event_log import EventLog, FrozenDict, FrozenList


class IdentityOccurrenceIndex:
    def __init__(self, codec, record_fields):
        self.codec = codec
        self.record_fields = record_fields
        self.owner_occurrences = {}
        self.occurrences = {}
        self.links_by_ident = {}

    @staticmethod
    def _mutable(value):
        cls = type(value)
        return (
            isinstance(value, (dict, list, set, EventLog))
            or (is_dataclass(value) and not cls.__dataclass_params__.frozen)
        )

    def _scan(self, value, path, out, active=None):
        if active is None:
            active = set()
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes, FrozenDict, FrozenList):
            return
        ident = id(value)
        if ident in active:
            raise ValueError("cycle in bound World identity graph")
        record = is_dataclass(value)
        if self._mutable(value):
            out.append((ident, value, path))
        active.add(ident)
        try:
            if record:
                for name in self.record_fields.get(cls, ()):
                    self._scan(
                        getattr(value, name),
                        path + (("field", name),),
                        out,
                        active,
                    )
            elif isinstance(value, dict):
                # Mutable mapping keys are unsupported by Python itself.
                for key, child in value.items():
                    self._scan(child, path + (("key", key),), out, active)
            elif isinstance(value, (list, tuple, EventLog)):
                for i, child in enumerate(value):
                    self._scan(child, path + (("index", i),), out, active)
            elif isinstance(value, (set, frozenset)):
                # Set elements are hashable; mutable identity cannot be restored
                # by an in-place set path and is outside the supported graph.
                return
        finally:
            active.remove(ident)

    def _add_occurrences(self, owner, value, owner_path):
        rows = []
        self._scan(value, owner_path, rows)
        self.owner_occurrences[owner] = rows
        for ident, obj, path in rows:
            entry = self.occurrences.get(ident)
            if entry is None:
                entry = [obj, set()]
                self.occurrences[ident] = entry
            elif entry[0] is not obj:
                raise RuntimeError("mutable identity address reused while indexed")
            entry[1].add(path)
        return {ident for ident, _obj, _path in rows}

    def bootstrap(self, owners):
        for owner, value, owner_path in owners:
            self._add_occurrences(owner, value, owner_path)
        self._rebuild_all_links()

    def refresh(self, owner, value, owner_path):
        affected = set()
        for ident, _obj, path in self.owner_occurrences.pop(owner, ()):
            affected.add(ident)
            entry = self.occurrences.get(ident)
            if entry is None:
                continue
            entry[1].discard(path)
            if not entry[1]:
                self.occurrences.pop(ident, None)
        if value is not None:
            affected.update(self._add_occurrences(owner, value, owner_path))
        changed = False
        for ident in affected:
            before = self.links_by_ident.get(ident, ())
            entry = self.occurrences.get(ident)
            after = () if entry is None else tuple(self._links_for(entry[1]))
            if tuple(before) != after:
                changed = True
            if after:
                self.links_by_ident[ident] = after
            else:
                self.links_by_ident.pop(ident, None)
        return changed

    def _links_for(self, paths):
        ordered = sorted(paths, key=self.codec.encode)
        if len(ordered) < 2:
            return []
        anchor = ordered[0]
        return [(target, anchor) for target in ordered[1:]]

    def _rebuild_all_links(self):
        self.links_by_ident = {
            ident: tuple(self._links_for(entry[1]))
            for ident, entry in self.occurrences.items()
            if len(entry[1]) > 1
        }

    @staticmethod
    def _suffix(path, prefix):
        if len(prefix) >= len(path) or path[:len(prefix)] != prefix:
            return None
        return path[len(prefix):]

    def links(self):
        links = [link for group in self.links_by_ident.values() for link in group]
        links.sort(
            key=lambda link: (
                len(link[0]),
                self.codec.encode(link[0]),
                self.codec.encode(link[1]),
            )
        )
        kept = []
        for target, owner in links:
            redundant = False
            for parent_target, parent_owner in kept:
                suffix = self._suffix(target, parent_target)
                if suffix is not None and owner == parent_owner + suffix:
                    redundant = True
                    break
            if not redundant:
                kept.append((target, owner))
        return kept
