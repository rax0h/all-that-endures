import argparse
import json
from time import perf_counter

from ate_sim import Simulation, generate_world
from ate_sim.magic_resources import _circulation_stock, resource_price
from ate_sim.resource_offers import ordered_resource_offers


KINDS = ("essence", "awakening_stone")


def legacy_offers(world, sid, people):
    offers = world.magic_resources.inventory("settlement", sid)
    for holder in people:
        if holder.alive and holder.age >= 16:
            offers.extend(_circulation_stock(world, holder)[2])
    return {
        kind: sorted(
            (r for r in offers if r.kind == kind),
            key=lambda r: (resource_price(r), r.id),
        )
        for kind in KINDS
    }


def ids(offers):
    return {kind: tuple(r.id for r in offers[kind]) for kind in KINDS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=843000)
    parser.add_argument("--years", type=int, default=200)
    parser.add_argument("--repeats", type=int, default=40)
    args = parser.parse_args()

    world = Simulation(generate_world(args.seed, mature=True)).run(args.years)
    by_sid = world.living_by_settlement()

    # Warm both implementations and prove the indexed snapshot is identical.
    expected = {}
    for sid, people in sorted(by_sid.items()):
        expected[sid] = ids(legacy_offers(world, sid, people))
        actual = ids(ordered_resource_offers(world, sid, people))
        if actual != expected[sid]:
            raise AssertionError(f"offer mismatch in settlement {sid}")

    start = perf_counter()
    for _ in range(args.repeats):
        for sid, people in sorted(by_sid.items()):
            legacy_offers(world, sid, people)
    legacy_seconds = perf_counter() - start

    start = perf_counter()
    for _ in range(args.repeats):
        for sid, people in sorted(by_sid.items()):
            actual = ids(ordered_resource_offers(world, sid, people))
            if actual != expected[sid]:
                raise AssertionError(f"indexed offer drift in settlement {sid}")
    indexed_seconds = perf_counter() - start

    print(json.dumps({
        "seed": args.seed,
        "years": args.years,
        "repeats": args.repeats,
        "offers": sum(len(v[k]) for v in expected.values() for k in KINDS),
        "legacy_seconds": legacy_seconds,
        "indexed_seconds": indexed_seconds,
        "speedup": None if indexed_seconds == 0 else legacy_seconds / indexed_seconds,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
