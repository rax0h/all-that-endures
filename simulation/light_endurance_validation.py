from __future__ import annotations

from collections import Counter
import argparse
import json
from time import perf_counter

from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world


def current_snapshot(world, interval_events, interval_start, elapsed, total_elapsed):
    alive = [p for p in world.people.values() if p.alive]
    adults = [p for p in alive if p.age >= 16]
    paths = world.advancement.paths
    users = [p for p in alive if p.id in paths]
    complete = [p for p in users if len(paths[p.id].abilities) == 20]
    ranks = Counter(world.advancement.rank(p.id) for p in complete)
    species = Counter(p.species for p in alive)
    resources = list(world.magic_resources.resources.values())
    available = [r for r in resources if r.consumed_year is None]
    interval_new_irons = Counter(
        e.year for e in interval_events
        if e.kind == "rank_advanced"
        and e.data.get("from_rank") == 0
        and e.data.get("to_rank") == 1
    )
    interval_graduates = Counter(
        e.year for e in interval_events if e.kind == "society_trainee_graduated"
    )
    years = range(interval_start + 1, world.year + 1)
    institutions = world.institutions.institution_by_kind("adventure_society")
    treasury = (
        dict(world.currency.treasuries.get(institutions.id, {}))
        if institutions is not None else {}
    )
    return {
        "record": "light_endurance_snapshot",
        "seed": world.seed,
        "year": world.year,
        "interval_start": interval_start,
        "interval_seconds": elapsed,
        "total_seconds": total_elapsed,
        "alive": len(alive),
        "people_total": len(world.people),
        "events_total": len(world.events),
        "species_population": dict(sorted(species.items())),
        "eligible_adults": len(adults),
        "essence_users_living": len(users),
        "adult_participation": len([p for p in adults if p.id in paths]) / max(1, len(adults)),
        "completed_paths": len(complete),
        "completed_path_ranks": {
            "iron": ranks[1],
            "bronze": ranks[2],
            "silver": ranks[3],
            "gold": ranks[4],
            "diamond": ranks[5],
        },
        "resources_total": len(resources),
        "resources_available": len(available),
        "coin_supply": dict(world.currency.minted),
        "society_treasury": treasury,
        "active_trainees": sum(len(b.trainees) for b in world.institutions.branches.values()),
        "interval_new_irons": sum(interval_new_irons.values()),
        "interval_years_without_new_irons": sum(not interval_new_irons[y] for y in years),
        "interval_society_graduations": sum(interval_graduates.values()),
    }


def main(seed: int, years: int, milestone: int):
    if years <= 0 or milestone <= 0:
        raise ValueError("years and milestone must be positive")
    world = generate_world(seed, mature=True)
    sim = Simulation(world)
    total_start = perf_counter()
    prior_year = 0
    prior_event_index = len(world.events)
    while world.year < years:
        target = min(years, world.year + milestone)
        chunk_start = perf_counter()
        sim.run(target - world.year)
        elapsed = perf_counter() - chunk_start
        interval_events = world.events[prior_event_index:]
        report = current_snapshot(
            world,
            interval_events,
            prior_year,
            elapsed,
            perf_counter() - total_start,
        )
        print(json.dumps(report, sort_keys=True), flush=True)
        prior_year = world.year
        prior_event_index = len(world.events)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--years", type=int, required=True)
    parser.add_argument("--milestone", type=int, default=1000)
    args = parser.parse_args()
    main(args.seed, args.years, args.milestone)
