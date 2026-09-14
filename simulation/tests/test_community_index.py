from copy import deepcopy
import pickle
from simulation.ate_sim.communities import CommunityState

def test_membership_index_preserves_order_strength_inheritance_and_checkpoint():
    state = CommunityState()
    for pid,cid,value in ((3,9,.8),(2,5,.4),(3,2,.6),(2,9,.9)):
        state.join(pid,cid,value)
    assert list(state.memberships_for(3)) == [9,2]
    state.join(3,9,.7)
    state.join(3,6,.005)
    state.join(3,4,.5)
    assert list(state.memberships_for(3)) == [9,2,4]
    state.memberships[(3,9)] = .2  # Strength updates are read from authoritative data.
    for pid in (2,3,8):
        expected = {cid:v for (person,cid),v in state.memberships.items() if person==pid and v>=.01}
        assert state.memberships_for(pid) == expected
    inherited = state.inherit(8,(3,2))
    assert list(inherited) == [9,2,4,5]
    for copy in (deepcopy(state),pickle.loads(pickle.dumps(state))):
        assert copy.memberships_for(8) == inherited
        del copy._membership_index
        assert copy.memberships_for(8) == inherited

def test_person_lookup_never_rescans_other_memberships():
    state = CommunityState()
    for pid in range(10000):
        state.join(pid,1,.8)
    state.memberships_for(1)
    class NoIteration(dict):
        def __iter__(self): raise AssertionError("membership archive scan")
        def items(self): raise AssertionError("membership archive scan")
    state.memberships = NoIteration(state.memberships)
    for pid in range(100):
        assert state.memberships_for(pid) == {1:.8}
    state.join(10001,2,.5)
    assert state.memberships_for(10001) == {2:.5}
