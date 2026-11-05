"""Read-only product review: reproduce against disposable World copies."""
from dataclasses import replace
from inspect import getgeneratorlocals
from pathlib import Path
import tempfile
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened
from ate_sim.persistence_lazy_store import _order_checksum, _namespace_checksum
NS = 'world.skills.skills'
def call(f):
    try: return repr(f())
    except Exception as e: return type(e).__name__+': '+str(e)
with tempfile.TemporaryDirectory() as d:
    path,pair=fixture(Path(d))
    with opened(path,pair) as s:
        st=s.store
        for bad in (replace(s.pin,token='unregistered'),replace(s.pin,store_identity='foreign')):
            print('caller',bad.token=='unregistered' and 'unregistered' or 'foreign',
                  'length',call(lambda:st.namespace_size(bad,NS)),
                  'first key',call(lambda:next(st.iter_keys(bad,NS))),
                  'full iteration',call(lambda:list(st.iter_keys(bad,NS))))
        it=st.iter_keys(s.pin,NS)
        print('paused',next(it),'held source payload bytes',len(getgeneratorlocals(it)['record'][2]),
              'membership bytes',len(getgeneratorlocals(it)['record'][6]))
        it.close()
        k=st.codec.encode((99,'craft'))
        st.db.execute('INSERT INTO lazy_order_versions VALUES(?,?,?,?,?,?)',
                      (NS,k,99,1,None,_order_checksum(NS,k,99,1,None)))
        st.db.commit()
        a=st._world_proof_authority
        a.epoch=a._epoch()
        print('listed at head 0 with additional open order starting at 1',
              call(lambda:list(st.iter_keys(s.pin,NS))))
        ghost='world.ghost'
        st.db.execute('INSERT INTO lazy_namespace_state(namespace,member_count,next_ordinal,valid_from,valid_to,row_checksum) VALUES(?,?,?,?,?,?)',
                      (ghost,0,0,1,None,_namespace_checksum(ghost,0,0,1,None)))
        st.db.commit();a.epoch=a._epoch()
        print('future-only physical namespace declared?',call(lambda:st._ordinary_namespace_is_lazy(ghost)))
        st.db.execute('DELETE FROM lazy_order_versions WHERE namespace=? AND typed_key=?',(NS,k))
        st.db.execute('UPDATE lazy_order_versions SET row_checksum=? WHERE namespace=?',('x'*4_194_304,NS))
        st.db.commit();a.epoch=a._epoch()
        statements=[]
        st.db.set_trace_callback(statements.append)
        print('bogus 4 MiB checksum',call(lambda:list(st.iter_keys(s.pin,NS))),
              'raw rank materialized',any('WITH physical AS MATERIALIZED (SELECT typed_key,ordinal,valid_from,valid_to,row_checksum' in x for x in statements))
        st.db.set_trace_callback(None)
