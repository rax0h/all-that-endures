"""Immutable proof-node storage inside a caller-owned SQLite transaction.

No root selection, commit, node collection or retained clean-node authority.
This private table is not selected by any existing World format reader.
"""
from .incremental_store import StoreError, StoreIntegrityError
from .persistence_proof_nodes import MAX_NODE_BYTES, decode_node, node_digest


class ProofNodeStore:
    def __init__(self, db):
        self.db = db
        self.reset_diagnostics()

    def create_schema(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS ate_proof_nodes ('
            'map_domain BLOB NOT NULL, digest BLOB NOT NULL CHECK(length(digest)=32), '
            'node_bytes BLOB NOT NULL CHECK(length(node_bytes)<=696), '
            'PRIMARY KEY(map_domain,digest)) WITHOUT ROWID')

    @staticmethod
    def _address(map_domain, digest):
        if type(map_domain) is not bytes or type(digest) is not bytes or len(digest) != 32:
            raise StoreIntegrityError('invalid proof node address')

    def read(self, map_domain, digest):
        self._address(map_domain, digest)
        self._read_requests += 1
        # TEXT length stops at NUL. Check storage class before evaluating its
        # length or transferring a corrupted body into Python.
        row = self.db.execute("SELECT CASE WHEN typeof(node_bytes)='blob' THEN length(node_bytes) END, "
            "CASE WHEN typeof(node_bytes)='blob' AND length(node_bytes)<=? THEN node_bytes END "
            'FROM ate_proof_nodes WHERE map_domain=? AND digest=?',
            (MAX_NODE_BYTES, map_domain, digest)).fetchone()
        if row is None:
            raise StoreIntegrityError('missing immutable proof node')
        self._read_nodes += 1
        size, raw = row
        if type(size) is not int or size > MAX_NODE_BYTES or type(raw) is not bytes:
            raise StoreIntegrityError('invalid stored proof node length/type')
        self._read_bytes += len(raw)
        if len(raw) != size or node_digest(map_domain, raw) != digest:
            raise StoreIntegrityError('stored proof node digest disagreement')
        decode_node(raw)
        return raw

    def write(self, map_domain, digest, raw):
        self._write_requests += 1
        if not self.db.in_transaction:
            raise StoreError('proof node write requires a caller transaction')
        self._address(map_domain, digest)
        decode_node(raw)
        if node_digest(map_domain, raw) != digest:
            raise StoreIntegrityError('written proof node digest disagreement')
        cursor = self.db.execute('INSERT OR IGNORE INTO ate_proof_nodes '
                                '(map_domain,digest,node_bytes) VALUES(?,?,?)',
                                (map_domain, digest, raw))
        inserted = cursor.rowcount
        cursor.close()
        if inserted:
            self._written_nodes += 1
            self._written_bytes += len(raw)
        elif self.read(map_domain, digest) != raw:
            raise StoreIntegrityError('conflicting immutable proof bytes')

    def reset_diagnostics(self):
        self._read_requests = self._read_nodes = self._read_bytes = 0
        self._write_requests = self._written_nodes = self._written_bytes = 0

    def diagnostics(self):
        return dict(read_requests=self._read_requests, read_nodes=self._read_nodes,
                    read_bytes=self._read_bytes, write_requests=self._write_requests,
                    written_nodes=self._written_nodes, written_bytes=self._written_bytes,
                    clean_cache_bytes=0)
