# Fresh review and executor disposition

One gpt-6-astra high fresh read-only review of5a96c4f..e51ddde; no repository writes or expensive suite/scaling repeats.

Strengths: mandatory external expected authority; raw bytes/allocator/pin binding; cross-incarnation exact-placement overlap checks; injective SQL-compatible zero/prefix ordering; guarded namespace UTF8; physical boundaries; explicit transactional source index construction.

Important1: four ordered index checks did not enforce inherited exact-placement/state interval indexes or cached capabilities, allowing legacy scans of expired history. Fixed by exact canonical SQL/index-capability preconditions before interval probes. Four regression variants reproduced RED.

Important2: old-pin current stream filtered valid_from<=pin after ordering, scanning arbitrarily many newer rows despite LIMIT. Reviewer measured5059/50059VM instructions at1k/10k new rows for an empty old group. Fixed with bounded ordered candidate fetch and explicit OccurrenceProofBudgetError when newer head rows intervene. Two regressions reproduced RED. No partial result or fallback is returned. The generic old-pin path remains a mandatory integration gate.

Supporting Minor: original current-only diagnostic counted SELECTs/plans but did not measure skipped rows/VM work. Addressed as part of Important2: driver now measures old/current pages and1k/10k/100k newer frontiers with bounded VM counters. No separate deferred minors.

Critical:none. Two Important findings accepted/fixed in one RED/GREEN pass; no re-review. Candidate suite/measurement results to be retained separately. No main merge/World activation endorsement.

Declined-to-judge items and executor rulings: World/data-owner admission; complete owner/group agreement and payload reference projections; headers/links/retirement; production certificates/manifests/retention/atomic publication; large-field and general old-pin selection; mature save performance; candidate CI. All remain explicit gates. Cost if these rulings are wrong is further integration before activation, not weaker authority in the current World path.
