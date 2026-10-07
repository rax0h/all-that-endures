from __future__ import annotations

import argparse
import hashlib
from collections import Counter

from ate_sim.advancement import RANKS
from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world


def _pick_index(seed: int, year: int, roll: int, mode: str, size: int) -> int:
    raw = f"{seed}|{year}|{roll}|{mode}".encode()
    token = hashlib.blake2b(raw, digest_size=8).digest()
    return int.from_bytes(token, "big") % size


def _rank_name(rank: int) -> str:
    rank = max(0, min(len(RANKS) - 1, int(rank)))
    return RANKS[rank]


def _fmt_float(value):
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _event_line(event):
    data = []
    for key, value in sorted(event.data.items(), key=lambda item: item[0])[:6]:
        rendered = repr(value)
        if len(rendered) > 70:
            rendered = rendered[:67] + "..."
        data.append(f"{key}={rendered}")
    suffix = "" if not data else " | " + ", ".join(data)
    return f"Y{event.year:>4}  #{event.id:<6} {event.kind}{suffix}"


def _relationship_score(rel):
    return (
        rel.familiarity
        + rel.attachment
        + rel.trust
        + rel.obligation
        + rel.attraction
        + 0.2 * len(rel.shared_history)
        - rel.resentment
    )


def _interesting_score(world, pid):
    person = world.people[pid]
    path = world.advancement.path(pid)
    relationships = tuple(world.social.relationships_for(pid))
    applications = [
        app for app in world.institutions.applications.values()
        if app.person == pid
    ]
    children = tuple(world.genealogy.children.get(pid, ()))
    communities = world.communities.memberships_for(pid)
    skills = [
        skill for (person_id, _domain), skill in world.skills.skills.items()
        if person_id == pid
    ]
    rank = world.advancement.rank(pid)
    return (
        rank * 20
        + (0 if path is None else len(path.abilities))
        + len(relationships) * 2
        + len(applications) * 6
        + len(children) * 2
        + len(communities) * 2
        + sum(1 for skill in skills if skill.level > 0.10)
        + person.age / 20
    )


def choose_person(world, mode, roll, explicit=None):
    living = sorted(p.id for p in world.current_people())
    if not living:
        raise RuntimeError("world has no living people")

    if explicit is not None:
        person = world.people.get(explicit)
        if person is None:
            raise ValueError(f"person {explicit} does not exist")
        return explicit, "explicit"

    if mode == "magic":
        pool = [pid for pid in living if world.advancement.essence_user(pid)]
        if not pool:
            pool = living
    elif mode == "interesting":
        ranked = sorted(
            ((_interesting_score(world, pid), pid) for pid in living),
            reverse=True,
        )
        top = [pid for _score, pid in ranked[:max(1, min(50, len(ranked)))]]
        pool = sorted(top)
    else:
        pool = living

    index = _pick_index(world.seed, world.year, roll, mode, len(pool))
    return pool[index], mode


def dossier(world, pid, selection_mode, roll, timeline_limit):
    p = world.people[pid]
    rank = world.advancement.rank(pid)
    path = world.advancement.path(pid)

    household = world.households.get(p.household)
    parents = [world.people.get(parent) for parent in p.parents]
    child_ids = tuple(world.genealogy.children.get(pid, ()))
    children = [world.people.get(child) for child in child_ids]

    relationships = sorted(
        world.social.relationships_for(pid),
        key=_relationship_score,
        reverse=True,
    )
    partnerships = sorted(
        key for key in world.social.partnerships
        if pid in key
    )

    memberships = world.communities.memberships_for(pid)
    community_rows = []
    for cid, strength in memberships.items():
        community = world.communities.communities.get(cid)
        community_rows.append((cid, strength, community))

    applications = sorted(
        (
            app for app in world.institutions.applications.values()
            if app.person == pid
        ),
        key=lambda app: (app.applied_year, app.id),
    )
    society_memberships = []
    for inst in world.institutions.institutions.values():
        if pid in inst.members:
            society_memberships.append((inst.kind, inst.name, inst.id))

    magic_records = world.institutions.records_for_person(pid)

    skills = sorted(
        (
            skill for (person_id, _domain), skill in world.skills.skills.items()
            if person_id == pid
        ),
        key=lambda skill: (-skill.level, skill.domain),
    )

    motive = world.agency.motives.get(pid)
    wallet = dict(world.currency.wallets.get(pid, {}))
    wallet_value = world.currency.balance_value(pid)
    inventory = world.magic_resources.inventory("person", pid)
    aspiration = world.magic_resources.aspirations.get(pid)

    direct_events = [
        event for event in world.events
        if any(actor.kind == "person" and actor.id == pid for actor in event.actors)
    ]
    event_counts = Counter(event.kind for event in direct_events)
    recent_actions = [
        action for action in world.agency.actions
        if action.person == pid
    ][-8:]

    print("=" * 78)
    print(f"PERSON #{pid}  |  year {world.year}  |  seed {world.seed}")
    print(f"selection: {selection_mode}, roll {roll}")
    print("=" * 78)
    print(
        f"alive={p.alive}  age={p.age}  born=Y{p.born}  species={p.species}  "
        f"occupation={p.occupation}"
    )
    print(
        f"settlement=#{p.settlement}  household=#{p.household}  "
        f"rank={_rank_name(rank)} ({rank})"
    )
    print(
        f"wealth={p.wealth:.3f}  health={p.health:.3f}  "
        f"wallet_value_lesser={wallet_value}"
    )
    print(
        "dispositions: "
        f"temperament={p.temperament:.3f} attachment={p.attachment:.3f} "
        f"curiosity={p.curiosity:.3f} inhibition={p.inhibition:.3f} "
        f"grief={p.grief:.3f} fear={p.fear:.3f}"
    )

    print("\nFAMILY / HOUSEHOLD")
    print("  parents:", ", ".join(
        f"#{parent.id} ({'alive' if parent.alive else 'dead'}, age {parent.age})"
        if parent is not None else "unknown"
        for parent in parents
    ) or "none recorded")
    print("  children:", ", ".join(
        f"#{child.id} ({'alive' if child.alive else 'dead'}, age {child.age})"
        if child is not None else "unknown"
        for child in children
    ) or "none recorded")
    print("  partnerships:", ", ".join(
        f"#{b if a == pid else a}" for a, b in partnerships
    ) or "none recorded")
    if household is not None:
        living_members = [
            member for member in household.members
            if world.people.get(member) is not None and world.people[member].alive
        ]
        print(
            f"  household members={len(household.members)} "
            f"living={living_members} food={household.food:.3f} "
            f"preparedness={household.preparedness:.3f}"
        )

    print("\nMAGIC")
    if path is None:
        print("  no essence path recorded")
    else:
        print("  essences:", ", ".join(path.essences) or "none")
        print(
            f"  confluence: {path.confluence_name or path.confluence or 'none'}  "
            f"abilities={len(path.abilities)}/{path.capacity}"
        )
        for ability in path.abilities:
            flags = []
            if ability.special:
                flags.append("special")
            if ability.aura:
                flags.append("aura")
            tag = "" if not flags else " [" + ",".join(flags) + "]"
            print(
                f"    - {ability.name}{tag} | essence={ability.essence} "
                f"function={ability.function} domain={ability.domain} "
                f"rank={_rank_name(ability.rank)} level={ability.level} "
                f"progress={ability.progress:.3f}"
            )
    if aspiration is not None:
        print(
            f"  aspiration: reason={aspiration.reason} drive={aspiration.drive:.3f} "
            f"urgency={aspiration.urgency:.3f} preparation={aspiration.preparation:.3f}"
        )
    if inventory:
        print("  held magical resources:")
        for resource in inventory:
            print(
                f"    - resource #{resource.id}: {resource.kind} {resource.key} "
                f"rarity={resource.rarity}"
            )
    else:
        print("  held magical resources: none")

    print("\nSOCIETIES / INSTITUTIONS")
    if society_memberships:
        for kind, name, iid in sorted(society_memberships):
            print(f"  member: {name} ({kind}, institution #{iid})")
    else:
        print("  society memberships: none")
    if applications:
        for app in applications:
            print(
                f"  application #{app.id}: {app.society} Y{app.applied_year} "
                f"stage={app.stage} passed={app.passed} "
                f"scores=({app.physical_score:.3f},{app.magical_score:.3f},"
                f"{app.judgment_score:.3f})"
            )
    else:
        print("  applications: none")
    if magic_records:
        for record in magic_records[-5:]:
            print(
                f"  magic record #{record.id}: Y{record.year} "
                f"disclosure={record.disclosure} branch=#{record.branch}"
            )

    print("\nCOMMUNITIES")
    if community_rows:
        for cid, strength, community in community_rows:
            if community is None:
                print(f"  #{cid}: strength={strength:.3f}")
            else:
                print(
                    f"  #{cid}: kind={community.kind} strength={strength:.3f} "
                    f"origin_settlement=#{community.origin_settlement} "
                    f"founded=Y{community.founded}"
                )
    else:
        print("  none recorded")

    print("\nSKILLS")
    shown = [skill for skill in skills if skill.level > 0.051][:12]
    if shown:
        for skill in shown:
            print(
                f"  {skill.domain}: level={skill.level:.3f} "
                f"practice={skill.practice:.3f} teachers={skill.teachers[-5:]}"
            )
    else:
        print("  no developed skills above baseline")

    print("\nCURRENT MOTIVES")
    if motive is None:
        print("  no current motive record")
    else:
        fields = (
            "hunger", "safety", "belonging", "wealth",
            "curiosity", "legacy", "obligation", "status",
        )
        ordered = sorted(
            ((name, getattr(motive, name)) for name in fields),
            key=lambda item: (-item[1], item[0]),
        )
        print("  " + "  ".join(f"{name}={value:.3f}" for name, value in ordered))

    print("\nSTRONGEST RECORDED RELATIONSHIPS")
    if relationships:
        for rel in relationships[:10]:
            other = rel.b if rel.a == pid else rel.a
            other_person = world.people.get(other)
            status = (
                "unknown"
                if other_person is None
                else ("alive" if other_person.alive else "dead")
            )
            print(
                f"  person #{other} ({status}): familiarity={rel.familiarity:.3f} "
                f"trust={rel.trust:.3f} attachment={rel.attachment:.3f} "
                f"obligation={rel.obligation:.3f} resentment={rel.resentment:.3f} "
                f"attraction={rel.attraction:.3f} shared_events={len(rel.shared_history)}"
            )
    else:
        print("  none recorded")

    print("\nRECENT RETAINED ACTIONS")
    if recent_actions:
        for action in recent_actions:
            print(
                f"  Y{action.year}: {action.action} "
                f"(motive={action.motive}, strength={action.strength:.3f})"
            )
    else:
        print("  none retained")

    print("\nDIRECT EVENT HISTORY")
    print(f"  explicit-actor events recorded: {len(direct_events)}")
    if event_counts:
        print(
            "  most common kinds: "
            + ", ".join(f"{kind}={count}" for kind, count in event_counts.most_common(12))
        )
    for event in direct_events[-timeline_limit:]:
        print("  " + _event_line(event))

    print("\nCOVERAGE / HONEST LIMITS")
    print(
        "  This is current authoritative state plus events where this person is an "
        "explicit actor. It is not an inferred autobiography."
    )
    print(
        "  Names, complete childhood, subjective memories, self-concept, and many "
        "ordinary daily events are not modeled yet, so the explorer does not invent them."
    )
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a world and inspect one recorded person without inventing biography."
    )
    parser.add_argument("--seed", type=int, default=843000)
    parser.add_argument("--years", type=int, default=250)
    parser.add_argument("--roll", type=int, default=1)
    parser.add_argument(
        "--mode",
        choices=("random", "magic", "interesting"),
        default="random",
    )
    parser.add_argument("--person-id", type=int)
    parser.add_argument("--timeline", type=int, default=18)
    args = parser.parse_args()

    if args.years < 0:
        raise SystemExit("--years must be nonnegative")
    if args.timeline < 1:
        raise SystemExit("--timeline must be positive")

    world = generate_world(args.seed)
    Simulation(world).run(args.years)
    pid, selected = choose_person(
        world, args.mode, args.roll, explicit=args.person_id
    )
    dossier(world, pid, selected, args.roll, args.timeline)


if __name__ == "__main__":
    main()
