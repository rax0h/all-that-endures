# Independent scope directory review

Reviewer: review_scope_directories, fresh read-only review of f73cc86..830ff97. Independently ran46focused tests in4.92s on native Python3.12/SQLite3.45.1. Two Important findings; no Critical/Minor. Assessment: with fixes, one fix pass and affected verification; no re-review.

1. Predecessor guards ran after inherited writer reads. Oversized query name/checksum and placement checksum could allocate8–17MiB before rejection. Parent added namespace/order checksum and old version body cases. Fix: stable owned parent snapshot covers preliminary inherited reads, including identity_effective; affected source type/byte/interval guards run before those reads and repeat inside BEGIN IMMEDIATE before existing writes. Old version payload+memberships have a64MiB combined explicit bound. The inherited writer retains checksum/projection checks. New allocator extraction is guarded before transfer too.
2. Main/temp database triggers could change sources after root validation. A generation-row insert trigger deleting current queries allowed successful publication. Fix: canonical scope schema preflight rejects any main/temp trigger before publication; this also covers node/descriptor/cleanup triggers.

Review regressions:7RED failures (six unbounded-transfer cases, one trigger). Single fix pass initially53focused GREEN7.31s. Added temp-trigger and actual writer-transaction recheck cases. The recheck fixture initially left its injected mutation in an implicit transaction; corrected the fixture to commit the mutation before the existing writer BEGIN. Final55focused GREEN8.92s. Both findings are covered without a second review.

Declined-to-judge rulings and costs:

- Complete World topology, target existence/kind, canonical admission: remains required before World exposure. Physical relation roots do not supply those authorities; ignoring this would expose invalid targets/aliases.
- Complete seven-root manifest, format activation, writer fencing and collection: gated future integration. Ignoring this would mistake one component for complete generation authority or allow old writers/collection to break it.
- Full World latency/endurance: separate acceptance; user requested no endurance here. Component point saves cannot prove full mature-year/open/warm-year targets; cost is a false performance claim.
- Full archive audit materialization at explicit bootstrap: preserved as separately reported archive work. Scope source metadata guards and affected-source save guards do not bound all unrelated inherited full-audit payloads; cost is bootstrap memory/time if treated as ordinary operation.
- Arbitrary replacement of trusted private Python methods: SQL guards are not a Python sandbox. Tests use replacements to challenge actual row checks, not to claim arbitrary-code isolation; cost is false in-process security assumptions.
- Unselected physical surplus during root-selected reads: full-audit work. Logical pages come from accepted roots; cost of skipping archive audit forever is undetected physical surplus/corruption.
