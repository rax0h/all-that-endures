"""Full source admission must check each immutable proof node once."""
import hashlib
import sqlite3
from types import SimpleNamespace

import pytest
from ate_sim.incremental_store import StoreIntegrityError, StoreError
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_nodes import Root, Branch
from ate_sim import persistence_proof_world as world
from ate_sim import persistence_proof_publication as content
from ate_sim.persistence_proof_store import ProofNodeStore
from simulation.tests.proof_world_fixtures import make_world


def test_full_world_source_audit_does_not_reread_shared_proof_paths(tmp_path, monkeypatch):
    def configure(w):
        w.genealogy.parents.update((i, (i - 1,)) for i in range(1, 513))

    store, pin, authorities, records, directory = make_world(tmp_path / 'world', configure=configure)
    try:
        proof = content._map(store)
        reachable = set()
        original = ProofNodeStore._read_bound_bytes

        def track(nodes, domain, digest):
            if domain == proof.map_domain:
                reachable.add(digest)
            return original(nodes, domain, digest)

        with monkeypatch.context() as patch:
            patch.setattr(ProofNodeStore, '_read_bound_bytes', track)
            list(proof.iter_leaves(authorities[0][0].versions))
        reads = []

        def count(nodes, domain, digest):
            if domain == proof.map_domain:
                reads.append(digest)
            return original(nodes, domain, digest)

        monkeypatch.setattr(ProofNodeStore, '_read_bound_bytes', count)
        result = world.audit_world_roots(store, pin, *authorities, records, directory)
        assert result.roots[0] == authorities[0][0].versions
        assert set(reads) == reachable
        assert len(reads) == len(reachable), (len(reads), len(reachable))
    finally:
        store.release_pin(pin)
        store.close()


def source_map(tmp_path):
    db=sqlite3.connect(tmp_path/'nodes.sqlite')
    nodes=ProofNodeStore(db);nodes.create_schema();db.execute('BEGIN')
    domain=b'world-source-audit-test'
    proof=ProofMap(domain,lambda h:nodes._read_bound_bytes(domain,h),lambda h,b:nodes.write(domain,h,b))
    values=[(str(i).encode(),hashlib.sha256(str(i).encode()).digest()) for i in range(80)]
    root=proof.empty
    for key,value in values:root=proof.set(root,key,value)
    return SimpleNamespace(db=db),proof,root,values


@pytest.mark.parametrize('damage',['missing','extra','changed','replacement','duplicate','missing-node','corrupt-node','wrong-count','wrong-domain','child-path'])
def test_full_source_merge_rejects_incomplete_or_corrupt_authority(tmp_path,damage):
    store,proof,root,values=source_map(tmp_path)
    try:
        if damage=='missing':values.pop()
        elif damage=='extra':values.append((b'extra',b'x'*32))
        elif damage=='changed':values[0]=(values[0][0],b'x'*32)
        elif damage=='replacement':values[0]=(b'extra',b'x'*32)
        elif damage=='duplicate':values[-1]=values[0]
        elif damage=='missing-node':
            leaf=store.db.execute("SELECT digest FROM ate_proof_nodes WHERE substr(node_bytes,1,6)=x'41544550014c' LIMIT 1").fetchone()[0]
            store.db.execute('DELETE FROM ate_proof_nodes WHERE digest=?',(leaf,))
        elif damage=='corrupt-node':store.db.execute('UPDATE ate_proof_nodes SET node_bytes=? WHERE digest=?',(b'invalid',root.digest))
        elif damage=='wrong-count':root=Root(root.digest,root.count+1)
        elif damage=='wrong-domain':proof.map_domain=b'foreign'
        elif damage=='child-path':
            node=proof._read(root);children=list(node.children)
            children[0],children[1]=(children[0][0],children[1][1]),(children[1][0],children[0][1])
            root=proof._write(Branch(node.prefix,tuple(children)))
        with pytest.raises(StoreIntegrityError):
            world._check_source_map(store,proof,root,iter(values),'source mismatch')
        assert store.db.execute("SELECT name FROM sqlite_temp_schema WHERE name='ate_world_source_content'").fetchall()==[]
    finally:store.db.rollback();store.db.close()


def test_source_merge_cannot_start_an_unowned_transaction(tmp_path):
    store,proof,root,values=source_map(tmp_path)
    store.db.commit()
    try:
        with pytest.raises(StoreError):
            world._check_source_map(store,proof,root,iter(values),'source mismatch')
        assert not store.db.in_transaction
    finally:store.db.close()


def test_repeat_source_audit_rereads_previously_checked_leaf(tmp_path):
    store,proof,root,values=source_map(tmp_path)
    try:
        assert world._check_source_map(store,proof,root,iter(values),'source mismatch')==80
        leaf=store.db.execute("SELECT digest FROM ate_proof_nodes WHERE substr(node_bytes,1,6)=x'41544550014c' LIMIT 1").fetchone()[0]
        store.db.execute('DELETE FROM ate_proof_nodes WHERE digest=?',(leaf,))
        with pytest.raises(StoreIntegrityError):
            world._check_source_map(store,proof,root,iter(values),'source mismatch')
    finally:store.db.rollback();store.db.close()


def test_empty_source_merge_requires_canonical_empty_root(tmp_path):
    store,proof,root,values=source_map(tmp_path)
    try:
        assert world._check_source_map(store,proof,proof.empty,iter(()),'empty mismatch')==0
        with pytest.raises(StoreIntegrityError):
            world._check_source_map(store,proof,Root(b'x'*32,0),iter(()),'empty mismatch')
    finally:store.db.rollback();store.db.close()


def test_source_failure_cleans_spool_and_does_not_authorize_next_call(tmp_path):
    store,proof,root,values=source_map(tmp_path)
    def fail():
        yield values[0]
        raise RuntimeError('source read failed')
    try:
        with pytest.raises(RuntimeError,match='source read failed'):
            world._check_source_map(store,proof,root,fail(),'source mismatch')
        assert world._check_source_map(store,proof,root,iter(values),'source mismatch')==80
    finally:store.db.rollback();store.db.close()


@pytest.mark.parametrize('source_fails',[False,True])
def test_source_audit_cleanup_preserves_primary_failure(tmp_path,source_fails):
    store,proof,root,values=source_map(tmp_path)
    def authorize(action,first,*args):
        return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_DROP_TEMP_TABLE and first=='ate_world_source_content' else sqlite3.SQLITE_OK
    def source():
        yield values[0]
        raise ValueError('primary source validator failure')
    store.db.set_authorizer(authorize)
    try:
        if source_fails:
            with pytest.raises(ValueError,match='primary source validator failure') as error:
                world._check_source_map(store,proof,root,source(),'source mismatch')
            assert any('cleanup failed' in note and 'not authorized' in note for note in error.value.__notes__)
        else:
            with pytest.raises(sqlite3.DatabaseError,match='not authorized'):
                world._check_source_map(store,proof,root,iter(values),'source mismatch')
    finally:store.db.set_authorizer(None);store.db.rollback();store.db.close()
