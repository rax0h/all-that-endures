from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.query import reconstruct_cultural_pattern


def test_culture_reconstructs_without_label_entity():
    w=generate_world(843000)
    Simulation(w).run(300)
    patterns=[reconstruct_cultural_pattern(w,sid) for sid in sorted(w.settlements)]
    assert all(p['practices'] for p in patterns)
    signatures={tuple((x['domain'],x['id']) for x in p['practices'][:8]) for p in patterns}
    assert len(signatures)>=2
    assert all('accommodation' in p and 'communities' in p for p in patterns)
