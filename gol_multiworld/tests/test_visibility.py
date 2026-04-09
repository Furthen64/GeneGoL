"""Tests for wall-occluded neighbor visibility."""

from __future__ import annotations

import pytest

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.visibility import (
    count_visible_live_neighbors,
    get_visible_neighbors,
)


def _make_grid(width: int = 5, height: int = 5) -> Grid:
    return Grid(width, height)


def test_all_neighbors_visible_in_open_field() -> None:
    grid = _make_grid(5, 5)
    # Interior cell at (2,2) — all 8 neighbors are empty and visible
    visible = get_visible_neighbors(grid, 2, 2)
    assert len(visible) == 8


def test_corner_has_fewer_visible_neighbors() -> None:
    grid = _make_grid(5, 5)
    # Top-left corner: only 3 in-bounds neighbors
    visible = get_visible_neighbors(grid, 0, 0)
    assert len(visible) == 3


def test_edge_center_has_five_visible_neighbors() -> None:
    grid = _make_grid(5, 5)
    # Top edge center: 5 neighbors in-bounds
    visible = get_visible_neighbors(grid, 2, 0)
    assert len(visible) == 5


def test_wall_neighbor_is_excluded() -> None:
    grid = _make_grid(5, 5)
    # Place a wall at (3, 2) — next to the cell at (2, 2)
    grid.set(3, 2, CellType.WALL)
    visible = get_visible_neighbors(grid, 2, 2)
    assert (3, 2) not in visible
    assert len(visible) == 7  # one less than the normal 8


def test_multiple_walls_reduce_visibility() -> None:
    grid = _make_grid(5, 5)
    grid.set(1, 1, CellType.WALL)
    grid.set(3, 1, CellType.WALL)
    visible = get_visible_neighbors(grid, 2, 2)
    assert (1, 1) not in visible
    assert (3, 1) not in visible
    assert len(visible) == 6


def test_count_live_neighbors_empty_grid() -> None:
    grid = _make_grid(5, 5)
    assert count_visible_live_neighbors(grid, 2, 2) == 0


def test_count_live_neighbors_surrounded() -> None:
    grid = _make_grid(5, 5)
    # Surround (2,2) with live cells
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            grid.set(2 + dx, 2 + dy, CellType.LIVE)
    assert count_visible_live_neighbors(grid, 2, 2) == 8


def test_wall_blocks_live_cell_from_count() -> None:
    grid = _make_grid(5, 5)
    grid.set(3, 2, CellType.LIVE)   # would normally count
    grid.set(3, 2, CellType.WALL)   # replace with wall — now excluded
    assert count_visible_live_neighbors(grid, 2, 2) == 0


def test_wall_hides_itself_not_cells_behind() -> None:
    """A wall at (3,2) hides itself; (4,2) is simply out of one-step reach."""
    grid = _make_grid(7, 7)
    grid.set(3, 3, CellType.WALL)
    grid.set(4, 3, CellType.LIVE)   # Two steps away — not in neighborhood
    # The live cell at (4,3) is NOT a direct neighbor of (2,3)
    assert count_visible_live_neighbors(grid, 2, 3) == 0


def test_food_and_toxic_are_not_live() -> None:
    grid = _make_grid(5, 5)
    grid.set(3, 2, CellType.FOOD)
    grid.set(1, 2, CellType.TOXIC)
    assert count_visible_live_neighbors(grid, 2, 2) == 0
