"""Rebuildable secondary indexes over authoritative identity-bearing records.

Queries touch changed records, not historical rows. Indexes and notification
links are disposable; checkpoints contain only the authoritative dictionary.
"""
import weakref


class IndexedRecord:
    def __setattr__(self, name, value):
        table = None
        if not name.startswith('_index_'):
            ref = self.__dict__.get('_index_table')
            table = None if ref is None else ref()
            if table is not None:
                preflight = getattr(table, "preflight_change", None)
                if preflight is not None:
                    preflight(self._index_key, name)
                shared_preflight = getattr(table, "preflight_shared_record", None)
                if shared_preflight is not None:
                    shared_preflight(self)
        object.__setattr__(self, name, value)
        if table is not None:
            table.changed(self._index_key, name)
            shared_changed = getattr(table, "shared_record_changed", None)
            if shared_changed is not None:
                shared_changed(self)

    def __getstate__(self):
        return {k:v for k,v in self.__dict__.items() if not k.startswith('_index_')}


class RecordTable(dict):
    def __init__(self, records=()):
        super().__init__()
        self.update(records)

    def __getstate__(self): return {}

    def __setitem__(self, key, record):
        super().__setitem__(key, record)
        # dataclasses.asdict reconstructs dict subclasses with plain dict rows.
        # Keep that serialization protocol; only live records support queries.
        if isinstance(record, IndexedRecord):
            record._index_table = weakref.ref(self)
            record._index_key = key
        self.changed(key)

    def changed(self, key, field=None):
        for fields,_,_,dirty in getattr(self, '_indexes', {}).values():
            if field is None or field in fields:dirty.add(key)

    def __delitem__(self, key):
        super().__delitem__(key)
        self.changed(key)

    def update(self, records=(), **kwargs):
        for key,record in dict(records, **kwargs).items(): self[key]=record

    def clear(self):
        super().clear()
        self.__dict__.pop('_indexes',None)

    def pop(self, key, *default):
        if key not in self:
            if default:return default[0]
            raise KeyError(key)
        record=self[key];del self[key];return record

    def popitem(self):
        if not self:raise KeyError('popitem(): dictionary is empty')
        key=next(reversed(self));return key,self.pop(key)

    def setdefault(self,key,default=None):
        if key not in self:self[key]=default
        return self[key]

    def __ior__(self,other): self.update(other);return self

    def buckets(self, fields):
        """Exact field-value buckets. Mutations repair only affected memberships."""
        fields=(fields,) if isinstance(fields,str) else tuple(fields)
        if not hasattr(self,'_indexes'):self._indexes={}
        if fields not in self._indexes:
            self._indexes[fields]=(fields,{}, {}, set(self))
        fields,buckets,previous,dirty=self._indexes[fields]
        for key in dirty:
            if key in previous:
                old=previous.pop(key);bucket=buckets[old];bucket.discard(key)
                if not bucket:del buckets[old]
            if key in self:
                record=self[key]
                value=tuple(getattr(record,field) for field in fields)
                buckets.setdefault(value,set()).add(key);previous[key]=value
        dirty.clear()
        return buckets

    def ids(self, fields, *values):
        return self.buckets(fields).get(tuple(values),())

    def select(self, fields, *values):
        # Historical dictionaries use increasing stable IDs. Status changes
        # cannot change tie ordering when a row leaves/re-enters an active set.
        return [self[key] for key in sorted(self.ids(fields,*values))]


def indexed(owner, name):
    """Load old checkpoints/direct fixtures once; never duplicate their facts."""
    table=getattr(owner,name)
    if not isinstance(table,RecordTable):
        table=RecordTable(table);setattr(owner,name,table)
    return table
