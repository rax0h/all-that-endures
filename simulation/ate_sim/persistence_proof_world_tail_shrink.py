"""Bounded integer-page removal under accepted content and child authority."""
from .incremental_store import StoreIntegrityError,_framed_sha
from .persistence_proof_nodes import _digest
from .persistence_proof_content import version_key
from . import persistence_proof_publication as content
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_world_backing_value import _parent
from . import persistence_proof_scope as scope,persistence_proof_world as world
from . import persistence_lazy_identity_catalog as catalog
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as HISTORY,PAGE_NAMESPACE as PAGES
from .persistence_history_types import NAMESPACE as TYPES,TAG


def prepare(store,request,versions,facts):
    codec=store.codec;sa=request.pairs[1][0];facts=list(facts);eligible={};removed={};headers={};directory=request.tail_child_root
    inspected=sum(len(i['payload'] or b'')+len(i['memberships_blob']) for i in versions)
    if len(versions)>512 or inspected>4*1048576:return {},tuple(facts),{}, {},directory
    def read(namespace,key):
        nonlocal inspected
        sizes=store._interval_rows('lazy_record_versions','length(payload)+length(memberships)',('namespace','typed_key'),(namespace,codec.encode(key)),request.pin.captured_head,'lazy_record_interval',limit=2)
        if len(sizes)==1 and type(sizes[0][0]) is int:
            if inspected+sizes[0][0]>4*1048576:return None
            inspected+=sizes[0][0]
        return _parent(store,request,namespace,key)
    by_key={(i['namespace'],i['typed_key']):i for i in versions}
    def clean(i,delete=False):return i is not None and i['change'].delete is delete and not i['change'].reinsertion and i['change'].record_schema==1 and i['memberships_blob']==codec.encode(())
    for item in versions:
        if item['namespace']!=HISTORY or not clean(item) or len(item['payload'])>4096:continue
        inc=codec.decode(item['typed_key']);new=codec.decode(item['payload'])
        if type(inc) is not int or inc<=0 or type(new) is not tuple or len(new)!=3 or new[0]!='list' or any(type(n) is not int or n<0 for n in new[1:]) or new[1]!=new[2]:continue
        if content._map(store).get(request.pairs[0][0].versions,version_key(HISTORY,item['typed_key'])) is None:continue
        old=read(HISTORY,inc)
        if type(old) is not tuple or len(old)!=3 or old[0]!='list' or any(type(n) is not int or n<0 for n in old[1:]) or old[1]!=old[2] or new[1]>=old[1]:continue
        old_pages=(old[1]+127)//128;new_pages=(new[1]+127)//128
        if old_pages<=new_pages or old_pages-new_pages>128:continue
        types=by_key.get((TYPES,codec.encode(inc)))
        if not clean(types) or len(types['payload'])>4096:continue
        if codec.encode(read(TYPES,inc))!=codec.encode((TAG,'list',(old[1],0,0))) or types['payload']!=codec.encode((TAG,'list',(new[1],0,0))):continue
        affected=[];deleted={};approved={};valid=True
        if new[1]%128:
            key=(inc,new_pages-1);page=by_key.get((PAGES,codec.encode(key)))
            if not clean(page):continue
            before=read(PAGES,key);after=codec.decode(page['payload'])
            if type(before) is not tuple or type(after) is not tuple or len(before)!=128 or len(after)!=new[1]%128 or any(type(v) is not int for v in (*before,*after)) or codec.encode(after)!=codec.encode(before[:len(after)]):continue
            affected.append(key)
        for number in range(new_pages,old_pages):
            key=(inc,number);typed=codec.encode(key);page=by_key.get((PAGES,typed))
            if not clean(page,True):valid=False;break
            before=read(PAGES,key)
            if type(before) is not tuple or len(before)!=min(128,old[1]-128*number) or any(type(v) is not int for v in before):valid=False;break
            header_key=codec.encode((PAGES,key));header=by_key.get((catalog.OWNER_NAMESPACE,header_key));prior=read(catalog.OWNER_NAMESPACE,(PAGES,key))
            if (type(prior) is not tuple or len(prior)!=9 or prior[:3]!=('identity-owner/v1',True,'lazy') or prior[4]!=1
                    or prior[5]!=_framed_sha(b'lazy-payload-v1',codec.encode(before)) or prior[6:]!=(None,0,_framed_sha(b'identity-owner-empty-v1'))):valid=False;break
            wanted=list(prior);wanted[1]=False;wanted[3]=request.pin.captured_head+1;wanted=codec.encode(tuple(wanted))
            if not clean(header) or header['payload']!=wanted:valid=False;break
            deleted[(PAGES,typed)]=codec.encode(before);approved[(catalog.OWNER_NAMESPACE,header_key)]=wanted
        if not valid:continue
        OrderedSeekMap(store.db,b'').create_schema();selected=scope.ChildScope(inc);domain=scope._seek_domain(store,selected);m=OrderedSeekMap(store.db,domain);root=scope._resolve(store,sa,selected)
        if root.count!=old_pages:raise StoreIntegrityError('shrink parent child inventory disagrees with descriptor')
        for number in range(new_pages,old_pages):
            _,position=scope._child_locator(PAGES,codec.encode((inc,number)))
            if m.get(root,position)!=scope._child_member(domain,position):raise StoreIntegrityError('removed page lacks accepted child membership')
            root=m.set(root,position,None)
        directory=scope._map(store,4).set(directory,scope._scope_key(selected),scope._write_descriptor(store,selected,root) if root.count else None)
        key=inc.to_bytes(8,'big');typed=codec.encode(inc)
        for index,label,wanted,replacement in (
            (0,b'backing-inventory',_digest(b'ate-world-backing/1',b'list',HISTORY.encode(),typed,codec.encode(old)),_digest(b'ate-world-backing/1',b'list',HISTORY.encode(),typed,item['payload'])),
            (4,b'backing-orders',_digest(b'ate-world-history-order/1',b'list',codec.encode(old)),_digest(b'ate-world-history-order/1',b'list',item['payload']))):
            mapping=world._map(store,label)
            if mapping.get(facts[index],key)!=wanted:raise StoreIntegrityError('shrink predecessor lacks accepted semantic fact')
            facts[index]=mapping.set(facts[index],key,replacement)
        eligible[inc]=tuple(affected);removed.update(deleted);headers.update(approved)
    return eligible,tuple(facts),removed,headers,directory
