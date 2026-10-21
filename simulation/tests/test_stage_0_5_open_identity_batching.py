"""Open may share stable certificates, but must authenticate every action."""
from collections import Counter
from math import ceil
import sqlite3

import pytest

from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, OWNER_NAMESPACE, OWNER_TREE_NAMESPACE
from ate_sim.incremental_store import StoreIntegrityError
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture, RULES


@pytest.mark.parametrize('size', [16, 320])
def test_open_batch_reuses_owner_proofs_but_checks_every_group(tmp_path, monkeypatch, size):
    path = fixture(tmp_path, size, shared=True)
    reads, owners, groups = Counter(), Counter(), []
    original_read, original_group = IdentityCatalog._read, IdentityCatalog.read_identity_group
    def read(self, pin, namespace, key):
        reads[namespace] += 1
        if namespace == OWNER_NAMESPACE: owners[key[0]] += 1
        return original_read(self, pin, namespace, key)
    def group(self, pin, incarnation):
        groups.append(incarnation)
        return original_group(self, pin, incarnation)
    monkeypatch.setattr(IdentityCatalog, '_read', read)
    monkeypatch.setattr(IdentityCatalog, 'read_identity_group', group)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert len(groups) >= size
        assert owners['world.agency.actions'] <= 2*ceil((size+1)/64)+2, dict(owners)
        action = session.world.agency.actions[0]
        assert action is session.world.agency.actions[-1]
        assert action is session.wallets[1]['action']
        assert action is session.world.events[0].data['action']
        assert getattr(session.store, '_validation_scope', None) is None


def test_disjoint_owners_are_each_checked_with_small_proof_budget(tmp_path):
    from simulation.tests.test_persistence_lazy_store import make_store
    from simulation.tests.test_stage_0_5_final_identity_catalog import groups, catalog
    from simulation.ate_sim.persistence_validation_scope import checked_read_operation
    with make_store(tmp_path/'disjoint.sqlite') as store:
        pin = groups(store, 16)
        cat = catalog().IdentityCatalog(store, occurrence_limit=2, byte_limit=4096)
        counts = Counter()
        original = cat._read
        def read(pin, namespace, key):
            counts[namespace] += 1
            return original(pin, namespace, key)
        cat._read = read
        with checked_read_operation(store, pin, byte_limit=512) as scope:
            for inc in range(1,17):
                result = cat.read_identity_group(pin, inc)
                assert len(result.occurrences) == 2 and len(result.links) == 1
            assert scope.bytes <= 512
            assert counts[catalog().OWNER_NAMESPACE] == 32


@pytest.mark.parametrize('authority', ['owner', 'node', 'group', 'occurrence', 'link'])
def test_corrupt_open_authority_is_not_hidden_by_batching(tmp_path, authority):
    from ate_sim.persistence_lazy_identity_catalog import GROUP_NAMESPACE, LINK_NAMESPACE
    path = fixture(tmp_path, 16, shared=True)
    with sqlite3.connect(path) as db:
        if authority == 'occurrence':
            db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=?', ('world.agency.actions',))
        else:
            namespace = {'owner': OWNER_NAMESPACE, 'node': OWNER_TREE_NAMESPACE,
                         'group': GROUP_NAMESPACE, 'link': LINK_NAMESPACE}[authority]
            db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (namespace,))
    with pytest.raises(StoreIntegrityError):
        with open_lazy_world_session(path, rules_id=RULES): pass
