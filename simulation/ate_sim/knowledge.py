from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class KnowledgeClaim:
    id:int; subject:str; proposition:str; truth:bool|None; origin_event:int|None

@dataclass
class KnowledgeState:
    claims:dict[int,KnowledgeClaim]=field(default_factory=dict); beliefs:dict[tuple[int,int],float]=field(default_factory=dict); claim_index:dict[tuple[str,str],int]=field(default_factory=dict); next_claim:int=1
    def claim(self,subject,proposition,truth=None,origin_event=None):
        key=(subject,proposition)
        if key in self.claim_index:return self.claim_index[key]
        i=self.next_claim; self.next_claim+=1; self.claims[i]=KnowledgeClaim(i,subject,proposition,truth,origin_event); self.claim_index[key]=i; return i
    def teach(self,teacher,student,claim,reliability=.8):
        source=self.beliefs.get((teacher,claim),.5); self.beliefs[(student,claim)]=max(0.,min(1.,source*reliability))
