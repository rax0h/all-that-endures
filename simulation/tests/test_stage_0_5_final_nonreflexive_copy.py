"""Explicit checked copies and materializing detach preserve native key sharing."""
import hashlib
import pytest

from ate_sim.persistence_catalog_copy import _copy_current_checked_catalog
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference
from ate_sim.persistence_history_dependencies import dependency_value
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.incremental_store import StoreIntegrityError
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    activate, open_bridge,
)
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, RULES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_shared(root):
    keys = list(root[0])
    assert len(keys) == 2 and keys[0] != keys[1]
    assert root[0][keys[0]] is keys[0] is next(iter(root[1]))
    assert root[0][keys[1]] is keys[1]


def source_with_atoms(tmp_path, size=32):
    from ate_sim.persistence_catalog_copy import _copy_with_checked_catalog
    legacy = legacy_lazy(tmp_path, size=size)
    source = tmp_path / 'atoms.sqlite'
    _copy_with_checked_catalog(legacy, source, rules_id=RULES)
    a, b = float('nan'), float('nan')
    with open_bridge(source, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{a: a, b: b}, {a}]
        s.save()
    return source


def test_checked_current_copy_preserves_nan_sharing_and_source_bytes(tmp_path):
    source = source_with_atoms(tmp_path)
    before = sha(source)
    target = tmp_path / 'copied.sqlite'
    _copy_current_checked_catalog(source, target, rules_id=RULES)
    assert sha(source) == before
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        root = s.skills[1, 'craft'].provenance
        assert_shared(root)
        key = next(iter(root[0]))
        root[0][key] = 8
        s.save()
        assert root[0][key] == 8
    with open_bridge(source, rules_id=RULES) as s:
        activate(s)
        assert_shared(s.skills[1, 'craft'].provenance)


def test_materializing_detach_preserves_nan_key_value_aliases_after_close(tmp_path):
    source = source_with_atoms(tmp_path)
    with open_bridge(source, rules_id=RULES) as s:
        activate(s)
        world = s.detach(materialize_history=True)
    assert_shared(world.skills.skills[1, 'craft'].provenance)


@pytest.mark.parametrize('kind', [None, 'map', 'record'])
def test_copy_rejects_nan_reference_with_missing_or_wrong_backing_role(kind):
    from ate_sim.persistence_catalog_copy import _check_reference_targets
    dependencies = () if kind is None else (VersionChange('aux.lazy.history.dependencies', 1, dependency_value(kind)),)
    with pytest.raises(StoreIntegrityError, match='NaN.*backing'):
        _check_reference_targets((NonreflexiveKeyReference(1),), dependencies)
