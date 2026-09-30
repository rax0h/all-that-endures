from __future__ import annotations

from collections import defaultdict
import argparse, json
from time import perf_counter

from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation

THRESHOLD = 0.58

def pair_context(world, pair):
    a, b = pair
    sa, sb = world.settlements[a], world.settlements[b]
    qa, qb = world.local[a], world.local[b]
    route = world.trade_routes.get(pair) or world.trade_routes.get((b, a))
    trade = 0.0 if route is None else min(1.0, route.strength + .002 * route.exchanges)
    scarcity = max(qa.scarcity, qb.scarcity)
    prosperity_gap = abs(sa.prosperity - sb.prosperity)
    grievance = .35 * (sa.memory.get("war", 0) + sb.memory.get("war", 0)) + .15 * (
        sa.memory.get("monster_surge", 0) + sb.memory.get("monster_surge", 0)
    )
    target = .42 * scarcity + .25 * prosperity_gap + .18 * grievance - .35 * trade
    return {
        "scarcity": round(scarcity, 4),
        "prosperity_gap": round(prosperity_gap, 4),
        "grievance": round(grievance, 4),
        "trade": round(trade, 4),
        "target": round(target, 4),
        "population_a": sum(1 for p in world.current_people() if p.alive and p.settlement == a),
        "population_b": sum(1 for p in world.current_people() if p.alive and p.settlement == b),
    }

def main(seed, years=1000):
    start = perf_counter()
    world = generate_world(seed, mature=True)
    sim = Simulation(world)

    peak = {}
    years_above = defaultdict(int)
    first_above = {}
    longest_streak = defaultdict(int)
    current_streak = defaultdict(int)
    threshold_entries = defaultdict(int)
    was_above = defaultdict(bool)
    conflict_count_seen = 0
    first_conflict_year = None

    for _ in range(years):
        sim.step()
        for pair, tension in sorted(world.warfare.tensions.items()):
            if pair not in peak or tension > peak[pair]["tension"]:
                peak[pair] = {
                    "tension": round(tension, 6),
                    "year": world.year,
                    "context": pair_context(world, pair),
                }
            above = tension >= THRESHOLD
            if above:
                years_above[pair] += 1
                current_streak[pair] += 1
                longest_streak[pair] = max(longest_streak[pair], current_streak[pair])
                first_above.setdefault(pair, world.year)
                if not was_above[pair]:
                    threshold_entries[pair] += 1
            else:
                current_streak[pair] = 0
            was_above[pair] = above

        if len(world.warfare.conflicts) > conflict_count_seen:
            conflict_count_seen = len(world.warfare.conflicts)
            if first_conflict_year is None:
                first_conflict_year = world.year

    event_counts = defaultdict(int)
    for e in world.events:
        if e.kind in ("war_declared", "battle", "peace_settlement", "death"):
            event_counts[e.kind] += 1

    wars = []
    for cid, c in sorted(world.warfare.conflicts.items()):
        wars.append({
            "id": cid,
            "attacker": c.attacker,
            "defender": c.defender,
            "started_year": c.started_year,
            "ended_year": c.ended_year,
            "cause": c.cause,
            "status": c.status,
            "battles": c.battles,
            "war_score": round(c.war_score, 4),
            "attacker_losses": c.attacker_losses,
            "defender_losses": c.defender_losses,
        })

    pairs = []
    for pair in sorted(world.warfare.tensions):
        pairs.append({
            "pair": list(pair),
            "final_tension": round(world.warfare.tensions[pair], 6),
            "peak_tension": peak[pair]["tension"],
            "peak_year": peak[pair]["year"],
            "peak_context": peak[pair]["context"],
            "years_at_or_above_threshold": years_above[pair],
            "first_threshold_year": first_above.get(pair),
            "threshold_entries": threshold_entries[pair],
            "longest_threshold_streak": longest_streak[pair],
        })
    pairs.sort(key=lambda x: x["peak_tension"], reverse=True)

    result = {
        "seed": seed,
        "years": years,
        "threshold": THRESHOLD,
        "seconds": round(perf_counter() - start, 3),
        "alive": sum(p.alive for p in world.people.values()),
        "events": len(world.events),
        "conflicts": len(world.warfare.conflicts),
        "first_conflict_year": first_conflict_year,
        "war_declarations": event_counts["war_declared"],
        "battles": event_counts["battle"],
        "peace_settlements": event_counts["peace_settlement"],
        "wars": wars,
        "pairs": pairs,
        "global_peak_tension": pairs[0]["peak_tension"] if pairs else 0.0,
        "global_peak_pair": pairs[0]["pair"] if pairs else None,
        "global_peak_year": pairs[0]["peak_year"] if pairs else None,
        "threshold_pair_count": sum(1 for p in pairs if p["years_at_or_above_threshold"] > 0),
    }
    print("WAR_SCAN_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("seed", type=int)
    parser.add_argument("--years", type=int, default=1000)
    args = parser.parse_args()
    main(args.seed, args.years)
