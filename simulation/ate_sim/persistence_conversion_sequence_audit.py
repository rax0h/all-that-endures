"""Disk-backed physical inventories for explicit clean sequence construction."""
from .incremental_store import StoreIntegrityError
from .persistence_conversion_workspace import DiskSet, DiskLookup


def scrub(sequence, workspace, inventory):
    from .persistence_lazy_sequence import (NAMESPACES, DESCRIPTOR_NAMESPACE, NODE_NAMESPACE,
        PARENT_NAMESPACE, LOCATOR_NAMESPACE, DIRECTORY_NAMESPACE, MEMBER_NAMESPACE, LEAF_SIZE, FANOUT)
    codec, store, inc = sequence._store.codec, sequence._store, sequence._incarnation
    expected = {namespace:DiskSet(workspace) for namespace in NAMESPACES}
    wanted_members, found_members = DiskSet(workspace), DiskSet(workspace)
    expected[DESCRIPTOR_NAMESPACE].add(codec.encode(inc))
    occurrences = None
    count = 0
    def mark(namespace, key, error):
        encoded = codec.encode(key)
        if encoded in expected[namespace]:raise StoreIntegrityError(error)
        expected[namespace].add(encoded)
    def visit(link, parent, root=False):
        nonlocal count
        key = inc,link[0]
        mark(NODE_NAMESPACE,key,'duplicate/cyclic main sequence node')
        expected[PARENT_NAMESPACE].add(codec.encode(key))
        kind,entries=sequence._nread(link,parent)
        if not root and len(entries)<(LEAF_SIZE//2 if kind=='leaf' else FANOUT//2):
            raise StoreIntegrityError('underfull main sequence node')
        if root and kind=='branch' and len(entries)<2:
            raise StoreIntegrityError('uncollapsed sequence root')
        if kind=='leaf':
            for slot,(occurrence,value) in enumerate(entries):
                mark(LOCATOR_NAMESPACE,(inc,occurrence),'duplicate main sequence occurrence')
                if sequence._read(LOCATOR_NAMESPACE,(inc,occurrence))!=(link[0],slot):
                    raise StoreIntegrityError('sequence scrub locator disagreement')
                member=sequence._member_key(value)
                if member is not None:wanted_members.add(codec.encode((member,count,occurrence)))
                yield occurrence,(count,value)
                count+=1
        else:
            for slot,child in enumerate(entries):yield from visit(child,(link[0],slot))
    def directory(link):
        mark(DIRECTORY_NAMESPACE,(inc,link[0]),'duplicate/cyclic sequence directory node')
        node=sequence._dread(link)
        if node[0]=='directory-branch/v1':
            for child in node[2]:directory(child[1:])
            return
        value,root=node[1:]
        def member(link,lower,upper):
            if link is None:return
            mark(MEMBER_NAMESPACE,(inc,link[0]),'duplicate/cyclic sequence member node')
            row=sequence._mread(link,value)
            rank,actual=occurrences.get(link[0],(-1,None))
            if actual!=value or not lower<rank<upper:
                raise StoreIntegrityError('sequence scrub member order disagreement')
            member(row[2],lower,rank)
            found_members.add(codec.encode((sequence._member_key(value),rank,link[0])))
            member(row[3],rank,upper)
        member(root,-1,sequence._length)
    try:
        with store.read_snapshot(sequence._pin):
            occurrences=DiskLookup(workspace,visit(sequence._root,(None,0),True))
            if occurrences.count!=sequence._length:
                raise StoreIntegrityError('sequence scrub descriptor count disagreement')
            if sequence._directory is not None:directory(sequence._directory)
            if not wanted_members.equals_set(found_members):
                raise StoreIntegrityError('sequence scrub membership completeness disagreement')
            occurrences.validate();found_members.validate()
            for namespace,keys in expected.items():
                keys.validate()
                inventory(namespace,(codec.decode(key) for (key,) in workspace.db.execute(
                    'SELECT key FROM conversion_sets WHERE stream=?',(keys.stream,))))
    finally:
        # Reuse scratch pages across millions of small backing trees.
        for keys in (*expected.values(),wanted_members,found_members):
            workspace.db.execute('DELETE FROM conversion_sets WHERE stream=?',(keys.stream,))
        if occurrences is not None:
            workspace.db.execute('DELETE FROM conversion_lookup WHERE stream=?',(occurrences.stream,))
        workspace.db.commit()
