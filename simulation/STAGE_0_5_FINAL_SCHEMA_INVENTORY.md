# Stage 0.5 schema and growth inventory

Final candidate inventory, October 13 UTC. All 483 declared stored fields have a closed classification; the machine manifest rejects newly added or obsolete fields. This table describes capability 6 selected by explicit `upgrade_lazy_snapshot`, with genuine format 3/4/5 compatibility kept separate. The final P5 and full-suite results are recorded in the closeout ledger, not inferred from this inventory.

Historical mutable children use the existing recursive history/record authority, checked identity catalog and sole hybrid publisher. Whole-container iteration, full scrub, conversion and portable detach intentionally cost the visited values. Point edit costs include actual dirty input D, related identity placements U, current resident topology C and the bytes of values requested or held by callers. Scalar text, integer size and immutable tuples are not universally constant-size; preserving a caller-held imported tuple may require encoding its complete current value. Tests measure those bytes separately rather than relabeling an unrestricted import as bounded.

## Concrete writer and import closure

| Field or family | Actual producer / generated guard | Capability 6 / import treatment | Permanent evidence |
|---|---|---|---|
| Household.members; Settlement.households | engine demography/adoption changes exact membership; duplicates and extinct references remain valid | counted sequence references; local page/path changes; no truncation | final_household_sequences test families |
| Settlement.memory | Simulation._pressure writes monster_surge/decays values; update_warfare writes war | unrestricted imported map and replacement become checked map; scalar owner edits read zero memory entries at H1k/H10k | final_settlement_memory; stage_0_5_settlement_memory_validation.json |
| culture.Institution.practices | civilization_step creates `set(strong[:4])`; at most three generated institutions per settlement; no later growth writer | generated child <=4; unrestricted import/replacement becomes checked set even without another alias | final_settlement_memory imported cultural practices regression |
| Advancement child graphs | add_essence stops at MAX_BASE_ESSENCES=3; ability admission uses SKILLS_PER_ESSENCE and MAX_SKILLS=20 | imports need not obey generated guards; recursive checked records/lists/maps preserve exact graph | final_advancement_graph, final_world_recursive_records tests |
| Understanding / ResponseModel | mastery_training.needs_trial and trial limit generated successful trials; trial trims samples to 3/5; solve emits <=5 coefficients | evidence/maps/transfers and imported oversized samples remain checked histories; no import cap | final_advancement_graph and final_world_recursive_records tests |
| currency wallets/treasuries | credit/transfer/consume/exchange validate six COIN_VALUE denomination keys | direct/imported maps unrestricted and checked; exact NaN atom keys retain identity and bits | final_currency_runtime, final_event_id_nonreflexive tests |
| Agency.actions | agency_step trims generated actions to the last 50,000 | accepted current packed body; imported larger bodies preserved, with explicit C/input bytes and full current-body action synchronization | final_world_packed_actions tests; P5 |
| World.event_ids | World.emit appends consecutive IDs; public exact set operations may create exceptions | compact captured prefix and counted removed/typed added histories; NaNs and immutable key containers remain paged; full copy scrubs exception semantics | final_event_id_exceptions, final_event_id_nonreflexive, final_complete_format tests |
| World.events / Event.data | World.emit snapshots data; event_log seals certified immutable tails | immutable disk segments plus checked recursive frozen snapshot data; mutable event identity retires while snapshot child ownership persists | final_world_recursive_events, final_legacy_event_copy tests |
| Person.parents; scalar species | demography assigns generated parent tuple; direct imported tuple/text size unrestricted | exact immutable value, held current-record byte cost measured separately; no clean-cache retention above budget | final_immutable_input_cost; parents 51,145/456,145 read bytes and 14,966/149,966 written; species 12,463/39,463 read and 2,072/11,072 written at 1k/10k |
| Genealogy/social/material index buckets and knowledge claims/index | actual family append/add/claim allocation can grow with history | checked bucket references or versioned scalar family; outer current key topology explicitly accounted for | final_graph_buckets, final_knowledge*, final_world_recursive* tests |
| Cells, local state, trade topology and other current roots | simulation steps visit current world topology C | resident current topology remains charged to C; no history-independence claim for explicitly visiting all current entities | ordinary complete open/P5; FIELD_POLICIES exhaustive schema test |

All mutable-field rows below use implemented compact storage in the capability 6 lane. Legacy resident compatibility costs apply only when opening a genuine earlier representation. For record field collections, whole replacement costs actual incoming values, even when generated values are small. The exact operation and scope are important: a constant number of metadata rows is not a constant byte claim.

| Record.field | Classification | Growth writer / guard | Actual bound | Capability 6 representation |
|---|---|---|---|---|
| AbilityProgress.aura | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.awakened_year | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.domain | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.essence | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.function | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.level | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.milestone_event | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.name | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.origin_event | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.progress | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.rank | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.response_model | bounded-generated-record | advancement.py: AbilityProgress writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| AbilityProgress.semantic_key | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.source | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.special | scalar | AbilityProgress field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AbilityProgress.understanding | bounded-generated-record | advancement.py: AbilityProgress writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| ActionRecord.action | scalar | ActionRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ActionRecord.event_id | scalar | ActionRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ActionRecord.motive | scalar | ActionRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ActionRecord.person | scalar | ActionRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ActionRecord.strength | scalar | ActionRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ActionRecord.year | scalar | ActionRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdvancementState.paths | root-collection | advancement.py: AdvancementState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| AdventureNotice.assigned_to | fixed-tuple | institutions.py: AdventureNotice writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| AdventureNotice.branch | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.cause_event | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.id | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.kind | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.location | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.required_rank | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.resolved_event | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.status | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AdventureNotice.year | scalar | AdventureNotice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AgencyState.actions | root-collection | agency.py: AgencyState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| AgencyState.motives | root-collection | agency.py: AgencyState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| AmbientField.critical_years | scalar | AmbientField field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AmbientField.level | scalar | AmbientField field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AmbientField.peak | scalar | AmbientField field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AmbientField.quintessence | scalar | AmbientField field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AmbientField.surges | scalar | AmbientField field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| AmbientMagicState.fields | root-collection | ambient_magic.py: AmbientMagicState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| Branch.authority | scalar | Branch field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Branch.founded_year | scalar | Branch field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Branch.id | scalar | Branch field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Branch.institution | scalar | Branch field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Branch.notices | set-history | institutions.py: Branch writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Branch.origin_event | scalar | Branch field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Branch.records | set-history | institutions.py: Branch writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Branch.settlement | scalar | Branch field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Branch.trainees | map-history | institutions.py: Branch writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Cell.elevation | scalar | Cell field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Cell.fertility | scalar | Cell field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Cell.forest | scalar | Cell field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Cell.hazard | scalar | Cell field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Cell.moisture | scalar | Cell field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Cell.x | scalar | Cell field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Cell.y | scalar | Cell field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Church.authority | scalar | Church field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Church.clergy | set-history | divinity.py: Church writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Church.doctrine_claims | set-history | divinity.py: Church writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Church.followers | set-history | divinity.py: Church writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Church.founded_year | scalar | Church field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Church.god | scalar | Church field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Church.id | scalar | Church field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Church.origin_event | scalar | Church field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Church.settlement | scalar | Church field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Church.wealth | scalar | Church field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Community.active | scalar | Community field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Community.founded | scalar | Community field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Community.id | scalar | Community field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Community.kind | scalar | Community field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Community.origin_event | scalar | Community field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Community.origin_settlement | scalar | Community field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Community.parent | scalar | Community field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CommunityState.communities | root-collection | communities.py: CommunityState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| CommunityState.memberships | root-collection | communities.py: CommunityState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| CommunityState.next_community | scalar | CommunityState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.attacker | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.attacker_losses | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.battles | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.cause | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.cause_event | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.defender | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.defender_losses | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.ended_year | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.id | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.origin_event | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.peace_event | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.started_year | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.status | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Conflict.war_score | scalar | Conflict field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.craftsperson | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.created_year | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.id | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.item_rank | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.kind | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.magical | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.magical_properties | fixed-tuple | materials.py: CraftedItem writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| CraftedItem.materials | fixed-tuple | materials.py: CraftedItem writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| CraftedItem.origin_event | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.owner_id | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.owner_kind | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.quality | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.rarity | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CraftedItem.settlement | scalar | CraftedItem field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CulturalState.adoption | root-collection | culture.py: CulturalState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| CulturalState.institutions | root-collection | culture.py: CulturalState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| CulturalState.laws | root-collection | culture.py: CulturalState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| CulturalState.next_institution | scalar | CulturalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CulturalState.next_law | scalar | CulturalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CulturalState.next_practice | scalar | CulturalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| CulturalState.practices | root-collection | culture.py: CulturalState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| DivineState.churches | root-collection | divinity.py: DivineState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| DivineState.gods | root-collection | divinity.py: DivineState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| DivineState.great_astral_beings | root-collection | divinity.py: DivineState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| DivineState.next_church | scalar | DivineState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Economy.next_property | scalar | Economy field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Economy.property | root-collection | economy.py: Economy writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| EssencePath.abilities | bounded-generated-list | advancement.py: EssencePath writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage; add_essence <=3 base, _semantic_ability <=20 abilities | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| EssencePath.base_essences | bounded-generated-list | advancement.py: EssencePath writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage; add_essence <=3 base, _semantic_ability <=20 abilities | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| EssencePath.confluence | scalar | EssencePath field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| EssencePath.confluence_concepts | fixed-tuple | advancement.py: EssencePath writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| EssencePath.confluence_name | scalar | EssencePath field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| EssencePath.core_fraction | scalar | EssencePath field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Event.actors | fixed-tuple | core.py: Event writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| Event.causes | fixed-tuple | core.py: Event writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| Event.data | value-history | core.py: Event writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Event.id | scalar | Event field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Event.kind | scalar | Event field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Event.layer | scalar | Event field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Event.location | scalar | Event field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Event.year | scalar | Event field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Genealogy.children | root-collection | genealogy.py: Genealogy writers | unbounded historical buckets; candidate lane uses compact headers and bounded point additions | typed list reference in explicit native-graph conversion; legacy buckets remain readable with resident costs |
| Genealogy.parents | root-collection | genealogy.py: Genealogy writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| God.domains | fixed-tuple | divinity.py: God writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| God.id | scalar | God field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| God.manifestations | list-history | divinity.py: God writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| God.name | scalar | God field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| God.ontology | scalar | God field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| God.relationships | map-history | divinity.py: God writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| God.transcendent | scalar | God field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| GreatAstralBeing.authorities | fixed-tuple | divinity.py: GreatAstralBeing writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| GreatAstralBeing.id | scalar | GreatAstralBeing field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| GreatAstralBeing.interventions | list-history | divinity.py: GreatAstralBeing writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| GreatAstralBeing.name | scalar | GreatAstralBeing field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| GreatAstralBeing.ontology | scalar | GreatAstralBeing field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| GreatAstralBeing.relationships | map-history | divinity.py: GreatAstralBeing writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| GreatAstralBeing.transcendent | scalar | GreatAstralBeing field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Household.alive | scalar | Household field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Household.food | scalar | Household field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Household.id | scalar | Household field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Household.lineage | scalar | Household field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Household.members | ordered-history | core.py: Household writers | unbounded; local counted tree edits in counted conversion lane | lazy household header and counted HistoryReference; accepted paged/eager legacy modes remain explicit |
| Household.preparedness | scalar | Household field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Household.settlement | scalar | Household field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Household.wealth | scalar | Household field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Infrastructure.built | scalar | Infrastructure field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Infrastructure.capacity | scalar | Infrastructure field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Infrastructure.condition | scalar | Infrastructure field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Infrastructure.id | scalar | Infrastructure field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Infrastructure.kind | scalar | Infrastructure field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Infrastructure.origin_event | scalar | Infrastructure field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Infrastructure.provenance | list-history | infrastructure.py: Infrastructure writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Infrastructure.settlements | fixed-tuple | infrastructure.py: Infrastructure writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| InfrastructureState.assets | root-collection | infrastructure.py: InfrastructureState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| InfrastructureState.next_id | scalar | InfrastructureState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.branch | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.closed_year | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.findings | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.id | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.opened_year | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.origin_event | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.resolved_event | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.severity | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.status | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.trigger_event | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Inquiry.trigger_kind | scalar | Inquiry field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| InstitutionState.applications | root-collection | institutions.py: InstitutionState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| InstitutionState.branches | root-collection | institutions.py: InstitutionState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| InstitutionState.institutions | root-collection | institutions.py: InstitutionState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| InstitutionState.magic_records | root-collection | institutions.py: InstitutionState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| InstitutionState.next_application | scalar | InstitutionState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| InstitutionState.next_branch | scalar | InstitutionState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| InstitutionState.next_institution | scalar | InstitutionState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| InstitutionState.next_notice | scalar | InstitutionState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| InstitutionState.next_record | scalar | InstitutionState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| InstitutionState.notices | root-collection | institutions.py: InstitutionState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| KnowledgeClaim.id | scalar | KnowledgeClaim field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| KnowledgeClaim.origin_event | scalar | KnowledgeClaim field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| KnowledgeClaim.proposition | scalar | KnowledgeClaim field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| KnowledgeClaim.subject | scalar | KnowledgeClaim field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| KnowledgeClaim.truth | scalar | KnowledgeClaim field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| KnowledgeState.beliefs | root-collection | knowledge.py: KnowledgeState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| KnowledgeState.claim_index | root-collection | knowledge.py: KnowledgeState.claim inserts the exact subject/proposition pair with its claim ID | unbounded outer map; generated keys are string pairs and values exact integer IDs | versioned scalar map family; marked conversion validates exact string-pair keys; genuine earlier eager authority remains readable |
| KnowledgeState.claims | root-collection | knowledge.py: KnowledgeState.claim allocates one claim for each new semantic pair | unbounded claim archive; point operations load/write only affected records; scalar string/bytes sizes remain actual value cost | versioned scalar record family; genuine earlier eager authority remains readable; portable detach uses the standard record table |
| KnowledgeState.next_claim | scalar | KnowledgeState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Law.domain | scalar | Law field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Law.enforcement | scalar | Law field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Law.id | scalar | Law field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Law.origin_event | scalar | Law field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Law.settlement | scalar | Law field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Law.strictness | scalar | Law field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LineageNode.id | scalar | LineageNode field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LineageNode.kind | scalar | LineageNode field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LineageNode.origin_event | scalar | LineageNode field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LineageNode.origin_year | scalar | LineageNode field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LineageNode.parents | fixed-tuple | lineage.py: LineageNode writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| LineageState.children | root-collection | lineage.py: LineageState writers | unbounded historical buckets; candidate lane uses compact headers and bounded point additions | typed set reference in explicit native-graph conversion; legacy buckets remain readable with resident costs |
| LineageState.nodes | root-collection | lineage.py: LineageState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| LocalState.drought | scalar | LocalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LocalState.flood | scalar | LocalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LocalState.rain | scalar | LocalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| LocalState.scarcity | scalar | LocalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.adventurer_aspiration | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.completion_goal | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.compromise_tolerance | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.desired_abilities | fixed-tuple | magic_resources.py: MagicAspiration writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| MagicAspiration.desired_base_essences | fixed-tuple | magic_resources.py: MagicAspiration writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| MagicAspiration.drive | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.formed_year | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.preparation | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.reason | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.risk_tolerance | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.search_years | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.stone_selectiveness | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicAspiration.urgency | scalar | MagicAspiration field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.consumed_by | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.consumed_event | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.consumed_year | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.created_year | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.id | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.key | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.kind | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.location | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.origin_event | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.owner_id | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.owner_kind | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.rarity | scalar | MagicResource field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResource.transfers | list-history | magic_resources.py: MagicResource writers | unbounded; compact header, bounded point/tail operations; whole-list edits remain explicit O(H) | typed list reference with current-owner integer event-ID validation; genuine legacy lists remain readable with resident costs |
| MagicResourceState.aspirations | root-collection | magic_resources.py: MagicResourceState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| MagicResourceState.next_id | scalar | MagicResourceState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicResourceState.owner_index | root-collection | magic_resources.py: MagicResourceState writers | unbounded historical buckets; candidate lane uses compact headers and bounded point additions | typed set reference in explicit native-graph conversion; legacy buckets remain readable with resident costs |
| MagicResourceState.resources | root-collection | magic_resources.py: MagicResourceState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| MagicUserRecord.abilities | fixed-tuple | institutions.py: MagicUserRecord writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| MagicUserRecord.ability_names | fixed-tuple | institutions.py: MagicUserRecord writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| MagicUserRecord.branch | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicUserRecord.confluence_id | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicUserRecord.confluence_name | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicUserRecord.disclosure | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicUserRecord.essence_ids | fixed-tuple | institutions.py: MagicUserRecord writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| MagicUserRecord.id | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicUserRecord.person | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicUserRecord.source_event | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicUserRecord.year | scalar | MagicUserRecord field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.ambient | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.created_year | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.environment_tags | fixed-tuple | threat_ecology.py: MagicalThreat writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| MagicalThreat.form | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.id | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.kind | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.location | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.origin_event | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.rank | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MagicalThreat.status | scalar | MagicalThreat field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialEconomy.active_lot_index | root-collection | materials.py: MaterialEconomy writers | unbounded historical buckets; candidate lane uses compact headers and bounded point additions | typed set reference in explicit native-graph conversion; legacy buckets remain readable with resident costs |
| MaterialEconomy.items | root-collection | materials.py: MaterialEconomy writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| MaterialEconomy.lot_index | root-collection | materials.py: MaterialEconomy writers | unbounded historical buckets; candidate lane uses compact headers and bounded point additions | typed list reference in explicit native-graph conversion; legacy buckets remain readable with resident costs |
| MaterialEconomy.lots | root-collection | materials.py: MaterialEconomy writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| MaterialEconomy.next_item | scalar | MaterialEconomy field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialEconomy.next_lot | scalar | MaterialEconomy field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.consumed | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.created_year | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.id | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.kind | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.magical_properties | fixed-tuple | materials.py: MaterialLot writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| MaterialLot.material_rank | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.origin_event | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.owner_id | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.owner_kind | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.producer | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.quality | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.quantity | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.settlement | scalar | MaterialLot field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MaterialLot.transfers | list-history | materials.py: MaterialLot writers | unbounded; compact header, bounded point/tail operations; whole-list edits remain explicit O(H) | typed list reference with current-owner integer event-ID validation; genuine legacy lists remain readable with resident costs |
| MetaphysicalState.next_token | scalar | MetaphysicalState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MetaphysicalState.resurrection_tokens | root-collection | metaphysics.py: MetaphysicalState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| MetaphysicalState.souls | root-collection | metaphysics.py: MetaphysicalState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| MotiveState.belonging | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MotiveState.curiosity | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MotiveState.hunger | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MotiveState.legacy | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MotiveState.obligation | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MotiveState.safety | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MotiveState.status | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| MotiveState.wealth | scalar | MotiveState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.age | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.alive | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.attachment | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.born | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.curiosity | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.fear | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.grief | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.health | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.household | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.id | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.inhibition | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.occupation | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.parents | fixed-tuple | core.py: Person writers | generated writer-specific tuple; imported tuple/element bytes unrestricted and preserved | exact native immutable current value; requested/held input bytes charged separately |
| Person.rank | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.settlement | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.species | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.temperament | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Person.wealth | scalar | Person field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Practice.domain | scalar | Practice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Practice.id | scalar | Practice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Practice.name | scalar | Practice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Practice.origin_settlement | scalar | Practice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Practice.origin_year | scalar | Practice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Practice.parent | scalar | Practice field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Practice.traits | map-history | culture.py: Practice writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Property.created | scalar | Property field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Property.id | scalar | Property field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Property.kind | scalar | Property field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Property.owner_id | scalar | Property field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Property.owner_kind | scalar | Property field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Property.ownership | list-history | economy.py: Property writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Property.provenance | list-history | economy.py: Property writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| Property.settlement | scalar | Property field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Property.value | scalar | Property field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| RankedCurrencyState.consumed | root-collection | currency.py: RankedCurrencyState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| RankedCurrencyState.minted | root-collection | currency.py: RankedCurrencyState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| RankedCurrencyState.treasuries | root-collection | currency.py: treasury_transfer | generated denomination keys guarded by COIN_VALUE; direct/imported dictionaries unrestricted and not truncated | lazy outer currency table; checked map root/physical entries in explicit graph-copy lane and native checked assignment; resident dict legacy compatibility |
| RankedCurrencyState.wallets | root-collection | currency.py: wallet, credit, transfer, consume, exchange | generated denomination keys guarded by COIN_VALUE; direct/imported dictionaries unrestricted and not truncated | lazy outer currency table; checked map root/physical entries in explicit graph-copy lane and native checked assignment; resident dict legacy compatibility |
| Ref.id | scalar | Ref field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Ref.kind | scalar | Ref field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.a | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.attachment | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.attraction | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.b | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.familiarity | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.obligation | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.resentment | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Relationship.shared_history | list-history | social.py: Relationship writers | unbounded; compact header, bounded point/tail operations; whole-list edits remain explicit O(H) | typed list reference with current-owner integer event-ID validation; genuine legacy lists remain readable with resident costs |
| Relationship.trust | scalar | Relationship field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResponseModel.coefficients | bounded-generated-list | mastery_training.py: ResponseModel writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage; trial trims samples to 3/5, solve coefficients <=5 | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| ResponseModel.samples | bounded-generated-list | mastery_training.py: ResponseModel writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage; trial trims samples to 3/5, solve coefficients <=5 | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| ResponseModel.trials | scalar | ResponseModel field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResponseModel.validated | scalar | ResponseModel field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.consumed_event | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.consumed_year | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.grant_event | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.granted_year | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.id | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.patron_id | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.patron_kind | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ResurrectionToken.person | scalar | ResurrectionToken field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.defense | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.food_stock | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.households | ordered-history | core.py: Settlement writers | unbounded; exact order, duplicates and extinct occurrences | counted HistoryReference in counted conversion lane; legacy eager mode remains explicit |
| Settlement.id | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.irrigation | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.memory | current-map | engine.py: Simulation._pressure writes monster_surge and decays values; warfare.py: update_warfare writes war | generated keys monster_surge/war; imported arbitrary map unrestricted and preserved | checked map reference in explicit graph-copy lane and checked assignment; genuine legacy remains resident compatibility |
| Settlement.prosperity | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.roads | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.x | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Settlement.y | scalar | Settlement field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SkillHistory.domain | scalar | SkillHistory field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SkillHistory.level | scalar | SkillHistory field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SkillHistory.person | scalar | SkillHistory field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SkillHistory.practice | scalar | SkillHistory field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SkillHistory.provenance | list-history | skills.py: SkillHistory writers | unbounded native scalar history; header and point/tail operations are paged; legacy representation has explicit O(H) costs | typed list reference and shared history-page budget; native scalar conversion integrated; recursive mutable cold imports reject before staging; genuine legacy lists remain readable |
| SkillHistory.teachers | list-history | skills.py: SkillHistory writers | unbounded native scalar history; header and point/tail operations are paged; legacy representation has explicit O(H) costs | typed list reference and shared history-page budget; native scalar conversion integrated; recursive mutable cold imports reject before staging; genuine legacy lists remain readable |
| SkillState.skills | root-collection | skills.py: SkillState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| SocialGraph.adjacency | root-collection | social.py: SocialGraph writers | unbounded historical buckets; candidate lane uses compact headers and bounded point additions | typed set reference in explicit native-graph conversion; legacy buckets remain readable with resident costs |
| SocialGraph.edges | root-collection | social.py: SocialGraph writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| SocialGraph.partnerships | root-collection | social.py: SocialGraph writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| SocietyAccountabilityState.inquiries | root-collection | society_accountability.py: SocietyAccountabilityState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| SocietyAccountabilityState.next_inquiry | scalar | SocietyAccountabilityState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.applied_year | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.branch | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.days_completed | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.eligibility_verified | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.id | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.judgment_score | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.magical_score | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.origin_event | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.passed | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.person | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.physical_score | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.resolved_event | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.society | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SocietyApplication.stage | scalar | SocietyApplication field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.authorities | set-history | metaphysics.py: SoulState writers | unbounded; compact header and indexed point edits; explicit iteration/materialization retains O(H) costs | typed scalar set/map reference and shared cache budget; mutable descendant cold imports reject before staging; genuine legacy collections remain readable |
| SoulState.body_generation | scalar | SoulState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.cosmic_links | map-history | metaphysics.py: SoulState writers | unbounded; compact header and indexed point edits; explicit iteration/materialization retains O(H) costs | typed scalar set/map reference and shared cache budget; mutable descendant cold imports reject before staging; genuine legacy collections remain readable |
| SoulState.death_count | scalar | SoulState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.marks | set-history | metaphysics.py: SoulState writers | unbounded; compact header and indexed point edits; explicit iteration/materialization retains O(H) costs | typed scalar set/map reference and shared cache budget; mutable descendant cold imports reject before staging; genuine legacy collections remain readable |
| SoulState.ontology | scalar | SoulState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.origin_world | scalar | SoulState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.outworlder | scalar | SoulState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.person | scalar | SoulState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.resurrection_count | scalar | SoulState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| SoulState.transformations | list-history | metaphysics.py: SoulState writers | unbounded native scalar history; header and point/tail operations are paged; legacy representation has explicit O(H) costs | typed list reference and shared history-page budget; native scalar conversion integrated; recursive mutable cold imports reject before staging; genuine legacy lists remain readable |
| ThreatEcologyState.next_id | scalar | ThreatEcologyState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| ThreatEcologyState.resolutions | root-collection | threat_ecology.py: ThreatEcologyState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| ThreatEcologyState.threats | root-collection | threat_ecology.py: ThreatEcologyState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| TradeRoute.a | scalar | TradeRoute field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| TradeRoute.b | scalar | TradeRoute field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| TradeRoute.exchanges | scalar | TradeRoute field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| TradeRoute.last_used | scalar | TradeRoute field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| TradeRoute.strength | scalar | TradeRoute field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.event_id | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.id | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.item_id | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.item_kind | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.kind | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.mutation | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.reliability | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.source_id | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.source_kind | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.target_id | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.target_kind | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Transmission.year | scalar | Transmission field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| TransmissionState.next_id | scalar | TransmissionState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| TransmissionState.records | root-collection | transmission.py: TransmissionState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| Understanding.applications | bounded-generated-map | advancement.py: Understanding writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage; mastery_training.needs_trial caps successful applications and transfers; evidence writer reviewed separately | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| Understanding.evidence | bounded-generated-map | advancement.py: Understanding writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage; mastery_training.needs_trial caps successful applications and transfers; evidence writer reviewed separately | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| Understanding.integration | scalar | Understanding field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| Understanding.transfers | bounded-generated-list | advancement.py: Understanding writers | generated guards only; explicit checked advancement copy preserves unrestricted imports in compact recursive storage; mastery_training.needs_trial caps successful applications and transfers; evidence writer reviewed separately | explicit checked advancement copy uses recursive record/history references; genuine legacy paths retain resident costs |
| WarfareState.conflicts | root-collection | warfare.py: WarfareState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| WarfareState.next_conflict | scalar | WarfareState field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| WarfareState.tensions | root-collection | warfare.py: WarfareState writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.advancement | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.agency | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.ambient_magic | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.cells | root-collection | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.communities | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.culture | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.currency | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.divinity | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.economy | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.event_ids | set-history | core.py: World.emit and exact set mutations | prefix does not materialize; local exception work; explicit whole-set iteration visits requested members | captured range or paged exceptions, checked NaN atoms and shared component authority; full-copy semantic scrub |
| World.events | root-collection | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.genealogy | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.households | root-collection | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.infrastructure | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.institutions | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.knowledge | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.lineage | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.local | root-collection | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.magic_resources | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.materials | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.metaphysics | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.next_event | scalar | World field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| World.next_household | scalar | World field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| World.next_person | scalar | World field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| World.next_settlement | scalar | World field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| World.people | root-collection | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.seed | scalar | World field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| World.settlements | root-collection | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.skills | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.social | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.society_accountability | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.threat_ecology | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.trade_routes | root-collection | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.transmission | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.warfare | state-root | core.py: World writers | current work or historical outer collection; concrete family boundary governs payload loading | registered root/family; legacy eager costs disclosed |
| World.year | scalar | World field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| culture.Institution.assets | scalar | culture.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| culture.Institution.authority | scalar | culture.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| culture.Institution.founded | scalar | culture.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| culture.Institution.id | scalar | culture.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| culture.Institution.kind | scalar | culture.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| culture.Institution.legitimacy | scalar | culture.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| culture.Institution.practices | set-history | civilization.py: civilization_step creates set(strong[:4]); culture.py reads support | generated <=4 practices; imported set unrestricted and preserved | checked set reference in explicit upgrade and checked replacement; genuine legacy resident |
| culture.Institution.settlement | scalar | culture.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| institutions.Institution.branches | list-history | institutions.py: Institution writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| institutions.Institution.founded_year | scalar | institutions.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| institutions.Institution.id | scalar | institutions.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| institutions.Institution.kind | scalar | institutions.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| institutions.Institution.members | set-history | institutions.py: Institution writers | unbounded; must use compact backing for ordinary operations | checked recursive history reference; Event snapshot data uses frozen histories/immutable segments; genuine legacy remains resident |
| institutions.Institution.name | scalar | institutions.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
| institutions.Institution.origin_event | scalar | institutions.Institution field assignment | one exact scalar; imported string/bytes length is not bounded | checked record/header scalar |
