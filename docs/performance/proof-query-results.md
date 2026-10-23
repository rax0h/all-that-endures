# Pinned physical query source adapter

The closed adapter now checks real pinned `lazy_query_versions` metadata against accepted ordered certificates without rereading owner payloads. It returns raw typed keys and ordinals only. No World reader, save/open path, or format capability selects it.

Source: local commit `49e7a8868c5d7849ca9fb770f8b83274880ef418`, runtime tree `de69bd0717240beb09b8d25bafda150cb8228497`. Driver/fixture hashes, environment and immutable partial/final receipts are in [proof-query](proof-query/summary.json). Python3.12.14, SQLite3.53.1.

## Actual store diagnostic

Eight active owners supply sixteen memberships, including repeated keys at distinct ordinals. Each measured page contains eight positions. Unrelated archive rows use the ordinary records table and actual store commit APIs. A separate full verification establishes test construction authority outside query timing. These are synthetic contents in real store schemas, not a mature World.

| Unrelated records | Checked payload SELECT/checks | Proof payload SELECT/checks | Proof node SELECTs | Proof heap peak | Checked / proof time (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 8 / 8 | 0 / 0 | 21 | 21,332 B | 2.11 / 5.65 |
| 10,000 | 8 / 8 | 0 / 0 | 24 | 21,557 B | 1.62 / 4.78 |
| 100,000 | 8 / 8 | 0 / 0 | 23 | 21,676 B | 1.67 / 4.96 |

All results and continuation positions match both the checked reader and literal expected keys. Each proof page uses eleven query SELECTs: two ordered seeks plus nine constant-only exact-position interval witnesses, including lookahead. This proves removal of owner-payload work for this metadata operation as unrelated records grow. The proof reader is slower for these tiny payloads; no elapsed speedup is claimed. Reads run sequentially with warm/uncontrolled caches and provide no latency distribution. Lifetime peak RSS includes construction, full verification and prior cases; see per-case receipts.

## Validation and failure evidence

240 affected tests passed in16.22s: all proof modules plus incremental store, lazy-store failures and actual pinned-store regressions. The36 source-adapter cases cover independent binding vectors, current/previous pins, cursor/page completeness, repeated keys, wrong authority/context, physical row faults, transaction ownership and raw-metadata admission boundaries.

Three retained RED memory regressions demonstrated >4MiB allocation before rejecting2MiB malformed metadata. SQL storage-class and byte-length guards now prevent transferring those bodies; all three pass below128KiB traced heap. The initial missing-module RED and subsequent proof-suite GREEN are retained alongside the diagnostic.

## Authority and remaining integration

An expected certificate commitment is mandatory and must ultimately come from an accepted outer manifest/directory. A self-hashed SQL projection is not completeness authority. Only explicit test/diagnostic construction exists here, after full verification. Default checked readers remain unchanged.

The fast metadata path caps each encoded key at4096 bytes and raises `QueryProofBudgetError` for larger keys. A separately budgeted certificate-checked path is required before World integration. Metadata checks do not authenticate or expose owner payloads: eventual exact content-root admission remains mandatory, including when an unread owner payload is corrupt.

Physical owner/group/link/namespace adapters, accepted generation manifests, retained immutable payloads, verified-copy upgrade/writer fencing, atomic changed-row/root/head publication, recovery and World admission remain integration gates. Interactive targets (warm year <=1s, incremental save <=2s, open <=10s) are still unproven. See [next integration](proof-map-foundation/NEXT_INTEGRATION.md).

The [fresh review](proof-query/final-review.md) found one Important overlap defect, repaired in one RED/GREEN pass. Four boundary regressions reproduced acceptance; all five added cases now pass. The refreshed receipts above supersede the retained pre-review measurements. Successor CI launch will be retained before handoff. The accepted parent run39878709646 remains separate evidence:3220 tests plus2 subtests, not a result for this new package.
