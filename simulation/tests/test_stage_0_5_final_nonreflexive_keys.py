"""Native equality gates for checked recursive nonreflexive keys."""
import pytest

from ate_sim.core import Ref
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    RULES, activate, converted_catalog, open_bridge,
)


SHAPES = {
    'float': lambda value: value,
    'tuple': lambda value: ('key', value),
    'frozenset': lambda value: frozenset(('key', value)),
    'ref': lambda value: Ref('key', value),
}


def native_container(kind, keys):
    return dict(zip(keys, range(len(keys)))) if kind == 'map' else set(keys)


@pytest.mark.parametrize('kind', ['map', 'set'])
@pytest.mark.parametrize('shape', SHAPES)
def test_distinct_nan_probe_is_absent_after_save(tmp_path, kind, shape):
    key = SHAPES[shape](float('nan'))
    probe = SHAPES[shape](float('nan'))
    native = native_container(kind, [key])
    assert key in native and probe not in native
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [native]
        backed = session.skills[1, 'craft'].provenance[0]
        assert key in backed
        session.save()
        assert probe not in backed


@pytest.mark.parametrize('kind', ['map', 'set'])
@pytest.mark.parametrize('shape', ['float', 'tuple'])
def test_two_distinct_nan_keys_survive_save_and_reopen(tmp_path, kind, shape):
    keys = [SHAPES[shape](float('nan')) for _ in range(2)]
    native = native_container(kind, keys)
    assert len(native) == 2
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [native]
        backed = session.skills[1, 'craft'].provenance[0]
        assert len(backed) == 2
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        backed = session.skills[1, 'craft'].provenance[0]
        restored = list(backed)
        assert len(restored) == len(backed) == 2
        assert restored[0] != restored[1]
        assert all(key in backed for key in restored)
        if kind == 'map':
            assert [backed[key] for key in restored] == [0, 1]


@pytest.mark.parametrize('kind', ['map', 'set'])
def test_numeric_equality_representatives_remain_one_key(tmp_path, kind):
    native = native_container(kind, [True, 1, 1.0])
    assert len(native) == 1
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [native]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        backed = session.skills[1, 'craft'].provenance[0]
        assert len(backed) == 1
        assert all(key in backed for key in (True, 1, 1.0))
        if kind == 'map':
            assert all(backed[key] == 2 for key in (True, 1, 1.0))


@pytest.mark.parametrize('kind', ['map', 'set'])
@pytest.mark.parametrize('shape', SHAPES)
def test_held_nan_key_remains_usable_across_cache_clear(tmp_path, kind, shape):
    key = SHAPES[shape](float('nan'))
    native = native_container(kind, [key])
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [native]
        backed = session.skills[1, 'craft'].provenance[0]
        session.save()
        held = next(iter(backed))
        backed._clear_cache()
        assert held in backed
        if kind == 'map':
            assert backed[held] == 0
            backed[held] = 9
            session.save()
            backed._clear_cache()
            assert backed[held] == 9 and len(backed) == 1
        else:
            backed.remove(held)
            session.save()
            assert len(backed) == 0
