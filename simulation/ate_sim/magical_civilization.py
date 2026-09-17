from __future__ import annotations

from .core_types import layer_ref
from .magic_resources import _aspiration, _make_resource, _wanted_resources, _transfer_to_seeker, _wants, absorb_essence_resource, use_awakening_stone
from .materials import _produce_lot, _craft_once
from .institutions import apply_for_society, full_essence_user

EXPEDITION_ACTIVITY_RATE = .62


def _living(world, sid):
    return sorted((p for p in world.current_people() if p.alive and p.age >= 16 and p.settlement == sid), key=lambda p: p.id)


def _practitioners(world, people):
    return [p for p in people if world.advancement.path(p.id) is not None]


def _institutional_capacity(world, sid):
    adventure = world.institutions.branch_for('adventure_society', sid)
    magic = world.institutions.branch_for('magic_society', sid)
    return adventure, magic


def _review_magic_demand(world, people, adventure, magic):
    """Let existing aspirations respond to a changing magical civilization."""
    user_ids = {p.id for p in people if world.advancement.essence_user(p.id)}
    for p in people:
        a = _aspiration(world, p)
        path = world.advancement.path(p.id)
        if path is not None:
            a.desired_base_essences = max(a.desired_base_essences, min(3, len(path.base_essences) + 1))
            a.desired_abilities = max(a.desired_abilities, min(20, max(5, len(path.abilities) + 2)))
        family = sum(1 for x in p.parents if x in user_ids)
        contacts = sum(1 for x in world.social.neighbors(p.id) if x in user_ids)
        occupation_need = p.occupation in ('adventurer', 'guard', 'hunter', 'soldier', 'farmer', 'crafter', 'smith', 'healer', 'merchant', 'scholar', 'builder', 'architect')
        settlement = world.settlements[p.settlement]
        cell = world.cells[(settlement.x, settlement.y)]
        pressure = max(cell.hazard, settlement.memory.get('monster_surge', 0.0))
        institutional_access = adventure is not None or magic is not None
        reason = None
        if family or contacts >= 2: reason = 'social magical exposure'
        elif occupation_need and institutional_access: reason = 'occupational capability'
        elif pressure >= .45 and institutional_access: reason = 'local magical pressure'
        if reason is None: continue
        a.drive = min(1., max(a.drive, .34 + .05 * min(3, family + contacts) + (.06 if occupation_need else 0.)))
        a.urgency = min(1., max(a.urgency, .30 + .28 * pressure + (.10 if occupation_need else 0.)))
        a.desired_base_essences = max(a.desired_base_essences, 1)
        a.desired_abilities = max(a.desired_abilities, 5)
        if a.reason == 'capability' or a.desired_base_essences == 1: a.reason = reason
        if a.adventurer_aspiration or (occupation_need and (family + contacts) >= 2 and a.drive >= .44):
            a.completion_goal = True; a.desired_base_essences = 3; a.desired_abilities = 20


def _expedition_step(world, rng, sid, people, users, adventure, magic):
    if not people: return
    ambient = world.ambient_magic.field(sid).level
    settlement = world.settlements[sid]; cell = world.cells[(settlement.x, settlement.y)]
    aspirants = [p for p in people if _aspiration(world, p).desired_base_essences > 0]
    adventurer_aspirants = [p for p in aspirants if _aspiration(world, p).adventurer_aspiration]
    member_count = 0 if adventure is None else sum(1 for p in people if p.id in world.institutions.institution_by_kind('adventure_society').members)
    institutional = (0. if adventure is None else 2.0 * adventure.authority) + (0. if magic is None else 1.5 * magic.authority)
    field_capacity = len(users) + len(adventurer_aspirants) * .45 + len(aspirants) * .08 + member_count * 1.5 + institutional
    if field_capacity <= 0: return
    rr = rng.stream('magical_field_economy', world.year, sid)
    pressure = max(0., ambient - .30) + .35 * cell.hazard + .08 * min(10, field_capacity)
    attempts = min(8, int(EXPEDITION_ACTIVITY_RATE * pressure * (1.2 + len(people) / 90.0)))
    if attempts <= 0: return
    candidates = sorted(users + [p for p in adventurer_aspirants if p not in users], key=lambda p: (_aspiration(world, p).risk_tolerance, _aspiration(world, p).preparation, p.health, -p.id), reverse=True)
    if not candidates: candidates = sorted(aspirants, key=lambda p: (_aspiration(world, p).risk_tolerance, _aspiration(world, p).preparation, p.health, -p.id), reverse=True)
    if not candidates: return
    Layer, Ref = layer_ref()
    for n in range(attempts):
        erng = rng.stream('magical_expedition', world.year, sid * 100 + n); leader = candidates[n % len(candidates)]; aspiration = _aspiration(world, leader)
        readiness = .20 + .22 * aspiration.preparation + .18 * aspiration.risk_tolerance + .08 * world.advancement.rank(leader.id)
        if adventure is not None: readiness += .14
        if magic is not None: readiness += .08
        danger = .08 + .22 * cell.hazard + .10 * max(0., ambient - .8)
        event = world.emit('magical_expedition', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), society_branch=None if adventure is None else adventure.id, ambient_magic=round(ambient, 3), readiness=round(readiness, 3), danger=round(danger, 3))
        if erng.random() > min(.86, readiness + .16 * ambient):
            world.emit('magical_expedition_returned_empty', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), (event.id,)); continue
        incomplete = sum(1 for p in users if len(world.advancement.path(p.id).abilities) < world.advancement.path(p.id).capacity)
        stone_share = min(.68, .38 + .025 * min(10, incomplete) + (.08 if magic is not None else 0.))
        kind = 'awakening_stone' if erng.random() < stone_share else 'essence'
        found = _make_resource(world, erng, sid, leader, kind, event.id, 'organized magical expedition')
        world.emit('magical_expedition_resource_recovered', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), (event.id, found.origin_event), resource=found.id, resource_kind=found.kind, key=found.key)
        aspiration.preparation = min(1., aspiration.preparation + .025)


def _kinship_circulation(world, sid, people):
    """Pass useful inherited/surplus magic through families before it stagnates.

    This is not a prevalence controller: it creates no resources and changes no
    aspirations. It only lets a willing holder give an existing resource to a
    local household member or direct parent/child who already wants it.

    Kin candidates are indexed once per settlement pass. This preserves the old
    ascending-person ordering without rescanning every adult for every holder.
    """
    Layer, Ref = layer_ref(); by_id = {p.id: p for p in people}; by_household = {}; children = {}
    for q in people:
        by_household.setdefault(q.household, []).append(q)
        for parent in q.parents:
            if parent in by_id: children.setdefault(parent, []).append(q)
    for holder in people:
        held = world.magic_resources.inventory('person', holder.id)
        if not held: continue
        surplus = _wanted_resources(world, holder, held, wanted=False)
        if not surplus: continue
        kin_by_id = {q.id: q for q in by_household.get(holder.household, ()) if q.id != holder.id}
        for parent in holder.parents:
            q = by_id.get(parent)
            if q is not None and q.id != holder.id: kin_by_id[q.id] = q
        for q in children.get(holder.id, ()):
            if q.id != holder.id: kin_by_id[q.id] = q
        kin = [kin_by_id[pid] for pid in sorted(kin_by_id)]
        if not kin: continue
        for resource in surplus:
            seekers = [q for q in kin if _wants(world, q, resource)]
            if not seekers: continue
            recipient = max(seekers, key=lambda q: (_aspiration(world, q).urgency, _aspiration(world, q).drive, _aspiration(world, q).preparation, -q.id))
            event = world.emit('magic_resource_transferred', Layer.SOCIETY, (Ref('person', holder.id), Ref('person', recipient.id)), Ref('settlement', sid), ((resource.origin_event,) if resource.origin_event else ()), resource=resource.id, resource_kind=resource.kind, key=resource.key, reason='family transmission', price=0, coin_transfer={}, price_domain='gift')
            world.magic_resources.transfer(resource.id, 'person', recipient.id, event.id, sid)
            _aspiration(world, recipient).preparation = min(1., _aspiration(world, recipient).preparation + .08)
            break


def _resource_circulation(world, rng, sid, people, users, magic):
    if not people: return
    rr = rng.stream('magical_circulation', world.year, sid); people_by_id = {p.id:p for p in people}; rounds = 3 + (3 if magic is not None else 0)
    for _ in range(rounds):
        # People are already id-sorted. Probe the owner index directly instead of
        # rescanning every owner bucket once per round and settlement.
        holder_ids = [p.id for p in people if world.magic_resources.owner_index.get(('person', p.id))]
        for holder_id in holder_ids:
            holder = people_by_id[holder_id]; path = world.advancement.path(holder.id); a = _aspiration(world, holder); base = 0 if path is None else len(path.base_essences)
            ess = _wanted_resources(world, holder, world.magic_resources.inventory('person', holder.id, 'essence')) if base < a.desired_base_essences else []
            if ess and base < a.desired_base_essences and rr.random() < .55 + .30 * a.urgency:
                viable = [r for r in ess if path is None or r.key not in path.base_essences]
                if viable and rr.random() < max(.25, a.compromise_tolerance): absorb_essence_resource(world, holder.id, viable[int(rr.random() * len(viable)) % len(viable)].id); path = world.advancement.path(holder.id)
            stones = [] if path is None else (_wanted_resources(world, holder, world.magic_resources.inventory('person', holder.id, 'awakening_stone')) if len(path.abilities) < min(a.desired_abilities, path.capacity) else [])
            if path is not None and stones and len(path.abilities)<min(a.desired_abilities,path.capacity) and rr.random()<max(.22,.82-.55*a.stone_selectiveness): use_awakening_stone(world,holder.id,stones[int(rr.random()*len(stones))%len(stones)].id)
            held=world.magic_resources.inventory('person',holder.id); surplus=_wanted_resources(world,holder,held,wanted=False) if held else []
            if surplus and rr.random()<(.58 if magic is not None else .28): _transfer_to_seeker(world,surplus[int(rr.random()*len(surplus))%len(surplus)],holder,people,rr)


def _society_pipeline(world, rng, sid, people, adventure, magic):
    existing = {(a.person, a.society) for a in world.institutions.applications.values() if a.passed is None or a.passed}
    for p in people:
        if not full_essence_user(world, p.id): continue
        aspiration = _aspiration(world, p); targets = []
        if aspiration.adventurer_aspiration: targets.append(('adventure_society', adventure, .72))
        craft = world.skills.get(p.id, 'craft').level; knowledge = world.skills.get(p.id, 'knowledge').level
        if p.curiosity > .52 or craft >= 1.2 or knowledge >= 1.2: targets.append(('magic_society', magic, .48 + .22 * p.curiosity))
        for society, branch, intent in targets:
            inst = world.institutions.institution_by_kind(society)
            if branch is None or inst is None or p.id in inst.members or (p.id, society) in existing: continue
            srng = rng.stream('society_career_intent', world.year, p.id + (0 if society == 'adventure_society' else 1000000))
            if srng.random() < min(.92, intent + .12 * aspiration.urgency + .10 * aspiration.preparation): apply_for_society(world, p.id, society); existing.add((p.id, society))


def _magical_workshops(world, rng, sid, people, users, magic):
    if not people: return
    settlement = world.settlements[sid]
    producers = sorted(people, key=lambda p: (world.skills.get(p.id, 'agriculture').level + world.skills.get(p.id, 'craft').level, p.health, -p.id), reverse=True)
    extra_batches = min(24, max(0, len(people) // 18 + int(settlement.prosperity * 3) - 1)); Layer, Ref = layer_ref()
    for n in range(extra_batches): _produce_lot(world, sid, producers[n % len(producers)], rng.stream('civilization_material_batch', world.year, sid * 100 + n), Layer, Ref)
    magical_crafters = [p for p in users if world.skills.get(p.id, 'craft').level >= .7]
    if not magical_crafters: return
    magical_lot_count = world.materials.magical_available_count(sid)
    if not magical_lot_count: return
    commissions = min(12, magical_lot_count, len(magical_crafters) * (2 if magic is not None else 1))
    for n in range(commissions):
        crafter = magical_crafters[n % len(magical_crafters)]; crng = rng.stream('magical_commission', world.year, sid * 100 + n)
        if crng.random() < (.78 if magic is not None else .48): _craft_once(world, sid, crafter, crng, Layer, Ref)


def magical_civilization_step(world, rng):
    """Civilizational feedback loop: magic is normal; exceptional power remains exceptional."""
    # Build the adult settlement index once. _living previously rescanned the
    # entire living population separately for every settlement.
    by_settlement = {sid: [] for sid in world.settlements}
    for p in world.current_people():
        if p.alive and p.age >= 16: by_settlement[p.settlement].append(p)
    for people in by_settlement.values(): people.sort(key=lambda p: p.id)
    for sid in sorted(world.settlements):
        people = by_settlement[sid]
        if not people: continue
        users = _practitioners(world, people); adventure, magic = _institutional_capacity(world, sid)
        _review_magic_demand(world, people, adventure, magic)
        _expedition_step(world, rng, sid, people, users, adventure, magic)
        _kinship_circulation(world, sid, people)
        users = _practitioners(world, people)
        _resource_circulation(world, rng, sid, people, users, magic)
        _society_pipeline(world, rng, sid, people, adventure, magic)
        _magical_workshops(world, rng, sid, people, users, magic)
