"""Concrete physical owner contracts for recursive history references.

These adapters describe existing payload authorities, not another ownership
graph. Registration alone does not enable recursive admission or format six.
"""
from dataclasses import dataclass
from types import MappingProxyType

from .incremental_store import Membership, StoreIntegrityError


def _positive(value):
    return type(value) is int and value > 0


def _stored_value(value):
    from .persistence_lazy_nested_history import immutable_value, reference
    if reference(value) or immutable_value(value):
        return True
    return type(value) is tuple and all(_stored_value(item) for item in value)


@dataclass(frozen=True)
class HistoryOwnerAdapter:
    namespace: str
    owner_kind: str
    record_schema: int = 1

    def validate_key(self, key):
        from .persistence_lazy_nested_history import immutable_value
        if type(key) is not tuple or len(key) != 2 or not _positive(key[0]):
            raise StoreIntegrityError('invalid physical history owner key')
        part = key[1]
        valid = (type(part) is int and part >= 0 if self.owner_kind == 'page'
                 else _positive(part) if self.owner_kind == 'leaf'
                 else immutable_value(part))
        if not valid:
            raise StoreIntegrityError('invalid physical history owner key')

    def validate_path(self, path):
        if type(path) is not tuple or any(type(c) is not tuple or len(c) != 2 for c in path):
            raise StoreIntegrityError('invalid physical history member path')
        # Empty is used to check an owner itself; it is not a child placement.
        if not path:
            return
        first = path[0]
        valid = (first[0] == 'index' and type(first[1]) is int and 0 <= first[1] < 128
                 if self.owner_kind == 'page' else first == ('index', 2)
                 if self.owner_kind == 'entry' else first[0] == 'key' and _positive(first[1]))
        if not valid or any(kind != 'index' or type(slot) is not int or slot < 0 for kind, slot in path[1:]):
            raise StoreIntegrityError('invalid physical history member path')

    def absolute_path(self, key, relative=()):
        self.validate_key(key)
        self.validate_path(relative)
        # Disjoint from World paths, which begin with a field component. A
        # sequence member uses a permanent occurrence ID, never its rank/slot.
        return (('key', self.namespace), ('key', key)) + relative

    def validate_source(self, source, storage_kind, codec):
        from .persistence_lazy_nested_history import immutable_value, equality_key
        self.validate_key(source.key)
        if storage_kind != 'lazy' or source.record_schema != self.record_schema:
            raise StoreIntegrityError('physical history owner requires its versioned schema')
        if source.delete:
            return
        value = source.value
        if self.owner_kind == 'page':
            valid = type(value) is tuple and len(value) <= 128 and all(_stored_value(v) for v in value)
            expected_members = ()
        elif self.owner_kind == 'entry':
            valid = (type(value) is tuple and len(value) == 3 and type(value[0]) is int and value[0] >= 0
                     and immutable_value(value[1]) and _stored_value(value[2])
                     and codec.encode(equality_key(value[1])) == codec.encode(source.key[1]))
            expected_members = (Membership('incarnation', source.key[0], value[0]),) if valid else ()
        else:
            valid = (type(value) is tuple and len(value) == 2 and value[0] == 'leaf'
                     and type(value[1]) is tuple and len(value[1]) <= 128
                     and all(type(v) is tuple and len(v) == 2 and _positive(v[0]) and _stored_value(v[1]) for v in value[1])
                     and len({v[0] for v in value[1]}) == len(value[1]))
            expected_members = ()
        if not valid or tuple(source.memberships) != expected_members:
            raise StoreIntegrityError('invalid physical history owner payload or projection')

    def reference_placements(self, value):
        from .persistence_lazy_nested_history import reference
        result = []
        def visit(item, path):
            if reference(item):
                result.append((path, item.incarnation))
            elif type(item) is tuple:
                for slot, child in enumerate(item):
                    visit(child, path + (('index', slot),))
        if self.owner_kind == 'page':
            for slot, item in enumerate(value):
                visit(item, (('index', slot),))
        elif self.owner_kind == 'entry':
            visit(value[2], (('index', 2),))
        else:
            for occurrence, item in value[1]:
                visit(item, (('key', occurrence),))
        return tuple(result)

    def _physical_path(self, value, path):
        self.validate_path(path)
        if not path:
            return ()
        if self.owner_kind != 'leaf':
            return path
        if (type(value) is not tuple or len(value) != 2 or value[0] != 'leaf'
                or type(value[1]) is not tuple or len(value[1]) > 128
                or any(type(entry) is not tuple or len(entry) != 2 or not _positive(entry[0]) for entry in value[1])):
            raise StoreIntegrityError('invalid bounded physical history leaf')
        occurrence = path[0][1]
        matches = [slot for slot, entry in enumerate(value[1]) if entry[0] == occurrence]
        if len(matches) != 1:
            raise StoreIntegrityError('missing or duplicate physical history occurrence')
        return (('index', 1), ('index', matches[0]), ('index', 1)) + path[1:]

    def resolve_path(self, value, path):
        for _, slot in self._physical_path(value, path):
            try:
                value = value[slot]
            except (IndexError, TypeError) as exc:
                raise StoreIntegrityError('physical history member path is absent') from exc
        return value

    def replace_path(self, value, path, replacement):
        physical = self._physical_path(value, path)
        def replace(item, remaining):
            if not remaining:
                return replacement
            _, slot = remaining[0]
            if type(item) is not tuple or slot >= len(item):
                raise StoreIntegrityError('physical history member path is absent')
            values = list(item)
            values[slot] = replace(values[slot], remaining[1:])
            return tuple(values)
        return replace(value, physical)


AUXILIARY_OWNER_FAMILIES = MappingProxyType({
    namespace: HistoryOwnerAdapter(namespace, kind)
    for namespace, kind in (
        ('aux.lazy.nested.list_pages', 'page'),
        ('aux.lazy.nested.entries', 'entry'),
        ('aux.lazy.sequence.nodes', 'leaf'),
    )
})
