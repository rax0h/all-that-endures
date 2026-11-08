from pathlib import Path
import tempfile,sys,sqlite3,time,os
from dataclasses import replace
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
from ate_sim.event_log import EventLog
from ate_sim.core import Layer
def cfg(w):
    w.events=EventLog()
    for i in range(EventLog.chunk_size):w.emit('review',Layer.REALITY,n=i)
    w.events.seal_before(1);w.year=1
p,pair=fixture(Path(tempfile.mkdtemp()),size=4,configure=cfg)
import shutil
def session():
    cp=Path(tempfile.mkdtemp())/'copy.sqlite';shutil.copyfile(p,cp)
    return opened(cp,pair)
s=session();d=s.store;pre=s.world.events._disk_prefix
pre[0]
for label,fn in [('cached-event',lambda:pre[0]),('cached-length',lambda:len(pre)),('generation',lambda:d.generation),('checked_head',d.checked_head)]:
    q=[];d.db.set_trace_callback(q.append);fn();d.db.set_trace_callback(None)
    t=time.perf_counter()
    for i in range(100):fn()
    print(label,len(q),'statements/read',round((time.perf_counter()-t)*10,3),'ms/read',flush=True)
s.close()
for mode in ('verify_full','event'):
    s=session();d=s.store;pre=s.world.events._disk_prefix
    payload=d.db.execute('select payload from segments limit 1').fetchone()[0];decode=d.codec.decode;fired=[]
    def hook(v):
        if v==payload and not fired:
            fired.append(True);d.db.execute("update segments set payload_checksum='invalid'");d.db.commit()
        return decode(v)
    d.codec.decode=hook
    try:print(mode,'returned',pre.verify_full() if mode=='verify_full' else pre[0],flush=True)
    except Exception as e:print(mode,type(e).__name__,str(e),flush=True)
    finally:d.close()
for mode in ('pin','rebegin','cleanup-epoch'):
    s=session();d=s.store;a=d._world_proof_authority
    decode=d.codec.decode;fired=[]
    def hook(v):
        if not fired:
            fired.append(True)
            if mode=='pin':a.read_pin=replace(a.read_pin,token='no-such-token')
            if mode=='rebegin':d.db.rollback();d.db.execute('BEGIN')
        return decode(v)
    if mode!='cleanup-epoch':d.codec.decode=hook
    else:
        def trace(q):
            if q=='ROLLBACK' and not fired:
                fired.append(True);d.db.execute("UPDATE segments SET payload_checksum='invalid'")
        d.db.set_trace_callback(trace)
    try:print(mode,'returned',d.checked_head().generation,'fired',fired,'epoch equal',a.epoch==a._epoch(),flush=True)
    except Exception as e:print(mode,type(e).__name__,str(e),flush=True)
    finally:d.db.set_trace_callback(None);d.close()
