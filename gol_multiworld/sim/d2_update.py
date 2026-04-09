"""D2 cellular-automaton update pass (double-buffered)."""

from __future__ import annotations

import random
from typing import Any

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.debug_trace import BirthCauseTracer, D2_BIRTH
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.visibility import count_visible_live_neighbors


def d2_update(
    grid: Grid,
    rules: dict[str, Any],
    rng: random.Random | None = None,
    debugger: BirthCauseTracer | None = None,
) -> Grid:
    """Advance the grid by one D2 tick using double-buffering.

    - Walls and Toxic cells are static (unchanged).
    - Food cells may spoil into Toxic cells.
    - Live cells survive when visible live neighbours are in the
      ``surviveIfVisibleLiveNeighborsIn`` set.
    - Empty cells are born when visible live neighbours are in the
      ``bornIfVisibleLiveNeighborsIn`` set.

    Parameters
    ----------
    grid:
        Current grid state (read-only during this call).
    rules:
        Loaded rules dictionary.

    Returns
    -------
    Grid
        The new grid state after the D2 update.
    """
    if rng is None:
        rng = random.Random()

    survive_set: set[int] = set(
        rules["liveCell"]["surviveIfVisibleLiveNeighborsIn"]
    )
    born_set: set[int] = set(
        rules["emptyCell"]["bornIfVisibleLiveNeighborsIn"]
    )
    food_spoil_chance = float(rules.get("foodSpoilChance", 0.0))

    next_grid = grid.clone()

    for y in range(grid.height):
        for x in range(grid.width):
            cell = grid.get(x, y)

            if cell == CellType.WALL or cell == CellType.TOXIC:
                continue

            if cell == CellType.FOOD:
                if rng.random() < food_spoil_chance:
                    if debugger is not None:
                        debugger.record_transition(
                            grid,
                            x,
                            y,
                            cell,
                            CellType.TOXIC,
                            cause="food_spoil",
                            phase="D2",
                        )
                    next_grid.set(x, y, CellType.TOXIC)
                continue

            live_count = count_visible_live_neighbors(grid, x, y)

            if cell == CellType.LIVE:
                if live_count not in survive_set:
                    if debugger is not None:
                        debugger.record_transition(
                            grid,
                            x,
                            y,
                            cell,
                            CellType.EMPTY,
                            cause="D2_death",
                            phase="D2",
                        )
                    next_grid.set(x, y, CellType.EMPTY)
            elif cell == CellType.EMPTY:
                if live_count in born_set:
                    if debugger is not None:
                        debugger.record_transition(
                            grid,
                            x,
                            y,
                            cell,
                            CellType.LIVE,
                            cause=D2_BIRTH,
                            phase="D2",
                        )
                    next_grid.set(x, y, CellType.LIVE)

    return next_grid
