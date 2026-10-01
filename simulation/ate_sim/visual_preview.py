from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .visual_spec import BuildingSpec, SettlementVisualSpec, Vec3


@dataclass(frozen=True)
class PreviewStyle:
    width: int = 1400
    height: int = 1000
    margin: int = 70
    background: str = "#d8d0bd"
    land: str = "#b8aa86"
    disturbed_land: str = "#a99370"
    water: str = "#6f9fb2"
    vegetation: str = "#6f8657"
    vegetation_outline: str = "#506441"
    road: str = "#685a48"
    parcel_fill: str = "#d8c9a4"
    parcel_outline: str = "#8a775d"
    building: str = "#5b5a56"
    building_outline: str = "#343431"
    damaged: str = "#b85c3f"
    repaired: str = "#d68a4a"
    magic: str = "#6a5acd"
    person: str = "#293a46"
    text: str = "#282723"
    panel: str = "#eee9dc"


def _all_points(spec: SettlementVisualSpec) -> Iterable[Vec3]:
    for region in spec.terrain_regions:
        yield from region.boundary
    for parcel in spec.parcels:
        yield parcel.position
    for road in spec.roads:
        yield from road.centerline.points
    for building in spec.buildings:
        yield building.position
    for zone in spec.vegetation_zones:
        yield from zone.boundary
    for person in spec.population:
        yield person.position
    for manifestation in spec.magic_manifestations:
        yield manifestation.position
    if spec.focus_position is not None:
        yield spec.focus_position


def _bounds(spec: SettlementVisualSpec) -> tuple[float, float, float, float]:
    points = list(_all_points(spec))
    if not points:
        return (0.0, 0.0, 100.0, 100.0)
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if math.isclose(min_x, max_x):
        min_x -= 10.0
        max_x += 10.0
    if math.isclose(min_y, max_y):
        min_y -= 10.0
        max_y += 10.0
    pad_x = max((max_x - min_x) * 0.08, 5.0)
    pad_y = max((max_y - min_y) * 0.08, 5.0)
    return min_x - pad_x, min_y - pad_y, max_x + pad_x, max_y + pad_y


def _transform(
    point: Vec3,
    bounds: tuple[float, float, float, float],
    style: PreviewStyle,
) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = bounds
    usable_w = style.width - style.margin * 2
    usable_h = style.height - style.margin * 2
    scale = min(usable_w / (max_x - min_x), usable_h / (max_y - min_y))
    drawn_w = (max_x - min_x) * scale
    drawn_h = (max_y - min_y) * scale
    left = (style.width - drawn_w) / 2
    top = (style.height - drawn_h) / 2
    x = left + (point.x - min_x) * scale
    y = top + drawn_h - (point.y - min_y) * scale
    return x, y


def _scale(bounds: tuple[float, float, float, float], style: PreviewStyle) -> float:
    min_x, min_y, max_x, max_y = bounds
    usable_w = style.width - style.margin * 2
    usable_h = style.height - style.margin * 2
    return min(usable_w / (max_x - min_x), usable_h / (max_y - min_y))


def _rotated_rect(
    center: tuple[float, float],
    width_px: float,
    height_px: float,
    degrees: float,
) -> list[tuple[float, float]]:
    cx, cy = center
    radians = math.radians(-degrees)
    cos_a = math.cos(radians)
    sin_a = math.sin(radians)
    corners = [
        (-width_px / 2, -height_px / 2),
        (width_px / 2, -height_px / 2),
        (width_px / 2, height_px / 2),
        (-width_px / 2, height_px / 2),
    ]
    result = []
    for x, y in corners:
        result.append((cx + x * cos_a - y * sin_a, cy + x * sin_a + y * cos_a))
    return result


def _building_damage(building: BuildingSpec) -> tuple[float, float]:
    damage = 0.0
    repair = 0.0
    for phase in building.phases:
        damage = max(damage, phase.damage_fraction)
        repair = max(repair, phase.repair_fraction)
    return damage, repair


def render_settlement_preview(
    spec: SettlementVisualSpec,
    output_path: str | Path,
    *,
    style: PreviewStyle | None = None,
    show_people: bool = True,
    show_labels: bool = True,
) -> Path:
    style = style or PreviewStyle()
    bounds = _bounds(spec)
    world_scale = _scale(bounds, style)
    image = Image.new("RGB", (style.width, style.height), style.background)
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()

    # Terrain and water.
    for region in spec.terrain_regions:
        polygon = [_transform(point, bounds, style) for point in region.boundary]
        if len(polygon) < 3:
            continue
        if region.surface_kind == "water":
            fill = style.water
        else:
            # Use only supplied terrain facts. Elevation darkens the base earth tone;
            # moisture adds a green cast. This is diagnostic styling, not new world state.
            elevation = sum(region.elevation_band) / 2.0
            moisture = max(0.0, min(1.0, region.moisture))
            base = (184, 170, 134)
            r = int(max(70, min(210, base[0] - elevation * 55 - moisture * 18)))
            g = int(max(70, min(210, base[1] - elevation * 35 + moisture * 26)))
            b = int(max(70, min(210, base[2] - elevation * 18)))
            fill = (r, g, b, 255)
            if region.disturbance is not None and region.disturbance >= 0.45:
                fill = style.disturbed_land
        draw.polygon(polygon, fill=fill, outline=style.text)

    # Vegetation.
    for zone in spec.vegetation_zones:
        polygon = [_transform(point, bounds, style) for point in zone.boundary]
        if len(polygon) < 3:
            continue
        alpha = int(70 + 120 * max(0.0, min(1.0, zone.density)))
        draw.polygon(
            polygon,
            fill=style.vegetation + f"{alpha:02x}",
            outline=style.vegetation_outline,
        )

    # Parcels.
    for parcel in spec.parcels:
        center = _transform(parcel.position, bounds, style)
        width_m, depth_m = parcel.size_m
        polygon = _rotated_rect(
            center,
            max(4.0, width_m * world_scale),
            max(4.0, depth_m * world_scale),
            parcel.facing_degrees,
        )
        alpha = 90 if parcel.land_use == "residential" else 120
        fill = style.parcel_fill + f"{alpha:02x}"
        if parcel.land_use == "institutional":
            fill = "#c6b88c99"
        elif parcel.land_use == "workshop":
            fill = "#c9aa7a99"
        elif parcel.land_use == "public":
            fill = "#d5c58db0"
        draw.polygon(polygon, fill=fill, outline=style.parcel_outline)

    # Roads.
    for road in spec.roads:
        points = [_transform(point, bounds, style) for point in road.centerline.points]
        if len(points) < 2:
            continue
        width = max(2, round(road.width_m * world_scale))
        draw.line(points, fill=style.road, width=width, joint="curve")

    # Buildings.
    for building in spec.buildings:
        center = _transform(building.position, bounds, style)
        width_m, height_m = building.footprint_size_m
        polygon = _rotated_rect(
            center,
            max(4.0, width_m * world_scale),
            max(4.0, height_m * world_scale),
            building.facing_degrees,
        )
        building_fill = style.building
        if building.function in ("market_hall",):
            building_fill = "#9a7748"
        elif "society" in building.function or building.function == "guildhall":
            building_fill = "#6f667f"
        elif building.function in ("smithy", "pottery", "carpenter_shop", "mason_yard", "weaving_house", "food_workshop", "workshop"):
            building_fill = "#7b5b45"
        elif building.function == "leased_dwelling":
            building_fill = "#686762"
        draw.polygon(polygon, fill=building_fill, outline=style.building_outline)
        damage, repair = _building_damage(building)
        if damage > 0.0:
            draw.line(polygon + [polygon[0]], fill=style.damaged, width=max(2, round(3 + 5 * damage)))
        if repair > 0.0:
            x, y = center
            radius = max(3, round(4 + 8 * repair))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=style.repaired, width=2)
        if show_labels and building.function not in ("dwelling", "leased_dwelling"):
            label = building.function.replace("_", " ")
            draw.text((center[0] + 6, center[1] - 6), label, fill=style.text, font=font)

    # People markers.
    if show_people:
        for person in spec.population:
            x, y = _transform(person.position, bounds, style)
            r = 3 if person.representation_tier != "embodied" else 5
            draw.ellipse((x - r, y - r, x + r, y + r), fill=style.person)

    # Settlement focus marker for truth-only simulation previews.
    if spec.focus_position is not None:
        x, y = _transform(spec.focus_position, bounds, style)
        r = 9
        draw.ellipse((x - r, y - r, x + r, y + r), fill=style.panel, outline=style.text, width=3)
        draw.line((x - 14, y, x + 14, y), fill=style.text, width=2)
        draw.line((x, y - 14, x, y + 14), fill=style.text, width=2)

    # Magic markers.
    for manifestation in spec.magic_manifestations:
        x, y = _transform(manifestation.position, bounds, style)
        radius = max(7.0, manifestation.radius_m * world_scale)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            outline=style.magic,
            width=3,
        )
        draw.line((x - radius, y, x + radius, y), fill=style.magic, width=1)
        draw.line((x, y - radius, x, y + radius), fill=style.magic, width=1)

    if show_labels:
        title = f"{spec.settlement_id}  |  year {spec.time_slice_year}  |  seed {spec.world_seed}"
        draw.rounded_rectangle((18, 16, 560, 48), radius=8, fill=style.panel, outline=style.text)
        draw.text((30, 26), title, fill=style.text, font=font)

        if spec.metadata:
            panel_x0 = style.width - 290
            panel_y0 = 16
            rows = list(sorted(spec.metadata.items()))[:14]
            panel_h = 26 + len(rows) * 15
            draw.rounded_rectangle(
                (panel_x0, panel_y0, style.width - 18, panel_y0 + panel_h),
                radius=8,
                fill=style.panel,
                outline=style.text,
            )
            draw.text((panel_x0 + 12, panel_y0 + 9), "simulation facts", fill=style.text, font=font)
            for index, (key, value) in enumerate(rows):
                y = panel_y0 + 27 + index * 15
                draw.text((panel_x0 + 12, y), f"{key}: {value}", fill=style.text, font=font)

        legend_y = style.height - 152
        draw.rounded_rectangle(
            (18, legend_y, 250, style.height - 18),
            radius=8,
            fill=style.panel,
            outline=style.text,
        )
        entries = [
            ("water", style.water),
            ("vegetation", style.vegetation),
            ("parcel", style.parcel_outline),
            ("road", style.road),
            ("building", style.building),
            ("damage", style.damaged),
            ("repair", style.repaired),
            ("magic", style.magic),
            ("person", style.person),
        ]
        for index, (label, color) in enumerate(entries):
            y = legend_y + 12 + index * 14
            draw.rectangle((30, y, 40, y + 8), fill=color)
            draw.text((47, y - 1), label, fill=style.text, font=font)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG", optimize=False)
    return target
