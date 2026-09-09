from .core import *
from .culture import seed_practices
from .species import habitat_suitability
import math
PEOPLES=('human','elf','celestine','leonid','smoulder','draconian','merfolk','runic')
def _local_peoples(rr,cell):
 weighted=[]
 for key in PEOPLES:
  fit=habitat_suitability(key,cell.elevation,cell.moisture,cell.forest);weighted.append((fit*rr.uniform(.72,1.28),key))
 weighted.sort(reverse=True);count=rr.randint(1,4);local=[key for _,key in weighted[:count]]
 if count>1 and rr.random()<.28:local[-1]=rr.choice([key for _,key in weighted[count:] or weighted])
 return tuple(dict.fromkeys(local))
def generate_world(seed:int,width=24,height=18,settlements=5):
 w=World(seed);r=RNG(seed)
 for y in range(height):
  for x in range(width):
   g=r.stream('terrain',0,y*width+x);nx=(x-(width-1)/2)/(width/2);ny=(y-(height-1)/2)/(height/2);continental=max(0,1-(nx*nx+ny*ny));elev=max(0,min(1,.12+.72*continental+g.uniform(-.16,.16)));moisture=max(0,min(1,.55+.25*math.sin(x*.43)+g.uniform(-.2,.2)-.18*elev));fertility=max(0,min(1,.15+.55*moisture+.25*(1-abs(elev-.42))));forest=max(0,min(1,moisture*.9+g.uniform(-.2,.15)));hazard=max(0,min(1,.12+.25*forest+g.uniform(0,.18)));w.cells[(x,y)]=Cell(x,y,elev,moisture,fertility,forest,hazard)
 candidates=sorted(w.cells.values(),key=lambda c:c.fertility-.25*c.hazard,reverse=True);chosen=[]
 for c in candidates:
  if c.elevation>=.2 and all((c.x-o.x)**2+(c.y-o.y)**2>18 for o in chosen):chosen.append(c)
  if len(chosen)>=settlements:break
 for c in chosen:
  sid=w.next_settlement;w.next_settlement+=1;s=Settlement(sid,c.x,c.y,food_stock=130+80*c.fertility,defense=.08+.12*c.hazard,irrigation=.08+.2*c.fertility,prosperity=.2+.3*c.fertility);w.settlements[sid]=s;w.local[sid]=LocalState();rr=r.stream('founders',0,sid);local=_local_peoples(rr,c)
  founded=w.emit('settlement_founded',Layer.REALITY,location=Ref('settlement',sid),fertility=c.fertility,species=tuple(sorted(local)),habitat_fit={key:round(habitat_suitability(key,c.elevation,c.moisture,c.forest),3) for key in local});w.lineage.register('settlement',sid,origin_event=founded.id,origin_year=0);community=w.communities.create('founder_network',0,sid,founded.id);w.lineage.register('community',community.id,origin_event=founded.id,origin_year=0)
  irrigation=w.infrastructure.create('irrigation',(sid,),max(.15,s.irrigation),40+120*s.irrigation,0,founded.id);w.lineage.register('infrastructure',irrigation.id,(('settlement',sid),),founded.id,0)
  for _ in range(rr.randint(5,9)):
   hid=w.next_household;w.next_household+=1;h=Household(hid,sid,wealth=rr.uniform(15,90),food=rr.uniform(8,20),preparedness=rr.uniform(.05,.3),lineage=f'Line-{sid}-{hid}');w.households[hid]=h;s.households.append(hid);w.lineage.register('household',hid,(('community',community.id),),founded.id,0);sp0=rr.choice(local);prop=w.economy.create('homestead',sid,'household',hid,h.wealth*.7,0,founded.id);w.lineage.register('property',prop.id,(('household',hid),),founded.id,0)
   for _ in range(rr.randint(2,6)):
    pid=w.next_person;w.next_person+=1;age=rr.randint(0,45);sp=sp0 if rr.random()<.88 else rr.choice(local);p=Person(pid,-age,sid,hid,age=age,wealth=h.wealth/max(1,len(h.members)+1),temperament=rr.random(),attachment=rr.random(),curiosity=rr.random(),inhibition=rr.random(),species=sp);w.people[pid]=p;h.members.append(pid);w.communities.join(pid,community.id,1.0);w.lineage.register('person',pid,(('household',hid),),founded.id,-age)
    if age>=18:
     w.skills.practice(pid,'agriculture',rr.uniform(.8,3.2),founded.id);w.skills.practice(pid,'construction',rr.uniform(.2,1.4),founded.id)
     if rr.random()<.18:
      w.advancement.awaken(pid);p.rank=1;w.emit('essence_user_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',sid),(founded.id,))
  for h in s.households:
   hm=w.households[h].members
   for a,b in zip(hm,hm[1:]):w.social.record(a,b,founded.id,trust=.15,attachment=.15)
 seed_practices(w,w.culture)
 for pid,practice in w.culture.practices.items():w.lineage.register('practice',pid,origin_year=practice.origin_year)
 return w
