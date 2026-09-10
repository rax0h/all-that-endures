import argparse
import cProfile
import io
import pstats
import time
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation


def main():
    parser=argparse.ArgumentParser(description='Profile a single deterministic history run and print the hottest cumulative call sites.')
    parser.add_argument('seed',type=int,nargs='?',default=843000)
    parser.add_argument('years',type=int,nargs='?',default=300)
    parser.add_argument('--top',type=int,default=40)
    args=parser.parse_args()

    world=generate_world(args.seed)
    profiler=cProfile.Profile()
    start=time.perf_counter()
    profiler.enable()
    Simulation(world).run(args.years)
    profiler.disable()
    elapsed=time.perf_counter()-start

    print({'seed':args.seed,'years':args.years,'elapsed_seconds':round(elapsed,3),'people_total':len(world.people),'events':len(world.events)})
    stream=io.StringIO()
    stats=pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumtime')
    stats.print_stats(args.top)
    print(stream.getvalue())


if __name__=='__main__':
    main()
