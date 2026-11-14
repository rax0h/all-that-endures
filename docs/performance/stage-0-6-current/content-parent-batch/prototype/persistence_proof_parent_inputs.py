"""Bounded ephemeral predecessor sorting, with checked SQLite spill on overflow."""
import sqlite3

from .incremental_store import StoreIntegrityError
from .persistence_lazy_budget import resident_bytes

BUFFER_BYTES = 1024 * 1024


class ParentInputs:
    def __init__(self, store):
        self.store = store
        self.rows = []
        self.bytes = resident_bytes(self.rows)
        self.spilled = False
        self.sorted = False

    def _insert(self, row):
        try:
            self.store.db.execute('INSERT INTO ate_content_predecessors VALUES(?,?,?,?)', row)
        except sqlite3.IntegrityError as exc:
            raise StoreIntegrityError('duplicate content predecessor locator') from exc

    def add(self, kind, locator, key, expected):
        if self.sorted:
            raise StoreIntegrityError('content predecessors already sorted')
        row = kind, locator, key, expected
        # Conservatively charge list over-allocation plus sort keys/workspace.
        # Existing source body/locator budgets still apply before this buffer.
        cost = resident_bytes(row) + 128
        if not self.spilled and self.bytes + cost > BUFFER_BYTES:
            self.store.db.execute('CREATE TEMP TABLE ate_content_predecessors(kind INTEGER,locator BLOB,key BLOB,value BLOB,PRIMARY KEY(kind,locator)) WITHOUT ROWID')
            self.spilled = True
            for buffered in self.rows:
                self._insert(buffered)
            self.rows.clear()
            self.bytes = resident_bytes(self.rows)
        if self.spilled:
            self._insert(row)
        else:
            self.rows.append(row)
            self.bytes += cost

    def members(self, kind):
        if self.spilled:
            return self.store.db.execute('SELECT key,value FROM ate_content_predecessors WHERE kind=? ORDER BY locator', (kind,))
        if not self.sorted:
            self.rows.sort(key=lambda row: (row[0], row[1]))
            self.sorted = True
        return ((row[2], row[3]) for row in self.rows if row[0] == kind)

    def close(self):
        self.rows.clear()
        self.bytes = resident_bytes(self.rows)
        if self.spilled:
            self.store.db.execute('DROP TABLE IF EXISTS ate_content_predecessors')
            self.spilled = False
