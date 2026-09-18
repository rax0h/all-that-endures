from __future__ import annotations

from .core_types import layer_ref
from .magic_resources import _aspiration, _make_resource, _wanted_resources, _transfer_to_seeker, absorb_essence_resource, use_awakening_stone
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


def _essence_supply_signal(world, people, sid):
    """Return actual local first/path-essence demand, shelf stock and pressure.

    This is a market signal, not a prevalence target. Demand exists only when a
    person's current path has fewer base essences than that person's own desired
    configuration. Existing settlement-owned essences are literal shelf stock.
    """
    first_seekers=0;partial_seekers=0
    for p in people:
        a=_aspiration(world,p);path=world.advancement.path(p.id)
        base=0 if path is None else len(path.base_essences)
        if base<a.desired_base_essences:
            if base==0:first_seekers+=1
            else:partial_seekers+=1
    seekers=first_seekers+partial_seekers
    stock=len(world.magic_resources.inventory('settlement',sid,'essence'))
    # First access carries the full civilian supply signal. Later path-building
    # still creates demand, but with lower weight so scarce common stock is not
    # expanded mainly to feed already-magical specialists.
    effective_demand=first_seekers+.35*partial_seekers
    gap=max(0.,effective_demand-stock)
    pressure=0. if effective_demand<=0 else min(1.,gap/max(1.,effective_demand))
    return seekers,stock,pressure


def _apply_external_magic_pressure(world, sid, people, users):
    """Make existing magical goals urgent when the world gives people a reason.

    This never creates interest. It only changes how hard an already-interested
    seeker pushes when monsters, magical peers, or competition for scarce local
    stock make delay costly.
    """
    if not people:return
    active=world.threat_ecology.active(sid)
    surge=world.settlements[sid].memory.get('monster_surge',0.)
    threat_rank=max((t.rank for t in active),default=0)
    local_user_share=len(users)/max(1,len(people))
    seekers,stock,supply_pressure=_essence_supply_signal(world,people,sid)
    peer_competition=min(1.,local_user_share*2.5)*(0.55+.45*supply_pressure)
    for p in people:
        a=_aspiration(world,p);path=world.advancement.path(p.id)
        base=0 if path is None else len(path.base_essences)
        if a.desired_base_essences<=base:continue
        # An uninterested person is not turned into a seeker by pressure here.
        if a.desired_base_essences<=0:continue
        motive=world.agency.motives.get(p.id)
        status_need=0. if motive is None else motive.status
        threat=max(surge,p.fear,min(1.,threat_rank/3.))
        competition=min(1.,peer_competition*(.65+.35*status_need))
        external=max(threat,competition)
        if external<.12:continue
        target=min(1.,.34+.46*threat+.34*competition+.10*a.drive)
        a.urgency=max(a.urgency,target)
        # Under real pressure, people become less precious about the exact first
        # essence they imagined and more willing to take a useful available path.
        a.compromise_tolerance=max(a.compromise_tolerance,min(.95,.42+.45*external))
        a.risk_tolerance=max(a.risk_tolerance,min(.92,.28+.38*external+.18*a.drive))


def _review_magic_demand(world, people, adventure, magic):
    """Let existing aspirations respond to a changing magical civilization."""
    user_ids = {p.id for p in people if world.advancement.essence_user(p.id)}
    for p in people:
        a = _aspiration(world, p)
        path = world.advancement.path(p.id)
        if path is not None and a.completion_goal:
            a.desired_base_essences = 3
            a.desired_abilities = 20
        # Family transmission is historical, not merely local/present-tense:
        # a dead or migrated magical parent can still have raised a child inside
        # an established magical culture.
        family = sum(1 for x in p.parents if world.advancement.essence_user(x))
        contacts = sum(1 for x in world.social.neighbors(p.id) if x in user_ids)
        named_profession = p.occupation in ('adventurer', 'guard', 'hunter', 'soldier', 'farmer', 'crafter', 'smith', 'healer', 'merchant', 'scholar', 'builder', 'architect', 'craft apprentice', 'magical craftsperson')
        # "Labor" is only a placeholder, but ordinary work must still become
        # specific before it creates magical demand. A person needs either a
        # named profession or substantial demonstrated skill, not merely a job.
        work_levels = {
            'agriculture': world.skills.get(p.id, 'agriculture').level,
            'construction': world.skills.get(p.id, 'construction').level,
            'craft': world.skills.get(p.id, 'craft').level,
            'knowledge': world.skills.get(p.id, 'knowledge').level,
            'defense': world.skills.get(p.id, 'defense').level,
        }
        work_domain, work_level = max(work_levels.items(), key=lambda x: x[1])
        skilled_specialist = work_level >= 1.60 and p.curiosity >= .55
        work_need = named_profession or skilled_specialist
        settlement = world.settlements[p.settlement]
        cell = world.cells[(settlement.x, settlement.y)]
        local = world.local[p.settlement]
        pressure = max(settlement.memory.get('monster_surge', 0.0), p.fear)
        acute_environment = cell.hazard >= .72 or pressure >= .48
        scarcity_need = local.scarcity >= .18 and work_levels['agriculture'] >= .45
        household = world.households[p.household]
        household_crisis = local.scarcity >= .24 and household.food < 4
        institutional_access = adventure is not None or magic is not None
        already_interested = a.desired_base_essences > 0
        social_start = (family >= 1 and p.curiosity >= .42) or (contacts >= 5 and p.curiosity >= .60)
        social_exposure = already_interested and ((family >= 1 and p.curiosity >= .38) or (contacts >= 4 and p.curiosity >= .50))
        motive = world.agency.motives.get(p.id)
        status_need = 0.0 if motive is None else motive.status
        work_start = work_need and (already_interested or p.curiosity >= .48 or status_need >= .38)
        reason = None
        if social_start or social_exposure: reason = 'social magical exposure'
        elif work_start and institutional_access: reason = f'{work_domain} capability'
        elif scarcity_need and institutional_access: reason = 'food-production pressure'
        elif household_crisis and institutional_access and p.attachment >= .45: reason = 'household scarcity'
        elif acute_environment and institutional_access: reason = 'local magical pressure'

        # Completion is driven by intrinsic mastery intent and exceptional
        # professional commitment, not by socially-inflated aspiration drive.
        # This prevents a mature magical society from recursively making nearly
        # every ordinary user chase all 20 abilities.
        started = path is not None and len(path.base_essences) > 0
        mastery_intent = min(1.0, .62*p.curiosity + .28*(1-p.inhibition) + .10*status_need)
        # Adventuring can become a vocation after childhood aspiration state was
        # formed, but institutional recruitment is owned by the bounded Society
        # apprenticeship allocator. This pass may discover self-directed intent;
        # it must not convert every plausible recruit into a completionist.
        adventure_intent = (
            a.adventurer_aspiration
            or (a.risk_tolerance >= .72 and p.curiosity >= .60
                and (work_levels['defense'] >= .85 or pressure >= .28))
        )
        if adventure_intent:
            a.adventurer_aspiration = True
        personal_mastery = started and mastery_intent >= .74
        professional_mastery = started and work_level >= 2.40 and mastery_intent >= .66
        magical_profession = started and p.occupation == 'magical craftsperson' and mastery_intent >= .60
        if adventure_intent or personal_mastery or professional_mastery or magical_profession:
            a.completion_goal = True; a.desired_base_essences = 3; a.desired_abilities = 20

        if reason is None: continue
        a.drive = min(1., max(a.drive, .34 + .05 * min(3, family + contacts) + (.06 if work_need else 0.) + .04 * min(1., work_level)))
        a.urgency = min(1., max(a.urgency, .30 + .28 * pressure + (.10 if work_need else 0.) + (.08 if scarcity_need or household_crisis else 0.)))
        a.desired_base_essences = max(a.desired_base_essences, 1)
        a.desired_abilities = max(a.desired_abilities, 5)
        if a.reason == 'capability' or a.desired_base_essences == 1: a.reason = reason


def _expedition_step(world, rng, sid, people, users, adventure, magic):
    if not people: return
    ambient = world.ambient_magic.field(sid).level
    settlement = world.settlements[sid]; cell = world.cells[(settlement.x, settlement.y)]
    aspirants = [p for p in people if _aspiration(world, p).desired_base_essences > 0]
    adventurer_aspirants = [p for p in aspirants if _aspiration(world, p).adventurer_aspiration]
    essence_seekers, essence_stock, supply_pressure = _essence_supply_signal(world, people, sid)
    member_count = 0 if adventure is None else sum(1 for p in people if p.id in world.institutions.institution_by_kind('adventure_society').members)
    institutional = (0. if adventure is None else 2.0 * adventure.authority) + (0. if magic is None else 1.5 * magic.authority)
    field_capacity = len(users) + len(adventurer_aspirants) * .45 + len(aspirants) * .08 + member_count * 1.5 + institutional
    if field_capacity <= 0: return
    rr = rng.stream('magical_field_economy', world.year, sid)
    pressure = max(0., ambient - .30) + .35 * cell.hazard + .08 * min(10, field_capacity)
    # Shortage changes what organized expeditions target, not how many physical
    # opportunities the ecology produces. Keep the existing bounded expedition
    # activity rate and let demand redirect recovery toward essences below.
    attempts = min(8, int(EXPEDITION_ACTIVITY_RATE * pressure * (1.2 + len(people) / 90.0)))
    if attempts <= 0: return
    user_ids={p.id for p in users}
    candidates = sorted(users + [p for p in adventurer_aspirants if p.id not in user_ids], key=lambda p: (_aspiration(world, p).risk_tolerance, _aspiration(world, p).preparation, p.health, -p.id), reverse=True)
    if not candidates: candidates = sorted(adventurer_aspirants, key=lambda p: (_aspiration(world, p).risk_tolerance, _aspiration(world, p).preparation, p.health, -p.id), reverse=True)
    if not candidates: return
    Layer, Ref = layer_ref()
    incomplete = sum(1 for p in users if len(world.advancement.path(p.id).abilities) < world.advancement.path(p.id).capacity)
    for n in range(attempts):
        erng = rng.stream('magical_expedition', world.year, sid * 100 + n); leader = candidates[n % len(candidates)]; aspiration = _aspiration(world, leader)
        readiness = .20 + .22 * aspiration.preparation + .18 * aspiration.risk_tolerance + .08 * leader.rank
        if adventure is not None: readiness += .14
        if magic is not None: readiness += .08
        danger = .08 + .22 * cell.hazard + .10 * max(0., ambient - .8)
        event = world.emit('magical_expedition', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), society_branch=None if adventure is None else adventure.id, ambient_magic=round(ambient, 3), readiness=round(readiness, 3), danger=round(danger, 3))
        if erng.random() > min(.86, readiness + .16 * ambient):
            world.emit('magical_expedition_returned_empty', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), (event.id,)); continue
        stone_share = min(.68, .38 + .025 * min(10, incomplete) + (.08 if magic is not None else 0.))
        if supply_pressure < .15: stone_share = max(stone_share, .82)
        kind = 'awakening_stone' if erng.random() < stone_share else 'essence'
        found = _make_resource(world, erng, sid, leader, kind, event.id, 'organized magical expedition')
        world.emit('magical_expedition_resource_recovered', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), (event.id, found.origin_event), resource=found.id, resource_kind=found.kind, key=found.key)
        aspiration.preparation = min(1., aspiration.preparation + .025)


def _resource_circulation(world, rng, sid, people, users, magic):
    if not people: return
    rr = rng.stream('magical_circulation', world.year, sid); rounds = 3 + (3 if magic is not None else 0)
    people_by_id={p.id:p for p in people}
    for _ in range(rounds):
        # Person-held magical resources are sparse, but the global owner index
        # grows with historical owners. Query the already-bounded local residents
        # instead of rescanning that global index once per settlement/round.
        holder_ids=[pid for pid in people_by_id
                    if world.magic_resources.owner_index.get(('person',pid))]
        if not holder_ids:break
        for holder_id in holder_ids:
            holder=people_by_id[holder_id]
            path = world.advancement.path(holder.id); a = _aspiration(world, holder); base = 0 if path is None else len(path.base_essences)
            ess = _wanted_resources(world, holder, world.magic_resources.inventory('person', holder.id, 'essence')) if base < a.desired_base_essences else []
            if ess and base < a.desired_base_essences and rr.random() < .55 + .30 * a.urgency:
                viable = [r for r in ess if path is None or r.key not in path.base_essences]
                if viable and rr.random() < max(.25, a.compromise_tolerance): absorb_essence_resource(world, holder.id, viable[int(rr.random() * len(viable)) % len(viable)].id); path = world.advancement.path(holder.id)
            stones = [] if path is None else (_wanted_resources(world, holder, world.magic_resources.inventory('person', holder.id, 'awakening_stone')) if len(path.abilities) < min(a.desired_abilities, path.capacity) else [])
            if path is not None and stones and len(path.abilities)<min(a.desired_abilities,path.capacity) and rr.random()<max(.22,.82-.55*a.stone_selectiveness): use_awakening_stone(world,holder.id,stones[int(rr.random()*len(stones))%len(stones)].id)
            held=world.magic_resources.inventory('person',holder.id); surplus=_wanted_resources(world,holder,held,wanted=False) if held else []
            if surplus and rr.random()<(.58 if magic is not None else .28): _transfer_to_seeker(world,surplus[int(rr.random()*len(surplus))%len(surplus)],holder,people,rr)


def _society_pipeline(world, rng, sid, people, adventure, magic, existing=None):
    # Initial intent may create one application here. Failed applicants are not
    # recreated every year: society_career_step owns deliberate reapplication
    # after its cooldown. Use the indexed pair set rather than rescanning the
    # centuries-long application archive once per settlement.
    existing = set(world.institutions.application_pairs()) if existing is None else existing
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
    application_pairs=set(world.institutions.application_pairs())
    for sid in sorted(world.settlements):
        people = by_settlement[sid]
        if not people: continue
        users = _practitioners(world, people); adventure, magic = _institutional_capacity(world, sid)
        _review_magic_demand(world, people, adventure, magic)
        _apply_external_magic_pressure(world, sid, people, users)
        _expedition_step(world, rng, sid, people, users, adventure, magic)
        users = _practitioners(world, people)
        _resource_circulation(world, rng, sid, people, users, magic)
        _society_pipeline(world, rng, sid, people, adventure, magic, application_pairs)
        _magical_workshops(world, rng, sid, people, users, magic)
