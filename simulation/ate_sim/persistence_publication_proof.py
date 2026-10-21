"""Immutable evidence for one fully validated, unchanged successor publication."""
from dataclasses import dataclass, replace


def publication_epoch(store):
    store._ensure_open()
    db = store.db
    return (db, store.codec, db.total_changes,
            db.execute('PRAGMA data_version').fetchone()[0],
            db.execute('PRAGMA schema_version').fetchone()[0], store._phase_hook)


def overlay_fingerprint(coordinator):
    return tuple(sorted((marker, coordinator.store.codec.encode((change.owner_namespace,
                            change.owner_key, change.occurrence_path, change.incarnation_id, change.delete)))
                        for marker, change in coordinator.placement_overlay.items()))


@dataclass(frozen=True)
class PublicationProof:
    coordinator: object
    prepared: object
    fingerprint: str
    pin: object
    epoch: tuple
    overlay_revision: int
    overlay: tuple
    standalone: bool

    @classmethod
    def after_validation(cls, coordinator, delta, pin, entry_epoch, standalone):
        epoch = publication_epoch(coordinator.store)
        return cls(coordinator, coordinator._prepared, delta.fingerprint, pin, epoch,
                   coordinator.placement_revision, overlay_fingerprint(coordinator),
                   standalone and entry_epoch == epoch and not coordinator.store.db.in_transaction)

    def finish_owned_read(self, entry_epoch):
        """Only the participant that owned the outer read may call this.

        A proof from an arbitrary borrowed/savepoint transaction stays unusable.
        The participant captures entry before BEGIN and checks again after its
        read-only rollback, so a rolled-back write cannot qualify a certificate.
        """
        store = self.coordinator.store
        if (entry_epoch is not None and not store.db.in_transaction
                and entry_epoch == self.epoch == publication_epoch(store)):
            return replace(self, standalone=True)
        return self

    def matches(self, coordinator, delta, successor_pin):
        store = coordinator.store
        if (not self.standalone or store._closed or coordinator is not self.coordinator
                or coordinator._prepared is not self.prepared or delta is not self.prepared.delta
                or delta.fingerprint != self.fingerprint or successor_pin != self.pin
                or store.db is not self.epoch[0] or store.codec is not self.epoch[1]
                or store.db.in_transaction or coordinator.placement_revision != self.overlay_revision):
            return False
        return self.overlay == overlay_fingerprint(coordinator) and self.epoch == publication_epoch(store)
