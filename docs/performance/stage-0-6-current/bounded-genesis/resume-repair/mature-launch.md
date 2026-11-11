# Protected mature launch

Prerequisite smoke42961490569 atb79039d passed all10jobs. Hosted156affected
tests passed139.74s. Actual upload/download, mid-rebase exit77, unchanged retained
catalog, ordinary-process retry, matching source/post-rebase digest, six-builder
proof construction, saved generation1 publication and separate fresh-process
verification all passed. Final acceptance is smoke-functional-only, not mature
performance acceptance. Authenticated raw evidence is hosted-smoke-42961490569.

Mature request changes only scheduling configuration. Runtime94267, all42critical
producer dependencies and all tests remain identical to the successful smoke.
Both9e6green prerequisite jobs are reused by exact IDs/source/archive hashes;
the failed parent run does not require another full simulation suite.

## Failure and restart contract

The restart unit is one unfinished stage. Only completed, closed database and
sealed metadata artifacts grant a restart point. Every next worker authenticates
the exact code, software, context, ordered parent receipt and archive bytes.
Read-only stages retain their prior database reference. The measure stage publishes
the saved generation1 database before fresh_restore. Failed current DAGs stop;
an explicit resume selects the latest committed compatible checkpoint without
replaying its prefix. No automatic full restart or unbounded retry is scheduled.

The proofs stage is one indivisible existing six-builder transaction with fresh
audits and final World/source/proof/physical checks. A failure inside that
transaction can lose that stage's unfinished work. Earlier checkpoints survive.
No persistent SQL audit memo or weakened source audit is introduced.

## Limits before expensive execution

| Stage | Compute limit (min) | Restore limit (min) | Job limit (min) | Published database |
|---|---:|---:|---:|---|
| source_digest | 60 | 30 | 120 | Reuses authenticated original |
| capture | 150 | 30 | 240 | Closed capture |
| catalog | 150 | 30 | 240 | Closed checked catalog |
| rebase | 150 | 30 | 240 | Closed rebased generation0 |
| after_digest | 60 | 30 | 120 | Reuses rebased database |
| proofs | 210 | 30 | 350 | Closed proof generation0 |
| measure | 15 | 30 | 150 | Closed saved generation1 |
| fresh_restore | 60 | 30 | 120 | Reuses saved database |

Database upload has45min and metadata upload5min; read-only stages only upload
metadata. These are reserved outside the declared compute budget, within the job
limit along with setup, hashing and provenance checks. The measure aggregate
deadline covers its copy and every operational phase. Disk/size gates precede
stage work. Limits bound loss and stop a stage; they are not completion estimates
or a guarantee that an unknown mature operation fits. Source digest runs first
because it was the last unknown blocker in the failed monolith, before rebuilding
the expensive capture/catalog prefix.

Available input metadata was rechecked before launch: original carrier12849181590
expires2026-11-27T20:23:25Z; green full-suite13778449621 and proof-map13774870495
expire2026-11-24T15:48:44Z and14:39:46Z respectively. New checkpoint artifacts use
30day retention. Receipt/code/software compatibility and expiry are enforced again
by each consumer. Missing/expired/incompatible inputs fail closed rather than
silently rerunning hours of work. Availability metadata and hashes are retained
in hosted-smoke-42961490569/mature-input-availability.json.

## Remaining acceptance

Mature open<=10s, save<=2s, warm year<=1s, exact saved1002digest and separate
fresh-process validation remain unmeasured. A known failed speed target stops
before a further deep restore/digest while preserving the saved checkpoint.
Stage0.6 is open until these real mature gates pass. No main merge, default
activation or endurance execution is included.


## Historical execution checkpoint (failed)

Published mature request78bf9b1b6033c789078446c08f5d371e6120b805 launched
[run42964119253](https://github.com/rax0h/all-that-endures/actions/runs/42964119253).
Its gate passed: targeted156tests, actual compatible smoke authentication,
exact green prerequisite reuse and retained-original producer availability.
Gate selected mode=mature, resume_index=-1, has_database=false, fresh=true.
The first mature worker is source-digest (job130337978833). It starts with the
original-source digest and cannot start capture/catalog until that control passes.
No mature phase duration, speed target or Stage0.6 completion is claimed yet.
Use this run's compatible committed checkpoints for any explicit resume; do not
restart the old monolithic workflow. The complete gate log is
mature-gate-42964119253.log. A later documentation-only commit does not change the
worker's pinned78bf9b1producer source or its42critical dependencies.

Run42964119253 subsequently stopped in source_digest at3600s. No capture/catalog/
rebase/proof/operational phase ran. CodecError wrapped the owned budget exception;
raw failure evidence is failure-42964119253. The November11 accepted-source-control
design supersedes repeating this historical scan. Its new candidate must pass a
compatible hosted smoke before another protected mature request; Stage0.6 remains
open. The actual post-rebase/fresh deep verification budget is now120min with a
180min worker limit, based on the observed incomplete60min original scan.
