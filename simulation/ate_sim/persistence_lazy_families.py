"""Concrete closeout family contracts; transaction ownership stays in the session.

The declarations below are deliberately static. New schema fields fail coverage
instead of receiving a guessed serialization or growth policy.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from types import MappingProxyType
from typing import Protocol
from .persistence_schema import ROOT_FIELDS, RECORD_FIELDS
from .incremental_store import RecordChange, Membership, _framed_sha
from .persistence_lazy_store import VersionChange, IdentityOccurrenceChange


@dataclass(frozen=True)
class FamilyAdapter:
    namespace: str
    root_path: tuple
    collection_kind: str
    storage_mode: str
    record_schema: int = 1
    identity_enabled: bool = True

    def absolute_path(self, key, relative=()):
        placement = (("index", key),) if self.collection_kind in ("list", "events") else (("key", key),)
        if self.namespace == "world.event_ids":
            placement = ()
        return self.root_path + placement + relative


# Baseline representation, not a claim that eager fields have been migrated.
_FAMILY_ROWS = (
    ('world.cells', 'dict', 'eager'),
    ('world.people', 'dict', 'lazy'),
    ('world.households', 'dict', 'eager'),
    ('world.settlements', 'dict', 'eager'),
    ('world.local', 'dict', 'eager'),
    ('world.trade_routes', 'dict', 'eager'),
    ('world.events', 'events', 'event'),
    ('world.event_ids', 'set', 'lazy'),
    ('world.genealogy.parents', 'dict', 'lazy'),
    ('world.genealogy.children', 'dict', 'lazy'),
    ('world.social.edges', 'dict', 'lazy'),
    ('world.social.partnerships', 'dict', 'lazy'),
    ('world.social.adjacency', 'dict', 'lazy'),
    ('world.economy.property', 'dict', 'lazy'),
    ('world.knowledge.claims', 'dict', 'eager'),
    ('world.knowledge.beliefs', 'dict', 'lazy'),
    ('world.knowledge.claim_index', 'dict', 'eager'),
    ('world.culture.practices', 'dict', 'lazy'),
    ('world.culture.institutions', 'dict', 'eager'),
    ('world.culture.laws', 'dict', 'eager'),
    ('world.culture.adoption', 'dict', 'lazy'),
    ('world.lineage.nodes', 'dict', 'lazy'),
    ('world.lineage.children', 'dict', 'lazy'),
    ('world.communities.communities', 'dict', 'lazy'),
    ('world.communities.memberships', 'dict', 'lazy'),
    ('world.transmission.records', 'dict', 'lazy'),
    ('world.skills.skills', 'dict', 'lazy'),
    ('world.infrastructure.assets', 'dict', 'lazy'),
    ('world.agency.motives', 'dict', 'lazy'),
    ('world.agency.actions', 'list', 'eager'),
    ('world.advancement.paths', 'dict', 'lazy'),
    ('world.magic_resources.resources', 'dict', 'lazy'),
    ('world.magic_resources.owner_index', 'dict', 'lazy'),
    ('world.magic_resources.aspirations', 'dict', 'lazy'),
    ('world.institutions.institutions', 'dict', 'lazy'),
    ('world.institutions.branches', 'dict', 'lazy'),
    ('world.institutions.magic_records', 'dict', 'lazy'),
    ('world.institutions.notices', 'dict', 'lazy'),
    ('world.institutions.applications', 'dict', 'lazy'),
    ('world.metaphysics.souls', 'dict', 'lazy'),
    ('world.metaphysics.resurrection_tokens', 'dict', 'lazy'),
    ('world.divinity.gods', 'dict', 'lazy'),
    ('world.divinity.great_astral_beings', 'dict', 'lazy'),
    ('world.divinity.churches', 'dict', 'lazy'),
    ('world.materials.lots', 'dict', 'lazy'),
    ('world.materials.items', 'dict', 'lazy'),
    ('world.materials.lot_index', 'dict', 'lazy'),
    ('world.materials.active_lot_index', 'dict', 'lazy'),
    ('world.ambient_magic.fields', 'dict', 'eager'),
    ('world.warfare.conflicts', 'dict', 'lazy'),
    ('world.warfare.tensions', 'dict', 'eager'),
    ('world.society_accountability.inquiries', 'dict', 'lazy'),
    ('world.currency.wallets', 'dict', 'lazy'),
    ('world.currency.minted', 'dict', 'eager'),
    ('world.currency.treasuries', 'dict', 'lazy'),
    ('world.currency.consumed', 'dict', 'eager'),
    ('world.threat_ecology.threats', 'dict', 'lazy'),
    ('world.threat_ecology.resolutions', 'dict', 'lazy'),
 )
FAMILIES = MappingProxyType({
    ns: FamilyAdapter(ns, tuple(("field", part) for part in ns.split(".")[1:]), kind, mode)
    for ns, kind, mode in _FAMILY_ROWS
})


def validate_manifest():
    expected = {f"{root}.{field}" for root, fields in ROOT_FIELDS.items()
                for field, kind in fields.items() if kind not in ("int", "state")}
    if len(_FAMILY_ROWS) != len(FAMILIES) or set(FAMILIES) != expected:
        raise ValueError(f"family coverage mismatch: {set(FAMILIES) ^ expected}")


@dataclass(frozen=True)
class FieldPolicy:
    category: str
    writer: str
    bound: str
    representation: str


# Exact scalar declarations generated once from the audited schema, never at open.
_SCALAR_FIELDS = {
    'Ref': ('kind', 'id'),
    'Event': ('id', 'year', 'kind', 'layer', 'location'),
    'Person': ('id', 'born', 'settlement', 'household', 'alive', 'age', 'wealth', 'health', 'temperament', 'attachment', 'curiosity', 'inhibition', 'grief', 'fear', 'rank', 'species', 'occupation'),
    'Household': ('id', 'settlement', 'wealth', 'food', 'preparedness', 'lineage', 'alive'),
    'Settlement': ('id', 'x', 'y', 'food_stock', 'defense', 'irrigation', 'roads', 'prosperity'),
    'Cell': ('x', 'y', 'elevation', 'moisture', 'fertility', 'forest', 'hazard'),
    'LocalState': ('rain', 'drought', 'flood', 'scarcity'),
    'TradeRoute': ('a', 'b', 'strength', 'exchanges', 'last_used'),
    'World': ('seed', 'year', 'next_person', 'next_household', 'next_settlement', 'next_event'),
    'Genealogy': (),
    'Relationship': ('a', 'b', 'familiarity', 'trust', 'attachment', 'obligation', 'resentment', 'attraction'),
    'SocialGraph': (),
    'Property': ('id', 'kind', 'settlement', 'owner_kind', 'owner_id', 'value', 'created'),
    'Economy': ('next_property',),
    'KnowledgeClaim': ('id', 'subject', 'proposition', 'truth', 'origin_event'),
    'KnowledgeState': ('next_claim',),
    'Practice': ('id', 'domain', 'name', 'origin_year', 'origin_settlement', 'parent'),
    'culture.Institution': ('id', 'settlement', 'kind', 'founded', 'authority', 'assets', 'legitimacy'),
    'Law': ('id', 'settlement', 'domain', 'strictness', 'enforcement', 'origin_event'),
    'CulturalState': ('next_practice', 'next_institution', 'next_law'),
    'LineageNode': ('kind', 'id', 'origin_event', 'origin_year'),
    'LineageState': (),
    'Community': ('id', 'kind', 'founded', 'origin_settlement', 'origin_event', 'parent', 'active'),
    'CommunityState': ('next_community',),
    'Transmission': ('id', 'year', 'kind', 'item_kind', 'item_id', 'source_kind', 'source_id', 'target_kind', 'target_id', 'event_id', 'reliability', 'mutation'),
    'TransmissionState': ('next_id',),
    'SkillHistory': ('person', 'domain', 'level', 'practice'),
    'SkillState': (),
    'Infrastructure': ('id', 'kind', 'condition', 'capacity', 'built', 'origin_event'),
    'InfrastructureState': ('next_id',),
    'MotiveState': ('hunger', 'safety', 'belonging', 'wealth', 'curiosity', 'legacy', 'obligation', 'status'),
    'ActionRecord': ('year', 'person', 'action', 'motive', 'strength', 'event_id'),
    'AgencyState': (),
    'Understanding': ('integration',),
    'AbilityProgress': ('essence', 'source', 'semantic_key', 'name', 'function', 'domain', 'awakened_year', 'origin_event', 'special', 'aura', 'rank', 'level', 'progress', 'milestone_event'),
    'EssencePath': ('confluence', 'confluence_name', 'core_fraction'),
    'AdvancementState': (),
    'ResponseModel': ('trials', 'validated'),
    'MagicAspiration': ('drive', 'reason', 'formed_year', 'preparation', 'search_years', 'completion_goal', 'urgency', 'compromise_tolerance', 'stone_selectiveness', 'risk_tolerance', 'adventurer_aspiration'),
    'MagicResource': ('id', 'kind', 'key', 'rarity', 'location', 'owner_kind', 'owner_id', 'created_year', 'origin_event', 'consumed_year', 'consumed_by', 'consumed_event'),
    'MagicResourceState': ('next_id',),
    'institutions.Institution': ('id', 'kind', 'name', 'founded_year', 'origin_event'),
    'Branch': ('id', 'institution', 'settlement', 'founded_year', 'origin_event', 'authority'),
    'MagicUserRecord': ('id', 'person', 'branch', 'year', 'confluence_id', 'confluence_name', 'disclosure', 'source_event'),
    'AdventureNotice': ('id', 'branch', 'year', 'kind', 'location', 'cause_event', 'status', 'resolved_event', 'required_rank'),
    'SocietyApplication': ('id', 'society', 'person', 'branch', 'applied_year', 'eligibility_verified', 'stage', 'days_completed', 'physical_score', 'magical_score', 'judgment_score', 'passed', 'origin_event', 'resolved_event'),
    'InstitutionState': ('next_institution', 'next_branch', 'next_record', 'next_notice', 'next_application'),
    'SoulState': ('person', 'origin_world', 'outworlder', 'body_generation', 'death_count', 'resurrection_count', 'ontology'),
    'ResurrectionToken': ('id', 'person', 'patron_kind', 'patron_id', 'granted_year', 'grant_event', 'consumed_year', 'consumed_event'),
    'MetaphysicalState': ('next_token',),
    'God': ('id', 'name', 'ontology', 'transcendent'),
    'GreatAstralBeing': ('id', 'name', 'ontology', 'transcendent'),
    'Church': ('id', 'god', 'settlement', 'founded_year', 'origin_event', 'authority', 'wealth'),
    'DivineState': ('next_church',),
    'MaterialLot': ('id', 'kind', 'quantity', 'quality', 'settlement', 'producer', 'created_year', 'origin_event', 'owner_kind', 'owner_id', 'consumed', 'material_rank'),
    'CraftedItem': ('id', 'kind', 'quality', 'rarity', 'settlement', 'craftsperson', 'created_year', 'origin_event', 'owner_kind', 'owner_id', 'item_rank', 'magical'),
    'MaterialEconomy': ('next_lot', 'next_item'),
    'AmbientField': ('level', 'peak', 'critical_years', 'quintessence', 'surges'),
    'AmbientMagicState': (),
    'Conflict': ('id', 'attacker', 'defender', 'started_year', 'cause', 'cause_event', 'status', 'war_score', 'battles', 'attacker_losses', 'defender_losses', 'ended_year', 'origin_event', 'peace_event'),
    'WarfareState': ('next_conflict',),
    'Inquiry': ('id', 'branch', 'opened_year', 'trigger_kind', 'trigger_event', 'severity', 'status', 'findings', 'closed_year', 'origin_event', 'resolved_event'),
    'SocietyAccountabilityState': ('next_inquiry',),
    'RankedCurrencyState': (),
    'MagicalThreat': ('id', 'kind', 'rank', 'location', 'created_year', 'ambient', 'status', 'origin_event', 'form'),
    'ThreatEcologyState': ('next_id',),
}

_COLLECTION_POLICIES = {
    ('Event', 'actors'): FieldPolicy('fixed-tuple', 'core.py: Event writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('Event', 'causes'): FieldPolicy('fixed-tuple', 'core.py: Event writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('Event', 'data'): FieldPolicy('value-history', 'core.py: Event writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Person', 'parents'): FieldPolicy('fixed-tuple', 'core.py: Person writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('Household', 'members'): FieldPolicy('ordered-history', 'core.py: Household writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Settlement', 'households'): FieldPolicy('ordered-history', 'core.py: Settlement writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Settlement', 'memory'): FieldPolicy('current-map', 'core.py: Settlement writers', 'generated keys monster_surge/war; imported arbitrary map unrestricted', 'resident current map with explicit imported-value classification'),
    ('World', 'cells'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'people'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'households'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'settlements'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'local'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'trade_routes'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'events'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'event_ids'): FieldPolicy('root-collection', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'genealogy'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'social'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'economy'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'knowledge'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'culture'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'lineage'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'communities'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'transmission'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'skills'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'infrastructure'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'agency'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'advancement'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'magic_resources'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'institutions'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'metaphysics'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'divinity'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'materials'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'ambient_magic'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'warfare'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'society_accountability'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'currency'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('World', 'threat_ecology'): FieldPolicy('state-root', 'core.py: World writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('Genealogy', 'parents'): FieldPolicy('root-collection', 'genealogy.py: Genealogy writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('Genealogy', 'children'): FieldPolicy('root-collection', 'genealogy.py: Genealogy writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('Relationship', 'shared_history'): FieldPolicy('list-history', 'social.py: Relationship writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('SocialGraph', 'edges'): FieldPolicy('root-collection', 'social.py: SocialGraph writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('SocialGraph', 'partnerships'): FieldPolicy('root-collection', 'social.py: SocialGraph writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('SocialGraph', 'adjacency'): FieldPolicy('root-collection', 'social.py: SocialGraph writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('Property', 'provenance'): FieldPolicy('list-history', 'economy.py: Property writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Property', 'ownership'): FieldPolicy('list-history', 'economy.py: Property writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Economy', 'property'): FieldPolicy('root-collection', 'economy.py: Economy writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('KnowledgeState', 'claims'): FieldPolicy('root-collection', 'knowledge.py: KnowledgeState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('KnowledgeState', 'beliefs'): FieldPolicy('root-collection', 'knowledge.py: KnowledgeState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('KnowledgeState', 'claim_index'): FieldPolicy('root-collection', 'knowledge.py: KnowledgeState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('Practice', 'traits'): FieldPolicy('map-history', 'culture.py: Practice writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('culture.Institution', 'practices'): FieldPolicy('set-history', 'culture.py: Institution writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('CulturalState', 'practices'): FieldPolicy('root-collection', 'culture.py: CulturalState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('CulturalState', 'institutions'): FieldPolicy('root-collection', 'culture.py: CulturalState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('CulturalState', 'laws'): FieldPolicy('root-collection', 'culture.py: CulturalState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('CulturalState', 'adoption'): FieldPolicy('root-collection', 'culture.py: CulturalState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('LineageNode', 'parents'): FieldPolicy('fixed-tuple', 'lineage.py: LineageNode writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('LineageState', 'nodes'): FieldPolicy('root-collection', 'lineage.py: LineageState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('LineageState', 'children'): FieldPolicy('root-collection', 'lineage.py: LineageState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('CommunityState', 'communities'): FieldPolicy('root-collection', 'communities.py: CommunityState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('CommunityState', 'memberships'): FieldPolicy('root-collection', 'communities.py: CommunityState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('TransmissionState', 'records'): FieldPolicy('root-collection', 'transmission.py: TransmissionState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('SkillHistory', 'teachers'): FieldPolicy('list-history', 'skills.py: SkillHistory writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('SkillHistory', 'provenance'): FieldPolicy('list-history', 'skills.py: SkillHistory writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('SkillState', 'skills'): FieldPolicy('root-collection', 'skills.py: SkillState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('Infrastructure', 'settlements'): FieldPolicy('fixed-tuple', 'infrastructure.py: Infrastructure writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('Infrastructure', 'provenance'): FieldPolicy('list-history', 'infrastructure.py: Infrastructure writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('InfrastructureState', 'assets'): FieldPolicy('root-collection', 'infrastructure.py: InfrastructureState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('AgencyState', 'motives'): FieldPolicy('root-collection', 'agency.py: AgencyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('AgencyState', 'actions'): FieldPolicy('root-collection', 'agency.py: AgencyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('Understanding', 'evidence'): FieldPolicy('bounded-generated-map', 'advancement.py: Understanding writers', 'generated guards only; unrestricted imports are materialized compatibility state; mastery_training.needs_trial caps successful applications and transfers; evidence writer reviewed separately', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('Understanding', 'applications'): FieldPolicy('bounded-generated-map', 'advancement.py: Understanding writers', 'generated guards only; unrestricted imports are materialized compatibility state; mastery_training.needs_trial caps successful applications and transfers; evidence writer reviewed separately', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('Understanding', 'transfers'): FieldPolicy('bounded-generated-list', 'advancement.py: Understanding writers', 'generated guards only; unrestricted imports are materialized compatibility state; mastery_training.needs_trial caps successful applications and transfers; evidence writer reviewed separately', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('AbilityProgress', 'response_model'): FieldPolicy('bounded-generated-record', 'advancement.py: AbilityProgress writers', 'generated guards only; unrestricted imports are materialized compatibility state', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('AbilityProgress', 'understanding'): FieldPolicy('bounded-generated-record', 'advancement.py: AbilityProgress writers', 'generated guards only; unrestricted imports are materialized compatibility state', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('EssencePath', 'base_essences'): FieldPolicy('bounded-generated-list', 'advancement.py: EssencePath writers', 'generated guards only; unrestricted imports are materialized compatibility state; add_essence <=3 base, _semantic_ability <=20 abilities', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('EssencePath', 'confluence_concepts'): FieldPolicy('fixed-tuple', 'advancement.py: EssencePath writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('EssencePath', 'abilities'): FieldPolicy('bounded-generated-list', 'advancement.py: EssencePath writers', 'generated guards only; unrestricted imports are materialized compatibility state; add_essence <=3 base, _semantic_ability <=20 abilities', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('AdvancementState', 'paths'): FieldPolicy('root-collection', 'advancement.py: AdvancementState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('ResponseModel', 'samples'): FieldPolicy('bounded-generated-list', 'mastery_training.py: ResponseModel writers', 'generated guards only; unrestricted imports are materialized compatibility state; trial trims samples to 3/5, solve coefficients <=5', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('ResponseModel', 'coefficients'): FieldPolicy('bounded-generated-list', 'mastery_training.py: ResponseModel writers', 'generated guards only; unrestricted imports are materialized compatibility state; trial trims samples to 3/5, solve coefficients <=5', 'resident tracked topology; oversized import requires explicit classification before new-format conversion'),
    ('MagicAspiration', 'desired_base_essences'): FieldPolicy('fixed-tuple', 'magic_resources.py: MagicAspiration writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('MagicAspiration', 'desired_abilities'): FieldPolicy('fixed-tuple', 'magic_resources.py: MagicAspiration writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('MagicResource', 'transfers'): FieldPolicy('list-history', 'magic_resources.py: MagicResource writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('MagicResourceState', 'resources'): FieldPolicy('root-collection', 'magic_resources.py: MagicResourceState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MagicResourceState', 'owner_index'): FieldPolicy('root-collection', 'magic_resources.py: MagicResourceState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MagicResourceState', 'aspirations'): FieldPolicy('root-collection', 'magic_resources.py: MagicResourceState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('institutions.Institution', 'branches'): FieldPolicy('list-history', 'institutions.py: Institution writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('institutions.Institution', 'members'): FieldPolicy('set-history', 'institutions.py: Institution writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Branch', 'records'): FieldPolicy('set-history', 'institutions.py: Branch writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Branch', 'notices'): FieldPolicy('set-history', 'institutions.py: Branch writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Branch', 'trainees'): FieldPolicy('map-history', 'institutions.py: Branch writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('MagicUserRecord', 'essence_ids'): FieldPolicy('fixed-tuple', 'institutions.py: MagicUserRecord writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('MagicUserRecord', 'abilities'): FieldPolicy('fixed-tuple', 'institutions.py: MagicUserRecord writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('MagicUserRecord', 'ability_names'): FieldPolicy('fixed-tuple', 'institutions.py: MagicUserRecord writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('AdventureNotice', 'assigned_to'): FieldPolicy('fixed-tuple', 'institutions.py: AdventureNotice writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('InstitutionState', 'institutions'): FieldPolicy('root-collection', 'institutions.py: InstitutionState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('InstitutionState', 'branches'): FieldPolicy('root-collection', 'institutions.py: InstitutionState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('InstitutionState', 'magic_records'): FieldPolicy('root-collection', 'institutions.py: InstitutionState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('InstitutionState', 'notices'): FieldPolicy('root-collection', 'institutions.py: InstitutionState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('InstitutionState', 'applications'): FieldPolicy('root-collection', 'institutions.py: InstitutionState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('SoulState', 'authorities'): FieldPolicy('set-history', 'metaphysics.py: SoulState writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('SoulState', 'marks'): FieldPolicy('set-history', 'metaphysics.py: SoulState writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('SoulState', 'cosmic_links'): FieldPolicy('map-history', 'metaphysics.py: SoulState writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('SoulState', 'transformations'): FieldPolicy('list-history', 'metaphysics.py: SoulState writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('MetaphysicalState', 'souls'): FieldPolicy('root-collection', 'metaphysics.py: MetaphysicalState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MetaphysicalState', 'resurrection_tokens'): FieldPolicy('root-collection', 'metaphysics.py: MetaphysicalState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('God', 'domains'): FieldPolicy('fixed-tuple', 'divinity.py: God writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('God', 'manifestations'): FieldPolicy('list-history', 'divinity.py: God writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('God', 'relationships'): FieldPolicy('map-history', 'divinity.py: God writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('GreatAstralBeing', 'authorities'): FieldPolicy('fixed-tuple', 'divinity.py: GreatAstralBeing writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('GreatAstralBeing', 'interventions'): FieldPolicy('list-history', 'divinity.py: GreatAstralBeing writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('GreatAstralBeing', 'relationships'): FieldPolicy('map-history', 'divinity.py: GreatAstralBeing writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Church', 'clergy'): FieldPolicy('set-history', 'divinity.py: Church writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Church', 'followers'): FieldPolicy('set-history', 'divinity.py: Church writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('Church', 'doctrine_claims'): FieldPolicy('set-history', 'divinity.py: Church writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('DivineState', 'gods'): FieldPolicy('root-collection', 'divinity.py: DivineState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('DivineState', 'great_astral_beings'): FieldPolicy('root-collection', 'divinity.py: DivineState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('DivineState', 'churches'): FieldPolicy('root-collection', 'divinity.py: DivineState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MaterialLot', 'magical_properties'): FieldPolicy('fixed-tuple', 'materials.py: MaterialLot writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('MaterialLot', 'transfers'): FieldPolicy('list-history', 'materials.py: MaterialLot writers', 'unbounded; must use compact backing for ordinary operations', 'typed history reference (existing or pending integration); event data uses immutable segment values'),
    ('CraftedItem', 'materials'): FieldPolicy('fixed-tuple', 'materials.py: CraftedItem writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('CraftedItem', 'magical_properties'): FieldPolicy('fixed-tuple', 'materials.py: CraftedItem writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('MaterialEconomy', 'lots'): FieldPolicy('root-collection', 'materials.py: MaterialEconomy writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MaterialEconomy', 'items'): FieldPolicy('root-collection', 'materials.py: MaterialEconomy writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MaterialEconomy', 'lot_index'): FieldPolicy('root-collection', 'materials.py: MaterialEconomy writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MaterialEconomy', 'active_lot_index'): FieldPolicy('root-collection', 'materials.py: MaterialEconomy writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('AmbientMagicState', 'fields'): FieldPolicy('root-collection', 'ambient_magic.py: AmbientMagicState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('WarfareState', 'conflicts'): FieldPolicy('root-collection', 'warfare.py: WarfareState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('WarfareState', 'tensions'): FieldPolicy('root-collection', 'warfare.py: WarfareState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('SocietyAccountabilityState', 'inquiries'): FieldPolicy('root-collection', 'society_accountability.py: SocietyAccountabilityState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('RankedCurrencyState', 'wallets'): FieldPolicy('root-collection', 'currency.py: RankedCurrencyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('RankedCurrencyState', 'minted'): FieldPolicy('root-collection', 'currency.py: RankedCurrencyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('RankedCurrencyState', 'treasuries'): FieldPolicy('root-collection', 'currency.py: RankedCurrencyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('RankedCurrencyState', 'consumed'): FieldPolicy('root-collection', 'currency.py: RankedCurrencyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('MagicalThreat', 'environment_tags'): FieldPolicy('fixed-tuple', 'threat_ecology.py: MagicalThreat writers', 'immutable tuple; writer-specific generated length, imported tuple unrestricted', 'exact tuple values; no mutable history flattening'),
    ('ThreatEcologyState', 'threats'): FieldPolicy('root-collection', 'threat_ecology.py: ThreatEcologyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
    ('ThreatEcologyState', 'resolutions'): FieldPolicy('root-collection', 'threat_ecology.py: ThreatEcologyState writers', 'current work or historical outer collection; concrete family boundary governs payload loading', 'registered root/family; legacy eager costs disclosed'),
}
FIELD_POLICIES = MappingProxyType({
    **{(name, field): FieldPolicy("scalar", f"{name} field assignment",
        "one exact scalar; imported string/bytes length is not bounded",
        "checked record/header scalar")
       for name, fields in _SCALAR_FIELDS.items() for field in fields},
    **_COLLECTION_POLICIES,
})


def record_name(cls):
    return (cls.__module__.split(".")[-1] + ".Institution"
            if cls.__name__ == "Institution" else cls.__name__)


def validate_field_inventory(records=RECORD_FIELDS):
    expected = {(record_name(cls), field) for cls, fields in records.items() for field in fields}
    mismatch = expected ^ set(FIELD_POLICIES)
    if mismatch:
        raise ValueError(f"unclassified or obsolete schema fields: {sorted(mismatch)}")


@dataclass(frozen=True)
class ParticipantDelta:
    participant: str
    version_bytes: tuple[bytes, ...]
    ordinary_bytes: tuple[bytes, ...]
    identity_bytes: tuple[bytes, ...]
    fingerprint: str

    @classmethod
    def freeze(cls, codec, participant, *, version_changes=(), ordinary_changes=(), identity_changes=()):
        versions = tuple(codec.encode((v.namespace, v.key, v.value, v.record_schema,
            v.delete, tuple((m.index_name, m.value, m.ordinal) for m in v.memberships),
            v.reinsertion)) for v in version_changes)
        records = tuple(codec.encode((r.namespace, r.key, r.value, r.record_schema, r.delete,
            tuple((m.index_name, m.value, m.ordinal) for m in r.memberships)))
                        for r in ordinary_changes)
        identities = tuple(codec.encode((i.owner_namespace, i.owner_key,
            i.occurrence_path, i.incarnation_id, i.delete)) for i in identity_changes)
        fingerprint = _framed_sha(b"save-participant-v1", codec.encode(participant),
                                  codec.encode((versions, records, identities)))
        return cls(participant, versions, records, identities, fingerprint)

    def decode(self, codec):
        versions = []
        for payload in self.version_bytes:
            ns, key, value, schema, delete, memberships, reinsert = codec.decode(payload)
            versions.append(VersionChange(ns, key, value, schema, delete,
                                          tuple(Membership(*m) for m in memberships), reinsert))
        records = []
        for payload in self.ordinary_bytes:
            ns, key, value, schema, delete, memberships = codec.decode(payload)
            records.append(RecordChange(ns, key, value, schema, delete,
                                       tuple(Membership(*m) for m in memberships)))
        return (tuple(versions), tuple(records),
                tuple(IdentityOccurrenceChange(*codec.decode(b)) for b in self.identity_bytes))


class SaveParticipant(Protocol):
    def prepare_delta(self, context) -> ParticipantDelta: ...
    def validate_publication(self, delta: ParticipantDelta, successor_pin) -> None: ...
    def accept_delta(self, delta: ParticipantDelta, successor_pin) -> None: ...


@dataclass(frozen=True)
class Measurement:
    store_counters: tuple[tuple[str, int], ...]

    @classmethod
    def capture(cls, store):
        return cls(tuple(asdict(store.diagnostics()).items()))

    def since(self, previous):
        old = dict(previous.store_counters)
        out = {k: v - old[k] for k, v in self.store_counters}
        # SQLite does not expose examined-row counts here. EXPLAIN and scale
        # tests are separate evidence; returned rows never stand in for scans.
        out["sql_rows_examined"] = None
        return out
