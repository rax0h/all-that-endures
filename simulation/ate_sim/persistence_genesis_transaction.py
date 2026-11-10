"""Private owned snapshots for offline genesis, never public read authority.

The source certificate cannot cross a commit. Source tables and main schema are
frozen; only predeclared derived proof tables may change before the final audit.
"""
from contextlib import contextmanager
import re
import sqlite3

from .incremental_store import StoreError, StoreIntegrityError
from .persistence_sqlite_guard import GuardedConnection, _WRITES, _READ_PRAGMAS, _ARGUMENT_PRAGMAS
from .persistence_validation_scope import ValidationScope


def _schema_definitions():
    from . import persistence_proof_record as record, persistence_proof_scope as scope
    from . import persistence_proof_publication as content, persistence_proof_inventory as inventory
    from . import persistence_proof_collection_directory as directory, persistence_proof_collection_publish as collection
    from . import persistence_proof_directory_publish as publication, persistence_proof_manifest_publish as manifest
    from . import persistence_proof_rank as ranks
    schemas=(record._NODE_SCHEMA,scope._SEEK_SCHEMA,record._BODY_SCHEMA,record._ROOT_SCHEMA,scope._DESCRIPTOR_SCHEMA,scope._ROOT_SCHEMA,
        content._ROOT_SCHEMA,inventory._SCHEMA,directory._SCHEMA,collection._SCHEMA,
        publication._SCHEMA,manifest._SCHEMA,manifest._CONTEXT)
    return schemas, directory._SOURCE_INDEXES, ranks._INDEX


def _prepare_schema(store, rank):
    from .persistence_proof_store import ProofNodeStore
    from .persistence_proof_seek import OrderedSeekMap
    from . import persistence_proof_collection_directory as directory, persistence_proof_rank as ranks
    schemas,source_indexes,rank_index=_schema_definitions()
    ProofNodeStore(store.db).create_schema()
    OrderedSeekMap(store.db,b'').create_schema()
    tables=set()
    for sql in schemas:
        name=re.match(r'CREATE TABLE (\w+)',sql).group(1)
        tables.add(name)
        store.db.execute(sql.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1))
        actual=store.db.execute("SELECT sql FROM main.sqlite_schema WHERE type='table' AND name=?",(name,)).fetchone()
        if actual is None or ''.join(actual[0].lower().split())!=''.join(sql.lower().split()):
            raise StoreIntegrityError('genesis proof schema differs: '+name)
    directory._source_indexes(store.db,create=True)
    if rank:ranks.index(store,create=True)
    return frozenset(tables)


class _FrozenScope(ValidationScope):
    frozen_sources=True
    def __init__(self, owner):
        super().__init__(owner.store,owner.pin,eligible=False,byte_limit=256*1024)
        self.owner=owner
        self._valid=True

    def can_reuse(self, store, pin):
        if not self._valid:return False
        self.owner.check()
        return (store is self.store and pin==self.pin
            and bool(getattr(store,'_checked_snapshot_depth',0)))


class _OwnedSources:
    freeze_factories=True
    def __init__(self,store,pin,*,proof=False,rank=True):
        self.store,self.pin,self.db,self.codec=store,pin,store.db,store.codec
        self.proof,self.rank=proof,rank
        self.denied=None;self.active=False;self.scope=None

    def reject(self,reason):
        self.denied=reason
        if getattr(self.db,'_native_sql_callback_depth',0) and self.boundary!='rollback':self.db.interrupt()
        raise StoreError(reason)

    def check(self):
        if (self.denied or not self.active or self.store._closed or self.store.db is not self.db
                or self.store.codec is not self.codec or self.store._phase_hook is not self.phase_hook
                or self.db.row_factory is not None or self.db.text_factory is not str
                or not self.db.in_transaction or not self.store._active_read_transaction
                or self.db._native_write_guard is not self or self.db._known_authorizer is not self.authorizer
                or self.store._validation_scope is not self.scope):
            self.reject(self.denied or 'owned genesis source custody changed')

    def _authorize(self,action,first,second,database,source):
        name=(first or '').lower()
        callback=bool(getattr(self.db,'_native_sql_callback_depth',0)) or self.db._callback_guard
        denied=callback and action in _WRITES
        if action==sqlite3.SQLITE_TRANSACTION and not self.boundary:denied=True
        if action==sqlite3.SQLITE_SAVEPOINT:denied=True
        if action in (sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_ALTER_TABLE,
                      sqlite3.SQLITE_ANALYZE):denied=True
        automatic=self.setup and any(name.startswith('sqlite_autoindex_'+table+'_') for table in self.tables)
        if action==sqlite3.SQLITE_REINDEX and database!='temp' and not (self.setup and name in self.indexes or automatic):denied=True
        if action in (sqlite3.SQLITE_CREATE_TRIGGER,sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
                      sqlite3.SQLITE_CREATE_VIEW,sqlite3.SQLITE_CREATE_TEMP_VIEW,
                      sqlite3.SQLITE_CREATE_VTABLE,sqlite3.SQLITE_DROP_VTABLE):denied=True
        if action==sqlite3.SQLITE_PRAGMA:
            reads=_READ_PRAGMAS|{'integrity_check','foreign_key_check','journal_mode','synchronous'}
            if name not in reads or second is not None and name not in _ARGUMENT_PRAGMAS:denied=True
        if action==sqlite3.SQLITE_FUNCTION and (second or '').lower()=='load_extension':denied=True
        if database=='main':
            if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                if (getattr(self,'sealed',False)
                        or name not in self.tables and name not in ('sqlite_master','sqlite_schema')):denied=True
            elif action==sqlite3.SQLITE_CREATE_TABLE:
                if name not in self.tables:denied=True
            elif action==sqlite3.SQLITE_CREATE_INDEX:
                if name not in self.indexes and not automatic:denied=True
            elif action in _WRITES and action not in (sqlite3.SQLITE_SAVEPOINT,sqlite3.SQLITE_REINDEX):denied=True
        if database=='temp' and action in (sqlite3.SQLITE_CREATE_TEMP_TABLE,sqlite3.SQLITE_CREATE_TABLE):
            setup_tables={'ate_ordered_seek_paths','ate_ordered_seek_build_frames','ate_ordered_seek_build_children'}
            if name in self.main_names or self.setup and name not in setup_tables:denied=True
        if denied:
            self.denied='source/schema/transaction mutation during owned genesis validation'
            if callback and self.boundary!='rollback':self.db.interrupt()
            return sqlite3.SQLITE_DENY
        return (sqlite3.SQLITE_OK if self.previous is None else
            self.db._invoke_sql_callback(self.previous,action,first,second,database,source))

    def __enter__(self):
        if type(self.db) is not GuardedConnection or self.db.in_transaction or self.store._active_read_transaction:
            raise StoreError('genesis validation requires an owned guarded transaction')
        if getattr(self.db,'_native_write_guard',None) is not None or self.db._callback_guard:
            raise StoreError('genesis validation cannot borrow another SQL capability')
        if self.db._writable_blobs:
            raise StoreError('genesis cannot borrow existing writable BLOB handles')
        if self.db.row_factory is not None or self.db.text_factory is not str:
            raise StoreError('genesis requires native SQLite result factories')
        self.phase_hook=self.store._phase_hook
        self.previous=self.db._known_authorizer
        self.previous_scope=getattr(self.store,'_validation_scope',None)
        self.read_context=None;self.boundary=False;self.setup=self.proof
        schemas,indexes,rank_index=_schema_definitions()
        self.tables=frozenset(re.match(r'CREATE TABLE (\w+)',sql).group(1) for sql in schemas) if self.proof else frozenset()
        self.indexes=frozenset(re.match(r'CREATE INDEX (\w+)',sql).group(1)
            for sql in (*indexes,*((rank_index,) if self.rank else ()))) if self.proof else frozenset()
        self.main_names=set(self.tables)
        self.authorizer=self._authorize
        sqlite3.Connection.set_authorizer(self.db,self.authorizer)
        self.db._known_authorizer=self.authorizer;self.db._native_write_guard=self
        try:
            self.boundary='begin'
            try:self.db.execute('BEGIN IMMEDIATE' if self.proof else 'BEGIN')
            finally:self.boundary=False
            if self.proof:_prepare_schema(self.store,self.rank)
            self.setup=False
            from .persistence_sqlite_guard import require_persistent_sources
            require_persistent_sources(self.db)
            self.main_names={r[0].lower() for r in self.db.execute('SELECT name FROM main.sqlite_schema')}
            self.store._active_read_transaction=True
            self.read_context=self.store.read_snapshot(self.pin)
            self.read_context.__enter__()
            self.scope=_FrozenScope(self)
            self.store._validation_scope=self.scope
            self.active=True
            self.check()
            return self
        except BaseException as exc:
            try:
                self.boundary='rollback'
                if self.db.in_transaction:self.db.rollback()
            except BaseException as cleanup:exc.add_note('genesis setup rollback failed: '+str(cleanup))
            finally:
                self.boundary=False
                self._restore()
            raise

    def _restore(self):
        self.active=False
        if self.scope is not None:self.scope.invalidate()
        self.db._native_write_guard=None
        sqlite3.Connection.set_authorizer(self.db,self.previous)
        self.db._known_authorizer=self.previous
        self.store._validation_scope=self.previous_scope
        if self.read_context is not None:
            context,self.read_context=self.read_context,None
            context.__exit__(None,None,None)
        self.store._active_read_transaction=False

    def __exit__(self,kind,error,tb):
        primary=error
        try:
            if primary is None:
                self.check()
                if self.proof:self.final_physical_check()
                self.boundary='commit' if self.proof else 'rollback'
                try:
                    if self.proof:self.db.commit()
                    else:self.db.rollback()
                finally:self.boundary=False
                if self.denied:raise StoreError(self.denied)
        except BaseException as exc:primary=exc
        finally:
            if self.db.in_transaction:
                try:
                    self.boundary='rollback'
                    self.db.rollback()
                except BaseException as exc:
                    if primary is None:primary=exc
                    else:primary.add_note('genesis rollback failed: '+str(exc))
                finally:self.boundary=False
            try:self._restore()
            except BaseException as exc:
                if primary is None:primary=exc
                else:primary.add_note('genesis guard cleanup failed: '+str(exc))
        if error is None and primary is not None:raise primary
        return False


class ProofGenesisTransaction(_OwnedSources):
    def __init__(self,store,pin,*,rank=True):
        super().__init__(store,pin,proof=True,rank=rank)
        self.audit_result=None;self.audit_reuses=0;self.physical_checks=0
        self.sealed=False

    def __enter__(self):
        from .persistence_lazy_store import _CONVERSION_AUDITS
        if not _CONVERSION_AUDITS.get() or self.pin.captured_head!=0:
            raise StoreError('bundled proof genesis requires explicit generation-zero construction')
        super().__enter__()
        try:
            if self.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()!=('7',):
                raise StoreError('bundled genesis requires format7')
            self.store._genesis_transaction=self
            return self
        except BaseException as exc:
            self.__exit__(type(exc),exc,exc.__traceback__)
            raise

    def verify_sources(self):
        self.check()
        if self.audit_result is None:
            from .persistence_proof_world_copy import _genesis_phase
            _genesis_phase('bootstrap.full_source_audit')
            self.audit_result=self.store._verify_all_in_snapshot()
            _genesis_phase('bootstrap.records.build')
        else:self.audit_reuses+=1
        return dict(self.audit_result)

    def final_physical_check(self):
        self.check()
        if self.audit_result is None or not self.sealed:
            raise StoreError('genesis cannot commit without full source and World audit')
        from .persistence_proof_world_copy import _genesis_phase
        _genesis_phase('bootstrap.final_physical_audit')
        if self.db.execute('PRAGMA main.integrity_check').fetchone()!=('ok',):
            raise StoreIntegrityError('new proof database failed global physical integrity')
        if self.db.execute('PRAGMA main.foreign_key_check').fetchone() is not None:
            raise StoreIntegrityError('new proof database failed foreign key integrity')
        self.physical_checks+=1

    def seal_manifest(self):
        self.check()
        self.sealed=True
        # Permission changes expire cached prepared statements too.
        sqlite3.Connection.set_authorizer(self.db,self.authorizer)

    def _restore(self):
        self.store._genesis_transaction=None
        super()._restore()


@contextmanager
def bootstrap_stage(store,pin):
    transaction=getattr(store,'_genesis_transaction',None)
    if transaction is not None:
        if type(transaction) is not ProofGenesisTransaction or transaction.store is not store or pin!=transaction.pin:
            raise StoreError('foreign genesis construction authority')
        transaction.check()
        if transaction.sealed:transaction.reject('genesis World audit already sealed the build')
        try:
            yield
            transaction.check()
        except BaseException:
            transaction.denied=transaction.denied or 'proof bootstrap stage failed'
            raise
        return
    if store.db.in_transaction or store._active_read_transaction:
        raise StoreError('proof bootstrap requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        yield
        store.db.commit()
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False


@contextmanager
def catalog_snapshot(store,pin):
    from .persistence_lazy_store import _CONVERSION_AUDITS
    existing=getattr(store,'_validation_scope',None)
    if existing is not None and existing.can_reuse(store,pin):
        with store.read_snapshot(pin):yield
    elif _CONVERSION_AUDITS.get() and not store.db.in_transaction and not store._active_read_transaction:
        with _OwnedSources(store,pin):yield
    else:
        with store.read_snapshot(pin):yield
