from __future__ import annotations

from collections import Counter, defaultdict, deque
import json

from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.advancement import RANKS

SEED = 843017
YEARS = 1000


def pid_from_event(event):
    for ref in event.actors:
        if ref.kind == "person":
            return ref.id
    return None


def main():
    world = generate_world(SEED, mature=True)
    Simulation(world).run(YEARS)
    events = list(world.events)

    deaths = defaultdict(list)
    births = defaultdict(list)
    person_events = defaultdict(list)
    for e in events:
        for ref in e.actors:
            if ref.kind == "person":
                person_events[ref.id].append(e)
        if e.kind == "death":
            pid = pid_from_event(e)
            if pid is not None:
                deaths[pid].append(e)
        elif e.kind == "birth":
            pid = pid_from_event(e)
            if pid is not None:
                births[pid].append(e)

    def death_year(pid):
        return deaths[pid][-1].year if deaths.get(pid) else None

    def rank(pid):
        return world.advancement.rank(pid)

    def person_card(pid):
        p = world.people[pid]
        path = world.advancement.path(pid)
        return {
            "id": pid,
            "born": p.born,
            "death_year": death_year(pid),
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

    roots = [pid for pid in world.people if not parents.get(pid)]

    def descendant_set(root):
        seen = set()
        stack = list(children.get(root, ()))
        while stack:
            pid = stack.pop()
            if pid in seen:
                continue
            seen.add(pid)
            stack.extend(children.get(pid, ()))
        return seen

    def best_chain_from(root, require_living=False):
        best = [root]
        stack = [(root, [root])]
        while stack:
            pid, path = stack.pop()
            if (not require_living or world.people[pid].alive) and len(path) > len(best):
                best = path
            for child in children.get(pid, ()):
                if child in world.people:
                    stack.append((child, path + [child]))
        return best

    families = []
    for root in roots:
        desc = descendant_set(root)
        if not desc:
            continue
        living = [d for d in desc if world.people[d].alive]
        ranked = [d for d in desc if rank(d) > 0]
        war_dead = [
            d for d in desc
            if any(e.data.get("cause") == "war" for e in deaths.get(d, ()))
        ]
        species = sorted({world.people[d].species for d in desc | {root}})
        chain = best_chain_from(root)
        living_chain = best_chain_from(root, require_living=True) if living else []
        families.append({
            "root": root,
            "descendants": len(desc),
            "living_descendants": len(living),
            "ranked_descendants": len(ranked),
            "war_dead_descendants": len(war_dead),
            "species": species,
            "deepest_generations": len(chain) - 1,
            "deepest_chain_ids": chain,
            "living_chain_ids": living_chain,
            "root_card": person_card(root),
        })
    families.sort(key=lambda f: (f["descendants"], f["deepest_generations"], f["living_descendants"]), reverse=True)

    deepest_family = max(families, key=lambda f: f["deepest_generations"], default=None)
    deepest_chain = [person_card(pid) for pid in deepest_family["deepest_chain_ids"]] if deepest_family else []
    living_families = [f for f in families if f["living_descendants"]]
    deepest_living = max(living_families, key=lambda f: len(f["living_chain_ids"]), default=None)
    deepest_living_chain = [person_card(pid) for pid in deepest_living["living_chain_ids"]] if deepest_living else []

    battles_by_conflict = defaultdict(list)
    for e in events:
        if e.kind == "battle":
            battles_by_conflict[e.data.get("conflict")].append(e)

    wars = []
    for cid, c in sorted(world.warfare.conflicts.items()):
        battle_ids = {e.id for e in battles_by_conflict.get(cid, ())}
        casualties = []
        for pid, ds in deaths.items():
            for d in ds:
                if d.data.get("cause") == "war" and any(cause in battle_ids for cause in d.causes):
                    casualties.append(person_card(pid))
                    break
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
            "casualties": casualties,
        })

    significant_kinds = {
        "war_declared", "peace_settlement", "church_founded", "god_manifested",
        "resurrection", "ranked_magic_manifested", "ranked_threat_resolved",
        "ranked_threat_escalated", "settlement_founded", "household_migrated",
        "society_trainee_graduated", "rank_advanced", "death", "birth",
    }

    def major_event(e):
        if e.kind not in significant_kinds:
            return False
        if e.kind == "rank_advanced":
            return e.data.get("to_rank", 0) >= 3
        if e.kind in ("ranked_magic_manifested", "ranked_threat_resolved"):
            return e.data.get("rank", e.data.get("threat_rank", 0)) >= 4
        if e.kind in ("death", "birth", "society_trainee_graduated"):
            return False
        return True

    def compact_event(e):
        data = {}
        for k, v in e.data.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                data[k] = v
        return {
            "id": e.id,
            "year": e.year,
            "kind": e.kind,
            "actors": [{"kind": r.kind, "id": r.id} for r in e.actors],
            "location": None if e.location is None else {"kind": e.location.kind, "id": e.location.id},
            "causes": list(e.causes),
            "data": data,
        }

    major_events = [compact_event(e) for e in events if major_event(e)]

    centuries = []
    for start in range(1, YEARS + 1, 100):
        end = min(YEARS, start + 99)
        es = [e for e in events if start <= e.year <= end]
        kinds = Counter(e.kind for e in es)
        centuries.append({
            "years": [start, end],
            "events": len(es),
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

    rank_counts = Counter(RANKS[rank(p.id)] for p in world.people.values() if p.alive)
    species_counts = Counter(p.species for p in world.people.values() if p.alive)
    settlement_counts = Counter(p.settlement for p in world.people.values() if p.alive)

    ranked_people = sorted(
        world.people,
        key=lambda pid: (
            rank(pid),
            len(world.genealogy.children.get(pid, ())),
            len(person_events.get(pid, ())),
            -pid,
        ),
        reverse=True,
    )
    notable_people = [person_card(pid) for pid in ranked_people[:20] if rank(pid) > 0]

    prolific = sorted(
        world.people,
        key=lambda pid: (len(children.get(pid, ())), len(descendant_set(pid)), -pid),
        reverse=True,
    )
    prolific_people = [
        {
            **person_card(pid),
            "descendant_count": len(descendant_set(pid)),
        }
        for pid in prolific[:15] if children.get(pid)
    ]

    war_dead = []
    for pid, ds in deaths.items():
        if any(e.data.get("cause") == "war" for e in ds):
            war_dead.append(person_card(pid))

    threat_rows = []
    for tid, t in sorted(world.threat_ecology.threats.items()):
        if t.rank >= 3:
            resolution_id = world.threat_ecology.resolutions.get(t.origin_event)
            resolver = None
            if resolution_id is not None:
                ev = next((e for e in events if e.id == resolution_id), None)
                if ev:
                    resolver = pid_from_event(ev)
            threat_rows.append({
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

    churches = []
    for cid, c in sorted(world.divinity.churches.items()):
        churches.append({
            "id": cid,
            "god": c.god,
            "settlement": c.settlement,
            "founded_year": c.founded_year,
            "authority": round(c.authority, 3),
            "living_followers": sum(1 for pid in c.followers if pid in world.people and world.people[pid].alive),
            "followers_recorded": len(c.followers),
            "clergy_recorded": len(c.clergy),
        })

    god_manifestations = [compact_event(e) for e in events if e.kind == "god_manifested"]
    resurrections = [compact_event(e) for e in events if e.kind == "resurrection"]

    event_counts = Counter(e.kind for e in events)
    report = {
        "seed": SEED,
        "year": world.year,
        "digest": world.digest(),
        "population": {
            "alive": sum(p.alive for p in world.people.values()),
            "people_ever_recorded": len(world.people),
            "species_alive": dict(species_counts),
            "settlements_alive_population": dict(settlement_counts),
            "ranks_alive": dict(rank_counts),
            "households_alive": sum(1 for h in world.households.values() if h.alive and any(world.people[pid].alive for pid in h.members if pid in world.people)),
        },
        "events_total": len(events),
        "event_counts_top": event_counts.most_common(50),
        "wars": wars,
        "war_deaths": war_dead,
        "families_top": families[:10],
        "deepest_chain": deepest_chain,
        "deepest_living_chain": deepest_living_chain,
        "notable_ranked_people": notable_people,
        "prolific_people": prolific_people,
        "major_events": major_events[:250],
        "major_events_truncated": len(major_events) > 250,
        "centuries": centuries,
        "rank3plus_threats": threat_rows,
        "churches": churches,
        "god_manifestations": god_manifestations,
        "resurrections": resurrections,
        "counts": {
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
        },
    }
    print("HISTORY_REPORT_JSON=" + json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
