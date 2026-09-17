from ate_sim.magic_access import _price, MAGIC_WORLD_ADOPTION_FLOOR, MAGIC_WORLD_ADOPTION_EXPECTED

class R:
 def __init__(self,kind,rarity):self.kind=kind;self.rarity=rarity

def test_common_and_uncommon_essences_are_ordinary_affordable_goods():
 assert _price(R('essence','Common'))==1.
 assert _price(R('essence','Uncommon'))==2.
 assert _price(R('essence','Rare'))>_price(R('essence','Uncommon'))
 assert _price(R('essence','Legendary'))>=20*_price(R('essence','Uncommon'))

def test_mature_world_adoption_is_a_floor_not_a_ceiling():
 assert MAGIC_WORLD_ADOPTION_FLOOR==.75
 assert MAGIC_WORLD_ADOPTION_EXPECTED>=MAGIC_WORLD_ADOPTION_FLOOR
 assert MAGIC_WORLD_ADOPTION_EXPECTED<1.
