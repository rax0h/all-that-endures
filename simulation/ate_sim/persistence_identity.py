"""Bootstrap-built mutable identity occurrence index for P2B/P3B.

Full graph discovery is allowed only at explicit binding/bootstrap or restore
verification. Incremental refreshes rescan changed persistence owners and emit
link deltas for only affected mutable identities. P3B cold projection is
explicitly opt-in and never walks sealed EventLog history.
"""
from dataclasses import is_dataclass

from .event_log import EventLog, FrozenDict, FrozenList


def iter_mutable_event_items(log):
    """Yield (absolute_index, Event) for mutable EventLog tail occurrences.

    Committed disk history and resident pending sealed chunks are value history,
    not current mutable identity owners. This helper deliberately inspects only
    _tail and therefore never decodes a pending chunk or reads a disk segment.
    Individually sealed Events still resident in the tail are skipped.
    """
    if not isinstance(log, EventLog):
        raise TypeError("expected EventLog")
    log._ensure_backend_readable()
    first = log._disk_count + len(log._chunks) * log.chunk_size
    for offset, event in enumerate(log._tail):
        log._ensure_backend_readable()
        if event.__dict__.get("_sealed", False) is True:
            continue
        yield first + offset, event


def iter_mutable_event_owners(log):
    """Yield canonical current LOG owners for the mutable EventLog tail."""
    for index, event in iter_mutable_event_items(log):
        yield (
            ("world.events", index),
            event,
            (("field", "events"), ("index", index)),
        )


class IdentityOccurrenceIndex:
    def __init__(
        self, codec, record_fields, *, mutable_event_tail_only=False
    ):
        self.codec = codec
        self.record_fields = record_fields
        self.mutable_event_tail_only = bool(mutable_event_tail_only)
        self.owner_occurrences = {}
        self.occurrences = {}
        self.links_by_ident = {}
        self.path_to_ident = {}
        self.last_retirement_work = {
            "owners_requested": 0,
            "owners_removed": 0,
            "occurrences_removed": 0,
            "affected_groups": 0,
            "surviving_paths_examined": 0,
            "removed_links": 0,
            "added_links": 0,
        }

    @staticmethod
    def _mutable(value):
        from .persistence_event_ids import EventIdSet
        cls = type(value)
        return (
            isinstance(value, (dict, list, set, EventLog, EventIdSet))
            or getattr(value, "_ate_household_page_sequence", False) is True
            or (is_dataclass(value) and not cls.__dataclass_params__.frozen)
        )

    def _scan(self, value, path, out, active=None):
        if active is None:
            active = set()
        cls = type(value)
        if value is None or cls in (
            bool, int, float, str, bytes, FrozenDict, FrozenList
        ):
            return
        if (
            isinstance(value, EventLog)
            and value._disk_prefix is not None
            and not self.mutable_event_tail_only
        ):
            raise ValueError(
                "disk-backed EventLog identity scanning requires "
                "mutable_event_tail_only=True"
            )
        ident = id(value)
        if ident in active:
            raise ValueError("cycle in bound World identity graph")
        from .persistence_lazy_nested_history import LazyHistoryList
        if type(value) is LazyHistoryList or getattr(value, "_ate_household_page_sequence", False) is True:
            # List-valued identity leaf: its checked ID pages do not contain
            # mutable child objects and are never scanned for alias links.
            out.append((ident, value, path))
            return
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
            elif isinstance(value, EventLog):
                if self.mutable_event_tail_only:
                    items = iter_mutable_event_items(value)
                else:
                    items = enumerate(value)
                for i, child in items:
                    self._scan(
                        child, path + (("index", i),), out, active
                    )
            elif isinstance(value, (list, tuple)):
                for i, child in enumerate(value):
                    self._scan(
                        child, path + (("index", i),), out, active
                    )
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
                raise RuntimeError(
                    "mutable identity address reused while indexed"
                )
            entry[1].add(path)
            self.path_to_ident[path] = ident
        return {ident for ident, _obj, _path in rows}

    def bootstrap(self, owners):
        for owner, value, owner_path in owners:
            self._add_occurrences(owner, value, owner_path)
        self.links_by_ident = {}

    def seed_explicit_links(self, links):
        grouped = {}
        for link in links:
            target, owner = link
            target_ident = self.path_to_ident.get(target)
            owner_ident = self.path_to_ident.get(owner)
            if target_ident is None or target_ident != owner_ident:
                raise RuntimeError(
                    "persisted identity link does not match live graph"
                )
            grouped.setdefault(target_ident, []).append(link)
        self.links_by_ident = {
            ident: tuple(group) for ident, group in grouped.items()
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
            affected.update(
                self._add_occurrences(owner, value, owner_path)
            )

        removed, added = [], []
        for ident in affected:
            before = tuple(self.links_by_ident.get(ident, ()))
            entry = self.occurrences.get(ident)
            after = () if entry is None else tuple(
                self._links_for(entry[1])
            )
            if before == after:
                continue
            before_tokens = {
                self.codec.encode(link): link for link in before
            }
            after_tokens = {
                self.codec.encode(link): link for link in after
            }
            removed.extend(
                before_tokens[token]
                for token in before_tokens.keys() - after_tokens.keys()
            )
            added.extend(
                after_tokens[token]
                for token in after_tokens.keys() - before_tokens.keys()
            )
            if after:
                self.links_by_ident[ident] = after
            else:
                self.links_by_ident.pop(ident, None)
        return removed, added

    @staticmethod
    def _validated_owner_set(owners):
        try:
            owner_set = set(owners)
        except TypeError as exc:
            raise TypeError(
                "retired identity owners must be a hashable owner iterable"
            ) from exc
        for owner in owner_set:
            if type(owner) is not tuple or len(owner) != 2:
                raise ValueError(
                    "identity owners require (namespace, key) tuples"
                )
        return owner_set

    def retire_owners(self, owners):
        """Retire owner occurrence rows as one final-state identity transition."""
        owner_set = self._validated_owner_set(owners)
        affected = set()
        removed_occurrences = 0
        owners_removed = 0

        for owner in owner_set:
            rows = self.owner_occurrences.pop(owner, ())
            if rows:
                owners_removed += 1
            for ident, _obj, path in rows:
                removed_occurrences += 1
                affected.add(ident)
                entry = self.occurrences.get(ident)
                if entry is None:
                    continue
                entry[1].discard(path)
                if self.path_to_ident.get(path) == ident:
                    self.path_to_ident.pop(path, None)
                if not entry[1]:
                    self.occurrences.pop(ident, None)

        removed_tokens = {}
        added_tokens = {}
        surviving_paths = 0
        for ident in affected:
            before = tuple(self.links_by_ident.get(ident, ()))
            entry = self.occurrences.get(ident)
            after = () if entry is None else tuple(
                self._links_for(entry[1])
            )
            if entry is not None:
                surviving_paths += len(entry[1])

            before_tokens = {
                self.codec.encode(link): link for link in before
            }
            after_tokens = {
                self.codec.encode(link): link for link in after
            }
            for token in before_tokens.keys() - after_tokens.keys():
                removed_tokens[token] = before_tokens[token]
            for token in after_tokens.keys() - before_tokens.keys():
                added_tokens[token] = after_tokens[token]

            if after:
                self.links_by_ident[ident] = after
            else:
                self.links_by_ident.pop(ident, None)

        overlap = removed_tokens.keys() & added_tokens.keys()
        for token in overlap:
            removed_tokens.pop(token, None)
            added_tokens.pop(token, None)

        removed = [
            removed_tokens[token] for token in sorted(removed_tokens)
        ]
        added = [added_tokens[token] for token in sorted(added_tokens)]
        self.last_retirement_work = {
            "owners_requested": len(owner_set),
            "owners_removed": owners_removed,
            "occurrences_removed": removed_occurrences,
            "affected_groups": len(affected),
            "surviving_paths_examined": surviving_paths,
            "removed_links": len(removed),
            "added_links": len(added),
        }
        return removed, added

    def diagnostics(self):
        return {
            "owners": len(self.owner_occurrences),
            "occurrences": sum(
                len(rows) for rows in self.owner_occurrences.values()
            ),
            "identities": len(self.occurrences),
            "paths": len(self.path_to_ident),
            "links": sum(
                len(group) for group in self.links_by_ident.values()
            ),
            "last_retirement": dict(self.last_retirement_work),
        }

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
