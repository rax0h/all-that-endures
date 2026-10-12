"""Explicit legacy graph copy projects native NaNs into existing checked atoms."""
import math
import struct
import pytest
from ate_sim.core import Event, Layer, Ref
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, module, RULES, sha
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate

SHAPES = {
    'float': lambda n:n,
    'tuple': lambda n:('key', n),
    'frozenset': lambda n:frozenset(('key', n)),
    'ref': lambda n:Ref('key', n),
}

@pytest.mark.parametrize('shape', SHAPES)
@pytest.mark.parametrize('kind', ['map', 'set'])
def test_legacy_event_key_copy_retains_exact_nan_and_shared_container(tmp_path, shape, kind):
    nan = struct.unpack('>d', bytes.fromhex('fff8000000000042'))[0]
    key = SHAPES[shape](nan)
    values = {key:9} if kind == 'map' else {key}
    def configure(world):
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'a':values, 'b':values}))
        world.event_ids.add(1); world.next_event=2
    source = legacy_lazy(tmp_path, configure=configure)
    before = sha(source); target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source)==before
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        a=s.world.events[0].data['a'];assert a is s.world.events[0].data['b']
        held=next(iter(a));assert held in a and SHAPES[shape](float('nan')) not in a
        if shape=='float':atom=held
        elif shape=='tuple':atom=held[1]
        elif shape=='frozenset':atom=next(x for x in held if type(x) is float)
        else:atom=held.id
        assert math.isnan(atom) and struct.pack('>d',atom).hex()=='fff8000000000042'
        if kind=='map':a[held]=11
        else:a.remove(held)
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        a=s.world.events[0].data['a']
        assert len(a)==(1 if kind=='map' else 0)
        if kind=='map':assert a[next(iter(a))]==11


@pytest.mark.parametrize('kind', ['map', 'set'])
def test_legacy_equal_bit_distinct_nan_members_are_not_collapsed(tmp_path, kind):
    keys=[float('nan'),float('nan')]
    values=dict(zip(keys,(3,7))) if kind=='map' else set(keys)
    def configure(world):
        world.currency.wallets[1]={'values':values}
        world.currency.treasuries[2]=world.currency.wallets[1]
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        a=s.wallets[1]['values'];assert a is s.treasuries[2]['values']
        held=list(a);assert len(a)==len(held)==2 and held[0] is not held[1]
        assert all(key in a for key in held)
        if kind=='map':assert [a[key] for key in held]==[3,7]
        s.save()


def test_legacy_nan_scalar_in_shared_native_action_preserves_public_float_type(tmp_path):
    from ate_sim.agency import ActionRecord
    action=ActionRecord(1,2,'work','wealth',float('nan'))
    def configure(world):
        world.agency.actions.append(action)
        world.events.append(Event(1,0,'legacy',Layer.SOCIETY,data={'action':action}))
        world.event_ids.add(1);world.next_event=2
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        action=s.world.agency.actions[0]
        assert s.world.events[0].data['action'] is action
        assert type(action.strength) is float and math.isnan(action.strength)
        action.strength=.8;s.save()
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        assert s.world.agency.actions[0].strength==.8


@pytest.mark.parametrize('sealed', [False, True])
def test_legacy_nan_values_and_frozen_keys_reopen_copy_and_detach(tmp_path, sealed):
    nan=float('nan');values={('key',nan):[nan]}
    def configure(world):
        event=Event(1,0,'legacy',Layer.SOCIETY,data={'values':values})
        if sealed:event.seal()
        world.events.append(event);world.event_ids.add(1);world.next_event=2
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    replica=tmp_path/'replica.sqlite'
    module()._copy_current_checked_catalog(target,replica,rules_id=RULES)
    with open_bridge(replica,rules_id=RULES) as s:
        activate(s)
        values=s.world.events[0].data['values'];key=next(iter(values))
        assert key in values and math.isnan(values[key][0])
        world=s.detach(materialize_history=True)
    values=world.events[0].data['values'];key=next(iter(values))
    assert key in values and math.isnan(values[key][0])


def test_legacy_equal_bit_nan_values_have_distinct_position_atoms(tmp_path):
    values={float('nan'):float('nan'),float('nan'):float('nan')}
    def configure(world):world.currency.wallets[1]={'values':values}
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        values=s.wallets[1]['values'];pairs=list(values.items())
        assert len(pairs)==2 and pairs[0][1] is not pairs[1][1]
        assert all(key is not value for key,value in pairs)
        held=pairs[0][1];values._clear_cache()
        assert values[pairs[0][0]] is held
        s.save()


def test_legacy_alias_nan_bit_disagreement_rejects_without_destination(tmp_path):
    from simulation.tests.test_stage_0_5_final_catalog_copy import opened
    from ate_sim.incremental_store import RecordChange, StoreIntegrityError
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    nan=float('nan')
    def configure(world):
        shared={'values':{nan:9}};world.currency.wallets[1]=shared;world.currency.treasuries[2]=shared
    source=legacy_lazy(tmp_path,configure=configure)
    with opened(source) as store:
        pin=store.capture_pin();value=store.read_version(pin,'world.currency.treasuries',2,expected_record_schema=1).value
        value['values']={struct.unpack('>d',bytes.fromhex('7ff8000000000042'))[0]:9}
        token='9'*32
        result=store.commit(pin,commit_token=token,changes=(
            RecordChange(EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY,(1,pin.captured_head+1,token)),),
            version_changes=(VersionChange('world.currency.treasuries',2,value),),new_segments=(),metadata=store.head_metadata())
        store.release_pin(result.pin)
    before=sha(source);target=tmp_path/'rejected.sqlite'
    with pytest.raises(StoreIntegrityError,match='disagree'):
        module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    assert sha(source)==before and not target.exists()


@pytest.mark.parametrize('kind', ['map', 'set', 'list'])
def test_older_page_backing_raw_nan_slots_upgrade_to_usable_atoms(tmp_path, kind):
    from ate_sim.metaphysics import SoulState
    nan=float('nan')
    def configure(world):
        soul=SoulState(1);world.metaphysics.souls[1]=soul
        if kind=='set':soul.marks={nan};values=soul.marks
        elif kind=='map':soul.cosmic_links={nan:nan};values=soul.cosmic_links
        else:
            world.skills.skills[1,'craft'].provenance=[nan];values=world.skills.skills[1,'craft'].provenance
        world.currency.wallets[1]={'values':values}
    source=legacy_lazy(tmp_path,configure=configure);before=sha(source);target=tmp_path/'normalized.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    assert sha(source)==before
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        values=s.wallets[1]['values']
        other=s.skills[1,'craft'].provenance if kind=='list' else getattr(s.souls[1], 'marks' if kind=='set' else 'cosmic_links')
        assert values is other
        held=values[0] if kind=='list' else next(iter(values))
        values._clear_cache()
        if kind=='list':assert values[0] is held
        else:assert held in values
        s.save()


def test_legacy_atom_normalization_composes_with_counted_copy_promotion(tmp_path):
    from simulation.tests.test_stage_0_5_final_catalog_copy import opened
    def configure(world):world.skills.skills[1,'craft'].provenance=[float('nan')]
    source=legacy_lazy(tmp_path,configure=configure)
    with opened(source) as store:
        pin=store.capture_pin()
        inc=store.read_version(pin,'world.skills.skills',(1,'craft'),expected_record_schema=1).value.provenance.incarnation
        store.release_pin(pin)
    target=tmp_path/'promoted.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True,promote_lists=(inc,))
    with open_bridge(target,rules_id=RULES) as s:
        activate(s)
        values=s.skills[1,'craft'].provenance;held=values[0]
        values._clear_cache()
        assert values[0] is held
        s.save()
