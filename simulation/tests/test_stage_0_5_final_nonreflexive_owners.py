"""Native immutable key components participate in checked physical ownership."""
import pytest

from ate_sim.core import Ref
from ate_sim.agency import ActionRecord
from ate_sim.incremental_store import Membership, StoreIntegrityError
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta, IdentityCatalog
from ate_sim.persistence_record_headers import record_header, NAMESPACE as RECORDS
from ate_sim.persistence_schema import RECORD_FIELDS
from ate_sim.persistence_nonreflexive_keys import (
    NonreflexiveKeyReference, canonical_stored_key, nonreflexive_key_header,
    NAMESPACE as ATOMS,
)
from simulation.tests.test_stage_0_5_final_record_headers import store_at, metadata


TOKEN = NonreflexiveKeyReference(2)
SHAPES = {
    'direct': (TOKEN, ()),
    'tuple': ((TOKEN,), (('index', 0),)),
    'ref': (Ref('key', TOKEN), (('field', 'id'),)),
    'frozenset': (frozenset((TOKEN,)), (('key', TOKEN),)),
    'deep': (Ref('key', (frozenset((Ref('inner', TOKEN),)),)),
             (('field', 'id'), ('index', 0), ('key', Ref('inner', TOKEN)), ('field', 'id'))),
}


def physical(kind, shape):
    member, relative = SHAPES[shape]
    if kind == 'page':
        namespace = 'aux.lazy.nested.list_pages'
        source = VersionChange(namespace, (1, 0), (member,))
        path = (('index', 0),) + relative
    elif kind == 'entry':
        namespace = 'aux.lazy.nested.entries'
        source = VersionChange(namespace, (1, canonical_stored_key(member)), (0, member, 9),
            memberships=(Membership('incarnation', 1, 0),))
        path = (('index', 1),) + relative
    elif kind == 'leaf':
        namespace = 'aux.lazy.sequence.nodes'
        source = VersionChange(namespace, (1, 1), ('leaf', ((8, member),)))
        path = (('key', 8),) + relative
    else:
        namespace = RECORDS
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        values = tuple(member if field == 'motive' else getattr(record, field)
                       for field in RECORD_FIELDS[type(record)])
        source = VersionChange(namespace, (1, 0), record_header(record, values=values))
        path = (('field', 'motive'),) + relative
    return AUXILIARY_OWNER_FAMILIES[namespace], source, path


@pytest.mark.parametrize('kind', ['page', 'entry', 'leaf', 'record'])
@pytest.mark.parametrize('shape', SHAPES)
def test_checked_key_component_paths_are_complete_and_resolve_native_reference(kind, shape):
    adapter, source, path = physical(kind, shape)
    codec = WorldCodec()
    adapter.validate_source(source, 'lazy', codec)
    assert adapter.reference_placements(source.value) == ((path, 2),)
    assert adapter.resolve_path(source.value, path) == TOKEN
    codec.encode(adapter.absolute_path(source.key, path))
    replacement = NonreflexiveKeyReference(3)
    updated = adapter.replace_path(source.value, path, replacement)
    assert adapter.resolve_path(updated, adapter.reference_placements(updated)[0][0]) == replacement
    assert adapter.resolve_path(source.value, path) == TOKEN


def test_entry_key_and_value_sharing_requires_both_checked_placements(tmp_path):
    adapter, source, key_path = physical('entry', 'ref')
    source = VersionChange(source.namespace, source.key, (0, source.value[1], TOKEN), memberships=source.memberships)
    value_path = (('index', 2),)
    assert adapter.reference_placements(source.value) == ((key_path, 2), (value_path, 2))
    placements = tuple(IdentityOccurrenceChange(source.namespace, source.key, path, 2)
                       for path in (key_path, value_path))
    atom = VersionChange(ATOMS, (2, 0), nonreflexive_key_header(float('nan')))
    with store_at(tmp_path / 'key-catalog.sqlite') as store:
        with pytest.raises(StoreIntegrityError, match='references disagree'):
            initial_catalog_delta(store.codec, (source, atom), placements[:1], next_incarnation_id=3, generation=1)
        delta = initial_catalog_delta(store.codec, (source, atom), placements, next_incarnation_id=3, generation=1)
        head = metadata(1)
        # Two placements create the existing current-sharing link authority.
        head['namespaces'] = ('world_identity_links',)
        pin = store.commit(store.capture_pin(), commit_token='key-components', changes=(),
            version_changes=(source, atom) + delta.decode(store.codec)[0], identity_changes=placements,
            next_incarnation_id=3, new_segments=(), required_format_version=5, metadata=head).pin
        group = IdentityCatalog(store).read_identity_group(pin, 2)
        assert set(group.occurrences) == {(source.namespace, source.key, path) for path in (key_path, value_path)}


@pytest.mark.parametrize('path', [
    (('index', 1), ('field', 'unknown')),
    (('index', 1), ('index', -1)),
    (('index', 1), ('key', object())),
    (('index', 0),),
    (('index', True),),
])
def test_key_component_paths_reject_undeclared_or_invalid_steps(path):
    adapter = AUXILIARY_OWNER_FAMILIES['aux.lazy.nested.entries']
    with pytest.raises(StoreIntegrityError):
        adapter.validate_path(path)


def test_missing_or_wrong_shape_key_paths_fail_with_integrity_errors():
    adapter, source, _ = physical('entry', 'ref')
    for path in ((('index', 1), ('index', 0)), (('index', 1), ('key', TOKEN)),
                 (('index', 1), ('field', 'kind'), ('index', 0))):
        with pytest.raises(StoreIntegrityError):
            adapter.resolve_path(source.value, path)
        with pytest.raises(StoreIntegrityError):
            adapter.replace_path(source.value, path, TOKEN)


def test_entry_address_must_match_canonical_projected_payload_key():
    adapter, source, _ = physical('entry', 'ref')
    wrong = VersionChange(source.namespace, (1, Ref('other', TOKEN)), source.value,
                          memberships=source.memberships)
    with pytest.raises(StoreIntegrityError):
        adapter.validate_source(wrong, 'lazy', WorldCodec())
