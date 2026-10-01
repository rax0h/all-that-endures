from __future__ import annotations

from dataclasses import dataclass, field
import math


@dataclass
class Parcel:
    id: int
    settlement: int
    kind: str
    center_x_m: float
    center_y_m: float
    width_m: float
    depth_m: float
    facing_degrees: float
    owner_kind: str | None
    owner_id: int | None
    created_year: int
    origin_event: int | None
    active: bool = True


@dataclass
class Structure:
    id: int
    settlement: int
    parcel: int
    kind: str
    center_x_m: float
    center_y_m: float
    width_m: float
    depth_m: float
    facing_degrees: float
    built_year: int
    owner_kind: str | None
    owner_id: int | None
    occupied_by_household: int | None
    origin_event: int | None
    property_id: int | None = None
    condition: float = 1.0
    active: bool = True
    provenance: list[int] = field(default_factory=list)


@dataclass
class Street:
    id: int
    settlement: int
    key: str
    kind: str
    points_m: tuple[tuple[float, float], ...]
    width_m: float
    surface_family: str
    built_year: int
    origin_event: int | None
    condition: float = 1.0
    active: bool = True


@dataclass
class SettlementSpatialState:
    parcels: dict[int, Parcel] = field(default_factory=dict)
    structures: dict[int, Structure] = field(default_factory=dict)
    streets: dict[int, Street] = field(default_factory=dict)
    next_parcel: int = 1
    next_structure: int = 1
    next_street: int = 1
    household_residence: dict[int, int] = field(default_factory=dict)
    property_structure: dict[int, int] = field(default_factory=dict)
    institution_structure: dict[str, int] = field(default_factory=dict)
    workshop_structure: dict[int, int] = field(default_factory=dict)
    market_structure: dict[int, int] = field(default_factory=dict)
    lot_cursor: dict[int, int] = field(default_factory=dict)
    settlement_orientation: dict[int, float] = field(default_factory=dict)
    street_ids: dict[tuple[int, str], int] = field(default_factory=dict)

    def create_parcel(
        self,
        settlement,
        kind,
        center_x_m,
        center_y_m,
        width_m,
        depth_m,
        facing_degrees,
        owner_kind,
        owner_id,
        created_year,
        origin_event=None,
    ):
        pid = self.next_parcel
        self.next_parcel += 1
        parcel = Parcel(
            pid,
            settlement,
            kind,
            center_x_m,
            center_y_m,
            width_m,
            depth_m,
            facing_degrees,
            owner_kind,
            owner_id,
            created_year,
            origin_event,
        )
        self.parcels[pid] = parcel
        return parcel

    def create_structure(
        self,
        settlement,
        parcel,
        kind,
        center_x_m,
        center_y_m,
        width_m,
        depth_m,
        facing_degrees,
        built_year,
        owner_kind,
        owner_id,
        occupied_by_household,
        origin_event=None,
        property_id=None,
    ):
        sid = self.next_structure
        self.next_structure += 1
        structure = Structure(
            sid,
            settlement,
            parcel,
            kind,
            center_x_m,
            center_y_m,
            width_m,
            depth_m,
            facing_degrees,
            built_year,
            owner_kind,
            owner_id,
            occupied_by_household,
            origin_event,
            property_id,
            provenance=[] if origin_event is None else [origin_event],
        )
        self.structures[sid] = structure
        if property_id is not None:
            self.property_structure[property_id] = sid
        return structure

    def create_street(
        self,
        settlement,
        key,
        kind,
        points_m,
        width_m,
        surface_family,
        built_year,
        origin_event=None,
        condition=1.0,
    ):
        old = self.street_ids.get((settlement, key))
        if old is not None:
            return self.streets[old]
        sid = self.next_street
        self.next_street += 1
        street = Street(
            sid,
            settlement,
            key,
            kind,
            tuple(points_m),
            width_m,
            surface_family,
            built_year,
            origin_event,
            max(0.0, min(1.0, condition)),
        )
        self.streets[sid] = street
        self.street_ids[(settlement, key)] = sid
        return street


# Slots are persistent town lots beside a small road hierarchy. Roads are created
# only when a used slot requires them, so settlement growth physically expands
# the street network rather than revealing a fully built grid at year zero.
def _slot_catalog():
    slots = []

    def add_row(street, axis, fixed, positions, side_offsets, facing):
        for position in positions:
            for side in side_offsets:
                if axis == "x":
                    slots.append((street, position, fixed + side, facing if side > 0 else facing + 180))
                else:
                    slots.append((street, fixed + side, position, facing if side < 0 else facing + 180))

    main_positions = [x for x in range(-132, 133, 22) if abs(x) > 12]
    cross_positions = [y for y in range(-110, 111, 22) if abs(y) > 12]
    lane_positions = [x for x in range(-120, 121, 24) if abs(x) > 20]
    vertical_positions = [y for y in range(-96, 97, 24) if abs(y) > 20]

    add_row("main", "x", 0, main_positions, (-15, 15), 0)
    add_row("cross", "y", 0, cross_positions, (-15, 15), 90)
    add_row("north", "x", 48, lane_positions, (-14, 14), 0)
    add_row("south", "x", -48, lane_positions, (-14, 14), 0)
    add_row("east", "y", 76, vertical_positions, (-14, 14), 90)
    add_row("west", "y", -76, vertical_positions, (-14, 14), 90)
    return tuple(slots)


_LOT_SLOTS = _slot_catalog()


def _rotate(x, y, degrees):
    r = math.radians(degrees)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


def _street_geometry(key):
    if key == "main":
        return ((-170, -5), (-85, 3), (0, 0), (85, -4), (170, 5)), 7.0, "main"
    if key == "cross":
        return ((-3, -130), (2, -65), (0, 0), (5, 65), (2, 130)), 5.5, "cross"
    if key == "north":
        return ((-145, 48), (-70, 51), (0, 48), (75, 45), (145, 49)), 4.2, "lane"
    if key == "south":
        return ((-145, -48), (-70, -45), (0, -48), (75, -51), (145, -47)), 4.2, "lane"
    if key == "east":
        return ((76, -120), (73, -55), (76, 0), (79, 60), (76, 120)), 4.0, "lane"
    return ((-76, -120), (-79, -55), (-76, 0), (-73, 60), (-76, 120)), 4.0, "lane"


def _ensure_orientation(world, sid, rng):
    state = world.settlement_space
    if sid not in state.settlement_orientation:
        rr = rng.stream("settlement_orientation", 0, sid)
        state.settlement_orientation[sid] = rr.uniform(-28.0, 28.0)
    return state.settlement_orientation[sid]


def _surface_for(world, sid):
    s = world.settlements[sid]
    return "compacted_gravel" if s.prosperity >= 0.42 else "packed_earth"


def _ensure_street(world, sid, key, rng, origin_event=None):
    state = world.settlement_space
    old = state.street_ids.get((sid, key))
    if old is not None:
        return state.streets[old]
    angle = _ensure_orientation(world, sid, rng)
    points, width, kind = _street_geometry(key)
    rotated = tuple(_rotate(x, y, angle) for x, y in points)
    return state.create_street(
        sid,
        key,
        kind,
        rotated,
        width,
        _surface_for(world, sid),
        world.year,
        origin_event,
        condition=max(0.25, world.settlements[sid].roads),
    )


def _property_for_household(world, hid, sid):
    candidates = [
        prop
        for prop in world.economy.property.values()
        if prop.settlement == sid
        and prop.owner_kind == "household"
        and prop.owner_id == hid
        and prop.id not in world.settlement_space.property_structure
        and prop.kind in ("homestead", "dwelling")
    ]
    return min(candidates, key=lambda prop: prop.id) if candidates else None


def _origin_event_for_household(world, hid):
    for event in reversed(world.events):
        if event.data.get("household") == hid and event.kind in ("household_formed", "household_split"):
            return event.id
    for event in world.events:
        if event.kind == "settlement_founded" and event.location and event.location.id == world.households[hid].settlement:
            return event.id
    return None


def _next_slot(world, sid, rng):
    state = world.settlement_space
    index = state.lot_cursor.get(sid, 0)
    if index >= len(_LOT_SLOTS):
        # Beyond the authored slot envelope, extend outward in deterministic rings.
        ring_index = index - len(_LOT_SLOTS)
        ring = 1 + ring_index // 24
        offset = ring_index % 24
        angle = 2 * math.pi * (offset / 24.0)
        radius = 175 + ring * 24
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        street_key = "main" if abs(y) < abs(x) else "cross"
        facing = math.degrees(math.atan2(-y, -x))
    else:
        street_key, x, y, facing = _LOT_SLOTS[index]
    state.lot_cursor[sid] = index + 1
    _ensure_street(world, sid, street_key, rng)
    angle = _ensure_orientation(world, sid, rng)
    rx, ry = _rotate(x, y, angle)
    return rx, ry, (facing + angle) % 360.0


def _residence_dimensions(world, hid):
    household = world.households[hid]
    living = sum(1 for pid in household.members if world.people[pid].alive)
    wealth = household.wealth
    width = 7.0 + min(7.0, living * 0.8 + wealth / 45.0)
    depth = 5.8 + min(5.5, living * 0.6 + wealth / 60.0)
    return round(width, 2), round(depth, 2)


def ensure_household_residence(world, rng, hid):
    state = world.settlement_space
    household = world.households[hid]
    if not household.alive:
        old_id = state.household_residence.get(hid)
        if old_id in state.structures:
            state.structures[old_id].occupied_by_household = None
        return None

    existing_id = state.household_residence.get(hid)
    if existing_id is not None:
        existing = state.structures.get(existing_id)
        if existing and existing.active and existing.settlement == household.settlement:
            existing.occupied_by_household = hid
            return existing
        if existing:
            existing.occupied_by_household = None

    sid = household.settlement
    prop = _property_for_household(world, hid, sid)
    origin_event = prop.provenance[0] if prop and prop.provenance else _origin_event_for_household(world, hid)
    x, y, facing = _next_slot(world, sid, rng)
    width, depth = _residence_dimensions(world, hid)
    parcel = state.create_parcel(
        sid,
        "residential",
        x,
        y,
        width + 7.0,
        depth + 10.0,
        facing,
        "household",
        hid,
        world.year,
        origin_event,
    )
    structure = state.create_structure(
        sid,
        parcel.id,
        "dwelling" if prop is not None else "leased_dwelling",
        x,
        y,
        width,
        depth,
        facing,
        world.year,
        "household" if prop is not None else None,
        hid if prop is not None else None,
        hid,
        origin_event,
        None if prop is None else prop.id,
    )
    state.household_residence[hid] = structure.id
    return structure


def _ensure_market(world, rng, sid):
    state = world.settlement_space
    if sid in state.market_structure:
        return
    exchange_count = sum(
        route.exchanges
        for (a, b), route in world.trade_routes.items()
        if sid in (a, b)
    )
    if exchange_count < 4:
        return
    angle = _ensure_orientation(world, sid, rng)
    x, y = _rotate(0, 0, angle)
    parcel = state.create_parcel(
        sid, "public", x, y, 32, 28, angle, None, None, world.year, None
    )
    structure = state.create_structure(
        sid, parcel.id, "market_hall", x, y, 18, 12, angle,
        world.year, None, None, None, None
    )
    state.market_structure[sid] = structure.id
    _ensure_street(world, sid, "main", rng)
    _ensure_street(world, sid, "cross", rng)


def _ensure_institutions(world, rng, sid):
    state = world.settlement_space
    branches = [b for b in world.institutions.branches.values() if b.settlement == sid]
    for branch in sorted(branches, key=lambda b: b.id):
        key = f"branch:{branch.id}"
        if key in state.institution_structure:
            continue
        x, y, facing = _next_slot(world, sid, rng)
        parcel = state.create_parcel(
            sid, "institutional", x, y, 24, 24, facing,
            "institution_branch", branch.id, branch.founded_year, branch.origin_event
        )
        institution = world.institutions.institutions[branch.institution]
        structure = state.create_structure(
            sid, parcel.id, institution.kind + "_hall", x, y, 15, 11, facing,
            branch.founded_year, "institution_branch", branch.id, None,
            branch.origin_event
        )
        state.institution_structure[key] = structure.id

    cultural = [i for i in world.culture.institutions.values() if i.settlement == sid]
    for institution in sorted(cultural, key=lambda i: i.id):
        key = f"culture:{institution.id}"
        if key in state.institution_structure:
            continue
        x, y, facing = _next_slot(world, sid, rng)
        parcel = state.create_parcel(
            sid, "institutional", x, y, 22, 22, facing,
            "culture_institution", institution.id, institution.founded, None
        )
        structure = state.create_structure(
            sid, parcel.id, "guildhall", x, y, 14, 10, facing,
            institution.founded, "culture_institution", institution.id, None, None
        )
        state.institution_structure[key] = structure.id


def _ensure_workshops(world, rng, sid):
    state = world.settlement_space
    crafters = [
        p for p in world.people.values()
        if p.alive and p.settlement == sid and p.occupation == "craftsperson"
    ]
    for person in sorted(crafters, key=lambda p: p.id):
        if person.household in state.workshop_structure:
            continue
        crafted = [
            item for item in world.materials.items.values()
            if item.craftsperson == person.id and item.settlement == sid
        ]
        if not crafted:
            continue
        common = {}
        for item in crafted:
            common[item.kind] = common.get(item.kind, 0) + 1
        craft_kind = max(common, key=lambda key: (common[key], key))
        names = {
            "metalwork": "smithy",
            "textile": "weaving_house",
            "ceramic": "pottery",
            "woodwork": "carpenter_shop",
            "masonry": "mason_yard",
            "provisions": "food_workshop",
        }
        x, y, facing = _next_slot(world, sid, rng)
        parcel = state.create_parcel(
            sid, "workshop", x, y, 22, 20, facing,
            "household", person.household, world.year,
            crafted[0].origin_event,
        )
        structure = state.create_structure(
            sid, parcel.id, names.get(craft_kind, "workshop"),
            x, y, 13, 9, facing, world.year,
            "household", person.household, None,
            crafted[0].origin_event,
        )
        state.workshop_structure[person.household] = structure.id


def seed_settlement_space(world, rng):
    for sid in sorted(world.settlements):
        founded = next(
            (
                event.id
                for event in world.events
                if event.kind == "settlement_founded"
                and event.location is not None
                and event.location.id == sid
            ),
            None,
        )
        _ensure_orientation(world, sid, rng)
        _ensure_street(world, sid, "main", rng, founded)
        for hid in sorted(world.settlements[sid].households):
            ensure_household_residence(world, rng, hid)


def settlement_space_step(world, rng):
    # Keep residence occupancy and new construction synchronized with social state.
    for hid in sorted(world.households):
        ensure_household_residence(world, rng, hid)
    for sid in sorted(world.settlements):
        _ensure_market(world, rng, sid)
        _ensure_institutions(world, rng, sid)
        _ensure_workshops(world, rng, sid)

    # Slow physical wear; prosperous towns preserve buildings better.
    for structure in world.settlement_space.structures.values():
        if not structure.active:
            continue
        prosperity = world.settlements[structure.settlement].prosperity
        decay = 0.0012 * max(0.25, 1.05 - prosperity)
        structure.condition = max(0.12, structure.condition - decay)
