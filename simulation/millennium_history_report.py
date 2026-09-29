from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
import json
from time import perf_counter

from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.advancement import RANKS

SEED = 843017
YEARS = 1000


def emit(label, value):
    print(label + "=" + json.dumps(value, sort_keys=True, separators=(",", ":")), flush=True)


def main():
    started = perf_counter()
    world = generate_world(SEED, mature=True)
    sim = Simulation(world)
    for mark in range(100, YEARS + 1, 100):
        sim.run(100)
        emit("PROGRESS", {
            "year": world.year,
            "people": len(world.people),
            "alive": sum(p.alive for p in world.people.values()),
            "events": len(world.events),
            "elapsed_seconds": round(perf_counter() - started, 3),
        })

    analysis_started = perf_counter()
    events = list(world.events)
    event_by_id = {e.id: e for e in events}
    person_events = defaultdict(list)
    death_event = {}
    for e in events:
        for ref in e.actors:
            if ref.kind == "person":
                person_events[ref.id].append(e)
        if e.kind == "death":
            pid = next((r.id for r in e.actors if r.kind == "person"), None)
            if pid is not None:
                death_event[pid] = e

    def rank(pid):
        return world.advancement.rank(pid)

    def death_year(pid):
        e = death_event.get(pid)
        return None if e is None else e.year

    def death_cause(pid):
        e = death_event.get(pid)
        return None if e is None else e.data.get("cause")

    def person_card(pid):
        p = world.people[pid]
        path = world.advancement.path(pid)
        return {
            "id": pid,
            "born": p.born,
            "death_year": death_year(pid),
            "death_cause": death_cause(pid),
            "alive": p.alive,
            "species": p.species,
            "settlement_at_end": p.settlement,
            "household": p.household,
            "household_lineage": world.households[p.household].lineage if p.household in world.households else None,
            "occupation": p.occupation,
            "rank": RANKS[rank(pid)],
            "rank_number": rank(pid),
            "base_essences": list(path.base_essences) if path else [],
            "abilities": len(path.abilities) if path else 0,
            "parents": list(world.genealogy.parents.get(pid, p.parents or ())),
            "children": list(world.genealogy.children.get(pid, ())),
            "event_count": len(person_events.get(pid, ())),
        }

    parents = {pid: tuple(world.genealogy.parents.get(pid, p.parents or ())) for pid, p in world.people.items()}
    children = {pid: tuple(world.genealogy.children.get(pid, ())) for pid in world.people}

    @lru_cache(maxsize=None)
    def founder_roots(pid):
        ps = tuple(p for p in parents.get(pid, ()) if p in world.people)
        if not ps:
            return frozenset((pid,))
        roots = set()
        for p in ps:
            roots.update(founder_roots(p))
        return frozenset(roots)

    @lru_cache(maxsize=None)
    def deepest_chain_to(pid):
        ps = tuple(p for p in parents.get(pid, ()) if p in world.people)
        if not ps:
            return (pid,)
        best = max((deepest_chain_to(p) for p in ps), key=len)
        return best + (pid,)

    root_stats = defaultdict(lambda: {
        "descendants": 0,
        "living_descendants": 0,
        "ranked_descendants": 0,
        "war_dead_descendants": 0,
        "species": set(),
    })
    for pid, p in world.people.items():
        for root in founder_roots(pid):
            if pid == root:
                continue
            s = root_stats[root]
            s["descendants"] += 1
            s["living_descendants"] += int(p.alive)
            s["ranked_descendants"] += int(rank(pid) > 0)
            s["war_dead_descendants"] += int(death_cause(pid) == "war")
            s["species"].add(p.species)

    families = []
    for root, s in root_stats.items():
        descendants = [pid for pid in world.people if root in founder_roots(pid) and pid != root]
        deepest_pid = max(descendants, key=lambda pid: len(deepest_chain_to(pid)), default=root)
        living = [pid for pid in descendants if world.people[pid].alive]
        deepest_living_pid = max(living, key=lambda pid: len(deepest_chain_to(pid)), default=None)
        families.append({
            "root": root,
            "root_card": person_card(root),
            "descendants": s["descendants"],
            "living_descendants": s["living_descendants"],
            "ranked_descendants": s["ranked_descendants"],
            "war_dead_descendants": s["war_dead_descendants"],
            "species": sorted(s["species"] | {world.people[root].species}),
            "deepest_generations": len(deepest_chain_to(deepest_pid)) - 1,
            "deepest_chain_ids": list(deepest_chain_to(deepest_pid)),
            "deepest_living_chain_ids": [] if deepest_living_pid is None else list(deepest_chain_to(deepest_living_pid)),
        })
    families.sort(key=lambda f: (f["descendants"], f["deepest_generations"], f["living_descendants"]), reverse=True)

    deepest_pid = max(world.people, key=lambda pid: len(deepest_chain_to(pid)))
    living_ids = [pid for pid, p in world.people.items() if p.alive]
    deepest_living_pid = max(living_ids, key=lambda pid: len(deepest_chain_to(pid))) if living_ids else None
    deepest_chain = [person_card(pid) for pid in deepest_chain_to(deepest_pid)]
    deepest_living_chain = [] if deepest_living_pid is None else [person_card(pid) for pid in deepest_chain_to(deepest_living_pid)]

    battles_by_conflict = defaultdict(list)
    battle_to_conflict = {}
    for e in events:
        if e.kind == "battle":
            cid = e.data.get("conflict")
            battles_by_conflict[cid].append(e)
            battle_to_conflict[e.id] = cid

    casualties_by_conflict = defaultdict(list)
    for pid, d in death_event.items():
        if d.data.get("cause") != "war":
            continue
        cid = next((battle_to_conflict[c] for c in d.causes if c in battle_to_conflict), None)
        if cid is not None:
            casualties_by_conflict[cid].append(person_card(pid))

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
            "war_score": round(c.war_score, 3),
            "attacker_losses": c.attacker_losses,
            "defender_losses": c.defender_losses,
            "battle_years": [e.year for e in battles_by_conflict.get(cid, ())],
            "casualties": casualties_by_conflict.get(cid, []),
        })

    centuries = []
    for start in range(1, YEARS + 1, 100):
        end = start + 99
        kinds = Counter(e.kind for e in events if start <= e.year <= end)
        centuries.append({
            "years": [start, end],
            "events": sum(kinds.values()),
            "births": kinds["birth"],
            "deaths": kinds["death"],
            "wars_declared": kinds["war_declared"],
            "battles": kinds["battle"],
            "peace_settlements": kinds["peace_settlement"],
            "churches_founded": kinds["church_founded"],
            "threats_manifested": kinds["ranked_magic_manifested"],
            "threats_resolved": kinds["ranked_threat_resolved"],
            "rank_advancements": kinds["rank_advanced"],
            "top_event_kinds": kinds.most_common(12),
        })

    ranked_people = sorted(
        world.people,
        key=lambda pid: (rank(pid), len(children.get(pid, ())), len(person_events.get(pid, ())), -pid),
        reverse=True,
    )
    notable_people = [person_card(pid) for pid in ranked_people if rank(pid) > 0][:30]

    prolific = sorted(world.people, key=lambda pid: (len(children.get(pid, ())), -pid), reverse=True)
    prolific_people = [person_card(pid) for pid in prolific if children.get(pid)][:20]

    threats = []
    for tid, t in sorted(world.threat_ecology.threats.items()):
        if t.rank < 3:
            continue
        resolution_id = world.threat_ecology.resolutions.get(t.origin_event)
        resolver = None
        if resolution_id is not None:
            ev = event_by_id.get(resolution_id)
            if ev:
                resolver = next((r.id for r in ev.actors if r.kind == "person"), None)
        threats.append({
            "id": tid,
            "kind": t.kind,
            "form": t.form,
            "rank": t.rank,
            "location": t.location,
            "created_year": t.created_year,
            "status": t.status,
            "resolver": resolver,
            "resolver_card": person_card(resolver) if resolver in world.people else None,
        })

    churches = [{
        "id": cid,
        "god": c.god,
        "settlement": c.settlement,
        "founded_year": c.founded_year,
        "authority": round(c.authority, 3),
        "living_followers": sum(1 for pid in c.followers if pid in world.people and world.people[pid].alive),
        "followers_recorded": len(c.followers),
        "clergy_recorded": len(c.clergy),
    } for cid, c in sorted(world.divinity.churches.items())]

    def compact_event(e):
        data = {k: v for k, v in e.data.items() if isinstance(v, (str, int, float, bool)) or v is None}
        return {
            "id": e.id, "year": e.year, "kind": e.kind,
            "actors": [{"kind": r.kind, "id": r.id} for r in e.actors],
            "location": None if e.location is None else {"kind": e.location.kind, "id": e.location.id},
            "causes": list(e.causes), "data": data,
        }

    special = []
    for e in events:
        if e.kind in ("war_declared", "peace_settlement", "god_manifested", "resurrection"):
            special.append(compact_event(e))
        elif e.kind == "rank_advanced" and e.data.get("to_rank", 0) >= 3:
            special.append(compact_event(e))
        elif e.kind in ("ranked_magic_manifested", "ranked_threat_resolved") and e.data.get("rank", e.data.get("threat_rank", 0)) >= 4:
            special.append(compact_event(e))

    meta = {
        "seed": SEED,
        "year": world.year,
        "digest": world.digest(),
        "simulation_seconds": round(analysis_started - started, 3),
        "analysis_seconds": round(perf_counter() - analysis_started, 3),
        "alive": sum(p.alive for p in world.people.values()),
        "people_ever_recorded": len(world.people),
        "events_total": len(events),
        "species_alive": dict(Counter(p.species for p in world.people.values() if p.alive)),
        "settlement_population": dict(Counter(p.settlement for p in world.people.values() if p.alive)),
        "ranks_alive": dict(Counter(RANKS[rank(p.id)] for p in world.people.values() if p.alive)),
        "households_alive": sum(1 for h in world.households.values() if h.alive and any(world.people[pid].alive for pid in h.members if pid in world.people)),
        "conflicts": len(world.warfare.conflicts),
        "churches": len(world.divinity.churches),
        "threats": len(world.threat_ecology.threats),
        "threat_resolutions": len(world.threat_ecology.resolutions),
        "practices": len(world.culture.practices),
        "laws": len(world.culture.laws),
        "relationships": len(world.social.edges),
        "partnerships": len(world.social.partnerships),
        "genealogical_births": len(world.genealogy.parents),
        "trade_routes": len(world.trade_routes),
        "trade_exchanges": sum(r.exchanges for r in world.trade_routes.values()),
        "event_counts_top": Counter(e.kind for e in events).most_common(60),
    }

    emit("REPORT_META", meta)
    emit("WARS_JSON", wars)
    emit("FAMILIES_JSON", families[:12])
    emit("DEEPEST_CHAIN_JSON", deepest_chain)
    emit("DEEPEST_LIVING_CHAIN_JSON", deepest_living_chain)
    emit("NOTABLE_PEOPLE_JSON", notable_people)
    emit("PROLIFIC_PEOPLE_JSON", prolific_people)
    emit("CENTURIES_JSON", centuries)
    emit("THREATS_JSON", threats[:80])
    emit("CHURCHES_JSON", churches)
    emit("SPECIAL_EVENTS_JSON", special[:300])
    emit("DONE", {"ok": True, "elapsed_seconds": round(perf_counter() - started, 3)})


if __name__ == "__main__":
    main()
