"""Read-only views of a world already in memory.

Nothing here calls methods that create relationships, wallets, or skills.
Population over time is replayed from founders and the event ledger, then
checked against the living set. If that check fails the series is withheld.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from .engine_loader import import_engine
from .values import calculated, measured, unavailable

_ENGINE = None


def engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = import_engine()
    return _ENGINE


def _actor(event, index=0):
    if len(event.actors) <= index:
        return None
    actor = event.actors[index]
    if getattr(actor, "kind", None) != "person":
        return None
    return actor.id


def population_replay(world) -> dict:
    """End-of-year population from recorded births, deaths, and resurrections."""
    founders = {person.id for person in world.people.values() if person.born <= 0}
    alive = set(founders)
    births: Counter = Counter()
    deaths: Counter = Counter()
    resurrections: Counter = Counter()
    warnings = []
    events = world.events
    index = 0
    points_pop = []
    points_birth = []
    points_death = []
    points_res = []
    for year in range(0, world.year + 1):
        while index < len(events) and events[index].year < year:
            warnings.append(f"event {events[index].id} is dated {events[index].year}, before replay year {year}")
            index += 1
            if len(warnings) > 5:
                break
        while index < len(events) and events[index].year == year:
            event = events[index]
            index += 1
            if event.kind == "birth":
                births[year] += 1
                person_id = _actor(event)
                if person_id is not None:
                    alive.add(person_id)
            elif event.kind == "death":
                deaths[year] += 1
                person_id = _actor(event)
                if person_id is not None:
                    alive.discard(person_id)
            elif event.kind == "resurrection":
                resurrections[year] += 1
                person_id = _actor(event)
                if person_id is not None:
                    alive.add(person_id)
        points_pop.append({"year": year, "value": len(alive)})
        points_birth.append({"year": year, "value": births[year]})
        points_death.append({"year": year, "value": deaths[year]})
        points_res.append({"year": year, "value": resurrections[year]})
    if index < len(events):
        warnings.append(f"{len(events) - index} events are dated after world.year {world.year}")
    living = {person.id for person in world.people.values() if person.alive}
    check_ok = alive == living and not warnings
    method = (
        "end-of-year replay: people with born<=0, then birth, death, and resurrection events in archive order"
    )
    population = calculated(points_pop, method) if check_ok else unavailable(
        "replay did not match the living set or the event archive was not in year order; series withheld. "
        + ("; ".join(warnings[:3]) if warnings else f"replay {len(alive)} vs living {len(living)}")
    )
    if check_ok:
        population["checked_against"] = "set of living person ids"
        population["check_ok"] = True
    return {
        "population": population,
        "births": measured(points_birth, "count of events with kind birth"),
        "deaths": measured(points_death, "count of events with kind death"),
        "resurrections": measured(points_res, "count of events with kind resurrection"),
        "alive_ids": alive,
        "warnings": warnings,
        "check_ok": check_ok,
    }


def _median(values: list[float]):
    if not values:
        return unavailable("no values")
    return calculated(statistics.median(values), "median of the measured values in this snapshot")


def _histogram(values: list[float], edges: list[tuple[float, float, str]]) -> dict:
    counts = {label: 0 for _, _, label in edges}
    for value in values:
        for low, high, label in edges:
            if low <= value <= high:
                counts[label] += 1
                break
    return calculated(
        [{"label": label, "count": counts[label]} for _, _, label in edges],
        "bins of measured values; bin edges are a display grouping",
    )


AGE_BINS = [(0, 0, "0"), (1, 17, "1–17"), (18, 39, "18–39"), (40, 59, "40–59"), (60, 79, "60–79"), (80, 10**9, "80+")]
WEALTH_BINS = [(0, 0, "0"), (0.0001, 10, "0–10"), (10, 50, "10–50"), (50, 200, "50–200"), (200, 10**12, "200+")]


def build_people_index(world) -> list[dict]:
    ranks = engine()["RANKS"]
    rows = []
    for person in world.people.values():
        path = world.advancement.path(person.id)
        if path is not None and path.abilities:
            advancement_rank = min(ability.rank for ability in path.abilities)
            rank_name = ranks[advancement_rank] if 0 <= advancement_rank < len(ranks) else str(advancement_rank)
        else:
            advancement_rank = None
            rank_name = None
        rows.append({
            "id": person.id,
            "born": person.born,
            "age": person.age,
            "alive": person.alive,
            "species": person.species,
            "occupation": person.occupation,
            "settlement": person.settlement,
            "household": person.household,
            "wealth": person.wealth,
            "health": person.health,
            "stored_rank": person.rank,
            "essence_user": path is not None,
            "advancement_rank": advancement_rank,
            "advancement_rank_name": rank_name,
        })
    rows.sort(key=lambda row: row["id"])
    return rows


def build_event_index(world) -> dict[int, list[int]]:
    index: dict[int, list[int]] = defaultdict(list)
    for event in world.events:
        seen = set()
        for actor in event.actors:
            if actor.kind == "person" and actor.id not in seen:
                seen.add(actor.id)
                index[actor.id].append(event.id)
    return index


def living_household_count(world) -> int:
    living = {person.id for person in world.people.values() if person.alive}
    count = 0
    for household in world.households.values():
        if household.alive and any(member in living for member in household.members):
            count += 1
    return count


def overview_from_world(world, series: dict, source: dict) -> dict:
    living = [person for person in world.people.values() if person.alive]
    ranks = engine()["RANKS"]
    rank_counts: Counter = Counter()
    non_users = 0
    for person in living:
        path = world.advancement.path(person.id)
        if path is None or not path.abilities:
            non_users += 1
            continue
        rank_counts[min(ability.rank for ability in path.abilities)] += 1
    species = Counter(person.species for person in living)
    occupations = Counter(person.occupation for person in living)
    ages = [person.age for person in living]
    wealths = [person.wealth for person in living]
    causes: Counter = Counter()
    kinds: Counter = Counter()
    for event in world.events:
        kinds[event.kind] += 1
        if event.kind == "death":
            causes[str(event.data.get("cause") or "not recorded")] += 1
    settlements = []
    living_by = Counter(person.settlement for person in living)
    for settlement in sorted(world.settlements.values(), key=lambda item: item.id):
        settlements.append({
            "id": settlement.id,
            "x": settlement.x,
            "y": settlement.y,
            "living": measured(living_by[settlement.id], "count of living people whose settlement id equals this id"),
            "households_recorded": measured(len(settlement.households), "length of settlement.households"),
            "food_stock": measured(settlement.food_stock, "settlement.food_stock"),
            "defense": measured(settlement.defense, "settlement.defense"),
            "irrigation": measured(settlement.irrigation, "settlement.irrigation"),
            "roads": measured(settlement.roads, "settlement.roads"),
            "prosperity": measured(settlement.prosperity, "settlement.prosperity"),
            "name": unavailable("settlements have coordinates and ids; the simulation does not store a place name"),
        })
    cells = [
        {
            "x": cell.x,
            "y": cell.y,
            "elevation": round(cell.elevation, 6),
            "moisture": round(cell.moisture, 6),
            "fertility": round(cell.fertility, 6),
            "forest": round(cell.forest, 6),
            "hazard": round(cell.hazard, 6),
        }
        for cell in world.cells.values()
    ]
    minted = {str(key): int(value) for key, value in world.currency.minted.items()}
    magical_items = sum(1 for item in world.materials.items.values() if getattr(item, "magical", False))
    available_magic = sum(1 for resource in world.magic_resources.resources.values() if resource.consumed_year is None)
    return {
        "source": source,
        "year": measured(world.year, "world.year"),
        "seed": measured(world.seed, "world.seed"),
        "population": measured(len(living), "count of people with alive true"),
        "people_total": measured(len(world.people), "len(world.people)"),
        "households_total": measured(len(world.households), "len(world.households)"),
        "living_households": calculated(
            living_household_count(world),
            "household.alive and at least one living member; same definition as run_long_history.snapshot",
        ),
        "settlement_count": measured(len(world.settlements), "len(world.settlements)"),
        "events": measured(len(world.events), "len(world.events)"),
        "relationships": measured(len(world.social.edges), "len(social.edges); social.get is not called"),
        "essence_users_living": measured(
            sum(1 for person in living if world.advancement.path(person.id) is not None),
            "living people present in advancement.paths",
        ),
        "series": {key: series[key] for key in ("population", "births", "deaths", "resurrections")},
        "species": measured(
            [{"species": name, "count": count} for name, count in sorted(species.items())],
            "living people grouped by person.species",
        ),
        "occupations": measured(
            [{"occupation": name, "count": count} for name, count in occupations.most_common()],
            "living people grouped by person.occupation",
        ),
        "advancement_ranks": calculated(
            [
                {"rank": rank, "name": ranks[rank] if 0 <= rank < len(ranks) else str(rank), "count": rank_counts[rank]}
                for rank in sorted(rank_counts)
            ],
            "min recorded ability rank per living essence user; AdvancementState.rank rule, people without abilities excluded",
        ),
        "living_without_essence_path": measured(non_users, "living people with no abilities on an essence path"),
        "age": {
            "min": measured(min(ages), "minimum living person.age") if ages else unavailable("no living people"),
            "max": measured(max(ages), "maximum living person.age") if ages else unavailable("no living people"),
            "median": _median(ages),
            "histogram": _histogram(ages, AGE_BINS) if ages else unavailable("no living people"),
        },
        "wealth": {
            "sum": measured(sum(wealths), "sum of living person.wealth") if wealths else unavailable("no living people"),
            "median": _median(wealths),
            "histogram": _histogram(wealths, WEALTH_BINS) if wealths else unavailable("no living people"),
        },
        "death_causes": measured(
            [{"cause": name, "count": count} for name, count in causes.most_common()],
            "death event data field cause",
        ),
        "event_kinds": measured(
            [{"kind": name, "count": count} for name, count in kinds.most_common()],
            "count of events by kind",
        ),
        "settlements": settlements,
        "cells": measured(cells, "stored cell elevation, moisture, fertility, forest, and hazard, rounded to 6 decimal places"),
        "historical_settlement_population": unavailable(
            "settlement membership is stored for the current year only; past residence is not a retained series"
        ),
        "economy": {
            "material_lots": measured(len(world.materials.lots), "len(materials.lots)"),
            "crafted_items": measured(len(world.materials.items), "len(materials.items)"),
            "magical_items": measured(magical_items, "items with magical true"),
            "magic_resources": measured(len(world.magic_resources.resources), "len(magic_resources.resources)"),
            "magic_resources_available": measured(available_magic, "resources whose consumed_year is None"),
            "ranked_coin_minted": measured(minted, "currency.minted") if minted else unavailable("currency.minted is empty"),
            "properties": measured(len(world.economy.property), "len(economy.property)"),
        },
        "lifespan_note": "Completed lifespans come from death events. Living people have age so far; their lifespan is not known.",
        "digest": unavailable("canonical digest is not computed during inspection; use Verify on a checkpoint or the performance action"),
    }


def _compact_event(event) -> dict:
    location = None
    if event.location is not None:
        location = {"kind": event.location.kind, "id": event.location.id}
    return {
        "id": event.id,
        "year": event.year,
        "kind": event.kind,
        "layer": event.layer.value if hasattr(event.layer, "value") else str(event.layer),
        "actors": [{"kind": actor.kind, "id": actor.id} for actor in event.actors],
        "location": location,
        "causes": list(event.causes),
        "data": event.data,
    }


def person_detail(world, person_id: int, event_ids: list[int], by_id: dict) -> dict:
    person = world.people.get(person_id)
    if person is None:
        return {"error": f"person {person_id} is not in this world"}
    beliefs = tuple(sorted(
        (claim, confidence)
        for (pid, claim), confidence in world.knowledge.beliefs.items()
        if pid == person_id
    ))
    view = engine()["from_person"](person, beliefs)
    household = world.households.get(person.household)
    skills = []
    for (owner, domain), skill in world.skills.skills.items():
        if owner == person_id:
            skills.append({
                "domain": domain,
                "level": measured(skill.level, "skill.level"),
                "practice": measured(skill.practice, "skill.practice"),
                "teachers": list(skill.teachers),
                "provenance_events": len(skill.provenance),
            })
    skills.sort(key=lambda row: row["domain"])
    path = world.advancement.path(person_id)
    if path is None:
        essence = unavailable("this person has no entry in advancement.paths")
    else:
        essence = measured({
            "base_essences": list(path.base_essences),
            "confluence": path.confluence,
            "confluence_name": path.confluence_name,
            "abilities": [
                {
                    "name": ability.name,
                    "essence": ability.essence,
                    "source": ability.source,
                    "function": ability.function,
                    "domain": ability.domain,
                    "awakened_year": ability.awakened_year,
                    "rank": ability.rank,
                    "level": ability.level,
                    "progress": ability.progress,
                    "special": ability.special,
                    "aura": ability.aura,
                }
                for ability in path.abilities
            ],
        }, "advancement path recorded on this world")
    relationships = []
    for (left, right), edge in world.social.edges.items():
        if person_id not in (left, right):
            continue
        other = right if left == person_id else left
        relationships.append({
            "person": other,
            "familiarity": edge.familiarity,
            "trust": edge.trust,
            "attachment": edge.attachment,
            "obligation": edge.obligation,
            "resentment": edge.resentment,
            "attraction": edge.attraction,
            "shared_history_count": len(edge.shared_history),
            "shared_history_tail": list(edge.shared_history[-12:]),
        })
    relationships.sort(key=lambda row: (-row["familiarity"], row["person"]))
    partners = []
    for (left, right), event_id in world.social.partnerships.items():
        if person_id in (left, right):
            partners.append({
                "person": right if left == person_id else left,
                "formed_event": event_id,
            })
    genealogy_parents = list(world.genealogy.parents.get(person_id, ()))
    children = list(world.genealogy.children.get(person_id, ()))
    descendants = []
    frontier = list(children)
    seen = {person_id}
    while frontier and len(descendants) < 200:
        current = frontier.pop(0)
        if current in seen:
            continue
        seen.add(current)
        descendants.append(current)
        frontier.extend(world.genealogy.children.get(current, ()))
    truncated_descendants = bool(frontier)
    events = []
    for event_id in event_ids[-120:]:
        event = by_id.get(event_id)
        if event is not None:
            events.append(_compact_event(event))
    death_ages = []
    for event_id in event_ids:
        event = by_id.get(event_id)
        if event is not None and event.kind == "death":
            death_ages.append(event.data.get("age"))
    if person.alive:
        lifespan = unavailable("person is alive; age is years so far, not a completed lifespan")
    elif death_ages:
        latest_age = death_ages[-1]
        lifespan = (
            measured(latest_age, "age field on the latest death event indexed for this person")
            if latest_age is not None
            else unavailable("a death event exists but it has no age field")
        )
    else:
        lifespan = unavailable("no death event in the retained event index for this person")
    coins = world.currency.wallets.get(person_id)
    if coins is None:
        wallet = unavailable("no wallet entry is stored for this person; an empty wallet was not invented")
    else:
        wallet = measured(dict(coins), "currency.wallets entry; wallet() was not called")
    communities = [
        {"community": cid, "strength": strength}
        for (pid, cid), strength in world.communities.memberships.items()
        if pid == person_id
    ]
    capabilities = {
        name: unavailable("personhood capabilities are unmodeled; None means unmodeled, not zero")
        for name in (
            "reasoning", "learning", "working_memory", "long_term_memory", "verbal", "spatial",
            "numerical", "practical", "social_perception", "creativity", "attention",
        )
    }
    return {
        "id": person.id,
        "name": unavailable("people do not have personal names in the current simulation state"),
        "identity": {
            "born": measured(person.born, "person.born"),
            "age": measured(person.age, "person.age at this world year"),
            "lifespan": lifespan,
            "alive": measured(person.alive, "person.alive"),
            "species": measured(person.species, "person.species"),
            "occupation": measured(person.occupation, "person.occupation"),
            "settlement": measured(person.settlement, "person.settlement"),
            "household": measured(person.household, "person.household"),
            "stored_rank": measured(person.rank, "person.rank field, distinct from ability rank"),
            "health": measured(person.health, "person.health"),
            "wealth": measured(person.wealth, "person.wealth"),
        },
        "dispositions": measured({
            "temperament": person.temperament,
            "attachment": person.attachment,
            "curiosity": person.curiosity,
            "inhibition": person.inhibition,
        }, "person fields via personhood.Dispositions"),
        "emotions": measured({"grief": person.grief, "fear": person.fear}, "person.grief and person.fear"),
        "capabilities": capabilities,
        "subjective": {
            "beliefs": measured(
                [{"claim": claim, "confidence": confidence} for claim, confidence in view.subjective.beliefs],
                "knowledge.beliefs rows for this person",
            ),
            "coverage": view.subjective.coverage,
            "memories": unavailable(view.subjective.coverage),
        },
        "household": None if household is None else {
            "id": household.id,
            "settlement": household.settlement,
            "alive": household.alive,
            "lineage": household.lineage,
            "member_count": len(household.members),
        },
        "family": {
            "parents_on_person": measured(list(person.parents), "person.parents"),
            "parents_in_genealogy": measured(genealogy_parents, "genealogy.parents")
            if person_id in world.genealogy.parents or genealogy_parents
            else unavailable("genealogy.parents has no row for this person"),
            "children": measured(children, "genealogy.children"),
            "descendants": calculated(descendants, "breadth-first walk of genealogy.children, capped at 200"),
            "descendants_truncated": truncated_descendants,
            "ancestors": calculated(
                sorted(world.genealogy.ancestors(person_id)),
                "Genealogy.ancestors depth 8",
            ),
        },
        "skills": skills,
        "essence": essence,
        "relationships": measured(relationships, "social.edges incident to this person; social.get was not called"),
        "partnerships": measured(partners, "social.partnerships keys containing this person, historical included"),
        "communities": measured(communities, "communities.memberships rows for this person"),
        "wallet": wallet,
        "events": events,
        "events_truncated": len(event_ids) > 120,
        "events_indexed": len(event_ids),
    }


def household_detail(world, household_id: int) -> dict:
    household = world.households.get(household_id)
    if household is None:
        return {"error": f"household {household_id} is not in this world"}
    members = []
    for person_id in household.members:
        person = world.people.get(person_id)
        if person is None:
            members.append({"id": person_id, "record": unavailable("member id is not in world.people")})
        else:
            members.append({
                "id": person.id,
                "alive": person.alive,
                "age": person.age,
                "species": person.species,
                "occupation": person.occupation,
            })
    return {
        "id": household.id,
        "settlement": measured(household.settlement, "household.settlement"),
        "alive": measured(household.alive, "household.alive"),
        "lineage": measured(household.lineage, "household.lineage"),
        "wealth": measured(household.wealth, "household.wealth"),
        "food": measured(household.food, "household.food"),
        "preparedness": measured(household.preparedness, "household.preparedness"),
        "members": measured(members, "household.members joined to person records"),
    }


def timeline(world, year: int, kind: str | None, layer: str | None, limit: int, offset: int) -> dict:
    if limit < 1 or limit > 400:
        limit = 200
    if offset < 0:
        offset = 0
    matched = []
    for event in world.events_between(year, year):
        event_layer = event.layer.value if hasattr(event.layer, "value") else str(event.layer)
        if kind and event.kind != kind:
            continue
        if layer and event_layer != layer:
            continue
        matched.append(_compact_event(event))
    page = matched[offset:offset + limit]
    return {
        "year": year,
        "world_year": world.year,
        "count": len(matched),
        "offset": offset,
        "limit": limit,
        "truncated": offset + limit < len(matched),
        "events": measured(page, "world.events_between for this year, then kind and layer filters"),
        "coverage": "events whose year field equals the selected year; not an inferred chronicle",
    }


def event_detail(world, event_id: int, by_id: dict) -> dict:
    event = by_id.get(event_id)
    if event is None:
        return {"error": f"event {event_id} is not in this world"}
    chain = engine()["query"].causal_chain(world, event_id)
    capped = chain[:40]
    return {
        "event": measured(_compact_event(event), "event record"),
        "causal_ancestors": calculated(
            [_compact_event(by_id[item]) for item in capped if item in by_id],
            "ate_sim.query.causal_chain, capped at 40 events",
        ),
        "causal_truncated": len(chain) > 40,
    }
