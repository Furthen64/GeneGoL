"""D1 coordinator: seeds new organisms when the world is sparse."""

from __future__ import annotations

import random
from typing import Any

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.genes import Gene
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.organism_detection import Organism

# Size of each seeded clump (2×2 square of Live cells)
_CLUMP_SIZE = 2

# Default minimum organism count before coordinator activates
# (can be overridden in rules JSON via "coordinatorSpawnThreshold")
_DEFAULT_SPAWN_THRESHOLD = 2


def coordinator_tick(
    grid: Grid,
    organisms: list[Organism],
    tick: int,
    rules: dict[str, Any],
    rng: random.Random | None = None,
) -> None:
    """Spawn new live-cell clumps if organism count is critically low.

    Newly spawned clumps receive default genes.  The coordinator does
    not bypass D2 — it simply plants seeds that D2 will evolve.

    Parameters
    ----------
    grid:
        Grid state (modified in-place).
    organisms:
        Currently active organisms.
    tick:
        Current simulation tick.
    rules:
        Loaded rules dictionary.  Reads ``coordinatorSpawnThreshold``
        (default 2) to determine when spawning is triggered.
    rng:
        Optional seeded random instance.
    """
    if rng is None:
        rng = random.Random()

    threshold: int = int(rules.get("coordinatorSpawnThreshold", _DEFAULT_SPAWN_THRESHOLD))
    if len(organisms) >= threshold:
        return

    # Find a free area (no walls or other non-empty cells nearby)
    attempts = 20
    for _ in range(attempts):
        x = rng.randint(1, grid.width - _CLUMP_SIZE - 2)
        y = rng.randint(1, grid.height - _CLUMP_SIZE - 2)
        if _area_free(grid, x, y, _CLUMP_SIZE):
            _plant_clump(grid, x, y, _CLUMP_SIZE)
            break


def _area_free(grid: Grid, x: int, y: int, size: int) -> bool:
    for dy in range(size):
        for dx in range(size):
            if grid.get(x + dx, y + dy) != CellType.EMPTY:
                return False
    return True


def _plant_clump(grid: Grid, x: int, y: int, size: int) -> None:
    for dy in range(size):
        for dx in range(size):
            grid.set(x + dx, y + dy, CellType.LIVE)
