"""Wall-occluded neighbor visibility helper."""

from __future__ import annotations

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.grid import Grid

# 8-connected neighbor offsets
_NEIGHBOR_OFFSETS: list[tuple[int, int]] = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
]


def get_visible_neighbors(grid: Grid, x: int, y: int) -> list[tuple[int, int]]:
    """Return the coordinates of all 8-neighbors visible from (x, y).

    A neighbor is *not* visible if the cell at that position is a Wall.
    Walls block their own position — cells on the far side of a wall are
    simply not reached because we only look one step away, so any wall
    in the 8-neighborhood hides *itself* from the live-count (since a
    wall can never be Live) and also marks that direction as blocked.

    Per the design spec: "if a wall blocks visibility in a direction,
    cells behind it are ignored."  For a 1-step Moore neighbourhood the
    wall IS the blocked cell, so we exclude it from the visible set.

    Returns
    -------
    list of (nx, ny) coordinates that are visible (not walls) and in bounds.
    """
    visible: list[tuple[int, int]] = []
    for dx, dy in _NEIGHBOR_OFFSETS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < grid.width and 0 <= ny < grid.height:
            if grid.get(nx, ny) != CellType.WALL:
                visible.append((nx, ny))
    return visible


def count_visible_live_neighbors(grid: Grid, x: int, y: int) -> int:
    """Count how many visible neighbors of (x, y) are Live cells."""
    count = 0
    for nx, ny in get_visible_neighbors(grid, x, y):
        if grid.get(nx, ny) == CellType.LIVE:
            count += 1
    return count
