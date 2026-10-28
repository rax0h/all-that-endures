"""Authenticated integer-list tail resizing within unchanged physical pages."""
from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import _digest
from .persistence_proof_content import version_key
from . import persistence_proof_publication as content
from . import persistence_proof_world as world
from .persistence_proof_world_backing_value import _parent
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as HISTORY,PAGE_NAMESPACE as PAGES
from .persistence_history_types import NAMESPACE as TYPES,TAG


def _same_page(store,request,versions):
    codec=store.codec;eligible={};facts=list(request.facts)
    if len(versions)>512:return {},None
    by_key={(i['namespace'],i['typed_key']):i for i in versions}
    for item in versions:
        if item['namespace']!=HISTORY or item['change'].delete or len(item['payload'])>4096:continue
        inc=codec.decode(item['typed_key']);new=codec.decode(item['payload'])
        if type(inc) is not int or inc<=0 or type(new) is not tuple or len(new)!=3 or new[0]!='list':continue
        if content._map(store).get(request.pairs[0][0].versions,version_key(HISTORY,item['typed_key'])) is None:continue
        old=_parent(store,request,HISTORY,inc)
        if (type(old) is not tuple or len(old)!=3 or old[0]!='list' or old[1]==new[1]
                or any(type(n) is not int or n<=0 for n in (old[1],old[2],new[1],new[2]))
                or old[1]!=old[2] or new[1]!=new[2] or (old[1]-1)//128!=(new[1]-1)//128):continue
        page_key=(inc,(old[1]-1)//128);page=by_key.get((PAGES,codec.encode(page_key)));types=by_key.get((TYPES,codec.encode(inc)))
        if page is None or types is None or any(x['change'].delete or x['change'].reinsertion or x['change'].record_schema!=1 or x['memberships_blob']!=codec.encode(()) for x in (item,page,types)):continue
        if len(page['payload'])>4*1048576 or len(types['payload'])>4096:continue
        before=_parent(store,request,PAGES,page_key);after=codec.decode(page['payload'])
        prior=_parent(store,request,TYPES,inc);next_types=codec.decode(types['payload'])
        if (type(before) is not tuple or type(after) is not tuple or len(before)!=old[1]-128*page_key[1]
                or len(after)!=new[1]-128*page_key[1] or any(type(v) is not int for v in (*before,*after))
                or codec.encode(before[:min(len(before),len(after))])!=codec.encode(after[:min(len(before),len(after))])):continue
        if codec.encode(prior)!=codec.encode((TAG,'list',(old[1],0,0))) or codec.encode(next_types)!=codec.encode((TAG,'list',(new[1],0,0))):continue
        # Authenticate the old semantic leaf before changing exactly that leaf.
        key=inc.to_bytes(8,'big');typed=codec.encode(inc)
        for index,label,wanted,replacement in (
            (0,b'backing-inventory',_digest(b'ate-world-backing/1',b'list',HISTORY.encode(),typed,codec.encode(old)),_digest(b'ate-world-backing/1',b'list',HISTORY.encode(),typed,item['payload'])),
            (4,b'backing-orders',_digest(b'ate-world-history-order/1',b'list',codec.encode(old)),_digest(b'ate-world-history-order/1',b'list',item['payload']))):
            mapping=world._map(store,label)
            if mapping.get(facts[index],key)!=wanted:raise StoreIntegrityError('tail predecessor lacks accepted semantic backing fact')
            facts[index]=mapping.set(facts[index],key,replacement)
        eligible[inc]=(page_key,)
    return eligible,tuple(facts) if eligible else None


def metadata_allowed(request,namespace,key):
    return namespace in (HISTORY,TYPES) and type(key) is int and key in (request.tail or {})


def page_allowed(request,key):
    return key in (request.tail or {}).get(key[0],())


def prepare(store,request,versions):
    from .persistence_proof_world_tail_pages import prepare as pages
    eligible,facts=_same_page(store,request,versions)
    extra,next_facts,request.tail_new,request.tail_child_root=pages(store,request,versions,facts or request.facts)
    eligible.update(extra)
    from .persistence_proof_world_tail_shrink import prepare as shrink
    smaller,next_facts,request.tail_removed,headers,request.tail_child_root=shrink(store,request,versions,next_facts)
    request.tail_new.update(headers);eligible.update(smaller)
    return eligible,next_facts if eligible else None
