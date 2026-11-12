"""Connection-owned authorizer tracking for bounded read-only fault callbacks.

This is a SQL capability guard, not a sandbox for arbitrary Python code.
The caller's existing authorizer remains active and is restored on every exit.
"""
from contextlib import contextmanager
import sqlite3
import weakref
import re
from .incremental_store import StoreError

_WRITES={getattr(sqlite3,'SQLITE_'+name) for name in (
    'INSERT','UPDATE','DELETE','TRANSACTION','SAVEPOINT','ATTACH','DETACH','ALTER_TABLE','REINDEX','ANALYZE',
    'CREATE_INDEX','CREATE_TABLE','CREATE_TRIGGER','CREATE_VIEW','CREATE_TEMP_INDEX','CREATE_TEMP_TABLE',
    'CREATE_TEMP_TRIGGER','CREATE_TEMP_VIEW','CREATE_VTABLE','DROP_INDEX','DROP_TABLE','DROP_TRIGGER','DROP_VIEW',
    'DROP_TEMP_INDEX','DROP_TEMP_TABLE','DROP_TEMP_TRIGGER','DROP_TEMP_VIEW','DROP_VTABLE')}
_READ_PRAGMAS={'schema_version','data_version','table_info','table_xinfo','index_info','index_xinfo','index_list',
    'foreign_key_list','database_list','compile_options','page_count','freelist_count'}
_ARGUMENT_PRAGMAS={'table_info','table_xinfo','index_info','index_xinfo','index_list','foreign_key_list'}
# An intentionally narrow allowlist of engine read/control statements. Anything
# else advances custody, even harmless commented/lowercase queries. Never parse
# arbitrary SQL as proof that it cannot replace bytes or reset SQLite counters.
_FACT_READ_SQL=frozenset(('PRAGMA data_version','PRAGMA schema_version',
                          'PRAGMA main.schema_version','PRAGMA temp.schema_version',
                          'BEGIN','COMMIT','ROLLBACK'))
_WITH_WRITES=re.compile(r'\b(?:INSERT|UPDATE|DELETE|REPLACE)\b',re.IGNORECASE)


def require_persistent_sources(db):
    """Unqualified validated names must resolve to durable main objects.

    SQLite resolves TEMP names first and identifiers ignore ASCII case.
    Reject shadows across all composed sources, not merely one root table.
    Proof workspaces use distinct temporary names and remain permitted.
    """
    if db.execute("SELECT 1 FROM sqlite_temp_schema AS t JOIN main.sqlite_schema AS m ON t.name=m.name COLLATE NOCASE WHERE t.type IN ('table','view') LIMIT 1").fetchone() is not None:
        raise StoreError('proof source cannot shadow persistent SQLite objects')
    for schema in ('main.sqlite_schema','sqlite_temp_schema'):
        if db.execute("SELECT 1 FROM "+schema+" WHERE type='trigger' LIMIT 1").fetchone() is not None:
            raise StoreError('proof source cannot contain database triggers')


class _NativeGuardCursor(sqlite3.Cursor):
    def __setattr__(self,name,value):
        if name=='row_factory':
            self.connection._reject_callback_factory_change()
            if value is not None:self.connection._sql_callback_generation += 1
            value=self.connection._wrap_sql_callback(value)
        return super().__setattr__(name,value)

    def execute(self,*args,**kwargs):
        self.connection._reject_callback_sql()
        self.connection._note_fact_sql(args[0] if args else kwargs.get('sql'))
        return super().execute(*args,**kwargs)
    def executemany(self,*args,**kwargs):
        self.connection._reject_callback_sql()
        self.connection._note_fact_sql(args[0] if args else kwargs.get('sql'))
        return super().executemany(*args,**kwargs)
    def executescript(self,*args,**kwargs):
        self.connection._reject_callback_sql()
        self.connection._schema_statement_generation += 1
        return super().executescript(*args,**kwargs)


class _GuardedBlob:
    """Track writable DB-API handles so source custody cannot borrow one."""
    def __init__(self,connection,blob):
        self._connection,self._blob=connection,blob
    def __getattr__(self,name):return getattr(self._blob,name)
    def __len__(self):return len(self._blob)
    def __getitem__(self,key):return self._blob[key]
    def _write_check(self):
        guard=getattr(self._connection,'_native_write_guard',None)
        if guard is not None:guard.reject('guarded source cannot mutate a writable BLOB')
    def __setitem__(self,key,value):
        self._write_check();self._blob[key]=value
    def write(self,value):
        self._write_check();return self._blob.write(value)
    def close(self):
        try:return self._blob.close()
        finally:self._connection._writable_blobs.discard(self)
    def __enter__(self):
        self._blob.__enter__();return self
    def __exit__(self,*args):self.close()


class GuardedConnection(sqlite3.Connection):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._known_authorizer=None
        self._callback_guard=False
        self._writable_blobs=weakref.WeakSet()
        # Immutable fact reuse is deliberately disabled after caller SQL
        # callbacks or opaque mutation/native-extension APIs have been used,
        # even if later unregistered. These need not change total_changes.
        self._sql_callback_generation=0
        self._schema_statement_generation=0

    def _note_fact_sql(self,sql):
        if type(sql) is str and (sql.startswith('SELECT ') or sql in _FACT_READ_SQL):return
        # SQLite WITH prefixes SELECT or one of these DML verbs, never DDL or
        # PRAGMA. Scan the entire text, including quoted/comment text: harmless
        # false positives advance custody too. No stripping or SQL rewriting.
        if type(sql) is str and sql.startswith('WITH ') and _WITH_WRITES.search(sql) is None:return
        self._schema_statement_generation += 1

    def blobopen(self,table,column,row,/,*,readonly=False,name='main'):
        guard=getattr(self,'_native_write_guard',None)
        if guard is not None and not readonly:guard.reject('guarded source cannot open a writable BLOB')
        if not readonly:self._sql_callback_generation += 1
        blob=super().blobopen(table,column,row,readonly=readonly,name=name)
        if readonly:return blob
        wrapped=_GuardedBlob(self,blob)
        self._writable_blobs.add(wrapped)
        return wrapped

    def deserialize(self,data,/,*,name='main'):
        guard=getattr(self,'_native_write_guard',None)
        if guard is not None:guard.reject('guarded source cannot deserialize a replacement database')
        self._sql_callback_generation += 1
        return super().deserialize(data,name=name)

    def enable_load_extension(self,enabled,/):
        self._reject_callback_registration()
        if enabled:self._sql_callback_generation += 1
        return super().enable_load_extension(enabled)

    def load_extension(self,path,/,*,entrypoint=None):
        self._reject_callback_registration()
        self._sql_callback_generation += 1
        return super().load_extension(path,entrypoint=entrypoint)

    def __setattr__(self,name,value):
        if name in ('row_factory','text_factory'):
            self._reject_callback_factory_change()
            if (name=='row_factory' and value is not None
                    or name=='text_factory' and value not in (str,bytes)):
                self._sql_callback_generation += 1
            if name=='row_factory' or value not in (str,bytes):value=self._wrap_sql_callback(value)
        return super().__setattr__(name,value)

    def _reject_callback_factory_change(self):
        guard=getattr(self,'_native_write_guard',None)
        if guard is not None and (getattr(guard,'freeze_factories',False)
                or getattr(self,'_native_sql_callback_depth',0) or self._callback_guard):
            guard.reject('native callback cannot replace SQLite factory')

    def _wrap_sql_callback(self,callback):
        if callback is None or not callable(callback):return callback
        def guarded(*args):return self._invoke_sql_callback(callback,*args)
        return guarded

    def _reject_callback_registration(self):
        guard=getattr(self,'_native_write_guard',None)
        if guard is not None:guard.reject('native proof operation cannot register SQLite callbacks')

    def create_function(self,name,narg,func,*,deterministic=False):
        self._reject_callback_registration()
        if func is not None:self._sql_callback_generation += 1
        return super().create_function(name,narg,self._wrap_sql_callback(func),deterministic=deterministic)

    def _aggregate_callback(self,aggregate_class,*,window=False):
        if aggregate_class is None:return None
        db=self
        class GuardedAggregate:
            def __init__(self):self.inner=db._invoke_sql_callback(aggregate_class)
            def step(self,*args):return db._invoke_sql_callback(self.inner.step,*args)
            def finalize(self):return db._invoke_sql_callback(self.inner.finalize)
        if window:
            class GuardedWindow(GuardedAggregate):
                def value(self):return db._invoke_sql_callback(self.inner.value)
                def inverse(self,*args):return db._invoke_sql_callback(self.inner.inverse,*args)
            return GuardedWindow
        return GuardedAggregate

    def create_aggregate(self,name,n_arg,aggregate_class):
        self._reject_callback_registration()
        if aggregate_class is not None:self._sql_callback_generation += 1
        return super().create_aggregate(name,n_arg,self._aggregate_callback(aggregate_class))

    def create_window_function(self,name,num_params,aggregate_class):
        self._reject_callback_registration()
        if aggregate_class is not None:self._sql_callback_generation += 1
        return super().create_window_function(name,num_params,self._aggregate_callback(aggregate_class,window=True))

    def create_collation(self,name,callback):
        self._reject_callback_registration()
        if callback is not None:self._sql_callback_generation += 1
        return super().create_collation(name,self._wrap_sql_callback(callback))

    def _reject_callback_sql(self):
        guard=getattr(self,'_native_write_guard',None)
        if guard is not None and getattr(self,'_native_sql_callback_depth',0):guard.reject('native SQLite callbacks cannot execute SQL')

    def _invoke_sql_callback(self,callback,*args):
        if getattr(self,'_native_write_guard',None) is None:return callback(*args)
        self._native_sql_callback_depth=getattr(self,'_native_sql_callback_depth',0)+1
        try:return callback(*args)
        finally:self._native_sql_callback_depth-=1

    def set_trace_callback(self,callback):
        if callback is not None and not callable(callback):raise TypeError('trace callback must be callable')
        if callback is not None:self._sql_callback_generation += 1
        return super().set_trace_callback(None if callback is None else lambda sql:self._invoke_sql_callback(callback,sql))

    def set_progress_handler(self,callback,n):
        if callback is not None:self._sql_callback_generation += 1
        if callback is not None and not callable(callback):raise TypeError('progress callback must be callable')
        return super().set_progress_handler(None if callback is None else lambda:self._invoke_sql_callback(callback),n)

    def cursor(self,factory=None):
        if factory is None or factory is sqlite3.Cursor:factory=_NativeGuardCursor
        elif getattr(self,'_native_write_guard',None) is not None and factory is not _NativeGuardCursor:
            self._native_write_guard.reject('native proof operation requires guarded cursors')
        elif factory is not _NativeGuardCursor:self._sql_callback_generation += 1
        return super().cursor(factory)

    def execute(self,*args,**kwargs):
        self._reject_callback_sql()
        return self.cursor().execute(*args,**kwargs)

    def executemany(self,*args,**kwargs):
        self._reject_callback_sql()
        return self.cursor().executemany(*args,**kwargs)

    def executescript(self,*args,**kwargs):
        self._reject_callback_sql()
        return self.cursor().executescript(*args,**kwargs)

    def commit(self):
        self._reject_callback_sql()
        return super().commit()

    def rollback(self):
        self._reject_callback_sql()
        return super().rollback()

    def set_authorizer(self,callback):
        guard=getattr(self,'_native_write_guard',None)
        if guard is not None:guard.reject('native proof operation cannot replace SQL authorizer')
        if self._callback_guard:raise StoreError('fault callback cannot replace SQL authorizer')
        if callback is not None:self._sql_callback_generation += 1
        result=super().set_authorizer(callback);self._known_authorizer=callback;return result

    def close(self):
        guard=getattr(self,'_native_write_guard',None)
        if guard is not None:guard.reject('native proof operation cannot close connection')
        if self._callback_guard:raise StoreError('fault callback cannot close guarded connection')
        return super().close()

    @contextmanager
    def readonly_callback(self):
        if self._callback_guard:raise StoreError('nested SQL fault callback guard is unsupported')
        previous=self._known_authorizer
        def authorize(action,first,second,database,source):
            if action in _WRITES:return sqlite3.SQLITE_DENY
            if action==sqlite3.SQLITE_PRAGMA:
                name=(first or '').lower()
                if name not in _READ_PRAGMAS or second is not None and name not in _ARGUMENT_PRAGMAS:return sqlite3.SQLITE_DENY
            if action==sqlite3.SQLITE_FUNCTION and (second or '').lower()=='load_extension':return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if previous is None else previous(action,first,second,database,source)
        super().set_authorizer(authorize);self._callback_guard=True
        try:yield
        finally:
            self._callback_guard=False
            super().set_authorizer(previous)
