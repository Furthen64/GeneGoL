"""Deterministic wall generation for startup and world resets."""

from __future__ import annotations

import random
from typing import Any

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.grid import Grid

DEFAULT_WALL_GENERATION: dict[str, Any] = {
    "mode": "structured",
    "minRoomSize": 6,
    "targetRoomSize": 10,
    "roomSizeJitter": 3,
    "dividerThickness": 1,
    "dividerGapSize": 2,
    "organicJitter": 1,
    "maxDepth": 6,
    "legacyWallDensity": 0.05,
}


def generate_walls(grid: Grid, rules: dict[str, Any], rng: random.Random) -> None:
    """Populate a fresh grid with wall layouts.

    The generator is deterministic for a given RNG seed. It supports a
    structured mode that subdivides the map into rooms with connected
    dividers, plus a legacy random mode for compatibility.
    """
    config = dict(DEFAULT_WALL_GENERATION)
    wall_generation = rules.get("wallGeneration", {})
    if isinstance(wall_generation, dict):
        config.update(wall_generation)

    grid.clear()

    mode = str(config.get("mode", "structured"))
    if mode == "legacy_random":
        _generate_legacy_random_walls(grid, rng, config)
        return

    _draw_perimeter(grid)

    if grid.width < 5 or grid.height < 5:
        return

    interior_width = grid.width - 2
    interior_height = grid.height - 2
    max_depth = int(config.get("maxDepth", 6))
    target_room_size = max(4, int(config.get("targetRoomSize", 10)))
    min_room_size = max(3, int(config.get("minRoomSize", 6)))
    room_size_jitter = max(0, int(config.get("roomSizeJitter", 3)))

    depth_from_width = max(0, interior_width // target_room_size)
    depth_from_height = max(0, interior_height // target_room_size)
    depth_budget = max(1, min(max_depth, depth_from_width + depth_from_height))

    _subdivide_region(
        grid=grid,
        x0=1,
        y0=1,
        x1=grid.width - 2,
        y1=grid.height - 2,
        depth=depth_budget,
        min_room_size=min_room_size,
        room_size_jitter=room_size_jitter,
        config=config,
        rng=rng,
    )


def _generate_legacy_random_walls(
    grid: Grid,
    rng: random.Random,
    config: dict[str, Any],
) -> None:
    wall_density = float(config.get("legacyWallDensity", 0.05))
    for y in range(grid.height):
        for x in range(grid.width):
            if x in (0, grid.width - 1) or y in (0, grid.height - 1):
                grid.set(x, y, CellType.WALL)
            elif rng.random() < wall_density:
                grid.set(x, y, CellType.WALL)


def _draw_perimeter(grid: Grid) -> None:
    for x in range(grid.width):
        grid.set(x, 0, CellType.WALL)
        grid.set(x, grid.height - 1, CellType.WALL)
    for y in range(grid.height):
        grid.set(0, y, CellType.WALL)
        grid.set(grid.width - 1, y, CellType.WALL)


def _subdivide_region(
    grid: Grid,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    depth: int,
    min_room_size: int,
    room_size_jitter: int,
    config: dict[str, Any],
    rng: random.Random,
) -> None:
    width = x1 - x0 + 1
    height = y1 - y0 + 1
    if depth <= 0 or width < min_room_size * 2 or height < min_room_size * 2:
        return

    orientation = _choose_orientation(width, height, rng)
    divider_thickness = max(1, int(config.get("dividerThickness", 1)))
    divider_gap_size = max(1, int(config.get("dividerGapSize", 2)))
    organic_jitter = max(0, int(config.get("organicJitter", 1)))

    if orientation == "vertical":
        split_x = _pick_split(x0, x1, min_room_size, room_size_jitter, rng)
        if split_x is None:
            return
        _draw_vertical_divider(
            grid,
            x=split_x,
            y0=y0,
            y1=y1,
            thickness=divider_thickness,
            gap_size=divider_gap_size,
            organic_jitter=organic_jitter,
            rng=rng,
        )
        _subdivide_region(
            grid,
            x0,
            y0,
            split_x - 1,
            y1,
            depth - 1,
            min_room_size,
            room_size_jitter,
            config,
            rng,
        )
        _subdivide_region(
            grid,
            split_x + divider_thickness,
            y0,
            x1,
            y1,
            depth - 1,
            min_room_size,
            room_size_jitter,
            config,
            rng,
        )
    else:
        split_y = _pick_split(y0, y1, min_room_size, room_size_jitter, rng)
        if split_y is None:
            return
        _draw_horizontal_divider(
            grid,
            y=split_y,
            x0=x0,
            x1=x1,
            thickness=divider_thickness,
            gap_size=divider_gap_size,
            organic_jitter=organic_jitter,
            rng=rng,
        )
        _subdivide_region(
            grid,
            x0,
            y0,
            x1,
            split_y - 1,
            depth - 1,
            min_room_size,
            room_size_jitter,
            config,
            rng,
        )
        _subdivide_region(
            grid,
            x0,
            split_y + divider_thickness,
            x1,
            y1,
            depth - 1,
            min_room_size,
            room_size_jitter,
            config,
            rng,
        )


def _choose_orientation(width: int, height: int, rng: random.Random) -> str:
    if width > height + 2:
        return "vertical"
    if height > width + 2:
        return "horizontal"
    return "vertical" if rng.random() < 0.5 else "horizontal"


def _pick_split(
    start: int,
    end: int,
    min_room_size: int,
    room_size_jitter: int,
    rng: random.Random,
) -> int | None:
    low = start + min_room_size
    high = end - min_room_size
    if low > high:
        return None

    preferred = start + (end - start) // 2
    if room_size_jitter > 0:
        preferred += rng.randint(-room_size_jitter, room_size_jitter)
    return max(low, min(high, preferred))


def _draw_vertical_divider(
    grid: Grid,
    x: int,
    y0: int,
    y1: int,
    thickness: int,
    gap_size: int,
    organic_jitter: int,
    rng: random.Random,
) -> None:
    gap_spans = _build_gap_spans(y0, y1, gap_size, rng)
    wobble = 0
    for y in range(y0, y1 + 1):
        if organic_jitter > 0 and (y - y0) % 5 == 0:
            wobble = max(-organic_jitter, min(organic_jitter, wobble + rng.randint(-1, 1)))
        if _in_gap(y, gap_spans):
            continue
        wall_x = max(1, min(grid.width - 2, x + wobble))
        for dx in range(thickness):
            grid.set(min(grid.width - 2, wall_x + dx), y, CellType.WALL)


def _draw_horizontal_divider(
    grid: Grid,
    y: int,
    x0: int,
    x1: int,
    thickness: int,
    gap_size: int,
    organic_jitter: int,
    rng: random.Random,
) -> None:
    gap_spans = _build_gap_spans(x0, x1, gap_size, rng)
    wobble = 0
    for x in range(x0, x1 + 1):
        if organic_jitter > 0 and (x - x0) % 5 == 0:
            wobble = max(-organic_jitter, min(organic_jitter, wobble + rng.randint(-1, 1)))
        if _in_gap(x, gap_spans):
            continue
        wall_y = max(1, min(grid.height - 2, y + wobble))
        for dy in range(thickness):
            grid.set(x, min(grid.height - 2, wall_y + dy), CellType.WALL)


def _build_gap_spans(start: int, end: int, gap_size: int, rng: random.Random) -> list[tuple[int, int]]:
    length = end - start + 1
    if length <= gap_size + 2:
        return []

    gap_count = 1 if length < 18 else 2
    spans: list[tuple[int, int]] = []
    available_start = start + 1
    available_end = end - 1
    for _ in range(gap_count):
        center = rng.randint(available_start, available_end)
        half = gap_size // 2
        span_start = max(start + 1, center - half)
        span_end = min(end - 1, span_start + gap_size - 1)
        spans.append((span_start, span_end))
    return spans


def _in_gap(value: int, spans: list[tuple[int, int]]) -> bool:
    for start, end in spans:
        if start <= value <= end:
            return True
    return False