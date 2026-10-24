"""Connection-owned authorizer tracking for bounded read-only fault callbacks.

This is a SQL capability guard, not a sandbox for arbitrary Python code.
The caller's existing authorizer remains active and is restored on every exit.
"""
from contextlib import contextmanager
import sqlite3
from .incremental_store import StoreError

_WRITES={getattr(sqlite3,'SQLITE_'+name) for name in (
    'INSERT','UPDATE','DELETE','TRANSACTION','SAVEPOINT','ATTACH','DETACH','ALTER_TABLE','REINDEX','ANALYZE',
    'CREATE_INDEX','CREATE_TABLE','CREATE_TRIGGER','CREATE_VIEW','CREATE_TEMP_INDEX','CREATE_TEMP_TABLE',
    'CREATE_TEMP_TRIGGER','CREATE_TEMP_VIEW','CREATE_VTABLE','DROP_INDEX','DROP_TABLE','DROP_TRIGGER','DROP_VIEW',
    'DROP_TEMP_INDEX','DROP_TEMP_TABLE','DROP_TEMP_TRIGGER','DROP_TEMP_VIEW','DROP_VTABLE')}
_READ_PRAGMAS={'schema_version','data_version','table_info','table_xinfo','index_info','index_xinfo','index_list',
    'foreign_key_list','database_list','compile_options','page_count','freelist_count'}
_ARGUMENT_PRAGMAS={'table_info','table_xinfo','index_info','index_xinfo','index_list','foreign_key_list'}


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


class GuardedConnection(sqlite3.Connection):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._known_authorizer=None
        self._callback_guard=False

    def set_authorizer(self,callback):
        if self._callback_guard:raise StoreError('fault callback cannot replace SQL authorizer')
        result=super().set_authorizer(callback);self._known_authorizer=callback;return result

    def close(self):
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
