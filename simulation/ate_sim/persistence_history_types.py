"""Bounded checked member-type witnesses, published with their history edits.

The three disjoint classes cover the concrete graph-owner policies. Counts
retain exact Python types: bool and float are not integer IDs. New conversion
can establish witnesses by reading its coherent source; an ordinary open never
constructs one from history. Genuine earlier stores retain explicit compatibility
admission scans until a source-preserving copy upgrade establishes the authority.
"""
from .incremental_store import StoreIntegrityError
from .persistence_lazy_store import VersionChange

NAMESPACE = 'aux.lazy.history.member_types'
TAG = 'history-member-types/v1'
KINDS = ('list', 'map', 'set', 'sequence')


def member_class(value):
    if type(value) is int:
        return 0
    if (type(value) is tuple and len(value) == 2
            and type(value[0]) is str and type(value[1]) is int):
        return 1
    return 2


def member_counts(values):
    counts = [0, 0, 0]
    for value in values:
        counts[member_class(value)] += 1
    return tuple(counts)


def initial_type_change(incarnation, kind, values):
    if kind not in KINDS or type(incarnation) is not int or incarnation < 1:
        raise ValueError('invalid history type witness')
    return VersionChange(NAMESPACE, incarnation, (TAG, kind, member_counts(values)))


class HistoryMemberTypes:
    def __init__(self, store, pin, incarnation, kind, *, new=False, required=None):
        store._require_pin(pin)
        if required is not None and type(required) is not bool:
            raise TypeError('checked history types must be bool or None')
        self.incarnation, self.kind = incarnation, kind
        self.enabled = (store._namespace_state_at(NAMESPACE, pin.captured_head) is not None
                        if required is None else required)
        self.counts = (0, 0, 0)
        self._base = None if new else self.counts
        if self.enabled and not new:
            try:
                value = store.read_version(pin, NAMESPACE, incarnation, expected_record_schema=1).value
            except KeyError as exc:
                raise StoreIntegrityError('mandatory history member type witness is absent') from exc
            if (type(value) is not tuple or len(value) != 3 or value[:2] != (TAG, kind)
                    or type(value[2]) is not tuple or len(value[2]) != 3
                    or any(type(n) is not int or n < 0 for n in value[2])):
                raise StoreIntegrityError('invalid history member type witness')
            self.counts = self._base = value[2]

    def check_length(self, length):
        if self.enabled and sum(self.counts) != length:
            raise StoreIntegrityError('history member type witness disagrees with descriptor count')

    def add(self, value, amount=1):
        if self.enabled:
            counts = list(self.counts)
            counts[member_class(value)] += amount
            if min(counts) < 0:
                raise StoreIntegrityError('history member type counter underflow')
            self.counts = tuple(counts)

    def replace_all(self, values):
        if self.enabled:
            self.counts = member_counts(values)

    def require_policy(self, history, policy):
        if policy not in ('int', 'lineage_pair'):
            raise ValueError('unknown history member policy')
        if self.enabled:
            self.check_length(len(history))
            allowed = 0 if policy == 'int' else 1
            valid = self.counts[allowed] == sum(self.counts)
        else:
            # Explicit genuine-legacy compatibility cost, never hidden migration.
            allowed = 0 if policy == 'int' else 1
            valid = all(member_class(value) == allowed for value in history)
        if not valid:
            raise TypeError('history member violates the incoming owner type')

    def pending_changes(self, length):
        self.check_length(length)
        if self.enabled and self.counts != self._base:
            return (VersionChange(NAMESPACE, self.incarnation, (TAG, self.kind, self.counts)),)
        return ()

    def accept_save(self):
        self._base = self.counts

    def verify_values(self, values):
        """Explicit full scrub/conversion check; never ordinary admission."""
        if self.enabled and member_counts(values) != self.counts:
            raise StoreIntegrityError('history member type witness disagrees with backing values')


def verify_type_witnesses(store, pin):
    """Explicit full destination verification with bounded streamed member state."""
    from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE, HISTORY_CLASSES
    from .persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as SEQUENCE_DESCRIPTOR
    from .persistence_history_retirement import _job, _scopes, NAMESPACE as RETIREMENT
    descriptors, witnesses = set(), set(store.iter_keys(pin, NAMESPACE))
    for namespace in (DESCRIPTOR_NAMESPACE, SEQUENCE_DESCRIPTOR):
        for incarnation in store.iter_keys(pin, namespace):
            if type(incarnation) is not int or incarnation < 1 or incarnation in descriptors:
                raise StoreIntegrityError('invalid or duplicate history type backing')
            descriptors.add(incarnation)
            descriptor = store.read_version(pin, namespace, incarnation, expected_record_schema=1).value
            if type(descriptor) is not tuple or not descriptor:
                raise StoreIntegrityError('invalid history type backing descriptor')
            kind = 'sequence' if namespace == SEQUENCE_DESCRIPTOR else descriptor[0]
            if kind not in KINDS:
                raise StoreIntegrityError('history type witness has unknown backing kind')
            # Partly reclaimed trees are deliberately no longer readable at
            # the current generation. Their checked queue retains the descriptor.
            if store.contains_lazy_key(pin, RETIREMENT, incarnation):
                job = _job(store, pin, incarnation)
                if job[1] != kind:
                    raise StoreIntegrityError('history retirement type disagrees with backing')
                if job[4]:
                    if incarnation in witnesses:
                        types = HistoryMemberTypes(store, pin, incarnation, kind, required=True)
                        position = 3 if kind == 'sequence' else 1
                        if len(descriptor) <= position or type(descriptor[position]) is not int:
                            raise StoreIntegrityError('invalid retiring history descriptor count')
                        types.check_length(descriptor[position])
                    else:
                        # v2 retires this authority immediately before the
                        # descriptor; no live owner may read the partial tree.
                        scopes = _scopes(job)
                        if job[0] != 'history-retirement/v2' or job[2] != len(scopes) - 1:
                            raise StoreIntegrityError('retiring history lost its type witness early')
                        descriptors.remove(incarnation)
                    continue
            history = HISTORY_CLASSES[kind](store, pin, incarnation, checked_types=True)
            history._member_types.verify_values(history)
    if descriptors != witnesses:
        raise StoreIntegrityError('history type witness inventory is incomplete or extra')
    return len(witnesses)
