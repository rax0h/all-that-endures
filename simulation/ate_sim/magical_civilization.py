from __future__ import annotations

from .core_types import layer_ref
from .magic_resources import _aspiration, _make_resource, _wants, _wanted_resources, absorb_essence_resource, use_awakening_stone
from .materials import _produce_lot, _craft_once
from .institutions import apply_for_society, full_essence_user


def _living(world, sid):
    return sorted((p for p in world.people.values() if p.alive and p.age >= 16 and p.settlement == sid), key=lambda p: p.id)


def _practitioners(world, people):
    return [p for p in people if world.advancement.path(p.id) is not None]


def _institutional_capacity(world, sid):
    adventure = world.institutions.branch_for('adventure_society', sid)
    magic = world.institutions.branch_for('magic_society', sid)
    return adventure, magic


def _expedition_step(world, rng, sid, people, users, adventure, magic):
    """Turn magical ecology into recoverable resources through actual expeditions and field work.

    Ambient magic determines what the landscape can yield. Population, experienced essence users,
    Society branches, preparation and local danger determine how much of that potential people can
    safely find. Resources are still random discoveries with provenance; nobody is handed the exact
    essence or stone they want.
    """
    if not people:
        return
    ambient = world.ambient_magic.field(sid).level
    settlement = world.settlements[sid]
    cell = world.cells[(settlement.x, settlement.y)]
    aspirants = [p for p in people if _aspiration(world, p).desired_base_essences > 0]
    adventurer_aspirants = [p for p in aspirants if _aspiration(world, p).adventurer_aspiration]
    member_count = 0 if adventure is None else sum(1 for p in people if p.id in world.institutions.institution_by_kind('adventure_society').members)
    field_capacity = len(users) + len(adventurer_aspirants) * .45 + member_count * 1.5
    if field_capacity <= 0:
        return

    rr = rng.stream('magical_field_economy', world.year, sid)
    pressure = max(0., ambient - .30) + .35 * cell.hazard + .08 * min(10, field_capacity)
    attempts = min(8, int(pressure * (1.2 + len(people) / 90.0)))
    if attempts <= 0:
        return

    candidates = sorted(users + [p for p in adventurer_aspirants if p not in users], key=lambda p: (_aspiration(world, p).risk_tolerance, _aspiration(world, p).preparation, p.health, -p.id), reverse=True)
    if not candidates:
        return
    Layer, Ref = layer_ref()
    for n in range(attempts):
        erng = rng.stream('magical_expedition', world.year, sid * 100 + n)
        leader = candidates[n % len(candidates)]
        aspiration = _aspiration(world, leader)
        readiness = .20 + .22 * aspiration.preparation + .18 * aspiration.risk_tolerance + .08 * world.advancement.rank(leader.id)
        if adventure is not None:
            readiness += .14
        if magic is not None:
            readiness += .08
        danger = .08 + .22 * cell.hazard + .10 * max(0., ambient - .8)
        event = world.emit('magical_expedition', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), society_branch=None if adventure is None else adventure.id, ambient_magic=round(ambient, 3), readiness=round(readiness, 3), danger=round(danger, 3))
        if erng.random() > min(.86, readiness + .16 * ambient):
            world.emit('magical_expedition_returned_empty', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), (event.id,))
            continue
        # Mature magical societies recover both essences and stones. Stones become increasingly
        # important once a population of partial/full users exists, without tailoring the stone.
        incomplete = sum(1 for p in users if len(world.advancement.path(p.id).abilities) < world.advancement.path(p.id).capacity)
        stone_share = min(.68, .38 + .025 * min(10, incomplete) + (.08 if magic is not None else 0.))
        kind = 'awakening_stone' if erng.random() < stone_share else 'essence'
        found = _make_resource(world, erng, sid, leader, kind, event.id, 'organized magical expedition')
        world.emit('magical_expedition_resource_recovered', Layer.SOCIETY, (Ref('person', leader.id),), Ref('settlement', sid), (event.id, found.origin_event), resource=found.id, resource_kind=found.kind, key=found.key)
        aspiration.preparation = min(1., aspiration.preparation + .025)


def _resource_circulation(world, rng, sid, people, users, magic):
    """Make established magical communities actually use and circulate the resources they recover."""
    if not users:
        return
    rr = rng.stream('magical_circulation', world.year, sid)
    # Magic Society presence improves information/market matching, not resource creation.
    rounds = 2 + (2 if magic is not None else 0)
    for _ in range(rounds):
        for holder in users:
            path = world.advancement.path(holder.id)
            a = _aspiration(world, holder)
            ess = _wanted_resources(world, holder, world.magic_resources.inventory('person', holder.id, 'essence'))
            if ess and len(path.base_essences) < a.desired_base_essences and rr.random() < .55 + .30 * a.urgency:
                viable = [r for r in ess if r.key not in path.base_essences]
                if viable and rr.random() < max(.25, a.compromise_tolerance):
                    absorb_essence_resource(world, holder.id, viable[int(rr.random() * len(viable)) % len(viable)].id)
                    path = world.advancement.path(holder.id)
            stones = _wanted_resources(world, holder, world.magic_resources.inventory('person', holder.id, 'awakening_stone'))
            if stones and len(path.abilities) < min(a.desired_abilities, path.capacity):
                # Selective users still wait sometimes, but a mature market gives them repeated real opportunities.
                if rr.random() < max(.22, .82 - .55 * a.stone_selectiveness):
                    use_awakening_stone(world, holder.id, stones[int(rr.random() * len(stones)) % len(stones)].id)


def _society_pipeline(world, rng, sid, people, adventure, magic):
    """Convert Society ambition into applications once the person has actually qualified."""
    existing = {(a.person, a.society) for a in world.institutions.applications.values() if a.passed is None or a.passed}
    for p in people:
        if not full_essence_user(world, p.id):
            continue
        aspiration = _aspiration(world, p)
        targets = []
        if aspiration.adventurer_aspiration:
            targets.append(('adventure_society', adventure, .72))
        # Curious, knowledge-oriented and craft-oriented full users have an organic Magic Society path.
        craft = world.skills.get(p.id, 'craft').level
        knowledge = world.skills.get(p.id, 'knowledge').level
        if p.curiosity > .52 or craft >= 1.2 or knowledge >= 1.2:
            targets.append(('magic_society', magic, .48 + .22 * p.curiosity))
        for society, branch, intent in targets:
            inst = world.institutions.institution_by_kind(society)
            if branch is None or inst is None or p.id in inst.members or (p.id, society) in existing:
                continue
            srng = rng.stream('society_career_intent', world.year, p.id + (0 if society == 'adventure_society' else 1000000))
            if srng.random() < min(.92, intent + .12 * aspiration.urgency + .10 * aspiration.preparation):
                apply_for_society(world, p.id, society)
                existing.add((p.id, society))


def _magical_workshops(world, rng, sid, people, users, magic):
    """Create careers and commissions instead of treating magical crafting as an annual lottery."""
    if not people:
        return
    settlement = world.settlements[sid]
    rr = rng.stream('magical_workshops', world.year, sid)
    # Ordinary economic batches scale with real labor; this represents market-relevant producer
    # batches, not every board, fleece or sack of grain made by the settlement.
    producers = sorted(people, key=lambda p: (world.skills.get(p.id, 'agriculture').level + world.skills.get(p.id, 'craft').level, p.health, -p.id), reverse=True)
    extra_batches = min(24, max(0, len(people) // 18 + int(settlement.prosperity * 3) - 1))
    Layer, Ref = layer_ref()
    for n in range(extra_batches):
        prng = rng.stream('civilization_material_batch', world.year, sid * 100 + n)
        _produce_lot(world, sid, producers[n % len(producers)], prng, Layer, Ref)

    magical_crafters = [p for p in users if world.skills.get(p.id, 'craft').level >= .7]
    if not magical_crafters:
        return
    magical_lot_count = world.materials.magical_available_count(sid)
    if not magical_lot_count:
        return
    # A functioning Magic Society creates commissions, supplier information and apprenticeship
    # pressure. It does not grant crafting ability: the crafter must still pass normal permission rules.
    commissions = min(12, magical_lot_count, len(magical_crafters) * (2 if magic is not None else 1))
    for n in range(commissions):
        crafter = magical_crafters[n % len(magical_crafters)]
        crng = rng.stream('magical_commission', world.year, sid * 100 + n)
        if crng.random() < (.78 if magic is not None else .48):
            _craft_once(world, sid, crafter, crng, Layer, Ref)


def magical_civilization_step(world, rng):
    """Civilizational feedback loop: magic is normal; exceptional power remains exceptional."""
    for sid in sorted(world.settlements):
        people = _living(world, sid)
        if not people:
            continue
        users = _practitioners(world, people)
        adventure, magic = _institutional_capacity(world, sid)
        _expedition_step(world, rng, sid, people, users, adventure, magic)
        # Recompute because expeditions can put resources into practitioners' hands.
        users = _practitioners(world, people)
        _resource_circulation(world, rng, sid, people, users, magic)
        _society_pipeline(world, rng, sid, people, adventure, magic)
        _magical_workshops(world, rng, sid, people, users, magic)
