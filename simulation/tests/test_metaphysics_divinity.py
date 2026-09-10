from ate_sim.worldgen import generate_world
from ate_sim.core import RNG
from ate_sim.divinity import GOD_DEFINITIONS,divine_step,grant_world_phoenix_resurrection
from ate_sim.metaphysics import register_outworlder,attempt_transcendence
from ate_sim.engine import Simulation
from ate_sim.institutions import ensure_core_societies,society_eligible,apply_for_society


def _adult(w):return next(p for p in w.people.values() if p.alive and p.age>=18)


def test_gods_and_great_astral_beings_are_objective_transcendent_world_state():
 w=generate_world(910001)
 assert set(GOD_DEFINITIONS).issubset(w.divinity.gods)
 assert all(g.transcendent and g.ontology=='god' for g in w.divinity.gods.values())
 assert {'world_phoenix','reaper','builder'}.issubset(w.divinity.great_astral_beings)
 assert all(x.transcendent and x.ontology=='great_astral_being' for x in w.divinity.great_astral_beings.values())
 assert not w.divinity.churches


def test_outworlder_tracks_origin_on_the_soul_not_species():
 w=generate_world(910002);p=_adult(w);species=p.species
 e=register_outworlder(w,p.id,'another-world');soul=w.metaphysics.soul(p.id)
 assert soul.outworlder and soul.origin_world=='another-world' and p.species==species and e.kind=='outworlder_arrived'


def test_world_phoenix_token_has_real_patron_provenance_and_resurrects():
 w=generate_world(910003);p=_adult(w);token=grant_world_phoenix_resurrection(w,p.id)
 assert token.patron_id=='world_phoenix' and token.grant_event in w.divinity.great_astral_beings['world_phoenix'].interventions
 Simulation(w)._die(p,'test')
 assert p.alive and token.consumed_event is not None
 assert w.metaphysics.soul(p.id).death_count==1 and w.metaphysics.soul(p.id).resurrection_count==1
 assert any(e.kind=='resurrection' and token.grant_event in e.causes for e in w.events)


def test_transcendence_requires_causes_not_random_rank_roll():
 w=generate_world(910004);p=_adult(w);s=w.metaphysics.soul(p.id)
 assert attempt_transcendence(w,p.id,'astral_king') is None
 s.marks.add('astral_throne_claimed');s.authorities.add('astral:domain')
 transformed=attempt_transcendence(w,p.id,'astral_king',('astral:domain',))
 assert transformed is not None and transformed.ontology=='astral_king' and 'transcendent' in transformed.marks


def test_society_membership_barrier_is_four_essences_not_partial_magic():
 w=generate_world(910005);ensure_core_societies(w);p=_adult(w)
 w.advancement.absorb_essence(p.id,'fire',w.year,('test',))
 assert not society_eligible(w,p.id,'adventure_society')
 rejected=apply_for_society(w,p.id,'adventure_society')
 assert rejected.stage=='rejected_ineligible' and rejected.passed is False
 for essence in ('water','wind'):w.advancement.absorb_essence(p.id,essence,w.year,('test',))
 assert len(w.advancement.path(p.id).essences)==4
 assert society_eligible(w,p.id,'adventure_society') and society_eligible(w,p.id,'magic_society')


def test_churches_can_emerge_but_are_not_guaranteed_at_world_birth():
 w=generate_world(910006)
 for year in range(1,1200):
  w.year=year;divine_step(w,RNG(w.seed))
  if w.divinity.churches:break
 assert w.divinity.churches
 c=next(iter(w.divinity.churches.values()))
 assert c.origin_event in w.event_ids and c.god in w.divinity.gods
