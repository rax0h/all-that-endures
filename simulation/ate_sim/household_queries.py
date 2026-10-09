"""Current-person household selection without traversing cold member history.

The canonical household sequence remains authoritative for order, duplicates
and positional membership. Only the P4 checked pager supports indexed
candidate occurrence lookup; eager/legacy collections retain native behavior.
"""


def living_household_members(world, household_id):
    members = world.households[household_id].members
    if getattr(members, "_ate_household_page_sequence", False):
        # The current people index is a current-state query. Do not enumerate
        # all historical Person payloads merely to reject those who died.
        live = {person.id: person for person in world.current_people()}
        return [live[member_id] for member_id in members.matching_member_ids(live)]
    return [world.people[member_id] for member_id in members
            if world.people[member_id].alive]
