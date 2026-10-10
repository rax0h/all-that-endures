"""Concrete graph-child policies; table integration uses the existing publisher."""
from types import MappingProxyType

BUCKET_KIND = 'dict-history/v1'
BUCKET_SPECS = MappingProxyType({
    'world.genealogy.children': ('list', 'genealogy_children', 'genealogy_child_touched_keys'),
    'world.lineage.children': ('set', 'lineage_children', 'lineage_child_touched_keys'),
    'world.social.adjacency': ('set', 'social_adjacency', 'social_adjacency_touched_keys'),
    'world.magic_resources.owner_index': ('set', 'owner_index', 'owner_index_touched_keys'),
    'world.materials.lot_index': ('list', 'material_lot_index', 'material_lot_index_touched_keys'),
    'world.materials.active_lot_index': ('set', 'material_active_index', 'material_active_index_touched_keys'),
})


def valid_member(namespace, value):
    if namespace == 'world.lineage.children':
        return type(value) is tuple and len(value) == 2 and type(value[0]) is str and type(value[1]) is int
    return type(value) is int


def valid_key(namespace, key):
    if namespace == 'world.lineage.children':
        return type(key) is tuple and len(key) == 2 and type(key[0]) is str and type(key[1]) is int
    if namespace == 'world.genealogy.children':
        return type(key) is int
    from .persistence_lazy_nested_history import immutable_value
    try:
        hash(key)
    except TypeError:
        return False
    return immutable_value(key)
