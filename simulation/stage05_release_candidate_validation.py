from __future__ import annotations

from collections import Counter
import argparse
import json
from time import perf_counter

from ate_sim.checkpoint import dumps, loads
from ate_sim.currency import COIN_VALUE, DENOMINATIONS
from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world


def rank_name(rank):
    return ("unranked", "iron", "bronze", "silver", "gold", "diamond")[rank]


def current_report(world, start_year, start_event_index, elapsed, total_elapsed):
    alive = [p for p in world.people.values() if p.alive]
    adults = [p for p in alive if p.age >= 16]
    paths = world.advancement.paths
    users = [p for p in alive if p.id in paths]
    complete = [p for p in users if len(paths[p.id].abilities) == 20]
    ranks = Counter(world.advancement.rank(p.id) for p in complete)
    species = Counter(p.species for p in alive)
    interval = world.events[start_event_index:]
    new_irons = Counter(
        e.year for e in interval
        if e.kind == "rank_advanced"
        and e.data.get("from_rank") == 0
        and e.data.get("to_rank") == 1
    )
    grads = Counter(e.year for e in interval if e.kind == "society_trainee_graduated")
    years = range(start_year + 1, world.year + 1)
    society = world.institutions.institution_by_kind("adventure_society")
    treasury = dict(world.currency.treasuries.get(society.id, {})) if society else {}
    return {
        "record": "release_snapshot",
        "seed": world.seed,
        "year": world.year,
        "interval_start": start_year,
        "interval_seconds": elapsed,
        "total_seconds": total_elapsed,
        "alive": len(alive),
        "people_total": len(world.people),
        "events_total": len(world.events),
        "eligible_adults": len(adults),
        "essence_users_living": len(users),
        "adult_participation": len([p for p in adults if p.id in paths]) / max(1, len(adults)),
        "completed_paths": len(complete),
        "completed_path_ranks": {rank_name(i): ranks[i] for i in range(1, 6)},
        "species_population": dict(sorted(species.items())),
        "resources_total": len(world.magic_resources.resources),
        "resources_available": sum(r.consumed_year is None for r in world.magic_resources.resources.values()),
        "coin_supply": dict(world.currency.minted),
        "society_treasury": treasury,
        "active_trainees": sum(len(b.trainees) for b in world.institutions.branches.values()),
        "interval_new_irons": sum(new_irons.values()),
        "interval_years_without_new_irons": sum(not new_irons[y] for y in years),
        "interval_society_graduations": sum(grads.values()),
    }


def audit(world):
    violations = []
    warnings = []

    # Event graph / chronology.
    ids = set()
    for expected, e in enumerate(world.events, start=1):
        if e.id != expected:
            violations.append(f"event id discontinuity: expected {expected}, got {e.id}")
            break
        if any(c >= e.id for c in e.causes):
            violations.append(f"event {e.id} has non-prior cause")
        if any(c not in ids for c in e.causes):
            violations.append(f"event {e.id} has missing cause")
        ids.add(e.id)
    if world.event_ids != ids:
        violations.append("event_ids index disagrees with event log")

    # Core referential integrity.
    for p in world.people.values():
        if p.settlement not in world.settlements:
            violations.append(f"person {p.id} has missing settlement {p.settlement}")
        if p.household not in world.households:
            violations.append(f"person {p.id} has missing household {p.household}")
        elif p.id not in world.households[p.household].members:
            violations.append(f"person {p.id} absent from household {p.household} membership")
    for h in world.households.values():
        if h.settlement not in world.settlements:
            violations.append(f"household {h.id} has missing settlement")
        for pid in h.members:
            if pid not in world.people:
                violations.append(f"household {h.id} references missing person {pid}")

    # Current magical state must agree with body rank and canonical prerequisites.
    for pid, path in world.advancement.paths.items():
        if pid not in world.people:
            violations.append(f"path references missing person {pid}")
            continue
        actual = world.advancement.rank(pid)
        if world.people[pid].rank != actual:
            violations.append(f"person {pid} snapshot rank {world.people[pid].rank} != advancement rank {actual}")
        if len(path.base_essences) > 3 or len(path.abilities) > 20:
            violations.append(f"person {pid} exceeds path capacity")
        if actual > 0:
            counts = Counter(a.essence for a in path.abilities)
            if len(path.base_essences) != 3 or path.confluence is None:
                violations.append(f"ranked person {pid} lacks complete essence configuration")
            if len(path.abilities) != 20 or len(counts) != 4 or set(counts.values()) != {5}:
                violations.append(f"ranked person {pid} lacks 4x5 ability configuration")
            if any(a.rank < actual for a in path.abilities):
                violations.append(f"ranked person {pid} has ability below body rank")
            if actual == 5 and path.core_fraction != 0:
                violations.append(f"Diamond {pid} retains core taint")

    # Ranked currency conservation and non-negativity.
    balances = Counter()
    for pid, wallet in world.currency.wallets.items():
        if pid not in world.people:
            violations.append(f"wallet references missing person {pid}")
        for d, n in wallet.items():
            if d not in COIN_VALUE or type(n) is not int or n < 0:
                violations.append(f"invalid wallet balance {pid}:{d}={n}")
            balances[d] += n
    for iid, treasury in world.currency.treasuries.items():
        if iid not in world.institutions.institutions:
            violations.append(f"treasury references missing institution {iid}")
        for d, n in treasury.items():
            if d not in COIN_VALUE or type(n) is not int or n < 0:
                violations.append(f"invalid treasury balance {iid}:{d}={n}")
            balances[d] += n
    for d, n in world.currency.consumed.items():
        if d not in COIN_VALUE or type(n) is not int or n < 0:
            violations.append(f"invalid consumed coin count {d}={n}")
        balances[d] += n
    for d in DENOMINATIONS:
        minted = world.currency.minted.get(d, 0)
        if balances[d] != minted:
            violations.append(f"coin conservation mismatch {d}: accounted {balances[d]} minted {minted}")

    # Magical-resource ownership/provenance indexes.
    resources = world.magic_resources.resources
    for rid, r in resources.items():
        if r.origin_event is not None and r.origin_event not in ids:
            violations.append(f"resource {rid} has missing origin event")
        indexed = rid in world.magic_resources.owner_index.get((r.owner_kind, r.owner_id), set()) if r.owner_kind is not None and r.owner_id is not None else False
        if r.consumed_year is None:
            if r.owner_kind == "person" and r.owner_id not in world.people:
                violations.append(f"resource {rid} owned by missing person")
            if r.owner_kind == "settlement" and r.owner_id not in world.settlements:
                violations.append(f"resource {rid} owned by missing settlement")
            if r.owner_kind is not None and r.owner_id is not None and not indexed:
                violations.append(f"available resource {rid} missing from owner index")
        else:
            if indexed:
                violations.append(f"consumed resource {rid} remains in owner index")
            if r.consumed_by not in world.people or r.consumed_event not in ids:
                violations.append(f"consumed resource {rid} has invalid consumption provenance")

    # Active Society trainee state is bounded, live, local, and causally linked.
    active_people = set()
    for branch in world.institutions.branches.values():
        if branch.institution not in world.institutions.institutions:
            violations.append(f"branch {branch.id} has missing institution")
        if branch.settlement not in world.settlements:
            violations.append(f"branch {branch.id} has missing settlement")
        if len(branch.trainees) > 3:
            violations.append(f"branch {branch.id} exceeds three trainee places")
        for pid, enrollment in branch.trainees.items():
            if pid in active_people:
                violations.append(f"person {pid} active in multiple trainee places")
            active_people.add(pid)
            p = world.people.get(pid)
            if p is None or not p.alive or p.settlement != branch.settlement:
                violations.append(f"active trainee {pid} is dead, missing, or nonlocal")
            path = world.advancement.path(pid)
            if path is not None and len(path.abilities) == 20:
                violations.append(f"active trainee {pid} already has complete path")
            if enrollment not in ids or world.events[enrollment - 1].kind != "society_trainee_enrolled":
                violations.append(f"active trainee {pid} has invalid enrollment event")

    alive = [p for p in world.people.values() if p.alive]
    adults = [p for p in alive if p.age >= 16]
    available = [r for r in resources.values() if r.consumed_year is None]
    paths = world.advancement.paths
    living_users = [p for p in alive if p.id in paths]
    complete = [p for p in living_users if len(paths[p.id].abilities) == 20]
    ranks = Counter(world.advancement.rank(p.id) for p in complete)

    recent_start = max(1, world.year - 99)
    recent_irons = Counter(
        e.year for e in world.events_between(recent_start, world.year)
        if e.kind == "rank_advanced"
        and e.data.get("from_rank") == 0
        and e.data.get("to_rank") == 1
    )
    gap = longest_gap(recent_irons, recent_start, world.year)

    if not alive:
        violations.append("living population collapsed to zero")
    if adults and not living_users:
        violations.append("living magical participation collapsed to zero")
    if not complete:
        violations.append("no living completed magical paths")
    if world.year >= 100 and not recent_irons:
        violations.append("no new Iron transition in final 100 years")
    if not available:
        violations.append("all magical resources exhausted")
    if world.currency.minted.get("iron", 0) <= 0:
        violations.append("Iron-denomination supply absent")

    if ranks[5] > 20:
        warnings.append(f"living Diamond count is high for current design expectation: {ranks[5]}")
    if gap > 25:
        warnings.append(f"longest no-new-Iron gap in final century is {gap} years")

    return {
        "record": "release_audit",
        "seed": world.seed,
        "year": world.year,
        "passed": not violations,
        "violations": violations[:100],
        "warnings": warnings,
        "living": len(alive),
        "eligible_adults": len(adults),
        "essence_users": len(living_users),
        "completed_paths": len(complete),
        "ranks": {rank_name(i): ranks[i] for i in range(1, 6)},
        "species": dict(sorted(Counter(p.species for p in alive).items())),
        "resources_total": len(resources),
        "resources_available": len(available),
        "new_irons_final_100": sum(recent_irons.values()),
        "years_without_new_iron_final_100": sum(not recent_irons[y] for y in range(recent_start, world.year + 1)),
        "longest_no_new_iron_gap_final_100": gap,
        "active_trainees": len(active_people),
        "events_total": len(world.events),
    }


def longest_gap(counts, first_year, last_year):
    longest = current = 0
    for year in range(first_year, last_year + 1):
        if counts[year]:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def run_audit(seed, years):
    world = generate_world(seed, mature=True)
    sim = Simulation(world)
    total_start = perf_counter()
    prior_year = 0
    prior_event = len(world.events)
    marks = sorted(set([m for m in (250, 500, 750, 1000, 2000, 3000) if m <= years] + [years]))
    for mark in marks:
        start = perf_counter()
        sim.run(mark - world.year)
        elapsed = perf_counter() - start
        print(json.dumps(current_report(world, prior_year, prior_event, elapsed, perf_counter() - total_start), sort_keys=True), flush=True)
        prior_year = world.year
        prior_event = len(world.events)
    report = audit(world)
    print(json.dumps(report, sort_keys=True), flush=True)
    if not report["passed"]:
        raise SystemExit("release audit failed")


def run_resume(seed, split, years):
    original = generate_world(seed, mature=True)
    sim = Simulation(original)
    start = perf_counter()
    sim.run(split)
    blob = dumps(original)
    restored = loads(blob)
    checkpoint_seconds = perf_counter() - start

    # Continue the in-memory world and the serialized/restored world independently.
    start_a = perf_counter()
    sim.run(years - split)
    a_seconds = perf_counter() - start_a
    start_b = perf_counter()
    Simulation(restored).run(years - split)
    b_seconds = perf_counter() - start_b

    digest_a = original.digest()
    digest_b = restored.digest()
    audit_a = audit(original)
    audit_b = audit(restored)
    report = {
        "record": "checkpoint_resume_release_test",
        "seed": seed,
        "split": split,
        "years": years,
        "checkpoint_seconds_including_digest": checkpoint_seconds,
        "uninterrupted_tail_seconds": a_seconds,
        "restored_tail_seconds": b_seconds,
        "digest_match": digest_a == digest_b,
        "digest": digest_a,
        "original_audit_passed": audit_a["passed"],
        "restored_audit_passed": audit_b["passed"],
        "original_violations": audit_a["violations"],
        "restored_violations": audit_b["violations"],
    }
    print(json.dumps(report, sort_keys=True), flush=True)
    if not report["digest_match"] or not report["original_audit_passed"] or not report["restored_audit_passed"]:
        raise SystemExit("checkpoint/resume release test failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("audit")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--years", type=int, default=1000)
    p = sub.add_parser("resume")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--split", type=int, default=500)
    p.add_argument("--years", type=int, default=1000)
    args = parser.parse_args()
    if args.mode == "audit":
        run_audit(args.seed, args.years)
    else:
        run_resume(args.seed, args.split, args.years)
