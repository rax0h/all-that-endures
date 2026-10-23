"""Cross-root raw group consistency with no owner-body restoration."""
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreError,StoreIntegrityError,StoreConflictError,Membership
from ate_sim.persistence_proof_occurrence import RawOccurrence,OwnerScope,GroupScope
from ate_sim.persistence_proof_occurrence_seek import certificate_commitment as occurrence_commitment
from ate_sim import persistence_lazy_identity_catalog as catalog
from simulation.tests.proof_identity_group_fixtures import (
    NS,PAGE,make_group_store,group_authorities,read_group,group_module,reanchor,retire_empty)


def test_literal_group_without_owner_payloads_or_world_decode(tmp_path):
    store,pin,pairs=make_group_store(tmp_path/'group.sqlite',1000)
    sql=[];store.reset_diagnostics();store.db.set_trace_callback(sql.append)
    got=read_group(store,pin,pairs);enc=store.codec.encode
    assert got.incarnation_id==1 and got.retired is False
    assert got.occurrences==(RawOccurrence(NS,enc(1),enc(()),1),RawOccurrence(NS,enc(2),enc(()),1))
    assert got.anchor==enc((('field','people'),('key',1)))
    assert got.links==((enc((('field','people'),('key',2))),enc((('field','people'),('key',1)))),)
    assert store.diagnostics().payload_reads==0
    body=[s for s in sql if 'then payload end' in s.lower()]
    assert body and all('world.people' not in s and "'archive'" not in s for s in body)
    store.close()


def test_retained_and_successor_reanchor(tmp_path):
    store,pin,pairs=make_group_store(tmp_path/'group.sqlite');old=store.capture_pin();writer=reanchor(store,pin)
    assert len(read_group(store,old,pairs).occurrences)==2
    current=read_group(store,writer,group_authorities(store,writer))
    assert current.occurrences==(RawOccurrence(NS,store.codec.encode(2),store.codec.encode(()),1),)
    assert current.links==() and current.anchor==store.codec.encode((('field','people'),('key',2)))
    store.close()


def test_live_empty_and_proved_retired_absence(tmp_path):
    store,pin,pairs=make_group_store(tmp_path/'empty.sqlite',inc=3)
    live=read_group(store,pin,pairs);assert live.occurrences==live.links==() and live.anchor is None and not live.retired
    old=store.capture_pin();writer=retire_empty(store,pin)
    assert not read_group(store,old,pairs).retired
    retired=read_group(store,writer,group_authorities(store,writer,3))
    assert retired.retired and retired.occurrences==retired.links==() and retired.anchor is None
    store.close()


@pytest.mark.parametrize('namespace',catalog.CATALOG_NAMESPACES[:-1])
def test_missing_selected_metadata_rejected(tmp_path,namespace):
    store,pin,pairs=make_group_store(tmp_path/'missing.sqlite')
    store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?',(namespace,));store.db.commit()
    with pytest.raises(StoreIntegrityError):read_group(store,pin,pairs)
    store.close()


@pytest.mark.parametrize('fault',['group-count','group-digest','group-anchor','owner-count','owner-leaf','link-inc','link-anchor','link-membership','allocator','empty-count','empty-link-count'])
def test_independently_committed_inconsistent_catalog_rejected(tmp_path,fault):
    def mutate(changes,codec):
        owner_digest=None
        if fault=='owner-leaf':
            for c in changes:
                if c.namespace==catalog.OWNER_TREE_NAMESPACE and c.key[:2]==(NS,1):
                    owner_digest=catalog.node_commit(codec,('owner-leaf/v1',(),2))[1]
        for c in changes:
            v=c.value
            if c.namespace==catalog.GROUP_NAMESPACE and c.key==(3 if fault.startswith('empty-') else 1):
                v=list(v)
                if fault=='group-count':v[2]=3
                elif fault=='group-digest':v[3]='0'*64
                elif fault=='group-anchor':v[6]=(('field','people'),('key',2))
                elif fault=='empty-count':v[2]=False
                elif fault=='empty-link-count':v[4]=False
                v=tuple(v)
            if c.namespace==catalog.OWNER_NAMESPACE and c.key==(NS,1):
                v=list(v)
                if fault=='owner-count':v[7]=2
                elif fault=='owner-leaf':v[8]=owner_digest
                v=tuple(v)
            if fault=='owner-leaf' and c.namespace==catalog.OWNER_TREE_NAMESPACE and c.key[:2]==(NS,1):v=('owner-leaf/v1',(),2)
            if c.namespace==catalog.LINK_NAMESPACE and not c.delete:
                if fault=='link-inc':v=('identity-link/v1',2,(('field','people'),('key',1)))
                elif fault=='link-anchor':v=('identity-link/v1',1,(('field','people'),('key',2)))
                elif fault=='link-membership':c=replace(c,memberships=c.memberships+(Membership('extra',1,0),))
            if fault=='allocator' and c.namespace==catalog.CATALOG_NAMESPACE:v=(v[0],v[1],5,v[3],v[4])
            yield replace(c,value=v)
    store,pin,pairs=make_group_store(tmp_path/'bad.sqlite',catalog_mutator=mutate,inc=3 if fault.startswith('empty-') else 1)
    with pytest.raises(StoreIntegrityError):read_group(store,pin,pairs)
    store.close()


@pytest.mark.parametrize('end',['bad',b'bad'])
def test_selected_owner_source_interval_storage_class_rejected(tmp_path,end):
    store,pin,pairs=make_group_store(tmp_path/'interval.sqlite')
    store.db.execute('UPDATE lazy_record_versions SET valid_to=? WHERE namespace=? AND typed_key=?',(end,NS,store.codec.encode(1)));store.db.commit()
    with pytest.raises(StoreIntegrityError):read_group(store,pin,pairs)
    store.close()


@pytest.mark.parametrize('fault',['missing-owner','duplicate-owner','extra-owner','wrong-owner-root','query-scope','expected','generation','cached-index','physical-index','released','transaction','hook'])
def test_authority_and_context_rejected(tmp_path,fault):
    store,pin,pairs=make_group_store(tmp_path/'authority.sqlite');pairs=list(pairs)
    if fault=='missing-owner':pairs[3]=pairs[3][1:]
    elif fault=='duplicate-owner':pairs[3]=pairs[3]+pairs[3][:1]
    elif fault=='extra-owner':
        from simulation.tests.proof_occurrence_seek_fixtures import construct_seek_certificates
        pairs[3]+=construct_seek_certificates(store,pin,(OwnerScope(NS,store.codec.encode(3)),))
    elif fault=='wrong-owner-root':
        from simulation.tests.proof_occurrence_seek_fixtures import construct_seek_certificates
        other=construct_seek_certificates(store,pin,(OwnerScope(NS,store.codec.encode(3)),))[0][0]
        cert=replace(pairs[3][0][0],root=other.root);pairs[3]=((cert,occurrence_commitment(cert)),)+pairs[3][1:]
    elif fault=='query-scope':
        from simulation.tests.proof_query_seek_fixtures import construct_query_seek
        pairs[2]=construct_query_seek(store,pin,replace(pairs[2][0].scope,index_value=store.codec.encode(2)))
    elif fault=='expected':pairs[0]=(pairs[0][0],b'x'*32)
    elif fault=='generation':
        cert=replace(pairs[1][0],generation=0);pairs[1]=(cert,occurrence_commitment(cert))
    elif fault=='cached-index':store._interval_indexes.discard('lazy_record_interval')
    elif fault=='physical-index':store.db.execute('DROP INDEX lazy_record_interval');store.db.commit()
    elif fault=='released':store.release_pin(pin)
    elif fault=='transaction':store.db.execute('BEGIN')
    else:store.codec.decode=lambda _:pytest.fail('caller hook invoked')
    with pytest.raises((StoreError,StoreIntegrityError,StoreConflictError)):read_group(store,pin,tuple(pairs))
    if store.db.in_transaction:store.db.rollback()
    store.close()


@pytest.mark.parametrize('kwargs',[{'max_members':1},{'max_bytes':1},{'max_source_bytes':1},{'max_metadata_bytes':1}])
def test_explicit_budget_errors(tmp_path,kwargs):
    store,pin,pairs=make_group_store(tmp_path/'budget.sqlite')
    with pytest.raises(group_module().GroupProofBudgetError):read_group(store,pin,pairs,**kwargs)
    store.close()


def test_large_owner_point_and_canonical_link_order(tmp_path):
    store,pin,pairs=make_group_store(tmp_path/'wide.sqlite',wide_owner=1000,aux_peer=True)
    store.reset_diagnostics();got=read_group(store,pin,pairs)
    assert tuple(r.namespace for r in got.occurrences)==(PAGE,NS,NS)
    # Absolute path format comes from the public family contract; encoded order,
    # unlike raw group SQL order, determines the canonical anchor.
    legacy=catalog.IdentityCatalog(store).read_identity_group(pin,1)
    assert got.anchor==store.codec.encode(legacy.anchor)
    assert got.links==tuple((store.codec.encode(t),store.codec.encode(a)) for t,a in legacy.links)
    assert got.anchor!=store.codec.encode(catalog.placement_path(PAGE,(4,0),(('index',0),)))
    store.close()


@pytest.mark.parametrize('fault',['missing','changed'])
def test_selected_retirement_range_checked(tmp_path,fault):
    store,pin,_=make_group_store(tmp_path/'retired.sqlite');writer=retire_empty(store,pin);pairs=group_authorities(store,writer,3)
    ns=catalog.RETIRED_NODE_NAMESPACE
    if fault=='missing':store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?',(ns,));store.db.commit()
    else:
        # A valid replacement source/root still disagrees with descriptor range.
        from ate_sim.persistence_lazy_store import VersionChange
        from simulation.tests.proof_identity_group_fixtures import metadata
        writer=store.commit(writer,commit_token='range-corruption',version_changes=(VersionChange(ns,3,('retired-range/v1',3,4,None,None)),),
            changes=(),new_segments=(),metadata=metadata(3)).pin
        pairs=group_authorities(store,writer,3)
    with pytest.raises(StoreIntegrityError):read_group(store,writer,pairs)
    store.close()
