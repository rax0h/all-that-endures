from pathlib import Path
from tempfile import TemporaryDirectory
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
with TemporaryDirectory() as d:
    path,pair=fixture(Path(d))
    with opened(path,pair) as s:
        st=s.store;a=st._world_proof_authority
        it=st.iter_keys(s.pin,'world.skills.skills')
        print('first',next(it));before=a.epoch
        s.world.year=1
        def fault(phase):
            if phase=='before_commit':raise RuntimeError('rollback')
        st._phase_hook=fault
        try:s.save()
        except RuntimeError:pass
        st._phase_hook=lambda _:None
        print('resolved generation',s.resolve_save(), 'changed accepted epoch',before!=a.epoch)
        try:print('next',next(it))
        except Exception as e:print('next raised',type(e).__name__,str(e))
