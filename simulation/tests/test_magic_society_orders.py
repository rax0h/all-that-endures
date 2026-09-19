from ate_sim import generate_world
from ate_sim.core import Layer,Ref
from ate_sim.magic_resources import _aspiration,_magic_society_network_stock,_network_order_resources
from ate_sim.semantic_dictionary import ESSENCES


class PickRemote:
    def random(self):return .99


def test_magic_society_remote_order_does_not_require_local_stock_exhaustion():
    world=generate_world(843003);magic=world.institutions.institution_by_kind('magic_society')
    buyer=next(p for p in world.current_people() if p.age>=18 and (world.advancement.path(p.id) is None or len(world.advancement.path(p.id).base_essences)<3))
    buyer.wealth=1000.;asp=_aspiration(world,buyer)
    base=0 if world.advancement.path(buyer.id) is None else len(world.advancement.path(buyer.id).base_essences)
    asp.desired_base_essences=base+1;asp.desired_abilities=0
    local=buyer.settlement;remote=next(sid for sid in world.settlements if sid!=local)
    # Choose keys the buyer does not already possess.
    path=world.advancement.path(buyer.id);owned=set() if path is None else set(path.base_essences)
    keys=[k for k in ESSENCES if k not in owned][:2]
    made=[]
    for sid,key in ((local,keys[0]),(remote,keys[1])):
        e=world.emit('test_network_stock',Layer.REALITY,location=Ref('settlement',sid),key=key)
        made.append(world.magic_resources.create('essence',key,ESSENCES[key]['rarity'],world.year,sid,'settlement',sid,e.id))
    stock=_magic_society_network_stock(world,magic)
    ordered=_network_order_resources(world,buyer,asp,stock,magic,PickRemote())
    assert ordered>=1
    event=next(e for e in reversed(world.events) if e.kind=='magic_resource_ordered')
    assert event.data['remote_order'] and event.data['delivery_days']==14
    assert event.data['source_settlement']==remote and event.data['destination_settlement']==local
    # Local stock still existed when the remote order was selected.
    assert world.magic_resources.resources[made[0].id].owner_kind=='settlement'
