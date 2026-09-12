from copy import deepcopy
from unittest.mock import patch
import pytest
from simulation.ate_sim import Simulation, generate_world
from simulation.ate_sim.core import RNG
from simulation.ate_sim import magic_resources as magic
from simulation.ate_sim.semantic_dictionary import ESSENCE_IDS, STONE_IDS
from simulation.tests.reference_magic_ecology import legacy_magic_ecology_step

@pytest.mark.parametrize("seed", [17, 843000])
def test_indexed_market_matches_legacy_with_accumulated_stock(seed):
    original = Simulation(generate_world(seed)).run(20)
    adults = [p for p in original.people.values() if p.alive and p.age >= 16]
    # Duplicate stock, household recovery, wealth ties and mid-loop path changes.
    for n in range(240):
        person = adults[n % len(adults)]
        kind = "essence" if n % 3 else "awakening_stone"
        key = ESSENCE_IDS[n % 7] if kind == "essence" else STONE_IDS[n % 7]
        owner_kind, owner = ("person", person.id) if n % 2 else ("settlement", person.settlement)
        original.magic_resources.create(kind, key, "common", original.year, person.settlement, owner_kind, owner)
    indexed = deepcopy(original)
    for _ in range(3):
        original.year += 1
        indexed.year += 1
        legacy_magic_ecology_step(original, RNG(seed))
        magic.magic_ecology_step(indexed, RNG(seed))
        assert original.digest() == indexed.digest()

def test_wanted_inventory_queries_once_per_semantic_demand_and_preserves_order():
    world = generate_world(17)
    person = next(p for p in world.people.values() if p.age >= 18)
    stock = [world.magic_resources.create("awakening_stone", STONE_IDS[n % len(STONE_IDS)], "common", 0, person.settlement, "person", person.id) for n in range(1000)]
    expected = [r for r in stock if magic._wants(world, person, r)]
    with patch.object(magic, "_wants", wraps=magic._wants) as wants:
        assert magic._wanted_resources(world, person, stock) == expected
        assert wants.call_count == 1

def test_market_contenders_preserve_wealth_ties_and_ineligible_top_buyer():
    world = generate_world(17)
    people = [p for p in world.people.values() if p.age >= 18][:3]
    resource = world.magic_resources.create("essence", ESSENCE_IDS[0], "common", 0)
    for p in people:
        world.magic_resources.aspirations[p.id] = magic.MagicAspiration(.7, 3, 20, "test", 0, urgency=.8, preparation=.5)
    contenders = magic._market_contenders(world, people, resource)
    for wealth in ((12, 11, 10), (5, 11, 10), (5, 4, 10), (0, 0, 0)):
        for p, value in zip(people, wealth):
            p.wealth = value
        reference = max(people, key=lambda p: (magic._aspiration(world,p).urgency, magic._aspiration(world,p).drive, magic._aspiration(world,p).preparation, p.wealth, -p.id))
        assert max(contenders, key=lambda p: (p.wealth, -p.id)) is reference
