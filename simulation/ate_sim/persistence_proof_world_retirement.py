"""Finite retirement transitions checked against accepted source/scope roots.

The existing retirement producer chooses work. This validator permits only its
safe queue/physical transitions; it never infers authority from that choice.
"""
from collections import Counter

from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_history_retirement as producer
from . import persistence_history_dependencies as dependencies
from . import persistence_proof_scope as scope
from . import persistence_proof_world as world
from .persistence_proof_world_new_backings import Unsupported


class Retirements:
    def __init__(self, store, request, rows, predecessor):
        self.store, self.request, self.rows, self.predecessor = store, request, rows, predecessor
        self.codec = store.codec
        self.handled, self.deleted, self.finished, self.initial = set(), set(), {}, {}
        self.background_rows = set()
        self.jobs = {}
        for (ns, typed), item in rows.items():
            if ns != producer.NAMESPACE:
                continue
            inc = self.codec.decode(typed)
            if type(inc) is not int or not 0 < inc < request.pairs[1][0].next_incarnation_id:
                raise StoreIntegrityError('retirement job has unaccepted incarnation')
            old = self.old(ns, typed)
            value = None if item['change'].delete else self.codec.decode(item['payload'])
            self.jobs[inc] = old, value
            initial = producer.initial_retirement_change(value[1], inc,
                generation=request.pin.captured_head+1) if type(value) is tuple and len(value)==5 and type(value[1]) is str and value[1] in producer.SCOPES else None
            if initial is not None and self.codec.encode(value) == self.codec.encode(initial.value):
                self.initial[inc] = initial.value
                continue
            if old is None:
                raise StoreIntegrityError('retirement transition lacks its accepted job')
            self.background(inc, self.job(inc, self.codec.decode(old.payload)), value)
        if len(self.background_rows) > 96:
            raise Unsupported()

    def old(self, namespace, typed):
        ok, row = self.predecessor(namespace, typed)
        if not ok:
            raise Unsupported()
        if row is not None and row.record_schema != 1:
            raise StoreIntegrityError('retirement predecessor has wrong schema')
        return row

    def job(self, incarnation, value):
        if (type(value) is not tuple or len(value)!=5 or value[0] not in (producer.TAG,'history-retirement/v1')
                or type(value[1]) is not str or value[1] not in producer.SCOPES or type(value[2]) is not int
                or not 0 <= value[2] < len(producer._scopes(value))
                or type(value[3]) is not int or not 1 <= value[3] <= self.request.pin.captured_head
                or type(value[4]) is not bool):
            raise StoreIntegrityError('invalid accepted retirement job')
        row = self.jobs[incarnation][0]
        if row.memberships != self.codec.encode((('pending', True, row.valid_from),)):
            raise StoreIntegrityError('retirement job has wrong pending membership')
        selected = scope.QueryScope(producer.NAMESPACE, 'pending', self.codec.encode(True))
        root = scope._resolve(self.store, self.request.pairs[1][0], selected)
        mapping = OrderedSeekMap(self.store.db, scope._seek_domain(self.store, selected))
        wanted = scope.query_member(scope.query_domain(self.store.store_identity, self.codec.version, selected),
            self.codec.encode(incarnation), row.valid_from)
        if mapping.get(root, scope.query_order_key(row.valid_from, self.codec.encode(incarnation))) != wanted:
            raise StoreIntegrityError('retirement job lacks accepted pending scope')
        return value

    def expect(self, namespace, key, *, delete=False, value=None, memberships=(), background=True):
        marker = namespace, self.codec.encode(key)
        item = self.rows.get(marker)
        if (item is None or item['change'].record_schema != 1 or item['change'].reinsertion
                or item['change'].delete != delete
                or item['payload'] != (None if delete else self.codec.encode(value))
                or item['memberships_blob'] != self.codec.encode(memberships)):
            raise StoreIntegrityError('retirement differs from its exact authorized slice')
        self.handled.add(marker)
        if background:
            self.background_rows.add(marker)
        if delete:
            if self.old(*marker) is None:
                raise StoreIntegrityError('retirement deletes an absent predecessor')
            self.deleted.add(marker)

    def backing(self, inc, kind):
        ns = producer.SCOPES[kind][-1]
        key = (inc, 0) if kind in ('record', 'nan-key') else inc
        row = self.old(ns, self.codec.encode(key))
        if row is None:
            raise StoreIntegrityError('retirement lacks its backing descriptor')
        value = self.codec.decode(row.payload)
        world.target._validate_descriptor(kind, inc, value)
        expected = _digest(b'ate-world-backing/1', kind.encode(), ns.encode(), self.codec.encode(key),
            world._structural_descriptor(self.codec, kind, row.payload))
        if world._map(self.store,b'backing-inventory').get(self.request.facts[0],inc.to_bytes(8,'big')) != expected:
            raise StoreIntegrityError('retirement descriptor lacks accepted World backing')
        dep = self.old(dependencies.NAMESPACE, self.codec.encode(inc))
        if dep is None:
            raise StoreIntegrityError('retirement lacks mandatory dependency source')
        tokens = dependencies._validate_value(self.codec.decode(dep.payload))
        if tokens[1] != kind:
            raise StoreIntegrityError('retirement dependency kind differs')
        return ns, key, row, tokens[2], expected

    def child_page(self, inc, namespace, limit):
        if namespace not in scope._CHILD_NAMES:
            raise Unsupported()
        selected = scope.ChildScope(inc)
        domain = scope._seek_domain(self.store, selected)
        root = scope._resolve(self.store, self.request.pairs[1][0], selected)
        prefix = bytes([scope._CHILD_NAMES.index(namespace)])
        rows = OrderedSeekMap(self.store.db, domain).page(root, after=prefix, limit=limit)
        result = []
        for position, value in rows:
            if not position.startswith(prefix):
                break
            if value != scope._child_member(domain, position):
                raise StoreIntegrityError('retirement child locator value differs')
            child, checked = scope._child_locator(namespace, position[1:])
            if child != selected or checked != position:
                raise StoreIntegrityError('retirement child belongs to another backing')
            key = self.codec.decode(position[1:])
            if self.old(namespace, position[1:]) is None:
                raise StoreIntegrityError('accepted retirement child is physically absent')
            result.append(key)
        return tuple(result)

    def background(self, inc, job, new):
        g = self.request.pin.captured_head
        group = scope._resolve(self.store,self.request.pairs[1][0],scope.GroupScope(inc))
        if group.count:
            if job[4] or new is not None:
                raise StoreIntegrityError('placed retirement job cannot reclaim or rotate')
            self.expect(producer.NAMESPACE, inc, delete=True)
            return
        ns, key, descriptor, tokens, fact = self.backing(inc, job[1])
        if new == job:
            self.expect(producer.NAMESPACE,inc,value=job,memberships=(('pending',True,g+1),))
            return
        if (job[3] > self.store._validated_retention_floor(g)
                or dependencies._active_tokens(self.store,tokens)):
            raise StoreIntegrityError('retirement reclaims a retained backing')
        scopes, position = producer._scopes(job), job[2]
        if job[1] == 'sequence':
            raise Unsupported()
        if position == len(scopes)-1:
            child = scope.ChildScope(inc)
            root = scope._resolve(self.store,self.request.pairs[1][0],child)
            expected_count = 1 if job[1] in ('record','nan-key') else 0
            if root.count != expected_count:
                raise StoreIntegrityError('retirement final descriptor still has physical children')
            if expected_count and self.child_page(inc,ns,2) != (key,):
                raise StoreIntegrityError('retirement final record child differs')
            self.expect(ns,key,delete=True)
            self.expect(dependencies.NAMESPACE,inc,delete=True)
            self.expect(producer.NAMESPACE,inc,delete=True)
            self.finished[inc] = job[1], ns, key, descriptor, fact
            return
        chosen = scopes[position]
        if chosen == producer.MEMBER_TYPES:
            row = self.old(chosen,self.codec.encode(inc))
            keys = () if row is None else (inc,)
            advance = True
        else:
            proposed = [self.codec.decode(typed) for namespace,typed in self.rows
                if namespace==chosen and self.rows[namespace,typed]['change'].delete
                and type(self.codec.decode(typed)) is tuple and self.codec.decode(typed)[0]==inc]
            if len(proposed)>127:
                raise Unsupported()
            page = self.child_page(inc,chosen,len(proposed)+1)
            keys = tuple(sorted(proposed,key=self.codec.encode))
            if page[:len(keys)] != keys:
                raise StoreIntegrityError('retirement skips an accepted physical child')
            advance = len(page)==len(keys)
            if not advance and not keys:
                raise StoreIntegrityError('retirement makes no bounded progress')
        for chosen_key in keys:
            self.expect(chosen,chosen_key,delete=True)
        expected = (job[0],job[1],position+int(advance),job[3],job[4] or bool(keys))
        self.expect(producer.NAMESPACE,inc,value=expected,memberships=(('pending',True,g+1),))

    def finish(self, placements, previous):
        delta = Counter()
        for inc in previous.values():
            delta[inc] -= 1
        for change in placements:
            if not change.delete:
                delta[change.incarnation_id] += 1
        lost = set()
        for inc, change in delta.items():
            if inc >= self.request.pairs[1][0].next_incarnation_id:
                continue  # Fresh groups have no placed predecessor to retire.
            old = scope._resolve(self.store,self.request.pairs[1][0],scope.GroupScope(inc))
            if old.count and old.count+change==0 and world._map(self.store,b'backing-inventory').get(
                    self.request.facts[0],inc.to_bytes(8,'big')) is not None:
                lost.add(inc)
        if lost != set(self.initial):
            raise StoreIntegrityError('last-owner removal and retirement jobs disagree')
        for inc,value in self.initial.items():
            self.backing(inc,value[1])
            self.expect(producer.NAMESPACE,inc,value=value,
                memberships=(('pending',True,self.request.pin.captured_head+1),),background=False)

    def facts(self, facts, child_directory):
        facts = list(facts)
        children = {}
        for ns,typed in self.deleted:
            locator = scope._child_locator(ns,typed)
            if locator is None:
                continue
            selected,position = locator
            mapping = OrderedSeekMap(self.store.db,scope._seek_domain(self.store,selected))
            root = children.get(selected.incarnation_id)
            if root is None:
                root = scope._resolve(self.store,self.request.pairs[1][0],selected)
            if mapping.get(root,position) != scope._child_member(mapping.domain,position):
                raise StoreIntegrityError('retirement child deletion lacks accepted locator')
            children[selected.incarnation_id] = mapping.set(root,position,None)
        directory = scope._map(self.store,4)
        for inc,root in children.items():
            selected = scope.ChildScope(inc)
            child_directory = directory.set(child_directory,scope._scope_key(selected),
                scope._write_descriptor(self.store,selected,root) if root.count else None)
        for inc,(kind,ns,key,row,expected) in self.finished.items():
            position = inc.to_bytes(8,'big')
            mapping = world._map(self.store,b'backing-inventory')
            if mapping.get(facts[0],position) != expected:
                raise StoreIntegrityError('retired backing differs from accepted semantic fact')
            facts[0] = mapping.set(facts[0],position,None)
            if kind not in ('record','nan-key'):
                mapping = world._map(self.store,b'backing-orders')
                if mapping.get(facts[4],position) != _digest(b'ate-world-history-order/1',kind.encode(),row.payload):
                    raise StoreIntegrityError('retired backing order differs')
                facts[4] = mapping.set(facts[4],position,None)
        return tuple(facts),child_directory


def audit_jobs(store,pin):
    """Explicit full audit: validate the existing partial-retirement boundary."""
    from .persistence_lazy_identity_catalog import IdentityCatalog
    from . import persistence_proof_publication as content
    catalog = IdentityCatalog(store)
    for inc in store.iter_keys(pin,producer.NAMESPACE):
        job = producer._job(store,pin,inc)
        group = catalog.read_identity_group(pin,inc)
        try:
            if job[4] and group.occurrences:
                raise StoreIntegrityError('partly retired backing still has placements')
        finally:
            for values in (group.occurrences,group.links):
                if hasattr(values,'close'):
                    values.close()
        row = content._source_version(store,pin.captured_head,producer.NAMESPACE,store.codec.encode(inc))
        if row is None or row.memberships != store.codec.encode((('pending',True,row.valid_from),)):
            raise StoreIntegrityError('retirement job pending projection differs')
        dep = dependencies._checked_value(store,pin,inc)
        if dep[1] != job[1] or job[4] and dependencies._active_tokens(store,dep[2]):
            raise StoreIntegrityError('partly retired backing has a live dependency or wrong kind')
        scopes = producer._scopes(job)
        key = (inc,0) if job[1] in ('record','nan-key') else inc
        descriptor = store.read_version(pin,scopes[-1],key,expected_record_schema=1).value
        world.target._validate_descriptor(job[1],inc,descriptor)
        for namespace in scopes[:job[2]]:
            if producer._scope_keys(store,pin,namespace,inc,limit=1):
                raise StoreIntegrityError('retirement cursor passed surviving physical authority')
