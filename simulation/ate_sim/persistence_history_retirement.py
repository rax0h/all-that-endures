"""Indexed, bounded retirement plans; the hybrid transaction alone publishes.

Last-owner deletion queues one compact job. It never walks the backing. Each
subsequent plan retires a bounded key slice, preserves old snapshots and checks
the mandatory dependency roster before touching children. Complete World and
copy-upgrade activation remains separate from these transaction primitives.
"""
from .incremental_store import Membership, StoreConflictError, StoreIntegrityError, StoreFormatError
from .persistence_lazy_store import VersionChange
from .persistence_lazy_families import ParticipantDelta
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as HISTORY_DESCRIPTOR, PAGE_NAMESPACE, ENTRY_NAMESPACE
from .persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as SEQUENCE_DESCRIPTOR, NAMESPACES as SEQUENCE_NAMESPACES
from .persistence_history_dependencies import (NAMESPACE as DEPENDENCIES,
    active_backing_dependencies, _checked_value as checked_dependencies)
from .persistence_history_types import NAMESPACE as MEMBER_TYPES

NAMESPACE = 'aux.lazy.history.retirement'
TAG = 'history-retirement/v2'
SCOPE_INDEX = 'lazy_record_current_key'
LEGACY_SCOPES = {'list': (PAGE_NAMESPACE, HISTORY_DESCRIPTOR),
          'map': (ENTRY_NAMESPACE, HISTORY_DESCRIPTOR),
          'set': (ENTRY_NAMESPACE, HISTORY_DESCRIPTOR),
          'sequence': tuple(ns for ns in SEQUENCE_NAMESPACES if ns != SEQUENCE_DESCRIPTOR) + (SEQUENCE_DESCRIPTOR,)}
SCOPES = {kind: scopes[:-1] + (MEMBER_TYPES, scopes[-1]) for kind, scopes in LEGACY_SCOPES.items()}


def _scopes(job):
    return LEGACY_SCOPES[job[1]] if job[0] == 'history-retirement/v1' else SCOPES[job[1]]


def initial_retirement_change(kind, incarnation, *, generation):
    if (kind not in SCOPES or type(incarnation) is not int or incarnation < 1
            or type(generation) is not int or generation < 1):
        raise ValueError('invalid history retirement job')
    return VersionChange(NAMESPACE, incarnation, (TAG, kind, 0, generation, False),
                         memberships=(Membership('pending', True, generation),))


def _job(store, pin, incarnation):
    value = store.read_version(pin, NAMESPACE, incarnation, expected_record_schema=1).value
    if (type(value) is not tuple or len(value) != 5 or value[0] not in (TAG, 'history-retirement/v1')
            or value[1] not in SCOPES or type(value[2]) is not int
            or not 0 <= value[2] < len(_scopes(value))
            or type(value[3]) is not int or not 1 <= value[3] <= pin.captured_head
            or type(value[4]) is not bool):
        raise StoreIntegrityError('invalid history retirement job')
    return value


def pending_retirement(store, pin, incarnation):
    try:
        _job(store, pin, incarnation)
    except KeyError:
        return False
    return True


def _scope_keys(store, pin, namespace, incarnation, *, limit):
    if namespace == MEMBER_TYPES:
        # Legacy backings have no type authority. Checked absence remains valid;
        # a dangling row/order still fails the ordinary version read.
        try:
            store.read_version(pin, namespace, incarnation, expected_record_schema=1)
        except KeyError:
            return ()
        return (incarnation,)
    if namespace in (HISTORY_DESCRIPTOR, SEQUENCE_DESCRIPTOR):
        try:
            store.read_version(pin, namespace, incarnation, expected_record_schema=1)
        except KeyError as exc:
            raise StoreIntegrityError('history retirement backing descriptor is absent') from exc
        return (incarnation,)
    # TypedCodec's canonical tuple framing gives an exact first-element range.
    # The partial index excludes expired versions before LIMIT, so churn cannot
    # turn a bounded returned page into a scan of unrelated or historical rows.
    prefix = store.codec.encode((incarnation,))[:-2] + b','
    rows = store.db.execute(
        f'SELECT typed_key FROM lazy_record_versions INDEXED BY {SCOPE_INDEX} '
        'WHERE namespace=? AND valid_to IS NULL AND typed_key>=? AND typed_key<? '
        'ORDER BY typed_key LIMIT ?', (namespace, prefix, prefix + b'\xff', limit)).fetchall()
    store._metadata_rows += len(rows)
    keys = []
    for (encoded,) in rows:
        key = store.codec.decode(encoded)
        if type(key) is not tuple or len(key) != 2 or type(key[0]) is not int or key[0] != incarnation:
            raise StoreIntegrityError('history scope index selected a foreign backing')
        row = store._visible_record_row(pin.captured_head, namespace, encoded)
        if row is None:
            raise StoreIntegrityError('history scope index has no checked backing row')
        _value, schema, *_ = store._check_record_row(namespace, encoded, row, decode=False)
        if schema != 1 or store._visible_order(namespace, encoded, pin.captured_head) is None:
            raise StoreIntegrityError('history retirement backing has invalid schema/order')
        keys.append(key)
    return tuple(keys)


def prepare_retirement_delta(store, pin, *, row_budget=256, protected_incarnations=()):
    if type(row_budget) is not int or not 0 <= row_budget <= 256:
        raise ValueError('history retirement row budget must be in0..256')
    protected = set(protected_incarnations)
    if any(type(inc) is not int or inc < 1 for inc in protected):
        raise ValueError('invalid protected history incarnation')
    if row_budget < 3:
        return ParticipantDelta.freeze(store.codec, 'history-retirement')
    changes = []
    with store.read_snapshot(pin):
        if pin.captured_head != store.generation:
            raise StoreConflictError('history retirement requires the current writer pin')
        if not store.db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',
                                ('index', SCOPE_INDEX)).fetchone():
            raise StoreFormatError('history retirement requires an explicit indexed copy upgrade')
        floor = store._validated_retention_floor(pin.captured_head)
        jobs = store.query_memberships(pin, NAMESPACE, 'pending', True, limit=row_budget)
        for incarnation, _checked_at in jobs:
            remaining = row_budget - len(changes)
            if remaining < 3:
                break
            job = _job(store, pin, incarnation)
            if store.read_identity_group(pin, incarnation).occurrences:
                if job[4]:
                    raise StoreIntegrityError('revived identity has a partly retired backing')
                # Revival cancels only the queue; the backing and dependency
                # authority remain exactly the same stable incarnation.
                changes.append(VersionChange(NAMESPACE, incarnation, delete=True))
                continue
            dependencies = checked_dependencies(store, pin, incarnation)
            if dependencies[1] != job[1]:
                raise StoreIntegrityError('history retirement kind disagrees with dependency authority')
            try:
                descriptor = store.read_version(pin, _scopes(job)[-1], incarnation,
                                                expected_record_schema=1).value
            except KeyError as exc:
                raise StoreIntegrityError('history retirement backing descriptor is absent') from exc
            if (type(descriptor) is not tuple or not descriptor
                    or (job[1] == 'sequence' and descriptor[0] not in ('ordered-sequence/v1', 'ordered-sequence/v2'))
                    or (job[1] != 'sequence' and descriptor[0] != job[1])):
                raise StoreIntegrityError('history retirement kind disagrees with backing descriptor')
            if incarnation in protected or job[3] > floor or active_backing_dependencies(store, pin, incarnation):
                # Rotating checked-at order prevents protected jobs starving
                # eligible jobs behind them. This is one bounded metadata edit.
                changes.append(VersionChange(NAMESPACE, incarnation, job,
                    memberships=(Membership('pending', True, pin.captured_head + 1),)))
                continue
            scopes, position = _scopes(job), job[2]
            if position == len(scopes) - 1:
                keys = _scope_keys(store, pin, scopes[position], incarnation, limit=1)
                changes.extend(VersionChange(scopes[position], key, delete=True) for key in keys)
                changes.append(VersionChange(DEPENDENCIES, incarnation, delete=True))
                changes.append(VersionChange(NAMESPACE, incarnation, delete=True))
            else:
                keys = _scope_keys(store, pin, scopes[position], incarnation, limit=remaining - 1)
                changes.extend(VersionChange(scopes[position], key, delete=True) for key in keys)
                position += len(keys) < remaining - 1
                changes.append(VersionChange(NAMESPACE, incarnation, (job[0], job[1], position, job[3], job[4] or bool(keys)),
                    memberships=(Membership('pending', True, pin.captured_head + 1),)))
    return ParticipantDelta.freeze(store.codec, 'history-retirement', version_changes=changes)


def validate_publication(store, delta, pin):
    if delta.participant != 'history-retirement':
        raise ValueError('different history retirement participant')
    versions, ordinary, identities = delta.decode(store.codec)
    if ordinary or identities or ParticipantDelta.freeze(store.codec, delta.participant,
            version_changes=versions).fingerprint != delta.fingerprint:
        raise StoreIntegrityError('history retirement participant fingerprint mismatch')
    with store.read_snapshot(pin):
        for change in versions:
            try:
                current = store.read_version(pin, change.namespace, change.key, expected_record_schema=change.record_schema)
            except KeyError:
                if not change.delete:
                    raise StoreIntegrityError('history retirement publication is absent') from None
            else:
                if change.delete or current.value != change.value:
                    raise StoreIntegrityError('history retirement publication disagrees with frozen plan')


def prepare_world_retirement_delta(store, pin, coordinator, dependencies):
    """Queue affected last-owner removals plus at most128 background edits.

    Foreground jobs scale with actual placement changes, never owner inventory.
    Both projections use the same checked coordinator and publisher lease.
    The other128 ordinary maintenance rows are reserved for physical expiry GC.
    """
    if (coordinator.store is not store or coordinator.pin != pin or coordinator._prepared is not None
            or dependencies.store is not store or dependencies.pin != pin or dependencies.closed):
        raise StoreIntegrityError('World retirement has a different publisher parent')
    jobs = []
    with store.read_snapshot(pin):
        for inc in sorted({i for i in coordinator._original.values() if i is not None}):
            group = coordinator.discover_group(inc)
            current = coordinator._current_placements(group)
            try:
                last_removed = bool(group.occurrences) and not current
            finally:
                if hasattr(current, 'close'):
                    current.close()
            if not last_removed:
                continue
            kinds = []
            for namespace in (HISTORY_DESCRIPTOR, SEQUENCE_DESCRIPTOR):
                try:
                    value = store.read_version(pin, namespace, inc, expected_record_schema=1).value
                except KeyError:
                    continue
                kind = 'sequence' if namespace == SEQUENCE_DESCRIPTOR else value[0] if type(value) is tuple and value else None
                if (kind not in SCOPES or type(value) is not tuple or not value
                        or namespace == SEQUENCE_DESCRIPTOR and value[0] not in ('ordered-sequence/v1', 'ordered-sequence/v2')):
                    raise StoreIntegrityError('retiring World history has an invalid descriptor')
                kinds.append(kind)
            authority = checked_dependencies(store, pin, inc, required=bool(kinds))
            if not kinds and authority is None:
                continue  # This incarnation is a record/container, not a backing.
            if len(kinds) != 1 or authority[1] != kinds[0]:
                raise StoreIntegrityError('retiring World history has conflicting backing authority')
            # Requeue if a previously revived job was awaiting cancellation.
            # The checked old group was placed, so background cannot delete its
            # children. Foreground replacement wins over that queue cancellation.
            jobs.append(initial_retirement_change(kinds[0], inc, generation=pin.captured_head + 1))
        background = prepare_retirement_delta(store, pin,
            row_budget=128,
            protected_incarnations=(*dependencies.protected_incarnations(), *coordinator.dirty_incarnations))
    combined = {(c.namespace, store.codec.encode(c.key)): c for c in background.decode(store.codec)[0]}
    combined.update(((c.namespace, store.codec.encode(c.key)), c) for c in jobs)
    return ParticipantDelta.freeze(store.codec, 'history-retirement', version_changes=tuple(combined.values()))
