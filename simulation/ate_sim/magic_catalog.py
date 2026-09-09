# Full Veilbound 2.0 Semantic Dictionary v0.1 catalog.
# Source of truth: Veilbound_Semantic_Dictionary_v0.1.json
import json

DOCUMENT='Veilbound 2.0 Semantic Dictionary v0.1'
STATUS='Working design layer grounded in the recovered Veilbound catalog.'
SYSTEM_RULES={'base_essences':3,'confluence_essences':1,'skills_per_essence':5,'innate_skills_total':4,'stone_awakened_skills_total':16,'total_skills':20}

# Compact embedded catalog preserves every essence's authored semantic data while keeping
# runtime lookup simple. Generated from the project semantic dictionary; do not hand-prune.
_CATALOG_JSON=r'''PLACEHOLDER'''
ESSENCES={e['id']:e for e in json.loads(_CATALOG_JSON)}
ESSENCE_IDS=tuple(ESSENCES)
AWAKENING_STONES={
'feast':{'name':'Feast','rarity':'Common','core':'consumption, nourishment, preparation, sharing','adjacent':'cooking, appetite, digestion, hospitality, resource conversion','pressure':'Prefer nourishment, consumption, preparation, recovery, conversion, or communal effects.','guardrail':'Do not make Feast merely a lifesteal stone.'},
'eyes':{'name':'Eyes','rarity':'Common','core':'perception, observation, revelation, perspective','adjacent':'targeting, diagnosis, appraisal, hidden information, foresight','pressure':'Prefer sensory, analytical, targeting, awareness, or information-changing manifestations.','guardrail':'Do not make every Eyes awakening literal eyesight.'},
'mercy':{'name':'Mercy','rarity':'Uncommon','core':'relief, restraint, preservation, compassion','adjacent':'healing, protection, painless endings, rescue, forgiveness','pressure':'Prefer recovery, prevention, protection, de-escalation, or harm-limiting manifestations.','guardrail':'Mercy is not synonymous with green healing magic.'},
'adventure':{'name':'Adventure','rarity':'Uncommon','core':'journey, risk, discovery, adaptability','adjacent':'travel, courage, improvisation, exploration, luck','pressure':'Prefer movement, survival, discovery, versatility, field utility, or risk-reward manifestations.','guardrail':'Do not reduce Adventure to movement speed.'},
'stars':{'name':'Stars','rarity':'Epic','core':'distance, celestial order, guidance, wonder','adjacent':'navigation, constellations, cosmic perspective, radiance, destiny','pressure':'Allow broad-range, guidance, remote, celestial, pattern, or high-concept manifestations.','guardrail':'Epic does not mean same skill with bigger damage.'},
'omens':{'name':'Omens','rarity':'Epic','core':'portents, possibility, warning, consequence','adjacent':'probability, fate, timing, pattern recognition, foreknowledge','pressure':'Allow conditional, predictive, probability-sensitive, delayed, or consequence-based manifestations.','guardrail':'Never grant perfect knowledge or deterministic prophecy for free.'},
'reaper':{'name':'Reaper','rarity':'Legendary','core':'ending, harvest, mortality, transition','adjacent':'death, severance, collection, inevitability, last moments','pressure':'Allow exceptional ending/harvesting/conversion mechanics and interactions with mortality or completion.','guardrail':'Legendary does not mean automatic execution; preserve counterplay and conceptual fit.'}}
STONE_IDS=tuple(AWAKENING_STONES)
