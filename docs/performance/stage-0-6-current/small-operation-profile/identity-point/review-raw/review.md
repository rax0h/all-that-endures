# Independent whole-package review: placement-read experiment

Verdict: no concrete Critical, Important or Minor safety/correctness finding in
the reviewed bounded candidate. Its exact occurrence proof satisfies the existing
decode placement comparison under the admitted proof-only authority. Reject this
candidate as a standalone latency repair: preserve its source diff, tests and raw
evidence, then restore the already validated engine. Do not infer a useful speed
gain, run a new full CI cycle, or launch mature work from these results.

This is the one independent whole-package review for W5 in the existing
bounded-genesis group. No further reviewer, delegation, CI, publishing or engine
edit was performed. Review writes are confined to this review-raw directory.

## Exact reviewed source and evidence

Base HEAD: 46494a0197994a9547c6f8c30f2a70bf7ffc943c. Published counterpart is
7261d61577f7c2bb09282b226c2f67508e9f4576 with baseline engine0785bf9.
The candidate modifies only these two runtime files:

| File | SHA256 |
|---|---|
| persistence_lazy_identity_coordinator.py | e7a22d534544e849bdbc622e5532f02c69c4ee57c6f318c83f6e605338425859 |
| persistence_history_runtime.py | 7497721858523d93d4473ecfbc0d2e3c2ce92bd82e496091e03aeec52c6345b1 |

evidence.json captures every runtime source hash, test/spec/plan/driver hashes,
diagnostic evidence hashes, saved/continued semantic values, and the complete
qualified software fingerprint. Candidate raw and profile runtime inventories
match these exact sources; baseline differs only in the two files above.
The full Python3.13.5/GCC14.2.0/SQLite3.46.1 fingerprint was independently
recomputed, including executable, extension and loaded library hashes, source ID
and compile options, and matched the mandatory qualification record.

Reviewed package includes both production edits, the19-case regression module,
design/plan, initial failed fixture logs and corrected controls, raw pair and
separate profile, report.md, the predecessor architecture review, and W5 closure
context. Hosted43099834661 source/summary records establish baseline-only greens;
they are not candidate engine validation.

## Why the point proof is sufficient here

The only changed consumer formerly extracted one incarnation from
_owner_changes(owner,()). It still synchronizes first and compares the result
with the reference incarnation before binding. New/private child retention and
the in-progress sequence rollback exception remain before that comparison.
Subsequent nonreflexive/record group discovery, event-ID authority loading,
history kind checks, registry canonical lookup and occurrence attachment remain
unchanged. Mutation validation, subtree replacement, synchronization, retirement,
save and recovery still use their complete affected closures.

Selection uses active(store), which accepts only the exact native authority
class, then its admitted boolean proof_only mode. Ordinary/audited modes still
execute the old complete _owner_changes implementation. Placement shape is
validated before the selected point API. No retained certificate or cache was
introduced by this candidate.

read_identity_occurrence starts the caller's checked snapshot and validates its
actual pin. Native point_row joins the accepted component certificate and
manifest allocator, validates physical allocator/interval/checksum metadata,
proves exact owner-scope membership, and, for a present row, proves the same
occurrence under the accepted group root. Missing physical rows are accepted
only when the authenticated owner root also proves point absence. A present
physical row absent from that root is rejected. The accepted manifest already
supplies global relation authority; this read need not rediscover the entire
owner catalog to answer its one placement comparison.

Native snapshot entry retains epoch, store/codec, pin/head/generation/retention,
uncertainty, persistent-source and callback boundaries. The physical point read
always precedes overlay access, so replacement, deletion and no-op/absent
overlays cannot suppress its failure. Only the API's authenticated-absence
KeyError is converted to None. Other integrity/conflict errors propagate.
There is no new callback or yield between point proof and overlay selection.

This is an exact-point guarantee, not a fresh inventory of unrelated owner
placements. Untracked physical drift normally fails the accepted epoch gate.
Tests that deliberately reset that gate demonstrate deeper proof rejection at
the requested point; they do not claim to detect every unrelated corruption
after manually replacing internal authority state.

## Independent verification and fixture limits

The independent six-case suite passed6.37s. It exercises present replacement and
tombstone overlays after physical row deletion, absent-point replacement/no-op
deletion after coherent physical row insertion, malformed paths, unknown/stale
caller pins, both publisher/SQLite callback guard states, and actual decode with
wrong incarnation or wrong live kind. Each rejection leaves no open transaction.
The absent deletion is intentionally a no-op under ordinary overlay semantics.
verification.log/xml preserve the actual result and test_independent_boundaries.py
preserves the probes. These probes ran after root's raw/profile captures ended.

Root's preserved focused result is19passed29.45s; its strengthened work assertion
counts all _owner_changes calls rather than just decode's direct caller and
separately passes1.44s. Do not add overlapping test totals. Unsupported nested
cold conversion and seeding both owners into a separately refused last-owner
retirement path were fixture failures. Corrected tests use actual decode on an
admitted reference and seed only skill1, retaining skill2's old history. No
production bypass, expanded conversion support or retirement fix is claimed.

## Performance conclusion and disposition

Independent parsing of reports confirms identical authenticated inputs, source
preservation, saved generation1/year2/seed843000/digestcebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451,
and separately restored/continued year3 digesta46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3.

Raw baseline/candidate warm times are9.544/9.150s and save7.852/8.176s. One pair
does not establish either a useful latency gain or a distributional regression.
Callcounts explain why removing1002owner calls is not removing1002inventories:
read_owner_identity1296→294, _owner_epoch1541→374 and _remember_owner245→80
show1051→214 existing standalone-cache hits and only165fewer miss completions.
Native point_row400→1402 and context/state1941→2613 replace much of that already
cached work. SQL execute calls fall458816→416146, but counts alone do not prove
the required latency outcome. The older baseline profile is suitable for this
same-source callcount attribution, not a controlled wall-time comparison.

The rejected-experiment disposition in report.md is appropriate. Preserve the
candidate as evidence, remove it from live production/tests before claiming the
baseline restored, and keep W3/U10 mature acceptance open. A future bounded
closed-read/batch experiment needs its own concrete authority/custody design and
measurement; this review does not approve or implement it.

## Findings and declined judgments

Critical: none. Important: none. Minor: none. No actionable finding is deferred
out of the current group. The failed performance selection is documented W5
experimental outcome, not an unclosed safety defect.

Declined to judge: mature scaling or interactive targets; repeated-run latency
distribution; complete candidate full-suite/hosted compatibility; unsupported
cold recursive conversion or full old-history retirement; corruption outside
the accessed proof after manual authority replacement; any proposed future
validation cache/batch. Source restoration and packaging are checked below.

## Final restoration check

After the candidate review, root preserved candidate.patch and candidate-tests.py
and restored production. Independent restoration.json verifies that the complete
current runtime inventory exactly equals the captured baseline, both edited files
equal HEAD byte-for-byte, the archived candidate test matches its reviewed hash,
and there is no tracked simulation/workflow diff or live candidate test module.
git apply --check confirms the archived patch applies to this restored baseline.
The final report and consolidated W5 register correctly close this as a rejected
experiment with no new engine authority or mature launch. No remaining finding.

The candidate-only verification scripts intentionally describe/run the captured
experiment, not the restored live runtime. To reproduce those probes later, use
an isolated baseline, apply candidate.patch, and restore candidate-tests.py to its
original simulation/tests/test_stage_0_6_proof_placement_reads.py path. Do not run
the archived candidate test expectation against the deliberately restored engine.
