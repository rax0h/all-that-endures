import json, platform, sqlite3, subprocess, time
from pathlib import Path
from ate_sim.core import Person
from ate_sim import persistence_proof_world as world
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened
out=Path('/tmp/ate-insert-baseline-results');out.mkdir(exist_ok=False)
source=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), runtime_tree=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip(), python=platform.python_version(),sqlite=sqlite3.sqlite_version)
rows=[]
for size in (1000,10000,100000):
    path,pair=fixture(out/str(size),size=size)
    with opened(path,pair) as s:
        s.world.people[99]=Person(99,0,1,1);s.world.next_person=100;s.save();pair=s.proof_manifest
    calls=[];original=world._audit_world
    def counted(*a,**kw):
        calls.append(True)
        return original(*a,**kw)
    with opened(path,pair) as s:
        world._audit_world=counted
        start,cpu=time.perf_counter(),time.process_time()
        try:
            s.world.people[100]=Person(100,0,1,1);s.world.next_person=101
            assert s.save()==2
            wall,used=time.perf_counter()-start,time.process_time()-cpu
            pair=s.proof_manifest
        finally:world._audit_world=original
    with opened(path,pair) as s:
        assert tuple(s.world.people)==(99,100)
        assert len(s.skills[1,'craft'].provenance)==size
    row=dict(size=size,archive_unit='retained history values',source=source,raw_save_seconds=wall,raw_save_cpu_seconds=used,full_world_audits_within_save=len(calls),status='complete')
    rows.append(row);(out/f'size-{size}.json').write_text(json.dumps(row,indent=2)+'\n')
    print(size,wall,used,len(calls),flush=True)
(out/'summary.json').write_text(json.dumps(dict(source=source,results=rows),indent=2)+'\n')
