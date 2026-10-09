"""Generation-pinned completeness witnesses for the current identity relation.

Authority uses existing checked MVCC versions and the existing hybrid commit.
No ordinary-open migration, separate transaction, or live-object registry lives
here. The authenticated owner radix directory lets a sharing-group read prove
one exact placement without enumerating a large owner's other identities.
"""
from __future__ import annotations
from dataclasses import dataclass
from .incremental_store import Membership, StoreIntegrityError, StoreFormatError, _framed_sha
from .persistence_lazy_store import VersionChange
from .persistence_lazy_families import FAMILIES, ParticipantDelta

CATALOG_NAMESPACE = 'aux.lazy.identity.catalog'
GROUP_NAMESPACE = 'aux.lazy.identity.groups'
OWNER_NAMESPACE = 'aux.lazy.identity.owners'
OWNER_TREE_NAMESPACE = 'aux.lazy.identity.owner_tree'
RETIRED_NAMESPACE = 'aux.lazy.identity.retired'
LINK_NAMESPACE = 'world_identity_links'
CATALOG_TAG = 'identity-catalog/v1'
SCHEMA = 1
CATALOG_NAMESPACES = (CATALOG_NAMESPACE, GROUP_NAMESPACE, OWNER_NAMESPACE,
                      OWNER_TREE_NAMESPACE, RETIRED_NAMESPACE, LINK_NAMESPACE)
FEATURES = ('complete-groups/v1', 'owner-radix/v1', 'versioned-p2c/v1')


def digest(codec, domain, values):
    return _framed_sha(domain, *(sorted(codec.encode(v) for v in values)))


def placement_path(namespace, key, path):
    if namespace not in FAMILIES:
        raise StoreFormatError(f'identity owner family is not registered: {namespace}')
    if type(path) is not tuple or any(type(c) is not tuple or len(c) != 2
        or c[0] not in ('field', 'key', 'index')
        or (c[0] == 'field' and (type(c[1]) is not str or not c[1]))
        or (c[0] == 'index' and (type(c[1]) is not int or c[1] < 0)) for c in path):
        raise StoreIntegrityError('invalid identity placement path')
    return FAMILIES[namespace].absolute_path(key, path)


def path_hash(codec, path):
    return bytes.fromhex(_framed_sha(b'identity-owner-path-v1', codec.encode(path)))


def node_commit(codec, value):
    if type(value) is not tuple or not value:
        raise StoreIntegrityError('invalid owner tree node')
    if value[0] == 'owner-leaf/v1' and len(value) == 3:
        path, inc = value[1:]
        if type(path) is not tuple or type(inc) is not int or inc < 1:
            raise StoreIntegrityError('invalid owner tree leaf')
        return 1, _framed_sha(b'identity-owner-node-v1', codec.encode(value))
    if value[0] == 'owner-branch/v1' and len(value) == 3:
        prefix, children = value[1:]
        if type(prefix) is not bytes or len(prefix) >= 32 or type(children) is not tuple or not 2 <= len(children) <= 256:
            raise StoreIntegrityError('invalid owner tree branch')
        previous = -1
        count = 0
        for child in children:
            if type(child) is not tuple or len(child) != 4:
                raise StoreIntegrityError('invalid owner tree child commitment')
            slot, child_prefix, size, child_digest = child
            if (type(slot) is not int or not previous < slot < 256 or type(child_prefix) is not bytes
                or not child_prefix.startswith(prefix) or not len(prefix) < len(child_prefix) <= 32
                or child_prefix[len(prefix)] != slot or type(size) is not int or size < 1
                or type(child_digest) is not str or len(child_digest) != 64):
                raise StoreIntegrityError('invalid owner tree child order/count')
            previous = slot
            count += size
        return count, _framed_sha(b'identity-owner-node-v1', codec.encode(value))
    raise StoreIntegrityError('unsupported owner tree node kind')


def initial_owner_tree(codec, owner, placements):
    """Explicit conversion only. Ordinary updates use affected paths later."""
    rows = [(path_hash(codec, path), path, inc) for path, inc in placements]
    if len({row[0] for row in rows}) != len(rows):
        raise StoreIntegrityError('duplicate/colliding owner occurrence paths')
    changes = []
    def build(items):
        if len(items) == 1:
            prefix, path, inc = items[0]
            value = ('owner-leaf/v1', path, inc)
        else:
            first = items[0][0]
            length = 0
            while length < 32 and all(item[0][length] == first[length] for item in items):
                length += 1
            prefix = first[:length]
            buckets = {}
            for item in items:
                buckets.setdefault(item[0][length], []).append(item)
            children = tuple((slot, *build(part)) for slot, part in sorted(buckets.items()))
            value = ('owner-branch/v1', prefix, children)
        count, checksum = node_commit(codec, value)
        changes.append(VersionChange(OWNER_TREE_NAMESPACE, (*owner, prefix), value))
        return prefix, count, checksum
    if not rows:
        return None, 0, _framed_sha(b'identity-owner-empty-v1'), ()
    prefix, count, checksum = build(rows)
    return prefix, count, checksum, tuple(changes)


def initial_catalog_delta(codec, owner_versions, identity_changes, *, next_incarnation_id, generation):
    """Freeze a complete explicit conversion; this does not publish a format floor."""
    if type(next_incarnation_id) is not int or next_incarnation_id < 1:
        raise ValueError('invalid incarnation allocator')
    owners = {(v.namespace, codec.encode(v.key)): v for v in owner_versions if not v.delete}
    by_owner = {}
    by_group = {}
    seen = set()
    for change in identity_changes:
        if change.delete or type(change.incarnation_id) is not int or not 0 < change.incarnation_id < next_incarnation_id:
            raise ValueError('initial catalog requires live allocated occurrences')
        placement_path(change.owner_namespace, change.owner_key, change.occurrence_path)
        marker = change.owner_namespace, codec.encode(change.owner_key), codec.encode(change.occurrence_path)
        if marker in seen or (marker[0], marker[1]) not in owners:
            raise ValueError('duplicate occurrence or missing owner source')
        seen.add(marker)
        by_owner.setdefault((marker[0], marker[1]), []).append((change.occurrence_path, change.incarnation_id))
        by_group.setdefault(change.incarnation_id, []).append((change.owner_namespace, change.owner_key, change.occurrence_path))
    changes = []
    for marker, version in owners.items():
        owner = version.namespace, version.key
        prefix, count, root_digest, nodes = initial_owner_tree(codec, owner, by_owner.get(marker, ()))
        changes.extend(nodes)
        payload_commit = _framed_sha(b'lazy-payload-v1', codec.encode(version.value))
        value = ('identity-owner/v1', True, 'lazy', generation, version.record_schema,
                 payload_commit, prefix, count, root_digest)
        changes.append(VersionChange(OWNER_NAMESPACE, owner, value))
    for inc in range(1, next_incarnation_id):
        occurrences = by_group.get(inc, ())
        paths = sorted((placement_path(*o) for o in occurrences), key=codec.encode)
        links = tuple((target, paths[0]) for target in paths[1:])
        for ordinal, (target, anchor) in enumerate(links):
            changes.append(VersionChange(LINK_NAMESPACE, target, ('identity-link/v1', inc, anchor),
                           memberships=(Membership('incarnation', inc, ordinal),)))
        value = ('identity-group/v1', 'mutable', len(occurrences),
                 digest(codec, b'identity-group-occurrences-v1', occurrences), len(links),
                 digest(codec, b'identity-group-links-v1', links), paths[0] if paths else None)
        changes.append(VersionChange(GROUP_NAMESPACE, inc, value))
    # Checked empty retirement directory is mandatory, not inferred from absence.
    changes.append(VersionChange(RETIRED_NAMESPACE, 0, ('identity-retired-directory/v1', 0, None)))
    changes.append(VersionChange(CATALOG_NAMESPACE, 0,
                   (CATALOG_TAG, FEATURES, next_incarnation_id, next_incarnation_id - 1,
                    ('identity-retired-directory/v1', 0, None))))
    # An explicit delete of an absent key declares a checked empty namespace
    # without inventing a live record or competing relation.
    populated = {change.namespace for change in changes}
    changes.extend(VersionChange(ns, ('empty-catalog-declaration/v1',), delete=True)
                   for ns in CATALOG_NAMESPACES if ns not in populated)
    return ParticipantDelta.freeze(codec, 'identity-catalog', version_changes=changes)


@dataclass(frozen=True)
class CheckedIdentityGroup:
    incarnation_id: int
    occurrences: tuple
    links: tuple
    anchor: tuple | None


@dataclass(frozen=True)
class CheckedOwnerIdentity:
    owner: tuple
    occurrences: tuple
    payload_revision: int
    payload_commitment: str
    exists: bool = True


class IdentityCatalog:
    def __init__(self, store):
        self.store = store
        self.codec = store.codec

    def _read(self, pin, namespace, key):
        try:
            return self.store.read_version(pin, namespace, key, expected_record_schema=SCHEMA).value
        except KeyError as exc:
            raise StoreIntegrityError(f'missing required identity authority in {namespace}') from exc

    def _descriptor(self, pin):
        for ns in CATALOG_NAMESPACES:
            if self.store._namespace_state_at(ns, pin.captured_head) is None:
                raise StoreIntegrityError(f'missing identity catalog namespace: {ns}')
        value = self._read(pin, CATALOG_NAMESPACE, 0)
        if (type(value) is not tuple or len(value) != 5 or value[0] != CATALOG_TAG
            or value[1] != FEATURES or type(value[2]) is not int or value[2] < 1
            or type(value[3]) is not int or value[3] < 0):
            raise StoreFormatError('identity catalog descriptor schema/capabilities mismatch')
        if value[2] != self.store._identity_state_at(pin.captured_head)[0]:
            raise StoreIntegrityError('identity catalog allocator disagreement')
        retired = self._read(pin, RETIRED_NAMESPACE, 0)
        if retired != value[4] or retired != ('identity-retired-directory/v1', 0, None):
            raise StoreIntegrityError('identity retirement directory commitment mismatch')
        return value

    def _owner(self, pin, owner):
        header = self._read(pin, OWNER_NAMESPACE, owner)
        if (type(header) is not tuple or len(header) != 9 or header[0] != 'identity-owner/v1'
            or type(header[1]) is not bool or header[2] != 'lazy' or type(header[3]) is not int
            or not 0 <= header[3] <= pin.captured_head or type(header[4]) is not int or header[4] < 1
            or type(header[5]) is not str or len(header[5]) != 64 or type(header[7]) is not int or header[7] < 0
            or type(header[8]) is not str or len(header[8]) != 64
            or (header[6] is not None and (type(header[6]) is not bytes or len(header[6]) > 32))):
            raise StoreIntegrityError('invalid identity owner witness')
        # Metadata-only agreement; actual payload checksum is checked on payload
        # access. Historical metadata comes from MVCC, never current ordinary rows.
        rows = self.store.db.execute('SELECT valid_from,record_schema,payload_checksum FROM lazy_record_versions '
            'WHERE namespace=? AND typed_key=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) LIMIT 2',
            (owner[0], self.codec.encode(owner[1]), pin.captured_head, pin.captured_head)).fetchall()
        self.store._metadata_rows += len(rows)
        if (header[1] and (len(rows) != 1 or rows[0] != (header[3], header[4], header[5]))) or (not header[1] and (rows or header[7] != 0)):
            raise StoreIntegrityError('identity owner/header commitment disagreement')
        if (header[7] == 0) != (header[6] is None):
            raise StoreIntegrityError('identity owner root/count mismatch')
        if header[6] is None and header[8] != _framed_sha(b'identity-owner-empty-v1'):
            raise StoreIntegrityError('identity owner empty commitment mismatch')
        return header

    def _node(self, pin, owner, prefix, expected_count, expected_digest):
        node = self._read(pin, OWNER_TREE_NAMESPACE, (*owner, prefix))
        count, checksum = node_commit(self.codec, node)
        if count != expected_count or checksum != expected_digest:
            raise StoreIntegrityError('identity owner tree count/digest disagreement')
        if node[0] == 'owner-leaf/v1':
            if path_hash(self.codec, node[1]) != prefix:
                raise StoreIntegrityError('identity owner leaf locator mismatch')
        elif node[1] != prefix:
            raise StoreIntegrityError('identity owner branch locator mismatch')
        return node

    def _point(self, pin, owner, path, incarnation, header):
        wanted = path_hash(self.codec, path)
        prefix, count, checksum = header[6:]
        while prefix is not None:
            node = self._node(pin, owner, prefix, count, checksum)
            if not wanted.startswith(prefix):
                break
            if node[0] == 'owner-leaf/v1':
                if node[1:] == (path, incarnation):
                    row = self.store.read_identity_occurrence(pin, owner[0], owner[1], path)
                    if row.incarnation_id == incarnation:
                        return
                break
            child = next((c for c in node[2] if c[0] == wanted[len(prefix)]), None)
            if child is None:
                break
            _, prefix, count, checksum = child
        raise StoreIntegrityError('identity group disagrees with exact owner membership')

    def read_owner_identity(self, pin, owner):
        with self.store.read_snapshot(pin):
            self._descriptor(pin)
            header = self._owner(pin, owner)
            actual = self.store.identity_occurrences_for_owner(pin, *owner)
            leaves = []
            def walk(prefix, count, checksum):
                node = self._node(pin, owner, prefix, count, checksum)
                if node[0] == 'owner-leaf/v1':
                    leaves.append(node[1:])
                else:
                    for _slot, child, child_count, child_checksum in node[2]:
                        walk(child, child_count, child_checksum)
            if header[6] is not None:
                walk(*header[6:])
            if len(actual) != header[7] or sorted(actual, key=self.codec.encode) != sorted(leaves, key=self.codec.encode):
                raise StoreIntegrityError('identity owner occurrence completeness mismatch')
            for path, inc in actual:
                placement_path(*owner, path)
                if type(inc) is not int or not 0 < inc < self.store._identity_state_at(pin.captured_head)[0]:
                    raise StoreIntegrityError('owner occurrence exceeds allocator')
            return CheckedOwnerIdentity(owner, tuple(actual), header[3], header[5], header[1])

    def read_identity_membership(self, pin, owner, path):
        """Prove an exact path's membership or absence through its owner root."""
        placement_path(*owner, path)
        with self.store.read_snapshot(pin):
            self._descriptor(pin)
            try:
                header = self._owner(pin, owner)
            except StoreIntegrityError:
                raw = self.store._visible_record_row(pin.captured_head, owner[0], self.codec.encode(owner[1]))
                witness = self.store._visible_record_row(pin.captured_head, OWNER_NAMESPACE, self.codec.encode(owner))
                if raw is None and witness is None:
                    return None  # No persisted owner; caller may prepare a new one.
                raise
            wanted = path_hash(self.codec, path)
            prefix, count, checksum = header[6:]
            found = None
            while prefix is not None:
                node = self._node(pin, owner, prefix, count, checksum)
                if not wanted.startswith(prefix):
                    break
                if node[0] == 'owner-leaf/v1':
                    if node[1] != path:
                        raise StoreIntegrityError('owner path hash collision')
                    found = node[2]
                    break
                child = next((c for c in node[2] if c[0] == wanted[len(prefix)]), None)
                if child is None:
                    break
                _, prefix, count, checksum = child
            try:
                forward = self.store.read_identity_occurrence(pin, *owner, path).incarnation_id
            except KeyError:
                forward = None
            if found != forward:
                raise StoreIntegrityError('exact owner membership disagrees with occurrence authority')
            return found

    def read_identity_group(self, pin, incarnation_id):
        if type(incarnation_id) is not int or incarnation_id < 1:
            raise ValueError('incarnation_id must be a positive int')
        with self.store.read_snapshot(pin):
            descriptor = self._descriptor(pin)
            if incarnation_id >= descriptor[2]:
                raise StoreIntegrityError('identity incarnation exceeds catalog allocator')
            header = self._read(pin, GROUP_NAMESPACE, incarnation_id)
            if (type(header) is not tuple or len(header) != 7 or header[0] != 'identity-group/v1'
                or header[1] != 'mutable' or type(header[2]) is not int or header[2] < 0
                or type(header[4]) is not int or header[4] != max(0, header[2] - 1)):
                raise StoreIntegrityError('identity group header schema/count mismatch')
            occurrences = self.store.identity_occurrences_for_incarnation(pin, incarnation_id)
            if len(occurrences) != header[2] or digest(self.codec, b'identity-group-occurrences-v1', occurrences) != header[3]:
                raise StoreIntegrityError('identity group count/digest completeness mismatch')
            paths = sorted((placement_path(*o) for o in occurrences), key=self.codec.encode)
            anchor = paths[0] if paths else None
            expected = tuple((target, anchor) for target in paths[1:])
            if anchor != header[6] or digest(self.codec, b'identity-group-links-v1', expected) != header[5]:
                raise StoreIntegrityError('identity group P2C commitment mismatch')
            owner_headers = {}
            for namespace, key, path in occurrences:
                owner = namespace, key
                marker = namespace, self.codec.encode(key)
                if marker not in owner_headers:
                    owner_headers[marker] = self._owner(pin, owner)
                self._point(pin, owner, path, incarnation_id, owner_headers[marker])
            projected = self.store.query_memberships(pin, LINK_NAMESPACE, 'incarnation', incarnation_id)
            if len(projected) != len(expected) or len({self.codec.encode(target) for target, _ in projected}) != len(expected):
                raise StoreIntegrityError('identity link projection count/completeness mismatch')
            actual = []
            for target, _ordinal in projected:
                value = self._read(pin, LINK_NAMESPACE, target)
                if value != ('identity-link/v1', incarnation_id, anchor):
                    raise StoreIntegrityError('identity P2C link owner/incarnation disagreement')
                actual.append((target, value[2]))
            if sorted(actual, key=self.codec.encode) != sorted(expected, key=self.codec.encode):
                raise StoreIntegrityError('identity P2C links disagree with current placements')
            return CheckedIdentityGroup(incarnation_id, tuple(occurrences), tuple(expected), anchor)

    def read_identity_links(self, pin, incarnation_id):
        return self.read_identity_group(pin, incarnation_id).links

    def prepare_delta(self, pin, owner_versions, identity_changes, *, next_incarnation_id):
        return _prepare_catalog_delta(self, pin, owner_versions, identity_changes,
                                      next_incarnation_id=next_incarnation_id)

    def validate_publication(self, delta, successor_pin):
        if delta.participant != 'identity-catalog':
            raise ValueError('wrong participant delta')
        expected = _framed_sha(b'save-participant-v1', self.codec.encode(delta.participant),
                              self.codec.encode((delta.version_bytes, delta.ordinary_bytes, delta.identity_bytes)))
        if expected != delta.fingerprint:
            raise StoreIntegrityError('identity participant fingerprint mismatch')
        with self.store.read_snapshot(successor_pin):
            self._descriptor(successor_pin)
            versions, ordinary, identities = delta.decode(self.codec)
            if ordinary or identities:
                raise StoreIntegrityError('catalog participant supplied unexpected independent writes')
            for change in versions:
                try:
                    checked = self.store.read_version(successor_pin, change.namespace, change.key,
                                                       expected_record_schema=change.record_schema)
                except KeyError:
                    if change.delete:
                        continue
                    raise StoreIntegrityError('missing frozen identity publication') from None
                if change.delete or self.codec.encode(checked.value) != self.codec.encode(change.value):
                    raise StoreIntegrityError('identity publication disagrees with frozen bytes')
                if change.namespace == GROUP_NAMESPACE:
                    self.read_identity_group(successor_pin, change.key)

    def accept_delta(self, delta, successor_pin):
        # The catalog has no committed mutable cache to publish. Coordinators
        # validate once, then accept their exact frozen overlay separately.
        self.validate_publication(delta, successor_pin)


class OwnerTreeEditor:
    """Persistent compressed radix edits: at most 32 branch levels per path."""
    def __init__(self, catalog, pin, owner, root):
        self.catalog, self.pin, self.owner = catalog, pin, owner
        self.root = root
        self.changes = {}
        self.cache = {}

    def _read(self, link):
        prefix, count, checksum = link
        if prefix in self.changes:
            value = self.changes[prefix]
            if value is None:
                raise StoreIntegrityError('owner tree reached a locally retired node')
            if node_commit(self.catalog.codec, value) != (count, checksum):
                raise StoreIntegrityError('owner tree overlay commitment mismatch')
            return value
        if prefix not in self.cache:
            self.cache[prefix] = self.catalog._node(self.pin, self.owner, prefix, count, checksum)
        return self.cache[prefix]

    def _write(self, prefix, value):
        self.changes[prefix] = value
        count, checksum = node_commit(self.catalog.codec, value)
        return prefix, count, checksum

    def replace(self, path, incarnation):
        codec = self.catalog.codec
        wanted = path_hash(codec, path)
        def leaf():
            return self._write(wanted, ('owner-leaf/v1', path, incarnation))
        def join(old, new):
            a, b = old[0], new[0]
            length = 0
            while length < min(len(a), len(b)) and a[length] == b[length]:
                length += 1
            if length == min(len(a), len(b)):
                raise StoreIntegrityError('owner tree path hash collision')
            prefix = a[:length]
            children = tuple(sorted(((a[length], *old), (b[length], *new))))
            return self._write(prefix, ('owner-branch/v1', prefix, children))
        def edit(link):
            if link is None:
                if incarnation is None:
                    raise StoreIntegrityError('deleting absent owner occurrence')
                return leaf()
            prefix = link[0]
            node = self._read(link)
            if not wanted.startswith(prefix):
                if incarnation is None:
                    raise StoreIntegrityError('deleting absent owner occurrence')
                return join(link, leaf())
            if node[0] == 'owner-leaf/v1':
                if node[1] != path:
                    raise StoreIntegrityError('owner tree encoded-path collision')
                if incarnation is None:
                    self.changes[prefix] = None
                    return None
                return leaf()
            slot = wanted[len(prefix)]
            children = {c[0]: c[1:] for c in node[2]}
            result = edit(children.get(slot))
            if result is None:
                children.pop(slot, None)
            else:
                children[slot] = result
            if len(children) == 1:
                self.changes[prefix] = None
                return next(iter(children.values()))
            return self._write(prefix, ('owner-branch/v1', prefix,
                               tuple((key, *value) for key, value in sorted(children.items()))))
        self.root = edit(self.root)

    def delta(self):
        out = []
        for prefix, value in self.changes.items():
            if prefix in self.cache and value == self.cache[prefix]:
                continue
            if value is None and prefix not in self.cache:
                # Created and retired within this preparation: no persisted row.
                continue
            out.append(VersionChange(OWNER_TREE_NAMESPACE, (*self.owner, prefix), value, delete=value is None))
        return tuple(out)


def _prepare_catalog_delta(self, pin, owner_versions, identity_changes, *, next_incarnation_id):
    versions = tuple(owner_versions)
    placements = tuple(identity_changes)
    if not versions and not placements:
        return ParticipantDelta.freeze(self.codec, 'identity-catalog')
    with self.store.read_snapshot(pin):
        descriptor = self._descriptor(pin)
        old_allocator = descriptor[2]
        if type(next_incarnation_id) is not int or next_incarnation_id < old_allocator:
            raise ValueError('incarnation allocator cannot move backwards')
        sources = {(v.namespace, self.codec.encode(v.key)): v for v in versions}
        owner_keys = {marker: (v.namespace, v.key) for marker, v in sources.items()}
        edits_by_owner = {}
        edits_by_group = {}
        for change in placements:
            owner = change.owner_namespace, change.owner_key
            marker = owner[0], self.codec.encode(owner[1])
            owner_keys[marker] = owner
            placement_path(*owner, change.occurrence_path)
            try:
                old = self.store.read_identity_occurrence(pin, *owner, change.occurrence_path).incarnation_id
            except KeyError:
                old = None
            new = None if change.delete else change.incarnation_id
            if new is not None and (type(new) is not int or not 0 < new < next_incarnation_id):
                raise ValueError('unallocated identity placement')
            if old == new:
                continue
            edits_by_owner.setdefault(marker, []).append(change)
            placement = (*owner, change.occurrence_path)
            pkey = self.codec.encode(placement)
            if old is not None:
                edits_by_group.setdefault(old, {})[pkey] = None
            if new is not None:
                edits_by_group.setdefault(new, {})[pkey] = placement
        changes = []
        for marker, owner in owner_keys.items():
            source = sources.get(marker)
            generation = pin.captured_head + 1
            try:
                header = self._owner(pin, owner)
            except StoreIntegrityError:
                # A new owner must be absent at the pin, not a corrupt old owner.
                if self.store._visible_record_row(pin.captured_head, owner[0], marker[1]) is not None:
                    raise
                if source is None or source.delete:
                    raise StoreIntegrityError('new identity owner lacks a prepared payload')
                header = ('identity-owner/v1', True, 'lazy', generation, source.record_schema,
                          _framed_sha(b'lazy-payload-v1', self.codec.encode(source.value)),
                          None, 0, _framed_sha(b'identity-owner-empty-v1'))
            root = None if header[6] is None else header[6:]
            editor = OwnerTreeEditor(self, pin, owner, root)
            for change in edits_by_owner.get(marker, ()):
                editor.replace(change.occurrence_path, None if change.delete else change.incarnation_id)
            changes.extend(editor.delta())
            tree = editor.root or (None, 0, _framed_sha(b'identity-owner-empty-v1'))
            if source is not None and source.delete:
                if tree[1] != 0:
                    raise StoreIntegrityError('owner deletion must retire all current placements')
                value = ('identity-owner/v1', False, 'lazy', generation, source.record_schema,
                         header[5], *tree)
            elif source is not None:
                value = ('identity-owner/v1', True, 'lazy', generation, source.record_schema,
                         _framed_sha(b'lazy-payload-v1', self.codec.encode(source.value)), *tree)
            else:
                value = (*header[:6], *tree)
            if value != header:
                changes.append(VersionChange(OWNER_NAMESPACE, owner, value))
        affected = set(edits_by_group) | set(range(old_allocator, next_incarnation_id))
        for inc in sorted(affected):
            if inc < old_allocator:
                group = self.read_identity_group(pin, inc)
                base = {self.codec.encode(o): o for o in group.occurrences}
                previous_links = dict(group.links)
            else:
                base, previous_links = {}, {}
            for pkey, value in edits_by_group.get(inc, {}).items():
                if value is None:
                    base.pop(pkey, None)
                else:
                    base[pkey] = value
            occurrences = tuple(base.values())
            paths = sorted((placement_path(*o) for o in occurrences), key=self.codec.encode)
            links = tuple((target, paths[0]) for target in paths[1:])
            final_links = dict(links)
            for target in previous_links.keys() - final_links.keys():
                changes.append(VersionChange(LINK_NAMESPACE, target, delete=True))
            for ordinal, (target, anchor) in enumerate(links):
                if previous_links.get(target) != anchor:
                    changes.append(VersionChange(LINK_NAMESPACE, target, ('identity-link/v1', inc, anchor),
                        memberships=(Membership('incarnation', inc, ordinal),)))
            value = ('identity-group/v1', 'mutable', len(occurrences),
                     digest(self.codec, b'identity-group-occurrences-v1', occurrences), len(links),
                     digest(self.codec, b'identity-group-links-v1', links), paths[0] if paths else None)
            changes.append(VersionChange(GROUP_NAMESPACE, inc, value))
        if next_incarnation_id != old_allocator:
            changes.append(VersionChange(CATALOG_NAMESPACE, 0,
                (CATALOG_TAG, FEATURES, next_incarnation_id, descriptor[3] + next_incarnation_id - old_allocator,
                 descriptor[4])))
        # Coalesce targets moved between groups to a final action. Group iteration
        # order cannot decide whether an old target deletion overrides its upsert.
        final = {}
        for change in changes:
            marker = change.namespace, self.codec.encode(change.key)
            existing = final.get(marker)
            if change.namespace == LINK_NAMESPACE and existing is not None and not existing.delete and change.delete:
                continue
            final[marker] = change
        return ParticipantDelta.freeze(self.codec, 'identity-catalog', version_changes=tuple(final.values()))


