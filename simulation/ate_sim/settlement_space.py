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
class SettlementSiteProfile:
    settlement: int
    archetype: str
    main_angle_degrees: float
    wet_side_degrees: float
    forest_side_degrees: float
    high_side_degrees: float
    growth_bias_degrees: float
    slope_strength: float
    moisture_gradient: float
    forest_gradient: float
    lane_spacing_m: float
    parcel_spacing_m: float
    curvature_m: float


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
    site_profiles: dict[int, SettlementSiteProfile] = field(default_factory=dict)

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


# Settlement geometry is derived from the physical site first, then history
# grows the town through persistent roads, parcels and structures.


def _rotate(x, y, degrees):
    r = math.radians(degrees)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


def _bearing(x, y, fallback=0.0):
    if abs(x) + abs(y) < 1e-12:
        return fallback
    return math.degrees(math.atan2(y, x))


def _gradient(world, sid, attribute):
    settlement = world.settlements[sid]
    center = world.cells[(settlement.x, settlement.y)]
    gx = 0.0
    gy = 0.0
    weight_sum = 0.0
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx == 0 and dy == 0:
                continue
            cell = world.cells.get((settlement.x + dx, settlement.y + dy))
            if cell is None:
                continue
            distance = math.hypot(dx, dy)
            weight = 1.0 / distance
            delta = getattr(cell, attribute) - getattr(center, attribute)
            gx += delta * (dx / distance) * weight
            gy += delta * (dy / distance) * weight
            weight_sum += weight
    if weight_sum:
        gx /= weight_sum
        gy /= weight_sum
    return gx, gy


def _regional_axis(world, sid):
    settlement = world.settlements[sid]
    choices = []
    for other_id, other in world.settlements.items():
        if other_id == sid:
            continue
        dx = other.x - settlement.x
        dy = other.y - settlement.y
        distance = math.hypot(dx, dy)
        choices.append((distance, other_id, dx, dy))
    if not choices:
        return (1.0, 0.0)
    _, _, dx, dy = min(choices)
    length = max(1e-9, math.hypot(dx, dy))
    return dx / length, dy / length


def _ensure_site_profile(world, sid, rng):
    state = world.settlement_space
    old = state.site_profiles.get(sid)
    if old is not None:
        return old

    settlement = world.settlements[sid]
    cell = world.cells[(settlement.x, settlement.y)]
    egx, egy = _gradient(world, sid, "elevation")
    mgx, mgy = _gradient(world, sid, "moisture")
    fgx, fgy = _gradient(world, sid, "forest")
    hgx, hgy = _gradient(world, sid, "hazard")
    slope = math.hypot(egx, egy)
    moisture_gradient = math.hypot(mgx, mgy)
    forest_gradient = math.hypot(fgx, fgy)

    regional_x, regional_y = _regional_axis(world, sid)

    # Roads prefer contours when slope is meaningful, but still acknowledge the
    # direction of regional travel. This makes the founding plan site-specific.
    if slope > 0.012:
        contour_x, contour_y = -egy, egx
        if contour_x * regional_x + contour_y * regional_y < 0:
            contour_x, contour_y = -contour_x, -contour_y
        contour_len = max(1e-9, math.hypot(contour_x, contour_y))
        contour_x /= contour_len
        contour_y /= contour_len
        main_x = contour_x * 0.72 + regional_x * 0.28
        main_y = contour_y * 0.72 + regional_y * 0.28
    else:
        main_x, main_y = regional_x, regional_y

    main_angle = _bearing(main_x, main_y)
    wet_angle = _bearing(mgx, mgy, main_angle + 90.0)
    forest_angle = _bearing(fgx, fgy, main_angle + 90.0)
    high_angle = _bearing(egx, egy, main_angle)
    # Expansion prefers drier, safer ground while still leaning toward regional travel.
    growth_x = regional_x * 0.38 - mgx * 4.8 - hgx * 2.2
    growth_y = regional_y * 0.38 - mgy * 4.8 - hgy * 2.2
    growth_angle = _bearing(growth_x, growth_y, main_angle)

    if cell.moisture >= 0.67 or moisture_gradient >= 0.045:
        archetype = "waterside"
    elif cell.forest >= 0.62 or forest_gradient >= 0.055:
        archetype = "woodland"
    elif cell.elevation >= 0.60 or slope >= 0.055:
        archetype = "upland"
    elif cell.fertility >= 0.66 and cell.forest < 0.52:
        archetype = "open_crossroads"
    else:
        archetype = "mixed"

    lane_spacing = {
        "waterside": 43.0,
        "woodland": 56.0,
        "upland": 38.0,
        "open_crossroads": 47.0,
        "mixed": 48.0,
    }[archetype]
    parcel_spacing = {
        "waterside": 24.0,
        "woodland": 29.0,
        "upland": 22.0,
        "open_crossroads": 21.0,
        "mixed": 23.0,
    }[archetype]
    curvature = min(
        22.0,
        3.0 + slope * 120.0 + moisture_gradient * 85.0 + forest_gradient * 45.0,
    )

    profile = SettlementSiteProfile(
        settlement=sid,
        archetype=archetype,
        main_angle_degrees=main_angle,
        wet_side_degrees=wet_angle,
        forest_side_degrees=forest_angle,
        high_side_degrees=high_angle,
        growth_bias_degrees=growth_angle,
        slope_strength=slope,
        moisture_gradient=moisture_gradient,
        forest_gradient=forest_gradient,
        lane_spacing_m=lane_spacing,
        parcel_spacing_m=parcel_spacing,
        curvature_m=curvature,
    )
    state.site_profiles[sid] = profile
    state.settlement_orientation[sid] = main_angle
    return profile


def _ensure_orientation(world, sid, rng):
    return _ensure_site_profile(world, sid, rng).main_angle_degrees


def _surface_for(world, sid):
    s = world.settlements[sid]
    return "compacted_gravel" if s.prosperity >= 0.42 else "packed_earth"


def _street_geometry(profile, key):
    c = profile.curvature_m
    spacing = profile.lane_spacing_m

    if key == "main":
        return (
            (-180, c * 0.18),
            (-95, -c * 0.30),
            (0, 0),
            (92, c * 0.34),
            (180, -c * 0.12),
        ), 7.0, "main"

    if key == "cross":
        cross_len = 145 if profile.archetype == "open_crossroads" else 118
        return (
            (-c * 0.10, -cross_len),
            (c * 0.20, -60),
            (0, 0),
            (-c * 0.18, 60),
            (c * 0.08, cross_len),
        ), 5.5, "cross"

    if key == "lane_a":
        return (
            (-150, spacing),
            (-72, spacing + c * 0.22),
            (0, spacing - c * 0.12),
            (74, spacing + c * 0.16),
            (150, spacing),
        ), 4.2, "lane"

    if key == "lane_b":
        return (
            (-145, -spacing),
            (-72, -spacing - c * 0.12),
            (0, -spacing + c * 0.18),
            (72, -spacing - c * 0.22),
            (145, -spacing),
        ), 4.2, "lane"

    if key == "spur_a":
        return (
            (-18, 8),
            (35, 42),
            (82, 78),
            (132, 112),
        ), 3.8, "spur"

    if key == "spur_b":
        return (
            (14, -10),
            (-34, -43),
            (-79, -82),
            (-124, -116),
        ), 3.8, "spur"

    raise KeyError(key)


def _ensure_street(world, sid, key, rng, origin_event=None):
    state = world.settlement_space
    old = state.street_ids.get((sid, key))
    if old is not None:
        return state.streets[old]
    profile = _ensure_site_profile(world, sid, rng)
    points, width, kind = _street_geometry(profile, key)
    rotated = tuple(_rotate(x, y, profile.main_angle_degrees) for x, y in points)
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


def _add_row(slots, street, axis, fixed, positions, side_offsets, facing):
    for position in positions:
        for side in side_offsets:
            if axis == "x":
                slots.append((street, position, fixed + side, facing if side > 0 else facing + 180))
            else:
                slots.append((street, fixed + side, position, facing if side < 0 else facing + 180))


def _site_slots(profile):
    spacing = profile.parcel_spacing_m
    long_positions = [
        -6 * spacing, -5 * spacing, -4 * spacing, -3 * spacing,
        -2 * spacing, -spacing, spacing, 2 * spacing,
        3 * spacing, 4 * spacing, 5 * spacing, 6 * spacing,
    ]
    short_positions = [-4 * spacing, -3 * spacing, -2 * spacing, -spacing, spacing, 2 * spacing, 3 * spacing, 4 * spacing]
    side = 14.0
    slots = []

    # Every settlement begins on its terrain-selected founding axis.
    _add_row(slots, "main", "x", 0.0, long_positions, (-side, side), 0)

    if profile.archetype == "waterside":
        # Determine which side of the main road is wetter; early growth favors the dry bank.
        relative = math.radians(profile.wet_side_degrees - profile.main_angle_degrees)
        wet_sign = 1 if math.sin(relative) >= 0 else -1
        dry_fixed = -wet_sign * profile.lane_spacing_m
        wet_fixed = wet_sign * profile.lane_spacing_m
        _add_row(slots, "lane_b" if dry_fixed < 0 else "lane_a", "x", dry_fixed, long_positions, (-side, side), 0)
        _add_row(slots, "cross", "y", 0.0, short_positions, (-side, side), 90)
        # The wet side fills later and more sparsely.
        sparse = long_positions[::2]
        _add_row(slots, "lane_a" if wet_fixed > 0 else "lane_b", "x", wet_fixed, sparse, (-side, side), 0)
    elif profile.archetype == "woodland":
        _add_row(slots, "spur_a", "x", 0.0, short_positions, (-13.0, 13.0), 34)
        _add_row(slots, "spur_b", "x", 0.0, short_positions, (-13.0, 13.0), 214)
        _add_row(slots, "cross", "y", 0.0, short_positions[::2], (-14.0, 14.0), 90)
        _add_row(slots, "lane_a", "x", profile.lane_spacing_m, short_positions[1::2], (-13.0, 13.0), 0)
    elif profile.archetype == "upland":
        _add_row(slots, "lane_a", "x", profile.lane_spacing_m, long_positions, (-12.0, 12.0), 0)
        _add_row(slots, "lane_b", "x", -profile.lane_spacing_m, short_positions, (-12.0, 12.0), 0)
        _add_row(slots, "cross", "y", 0.0, short_positions[::2], (-13.0, 13.0), 90)
    elif profile.archetype == "open_crossroads":
        _add_row(slots, "cross", "y", 0.0, long_positions, (-14.0, 14.0), 90)
        _add_row(slots, "lane_a", "x", profile.lane_spacing_m, long_positions, (-13.0, 13.0), 0)
        _add_row(slots, "lane_b", "x", -profile.lane_spacing_m, long_positions, (-13.0, 13.0), 0)
    else:
        _add_row(slots, "cross", "y", 0.0, short_positions, (-14.0, 14.0), 90)
        _add_row(slots, "lane_a", "x", profile.lane_spacing_m, short_positions, (-13.0, 13.0), 0)
        _add_row(slots, "lane_b", "x", -profile.lane_spacing_m, short_positions, (-13.0, 13.0), 0)

    return tuple(slots)


def _next_slot(world, sid, rng):
    state = world.settlement_space
    profile = _ensure_site_profile(world, sid, rng)
    slots = _site_slots(profile)
    index = state.lot_cursor.get(sid, 0)

    if index < len(slots):
        street_key, x, y, facing = slots[index]
        _ensure_street(world, sid, street_key, rng)
        state.lot_cursor[sid] = index + 1
        rx, ry = _rotate(x, y, profile.main_angle_degrees)
        return rx, ry, (facing + profile.main_angle_degrees) % 360.0

    # Late growth forms an irregular outer ring biased toward the safer/drier
    # growth direction selected by the site's actual gradients.
    ring_index = index - len(slots)
    ring = 1 + ring_index // 28
    offset = ring_index % 28
    relative_bias = math.radians(profile.growth_bias_degrees - profile.main_angle_degrees)
    golden = math.radians(137.507764)
    theta = relative_bias + offset * golden
    radius = 180 + ring * (26 if profile.archetype != "woodland" else 32)
    x = math.cos(theta) * radius
    y = math.sin(theta) * radius
    street_key = "main" if abs(y) < abs(x) else "cross"
    _ensure_street(world, sid, street_key, rng)
    state.lot_cursor[sid] = index + 1
    rx, ry = _rotate(x, y, profile.main_angle_degrees)
    facing = math.degrees(math.atan2(-ry, -rx))
    return rx, ry, facing % 360.0


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


def _ensure_trade_gateways(world, rng, sid):
    state = world.settlement_space
    origin = world.settlements[sid]
    profile = _ensure_site_profile(world, sid, rng)
    for asset in sorted(world.infrastructure.assets.values(), key=lambda a: a.id):
        if asset.kind != "road" or sid not in asset.settlements or len(asset.settlements) != 2:
            continue
        destination = asset.settlements[0] if asset.settlements[1] == sid else asset.settlements[1]
        key = f"gateway:{destination}"
        if (sid, key) in state.street_ids:
            continue
        target = world.settlements[destination]
        bearing = math.degrees(math.atan2(target.y - origin.y, target.x - origin.x))
        radians = math.radians(bearing)
        nx, ny = -math.sin(radians), math.cos(radians)
        bend = min(16.0, profile.curvature_m * 0.55)
        points = (
            (0.0, 0.0),
            (math.cos(radians) * 72 + nx * bend, math.sin(radians) * 72 + ny * bend),
            (math.cos(radians) * 145 - nx * bend * 0.4, math.sin(radians) * 145 - ny * bend * 0.4),
            (math.cos(radians) * 205, math.sin(radians) * 205),
        )
        state.create_street(
            sid,
            key,
            "gateway",
            points,
            5.0 + asset.condition * 2.0,
            _surface_for(world, sid),
            asset.built,
            asset.origin_event,
            condition=asset.condition,
        )


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
        _ensure_site_profile(world, sid, rng)
        _ensure_street(world, sid, "main", rng, founded)
        for hid in sorted(world.settlements[sid].households):
            ensure_household_residence(world, rng, hid)


def settlement_space_step(world, rng):
    # Keep residence occupancy and new construction synchronized with social state.
    for hid in sorted(world.households):
        ensure_household_residence(world, rng, hid)
    for sid in sorted(world.settlements):
        _ensure_trade_gateways(world, rng, sid)
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
