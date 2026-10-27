"""Integer-tail growth with authenticated new pages and empty physical owners."""
from .incremental_store import StoreIntegrityError,_framed_sha
from .persistence_proof_content import version_key
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_proof_publication as content
from . import persistence_proof_scope as scope
from . import persistence_proof_world as world
from . import persistence_lazy_identity_catalog as catalog
from .persistence_proof_world_backing_value import _parent
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as HISTORY,PAGE_NAMESPACE as PAGES
from .persistence_history_types import NAMESPACE as TYPES,TAG


def prepare(store,request,versions,facts):
    codec=store.codec;ca=request.pairs[0][0];sa=request.pairs[1][0]
    child_directory=sa.roots[4];eligible={};new_rows={};facts=list(facts)
    if len(versions)>512 or sum(len(i['payload'] or b'')+len(i['memberships_blob']) for i in versions)>4*1048576:return {},tuple(facts),{},child_directory
    by_key={(i['namespace'],i['typed_key']):i for i in versions}
    def clean(i):return i is not None and not i['change'].delete and not i['change'].reinsertion and i['change'].record_schema==1 and i['memberships_blob']==codec.encode(())
    for item in versions:
        if item['namespace']!=HISTORY or not clean(item) or len(item['payload'])>4096:continue
        inc=codec.decode(item['typed_key']);new=codec.decode(item['payload'])
        if type(inc) is not int or inc<=0 or type(new) is not tuple or len(new)!=3 or new[0]!='list' or any(type(n) is not int or n<=0 for n in new[1:]) or new[1]!=new[2]:continue
        if content._map(store).get(ca.versions,version_key(HISTORY,item['typed_key'])) is None:continue
        old=_parent(store,request,HISTORY,inc)
        if type(old) is not tuple or len(old)!=3 or old[0]!='list' or type(old[1]) is not int or old[1]<=0 or old[1]!=old[2]:continue
        old_pages=(old[1]+127)//128;new_pages=(new[1]+127)//128
        if new_pages<=old_pages or new_pages-old_pages>128:continue
        types=by_key.get((TYPES,codec.encode(inc)))
        if not clean(types) or len(types['payload'])>4096:continue
        if codec.encode(_parent(store,request,TYPES,inc))!=codec.encode((TAG,'list',(old[1],0,0))) or types['payload']!=codec.encode((TAG,'list',(new[1],0,0))):continue
        affected=[];added={};valid=True
        if old[1]%128:
            key=(inc,old_pages-1);page=by_key.get((PAGES,codec.encode(key)))
            if not clean(page):continue
            before=_parent(store,request,PAGES,key);after=codec.decode(page['payload'])
            if type(before) is not tuple or type(after) is not tuple or len(before)!=old[1]%128 or len(after)!=128 or any(type(v) is not int for v in (*before,*after)) or codec.encode(before)!=codec.encode(after[:len(before)]):continue
            affected.append(key)
        for number in range(old_pages,new_pages):
            key=(inc,number);typed=codec.encode(key);page=by_key.get((PAGES,typed))
            if not clean(page):valid=False;break
            values=codec.decode(page['payload'])
            if type(values) is not tuple or len(values)!=min(128,new[1]-128*number) or any(type(v) is not int for v in values):valid=False;break
            header_key=codec.encode((PAGES,key));header=by_key.get((catalog.OWNER_NAMESPACE,header_key))
            wanted=codec.encode(('identity-owner/v1',True,'lazy',request.pin.captured_head+1,1,_framed_sha(b'lazy-payload-v1',page['payload']),None,0,_framed_sha(b'identity-owner-empty-v1')))
            if not clean(header) or header['payload']!=wanted:valid=False;break
            if any(content._map(store).get(ca.versions,version_key(ns,k)) is not None for ns,k in ((PAGES,typed),(catalog.OWNER_NAMESPACE,header_key))):
                valid=False;break  # A retained tombstone needs the checked reuse path.
            added[(PAGES,typed)]=page['payload'];added[(catalog.OWNER_NAMESPACE,header_key)]=wanted;affected.append(key)
        if not valid:continue
        OrderedSeekMap(store.db,b'').create_schema()
        selected=scope.ChildScope(inc);domain=scope._seek_domain(store,selected);m=OrderedSeekMap(store.db,domain);root=scope._resolve(store,sa,selected)
        if root.count!=old_pages:raise StoreIntegrityError('tail parent physical inventory disagrees with descriptor')
        for number in range(old_pages,new_pages):
            _,position=scope._child_locator(PAGES,codec.encode((inc,number)))
            if m.get(root,position) is not None:raise StoreIntegrityError('new tail page lacks accepted child absence')
            root=m.set(root,position,scope._child_member(domain,position))
        child_directory=scope._map(store,4).set(child_directory,scope._scope_key(selected),scope._write_descriptor(store,selected,root))
        key=inc.to_bytes(8,'big');typed=codec.encode(inc)
        for index,label,wanted,replacement in (
            (0,b'backing-inventory',_digest(b'ate-world-backing/1',b'list',HISTORY.encode(),typed,codec.encode(old)),_digest(b'ate-world-backing/1',b'list',HISTORY.encode(),typed,item['payload'])),
            (4,b'backing-orders',_digest(b'ate-world-history-order/1',b'list',codec.encode(old)),_digest(b'ate-world-history-order/1',b'list',item['payload']))):
            mapping=world._map(store,label)
            if mapping.get(facts[index],key)!=wanted:raise StoreIntegrityError('tail predecessor lacks semantic backing authority')
            facts[index]=mapping.set(facts[index],key,replacement)
        eligible[inc]=tuple(affected);new_rows.update(added)
    return eligible,tuple(facts),new_rows,child_directory
