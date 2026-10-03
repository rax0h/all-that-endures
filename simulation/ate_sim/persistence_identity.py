"""Mutable identity occurrence indexing for P2B/P3B.

Full graph discovery is allowed only at explicit binding/bootstrap or restore
verification. Incremental refreshes rescan changed persistence owners and emit
link deltas for only affected mutable identities.

P3B cold identity projection is opt-in: sealed EventLog history is immutable
value history and must not become mutable identity ownership.
"""
from dataclasses import is_dataclass

from .event_log import EventLog, FrozenDict, FrozenList


def iter_mutable_event_items(log):
    """Yield only mutable EventLog tail occurrences as (absolute_index, Event).

    This is deliberately an internal identity boundary. It never enumerates the
    logical log, decodes pending chunks, or reads committed disk segments.
    """
    if not isinstance(log, EventLog):
        raise TypeError("expected EventLog")
    log._ensure_backend_readable()
    first = log._disk_count + len(log._chunks) * log.chunk_size
    for offset, event in enumerate(log._tail):
        log._ensure_backend_readable()
        if event.__dict__.get("_sealed") is True:
            continue
        yield first + offset, event


def iter_mutable_event_owners(log):
    """Yield canonical owner triples for mutable World.events tail Events."""
    for index, event in iter_mutable_event_items(log):
        yield (
            ("world.events", index),
            event,
            (("field", "events"), ("index", index)),
        )


class IdentityOccurrenceIndex:
    def __init__(self, codec, record_fields, *, mutable_event_tail_only=False):
        if type(mutable_event_tail_only) is not bool:
            raise TypeError("mutable_event_tail_only must be bool")
        self.codec = codec
        self.record_fields = record_fields
        self.mutable_event_tail_only = mutable_event_tail_only
        self.owner_occurrences = {}
        self.occurrences = {}
        self.links_by_ident = {}
        self.path_to_ident = {}
        self.last_retirement_work = {
            "owners": 0,
            "occurrences": 0,
            "identities": 0,
        }

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
                "disk-backed EventLog identity scan requires "
                "mutable_event_tail_only=True"
            )
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
                    self._scan(
                        child, path + (("key", key),), out, active
                    )
            elif isinstance(value, EventLog):
                if self.mutable_event_tail_only:
                    items = iter_mutable_event_items(value)
                else:
                    items = enumerate(value)
                for index, child in items:
                    self._scan(
                        child,
                        path + (("index", index),),
                        out,
                        active,
                    )
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value):
                    self._scan(
                        child,
                        path + (("index", index),),
                        out,
                        active,
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
                raise RuntimeError(
                    "persisted identity link does not match live graph"
                )
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

    def retire_owners(self, owners):
        """Retire owner occurrence rows as one final-state identity transition."""
        # Consume and hash the entire request before mutating the index. A bad
        # generator element or unhashable owner therefore cannot half-apply.
        retiring = set(owners)
        affected = set()
        removed_occurrences = 0

        for owner in retiring:
            rows = self.owner_occurrences.pop(owner, ())
            removed_occurrences += len(rows)
            for ident, _obj, path in rows:
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
        for ident in affected:
            before = tuple(self.links_by_ident.get(ident, ()))
            entry = self.occurrences.get(ident)
            after = () if entry is None else tuple(self._links_for(entry[1]))

            before_by_token = {
                self.codec.encode(link): link for link in before
            }
            after_by_token = {
                self.codec.encode(link): link for link in after
            }
            for token in before_by_token.keys() - after_by_token.keys():
                removed_tokens[token] = before_by_token[token]
            for token in after_by_token.keys() - before_by_token.keys():
                added_tokens[token] = after_by_token[token]

            if after:
                self.links_by_ident[ident] = after
            else:
                self.links_by_ident.pop(ident, None)

        # A final patch must never ask a caller to remove and add the same link.
        overlap = removed_tokens.keys() & added_tokens.keys()
        for token in overlap:
            removed_tokens.pop(token, None)
            added_tokens.pop(token, None)

        self.last_retirement_work = {
            "owners": len(retiring),
            "occurrences": removed_occurrences,
            "identities": len(affected),
        }
        return (
            [removed_tokens[token] for token in sorted(removed_tokens)],
            [added_tokens[token] for token in sorted(added_tokens)],
        )

    def diagnostics(self):
        return {
            "owners": len(self.owner_occurrences),
            "occurrences": sum(
                len(rows) for rows in self.owner_occurrences.values()
            ),
            "identities": len(self.occurrences),
            "paths": sum(
                len(entry[1]) for entry in self.occurrences.values()
            ),
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
