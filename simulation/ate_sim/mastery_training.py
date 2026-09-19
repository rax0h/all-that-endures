"""Ability-specific response modeling and controlled application.

These are simulated calibration problems, not off-screen exploits or invented
philosophical prose. Bounded response models compress observations and predict
held-out results; successful models also improve practical control precision.
"""
from dataclasses import dataclass,field
from functools import lru_cache
from heapq import nsmallest
import hashlib
from .core_types import layer_ref
from .magic_progression import record_application

@dataclass
class ResponseModel:
    samples:list=field(default_factory=list)
    coefficients:list=field(default_factory=list)
    trials:int=0
    validated:int=0


def features(x,y,rank):
    return [1.,x,y] if rank==3 else [1.,x,y,x*y,x*x]


def solve(rows,values):
    """Small pivoted system, at most five parameters. No external dependency."""
    n=len(rows)
    if any(len(row)!=n for row in rows):return []
    a=[list(row)+[value] for row,value in zip(rows,values)]
    for j in range(n):
        k=max(range(j,n),key=lambda i:abs(a[i][j]))
        if abs(a[k][j])<1e-9:return []
        a[j],a[k]=a[k],a[j];scale=a[j][j]
        a[j]=[v/scale for v in a[j]]
        for i in range(n):
            if i!=j:
                factor=a[i][j];a[i]=[v-factor*w for v,w in zip(a[i],a[j])]
    return [row[-1] for row in a]


@lru_cache(maxsize=None)
def _response_coefficients(semantic_key,function,domain):
    # Ability identity/function/domain never change after awakening. Cache this
    # immutable response law instead of hashing it for every mastery trial.
    key=hashlib.blake2b((semantic_key+'|'+function+'|'+domain).encode(),digest_size=16).digest()
    return tuple(.15+key[i]/255 for i in range(5))

def response(ability,inputs):
    # The response law belongs to this ability/essence/function/domain. It is
    # independent of the learner's estimated model and cannot read that model.
    coeffs=_response_coefficients(ability.semantic_key,ability.function,ability.domain)
    return sum(coeffs[i]*x for i,x in enumerate(inputs))


def trial(world,person,ability,rng):
    if ability.rank not in (3,4) or ability.understanding.ready(ability.rank):return False
    model=ability.response_model
    # Training is bounded by real annual time; unsuccessful measurements cost
    # that attempt, too. Pressure/health affect whether useful work is possible.
    if rng.random()>.35+.35*person.curiosity+.20*person.health:return False
    rank=ability.rank;n=3 if rank==3 else 5
    local=world.local[person.settlement]
    x=.1+.8*rng.random();y=.1+.6*rng.random()+.2*local.rain
    inputs=features(x,y,rank);measured=response(ability,inputs)
    predicted=sum(c*v for c,v in zip(model.coefficients,inputs)) if model.coefficients else None
    error=abs(measured-predicted) if predicted is not None else None
    held_out=predicted is not None
    success=not held_out or error<1e-7
    model.trials+=1
    Layer,Ref=layer_ref()
    causes=tuple(s['event'] for s in model.samples) if held_out else ()
    origin=ability.milestone_event or ability.origin_event
    if origin is not None:causes=(*causes,origin)
    e=world.emit('ability_control_trial',Layer.REALITY,(Ref('person',person.id),),Ref('settlement',person.settlement),causes,
        ability=ability.semantic_key,essence=ability.essence,function=ability.function,domain=ability.domain,
        ability_rank=rank,ability_level=ability.level,inputs=inputs,measured_response=measured,
        prediction=predicted,prediction_error=error,model_parameters=list(model.coefficients),
        held_out=held_out,success=success,challenge_complexity=rank if held_out else rank-1,
        output_metric='normalized control accuracy',effort='one supervised or deliberate practical session',
        model='ATE response-law learning approximation')
    if not held_out:
        model.samples.append({'event':e.id,'inputs':inputs,'response':measured})
        if len(model.samples)>=n:
            model.samples=model.samples[-n:]
            model.coefficients=solve([s['inputs'] for s in model.samples],[s['response'] for s in model.samples])
    if success:
        if held_out:model.validated=min(2,model.validated+1)
        record_application(world,person,ability,e,constraint=f'control:{model.trials}',difficulty=rank if held_out else rank-1,outcome=1.)
    return success


def mastery_training_step(world,person,path,rng):
    candidates=[a for a in path.abilities if a.rank in (3,4) and not a.understanding.ready(a.rank)]
    # Rotate across every function, including rare semantic functions; no
    # arbitrary occupation/function whitelist can make an ability impossible.
    candidates=nsmallest(2,candidates,key=lambda a:(a.response_model.trials,a.semantic_key))
    for ability in candidates:trial(world,person,ability,rng)
