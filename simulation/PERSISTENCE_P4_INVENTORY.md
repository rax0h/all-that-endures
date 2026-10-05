# P4 record, memory and alias inventory

**Status:** P4 preparation / architecture-review input. This is diagnosis and design evidence only; it does not implement production P4.
**Prepared from live PR head:** `62f3ec5e71242c7373d343fd121baaf0afaea842`.
**Probe candidate:** `5e91bebe5719ff674ca56edc62275a2749f7843c`.
**CI:** https://github.com/rax0h/all-that-endures/actions/runs/37269630276; 5 diagnostic fixture tests passed in 1.16s.
**Machine-readable evidence:** `simulation/persistence_p4_baseline.json`.

## 1. Selection result

The first useful P4 storage family is **`world.people`**.

The fixed-active-set probe held 32 people alive while increasing inactive, still-mutable `Person` records from 1,000 to 10,000. Current P3B cold open remained eager:

| Measure | 1,000 inactive | 10,000 inactive | Observation |
| --- | ---: | ---: | --- |
| total people | 1032 | 10032 | fixed 32 active |
| `world.people` encoded payload bytes | 672679 | 6558744 | ~linear |
| cold-open checked payload reads | 2103 | 20103 | ~9.6x |
| cold-open checked bytes | 1370124 | 13142258 | ~9.6x |
| cold-open peak allocation | 3821388 | 30963854 | ~8.1x |
| resident Person objects | 1032 | 10032 | all records |
| session memo entries | 1033 | 10033 | archive-sized |
| identity-index identities | 1033 | 10033 | archive-sized |
| baseline ordinal entries | 1034 | 10034 | archive-sized |
| cold persisted-key entries | 1066 | 10066 | archive-sized |
| first `alive=True` index source rows | 1032 | 10032 | archive-sized |
| checked point read | 1 payload / 654 B | 1 payload / 656 B | already bounded |
| one reactivation/save | 3 writes / 795 B | 3 writes / 795 B | archive-independent |
| full scrub checked reads | 1066 | 10066 | deliberately O(total) |

The bottleneck is therefore **discovery and retention**, not point I/O or incremental write scope. P2C/P3B already keep a one-person edit bounded, but ordinary open still decodes and binds every person, and the first RecordTable bucket still scans every key.

A `Person` is a good pilot because its declared fields are scalar/tuple values: unlike households, properties, resources, paths and relationships, it has no nested mutable list/dict/set that first needs a segmentation policy. Death is **not** used as an immutability boundary. The probe explicitly reactivated an inactive person and verified the existing index and save path.

## 2. Current runtime retention graph

Cold open currently restores all non-event collections through `_restore_collection()`, then captures stable ordinals, restores current identity links and binds every mutable owner. For `world.people`, the 10,000-inactive fixture retained:

- 10032 Person objects in the root container;
- 10033 `_memo` and 10033 reverse-memo entries;
- 10056 binding IDs;
- 10034 identity owners / 10034 occurrences / 10034 paths;
- 10034 baseline ordinal entries and 10066 persisted-key entries.

Those are independent strong/metadata retention paths. Moving payload bytes to SQLite without changing these structures would not make ordinary residency bounded.

The first `RecordTable.buckets("alive")` call initializes its dirty set with every key and materializes `previous` membership for every record. At 10,032 people the resulting `alive` index held 10032 previous entries and 10032 bucket members. Repeat queries are cheap only because the archive-sized index is then retained.

## 3. Exhaustive canonical-family inventory

The classifications below mean:

- **KEEP** — current representation is not a demonstrated history-size blocker or is intentionally bounded.
- **EXTEND** — retain canonical authority but add bounded lookup/representation support.
- **MIGRATE** — move record payload residency and/or growing nested history to P4 lazy/versioned storage.
- **DERIVED** — runtime-only cache; rebuild or hold IDs/weak references, never make it authority.
- **DEFER** — not the first measured blocker; preserve eagerly until measurements justify migration.

| Family | Authority / order | Mutation and reactivation paths | Queries / ordering | Alias & retention hazards | Classification |
| --- | --- | --- | --- | --- | --- |
| `world.people[pid]` | pid-keyed canonical dictionary; stable ID order is used by indexes | births insert; annual simulation mutates fields; death flips `alive`; resurrection can make an old person current again; valid direct field edits remain tracked | `current_people` uses `alive=True`, sorted stable IDs; many subsystems perform direct `get` / `[]` point reads | root table + P2 memo + identity occurrence index + RecordTable buckets retain all | **MIGRATE first** |
| `world.households[hid]` | hid-keyed record; `members` order is canonical | formation/birth append members; wealth/food/preparedness/alive mutate; old household can remain referenced by people | active households by `alive`; occupied households from current people; direct member traversal | nested `members` list can be retained externally and may grow; whole-owner alias group required | **EXTEND**, then migrate if residual dominates |
| settlements / local / cells | stable map/settlement keys | weather, prosperity, infrastructure effects mutate local/settlement state; cells treated as canonical even when mostly static | direct location lookups; deterministic dictionary order where iterated | small map-size domain, not history count | **KEEP** |
| trade routes | pair key | exchanges/strength/last-used mutate; routes may be revisited | route/location lookup | growth tied to settlement graph, not age alone | **EXTEND** |
| `event_ids` | canonical set of event IDs, currently consecutive by accepted EventLog contract | `World.emit` adds exactly next event ID; P3 bootstrap validates event order/next ID | cause membership in `emit` | full Python set duplicates event history and remains O(events) | **EXTEND** to exact compact/range representation only after compatibility proof |
| EventLog | accepted P3 disk prefix + bounded reader cache | append/seal only under accepted P3 rules | point/year/streaming archive/digest | already has bounded sealed-history residency | **KEEP (P3)** |
| genealogy parents/children | child->parent tuple and parent->ordered child list are canonical | `birth()` writes both; old ancestry remains queryable; no death freeze assumption | ancestry walks parent links; dependents read children | children lists are nested mutable historical memberships | **MIGRATE** keyed memberships/ordered child rows after people |
| social edges/adjacency/partnerships | pair-keyed Relationship plus canonical adjacency/partnership maps | `get`, `record`, `partner`; `shared_history` appends | neighbors, relationships_for, living_partnerships; stable pair semantics | `_relationships` strongly retains mutable Relationship objects; `shared_history` can grow | **MIGRATE**; persist current memberships and address history list separately |
| economy property | property ID; owner fields authoritative; provenance/ownership ordered | create/transfer; ownership can change long after creation | `owned(kind,owner)` exact indexed lookup | provenance and ownership lists grow; RecordTable index can retain all | **MIGRATE** with owner membership + nested history policy |
| knowledge claims/beliefs/claim_index | claim ID and exact subject/proposition index are canonical | claim/teach; beliefs update | direct claim index and belief lookups | canonical reverse index cannot simply disappear | **EXTEND**, migrate if measured residual dominates |
| culture practices/institutions/laws/adoption | typed IDs/maps | cultural step creates/updates; adoption changes | local scans and IDs | historical but not currently measured dominant | **DEFER** |
| lineage nodes/children | typed `(kind,id)` node key and child set | register appends node/child relations | ancestry traversal | historical child sets | **MIGRATE** after people/genealogy |
| communities/memberships | community ID; membership key `(person,community)`; insertion order matters for memberships-for | join/inherit/diaspora can update old memberships | memberships_for(person) and local roots | `_membership_index` is ID-only but can still grow with all persons | **MIGRATE** memberships with person lookup rows |
| transmission records | transmission ID | append via `record` | history(item_kind,item_id) currently scans all | pure archive grows with history | **MIGRATE** with item lookup memberships |
| skills | key `(person,domain)` | practice/teach; nested teachers/provenance append | point key lookup | nested lists grow and aliases must preserve order | **MIGRATE** |
| infrastructure | asset ID | create/maintain/decay; provenance append | route-condition scans assets | active asset count may be genuine stock; provenance grows | **EXTEND** |
| agency motives/actions | motives keyed person; actions ordered list capped at 50,000 | annual assess/choose mutates motives; actions append then truncate | current motives and recent action history | motives can retain old persons; actions have explicit cap | motives **MIGRATE**; actions **KEEP (50k cap)** |
| advancement paths | person key; one path owns nested abilities/understanding/response models | absorb/awaken/practice and later rank changes | point path/rank; eligibility queries | deeply nested mutable tree; retained alias must pin whole owner/group | **MIGRATE**, but not first pilot |
| magic resources | resource ID; `owner_index` canonical current ownership; aspirations keyed person | create/transfer/consume; dead-owner recovery transfers; aspirations can be created later | inventory(owner), circulation, ordered offers; stable resource ID / price ordering | resources and `transfers` grow; inventory cache holds tuples of live Resource objects | **MIGRATE high-impact** after people; **EXTEND** owner index |
| institution records | institution/branch/record/notice/application IDs | members, branches, records, notices, trainees, applications mutate through domain methods; old applications/notices remain | status/person/society queries and stable IDs | member sets and branch sets grow; RecordTable buckets retain archive | **MIGRATE** with status/person memberships |
| metaphysics | souls keyed person; resurrection tokens keyed ID | death/resurrection/transform/tokens mutate old people/souls | soul/token point reads | explicitly proves death is not an eviction/freeze boundary | **MIGRATE** coupled to people reactivation |
| divinity | gods/GAB small named authorities; churches ID-keyed | church followers/clergy/doctrine sets grow | church filters, living follower intersections | church membership is historical | gods/GAB **KEEP**; churches/memberships **MIGRATE** |
| materials | lot/item IDs; lot_index and active_lot_index canonical | produce/consume/purchase; lot ownership and transfers mutate; old lots remain queryable | available/best/rank/crafting selection by active lot IDs | lots and transfer lists grow; selection caches are IDs/heaps and rebuildable | lots/items **MIGRATE high-impact**; canonical indexes **EXTEND** |
| ambient magic | settlement-keyed fields | annual mutation | direct settlement lookup | bounded by settlements | **KEEP** |
| warfare | conflict IDs + pair tensions | tension/campaign/open/close mutate | active conflicts by status | RecordTable active index otherwise archive-sized | **MIGRATE** if residual material |
| society accountability | inquiry ID | open/close/findings mutate | active/status queries | RecordTable archive-sized | **MIGRATE** if residual material |
| currency | wallets person-keyed, treasuries institution-keyed; minted/consumed denomination counters | credit/transfer/treasury/consume/exchange; nested dict direct mutations tracked | point balance/payment | wallets can exist for historical people; shared wallet aliases are supported and tested | wallets/treasuries **MIGRATE** with alias groups; counters **KEEP** |
| threat ecology | threat ID + resolutions | creation/status/resolution mutate | status/current lookups | historical threats accumulate | **MIGRATE** if residual material |

## 4. Derived caches and strong-reference hazards

| Cache | Current contents | Retention consequence | P4 rule |
| --- | --- | --- | --- |
| `World._living_cache` | tuple of Person objects within current_people scope | deliberately strong, but step-local | allowed active pin; must be cleared at scope exit as today |
| `SocialGraph._relationships` | per-person dict of **Relationship objects** | can pin historical mutable edges indefinitely | replace retained record refs with keys/weak refs or count live values as sharing-group pins |
| social partnership index/count | pair IDs / scalar | metadata grows with historical partnerships | source from persistent current membership rows; no Relationship retention |
| community membership index | IDs only | O(memberships) metadata | persistent indexed lookup + bounded local overlay |
| magic resource inventory | tuples of **MagicResource objects** | pins resource records by owner once queried | cache keys/IDs/tokens only, materialize through identity map |
| magic resource selection | lists of **MagicResource objects** | pins holder inventory | retain IDs/signatures, resolve through identity map |
| offer books | price/resource IDs and owner tokens | structurally bounded by eligible/current offer stock, not irrelevant history in probe | keep derived; never make it authority |
| material selection/rank heaps/selection IDs | IDs/primitives | bounded by genuinely active material stock, not all consumed lots | keep derived/current; persistent active membership replaces eager source scan |
| advancement rank cache | scalar rank by person during scope | current working set only if scope discipline holds | allowed bounded scope cache |

The offer probe confirms the current offer-book algorithm itself does not scan irrelevant consumed resource history: both 1,000 and 10,000 irrelevant-resource cases visited exactly 4 eligible inventory IDs on first query and 0 on repeat, returning identical order `essence=[1,2]`, `awakening_stone=[3,4]`. However `resources_resident` still grew from 1004 to 10004. P4 should preserve offer semantics while changing resource residency, not reopen the offer algorithm.

## 5. Persistence bookkeeping inventory

| Structure | Authority | Current cost | P4 disposition |
| --- | --- | --- | --- |
| `_root_containers` | live mapping wrappers | one strong root wrapper per namespace, but each wrapper currently owns every record | lazy family wrapper must own keys/order metadata, not decoded values |
| `_memo` / `_memo_reverse` | binding conversion identity | strong entries per decoded mutable object | do not populate for unloaded lazy records; replace lazy-family identity retention with weak group registry + explicit strong pins |
| `_bound_ids` / global `_BINDINGS` | mutation hooks | IDs scale with every bound object; bindings associate session | only loaded mutable identities participate |
| `IdentityOccurrenceIndex` | current alias/link computation | currently stores object references, owner rows and paths for the full graph | lazy sharing groups are loaded/indexed on demand; persisted identity-link metadata remains authority |
| `_baseline_ordinals` | stable collection iteration/order | one entry per member, loaded eagerly | move order into persisted ordinal/membership rows; do not load full key map on open |
| `_cold_persisted_keys` | cold save delete/existence bookkeeping | set per persisted key | replace with point existence/version metadata and changed-key journal for lazy namespaces |
| current identity rows / reverse lookups | persisted shared-identity authority | current links are bounded by aliases but bootstrap discovery is full-graph | preserve rows; add indexed owner/group lookup so a lazy record loads its complete sharing group without graph scan |
| `query_membership` table | P1 storage primitive, currently unused by World adapter | rows are already committed atomically with RecordChange | P4 promotes this concept into versioned current-query authority derived from owning records |
| EventLog cache/prefix metadata | accepted P3 authority | bounded four-segment cache plus fixed metadata | preserve unchanged |

## 6. Mutable nested-history inventory

P4 must not force these into a falsely immutable record merely because their owner is old:

- `Relationship.shared_history`, `Property.provenance` and `Property.ownership`;
- `SkillHistory.teachers` / `provenance`;
- `Infrastructure.provenance`;
- `MagicResource.transfers`;
- `MaterialLot.transfers`;
- institution `members`, branch `records/notices/trainees`, church `followers/clergy`;
- genealogy children and lineage children;
- household members;
- advancement ability/understanding/response-model containers.

For the P4 pilot no new segmentation mechanism is required because Person has no such nested mutable collection. The implementation proposal treats later nested-history migration as an explicit family-by-family adapter decision: keyed membership rows when set/dict semantics apply; fixed-size sequence segments plus mutable tail only when an append-only contract is actually proven; otherwise a mutable per-owner record remains authoritative and its remaining size bound is reported honestly.

## 7. Current query requirements

Current queries cannot be rebuilt by decoding the archive on first use. Required persistent memberships include at minimum:

- people: `alive`, with stable ID order;
- households: `alive`;
- applications: `passed`, `(person,society)`;
- notices: `status`, `cause_event`;
- conflicts/inquiries/threats: current status;
- property: `(owner_kind,owner_id)`;
- resources: `(owner_kind,owner_id)` and consumed/current availability;
- materials: settlement active-lot membership and rank where needed;
- community/person memberships;
- social adjacency/partnership endpoint memberships where migrated.

Owning records remain authoritative. Membership rows must be checksum/type validated, versioned, and committed in the same transaction as owning record versions, identity changes, counters, EventLog publication and the new head. Unsaved local changes require a per-index overlay of additions/removals keyed by record ID/ordinal; merge is deterministic and de-duplicates by key without archive scans.

## 8. Retained late-world evidence

The repository retains trustworthy **measurements**, but not a replayable late-world World/store:

- `LONG_HISTORY_VALIDATION.md` records that the year-2000 and year-3010 checkpoints were lost in a workspace reset.
- The inspected Actions runs 36278414000, 36261595896, 35529400618 currently expose **zero retained artifacts**.
- Existing JSON/markdown contains counts/digests and is evidence about historical workload, not a World.

Useful retained workload facts include the canonical year-1000 result with 17,159 total people, 1,500 living, 94,850 magic resources and 104,326 material lots, and the later year-3000 report with 3,618,351 events and non-event archives still resident in RAM. These support prioritizing people/resources/materials but cannot substitute for P5 resumed-world validation.

A durable trusted late-world fixture, with checksum/provenance/rules/configuration and restore command, remains a **P5 prerequisite**. No long run was performed to replace it.

## 9. Exhaustive namespace measurement appendix

Counts and encoded bytes below come from the small independent-control fixture in the green P4 probe. They establish codec/namespace shape, not late-world scale. The complete 1k/10k structural measurements are in `persistence_p4_baseline.json`.

| Namespace | Records | Record payload B | Segment payload B | Classification |
| --- | ---: | ---: | ---: | --- |
| `world.advancement.paths` | 7 | 7856 | 0 | MIGRATE |
| `world.agency.actions` | 70 | 15978 | 0 | KEEP (50k cap) |
| `world.agency.motives` | 36 | 14642 | 0 | MIGRATE |
| `world.ambient_magic.fields` | 2 | 502 | 0 | KEEP |
| `world.cells` | 48 | 14659 | 0 | KEEP |
| `world.communities.communities` | 2 | 499 | 0 | MIGRATE |
| `world.communities.memberships` | 54 | 2960 | 0 | MIGRATE |
| `world.communities.next_community` | 1 | 35 | 0 | KEEP |
| `world.culture.adoption` | 10 | 540 | 0 | DEFER |
| `world.culture.institutions` | 0 | 0 | 0 | DEFER |
| `world.culture.laws` | 0 | 0 | 0 | DEFER |
| `world.culture.next_institution` | 1 | 35 | 0 | KEEP |
| `world.culture.next_law` | 1 | 35 | 0 | KEEP |
| `world.culture.next_practice` | 1 | 36 | 0 | KEEP |
| `world.culture.practices` | 10 | 5659 | 0 | DEFER |
| `world.currency.consumed` | 0 | 0 | 0 | KEEP |
| `world.currency.minted` | 0 | 0 | 0 | KEEP |
| `world.currency.treasuries` | 0 | 0 | 0 | MIGRATE |
| `world.currency.wallets` | 0 | 0 | 0 | MIGRATE |
| `world.divinity.churches` | 0 | 0 | 0 | MIGRATE |
| `world.divinity.gods` | 17 | 5122 | 0 | KEEP |
| `world.divinity.great_astral_beings` | 3 | 1016 | 0 | KEEP |
| `world.divinity.next_church` | 1 | 35 | 0 | KEEP |
| `world.economy.next_property` | 1 | 36 | 0 | KEEP |
| `world.economy.property` | 16 | 6269 | 0 | MIGRATE |
| `world.event_ids` | 58 | 2127 | 0 | EXTEND |
| `world.events` | 58 | 34024 | 0 | KEEP (accepted P3) |
| `world.genealogy.children` | 8 | 402 | 0 | MIGRATE |
| `world.genealogy.parents` | 5 | 305 | 0 | MIGRATE |
| `world.households` | 16 | 5670 | 0 | EXTEND |
| `world.infrastructure.assets` | 2 | 678 | 0 | EXTEND |
| `world.infrastructure.next_id` | 1 | 35 | 0 | KEEP |
| `world.institutions.applications` | 0 | 0 | 0 | MIGRATE |
| `world.institutions.branches` | 4 | 1240 | 0 | MIGRATE |
| `world.institutions.institutions` | 2 | 570 | 0 | MIGRATE |
| `world.institutions.magic_records` | 0 | 0 | 0 | MIGRATE |
| `world.institutions.next_application` | 1 | 35 | 0 | KEEP |
| `world.institutions.next_branch` | 1 | 35 | 0 | KEEP |
| `world.institutions.next_institution` | 1 | 35 | 0 | KEEP |
| `world.institutions.next_notice` | 1 | 35 | 0 | KEEP |
| `world.institutions.next_record` | 1 | 35 | 0 | KEEP |
| `world.institutions.notices` | 0 | 0 | 0 | MIGRATE |
| `world.knowledge.beliefs` | 0 | 0 | 0 | EXTEND |
| `world.knowledge.claim_index` | 0 | 0 | 0 | EXTEND |
| `world.knowledge.claims` | 0 | 0 | 0 | EXTEND |
| `world.knowledge.next_claim` | 1 | 35 | 0 | KEEP |
| `world.lineage.children` | 30 | 5375 | 0 | MIGRATE |
| `world.lineage.nodes` | 108 | 25134 | 0 | MIGRATE |
| `world.local` | 2 | 355 | 0 | KEEP |
| `world.magic_resources.aspirations` | 36 | 21691 | 0 | MIGRATE |
| `world.magic_resources.next_id` | 1 | 35 | 0 | KEEP |
| `world.magic_resources.owner_index` | 1 | 45 | 0 | EXTEND |
| `world.magic_resources.resources` | 8 | 3407 | 0 | MIGRATE |
| `world.materials.active_lot_index` | 2 | 187 | 0 | EXTEND |
| `world.materials.items` | 0 | 0 | 0 | MIGRATE |
| `world.materials.lot_index` | 2 | 189 | 0 | EXTEND |
| `world.materials.lots` | 10 | 4807 | 0 | MIGRATE |
| `world.materials.next_item` | 1 | 35 | 0 | KEEP |
| `world.materials.next_lot` | 1 | 36 | 0 | KEEP |
| `world.metaphysics.next_token` | 1 | 35 | 0 | KEEP |
| `world.metaphysics.resurrection_tokens` | 0 | 0 | 0 | MIGRATE |
| `world.metaphysics.souls` | 54 | 20771 | 0 | MIGRATE |
| `world.next_event` | 1 | 36 | 0 | KEEP |
| `world.next_household` | 1 | 36 | 0 | KEEP |
| `world.next_person` | 1 | 36 | 0 | KEEP |
| `world.next_settlement` | 1 | 35 | 0 | KEEP |
| `world.people` | 54 | 35259 | 0 | MIGRATE (pilot) |
| `world.seed` | 1 | 40 | 0 | KEEP |
| `world.settlements` | 2 | 965 | 0 | KEEP |
| `world.skills.skills` | 110 | 28647 | 0 | MIGRATE |
| `world.social.adjacency` | 54 | 4944 | 0 | MIGRATE |
| `world.social.edges` | 121 | 49376 | 0 | MIGRATE |
| `world.social.partnerships` | 7 | 252 | 0 | MIGRATE |
| `world.society_accountability.inquiries` | 0 | 0 | 0 | MIGRATE |
| `world.society_accountability.next_inquiry` | 1 | 35 | 0 | KEEP |
| `world.threat_ecology.next_id` | 1 | 35 | 0 | KEEP |
| `world.threat_ecology.resolutions` | 0 | 0 | 0 | MIGRATE |
| `world.threat_ecology.threats` | 0 | 0 | 0 | MIGRATE |
| `world.trade_routes` | 1 | 189 | 0 | EXTEND |
| `world.transmission.next_id` | 1 | 35 | 0 | KEEP |
| `world.transmission.records` | 5 | 2215 | 0 | MIGRATE |
| `world.warfare.conflicts` | 0 | 0 | 0 | MIGRATE |
| `world.warfare.next_conflict` | 1 | 35 | 0 | KEEP |
| `world.warfare.tensions` | 1 | 54 | 0 | MIGRATE |
| `world.year` | 1 | 35 | 0 | KEEP |

## 10. Inventory conclusion

The current store already has bounded checked point reads and bounded changed-record writes. P4 should therefore **not** redesign P1/P2/P3 transaction semantics. The first implementation task should make `world.people` lazy while preserving direct mapping behavior, one mutable instance, alive-membership ordering, reactivation/resurrection, stale-session semantics and materializing detach. Only after that measured pilot should the same primitives expand to resources/materials and the other families that dominate residual residency.
