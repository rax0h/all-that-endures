"""Explicit fully audited native sessions; no fast admission or save claim.

The existing native registry, frozen participants and SQLite publisher remain the
only runtime/transaction authorities. External expected commitment is mandatory.
"""
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from . import persistence_proof_manifest_publish as manifests
from . import persistence_proof_world as world


class _WorldProofAuthority:
    def __init__(self,expected):
        if type(expected) is not bytes or len(expected)!=32:raise StoreIntegrityError('invalid external World commitment')
        self.expected=expected;self.store=None;self.pair=None;self.epoch=None
        self.busy=False;self.uncertain=False;self.pending=None

    def bind(self,store):
        if self.store is not None:raise StoreError('native proof admission is single-use')
        if store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()!=('7',):raise StoreError('audited native admission requires proof format7')
        self.store=store
        self._admission_temp_schema=store.db.execute('PRAGMA temp.schema_version').fetchone()[0]

    def _epoch(self):
        db=self.store.db
        return (db,self.store.codec,db.execute('PRAGMA data_version').fetchone()[0],db.total_changes,
            db.execute('PRAGMA main.schema_version').fetchone()[0],db.execute('PRAGMA temp.schema_version').fetchone()[0])

    def guard(self):
        if self.busy or self.epoch is None:return
        if self.uncertain:raise StoreError('native proof publication requires exact recovery')
        if self._epoch()!=self.epoch:raise StoreConflictError('native proof authority invalidated by untracked SQL; reopen against accepted commitment')

    def _audit(self,pin):
        store=self.store;owned=not store.db.in_transaction;active=store._active_read_transaction
        if owned:store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
        try:
            with store.read_snapshot(pin,_preflight=lambda:manifests._schemas(store)):
                world.OrderedSeekMap(store.db,world.directory.domain(store.store_identity,store.codec.version)).create_schema()
                pairs,facts=manifests._load(store,pin,self.pair)
                proof=world._audit_world(store,pin,*pairs)
                if proof.roots!=self.pair[0].roots or proof.facts!=facts:raise StoreIntegrityError('native World audit disagrees with accepted manifest')
            verified_epoch=self._epoch()
            if owned:store.db.commit()
            return verified_epoch
        except BaseException:
            if owned and store.db.in_transaction:store.db.rollback()
            raise
        finally:store._active_read_transaction=active

    def admit(self,pin):
        if self.pair is not None:raise StoreError('native proof admission cannot be replayed')
        from .persistence_proof_generation import read_generation_manifest
        self.busy=True
        try:
            with self.store.read_snapshot(pin,_preflight=lambda:manifests._schemas(self.store)):
                value=read_generation_manifest(self.store,pin,self.expected)
                self.pair=value,self.expected
                verified_epoch=self._audit(pin)
            self.epoch=verified_epoch
        finally:self.busy=False

    def finish_admission(self):
        # The native opener rolls back its owned restore transaction. TEMP
        # audit workspace DDL is rolled back to the exact pre-admission schema;
        # data/codec/main-schema authority keeps its already verified epoch.
        if self.epoch is not None:self.epoch=(*self.epoch[:-1],self._admission_temp_schema)

    def execute(self,session,callback,*,recovery=False):
        if self.busy:raise StoreError('reentrant native proof operation')
        if not(recovery and self.pending is not None):self.guard()
        self.busy=True
        try:
            result=callback()
            observed=self._epoch()
            verified=self._audit(session.pin) if self.epoch!=observed else observed
            self.pending=None;self.uncertain=False;self.epoch=verified
            return result
        except BaseException:
            self.uncertain=True
            if session._state=='active' and session._pending_save is None:
                # A known rolled-back attempt leaves journals dirty but the old
                # manifest authoritative. Reauthenticate before permitting retry.
                verified=self._audit(session.pin)
                self.pending=None;self.uncertain=False;self.epoch=verified
            raise
        finally:self.busy=False

    def commit(self,session,plan):
        from .persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
        if not self.busy or self.pair[0].generation!=plan.publication.parent_pin.captured_head:raise StoreIntegrityError('native frozen parent differs from accepted manifest')
        args=plan.publication.commit_arguments(plan)
        if (args['commit_token']!=plan.token or plan.target_generation!=plan.publication.target_generation
                or plan.publication.target_generation!=self.pair[0].generation+1):raise StoreIntegrityError('frozen native token/generation disagrees with original manifest parent')
        changes=args['changes'];marker=(EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY)
        controls=[c for c in changes if (c.namespace,c.key)==marker]
        expected=(1,self.pair[0].generation+1,args['commit_token'])
        if len(controls)!=1 or controls[0].delete or controls[0].record_schema!=1 or controls[0].memberships or self.store.codec.encode(controls[0].value)!=self.store.codec.encode(expected):raise StoreIntegrityError('frozen native commit descriptor disagrees with manifest attempt')
        args['changes']=tuple(c for c in changes if (c.namespace,c.key)!=marker)
        args['required_format_version']=7
        self.pending=plan.publication.parent_pin,self.pair,args['commit_token']
        result=manifests.commit_world_manifest(self.store,plan.publication.parent_pin,*self.pair,**args)
        if result.manifest:self.pair=result.manifest
        if result.commit.outcome=='committed':self._audit(result.commit.pin)
        return result.commit

    def resolve(self,session,plan):
        if not self.busy or self.pending is None:raise StoreError('native manifest lacks original recovery context')
        pin,parent,token=self.pending
        if token!=plan.token or pin!=plan.publication.parent_pin:raise StoreIntegrityError('native manifest recovery differs from frozen plan')
        result=manifests.resolve_world_manifest(self.store,pin,*parent,commit_token=token)
        if result.manifest:
            self.pair=result.manifest
            self._audit(result.commit.pin)
        return result.commit


def open_audited_proof_world_session(path,*,rules_id,expected_commitment,paged_household_members=None):
    """Full audit + existing canonical restoration; deliberately explicit/slow."""
    from .persistence_lazy import open_lazy_world_session
    admission=_WorldProofAuthority(expected_commitment)
    return open_lazy_world_session(path,rules_id=rules_id,paged_household_members=paged_household_members,_proof_admission=admission)
