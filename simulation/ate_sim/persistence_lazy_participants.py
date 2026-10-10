"""Immutable family deltas inside the existing central hybrid transaction.

The frozen bytes are publication evidence, not another persistence authority.
Domain-specific index/event validators and runtime journal acceptance remain authoritative.
No participant commits, discovers owners, or walks a live registry.
"""
from collections import defaultdict
from dataclasses import dataclass, fields, replace

from .incremental_store import NewSegment, StoreIntegrityError, StoreConflictError, _framed_sha, _record_checksum
from .persistence_lazy_families import FAMILIES, ParticipantDelta


# Explicit order preserves the existing hybrid transaction's source order.
_PREFIXES = ('', 'aspiration_', 'resource_', 'owner_index_', 'material_lot_',
    'material_item_', 'material_lot_index_', 'material_active_index_', 'wallet_',
    'treasury_', 'soul_', 'advancement_', 'institution_magic_record_',
    'institution_notice_', 'institution_application_', 'transmission_', 'motive_',
    'social_edge_', 'social_adjacency_', 'social_partnership_', 'skill_',
    'lineage_node_', 'lineage_child_', 'genealogy_parent_', 'genealogy_child_',
    'community_membership_')
VERSION_FIELDS = tuple(field for p in _PREFIXES for field in
    ((p + 'version_changes', 'lineage_child_edge_version_changes') if p == 'lineage_child_'
     else (p + 'version_changes',))) + ('household_member_version_changes',
    'nested_history_version_changes', 'scalar_index_version_changes')
IDENTITY_FIELDS = tuple(p + 'identity_changes' for p in _PREFIXES) + ('nested_history_identity_changes',)


def _delta(codec, namespace, versions, records, identities):
    fingerprint = _framed_sha(b'save-participant-v1', codec.encode(namespace),
                             codec.encode((versions, records, identities)))
    return ParticipantDelta(namespace, versions, records, identities, fingerprint)


class FamilySaveParticipant:
    """One concrete namespace's immutable writes and exact acknowledgement."""
    def __init__(self, store, pin, target_generation, delta):
        self.store, self.parent_pin = store, pin
        self.target_generation, self.namespace = target_generation, delta.participant
        self.adapter = FAMILIES.get(self.namespace)  # Auxiliary namespaces have their own checked schemas.
        self.delta = delta
        self._validated_pin = None
        self._row_proved_pin = None
        self._event_controls = ()
        self.accepted = False

    def prepare_delta(self, context):
        if context is not None:
            raise StoreIntegrityError('family participant was already prepared')
        return self.delta

    def _check(self, delta, pin):
        if (delta is not self.delta or pin.store_identity != self.parent_pin.store_identity
                or pin.token != self.parent_pin.token or pin.captured_head != self.target_generation):
            raise StoreIntegrityError('family participant acknowledgement differs from frozen plan')

    def validate_publication(self, delta, successor_pin):
        self._check(delta, successor_pin)
        self._validated_pin = self._row_proved_pin = None
        self._event_controls = ()
        codec = self.store.codec
        versions, ordinary, identities = delta.decode(codec)
        from .persistence_events import EVENT_STORAGE, DESCRIPTOR_KEY
        from .persistence_session import TAIL_DESCRIPTOR_KEY, COMMIT_DESCRIPTOR_KEY
        event_controls = []
        with self.store.read_snapshot(successor_pin):
            # Ordinary rows carry only current authority; never read them for old pins.
            if self.store.checked_head().generation != self.target_generation:
                raise StoreConflictError('family publication successor was replaced')
            for change in versions:
                key = codec.encode(change.key)
                row = self.store._visible_record_row(self.target_generation, change.namespace, key)
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError('deleted family version remains visible')
                    continue
                if row is None:
                    raise StoreIntegrityError('saved family version is missing')
                _, schema, _, _, memberships = self.store._check_record_row(change.namespace, key, row, decode=False)
                expected = tuple((m.index_name, m.value, m.ordinal) for m in change.memberships)
                if (self.adapter is not None and change.record_schema != self.adapter.record_schema
                        or schema != change.record_schema or row[2] != codec.encode(change.value) or memberships != expected):
                    message = ('saved nested authority evidence mismatch' if change.namespace.startswith('aux.lazy.nested.')
                               else 'family version publication differs from frozen plan')
                    raise StoreIntegrityError(message)
            for change in ordinary:
                if (change.namespace == EVENT_STORAGE and change.key in
                        (DESCRIPTOR_KEY, TAIL_DESCRIPTOR_KEY, COMMIT_DESCRIPTOR_KEY)):
                    # The existing cold protocol checks all three descriptors
                    # together. Acceptance stays blocked until it proves ours.
                    event_controls.append(change)
                    continue
                key = codec.encode(change.key)
                row = self.store.db.execute('SELECT payload,payload_checksum,codec_version,record_schema,'
                    'last_changed_generation FROM records WHERE namespace=? AND typed_key=?',
                    (change.namespace, key)).fetchone()
                if change.delete:
                    if row is not None:
                        raise StoreIntegrityError('deleted ordinary family record remains visible')
                    continue
                if row is None:
                    raise StoreIntegrityError('saved ordinary family record is missing')
                payload, checksum, codec_version, schema, generation = row
                self.store._payload_check_reads += 1
                self.store._payload_check_bytes += len(payload)
                if (codec_version != codec.version or schema != change.record_schema
                        or payload != codec.encode(change.value)
                        or checksum != _record_checksum(change.namespace, key, schema, codec_version, generation, payload)):
                    raise StoreIntegrityError(f'ordinary family publication differs from frozen plan: {change.namespace}')
                for member in change.memberships:
                    row = self.store.db.execute('SELECT generation FROM query_membership '
                        'WHERE namespace=? AND index_name=? AND index_value=? AND record_key=? AND ordinal=?',
                        (change.namespace, member.index_name, codec.encode(member.value), key, member.ordinal)).fetchone()
                    self.store._metadata_rows += int(row is not None)
                    if row is None or row[0] != self.target_generation:
                        raise StoreIntegrityError('ordinary family query publication differs from frozen plan')
            for change in identities:
                row = self.store._visible_identity_occurrence(self.target_generation, change.owner_namespace,
                    codec.encode(change.owner_key), codec.encode(change.occurrence_path))
                if (row is not None) if change.delete else (row is None or row[0] != change.incarnation_id):
                    raise StoreIntegrityError('family identity publication differs from frozen plan')
        self._row_proved_pin = successor_pin
        self._event_controls = tuple(event_controls)
        if not event_controls:
            self._validated_pin = successor_pin

    def confirm_cold_publication(self, delta, successor_pin, cold_plan, head):
        """Join the existing checked cold-protocol proof, without rereading it."""
        self._check(delta, successor_pin)
        if (self._row_proved_pin != successor_pin or head.generation != self.target_generation
                or head.parent_generation != self.parent_pin.captured_head):
            raise StoreIntegrityError('family participant lacks cold successor proof')
        if not self._event_controls:
            self._validated_pin = successor_pin
            return
        from .persistence_events import DESCRIPTOR_KEY, _descriptor_value
        from .persistence_session import TAIL_DESCRIPTOR_KEY, COMMIT_DESCRIPTOR_KEY
        tail = cold_plan.after_tail
        expected = {DESCRIPTOR_KEY: _descriptor_value(cold_plan.after_prefix),
            TAIL_DESCRIPTOR_KEY: (1, tail.disk_events, tail.sealed_events, tail.total_events, tail.last_event_year),
            COMMIT_DESCRIPTOR_KEY: (1, self.target_generation, cold_plan.token)}
        for change in self._event_controls:
            if (change.delete or change.record_schema != 1 or change.memberships
                    or self.store.codec.encode(change.value) != self.store.codec.encode(expected[change.key])):
                raise StoreIntegrityError('frozen event control differs from checked cold successor')
        self._validated_pin = successor_pin

    def accept_delta(self, delta, successor_pin):
        self._check(delta, successor_pin)
        if self._validated_pin != successor_pin:
            raise StoreIntegrityError('family participant lacks checked publication acknowledgement')
        self.accepted = True  # Idempotent; the central owner clears runtime journals.


class CoordinatorSaveParticipant:
    """Join catalog validation and live acceptance to the existing publisher."""
    namespace = 'identity-coordinator'

    def __init__(self, coordinator, delta, parent_pin, target_generation):
        self.coordinator, self.store = coordinator, coordinator.store
        self.delta, self.parent_pin = delta, parent_pin
        self.target_generation = target_generation
        self._validated_pin = self._row_proved_pin = None
        self.accepted = False

    def prepare_delta(self, context):
        if context is not None:
            raise StoreIntegrityError('coordinator participant was already prepared')
        return self.delta

    def _check(self, delta, pin):
        if (delta is not self.delta or pin.store_identity != self.parent_pin.store_identity
                or pin.token != self.parent_pin.token or pin.captured_head != self.target_generation):
            raise StoreIntegrityError('coordinator acknowledgement differs from frozen plan')

    def validate_publication(self, delta, successor_pin):
        self._check(delta, successor_pin)
        self._validated_pin = self._row_proved_pin = None
        with self.store.read_snapshot(successor_pin):
            if self.store.checked_head().generation != self.target_generation:
                raise StoreConflictError('coordinator publication successor was replaced')
            if self.accepted:
                # Partial in-memory publication can be resumed. The exact
                # coordinator acknowledgement still checks its registered lease.
                self.coordinator.accept_delta(delta, successor_pin)
            else:
                self.coordinator.validate_publication(delta, successor_pin)
        self._row_proved_pin = successor_pin

    def confirm_cold_publication(self, delta, successor_pin, cold_plan, head):
        self._check(delta, successor_pin)
        if (self._row_proved_pin != successor_pin or head.generation != self.target_generation
                or head.parent_generation != self.parent_pin.captured_head):
            raise StoreIntegrityError('coordinator lacks central successor proof')
        self._validated_pin = successor_pin

    def accept_delta(self, delta, successor_pin):
        self._check(delta, successor_pin)
        if self._validated_pin != successor_pin:
            raise StoreIntegrityError('coordinator lacks checked publication acknowledgement')
        self.coordinator.accept_delta(delta, successor_pin)
        self.accepted = True

    def abort_delta(self, commit_token):
        self.coordinator.abort_delta(self.delta, commit_token)


@dataclass(frozen=True)
class FrozenHybridPublication:
    sources: tuple
    scalar_sources: tuple
    ordinary_delta: ParticipantDelta
    participants: tuple
    metadata_bytes: bytes
    segment_bytes: tuple
    layout_bytes: bytes
    cold_layout_bytes: bytes
    next_incarnation: int
    required_format_version: int
    parent_pin: object
    target_generation: int
    commit_token_bytes: bytes
    coordinator_participant: object = None

    @property
    def frozen_bytes(self):
        # Source and namespace deltas share the same immutable byte objects.
        return sum(len(payload) for _, delta in self.sources for payload in
            (*delta.version_bytes, *delta.ordinary_bytes, *delta.identity_bytes)) + sum(
            len(payload) for _, delta in self.scalar_sources for payload in
            (*delta.version_bytes, *delta.identity_bytes)) + sum(map(len, self.ordinary_delta.ordinary_bytes)) + sum(
            map(len, self.segment_bytes)) + len(self.metadata_bytes) + len(self.layout_bytes) + len(self.cold_layout_bytes) + len(
            self.commit_token_bytes) + (sum(len(b) for b in (*self.coordinator_participant.delta.version_bytes,
            *self.coordinator_participant.delta.identity_bytes)) if self.coordinator_participant is not None else 0)

    def abort_uncommitted(self):
        """Release a checked failed catalog freeze, preserving all dirty state."""
        if self.coordinator_participant is not None:
            codec = self.coordinator_participant.store.codec
            self.coordinator_participant.abort_delta(codec.decode(self.commit_token_bytes))
        else:
            from .persistence_lazy_publication_guard import checked_uncommitted_publication
            store = self.participants[0].store
            with checked_uncommitted_publication(store, self.parent_pin, store.codec.decode(self.commit_token_bytes)):
                pass

    def replay_plan(self, plan):
        codec = self.participants[0].store.codec
        replacements = {'token': codec.decode(self.commit_token_bytes),
                        'target_generation': self.target_generation}
        for field, delta in self.sources:
            versions, _, identities = delta.decode(codec)
            replacements[field] = identities if field in IDENTITY_FIELDS else versions
        scalars = []
        for original, delta in self.scalar_sources:
            versions, _, identities = delta.decode(codec)
            scalars.append(replace(original, version_changes=versions, identity_changes=identities))
        replacements['scalar_record_plans'] = tuple(scalars)
        replacements['layout_value'] = codec.decode(self.layout_bytes)
        replacements['cold_plan'] = replace(plan.cold_plan,
            token=codec.decode(self.commit_token_bytes),
            changes=self.ordinary_delta.decode(codec)[1],
            new_segments=tuple(NewSegment(*codec.decode(b)) for b in self.segment_bytes),
            metadata=codec.decode(self.metadata_bytes), layout_value=codec.decode(self.cold_layout_bytes))
        replacements['publication'] = self
        return replace(plan, **replacements)

    def commit_arguments(self, plan):
        # Every call returns private decoded values. No runtime aliases enter commit.
        replay = self.replay_plan(plan)
        versions, identities = [], []
        for field in VERSION_FIELDS:
            versions.extend(getattr(replay, field))
            if field == 'motive_version_changes':
                versions.extend(change for unit in replay.scalar_record_plans for change in unit.version_changes)
        for field in IDENTITY_FIELDS:
            identities.extend(getattr(replay, field))
            if field == 'motive_identity_changes':
                identities.extend(change for unit in replay.scalar_record_plans for change in unit.identity_changes)
        if self.coordinator_participant is not None:
            versions.extend(self.coordinator_participant.delta.decode(self.coordinator_participant.store.codec)[0])
        return dict(commit_token=replay.token, version_changes=tuple(versions), identity_changes=tuple(identities),
            next_incarnation_id=self.next_incarnation, required_format_version=self.required_format_version,
            changes=replay.cold_plan.changes, new_segments=replay.cold_plan.new_segments,
            metadata=replay.cold_plan.metadata)


def freeze_hybrid_publication(store, pin, plan, *, next_incarnation, required_format_version,
                              identity_coordinator=None):
    declared = {f.name for f in fields(plan) if f.name.endswith(('_version_changes', '_identity_changes'))
                or f.name in ('version_changes', 'identity_changes')}
    if declared != set(VERSION_FIELDS + IDENTITY_FIELDS):
        raise StoreIntegrityError('hybrid save source field coverage mismatch')
    if plan.target_generation != pin.captured_head + 1 or plan.cold_plan.token != plan.token:
        raise StoreIntegrityError('hybrid save header differs from prepared parent')
    codec = store.codec
    sources = tuple((field, ParticipantDelta.freeze(codec, field,
        **({'identity_changes': getattr(plan, field)} if field in IDENTITY_FIELDS
           else {'version_changes': getattr(plan, field)}))) for field in VERSION_FIELDS + IDENTITY_FIELDS)
    scalars = tuple((replace(unit, version_changes=(), identity_changes=()), ParticipantDelta.freeze(codec, unit.namespace,
        version_changes=unit.version_changes, identity_changes=unit.identity_changes)) for unit in plan.scalar_record_plans)
    ordinary = ParticipantDelta.freeze(codec, 'eager', ordinary_changes=plan.cold_plan.changes)
    # Complete the byte capture before freezing any live participant. Codec
    # failures must leave the owner free to repair its unsaved values.
    metadata_bytes = codec.encode(plan.cold_plan.metadata)
    segment_bytes = tuple(codec.encode((s.namespace, s.ordinal, s.value, s.element_count,
                                       s.first_id, s.last_id)) for s in plan.cold_plan.new_segments)
    layout_bytes, cold_layout_bytes = codec.encode(plan.layout_value), codec.encode(plan.cold_plan.layout_value)
    commit_token_bytes = codec.encode(plan.token)
    coordinator_participant = None
    if identity_coordinator is not None:
        coord = identity_coordinator
        if (coord.store is not store or coord.pin != pin or coord._prepared is not None
                or coord.registry.next_incarnation != next_incarnation):
            raise StoreIntegrityError('hybrid coordinator parent or allocator differs from frozen plan')
        deltas = tuple(d for _, d in sources) + tuple(d for _, d in scalars)
        identity_bytes = tuple(b for d in deltas for b in d.identity_bytes)
        expected = ParticipantDelta.freeze(codec, 'identity-coordinator',
            identity_changes=tuple(coord.placement_overlay.values())).identity_bytes
        if sorted(identity_bytes) != sorted(expected):
            raise StoreIntegrityError('hybrid identity sources differ from coordinator overlay')
        owner_versions = tuple(change for d in deltas for change in d.decode(codec)[0]
                               if change.namespace in FAMILIES)
        owner_records = tuple(change for change in ordinary.decode(codec)[1] if change.namespace in FAMILIES)
        supplied_owners = {(change.namespace, codec.encode(change.key))
                           for change in (*owner_versions, *owner_records)}
        dirty_owners = {(namespace, codec.encode(key)) for namespace, key in coord.dirty_owners}
        if not dirty_owners <= supplied_owners:
            raise StoreIntegrityError('hybrid save omits a touched identity owner payload')
        if any(change.namespace == 'world_identity_links' for change in ordinary.decode(codec)[1]):
            raise StoreIntegrityError('checked catalog cannot publish legacy identity links')
        # Catalog metadata augments the central version list. Placement writes
        # already belong to the family sources and are never appended twice.
        delta = coord.prepare_delta(owner_versions, ordinary_changes=owner_records)
        coordinator_participant = CoordinatorSaveParticipant(coord, delta, pin, plan.target_generation)
    grouped = defaultdict(lambda: [[], [], []])
    for delta in tuple(d for _, d in sources) + tuple(d for _, d in scalars) + (ordinary,):
        for category, payloads in enumerate((delta.version_bytes, delta.ordinary_bytes, delta.identity_bytes)):
            for payload in payloads:
                namespace = codec.decode(payload)[0]
                grouped[namespace][category].append(payload)
    participants = tuple(FamilySaveParticipant(store, pin, plan.target_generation,
        _delta(codec, namespace, *(tuple(values) for values in groups))) for namespace, groups in sorted(grouped.items()))
    if coordinator_participant is not None:
        participants += (coordinator_participant,)
    if not participants:
        raise StoreIntegrityError('nonempty hybrid plan has no family participants')
    return FrozenHybridPublication(sources, scalars, ordinary, participants,
        metadata_bytes, segment_bytes, layout_bytes, cold_layout_bytes,
        next_incarnation, required_format_version, pin, plan.target_generation,
        commit_token_bytes, coordinator_participant)
