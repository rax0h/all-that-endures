from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch
from ate_sim.incremental_store import StoreError, StoreIntegrityError, TypedCodec
from ate_sim import persistence_proof_native_roster as roster
from ate_sim.persistence_validation_scope import checked_read_operation
from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, LINK_NAMESPACE
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened

codec=TypedCodec()
authority=SimpleNamespace(pair=(None,b'x'*32))
store=SimpleNamespace()
def count(blob, namespace='world.year'):
    return roster.expected_count(store,authority,SimpleNamespace(head=SimpleNamespace(namespace_counts=blob)),namespace)
assert count(codec.encode({'world.year':(2,3)}))==2
assert count(codec.encode({'world.year':(0,3)}))==0
assert count(codec.encode({}))==0
for value in [[], {'world.year':[1,0]}, {'world.year':(True,0)}, {'world.year':(-1,0)}, {'world.year':(0,0)}, {3:(1,0)}]:
    try: count(codec.encode(value))
    except StoreError: pass
    else: raise AssertionError(('accepted malformed count',value))
for blob in [b'x'*1048577, bytearray(codec.encode({})), b'not-json']:
    try: count(blob)
    except StoreError: pass
    else: raise AssertionError('accepted malformed/oversized blob')
print('PASS: record/segment pairs, absent namespace, six invalid count schemas and three blob guards',flush=True)

with tempfile.TemporaryDirectory(prefix='ate-roster-independent-',dir='/tmp') as directory:
    path,pair=fixture(Path(directory),size=8)
    with opened(path,pair) as session:
        st=session.store
        parses=[];sql=[];original=roster._namespace_counts
        def parse(*args):
            parses.append(1)
            return original(*args)
        st.db.set_trace_callback(sql.append)
        try:
            with patch.object(roster,'_namespace_counts',parse):
                with checked_read_operation(st,session.pin):
                    assert st.read_records('world.year')==((0,(0,0),1),)
                    assert st.read_records('world.year')==((0,(0,0),1),)
                with checked_read_operation(st,session.pin):
                    assert st.read_records('world.year')==((0,(0,0),1),)
        finally: st.db.set_trace_callback(None)
        assert len(parses)==2,parses
        counts=[q for q in sql if q.lower().startswith('select count(*) from records where namespace=')]
        assert len(counts)==3,counts
        assert not st.db.in_transaction
        print('PASS: accepted count metadata parsed once per scope; three physical COUNT checks for three reads',flush=True)
        cat=IdentityCatalog(st);owner=('world.skills.skills',(1,'craft'));where=(('field','provenance'),)
        incarnation=st.read_identity_occurrence(session.pin,*owner,where).incarnation_id
        first=cat.read_owner_identity(session.pin,owner)
        assert cat.read_owner_identity(session.pin,owner)==first
        assert cat.owner_cache_diagnostics()['hits']>=1
        assert cat.read_identity_links(session.pin,incarnation)
        changed=st.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND index_value=?',(LINK_NAMESPACE,'incarnation',st.codec.encode(incarnation))).rowcount
        assert changed>0
        st.db.commit();st._world_proof_authority.epoch=st._world_proof_authority._epoch()
        try: cat.read_identity_links(session.pin,incarnation)
        except StoreIntegrityError as exc: print('PASS: missing link projection rejected through public warmed catalog:',str(exc),flush=True)
        else: raise AssertionError('missing link projection accepted')
        assert not st.db.in_transaction
print('All independent probes passed',flush=True)
