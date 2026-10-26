# SDD ledger — plan: docs/superpowers/plans/2026-10-26-ate-world-manifest-production.md

Baseline046992d, hosted run40275423651 accepted4211 full simulation/1115 proof tests,26 complete scaling matrices with archive digests/source/hash/XML checks.

Pre-flight: audit consumes complete-format sources plus existing proof components; copy produces a new coherent generation0 source; manifest writer consumes exact same-generation audited roots after inventory publication. No predecessor manifest may be invented for an existing positive generation.

Ruling: retain generation0-only genesis and create a new source-preserving store identity — existing positive generations cannot be trusted without their actual parent manifests — rebasing is private copy construction, never mutation of the source's history.
Ruling: use established explicit full audit for changed complete World authority until native integration supplies affected-owner transitions — this establishes production correctness without pretending the existing selected-closure bounds cover arbitrary World history — changed World production remains expensive and cannot be activated as an interactive save.

Implementation progress before review:
- Real complete World audit/source fixtures, genesis-only manifest construction, source-preserving new-identity copy with revision/checksum rebasing and pre/post canonical digest equality, fenced format7 and ordinary World admission block implemented.
- Same-writer manifest publication, exact recovery, retained manifests, five bound context roots, global owner/backing/physical-child joins and actual field/query contracts implemented.
- Canonical topology excludes mutable scalar bytes; structural counts remain bound. Orders bind lazy collections, ordinary envelope ordinals, checked history descriptors and entry query order.
- Full source audit authenticates all actual content and reconstructs all six scope roots/complete lazy directory against accepted component authority, not just their stored hashes.
- TDD initial missing APIs; subsequent RED regressions proved altered component context types, format-floor injection, wrong native record class, wrong field container kind, forged query projection, stale head metadata, ordinary ordering omission, scalar topology pollution, missing scalar source, frozen mutation, structural-length omission and cyclic graph acceptance. Fixes under focused verification.
- Last completed focused suite before final structural/cycle/frozen fixes:26/26 passed46.11s; latest26-case rerun pending. No hosted CI started during this package.

Ruling: sealed Event roots use the established immutable identity projection while their typed frozen-data references remain checked — matching existing complete-format catalog semantics — counting sealed Events as mutable creates false corruption reports.
Ruling: ordinary query rows are rejected for current World format because it has no declared ordinary secondary-query source contract; declared lazy projections are recomputed using existing runtime helpers — accepting arbitrary coherent query rows would certify an invented query meaning.
Ruling: topology binds kind/schema and structural descriptors plus complete physical/owner scopes, not scalar payload fingerprints; complete source roots separately bind bytes — including payload hashes in topology would defeat content-only reuse.
Ruling: source construction/full changed-World audit remains explicit history work, including the existing current-copy engine's full capture — checkpoints reuse facts and do not claim interactive ordinary saves — native integration must replace changed-World full audits before activation.

Task1/2: complete —26 focused cases passed61.25s, then46.11s after format-type/fencing validation. All noted RED contracts are GREEN: namespace classes/field kinds/query derivation/head scalars, source/digest preservation, immutable edits, cyclic graphs, structural cardinality, ordinary ordering, topology/content separation, root context types, before-head/before-commit/after-commit and reopened recovery. Source/driver/workflow checkpoint follows; full proof/runtime suites and scaling next.

Review checkpoint b920b78: fresh Astra/high,0 Critical/4 Important/0 Minor.
One fix pass addresses all four: consuming family kinds/scalar maps, recursive backing
field kinds, retired query ordinal rebasing, and complete effective layout cardinality.
Corrected RED regressions independently reproduced each issue (including four publication
count variants); three initial test-fixture confounders are documented in world-manifest/review.md.
Rulings and costs for every declined review area are recorded there. No second review requested.

Final corrected-source verification:1151 proof tests passed565.03s (including all35
World cases),125 related runtime/copy tests passed216.13s,0 failures/errors/skips.
All12 changed runtime/test/driver/workflow SHA256 values match the execution source.
The four Important findings are GREEN, including all nine regression variants.
Task3 review/fix pass complete; clean-source checkpoint matrix and publication follow.

Task3 final checkpoint matrix:all1k/10k/100k retained-value cases complete on corrected
runtime18bccc1a775299e6770c051437e8be7035b9173d,zero history bodies and no
reaudit,under2million interval-one SQLite VM steps and4MiB measured Python peak.
Construction and checkpoint times remain separate; exact data in world-manifest/scaling/.
One bundled publication follows. Hosted full-suite/27-matrix acceptance remains pending.
