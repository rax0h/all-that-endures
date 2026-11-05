"""Run from repository root with PYTHONPATH=simulation:. (review only)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened
from ate_sim.persistence_proof_native_guard import NativeWriteGuard
from ate_sim.persistence_proof_native_sources import active
from ate_sim.persistence_lazy_store import _version_checksum
from ate_sim.incremental_store import _record_checksum
from unittest.mock import patch

def run(fn):
    with TemporaryDirectory() as temp:
        path, pair = fixture(Path(temp))
        s = opened(path, pair)
        try: fn(s, path)
        finally: s.store.close()

def publication(s,path):
    store=s.store
    s.world.year=1
    def hook(phase):
        if phase=='before_commit':
            print('before_commit callback_guard/accepted_generation/read', store.db._callback_guard, s.store._world_proof_authority.pair[0].generation,store.read_record('world.year',0),flush=True)
            raise RuntimeError('roll back')
    store._phase_hook=hook
    try: s.save()
    except RuntimeError: pass
    store._phase_hook=lambda _:None
    print('rolled_back_generation',s.resolve_save(),'stored_year',store.read_record('world.year',0),flush=True)

def foreign(s,path):
    store=s.store
    typed=store.codec.encode(0); payload=store.codec.encode((0,999)); codec=store.codec.version
    store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',(payload,_record_checksum('world.year',typed,1,codec,0,payload),'world.year',typed));store.db.commit()
    with NativeWriteGuard(store.db) as other:
        with other.publisher():
            print('unowned_guard_bypasses',active(store) is None, 'returned',store.read_record('world.year',0),flush=True)

def interval(s,path):
    store=s.store
    ns='world.skills.skills';typed=store.codec.encode((1,'craft'))
    start,end,p,checksum,c,sc,m,r=store._visible_record_row(0,ns,typed)
    store.db.execute('UPDATE lazy_record_versions SET valid_to=13,row_checksum=? WHERE namespace=? AND typed_key=?',(_version_checksum(ns,typed,sc,c,start,13,m,p),ns,typed));store.db.commit()
    with patch.object(store._world_proof_authority,'guard',lambda:None):
        v=store.read_version(s.pin,ns,(1,'craft'),expected_record_schema=1)
        print('head0_forged_valid_to',v.valid_to,flush=True)

def race(s,path):
    store=s.store; other=sqlite3.connect(path); wrote=[]
    def trace(sql):
        if sql=='BEGIN' and not wrote:
            other.execute("UPDATE records SET record_schema=919 WHERE namespace='world.settlements'")
            other.execute("UPDATE records SET record_schema=record_schema WHERE namespace='world.year'")
            other.commit();wrote.append(True)
    store.db.set_trace_callback(trace)
    try:
        print('epoch_changed_before_snapshot',store.read_record('world.year',0),'mutation_applied',bool(wrote),flush=True)
        try:store.read_record('world.year',0)
        except Exception as e:print('later_call',type(e).__name__,flush=True)
    finally:store.db.set_trace_callback(None);other.close()

def metadata(s,path):
    store=s.store;store.db.execute("UPDATE records SET payload=zeroblob(4194304), record_schema='invalid' WHERE namespace='world.year'")
    store.db.commit();seen=[]
    def observe(_cursor,row):
        for v in row:
            if isinstance(v,bytes) and len(v)==4194304:seen.append(len(v))
        return row
    store.db.row_factory=observe
    with patch.object(store._world_proof_authority,'guard',lambda:None):
        try:store.read_record('world.year',0)
        except Exception as e:print('invalid_metadata_transferred_body',seen,'error',type(e).__name__,flush=True)
def operational(s,path):
    store=s.store
    store.db.execute("UPDATE save_head SET namespace_inventory=zeroblob(4194304)")
    store.db.commit()
    seen=[]
    def observe(_cursor,row):
        seen.extend(len(v) for v in row if isinstance(v,bytes) and len(v)==4194304)
        return row
    store.db.row_factory=observe
    try:store.read_version(s.pin,'world.skills.skills',(1,'craft'),expected_record_schema=1)
    except Exception as e:print('untracked_sql_version_pre_epoch_head_body',seen,'error',type(e).__name__,str(e),flush=True)
for f in (publication,foreign,interval,race,metadata,operational): run(f)
