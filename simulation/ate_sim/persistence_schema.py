"""Explicit P2A v1 field/type allowlist. Schema changes require deliberate review."""
from . import core
from . import genealogy
from . import social
from . import economy
from . import knowledge
from . import culture
from . import lineage
from . import communities
from . import transmission
from . import skills
from . import infrastructure
from . import agency
from . import advancement
from . import mastery_training
from . import magic_resources
from . import institutions
from . import metaphysics
from . import divinity
from . import materials
from . import ambient_magic
from . import warfare
from . import society_accountability
from . import currency
from . import threat_ecology

RECORD_FIELDS = {
    core.Ref: ('kind', 'id'),
    core.Event: ('id', 'year', 'kind', 'layer', 'actors', 'location', 'causes', 'data'),
    core.Person: ('id', 'born', 'settlement', 'household', 'alive', 'age', 'wealth', 'health', 'temperament', 'attachment', 'curiosity', 'inhibition', 'grief', 'fear', 'rank', 'species', 'occupation', 'parents'),
    core.Household: ('id', 'settlement', 'members', 'wealth', 'food', 'preparedness', 'lineage', 'alive'),
    core.Settlement: ('id', 'x', 'y', 'households', 'food_stock', 'defense', 'irrigation', 'roads', 'prosperity', 'memory'),
    core.Cell: ('x', 'y', 'elevation', 'moisture', 'fertility', 'forest', 'hazard'),
    core.LocalState: ('rain', 'drought', 'flood', 'scarcity'),
    core.TradeRoute: ('a', 'b', 'strength', 'exchanges', 'last_used'),
    core.World: ('seed', 'year', 'cells', 'people', 'households', 'settlements', 'local', 'trade_routes', 'events', 'event_ids', 'genealogy', 'social', 'economy', 'knowledge', 'culture', 'lineage', 'communities', 'transmission', 'skills', 'infrastructure', 'agency', 'advancement', 'magic_resources', 'institutions', 'metaphysics', 'divinity', 'materials', 'ambient_magic', 'warfare', 'society_accountability', 'currency', 'threat_ecology', 'next_person', 'next_household', 'next_settlement', 'next_event'),
    genealogy.Genealogy: ('parents', 'children'),
    social.Relationship: ('a', 'b', 'familiarity', 'trust', 'attachment', 'obligation', 'resentment', 'attraction', 'shared_history'),
    social.SocialGraph: ('edges', 'partnerships', 'adjacency'),
    economy.Property: ('id', 'kind', 'settlement', 'owner_kind', 'owner_id', 'value', 'created', 'provenance', 'ownership'),
    economy.Economy: ('property', 'next_property'),
    knowledge.KnowledgeClaim: ('id', 'subject', 'proposition', 'truth', 'origin_event'),
    knowledge.KnowledgeState: ('claims', 'beliefs', 'claim_index', 'next_claim'),
    culture.Practice: ('id', 'domain', 'name', 'origin_year', 'origin_settlement', 'traits', 'parent'),
    culture.Institution: ('id', 'settlement', 'kind', 'founded', 'practices', 'authority', 'assets', 'legitimacy'),
    culture.Law: ('id', 'settlement', 'domain', 'strictness', 'enforcement', 'origin_event'),
    culture.CulturalState: ('practices', 'institutions', 'laws', 'adoption', 'next_practice', 'next_institution', 'next_law'),
    lineage.LineageNode: ('kind', 'id', 'parents', 'origin_event', 'origin_year'),
    lineage.LineageState: ('nodes', 'children'),
    communities.Community: ('id', 'kind', 'founded', 'origin_settlement', 'origin_event', 'parent', 'active'),
    communities.CommunityState: ('communities', 'memberships', 'next_community'),
    transmission.Transmission: ('id', 'year', 'kind', 'item_kind', 'item_id', 'source_kind', 'source_id', 'target_kind', 'target_id', 'event_id', 'reliability', 'mutation'),
    transmission.TransmissionState: ('records', 'next_id'),
    skills.SkillHistory: ('person', 'domain', 'level', 'practice', 'teachers', 'provenance'),
    skills.SkillState: ('skills',),
    infrastructure.Infrastructure: ('id', 'kind', 'settlements', 'condition', 'capacity', 'built', 'origin_event', 'provenance'),
    infrastructure.InfrastructureState: ('assets', 'next_id'),
    agency.MotiveState: ('hunger', 'safety', 'belonging', 'wealth', 'curiosity', 'legacy', 'obligation', 'status'),
    agency.ActionRecord: ('year', 'person', 'action', 'motive', 'strength', 'event_id'),
    agency.AgencyState: ('motives', 'actions'),
    advancement.Understanding: ('evidence', 'applications', 'transfers', 'integration'),
    advancement.AbilityProgress: ('essence', 'source', 'semantic_key', 'name', 'function', 'domain', 'awakened_year', 'origin_event', 'special', 'aura', 'rank', 'level', 'progress', 'response_model', 'milestone_event', 'understanding'),
    advancement.EssencePath: ('base_essences', 'confluence', 'confluence_name', 'confluence_concepts', 'abilities', 'core_fraction'),
    advancement.AdvancementState: ('paths',),
    mastery_training.ResponseModel: ('samples', 'coefficients', 'trials', 'validated'),
    magic_resources.MagicAspiration: ('drive', 'desired_base_essences', 'desired_abilities', 'reason', 'formed_year', 'preparation', 'search_years', 'completion_goal', 'urgency', 'compromise_tolerance', 'stone_selectiveness', 'risk_tolerance', 'adventurer_aspiration'),
    magic_resources.MagicResource: ('id', 'kind', 'key', 'rarity', 'location', 'owner_kind', 'owner_id', 'created_year', 'origin_event', 'consumed_year', 'consumed_by', 'consumed_event', 'transfers'),
    magic_resources.MagicResourceState: ('resources', 'owner_index', 'aspirations', 'next_id'),
    institutions.Institution: ('id', 'kind', 'name', 'founded_year', 'origin_event', 'branches', 'members'),
    institutions.Branch: ('id', 'institution', 'settlement', 'founded_year', 'origin_event', 'authority', 'records', 'notices', 'trainees'),
    institutions.MagicUserRecord: ('id', 'person', 'branch', 'year', 'essence_ids', 'confluence_id', 'confluence_name', 'abilities', 'ability_names', 'disclosure', 'source_event'),
    institutions.AdventureNotice: ('id', 'branch', 'year', 'kind', 'location', 'cause_event', 'status', 'assigned_to', 'resolved_event', 'required_rank'),
    institutions.SocietyApplication: ('id', 'society', 'person', 'branch', 'applied_year', 'eligibility_verified', 'stage', 'days_completed', 'physical_score', 'magical_score', 'judgment_score', 'passed', 'origin_event', 'resolved_event'),
    institutions.InstitutionState: ('institutions', 'branches', 'magic_records', 'notices', 'applications', 'next_institution', 'next_branch', 'next_record', 'next_notice', 'next_application'),
    metaphysics.SoulState: ('person', 'origin_world', 'outworlder', 'body_generation', 'death_count', 'resurrection_count', 'ontology', 'authorities', 'marks', 'cosmic_links', 'transformations'),
    metaphysics.ResurrectionToken: ('id', 'person', 'patron_kind', 'patron_id', 'granted_year', 'grant_event', 'consumed_year', 'consumed_event'),
    metaphysics.MetaphysicalState: ('souls', 'resurrection_tokens', 'next_token'),
    divinity.God: ('id', 'name', 'domains', 'ontology', 'transcendent', 'manifestations', 'relationships'),
    divinity.GreatAstralBeing: ('id', 'name', 'authorities', 'ontology', 'transcendent', 'interventions', 'relationships'),
    divinity.Church: ('id', 'god', 'settlement', 'founded_year', 'origin_event', 'clergy', 'followers', 'authority', 'wealth', 'doctrine_claims'),
    divinity.DivineState: ('gods', 'great_astral_beings', 'churches', 'next_church'),
    materials.MaterialLot: ('id', 'kind', 'quantity', 'quality', 'settlement', 'producer', 'created_year', 'origin_event', 'owner_kind', 'owner_id', 'magical_properties', 'consumed', 'transfers', 'material_rank'),
    materials.CraftedItem: ('id', 'kind', 'quality', 'rarity', 'settlement', 'craftsperson', 'created_year', 'origin_event', 'materials', 'magical_properties', 'owner_kind', 'owner_id', 'item_rank', 'magical'),
    materials.MaterialEconomy: ('lots', 'items', 'lot_index', 'active_lot_index', 'next_lot', 'next_item'),
    ambient_magic.AmbientField: ('level', 'peak', 'critical_years', 'quintessence', 'surges'),
    ambient_magic.AmbientMagicState: ('fields',),
    warfare.Conflict: ('id', 'attacker', 'defender', 'started_year', 'cause', 'cause_event', 'status', 'war_score', 'battles', 'attacker_losses', 'defender_losses', 'ended_year', 'origin_event', 'peace_event'),
    warfare.WarfareState: ('conflicts', 'tensions', 'next_conflict'),
    society_accountability.Inquiry: ('id', 'branch', 'opened_year', 'trigger_kind', 'trigger_event', 'severity', 'status', 'findings', 'closed_year', 'origin_event', 'resolved_event'),
    society_accountability.SocietyAccountabilityState: ('inquiries', 'next_inquiry'),
    currency.RankedCurrencyState: ('wallets', 'minted', 'treasuries', 'consumed'),
    threat_ecology.MagicalThreat: ('id', 'kind', 'rank', 'location', 'created_year', 'ambient', 'status', 'origin_event', 'form', 'environment_tags'),
    threat_ecology.ThreatEcologyState: ('threats', 'next_id', 'resolutions'),
}

ROOT_TYPES = {
    "world": core.World,
    "world.genealogy": genealogy.Genealogy,
    "world.social": social.SocialGraph,
    "world.economy": economy.Economy,
    "world.knowledge": knowledge.KnowledgeState,
    "world.culture": culture.CulturalState,
    "world.lineage": lineage.LineageState,
    "world.communities": communities.CommunityState,
    "world.transmission": transmission.TransmissionState,
    "world.skills": skills.SkillState,
    "world.infrastructure": infrastructure.InfrastructureState,
    "world.agency": agency.AgencyState,
    "world.advancement": advancement.AdvancementState,
    "world.magic_resources": magic_resources.MagicResourceState,
    "world.institutions": institutions.InstitutionState,
    "world.metaphysics": metaphysics.MetaphysicalState,
    "world.divinity": divinity.DivineState,
    "world.materials": materials.MaterialEconomy,
    "world.ambient_magic": ambient_magic.AmbientMagicState,
    "world.warfare": warfare.WarfareState,
    "world.society_accountability": society_accountability.SocietyAccountabilityState,
    "world.currency": currency.RankedCurrencyState,
    "world.threat_ecology": threat_ecology.ThreatEcologyState,
}

# Every root field is classified explicitly; no default-value omission.
ROOT_FIELDS = {
    'world': {'seed': 'int', 'year': 'int', 'cells': 'dict', 'people': 'dict', 'households': 'dict', 'settlements': 'dict', 'local': 'dict', 'trade_routes': 'dict', 'events': 'events', 'event_ids': 'set', 'genealogy': 'state', 'social': 'state', 'economy': 'state', 'knowledge': 'state', 'culture': 'state', 'lineage': 'state', 'communities': 'state', 'transmission': 'state', 'skills': 'state', 'infrastructure': 'state', 'agency': 'state', 'advancement': 'state', 'magic_resources': 'state', 'institutions': 'state', 'metaphysics': 'state', 'divinity': 'state', 'materials': 'state', 'ambient_magic': 'state', 'warfare': 'state', 'society_accountability': 'state', 'currency': 'state', 'threat_ecology': 'state', 'next_person': 'int', 'next_household': 'int', 'next_settlement': 'int', 'next_event': 'int'},
    'world.genealogy': {'parents': 'dict', 'children': 'dict'},
    'world.social': {'edges': 'dict', 'partnerships': 'dict', 'adjacency': 'dict'},
    'world.economy': {'property': 'dict', 'next_property': 'int'},
    'world.knowledge': {'claims': 'dict', 'beliefs': 'dict', 'claim_index': 'dict', 'next_claim': 'int'},
    'world.culture': {'practices': 'dict', 'institutions': 'dict', 'laws': 'dict', 'adoption': 'dict', 'next_practice': 'int', 'next_institution': 'int', 'next_law': 'int'},
    'world.lineage': {'nodes': 'dict', 'children': 'dict'},
    'world.communities': {'communities': 'dict', 'memberships': 'dict', 'next_community': 'int'},
    'world.transmission': {'records': 'dict', 'next_id': 'int'},
    'world.skills': {'skills': 'dict'},
    'world.infrastructure': {'assets': 'dict', 'next_id': 'int'},
    'world.agency': {'motives': 'dict', 'actions': 'list'},
    'world.advancement': {'paths': 'dict'},
    'world.magic_resources': {'resources': 'dict', 'owner_index': 'dict', 'aspirations': 'dict', 'next_id': 'int'},
    'world.institutions': {'institutions': 'dict', 'branches': 'dict', 'magic_records': 'dict', 'notices': 'dict', 'applications': 'dict', 'next_institution': 'int', 'next_branch': 'int', 'next_record': 'int', 'next_notice': 'int', 'next_application': 'int'},
    'world.metaphysics': {'souls': 'dict', 'resurrection_tokens': 'dict', 'next_token': 'int'},
    'world.divinity': {'gods': 'dict', 'great_astral_beings': 'dict', 'churches': 'dict', 'next_church': 'int'},
    'world.materials': {'lots': 'dict', 'items': 'dict', 'lot_index': 'dict', 'active_lot_index': 'dict', 'next_lot': 'int', 'next_item': 'int'},
    'world.ambient_magic': {'fields': 'dict'},
    'world.warfare': {'conflicts': 'dict', 'tensions': 'dict', 'next_conflict': 'int'},
    'world.society_accountability': {'inquiries': 'dict', 'next_inquiry': 'int'},
    'world.currency': {'wallets': 'dict', 'minted': 'dict', 'treasuries': 'dict', 'consumed': 'dict'},
    'world.threat_ecology': {'threats': 'dict', 'next_id': 'int', 'resolutions': 'dict'},
}
