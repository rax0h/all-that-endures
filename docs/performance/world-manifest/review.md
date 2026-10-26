# Whole-package review and rulings

Scope: 046992d22136fdb8079a760c8e935b641788677a..b920b786ecb5742dba964787721bd3f5d939c179.
One fresh read-only Astra/high reviewer (`review_world_manifest`). Verdict: 0 Critical,
4 Important, 0 Minor. The reviewer independently ran six checkpoint/recovery/retained/fence
cases (14.47s); this was not a fresh whole-suite run. No second review is claimed.

## Important findings — one fix pass

1. **Family root types.** A coherent list target could replace a map-valued currency
   wallet because only registered record classes were enforced. Validate non-record
   family values from their declared root types, exact graph-bucket kinds and existing
   scalar-map key/value rules. Cost: full-audit metadata/type checks, no checkpoint work.
   Regression cases cover wallet map, genealogy list bucket and scalar claim index.
2. **Backed record fields.** The auxiliary record-header adapter checked closed values
   and schema, but skipped consuming field annotations. Apply the same field-reference
   validator to checked header class/values without restoring a native object. Cost:
   explicit full-audit header checks only. Regression uses a real runtime-created nested
   SkillHistory whose teachers list is replaced by a coherent map reference.
3. **Retired query rebasing.** Membership retirement ordinals became zero while matching
   lazy query ordinals retained their old generation. Rebase both and recompute the query
   checksum. Cost: the already explicit private-copy rewrite. Regression deletes both
   shared-history skill owners, retains unplaced groups, audits and copies the source,
   then verifies exact query/membership consistency at generation zero.
4. **Cold layout cardinality.** Coherent publication could claim 102 skill owners with
   only two physical owners. Reuse the complete cold head-inventory contract, validate
   declared layout kinds/counts and compare compact Event-ID/packed-action logical sizes
   to their actual descriptors/payloads. Cost: explicit audit metadata and two singleton
   bodies; unchanged checkpoint reuse remains body-free. Regressions cover lazy skills,
   ordinary settlements, packed actions and compact Event-IDs, including atomic rollback.

Test development corrected three fixture confounders before asserting the reproduced
bugs: used an empty map to isolate bucket kind from member policy, used an unrelated map
to avoid introducing a backing cycle, and excluded layout metadata from identity-owner
inputs. The corrected pre-fix probes accepted all three wrong family values and the
wrong backed-record field; the retired-copy probe failed with incomplete query membership;
all four invented layout counts were accepted. These are the intended RED observations.

Final GREEN evidence is in verification.json. This is executor validation after the
single review, not reviewer approval of the amended source or exhaustive adversarial coverage.

## Declined areas — explicit rulings

- Mature latency, interactive saves and bounded-memory construction: outside this
  producer package. Keep format7 native open blocked and changed-World full audit explicit;
  integration must replace that expensive path before performance acceptance.
- Ancestor CI authentication and executor suite/matrix reruns: reviewer did not reproduce
  them. Retain accepted archive digests/source checks separately and require fresh hosted
  CI for this candidate; local suite evidence identifies its own source.
- Inherited current/legacy copy guarantees: reuse the existing checked-copy engine and
  related regressions; new pre/post-rebase canonical digest equality is required. Its
  full-capture cost remains construction work, with no bounded-memory claim.
- Partial retirement jobs, mixed inline/backed identities, cyclic backing graphs and
  inline World key/set reference routes: fail closed with explicit unsupported paths.
  Dedicated support would require separate contracts; no success flags or guessed roots.
- Node collection: deferred. Retain nodes and protected roots; storage growth remains
  until reachability/protection and collection are implemented and validated.
- Release readiness and main integration: not claimed. Publish this inactive producer on
  the dedicated branch; no main merge, ordinary activation or endurance run.
- Exhaustive family/immutable-lifecycle adversarial coverage: not claimed. Existing full
  source/catalog/type/sequence checks plus the concrete regressions establish the tested
  domain; native integration still needs real participant, alias and interaction cases.
