import cProfile
import pstats
import sys
from io import StringIO
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation


def main(seed=843000, years=150, limit=40, warmup=0):
    world=generate_world(seed)
    sim=Simulation(world)
    sim.run(warmup)
    profiler=cProfile.Profile()
    profiler.enable()
    sim.run(years)
    profiler.disable()
    stream=StringIO()
    pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumtime').print_stats(limit)
    print(stream.getvalue())
    print(f'profile_start_year={warmup+1} profile_end_year={world.year} profile_years={years} events={len(world.events)} people={len(world.people)} lots={len(world.materials.lots)} resources={len(world.magic_resources.resources)}')

if __name__=='__main__':
    seed=int(sys.argv[1]) if len(sys.argv)>1 else 843000
    years=int(sys.argv[2]) if len(sys.argv)>2 else 150
    warmup=int(sys.argv[3]) if len(sys.argv)>3 else 0
    main(seed,years,warmup=warmup)
