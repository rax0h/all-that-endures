# Magic progression: source audit and engineering specification

Status: **audit checkpoint, implementation blocked on source verification**.
This is not a completed canon specification or a claim that main is canonically
valid. Audited base: `9551c9c314b8cdbd15f5b6e0c22e95b203d848e2`.
Branch: `sim/canonical-magic-progression`. Audit date: 2026-09-14.

The source books are authoritative for this phase. Earlier ATE documents calling
mechanics “canon-inspired” do not establish those mechanics as book canon. No
simulation rules, golden digests, balance constants or performance gates have
been changed at this checkpoint.

## Evidence classifications

- **Explicit:** directly supported by identified author/publisher text.
- **Implication:** inference from that text; not an independently stated rule.
- **Approximation:** an engineering choice, including existing ATE choices.
- **Unknown:** not established by the primary material inspected here. Unknown
  does not mean the books leave the issue unspecified.

Character-specific powers and exceptions must not become universal mechanics.
Fan fiction, reader recollection and unsourced wiki summaries are not sufficient
to certify a prerequisite. Published editions may supersede original serial text.

## Primary sources inspected

The author's [Royal Road serial](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters)
currently retains early introductory and much later chapters, with a large gap
covering the original advancement explanations. No book text was found in the
repository. The following are short rule extractions, not reproduced passages.

| ID | Source | Narrow evidence established |
| --- | --- | --- |
| S1 | [Chapter 7, Spoils](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters/chapter/387329/chapter-7-spoils) | Essences and awakening stones are objects; an awakening stone requires an unawakened essence ability. Materials, equipment and knowledge items can have ranks and requirements. Coins have named denominations. Jason's particular loot power is not proof of universal automatic loot generation. |
| S2 | [Chapter 8, Dark Magic](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters/chapter/387361/chapter-8-dark-magic) | One absorbed essence is one quarter of the progress to Iron; it raises the associated attribute. That essence has five ability positions, with one initially awakened. Advancement of its attribute depends on mastering its abilities. A stone awakens another ability. |
| S3 | [Chapter 9, Escape](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters/chapter/387399/chapter-9-escape) | Spirit coins have magical uses, including a temporary attribute increase in this scene. This is not permanent body advancement. Mana toxicity matters. |
| S4 | [Book 12 ability appendix](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters/chapter/2012655/bonus-material-book-12-appendices-jasons-abilities) | The displayed character has four essence groups with five abilities each and rank-dependent effects. The author explicitly cautions that the abbreviated appendix is not exhaustive. |
| S5 | [Chapter 997, The Man Who Fought the Monsters](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters/chapter/3212262/chapter-997-the-man-who-fought-the-monsters) | Later Gold advancement involves self-examination and engagement with one's essences. Different individuals develop through different experiences; continued combat alone is not the entire mechanism. This does not supply a numerical advancement formula. |
| S6 | [Chapter 998, Sitting on a Volcano](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters/chapter/3220123/chapter-998-sitting-on-a-volcano) | A particular power advances from Gold 6 to Gold 7 through insight. Named body rank and a power's within-rank level must be distinct. Research and combat are not interchangeable training for every individual. |
| S7 | [Chapter 954, Misgivings](https://www.royalroad.com/fiction/26294/he-who-fights-with-monsters/chapter/2028384/chapter-954-misgivings) | Sustaining high ranks in a low-magic world can require infrastructure; the text distinguishes Diamond from lower ranks. This supplies no universal multiplier for wealth or lifespan. |

The [publisher's Book 1 page](https://aethonbooks.com/book/he-who-fights-with-monsters/)
links to an Amazon sample, but that sample could not be retrieved. The licensed
[Google Books Book 2 listing](https://books.google.com/books/about/He_Who_Fights_with_Monsters_2.html?id=-y4HEgAAQBAJ)
exposes a contents list; its linked “Iron Rank” and “The Perks of Being an Essence
User” preview pages did not expose readable book text through the available
retrieval. These failed accesses are not evidence about the rules themselves.

## Rule-to-code audit

| Area | Evidence status | Current ATE representation | Required disposition |
| --- | --- | --- | --- |
| Unranked and partial absorption | Explicit S2 distinguishes partial progress from Iron | First essence sets `Person.rank` to 1; `AdvancementState.rank` returns minimum existing ability rank | Separate partial essence/attribute state from whole-body rank. Update every rank writer together. |
| Essence count and confluence | Four groups supported by S2/S4; precise third-essence formation rule and combination identity still require primary verification | Three base essences; third absorption creates a confluence automatically | Preserve structural slot limits while verifying formation, combination identity and exceptions. |
| Confluence identity | Unknown for arbitrary combinations | `_confluence` hashes personal context as well as the essence set | Do not certify person-specific confluence species as canonical; distinguish confluence identity from individually expressed abilities. |
| Ability slots | Five per essence supported by S2/S4 | Five per group, maximum twenty | Keep ownership by essence and stable ability identity explicit. |
| Innate ability and stones | Explicit S1/S2 for the shown absorption/awakening | Absorption creates an innate ability; stones create additional abilities | Acquisition, consumption and awakening remain separate events. Verify ritual details before modeling them. |
| Iron completion | All four essences for body Iron supported by S2 | One essence already gives body Iron | Do not confuse all essences absorbed with all twenty abilities awakened. |
| Iron to Bronze | All-required-abilities prerequisite strongly indicated by S2; exact threshold and lagging-ability rules not verified from the available primary text | Only existing abilities participate in minimum-rank calculation | Missing abilities must not disappear from eligibility. Obtain exact rule before defining the transition invariant. |
| Bronze to Silver | Unknown exact primary rule in this audit | Same minimum-of-existing rule | Verify ability, essence/attribute and body ordering; no generic XP bypass. |
| Silver to Gold | Unknown exact transition requirements | Ordinary per-ability progress threshold; no separate Silver transition insight requirement | Obtain relevant source explanation; do not assume the Gold-to-Diamond scalar also models this transition. |
| Gold to Diamond | Qualitative understanding supported by S5/S6; exact final transition conditions unknown | Shared `revelation` and `integrated` floats unlock each Gold ability at 0.92 | These floats and threshold are approximations, not source-established prerequisites. |
| Ability levels and ceilings | Explicit S6 supports within-rank levels | Every ability has `rank`, `level`, `progress`; no body-relative ability ceiling | Verify whether/how far an ability can outrun its body; label both axes explicitly. |
| Practice, teaching, work and cores | S5/S6 support individual relevance and insight; exact core and training rules unresolved | Practice assigns numeric gain; Gold reflection is shared across the entire path | Activities must affect eligible abilities and relevant understanding. Rates remain documented approximations, never prerequisite substitutes. |
| Extra normal essence absorption | Four-group limit supported; exceptional removal/replacement rules unknown | Duplicate or fourth base essence rejected before resource consumption | Preserve the guard; ownership of another essence must remain legal without absorption. |
| Divine grants | Current code meaning verified; exact divine exceptions not verified from primary sources | `divine_step` creates a person-owned resource; does not absorb it | Preserve this distinction. Do not “fix” valid property grants by deleting resources or changing the loadout. |
| Mortality, aging, rejuvenation | Exact rank/species lifespan and age-reversal rules unknown in inspected sources | Current rank rescales entire chronological age; Gold has no senescence; Diamond aliases Gold | Numerical longevity cannot be presented as canon. Model ordinary mortality separately from verified magical changes. |
| Species interaction | Unknown exact source constraints for ATE's catalog | Provisional species longevity multipliers divide mortality | Do not invent species-wide longevity lore from a fantasy convention. |
| Monster rank and confrontation | S1 supports ranked remains; encounter outcomes require circumstances | Threat response can add an effective rank, then permit another rank of gap | Audit compounded advantage and record concrete participants/preparation. Do not substitute a universal hard prohibition for causal combat. |
| Loot and rewards | Ranked objects/coins explicit S1/S3; universal yield and harvest mechanics unresolved | Threat resolution has no corresponding ranked remains payout; Society pays the recipient's rank | Match reward to the actual task/resource and provenance, not a Diamond recipient bonus. Verify harvesting versus character-specific loot powers. |
| Currency denominations | Named tiers explicit; precise ratios not verified in inspected primary text | 100 lesser per Iron, then tenfold steps; separate integer wallet | Preserve existing ratios provisionally; do not claim this audit verified them. Obtain exchange/use restrictions. |
| Purchasing and inheritance | Simulation-required economic mechanics | Ordinary purchases use `Person.wealth`; ranked wallet has credit but no debit/transfer API | Connecting the economies requires explicit payment, change, liquidity and conservation semantics. Valuation is not automatic exchange. |
| Gold/Diamond material consequences | S7 supports meaningful physical distinctions; precise profiles unknown | `profile(5)` returns Gold's exact profile | A distinct Diamond profile is required, but its numerical fields need sourced constraints and labeled approximations. |
| Society rank | Task and membership distinctions require further source verification | Society application/membership exists separately, but notice reward uses recipient rank | Keep credentials, task difficulty, body rank and ability level separate. |

## Confirmed engineering failures independent of exact calibration

1. Missing essence groups/ability slots exert no constraint on body advancement.
   A single Visage ability reaches Diamond through the public practice method.
2. Diamond has no distinct physical profile. Clamping silently aliases it to Gold.
3. Current tests explicitly permit a single-ability Diamond and require a
   person-context-dependent confluence. Passing them cannot establish source
   fidelity; they must be deliberately replaced after the relevant rules are
   verified, rather than treated as an immutable canon specification.
4. Rank-up events lack ability milestone causes. Final ability snapshots cannot
   prove that every ability was ready at each historical body transition.
5. Ranked currency rewards do not fund ordinary purchases through the current
   wealth scalar. Issuing more high-rank coins cannot repair this separation.

## Implementation boundary once source questions are resolved

Use one typed magical configuration as the authority. Represent base slots,
confluence identity, essence-to-attribute association and five stable ability
slots per group. Derive/check body eligibility using all required slots. Keep
the public named body rank distinct from ability rank and within-rank level.
Update world generation, resource absorption, agency and rank ecology together;
do not leave competing writers of `Person.rank`.

Record genuine absorption, confluence, awakening, ability milestone and body
transition events with stable IDs and causes at the time they occur. Eligibility
events must reference the actual prerequisite milestones. Retain blocker state
or changes when useful, not an annual event for every unchanged missing slot.
Do not backfill invented ability histories into old archives.

Keep coins in denomination-aware wallets. Introduce conservation-checked debit
and transfer operations before connecting rewards to purchases. Transactions
need actual payer/payee, denomination, amount and source. Do not assume every
merchant can exchange or accept any tier just because an integer valuation exists.
Source constraints decide which monetary conversions are legitimate; liquidity,
pricing schedules and contract amounts remain simulation approximations.

Checkpoint schema changes must be explicit. A legacy impossible magical history
cannot become canonically valid through silent normalization. Preserve old
archives as evidence, distinguish legacy snapshots, and validate corrected worlds
through new deterministic runs. No broad economy, personhood or language refactor
belongs in this phase.

## Blocking source questions

These are foundational rather than requests to choose a tuning constant:

1. Exact ability/essence-attribute/body transition sequence from Iron through
   Diamond, including lagging abilities, allowable ability lead over body rank,
   Silver-to-Gold requirements and the final Diamond process.
2. Rank-based aging/lifespan/rejuvenation rules and their interaction with
   ordinary species biology. A 108-year-old human is not itself proof of a
   forbidden state; survival probability and the applicable source rules matter.
3. Canonical confluence combination identity, divine removal/replacement
   exceptions, and tiered coin exchange/use and normal monster harvesting rules.

Relevant book excerpts or directly attributable author answers are needed to
close these questions. This audit does not authorize replacing absent evidence
with fan-wiki rules. Small stochastic rates may be approximated once hard
prerequisites are known; the prerequisites themselves must not be invented.

## Validation contract

After the specification is completed: targeted prerequisite/ownership/economy
tests, checkpoint and archive chronology tests, deterministic replay, existing
full suite and smoke checks, medium-history inspection, then one canonical
seed-843000 millennium. Keep simulation at or below 120 seconds, time archive
export separately, inspect every living Gold/Diamond and representative lower
ranks and unranked humans. Validate histories, not only final rank counts.
Explain the expected semantic digest change; never refresh a golden merely to
hide an unexplained difference. No Diamond population quota is an acceptance test.
