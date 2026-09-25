import pytest
from ate_sim.core import RNG
from ate_sim.mastery_training import solve,features,response,trial
from ate_sim.magic_progression import practice_ability
from ate_sim.semantic_dictionary import ESSENCES
from test_magic_understanding import configured_world


def test_response_model_predicts_unseen_inputs_without_reading_true_coefficients():
    w,p,path=configured_world();a=path.abilities[0]
    inputs=[features(x,y,4) for x,y in ((.1,.2),(.4,.1),(.9,.6),(.3,.8),(.8,.4))]
    coefficients=solve(inputs,[response(a,x) for x in inputs])
    unseen=features(.62,.73,4)
    assert sum(c*x for c,x in zip(coefficients,unseen))==pytest.approx(response(a,unseen))


def test_every_semantic_function_has_a_measured_mastery_route():
    functions={f for e in ESSENCES.values() for f in e.get('suggested_functions',[])}
    for fn in sorted(functions):
        w,p,path=configured_world();a=path.abilities[0];a.function=fn;p.curiosity=1;p.health=1
        for year in range(150):
            w.year=year
            trial(w,p,a,RNG(83).stream('trial',year,p.id))
            practice_ability(w,p,0,100,100,context='deliberate control training')
            if a.rank==5:break
        assert a.rank==5,fn
        e=next(e for e in w.events if e.kind=='essence_revelation_integrated')
        assert len(e.data['transfer_proofs'])==2
        trials=[e for e in w.events if e.kind=='ability_control_trial' and e.data['held_out']]
        assert trials and all(e.data['prediction_error']<1e-7 for e in trials)


def test_model_is_bounded_and_preserved_in_checkpoint():
    from ate_sim.checkpoint import dumps,loads
    w,p,path=configured_world();a=path.abilities[0]
    for year in range(30):trial(w,p,a,RNG(5).stream('trial',year,p.id))
    assert len(a.response_model.samples)<=5
    other=loads(dumps(w))
    assert other.digest()==w.digest()
    assert other.advancement.path(p.id).abilities[0].response_model==a.response_model
