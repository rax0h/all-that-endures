from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref

@dataclass
class Inquiry:
 id:int; branch:int; opened_year:int; trigger_kind:str; trigger_event:int; severity:float; status:str='open'; findings:tuple[str,...]=(); closed_year:int|None=None; origin_event:int|None=None; resolved_event:int|None=None

@dataclass
class SocietyAccountabilityState:
 inquiries:dict[int,Inquiry]=field(default_factory=dict); next_inquiry:int=1

def _open(world,branch,trigger,severity):
 state=world.society_accountability
 if any(q.status=='open' and q.branch==branch.id for q in state.inquiries.values()):return
 Layer,Ref=layer_ref();e=world.emit('society_inquiry_opened',Layer.SOCIETY,location=Ref('settlement',branch.settlement),causes=(trigger.id,),branch=branch.id,trigger=trigger.kind,severity=round(severity,3));qid=state.next_inquiry;state.next_inquiry+=1;state.inquiries[qid]=Inquiry(qid,branch.id,world.year,trigger.kind,trigger.id,severity,origin_event=e.id)

def _close(world,q):
 branch=world.institutions.branches[q.branch];recent=[e for e in world.events_between(q.opened_year-4,world.year) if e.location and e.location.kind=='settlement' and e.location.id==branch.settlement]
 deaths=sum(1 for e in recent if e.kind=='death' and e.data.get('cause') in ('war','monster','dangerous_magic'));failed=sum(1 for a in world.institutions.applications.values() if a.branch==branch.id and a.passed is False);findings=[]
 if deaths>=4:findings.append('inadequate_public_safety')
 if failed>=5:findings.append('training_or_selection_failure')
 if branch.authority<.4:findings.append('weak_branch_governance')
 if q.trigger_kind in ('dangerous_magic','missing_person'):findings.append('incident_response_failure')
 if not findings:findings.append('no_systemic_breach_found')
 q.findings=tuple(findings);q.status='closed';q.closed_year=world.year
 if 'no_systemic_breach_found' not in findings:branch.authority=max(.15,branch.authority-.04*len(findings))
 else:branch.authority=min(.95,branch.authority+.01)
 Layer,Ref=layer_ref();causes=(() if q.origin_event is None else (q.origin_event,));e=world.emit('society_inquiry_closed',Layer.SOCIETY,location=Ref('settlement',branch.settlement),causes=causes,inquiry=q.id,findings=q.findings,authority=round(branch.authority,3));q.resolved_event=e.id

def accountability_step(world,rng):
 state=world.society_accountability
 current=[e for e in world.events_between(world.year,world.year) if e.kind in ('monster_surge','dangerous_magic','missing_person','battle','adventure_notice_failed')]
 for e in current:
  if e.location is None or e.location.kind!='settlement':continue
  branch=world.institutions.branch_for('adventure_society',e.location.id)
  if branch is None:continue
  severity=.45 if e.kind in ('dangerous_magic','missing_person') else (.65 if e.kind=='battle' else .3)
  rr=rng.stream('society_inquiry',world.year,e.id)
  if severity>=.6 or rr.random()<severity*.12:_open(world,branch,e,severity)
 for q in sorted(state.inquiries.values(),key=lambda x:x.id):
  if q.status=='open' and world.year-q.opened_year>=2:_close(world,q)
