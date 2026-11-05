"""Independent closure probe for admission cleanup and cross-event alias mutation."""
import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from ate_sim import persistence_proof_world_session as api
from ate_sim.core import Layer
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened

with TemporaryDirectory(dir='/tmp', prefix='ate-close-review-') as d:
    path, pair = fixture(Path(d))
    def count_pins():
        with sqlite3.connect(path) as db:
            return db.execute('select count(*) from generation_pins').fetchone()[0]
    print('pins before', count_pins())
    with patch.object(api, '_restore_current_event_aliases', side_effect=ValueError('injected admission failure')):
        try:
            opened(path, pair)
        except Exception as e:
            print(type(e).__name__, e)
    print('pins after', count_pins())
with TemporaryDirectory(dir='/tmp', prefix='ate-alias-review-') as d:
    path, pair = fixture(Path(d))
    with opened(path, pair) as s:
        shared = [1, 2]
        s.world.emit('A', Layer.REALITY, a=shared, b=shared)
        s.world.emit('B', Layer.REALITY, c=s.world.events[-1].data['a'])
        s.save()
        pair = s.proof_manifest
    with opened(path, pair) as s:
        a, b = s.world.events
        print('cross/same on open', a.data['a'] is a.data['b'], a.data['a'] is b.data['c'])
        a.data['b'].append(42)
        print('on mutation', list(b.data['c']))
        s.save()
        pair = s.proof_manifest
    with opened(path, pair) as s:
        a, b = s.world.events
        print('on reopen', list(a.data['a']), list(a.data['b']), list(b.data['c']), a.data['b'] is b.data['c'])
