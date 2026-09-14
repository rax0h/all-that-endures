import pickle
from types import SimpleNamespace
from simulation.ate_sim.social import SocialGraph


def test_living_partnerships_match_archive_and_follow_life_changes():
    graph=SocialGraph()
    people=[SimpleNamespace(id=i,alive=i<5) for i in range(20)]
    for a,b in ((1,2),(3,2),(2,6),(6,8),(0,1)):
        graph.partner(a,b,10*a+b)
    def verify(g):
        living={p.id for p in people if p.alive}
        assert g.living_partnerships(people)=={key:e for key,e in g.partnerships.items() if all(pid in living for pid in key)}
    verify(graph)
    people[2].alive=False
    verify(graph)
    people[6].alive=True
    verify(graph)
    people[2].alive=True
    graph.partner(2,4,123)
    verify(graph)
    graph.partnerships[(1,4)]=124
    verify(graph)
    verify(pickle.loads(pickle.dumps(graph)))
    del graph._partnership_index
    verify(graph)


def test_living_partnership_query_does_not_iterate_archive():
    graph=SocialGraph()
    for n in range(10000):graph.partner(n,n+1,n)
    people=[SimpleNamespace(id=1,alive=True),SimpleNamespace(id=2,alive=True)]
    assert graph.living_partnerships(people)=={(1,2):1}
    class NoIteration(dict):
        def __iter__(self):raise AssertionError('partnership archive scan')
        def items(self):raise AssertionError('partnership archive scan')
    graph.partnerships=NoIteration(graph.partnerships)
    assert graph.living_partnerships(people)=={(1,2):1}
    graph.partner(1,2,88)
    assert graph.living_partnerships(people)=={(1,2):88}
