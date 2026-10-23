"""Immutable ordered byte-key radix proofs, independent of physical generations.

No publisher, World object admission, retained clean cache or node collection.
The caller owns a stable SQLite snapshot and every write/rollback transaction.
"""
from dataclasses import dataclass
import uuid

from .incremental_store import StoreError, StoreIntegrityError
from .persistence_proof_nodes import Root, MAX_COUNT, _digest

MAX_KEY_BYTES=32768
MAX_NODE_BYTES=131072


@dataclass(frozen=True)
class _Leaf:
    key: bytes
    value: bytes


@dataclass(frozen=True)
class _Branch:
    prefix: bytes
    children: tuple


def _key(key):
    if type(key) is not bytes or len(key)>MAX_KEY_BYTES:
        raise StoreIntegrityError('invalid ordered seek key')
    return key


def _symbols(key):
    return bytes(symbol for byte in key for symbol in ((byte>>4)+1,(byte&15)+1))+b'\x00'


def _prefix(node):return _symbols(node.key) if type(node) is _Leaf else node.prefix


def _count(node):return 1 if type(node) is _Leaf else sum(ref.count for _,ref in node.children)


def _encode(node):
    if type(node) is _Leaf:
        _key(node.key)
        if type(node.value) is not bytes or len(node.value)!=32:
            raise StoreIntegrityError('invalid ordered seek value')
        return b'ATES\x01L'+len(node.key).to_bytes(4,'big')+node.key+node.value
    if (type(node) is not _Branch or type(node.prefix) is not bytes or len(node.prefix)>=2*MAX_KEY_BYTES
            or any(not 1<=s<=16 for s in node.prefix) or not 2<=len(node.children)<=17):
        raise StoreIntegrityError('invalid ordered seek branch')
    previous=-1;total=0;parts=[]
    for slot,ref in node.children:
        if (type(slot) is not int or not previous<slot<=16 or type(ref) is not Root
                or type(ref.count) is not int or not 0<ref.count<=MAX_COUNT
                or type(ref.digest) is not bytes or len(ref.digest)!=32):
            raise StoreIntegrityError('invalid ordered seek child')
        previous=slot;total+=ref.count
        parts.append(bytes([slot])+ref.count.to_bytes(8,'big')+ref.digest)
    if total>MAX_COUNT:raise StoreIntegrityError('ordered seek count overflow')
    return b'ATES\x01B'+len(node.prefix).to_bytes(4,'big')+node.prefix+bytes([len(parts)])+b''.join(parts)


def _decode(raw):
    if type(raw) is not bytes or len(raw)>MAX_NODE_BYTES or len(raw)<10:
        raise StoreIntegrityError('invalid ordered seek node length/type')
    size=int.from_bytes(raw[6:10],'big')
    if raw[:6]==b'ATES\x01L':
        if size>MAX_KEY_BYTES or len(raw)!=10+size+32:raise StoreIntegrityError('invalid ordered seek leaf bytes')
        node=_Leaf(raw[10:10+size],raw[10+size:])
    elif raw[:6]==b'ATES\x01B':
        if size>=2*MAX_KEY_BYTES or len(raw)<11+size:raise StoreIntegrityError('invalid ordered seek prefix')
        count=raw[10+size]
        if len(raw)!=11+size+count*41:raise StoreIntegrityError('invalid ordered seek branch bytes')
        children=[]
        for offset in range(11+size,len(raw),41):
            children.append((raw[offset],Root(raw[offset+9:offset+41],int.from_bytes(raw[offset+1:offset+9],'big'))))
        node=_Branch(raw[10:10+size],tuple(children))
    else:raise StoreIntegrityError('unknown ordered seek node tag')
    if _encode(node)!=raw:raise StoreIntegrityError('noncanonical ordered seek node')
    return node


class OrderedSeekMap:
    def __init__(self,db,domain):
        if type(domain) is not bytes:raise StoreIntegrityError('invalid ordered seek domain')
        self.db,self.domain=db,domain
        self.empty=Root(_digest(b'ate-ordered-seek-empty/1',domain),0)
        self.reset_diagnostics()

    def create_schema(self):
        if not self.db.in_transaction:raise StoreError('ordered seek schema requires caller transaction')
        self.db.execute('CREATE TABLE IF NOT EXISTS ate_ordered_seek_nodes('
            'domain BLOB NOT NULL,digest BLOB NOT NULL,raw BLOB NOT NULL,PRIMARY KEY(domain,digest)) WITHOUT ROWID')
        # Prepare workspace BEFORE a streaming source cursor opens. Per-point
        # CREATE/DROP would lock against that active cursor. Rows, not schema,
        # are scoped to an operation and removed by DML in set's finally.
        self.db.execute('CREATE TEMP TABLE IF NOT EXISTS ate_ordered_seek_paths('
            'operation BLOB,ordinal INTEGER,slot INTEGER,raw BLOB,digest BLOB,count INTEGER,'
            'PRIMARY KEY(operation,ordinal)) WITHOUT ROWID')
        self.db.execute('CREATE TEMP TABLE IF NOT EXISTS ate_ordered_seek_build_frames('
            'operation BLOB,depth INTEGER,prefix BLOB,PRIMARY KEY(operation,depth)) WITHOUT ROWID')
        self.db.execute('CREATE TEMP TABLE IF NOT EXISTS ate_ordered_seek_build_children('
            'operation BLOB,depth INTEGER,slot INTEGER,count INTEGER,digest BLOB,'
            'PRIMARY KEY(operation,depth,slot)) WITHOUT ROWID')

    def _reference(self,ref):
        if (type(ref) is not Root or type(ref.digest) is not bytes or len(ref.digest)!=32
                or type(ref.count) is not int or not 0<=ref.count<=MAX_COUNT
                or ref.count==0 and ref!=self.empty):raise StoreIntegrityError('invalid ordered seek root')

    def _read(self,ref,required=b''):
        self._reference(ref);self._read_requests+=1
        if not ref.count:raise StoreIntegrityError('empty ordered seek child')
        row=self.db.execute("SELECT CASE WHEN typeof(raw)='blob' THEN length(raw) END,"
            "CASE WHEN typeof(raw)='blob' AND length(raw)<=? THEN raw END "
            'FROM ate_ordered_seek_nodes WHERE domain=? AND digest=?',
            (MAX_NODE_BYTES,self.domain,ref.digest)).fetchone()
        if row is None:raise StoreIntegrityError('missing ordered seek node')
        size,raw=row
        if (type(size) is not int or size>MAX_NODE_BYTES or type(raw) is not bytes or len(raw)!=size
                or _digest(b'ate-ordered-seek-node/1',self.domain,raw)!=ref.digest):
            raise StoreIntegrityError('ordered seek node bytes/digest disagreement')
        self._read_nodes+=1;self._read_bytes+=len(raw)
        node=_decode(raw)
        if _count(node)!=ref.count or not _prefix(node).startswith(required):
            raise StoreIntegrityError('ordered seek child count/path disagreement')
        return node

    def _write(self,node):
        if not self.db.in_transaction:raise StoreError('ordered seek write requires caller transaction')
        raw=_encode(node);digest=_digest(b'ate-ordered-seek-node/1',self.domain,raw);ref=Root(digest,_count(node))
        cursor=self.db.execute('INSERT OR IGNORE INTO ate_ordered_seek_nodes VALUES(?,?,?)',(self.domain,digest,raw))
        if cursor.rowcount:
            self._written_nodes+=1;self._written_bytes+=len(raw)
        elif _encode(self._read(ref))!=raw:raise StoreIntegrityError('conflicting ordered seek node bytes')
        cursor.close();return ref

    def _branch(self,prefix,children):
        if not children:return self.empty
        if len(children)==1:
            slot,ref=children[0];self._read(ref,prefix+bytes([slot]));return ref
        return self._write(_Branch(prefix,tuple(children)))

    def set(self,root,key,value):
        if not self.db.in_transaction:raise StoreError('ordered seek mutation requires caller transaction')
        self._reference(root);_key(key)
        if value is not None and (type(value) is not bytes or len(value)!=32):
            raise StoreIntegrityError('invalid ordered seek value')
        wanted=_symbols(key)
        operation=uuid.uuid4().bytes
        ref,required,depth=root,b'',0
        try:
            while True:
                if not ref.count:
                    if value is None:return root
                    changed=self._write(_Leaf(key,value));break
                node=self._read(ref,required);prefix=_prefix(node)
                if type(node) is _Leaf and node.key==key:
                    if node.value==value:return root
                    changed=self.empty if value is None else self._write(_Leaf(key,value));break
                if not wanted.startswith(prefix):
                    if value is None:return root
                    shared=0
                    while wanted[shared]==prefix[shared]:shared+=1
                    new=self._write(_Leaf(key,value))
                    children=tuple(sorted(((prefix[shared],ref),(wanted[shared],new))))
                    changed=self._write(_Branch(wanted[:shared],children));break
                if type(node) is not _Branch:raise StoreIntegrityError('invalid ordered seek terminal prefix')
                slot=wanted[len(prefix)];children=dict(node.children)
                if slot not in children:
                    if value is None:return root
                    children[slot]=self._write(_Leaf(key,value))
                    changed=self._branch(prefix,tuple(sorted(children.items())));break
                self.db.execute('INSERT INTO ate_ordered_seek_paths VALUES(?,?,?,?,?,?)',
                    (operation,depth,slot,_encode(node),ref.digest,ref.count))
                depth+=1;ref=children[slot];required=prefix+bytes([slot])
            cursor=self.db.execute('SELECT slot,raw,digest,count FROM ate_ordered_seek_paths '
                                   'WHERE operation=? ORDER BY ordinal DESC',(operation,))
            try:
                for slot,raw,digest,count in cursor:
                    parent=_decode(raw)
                    if (type(parent) is not _Branch or _count(parent)!=count
                            or _digest(b'ate-ordered-seek-node/1',self.domain,raw)!=digest):
                        raise StoreIntegrityError('ordered seek staged ancestor disagreement')
                    children=dict(parent.children)
                    if changed.count:children[slot]=changed
                    else:del children[slot]
                    changed=self._branch(parent.prefix,tuple(sorted(children.items())))
            finally:cursor.close()
            return changed
        finally:self.db.execute('DELETE FROM ate_ordered_seek_paths WHERE operation=?',(operation,))

    def build(self,rows):
        if not self.db.in_transaction:raise StoreError('ordered seek build requires caller transaction')
        operation=uuid.uuid4().bytes;depth=-1;previous=None;pending=None;pending_prefix=None
        def frame_prefix():
            return self.db.execute('SELECT prefix FROM ate_ordered_seek_build_frames '
                'WHERE operation=? AND depth=?',(operation,depth)).fetchone()[0]
        def add_child(prefix):
            if not pending_prefix.startswith(prefix) or len(pending_prefix)<=len(prefix):
                raise StoreIntegrityError('ordered seek construction prefix disagreement')
            self.db.execute('INSERT INTO ate_ordered_seek_build_children VALUES(?,?,?,?,?)',
                (operation,depth,pending_prefix[len(prefix)],pending.count,pending.digest))
        def close_frame(prefix):
            children=tuple((slot,Root(digest,count)) for slot,count,digest in self.db.execute(
                'SELECT slot,count,digest FROM ate_ordered_seek_build_children '
                'WHERE operation=? AND depth=? ORDER BY slot',(operation,depth)))
            if not 2<=len(children)<=17:raise StoreIntegrityError('invalid ordered seek construction branch')
            result=self._write(_Branch(prefix,children))
            self.db.execute('DELETE FROM ate_ordered_seek_build_children WHERE operation=? AND depth=?',(operation,depth))
            self.db.execute('DELETE FROM ate_ordered_seek_build_frames WHERE operation=? AND depth=?',(operation,depth))
            return result
        try:
            for item in rows:
                if type(item) not in (tuple,list) or len(item)!=2:
                    raise StoreIntegrityError('invalid ordered seek build row')
                key,value=item;_key(key)
                if previous is not None and key<=previous:raise StoreIntegrityError('ordered seek input must be strictly sorted')
                if type(value) is not bytes or len(value)!=32:raise StoreIntegrityError('invalid ordered seek build value')
                symbols=_symbols(key)
                if previous is not None:
                    before=_symbols(previous);shared=0
                    while before[shared]==symbols[shared]:shared+=1
                    while depth>=0 and len(frame_prefix())>shared:
                        prefix=frame_prefix();add_child(prefix)
                        pending=close_frame(prefix);pending_prefix=prefix;depth-=1
                    if depth<0 or len(frame_prefix())<shared:
                        depth+=1;prefix=before[:shared]
                        self.db.execute('INSERT INTO ate_ordered_seek_build_frames VALUES(?,?,?)',(operation,depth,prefix))
                    else:prefix=frame_prefix()
                    add_child(prefix)
                pending=self._write(_Leaf(key,value));pending_prefix=symbols;previous=key
            while depth>=0:
                prefix=frame_prefix();add_child(prefix)
                pending=close_frame(prefix);pending_prefix=prefix;depth-=1
            return self.empty if pending is None else pending
        finally:
            self.db.execute('DELETE FROM ate_ordered_seek_build_children WHERE operation=?',(operation,))
            self.db.execute('DELETE FROM ate_ordered_seek_build_frames WHERE operation=?',(operation,))

    def get(self,root,key):
        self._reference(root);_key(key);wanted=_symbols(key);ref,required=root,b''
        while ref.count:
            node=self._read(ref,required);prefix=_prefix(node)
            if not wanted.startswith(prefix):return None
            if type(node) is _Leaf:return node.value if node.key==key else None
            slot=wanted[len(prefix)];ref=dict(node.children).get(slot,self.empty);required=prefix+bytes([slot])
        return None

    def _minimum(self,ref,required):
        while True:
            node=self._read(ref,required)
            if type(node) is _Leaf:return node.key,node.value
            slot,ref=node.children[0];required=node.prefix+bytes([slot])

    def _successor(self,root,after):
        if not root.count:return None
        if after is None:return self._minimum(root,b'')
        wanted=_symbols(after);ref,required,candidate=root,b'',None
        while True:
            node=self._read(ref,required);prefix=_prefix(node)
            if type(node) is _Leaf:
                if node.key>after:return node.key,node.value
                return self._minimum(*candidate) if candidate is not None else None
            common=wanted[:len(prefix)]
            if prefix>common:return self._minimum(ref,required)
            if prefix<common:return self._minimum(*candidate) if candidate is not None else None
            slot=wanted[len(prefix)];equal=None;greater=None
            for chosen,child in node.children:
                if chosen==slot:equal=child
                elif chosen>slot and greater is None:greater=(child,prefix+bytes([chosen]))
            if equal is None:
                chosen=greater if greater is not None else candidate
                return self._minimum(*chosen) if chosen is not None else None
            if greater is not None:candidate=greater
            ref,required=equal,prefix+bytes([slot])

    def page(self,root,*,after=None,limit=128):
        self._reference(root)
        if after is not None:_key(after)
        if type(limit) is not int or not 1<=limit<=256:raise StoreIntegrityError('invalid ordered seek page limit')
        result=[]
        for _ in range(limit):
            item=self._successor(root,after)
            if item is None:break
            if after is not None and item[0]<=after:raise StoreIntegrityError('ordered seek successor did not advance')
            result.append(item);after=item[0]
        return tuple(result)

    def verify(self,root):
        count=0;after=None
        while True:
            page=self.page(root,after=after,limit=256)
            if not page:break
            count+=len(page);after=page[-1][0]
            if count>root.count:raise StoreIntegrityError('ordered seek surplus leaves')
        if count!=root.count:raise StoreIntegrityError('ordered seek incomplete leaf inventory')

    def reset_diagnostics(self):
        self._read_requests=self._read_nodes=self._read_bytes=self._written_nodes=self._written_bytes=0

    def diagnostics(self):
        return dict(read_requests=self._read_requests,read_nodes=self._read_nodes,read_bytes=self._read_bytes,
                    written_nodes=self._written_nodes,written_bytes=self._written_bytes,clean_cache_bytes=0)
