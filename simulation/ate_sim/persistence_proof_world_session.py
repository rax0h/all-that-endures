"""Explicit audited admission with bounded proof-reusing native saves.

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
        self.busy=False;self.uncertain=False;self.pending=None;self._postcommit_verified_epoch=None
        self.read_pin=None

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
        guard=getattr(self,'_write_guard',None)
        if guard is None:return self._audit_inner(pin)
        with guard.publisher():return self._audit_inner(pin)

    def _audit_inner(self,pin):
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
            self.read_pin=pin
        finally:self.busy=False

    def finish_admission(self):
        # The native opener rolls back its owned restore transaction. TEMP
        # audit workspace DDL is rolled back to the exact pre-admission schema;
        # data/codec/main-schema authority keeps its already verified epoch.
        if self.epoch is not None:self.epoch=(*self.epoch[:-1],self._admission_temp_schema)

    def _settle(self,pin,entry):
        from .persistence_sqlite_guard import require_persistent_sources
        store=self.store
        if store.db.in_transaction:raise StoreError('native proof acknowledgement left an open transaction')
        store.db.execute('BEGIN IMMEDIATE');active=store._active_read_transaction;store._active_read_transaction=True
        try:
            self._write_guard.check();require_persistent_sources(store.db)
            with store.read_snapshot(pin,_preflight=lambda:manifests._schemas(store)):
                manifests._load(store,pin,self.pair)
                verified=self._epoch()
                if verified[:3]!=entry[:3] or verified[4]!=entry[4]:raise StoreConflictError('external source or schema changed during native proof save')
            store.db.commit();return verified
        except BaseException:
            if store.db.in_transaction:store.db.rollback()
            raise
        finally:store._active_read_transaction=active

    def execute(self,session,callback,*,recovery=False):
        from .persistence_proof_native_guard import NativeWriteGuard
        if session._state=='closed':raise StoreError('native proof session is closed')
        if self.busy:raise StoreError('reentrant native proof operation')
        try:
            with NativeWriteGuard(self.store.db) as guard:
                self._write_guard=guard
                if not(recovery and self.pending is not None):self.guard()
                guard.check();entry=self.epoch;self.busy=True;self._can_settle=not recovery;self._postcommit_verified_epoch=None
                try:
                    result=callback();guard.check();observed=self._epoch()
                    if self._can_settle:
                        verified=observed if observed==entry else self._settle(session.pin,entry)
                    else:
                        verified=self._postcommit_verified_epoch
                        if verified is None or verified!=observed:
                            verified=self._audit(session.pin) if self.epoch!=observed else observed
                        else:
                            # A matching SQLite epoch does not describe an open
                            # transaction or in-place mutation of codec methods.
                            if self.store.db.in_transaction:raise StoreError('native proof acknowledgement left an open transaction')
                            world._require_closed_codec(self.store)
                    self.pending=None;self.uncertain=False;self.epoch=verified
                    return result
                except BaseException as exc:
                    self.uncertain=True
                    if session._state=='active' and session._pending_save is None and not self.store.db.in_transaction:
                        verified=self._audit(session.pin)
                        self.pending=None;self.uncertain=False;self.epoch=verified
                    if guard.denied:raise StoreIntegrityError(guard.denied) from exc
                    raise
        finally:self._postcommit_verified_epoch=None;self._write_guard=None;self.busy=False

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
        with self._write_guard.publisher():
            result=manifests.commit_world_manifest(self.store,plan.publication.parent_pin,*self.pair,**args)
        if result.manifest:
            self.pair=result.manifest
            self.read_pin=result.commit.pin
        self._can_settle=not result.reaudited
        if result.commit.outcome=='committed' and result.reaudited:
            # Reuse only this committed attempt's fully verified postcommit epoch.
            # execute() falls back to the original audit when the epoch changes.
            self._postcommit_verified_epoch=self._audit(result.commit.pin)
        return result.commit

    def resolve(self,session,plan):
        if not self.busy or self.pending is None:raise StoreError('native manifest lacks original recovery context')
        pin,parent,token=self.pending
        if token!=plan.token or pin!=plan.publication.parent_pin:raise StoreIntegrityError('native manifest recovery differs from frozen plan')
        self._can_settle=False
        with self._write_guard.publisher():
            result=manifests.resolve_world_manifest(self.store,pin,*parent,commit_token=token)
        if result.manifest:
            self.pair=result.manifest
            self.read_pin=result.commit.pin
            self._audit(result.commit.pin)
        return result.commit


def _event_occurrences_by_depth(occurrences):
    if type(occurrences) is tuple:
        yield from sorted(occurrences,key=lambda item:len(item[0]))
        return
    # The catalog transfers ownership of a spill above its residency limit.
    # Stream each depth instead of rebuilding that whole roster in Python.
    depth=max((len(path) for path,_number in occurrences),default=0)
    for level in range(depth+1):
        for path,number in occurrences:
            if len(path)==level:
                yield path,number


def _restore_current_event_aliases(session):
    """Stitch resident inline copies using the existing checked catalog.

    Ordinary codecs encode values independently at each path. The catalog is
    their identity authority, including two paths inside one mutable event.
    Only the current mutable tail is visited; sealed event bodies stay cold.
    """
    from .persistence_identity import iter_mutable_event_owners
    from .persistence_lazy_identity import IncarnationId,Occurrence
    registry,bindings=session._registry,session._family_bindings
    coordinator=session._identity_coordinator
    for owner,_event,_absolute in iter_mutable_event_owners(session.world.events):
        accepted=coordinator.catalog.read_owner_identity(session.pin,owner)
        try:
            for path,number in _event_occurrences_by_depth(accepted.occurrences):
                incarnation=IncarnationId(session.store.store_identity,number)
                value=bindings.load_owner(owner)
                current=bindings.resolve_path(value,path)
                canonical=registry.object_for_incarnation(incarnation)
                if canonical is None:
                    registry.bind(current,incarnation=incarnation)
                    canonical=current
                elif current is not canonical:
                    if bindings.encode_placement(owner,path,current)!=bindings.encode_placement(owner,path,canonical):
                        raise StoreIntegrityError('checked current event alias payload copies disagree')
                    bindings.install_path(owner,path,canonical)
                registry.attach_occurrence(canonical,Occurrence(*owner,path))
        finally:
            if hasattr(accepted.occurrences,'close'):accepted.occurrences.close()


def open_audited_proof_world_session(path,*,rules_id,expected_commitment,paged_household_members=None):
    """Full audit + existing canonical restoration; deliberately explicit/slow."""
    from .persistence_lazy import open_lazy_world_session
    admission=_WorldProofAuthority(expected_commitment)
    session=open_lazy_world_session(path,rules_id=rules_id,paged_household_members=paged_household_members,_proof_admission=admission)
    try:
        admission.execute(session,lambda:_restore_current_event_aliases(session))
        return session
    except BaseException:
        try:session.close()
        except BaseException:session.store.close()
        raise
