"""Grid representation and random-world generation."""

from __future__ import annotations

import random
from typing import Any

from gol_multiworld.sim.cell_types import CellType


class Grid:
    """2D grid of CellType values supporting double-buffering for D2 updates."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._cells: list[list[int]] = [
            [CellType.EMPTY] * width for _ in range(height)
        ]

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    def get(self, x: int, y: int) -> int:
        """Return the cell type at (x, y) or EMPTY if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._cells[y][x]
        return CellType.EMPTY

    def set(self, x: int, y: int, value: int) -> None:
        """Set the cell type at (x, y). Ignores out-of-bounds writes."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._cells[y][x] = value

    def clone(self) -> "Grid":
        """Return a deep copy of this grid (used for double-buffering)."""
        new_grid = Grid(self.width, self.height)
        new_grid._cells = [row[:] for row in self._cells]
        return new_grid

    # ------------------------------------------------------------------
    # World generation
    # ------------------------------------------------------------------

    def randomize(
        self,
        rules: dict[str, Any],
        seed: int | None = None,
        toxic_density: float = 0.02,
        live_density: float = 0.15,
    ) -> None:
        """Fill the grid with a random initial state.

        Parameters
        ----------
        rules:
            Loaded rules dict (used for foodScarcity).
        seed:
            Optional RNG seed for deterministic runs.
        toxic_density:
            Fraction of cells that become toxic.
        live_density:
            Fraction of cells that start as live.
        """
        rng = random.Random(seed)
        food_density: float = float(rules.get("foodScarcity", 0.02))

        for y in range(self.height):
            for x in range(self.width):
                if self._cells[y][x] == CellType.WALL:
                    continue
                r = rng.random()
                if r < toxic_density:
                    self._cells[y][x] = CellType.TOXIC
                elif r < toxic_density + food_density:
                    self._cells[y][x] = CellType.FOOD
                elif r < toxic_density + food_density + live_density:
                    self._cells[y][x] = CellType.LIVE
                else:
                    self._cells[y][x] = CellType.EMPTY

    def clear(self) -> None:
        """Reset all cells to EMPTY."""
        for y in range(self.height):
            for x in range(self.width):
                self._cells[y][x] = CellType.EMPTY
