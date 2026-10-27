"""Operation-local SQL capability: native preparation/ack cannot publish data."""
from contextlib import contextmanager
import sqlite3
from .incremental_store import StoreError,StoreIntegrityError
from .persistence_sqlite_guard import GuardedConnection,_WRITES,_READ_PRAGMAS,_ARGUMENT_PRAGMAS

class NativeWriteGuard:
    def __init__(self,db):
        if type(db) is not GuardedConnection:raise StoreError('native proof saves require guarded connection')
        self.db=db;self.denied=None;self.depth=0

    def reject(self,reason):
        self.denied=reason
        raise StoreError(reason)

    def _install(self):
        allow=self.depth>0;previous=self.previous
        def authorize(action,first,second,database,source):
            callback=getattr(self.db,'_native_sql_callback_depth',0)>0
            denied=callback and action in _WRITES
            if not allow:
                if action in _WRITES and action not in (sqlite3.SQLITE_TRANSACTION,sqlite3.SQLITE_SAVEPOINT) and database!='temp':denied=True
                if action in (sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH):denied=True
                if action==sqlite3.SQLITE_PRAGMA and ((first or '').lower() not in _READ_PRAGMAS or second is not None and (first or '').lower() not in _ARGUMENT_PRAGMAS):denied=True
                if action==sqlite3.SQLITE_FUNCTION and (second or '').lower()=='load_extension':denied=True
            if denied:self.denied='unlisted durable SQL outside native proof publisher';return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if previous is None else self.db._invoke_sql_callback(previous,action,first,second,database,source)
        self.authorizer=authorize
        sqlite3.Connection.set_authorizer(self.db,authorize);self.db._known_authorizer=authorize

    def __enter__(self):
        if self.db.in_transaction:raise StoreError('native proof operation requires an owned transaction boundary')
        if getattr(self.db,'_native_write_guard',None) is not None or self.db._callback_guard:raise StoreError('nested native SQL write guard')
        self.previous=self.db._known_authorizer;self.db._native_write_guard=self;self._install();return self

    def __exit__(self,*_):
        self.db._native_write_guard=None
        sqlite3.Connection.set_authorizer(self.db,self.previous);self.db._known_authorizer=self.previous

    @contextmanager
    def publisher(self):
        self.depth+=1;self._install()
        try:yield
        finally:self.depth-=1;self._install()

    def check(self):
        if self.denied or self.db._native_write_guard is not self or self.db._known_authorizer is not self.authorizer:raise StoreIntegrityError(self.denied or 'native SQL capability was replaced')
