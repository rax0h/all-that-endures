from __future__ import annotations
from dataclasses import dataclass,field

@dataclass
class SkillHistory:
    person:int
    domain:str
    level:float=.05
    practice:float=0.
    teachers:list[int]=field(default_factory=list)
    provenance:list[int]=field(default_factory=list)

@dataclass
class SkillState:
    skills:dict[tuple[int,str],SkillHistory]=field(default_factory=dict)

    def get(self,person:int,domain:str)->SkillHistory:
        key=(person,domain)
        if key not in self.skills:self.skills[key]=SkillHistory(person,domain)
        return self.skills[key]

    def practice(self,person:int,domain:str,amount:float,event_id:int|None=None):
        s=self.get(person,domain);amount=max(0.,amount);s.practice+=amount;s.level=min(1.,s.level+amount*(1-s.level)*.035)
        if event_id is not None:s.provenance.append(event_id)
        return s.level

    def teach(self,teacher:int,student:int,domain:str,reliability:float,event_id:int|None=None):
        src=self.get(teacher,domain);dst=self.get(student,domain);gain=max(0.,min(1.,reliability))*src.level*.045*(1-dst.level);dst.level=min(1.,dst.level+gain)
        if teacher not in dst.teachers:dst.teachers.append(teacher)
        if event_id is not None:dst.provenance.append(event_id)
        return dst.level
