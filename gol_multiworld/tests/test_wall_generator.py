"""Tests for structured wall generation."""

from __future__ import annotations

import random

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.wall_generator import generate_walls


RULES = {
    "foodScarcity": 0.02,
    "wallGeneration": {
        "mode": "structured",
        "minRoomSize": 5,
        "targetRoomSize": 8,
        "dividerThickness": 1,
        "dividerGapSize": 2,
        "organicJitter": 1,
        "maxDepth": 5,
    },
}


def _wall_snapshot(grid: Grid) -> list[list[int]]:
    return [row[:] for row in grid._cells]


def test_structured_walls_are_deterministic() -> None:
    grid_a = Grid(24, 24)
    grid_b = Grid(24, 24)

    generate_walls(grid_a, RULES, random.Random(1234))
    generate_walls(grid_b, RULES, random.Random(1234))

    assert _wall_snapshot(grid_a) == _wall_snapshot(grid_b)


def test_structured_walls_draw_perimeter_and_internal_dividers() -> None:
    grid = Grid(24, 24)
    generate_walls(grid, RULES, random.Random(42))

    for x in range(grid.width):
        assert grid.get(x, 0) == CellType.WALL
        assert grid.get(x, grid.height - 1) == CellType.WALL
    for y in range(grid.height):
        assert grid.get(0, y) == CellType.WALL
        assert grid.get(grid.width - 1, y) == CellType.WALL

    interior_walls = sum(
        1
        for y in range(1, grid.height - 1)
        for x in range(1, grid.width - 1)
        if grid.get(x, y) == CellType.WALL
    )
    assert interior_walls > 0

    middle_row = [grid.get(x, grid.height // 2) for x in range(grid.width)]
    assert any(cell == CellType.WALL for cell in middle_row)
    assert any(cell == CellType.EMPTY for cell in middle_row)


def test_legacy_random_mode_keeps_random_scatter() -> None:
    grid = Grid(20, 20)
    rules = {
        "foodScarcity": 0.02,
        "wallGeneration": {
            "mode": "legacy_random",
            "legacyWallDensity": 0.1,
        },
    }

    generate_walls(grid, rules, random.Random(7))

    interior_walls = sum(
        1
        for y in range(1, grid.height - 1)
        for x in range(1, grid.width - 1)
        if grid.get(x, y) == CellType.WALL
    )
    assert interior_walls > 0
    assert interior_walls < (grid.width - 2) * (grid.height - 2)


def test_none_mode_leaves_grid_without_walls() -> None:
    grid = Grid(20, 20)
    rules = {
        "foodScarcity": 0.02,
        "wallGeneration": {
            "mode": "none",
        },
    }

    generate_walls(grid, rules, random.Random(11))

    assert all(
        grid.get(x, y) != CellType.WALL
        for y in range(grid.height)
        for x in range(grid.width)
    )