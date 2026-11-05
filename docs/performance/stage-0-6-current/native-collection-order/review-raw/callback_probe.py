"""Prove whether a normal sqlite3 row factory can enter publisher-only reads."""
from tempfile import TemporaryDirectory
from pathlib import Path
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
from ate_sim import persistence_proof_native_sources as sources
NS='world.skills.skills'
with TemporaryDirectory() as d:
    path,pair=fixture(Path(d))
    with opened(path,pair) as s:
        st=s.store;attempts=[]
        def row(cur,values):
            guard=getattr(st.db,'_native_write_guard',None)
            if not attempts and guard is not None and guard.depth:
                attempts.append('entered')
                try:
                    attempts.append(('ordinary-source-bypass',sources.active(st) is None))
                    attempts.append(('native-point-order',st._visible_order(NS,st.codec.encode((1,'craft')),0)))
                    attempts.append(('native-count',st.namespace_size(s.pin,NS)))
                    attempts.append(('durable-write',st.db.execute("UPDATE records SET record_schema=record_schema WHERE namespace='world.year'").rowcount))
                except Exception as e:attempts.append((type(e).__name__,str(e)))
            return values
        st.db.row_factory=row
        try:s.world.year=1;print('save',s.save())
        except Exception as e:print('save error',type(e).__name__,str(e))
        finally:st.db.row_factory=None
        print('row factory actions',attempts)
