# Astra Stage 0.5 Update

## Authority and resume point

Astra remains the repo-wide owner of Stage 0.5 stabilization. Resume production work from Astra's last trusted implementation in PR #5, branch `sim/canonical-magic-progression`, head `fbfbe58ef1e18fa35eb4d63af98cd66e00f64c4f`.

PRs #6-#11 are quarantined post-Astra experiments. PR #12 (`research/stage-0.5-causal-rebuild`) is research only. It may provide evidence and requirements, but its implementation is not a production continuation point and must not be cherry-picked blindly.

This update supplements `docs/IMPLEMENTATION_ROADMAP.md` and records a Stage 0.5 modeling discovery made while investigating magical participation.

## Discovery: the canonical history does not need to bootstrap magic from zero

The earlier calibration work implicitly treated year 0 as if it were the beginning of magic and magical civilization. That creates an artificial bootstrap problem: a founding population with few or no practitioners must manufacture teachers, magical households, supply chains, institutional knowledge, magical occupations, resource circulation and accumulated magical wealth during the observed simulation window before the world can resemble the mature magical civilization ATE is intended to model.

That assumption is unnecessary and conflicts with the magical-world invariant. **ATE's year 0 should be understood as the beginning of the recorded/observed simulation window, not the beginning of magic, society or history.** Magic may have shaped civilization for generations or millennia before the archive begins.

Therefore the canonical starting state may be initialized as an already-established magical civilization. For a mature connected society, seed a coherent cross-section consistent with the observational expectation already used in Stage 0.5: roughly 75-80% of eligible adults may begin with at least one genuinely absorbed essence. This is an **initial-condition model**, not a prevalence controller.

After initialization there must be **no target-maintenance rule, quota, cap or corrective pressure** that forces the population back toward the seeded percentage. Births, deaths, inheritance, family/cultural transmission, occupations, markets, institutions, ecology, resource availability, teaching, individual decisions and historical shocks must determine the subsequent trajectory. If participation falls sharply over centuries, that is useful evidence that the mature civilization cannot reproduce its magical culture. If it rises, that is also a legitimate emergent result.

## Seed coherent state, not flags

Do not implement mature initialization as `magic_user=True`, a rank assignment, or an exception to canonical progression. Founders who begin with magic must possess valid underlying state through the same authoritative systems used during simulation: absorbed essence records, canonical path state, abilities where applicable, resource consumption/provenance, and coherent rank state.

As the initializer becomes more representative, it may also seed historically inherited state that a mature civilization reasonably begins with: partial and completed paths, a causal rank pyramid, teachers/practitioners, institutional continuity, Society membership/records, magical occupations, inventories, resource ownership, ordinary/ranked wealth, trade relationships and other pre-observation state. These should be represented explicitly as pre-simulation/founder-era state with provenance rather than fabricated as events that supposedly first occurred after year 0.

Initialization must preserve all canonical progression invariants. Seeding a mature civilization is not permission to bypass the three-base-plus-confluence path, 20-ability ranked-path requirement, mastery/understanding requirements, resource conservation, provenance or chronology.

## Audit bootstrap-only machinery

This changes the Stage 0.5 question from:

> Can a nearly mundane founding population bootstrap a mature magical civilization quickly enough?

into:

> Can an already-established magical civilization sustain, reproduce, transmit, trade, teach, lose and transform its magical culture over 100, 500 and 1,000 years?

Audit existing and experimental code for mechanisms whose primary purpose is rescuing the artificial zero-magic start. Examples include zero-practitioner special cases, artificial aspiration escalation, emergency access/provisioning, discovery/expedition behavior added solely to create first-generation practitioners, and broad annual access machinery that compensates for absent inherited civilization.

Do **not** delete a mechanism merely because it also helps bootstrap. Keep it when it represents legitimate mature-world behavior with a clear authoritative owner. Remove, simplify or redesign it when its only causal justification is forcing a zero-magic world toward the desired mature distribution.

The audit should reduce machinery rather than stack another initialization layer on top of old bootstrap compensators.

## Validation consequence

Stage 0.5 calibration should now measure **retention and reproduction of magical civilization**, not just spontaneous acquisition from zero.

For canonical seed `843000` and representative additional seeds, report at year 0 and later checkpoints (at least 100/500/1,000): eligible adults, adults with >=1 absorbed essence, path-stage funnel, completed 20/20 paths, rank distribution, resource stocks/flows, acquisition routes, institutional continuity, and relevant currency/liquidity. Preserve deterministic replay, provenance/chronology, conservation and the <=120-second millennium gate.

The initial mature percentage is not itself proof of success. The meaningful result is what the simulation does **after the initializer releases control**.

## Current research evidence

PR #12 is testing this hypothesis in isolation. Its first mature-founder experiment changed world generation so 78% of founding adults receive real absorbed essences through the existing resource and advancement authorities. No maintenance controller was added. Treat its runs as diagnostic evidence only; Astra should independently inspect the approach from PR #5 before adopting production implementation.

The main architectural rule remains: **build causes once, let many stories use them.** Mature initialization supplies the history that occurred before observation; the simulation remains responsible for everything that happens afterward.
