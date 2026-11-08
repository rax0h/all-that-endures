# Native rank package consolidated review register

Baseline f1ecae0; reviewed candidate 087f064 / runtime 1ca8ec8. One independent
whole-package review found four Important findings and one Minor, no Critical.
Every finding is accepted and repaired in this group; no deferred findings.

| ID / severity | Finding and concrete action | Evidence | Status |
|---|---|---|---|
| R1 Important | Projected CASE aliases caused a full live-bucket sort before LIMIT. Qualify physical source ordering separately from the bounded outer window. | Independent 100/1k/10k VM ~5200/50400/500400 before; four promoted live-bucket RED cases; all fixed cases in review-fixed.xml pass | Closed |
| R2 Important | Caller values encoded before field caps and pin validation. Validate caller snapshot first, bound immutable key shapes/bytes/depth before serialization, retain exact encoded cap. | Three large-input RED indicators preserved; stale pin RED encodes RANK/KEY; all four promoted cases GREEN | Closed |
| R3 Important | Temporary source/index shadows could serve a physical window during legitimate guarded preparation. Require persistent source resolution before entry and again in selected context. | Independent temp shadow returned key11; promoted guarded-shadow RED to GREEN | Closed |
| R4 Important | Codec hooks could end the SQLite snapshot/change source or accepted epoch after physical comparison. Bind original epoch and check active snapshot/physical epoch before return and each exclusion continuation. | Six promoted decoder/epoch/commit/rollback cases, including previously passing continuations, all GREEN; seven boundary RED failures recorded | Closed |
| R5 Minor | Missing active component context fell into legacy selection. Permit compatibility only for an identified six-root certificate; absent/unsupported active context fails closed. | Removed minimum + context None RED returned12; promoted regression GREEN | Closed |
| A1 Author fixture | UDF errors outside publisher marking had the wrong test boundary/exception wrapper. Test caught StoreConflictError inside an actual NativeWriteGuard callback. | index-native.xml and native-final.xml pass; historical native-green.log failure retained | Closed |

Independent positive probe validates 664 binary-prefix/ordinal/forward/reverse
comparisons and a seven-root reference closure retaining both aliases and
sequence members (7,8); independent-positive.log. Final focused new package:
45 passed in39.23s, review-fixed.xml. The original broad regression loaded the
pre-review source; its result is supporting evidence, not final-source coverage.

Review scope rulings: six-root compatibility stays intentional and audited;
only visited windows/lookahead are certified; synchronous neighbor has no
paused iterator, with codec reentry covered by R4; selected owner's accepted
metadata plus existing World audit preserve insertion membership. Four/five-root
standalone certificates do not authorize native World admission. Removing full
opening audits, generic query/order changes, mature speed acceptance and hosted
completion are separate gates, and are not claimed by this package. If those
gates were bypassed, unverified relations or unmeasured latency could be exposed;
they remain enforced.

R3 continuation hardening: a codec may create a TEMP shadow after the entry
check during legitimate preparation. Added a post-codec persistent-source guard
to the same epoch/snapshot check. Promoted test correctly RED after changing
cleanup to DROP IF EXISTS (the owned read rollback removes TEMP DDL); final47
new cases pass45.35s. Scalar/composite/Ref/enum key compatibility also passes.
Exact earlier259source/query/head/session cases pass231.87s; this new one-line
guard has its47-case final package coverage and will be covered by hosted suite.
Independent fixed input/shadow probe rejects shadows, allocates only10,031/
10,167bytes for8MiB rank/key rejection, and rejects stale pins before encoding.

Conversion diagnostic: an uninterrupted exact-current copy of the same generated
input now passes (serial-copy-control.log). Initial concurrent failures remain
preserved and unexplained; canonical generated-year raw/diagnostic gate still
requires a clean committed source, not this copy-only control.
