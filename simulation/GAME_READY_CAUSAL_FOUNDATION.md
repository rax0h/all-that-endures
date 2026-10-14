# Game-ready causal foundation rebuild

Baseline: immutable PR #5 head `fbfbe58ef1e18fa35eb4d63af98cd66e00f64c4f`.

This branch is a clean architectural continuation from that exact commit. PR #5 is not modified.
PR #12 is evidence only: accepted behaviors and exposed failure modes may be retained, but its
implementation is not authoritative.

## Product contract

All That Endures is a causally persistent world simulation for a 2.75D fantasy RPG. The simulation
creates objective history. Society reacts to it. Knowledge can be incomplete or wrong. Narrative and
the renderer may interpret state but must never fabricate objective causes.

The player uses the same rules as NPCs. Persistent identity, ownership, genealogy, rank, institutions,
objects, places and events must survive long histories at an appropriate resolution.

## Stage 0.5 completion boundary

Stage 0.5 is the game-ready living-world foundation gate. It does **not** smuggle Stage 1 psyche,
subjective-memory or language systems into placeholder counters. It must leave clean seams for those
later systems.

Stage 0.5 is complete only when all of the following are true:

1. **Magic legality**
   - Three base essences + confluence.
   - Exactly five abilities per essence group; twenty abilities total for a ranked path.
   - No Iron-or-higher body with an incomplete path.
   - Ability-specific advancement, tier ceilings, understanding/evidence and core taint remain real gates.
   - Acquisition, possession, absorption and use remain distinct causal events.

2. **Magic civilization**
   - The observation boundary may begin inside an already mature magical region.
   - Common/basic magic participation can be broad without making mastery common.
   - Adventure Society and Magic Society are durable institutions, not spawn-rate knobs.
   - Adventure Society forms recurring cadet cohorts, physically provisions training, graduates complete
     Iron paths and replenishes its professional population.
   - Civilian access, institutional supply and exceptional mastery are separate causal pipelines.
   - Resources have provenance, custody, transfer and consumption. No desired resource is materialized
     directly for a person.

3. **Rank ecology**
   - Iron and Bronze replenish continuously.
   - A large Silver shelf is a valid mature outcome.
   - Silver individuals may accumulate partial Gold progress for decades/centuries.
   - Gold is uncommon and Diamond exceptional.
   - Population counts are diagnostics, never quotas. Do not weaken prerequisites to hit a target.

4. **Economy**
   - Ranked currency is finite/conserved except explicit production and consumption.
   - Payment has payer, payee, denomination and provenance.
   - Equal-value denomination exchange/change must use legitimate counterparties or institutional reserves;
     valuation alone never creates coins.
   - Institutional reproduction must not halt merely because the treasury has wealth trapped in the wrong
     denomination.
   - Materials, magical resources, crafted items and property preserve provenance.

5. **Living world**
   - Ordinary aging, mortality, reproduction, health, scarcity and hazards remain active.
   - Species differences affect embodiment/ecology without becoming personality stereotypes.
   - Geography, weather, ambient magic, ecology, threats, settlements, migration, infrastructure and trade
     exert causal pressure.
   - No population floors, forced disasters or output-target patches.

6. **Authority**
   - One authoritative transition for death/inheritance/resurrection.
   - One authoritative body-rank writer.
   - Institutions own recruitment/cohorts/membership.
   - Resource systems own physical magical resources.
   - Advancement owns prerequisites/progression.
   - Currency owns denomination conservation/exchange.
   - History owns objective event provenance.

7. **Performance architecture**
   - Canonical state is distinct from rebuildable runtime indexes.
   - Annual systems reuse shared living/settlement/institution/resource indexes.
   - Historical collections are never rescanned per person in hot loops.
   - Durable institutional pipelines use indexed queues/state, not repeated archive scans.
   - Deterministic RNG streams remain isolated by namespace/year/entity.
   - 1,000 exact years must pass the <=120 second canonical simulation gate on the accepted runner contract.
   - 10,000-year longevity must be practical enough for routine world-generation validation; long-history
     performance is treated as an engine property, not a reporting-harness problem.

8. **History and game-facing inspection**
   - Causal event IDs remain stable and backward-pointing.
   - Archive/export remains read-only relative to simulation state.
   - Missing history is unknown, never invented.
   - Game/query layers can inspect people, places, institutions, provenance and causal chains without
     exposing omniscient data directly to NPC minds.

## Later-stage seams that must remain intact

The architecture must be able to add, without replacing Stage 0.5 truth:

- persistent multidimensional personhood and development;
- directional relationships;
- perception, memory, belief, ignorance and rumor;
- language/dialect/literacy/register;
- interaction and expression;
- artifacts, literature and cultural influence;
- deeper politics/law, archaeology, technology and knowledge institutions;
- cosmology/off-world systems when canonized;
- visual realization through deterministic simulation-derived specifications.

## Acceptance runs

Before this branch can be considered frozen:

- focused semantic/invariant tests;
- full suite and smoke checks;
- deterministic 100-year validation;
- deterministic 500-year inspection;
- canonical seed 843000 at 1,000 years with progression/economy/history validation and <=120 second simulation gate;
- a separate fresh-seed 10,000-year world-health run with snapshots at 1,000 / 5,000 / 7,500 / 10,000,
  including every species, demography, settlements, magic funnel/ranks, institutions, economy, ecology,
  conflict, culture/knowledge and state-growth/performance telemetry.

No merge is automatic.
