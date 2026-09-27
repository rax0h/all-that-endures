"""Bootstrap-built mutable identity occurrence index for P2B.

Full graph discovery is allowed only at explicit binding/bootstrap or restore
verification. Incremental refreshes rescan changed persistence owners and emit
link deltas for only affected mutable identities.
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
        self.path_to_ident = {}

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
                for key, child in value.items():
                    self._scan(child, path + (("key", key),), out, active)
            elif isinstance(value, (list, tuple, EventLog)):
                for i, child in enumerate(value):
                    self._scan(child, path + (("index", i),), out, active)
            elif isinstance(value, (set, frozenset)):
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
            self.path_to_ident[path] = ident
        return {ident for ident, _obj, _path in rows}

    def bootstrap(self, owners):
        for owner, value, owner_path in owners:
            self._add_occurrences(owner, value, owner_path)
        # Explicit persisted links are seeded separately. Bootstrap occurrence
        # discovery must not invent links that a legacy parent alias already
        # implies by containment.
        self.links_by_ident = {}

    def seed_explicit_links(self, links):
        grouped = {}
        for link in links:
            target, owner = link
            target_ident = self.path_to_ident.get(target)
            owner_ident = self.path_to_ident.get(owner)
            if target_ident is None or target_ident != owner_ident:
                raise RuntimeError("persisted identity link does not match live graph")
            grouped.setdefault(target_ident, []).append(link)
        self.links_by_ident = {
            ident: tuple(group)
            for ident, group in grouped.items()
        }

    def refresh(self, owner, value, owner_path):
        """Return (removed_links, added_links) for identities touched by owner."""
        affected = set()
        for ident, _obj, path in self.owner_occurrences.pop(owner, ()):
            affected.add(ident)
            entry = self.occurrences.get(ident)
            if entry is None:
                continue
            entry[1].discard(path)
            self.path_to_ident.pop(path, None)
            if not entry[1]:
                self.occurrences.pop(ident, None)
        if value is not None:
            affected.update(self._add_occurrences(owner, value, owner_path))

        removed, added = [], []
        for ident in affected:
            before = tuple(self.links_by_ident.get(ident, ()))
            entry = self.occurrences.get(ident)
            after = () if entry is None else tuple(self._links_for(entry[1]))
            if before == after:
                continue
            before_tokens = {self.codec.encode(link): link for link in before}
            after_tokens = {self.codec.encode(link): link for link in after}
            removed.extend(before_tokens[token] for token in before_tokens.keys() - after_tokens.keys())
            added.extend(after_tokens[token] for token in after_tokens.keys() - before_tokens.keys())
            if after:
                self.links_by_ident[ident] = after
            else:
                self.links_by_ident.pop(ident, None)
        return removed, added

    @staticmethod
    def _suffix(path, prefix):
        """Compatibility probe for review instrumentation; save no longer uses it."""
        if len(prefix) >= len(path) or path[:len(prefix)] != prefix:
            return None
        return path[len(prefix):]

    def _links_for(self, paths):
        ordered = sorted(paths, key=self.codec.encode)
        if len(ordered) < 2:
            return []
        anchor = ordered[0]
        return [(target, anchor) for target in ordered[1:]]
