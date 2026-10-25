"""Real backing/catalog composition; dropping the full group check breaks peers."""
import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE
from ate_sim.persistence_proof_target import read_reference_target
from ate_sim import persistence_lazy_identity_catalog as catalog
from simulation.tests.proof_owner_target_fixtures import make_owner_target_store,PAGE
from simulation.tests.proof_target_fixtures import make_target_store,authorities,KINDS


def read(s,p,ref,a,**kw):
 return importlib.import_module('ate_sim.persistence_proof_target_group').read_target_group(s,p,ref,*a,**kw)


def test_complete_incoming_group_and_target(tmp_path):
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite');r=read(s,p,ref,a)
 assert r.target.kind=='list' and r.target.descriptor==('list',0,0)
 assert [(x.namespace,s.codec.decode(x.typed_key),s.codec.decode(x.path),x.incarnation_id) for x in r.group.occurrences]==[(PAGE,(3,0),(('index',0),),2),(PAGE,(3,0),(('index',1),),2),('world.people',1,(('key','pointer'),),2)]
 assert len(r.group.links)==2 and not r.group.retired
 assert s.codec.decode(r.group.anchor)==(('field','people'),('key',1),('key','pointer'))
 assert [s.codec.decode(x) for x,_ in r.group.links]==[(('key',PAGE),('key',(3,0)),('index',0)),(('key',PAGE),('key',(3,0)),('index',1))]
 s.close()


@pytest.mark.parametrize('kind',KINDS)
def test_all_closed_target_families(tmp_path,kind):
 s,p,ref,a=make_target_store(tmp_path/'g.sqlite',kind=kind);r=read(s,p,ref,a)
 assert r.target.kind==kind and r.group.incarnation_id==2 and len(r.group.occurrences)==(2 if kind=='event-ids' else 1)
 s.close()


@pytest.mark.parametrize('fault',['peer','owner','radix','link'])
def test_later_peer_corruption_rejected_after_point_target_passes(tmp_path,fault):
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite')
 if fault=='peer':s.db.execute("DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace='world.people' AND occurrence_path=?",(s.codec.encode((('key','pointer'),)),));s.db.commit()
 else:
  ns,key={
   'owner':(catalog.OWNER_NAMESPACE,('world.people',1)),
   'radix':(catalog.OWNER_TREE_NAMESPACE,('world.people',1,catalog.path_hash(s.codec,(('key','pointer'),)))),
   'link':(catalog.LINK_NAMESPACE,catalog.placement_path(PAGE,(3,0),(('index',1),))),
  }[fault]
  s.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',(ns,s.codec.encode(key)));s.db.commit()
 assert read_reference_target(s,p,ref,*a).kind=='list'
 with pytest.raises(StoreError):read(s,p,ref,a)
 s.close()


@pytest.mark.parametrize('kw',[{'max_members':2},{'max_members':True},{'max_bytes':1},{'max_source_bytes':1},{'max_metadata_bytes':1}])
def test_complete_operation_bounds(tmp_path,kw):
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite')
 with pytest.raises(StoreError):read(s,p,ref,a,**kw)
 assert len(read(s,p,ref,a,max_members=3).group.occurrences)==3;s.close()


def test_retained_target_and_group_use_one_generation(tmp_path):
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite');old=s.capture_pin()
 successor=s.commit(p,commit_token='grow',version_changes=(VersionChange(DESCRIPTOR_NAMESPACE,2,('list',1,1)),VersionChange(PAGE,(2,0),(11,))),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 anew=authorities(s,successor)
 assert read(s,old,ref,a).target.descriptor==('list',0,0)
 assert read(s,successor,ref,anew).target.descriptor==('list',1,1)
 with pytest.raises(StoreError):read(s,successor,ref,(anew[0],a[1],anew[2]))
 s.close()


@pytest.mark.parametrize('fault',['codec','transaction','shadow','view','authority','kind'])
def test_join_guards(tmp_path,fault):
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite')
 if fault=='codec':s.codec.decode=lambda _:pytest.fail('caller codec hook invoked')
 elif fault=='transaction':s.db.execute('BEGIN')
 elif fault=='shadow':s.db.execute('CREATE TEMP TABLE save_head AS SELECT * FROM main.save_head');s.db.commit()
 elif fault=='view':s.db.execute('ALTER TABLE save_head RENAME TO old_head');s.db.execute('CREATE VIEW save_head AS SELECT * FROM old_head');s.db.commit()
 elif fault=='authority':a=(a[0],(a[1][0],b'x'*32),a[2])
 else:ref=HistoryReference('map',2)
 with pytest.raises(StoreError):read(s,p,ref,a)
 if s.db.in_transaction:s.db.rollback()
 s.close()


def test_source_budget_is_shared_between_target_discovery_and_group(tmp_path):
 from simulation.tests.proof_identity_group_fixtures import group_authorities,read_group
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite')
 assert read_reference_target(s,p,ref,*a,max_bytes=7000).kind=='list'
 assert len(read_group(s,p,group_authorities(s,p,2),max_bytes=7000).occurrences)==3
 with pytest.raises(StoreError):read(s,p,ref,a,max_bytes=7000)
 assert len(read(s,p,ref,a,max_bytes=8000).group.occurrences)==3;s.close()


def test_group_discovery_crosses_page_boundary(tmp_path):
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite')
 value={'pointer':ref,'owner':HistoryReference('list',3),**{f'peer{n}':ref for n in range(130)}}
 owners=(VersionChange('world.people',1,value),)
 placements=tuple(IdentityOccurrenceChange('world.people',1,(('key',f'peer{n}'),),2) for n in range(130))
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=4)
 p=s.commit(p,commit_token='many',version_changes=owners+delta.decode(s.codec)[0],identity_changes=placements,next_incarnation_id=4,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a=authorities(s,p);r=read(s,p,ref,a,max_members=133)
 assert len(r.group.occurrences)==133 and len(r.group.links)==132
 assert sum(x.namespace==PAGE for x in r.group.occurrences)==2
 with pytest.raises(StoreError):read(s,p,ref,a,max_members=132)
 s.close()


def test_retained_group_keeps_old_paths_and_canonical_links(tmp_path):
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 s,p,ref,a=make_owner_target_store(tmp_path/'g.sqlite');old=s.capture_pin()
 owners=(VersionChange('world.people',1,{'moved':ref,'owner':HistoryReference('list',3)}),)
 placements=(IdentityOccurrenceChange('world.people',1,(('key','pointer'),),delete=True),IdentityOccurrenceChange('world.people',1,(('key','moved'),),2))
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=4)
 p=s.commit(p,commit_token='move',version_changes=owners+delta.decode(s.codec)[0],identity_changes=placements,next_incarnation_id=4,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 anew=authorities(s,p);before=read(s,old,ref,a);after=read(s,p,ref,anew)
 assert s.codec.decode(before.group.anchor)==(('field','people'),('key',1),('key','pointer'))
 assert s.codec.decode(after.group.anchor)==(('field','people'),('key',1),('key','moved'))
 assert before.group.links!=after.group.links and len(after.group.occurrences)==3;s.close()
