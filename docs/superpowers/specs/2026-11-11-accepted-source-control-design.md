# Reuse the accepted source control after the bounded digest timeout

## Intent and evidence

Continue authorized Stage0.6 completion without repeating accepted work or
weakening current integrity checks. Mature run42964119253 stopped in source_digest
at its3600s limit, during social decoding. The timer exception was wrapped by
CodecError; receipts incorrectly call this an error. No capture/catalog/rebase/
proofs/operational stage ran. The source hash was checked in cleanup. Authenticated
raw logs, phase resources and field progress are in resume-repair/failure-42964119253.

The exact source database SHA4a39288b.../29,922,463,744bytes/year1001/gen126 already
has an authenticated accepted canonical digest57f60fdf49e221af24ffc0a1f2d5a3885dd37c07db00d153171adcb91c579eed.
Its actual accepted/year-verified.json is retained by the original authenticated
carrier. Existing prepare_retained validates the full original chain. This
accepted expectation is independent of the current reader.

## Approaches and decision

1. Repeat the full original digest with a larger limit: repeats an accepted
   source control and leaves the same independent control unused; rejected.
2. Serialize/resume arbitrary canonical hash state or introduce field artifacts:
   expands the serializer/transport protocol and storage overhead; unnecessary
   for an already accepted unchanged source.
3. Selected: mature source_digest imports only the historical canonical expectation
   from the actual authenticated accepted receipt. Preserve the actual current
   post-rebase canonical comparison and every current source/catalog/proof audit.

These engineering choices follow existing hands-off authorization. No change to
simulation/ate_sim, old trigger paths, compatibility semantics or magic rules.

## Source-control contract

The production launcher must first run unchanged full retained transport/chain
authentication. Read the actual accepted member with exact570001bytes and
SHA5e54ce0e4e27b6d3a17cb22ce4fda887e5f1ee9cde6c052ab2d270144367ef45,
as pinned in the unchanged save1002 preflight. Validate year acceptance and exact
original acceptance producer, candidate artifact, DB bytes/hash, UUID, generation,
year, rules/seed authority, audit and digest receipt chain. A repository summary,
bare digest string or claimed metadata match is never acceptance authority.

Only the canonical expectation is reused. Label metrics historical-control-reused;
do not claim a newly computed current digest or source audit. Smoke retains its
actual original digest, and also exercises the accepted-control route on a real
small source. Exact before/after source file hashes remain required. The current
post-rebase digest must equal the historical expectation before proof construction.
Codec/canonical/schema compatibility must fail closed; the unchanged encoder,
World fields and declared format6/rules path are fenced by the launcher. A change
requiring different semantics needs an explicit migration, not a new expected hash.

## Honest timeout and budgets

A harness-local Recorder tracks whether its own alarm fired. If a lower layer
wraps the alarm exception, surface BudgetExpired and preserve the original chain
before the shared recorder writes its single immutable final receipt. Ordinary
CodecError remains an error. Do not modify shared old benchmark/runtime helpers.

The observed original scan is incomplete after60min; it cannot justify a60min
full post-rebase/fresh digest ceiling. Use120min compute and180min job limits for
after_digest and fresh_restore, keeping30min restore and metadata publication
reserve. These remain bounded unfinished stages, with their prior DB checkpoint
retained. This is an evidence-based offline verification limit, not an interactive
latency target or guarantee. Do not repeat the mature source scan.

The successful smoke took20min24s with repeated large-run disk cleanup. Restrict
that cleanup to mature workers; all per-stage disk/size checks still run for both
modes. This reduces repeated small recovery-run overhead without changing mature
capacity preparation or its acceptance gate.

## Verification and scope

RED/GREEN: real accepted small receipt reuse and mutated hash/binding/digest/
producer/schema rejection; no World open/copy/digest for imported control; actual
small post-rebase digest equality and false-control rejection; real wrapped alarm
classified timeout, genuine malformed payload still error; workflow cleanup mode
and budget reserves. Use the complete qualified313fingerprint. Run the new/affected
harness suites, then the same independent whole-package reviewer closes every
finding in bounded-genesis/closure.md. Engine94267 and exact9e6green full/proof
jobs remain unchanged. First publish small hosted smoke; only after its real
transport/recovery/accepted-control success may a new protected mature request run.
Stage0.6, main/default activation and endurance remain outside this local closure.
