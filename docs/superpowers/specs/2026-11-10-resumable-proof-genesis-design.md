# Resumable mature proof genesis

## Intent and evidence

User requires completed verified work to survive failures, successful tests to be
reused when their code is unchanged, and cheap bounded checks before expensive
work. Existing hands-off authorization covers implementation/CI on the current
branch. The choices below are engineering decisions, not new user approvals.

42823293423 at9e6f022/runtime94267 passed both prerequisite jobs, then exhausted
12600s construction budget at canonical_digest.before_rebase. Capture/physical
validation took~99min; catalog/reference checking finished~99min later. Only
~13min remained for digest, rebase, second digest and all proof builders. The
existing210min aggregate was not a defensible completion budget. Original bytes
were unchanged; no operational/save measurements were reached. Raw authenticated
failure is review-raw/timeout-42823293423. No repeat of that monolithic request.

## Approaches and decision

1. Raise the monolithic limit: retains loss of all preparation on failure and
   lacks evidence later phases fit; rejected.
2. Refactor runtime persistence into a new general checkpoint API: expands
   behavioral surface and invalidates green engine tests; unnecessary here.
3. Selected: offline staged harness around exact unchanged runtime94267. Durable
   closed SQLite artifacts and strict metadata receipts separate completed work.
   Reuse exact green engine jobs; validate only new harness/workflow changes.
   Extra transfer/hash/storage overhead is accepted to protect hours of work.

## Stage contract

Format6 only. Stages: source_digest -> capture -> catalog -> rebase ->
after_digest -> proofs -> measure -> fresh_restore. Move the baseline canonical control to the
original authenticated source working COPY. Native current capture and catalog
checks preserve logical World data; post-rebase digest must equal this stronger
original-source control. A digest receipt grants no source/catalog authority.
No legacy conversion/normalization is admitted by this harness.

source_digest and after_digest are read-only logical computations on disposable
copies and retain the prior immutable database reference. Capture/catalog/rebase/
proofs produce closed database checkpoints. Every phase starts from authenticated
closed input; no writable input hardlinks. The catalog capture adapter may replace
exactly one copy_current_head call only, from the already checked capture's exact
bytes into the helper's exact requested private destination. Validate path, codec,
schema, rules, bool option, generation and one-call count; restore before return.
All catalog/roster/reference/type/sequence/retired/graph checks still run.

Rebase retains its real pre-audit. Proofs retains a fresh real post-rebase audit
inside the existing six-builder owned transaction, final full World/source/proof
correspondence and final physical/FK checks. SQL audit certificates NEVER survive
processes. The six-builder transaction is one indivisible failure unit; failure
can discard that stage, while earlier checkpoints remain reusable.

Canonical field progress adapter yields exactly the original field pairs, reads
no values and changes no byte ordering or digest. First source digest is bounded
before the~198min preparation prefix. Budget expiry is censored and prevents
later jobs from starting. It is not a successful canonical control.

## Durable inputs, receipts and provenance

A metadata artifact contains checkpoint.json with schema/stage, semantic context,
original source hash/size/UUID/head/year/seed/rules, rank=true, runtime tree and
critical producer-code blob fingerprints, input receipt hash, root baseline digest,
current closed DB hash/size/UUID/head/format and reference to its immutable data
artifact. Data and metadata are separate artifacts, so read-only stages reuse a
large database without re-upload. Receipt parent chain is embedded/bounded and
validated for exact order/context; partial/unknown stages cannot advance.

Consumers authenticate artifact id/name/run/head/workflow and exact producer
attempt, expiry, archive hash/size, and exact regular-file inventory. Checkpoint
custody requires a unique completed producer job with successful, uniquely named
data-upload (when required), provenance-seal and metadata-upload steps in that
order. Artifact creation must fall within its upload step, and the ordered steps
must fall within that job. A later diagnostic or post-job cleanup failure may
leave this already committed checkpoint reusable on an explicit resume; the
current failed workflow DAG still stops. Diagnostic uploads are nonfatal, while
data upload, sealing and metadata publication remain fatal. Original full-suite
and proof-map green reuse separately requires those exact jobs to have succeeded;
this checkpoint custody rule does not relax either gate.
Producer code must be ancestor-compatible with unchanged runtime and exact
critical harness/workflow blobs. Changed algorithm/context, corrupt/extra bytes,
expired input, missing checkpoint, mixed branch/mode or invalid parent fails before
engine work. Metadata bounds and disk headroom are checked before bulk restore.
Credentials are never sent to signed cross-origin URLs.

Green reuse binds successful proof-map and full-suite jobs in42823293423 to9e6f022,
its runtime94267 and authenticated source.json receipts; the overall run's mature
failure is not a reason to rerun those successful jobs. Smoke/mature contexts are
separate and cannot promote into each other. New targeted harness CI is mandatory.

## Workflow and operational limits

New workflow only; old monolithic request and engine paths remain unchanged.
Push runs small smoke; workflow_dispatch explicitly selects mature or smoke and
optional resume run. Gate discovers the last successful compatible checkpoint,
skips only preceding verified stages and resumes its immediate successor. Each
stage uploads a closed DB where changed, then a sealed metadata artifact; no
partial stage authenticates. The measure request's aggregate deadline covers its
working copy, open, first year, save, warm year and close. Individual phase caps
also apply using the remaining aggregate time, without nested alarms. Upload has
reserved wall time beyond phase budgets.
Per-stage source/copy/disk/hash/compute budgets and worst lost work are explicit.
No promise that an unfinished transaction, machine loss or expired artifact can
resume; no promise of constant whole-conversion memory or mature interactive speed.
Checkpoint references expire with GitHub retention and are checked before work.

A real small hosted smoke must exercise upload/download and continuation before
mature dispatch. Smoke verifies exact original-source vs post-rebase digest,
shared identity, no replay of completed work, output fresh-process continuation,
and failure/recovery; it does not establish mature latency. New mature attempt
must reuse green engine validation and start with the known blocked digest stage,
not repeat the expensive capture/catalog prefix blindly. It remains outside
Stage0.6 acceptance until10sopen/2ssave/1swarm targets and exact saved1002digest pass.

## Non-goals

No main merge/default activation/endurance, no weakening audits, no general save
format migration, no arbitrary persistent source certificate or ZIP provenance
shortcut, and no automatic unbounded retry. Later bottlenecks require evidence
from their bounded stage; do not pre-emptively redesign the persistence engine.
