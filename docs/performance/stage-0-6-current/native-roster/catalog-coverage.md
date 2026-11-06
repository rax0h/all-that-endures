# Catalog composition and remaining admission gate

This package leaves catalog runtime unchanged. Its public reads compose the
native source, directory, query and identity checks already enabled by verified
World admission. The opening audit remains mandatory. This is an entrypoint
composition inventory, not a claim that every raw SQL consumer is closed.

| Public operation | Checked seams | Accepted authority and contract | Evidence |
|---|---|---|---|
| `read_owner_identity` | Descriptor/retired/owner/tree `read_version`; namespace state/size; allocator; complete owner occurrence iteration | Source bytes, collection directory, manifest allocator, owner/group occurrence roots; owner leaves must equal complete physical placements | Descriptor/owner/tree/placement tamper cases through public reads, with a warmed owner cache; existing catalog alias/cache regression |
| `read_identity_membership` | Owner/tree `read_version`, exact `read_identity_occurrence`, snapshot/epoch guard | Checked owner tree and both occurrence roots; absence must agree in both directions | Public membership placement tamper and missing source/header/placements cases; existing catalog/native identity regression |
| `read_identity_group` | Descriptor/group/owner/tree/link `read_version`; group occurrence iteration; exact owner membership; query membership iteration | Accepted bytes, complete group placements, owner membership, accepted link query windows plus each selected link's bytes; existing count/digest/anchor checks remain | Descriptor/group/placement corruption through public group reads; existing group/retirement/alias tests |
| `read_identity_links` | Delegates to complete `read_identity_group` | Same checked group and link projection contract | Public link-body corruption before forged decoder; existing link regression |
| Ordinary `read_records` | Accepted lazy declaration check, accepted head count, indexed selected-namespace COUNT, every actual `_record` source join | Full ordinary roster completeness plus each unique key/body against accepted ordinary root; separate segment count never added | Missing/extra/compensated rows, physical head forgery, segment namespace, empty/unknown/lazy and commit/recovery tests |

`read_owner_identity` returns a **metadata witness**. Its payload commitment is
the accepted owner header's commitment, checked against current source metadata;
it does not certify the present source body's bytes. A separately corrupted
owner payload retaining old metadata can leave this witness valid. The new
metadata-boundary test requires that behavior and separately requires
`read_version` to reject that body. No caller may treat the witness as permission
to decode unproved bytes. Ordinary historical owner witnesses likewise do not
authorize reading today's overwritten body as historical authority.

Cross-operation owner caches retain their existing epoch checks; ValidationScope
reuse is operation-local and epoch-bound. The new count cache holds only an
immutable accepted metadata tuple keyed by manifest commitment. Physical COUNT
and every returned body's proof are repeated. The COUNT is linear in the selected
namespace, not constant first-body work or an archive scan.

The 1k/10k retained-value controls instrument SQL plus SQLite column access:
ten selected `world.year` payload cursors, ten empty namespace cursors returning
no bodies, zero other ordinary/lazy/segment payload accesses. They measure only
these read operations, not catalog construction, opening or a whole simulation.

Remaining gate: inventory and certify other native/raw metadata consumers,
including rank-neighbor, event descriptor, retirement/cleanup and planning paths,
before changing admission policy. Existing schema/checksum and full World audit
remain enabled. This group does not activate a default, merge main, run endurance
or launch the mature fixture, and makes no mature timing or controlled speed claim.

The next inventory has concrete starting points below. These are coverage
questions, not newly established product defects; this package makes no change
to their existing behavior.

| Reader | Existing checked seam | Remaining coverage question |
|---|---|---|
| `persistence_lazy_minimum.rank_neighbor` / `checked_marker` | Selected owner's bytes and encoded membership use native source checks | Raw ordered query selection/absence must prove the selected neighbor, including exclusions, against accepted query authority |
| `LazyRecordStore.head_metadata`, used by `persistence_events._read_descriptor` | Descriptor body uses `read_record`; physical head checksum/schema checks remain | Bind operational head metadata and namespace inventory decisions explicitly to accepted head authority |
| `persistence_history_retirement._scope_keys` | Every returned source/order is checked | Certify the raw indexed prefix/LIMIT roster and absence against accepted collection authority |
| `RetiredIdentityRanges.scrub` | Header/tree body reads and visited-node checks remain | Inventory raw physical node-key enumeration and bound its audit/publication-only use |
| `LazyRecordStore._validated_retention_floor` | Existing checked live-pin/receipt/attempt bookkeeping | Keep mutable operational authority distinct from immutable World commitments and verify permitted consumer boundaries |
