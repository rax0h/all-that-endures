"""A separate rank projection shares the existing atomic scope publisher."""
import pytest

from ate_sim.incremental_store import Membership,StoreError,TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange
from ate_sim.persistence_lazy_minimum import numeric_rank
from ate_sim import persistence_proof_scope as scopes
from ate_sim.persistence_proof_seek import OrderedSeekMap

NAME='minimum/v1/test'


def metadata(position=1):
    return dict(simulation_position=position,seed=7,next_ids={},namespaces=('people',))


def change(key,rank,ordinal):
    return VersionChange('people',key,{'id':rank},memberships=(Membership(NAME,numeric_rank(rank),ordinal),))


def ranked_store(tmp_path,*,ranked=True):
    store=LazyRecordStore.create(tmp_path/'rank.sqlite',codec=TypedCodec(),simulation_schema='8',rules_id='rank-test')
    pin=store.commit(store.capture_pin(),commit_token='seed',version_changes=(change('a',-2,7),change('b',-2,2),change('c',4,0)),
        changes=(),new_segments=(),metadata=metadata()).pin
    pair=scopes.bootstrap_scope_proofs(store,pin,include_children=True,include_sequence=True,include_rank=ranked)
    return store,pin,pair


def positions(store,pair):
    from ate_sim.persistence_proof_rank import RankScope,parse_position
    scope=RankScope('people',NAME)
    root=scopes._resolve(store,pair[0],scope)
    return tuple(parse_position(k) for k,v in OrderedSeekMap(store.db,scopes._seek_domain(store,scope)).page(root))


def test_rank_projection_is_separate_from_ordinal_query_and_atomically_moves(tmp_path):
    store,pin,pair=ranked_store(tmp_path)
    try:
        assert len(pair[0].roots)==7
        assert positions(store,pair)==((store.codec.encode(numeric_rank(-2)),2,store.codec.encode('b')),
            (store.codec.encode(numeric_rank(-2)),7,store.codec.encode('a')),
            (store.codec.encode(numeric_rank(4)),0,store.codec.encode('c')))
        old=store.capture_pin()
        result=scopes.commit_scope_proof(store,pin,*pair,commit_token='move',version_changes=(change('b',10,2),),
            changes=(),identity_changes=(),new_segments=(),metadata=metadata(2))
        new=(result.certificate,result.commitment)
        assert result.commit.outcome=='committed'
        assert tuple(store.codec.decode(k) for r,o,k in positions(store,new))==('a','c','b')
        assert tuple(store.codec.decode(k) for r,o,k in positions(store,pair))==('b','a','c')
        assert scopes._load_root(store,2)[0]==new
        store.release_pin(old)
    finally:store.close()


@pytest.mark.parametrize('phase',['before_commit','after_commit'])
def test_rank_projection_fault_keeps_original_atomic_recovery(tmp_path,phase):
    store,pin,pair=ranked_store(tmp_path)
    original=positions(store,pair)
    def fault(at):
        if at==phase:raise RuntimeError('rank fault')
    store._phase_hook=fault
    try:
        with pytest.raises(RuntimeError,match='rank fault'):
            scopes.commit_scope_proof(store,pin,*pair,commit_token='fault',version_changes=(VersionChange('people','b',delete=True),),
                changes=(),identity_changes=(),new_segments=(),metadata=metadata(2))
        store._phase_hook=lambda _:None
        result=scopes.resolve_scope_commit(store,pin,*pair,commit_token='fault')
        expected='committed' if phase=='after_commit' else 'not_committed'
        assert result.commit.outcome==expected
        assert len(result.certificate.roots)==7
        keys=tuple(store.codec.decode(k) for r,o,k in positions(store,(result.certificate,result.commitment)))
        assert keys==(('a','c') if phase=='after_commit' else ('b','a','c'))
        assert positions(store,pair)==original
    finally:store.close()


def test_six_root_certificate_cannot_claim_empty_ranked_scope(tmp_path):
    from ate_sim.persistence_proof_rank import RankScope
    store,pin,pair=ranked_store(tmp_path,ranked=False)
    try:
        assert len(pair[0].roots)==6
        with pytest.raises(StoreError):scopes._resolve(store,pair[0],RankScope('people',NAME))
    finally:store.close()


def test_rank_scope_position_handles_binary_prefixes_without_collisions():
    from ate_sim.persistence_proof_rank import position,parse_position
    literal=[(b'',0,b'k'),(b'\0',0,b''),(b'\0\0',0,b'a'),(b'a',0,b'z'),(b'a',1,b''),(b'a\0',0,b'a'),(b'a\xff',0,b'')]
    encoded=[position(*v) for v in literal]
    assert encoded==sorted(encoded) and len(set(encoded))==len(encoded)
    assert [parse_position(p) for p in encoded]==literal


@pytest.mark.parametrize('count',[1000,10000])
@pytest.mark.parametrize('before',[False,True])
def test_rank_physical_window_limits_indexed_live_bucket_before_materializing(tmp_path,count,before):
    from ate_sim.persistence_proof_rank import RankScope
    from ate_sim.persistence_proof_native_rank import _physical
    store=LazyRecordStore.create(tmp_path/'live.sqlite',codec=TypedCodec(),simulation_schema='8',rules_id='rank-test')
    try:
        pin=store.commit(store.capture_pin(),commit_token='live',version_changes=(change(i,1,i) for i in range(count)),
            changes=(),new_segments=(),metadata=metadata()).pin
        pair=scopes.bootstrap_scope_proofs(store,pin,include_children=True,include_sequence=True,include_rank=True)
        scope=RankScope('people',NAME)
        wanted=(count-1,count-2) if before else (0,1)
        positions=[(store.codec.encode(numeric_rank(1)),i,store.codec.encode(i)) for i in wanted]
        ticks=[];store.db.set_progress_handler(lambda:ticks.append(1) or 0,100)
        try:
            with store.read_snapshot(pin):
                _physical(store,pin.captured_head,scope,positions,bound=None,before=before,continuation=None)
        finally:store.db.set_progress_handler(None,0)
        assert len(ticks)*100<8000
    finally:store.close()
