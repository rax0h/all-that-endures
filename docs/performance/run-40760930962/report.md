# Authenticated fixture retention and bounded first-year profile

Run: https://github.com/rax0h/all-that-endures/actions/runs/40760930962

Candidate b524bbe2ff1b697f79d7fcbf3c8a3b7d9c82efdf; runtime tree
63d5ac487d0157a5ef521b4def8ee9ce94532e0c. Retain/sample job succeeded;
full measurement job was skipped. Python3.12.15, SQLite3.45.1,4CPU hosted runner.

The downloaded diagnostic ZIP matches its GitHub SHA256. Its retained-input
receipt matches the uploaded checkpoint artifact ID, archive digest and exact
producer SHA in GitHub metadata. The original authenticated year1001 database
remains29,922,463,744bytes with SHA256
4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2.
Retained artifact12849181590 expires2026-11-27T20:23:25Z. Original producer and
acceptance authority are preserved inside the receipt. This inspection did not
download the4.4GB retained ZIP again; its upload binding and hosted authentication
are the evidence. See artifact-verification.json and retained-input.json.

| Operation | Wall seconds | Meaning |
|---|---:|---|
| Database initialization |0.002166|SQLite/store open only|
| Checked restoration |252.947046|Total open minus initialization; includes admission|
| Total open |252.949212|Exceeds repository10second mature-open target|
| First-year profile |60.000100|Censored instrumented prefix, not completed year|
| First-year inclusive operation/unwind |60.786379|Includes0.786280seconds outside profiling|
| Save, warm year, fresh saved restore |Unmeasured|Not run in this diagnostic|

Open read628,525payloads/2,304,298,297bytes and2,749,351metadata rows.
The sampled step read144,569payloads/35,198,770bytes,805,080metadata rows and
529,038pin rows. Verification-byte counters overlap payload reads; they must
not be added as physical disk IO. Input hash checks and copying are separate
phases in result.json. Source bytes were unchanged; no partial year was saved.

Within the censored profile, person-table access accumulated34.232s across27,181
calls, read_owner_identity30.486s across23,972calls, and current_people29.890s
across25calls. These inclusive times overlap and include profiler overhead.
living_household_members accounts for26.913s across17calls, with13_die calls
accounting for28.188s. Repeated living-person selection and identity loading are
concrete investigation targets. This prefix does not establish their share of
the full year, predict a speedup, or attribute save costs.

The prior454.541second open used a different run/runner with the same runtime
tree. The lower252.949second observation is not evidence of a code optimization.
Performance acceptance remains open. The next integration gate is a complete
generated-world year through the explicit proof bridge, save, reopen against
the externally held commitment and exact deterministic continuation.
