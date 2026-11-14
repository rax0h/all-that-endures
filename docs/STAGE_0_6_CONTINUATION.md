# Stage 0.6 continuation

Active checkout `/workspace/scratch/d88f8db353e8/ate`, branch
`sol/durable-proof-map`. Other checkouts are historical/measurement baselines.

## Current candidate

Coordinator publication read scope, local engine commit41291bc8feabcdad58d33d118428f93fb2ea99c8,
runtime030b9c934f5ea4f59101d6f6677216aa7b52a03e. Only production change is the
outer CoordinatorSaveParticipant validation context: use existing closed
checked_read_operation with min(256KiB,catalog.byte_limit//6). All frozen-row,
root, pin, epoch, corruption and recovery checks remain; no new cache/certificate.

Actual native32-person metadata RED147head checks→GREEN≤10. Independent review
found one Minor budget regression, reproduced and fixed; custom128budget now
scope21/retained0. No actionable finding remains.44focused+160additional related
cases pass, source/XML/log/runtime/reviewer fences verified. One hosted proof/full
gate is required before accepting this candidate. Read publication.json beside
the report for the exact published source/run; later pointers are docs-only.

Fresh current-engine attribution and two pinned raw pairs are in
performance/stage-0-6-current/save-phase-attribution/report.md. Acknowledgement
SQL102387→88855; preparation/commit SQL unchanged. Saves4.268→4.099s and
4.431→4.211s. A modest same-input observation, no mature/overall/interactive claim.
The next action is checking this exact candidate's hosted gate, not starting a
new optimization or repeating a completed constructor prefix while CI is active.

## Last accepted engine

Published457a619f84f6610f9b965829b2be8cb8389c5f9b/runtime95c61911fedd093119439bc9d8d80c1d4f896738
is GREEN43501337447:5115passed+2subtests, proof34XMLs1960overlapping tests plus
scaling. Source/artifact/XML/hash receipts in rank-ecology-lifetime/hosted-43501337447/.
W11 rank-up and W12 annual-lifetime engine gates CLOSED. W13 parent batching was
not promoted; source prototypes/eight raw trials remain in content-parent-batch/.
Do not resurrect that experiment or claim its lower node count as a whole-save win.

## Open goals and inputs

Stage0.6 remains OPEN: mature10sopen/2ssave/1swarm, exact state/deterministic
continuation. No mature/default/main/endurance activation authorized here.
First-playable interpretation is a separate note in save-phase-attribution/;
annual throughput is not player input latency, and no interactive UI/background
responsiveness has been demonstrated. Do not relax formal acceptance implicitly.

Use unchanged complete-qualified313 fingerprint. Original small input
SHA2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554 must only be
opened through disposable copies; native pin bookkeeping changes bytes. Archive
expires December11. Preserve compatible outputs; inspect prior durations and
reserve full stage/cleanup/publication budgets before expensive work.
Consolidated register: performance/stage-0-6-current/bounded-genesis/closure.md.
