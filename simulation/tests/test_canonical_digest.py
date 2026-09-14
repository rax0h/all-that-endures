import hashlib
import json
from dataclasses import asdict
from simulation.ate_sim import Simulation, generate_world
from simulation.ate_sim.core import _canonical
from simulation.ate_sim.checkpoint import dumps, loads

def test_canonical_world_matches_legacy_deep_copy_representation():
    world = Simulation(generate_world(843000)).run(8)
    legacy = _canonical(asdict(world))
    assert _canonical(world) == legacy
    encoded = json.dumps(legacy,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    assert world.digest() == hashlib.sha256(encoded).hexdigest()
    assert loads(dumps(world)).digest() == world.digest()
