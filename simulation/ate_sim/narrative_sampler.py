from __future__ import annotations
import hashlib

def _pick(seq,key):
 if not seq:return None
 h=int(hashlib.blake2b(key.encode(),digest_size=8).hexdigest(),16);return sorted(seq,key=lambda x:getattr(x,'id',0))[h%len(seq)]
def _person_events(world,pid):return [e for e in world.events if any(a.kind=='person' and a.id==pid for a in e.actors)]
def _render_person(world,p):
 path=world.advancement.path(p.id);events=_person_events(world,p.id);kinds=[e.kind for e in events]
 bits=[f'Person {p.id}, a {p.species} born in year {p.born}, lived in settlement {p.settlement}.']
 if path:
  bits.append(f'Their essence path reached {len(path.base_essences)} base essences, {len(path.abilities)} awakened abilities, and rank {world.advancement.rank(p.id)}.')
 apps=[a for a in world.institutions.applications.values() if a.person==p.id]
 if apps:
  passed=sum(1 for a in apps if a.passed);failed=sum(1 for a in apps if a.passed is False);bits.append(f'They made {len(apps)} Society application(s): {passed} passed and {failed} failed.')
 battles=sum(1 for e in events if e.kind=='battle');contracts=sum(1 for e in events if e.kind=='adventure_notice_resolved')
 if battles or contracts:bits.append(f'The surviving record links them to {battles} battle event(s) and {contracts} resolved Adventure Society contract(s).')
 if not p.alive:
  death=next((e for e in reversed(events) if e.kind=='death'),None)
  if death:bits.append(f'They died in year {death.year}; the recorded cause was {death.data.get("cause","unknown")}.')
 return ' '.join(bits)
def _render_item(world,item):
 lots=[world.materials.lots[x] for x in item.materials if x in world.materials.lots];parts=[f'Item {item.id} was made in year {item.created_year} in settlement {item.settlement} by person {item.craftsperson}.']
 if lots:
  l=lots[0];parts.append(f'Its recorded material lot {l.id} was produced by person {l.producer} in year {l.created_year}, with quality {l.quality:.2f}.')
 if item.magical:parts.append(f'It is recorded as a rank-{item.item_rank} magical {item.kind}, carrying {", ".join(item.magical_properties) if item.magical_properties else "unnamed magical properties"}.')
 else:parts.append(f'It is recorded as a nonmagical {item.kind} of {item.rarity} rarity.')
 return ' '.join(parts)
def _render_conflict(c):
 end='still active' if c.status=='war' else f'ended in year {c.ended_year}'
 return f'Conflict {c.id} began in year {c.started_year} when settlement {c.attacker} attacked settlement {c.defender} over {c.cause.replace("_"," ")}. It produced {c.battles} battle event(s), with {c.attacker_losses} recorded attacker deaths and {c.defender_losses} defender deaths, and {end}.'
def sample_history(world,count=3):
 out=[];people=[p for p in world.people.values() if world.advancement.path(p.id) is not None or any(a.person==p.id for a in world.institutions.applications.values())]
 p=_pick(people,f'{world.seed}:{world.year}:person')
 if p:out.append({'kind':'life','subject':p.id,'text':_render_person(world,p)})
 items=list(world.materials.items.values());item=_pick(items,f'{world.seed}:{world.year}:item')
 if item:out.append({'kind':'artifact','subject':item.id,'text':_render_item(world,item)})
 conflicts=list(world.warfare.conflicts.values());c=_pick(conflicts,f'{world.seed}:{world.year}:war')
 if c:out.append({'kind':'war','subject':c.id,'text':_render_conflict(c)})
 return out[:count]
