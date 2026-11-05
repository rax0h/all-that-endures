"""Check unwrapped Python callbacks using sqlite3's public customization API."""
from pathlib import Path
from tempfile import TemporaryDirectory
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
from ate_sim import persistence_proof_native_sources as sources
for kind in ('text_factory','scalar'):
    with TemporaryDirectory() as d:
        path,pair=fixture(Path(d))
        with opened(path,pair) as s:
            st=s.store;seen=[]
            def probe():
                guard=getattr(st.db,'_native_write_guard',None)
                if seen or guard is None or not guard.depth:return
                seen.append(('ordinary-source-bypass',sources.active(st) is None))
                try:
                    seen.append(('point-order',st._visible_order('world.skills.skills',st.codec.encode((1,'craft')),0)))
                except Exception as e:seen.append((type(e).__name__,str(e)))
            def text(b):
                probe()
                return b.decode()
            def length(v):
                probe()
                if v is None:return None
                if type(v) is bytes:return len(v)
                return len(str(v).split(chr(0),1)[0])
            if kind=='text_factory':st.db.text_factory=text
            else:st.db.create_function('length',1,length)
            try:s.world.year=1;print(kind,'save',s.save(),'actions',seen)
            finally:st.db.text_factory=str
