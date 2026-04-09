"""D3 controller: food consumption, toxic memory, and gentle steering."""

from __future__ import annotations

import random
from typing import Any

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.organism_detection import Organism

# 8-connected offsets
_NEIGHBOR_OFFSETS: list[tuple[int, int]] = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
]


def d3_tick(
    grid: Grid,
    organisms: list[Organism],
    tick: int,
    rules: dict[str, Any],
    rng: random.Random | None = None,
) -> Grid:
    """Run the D3 pass for one tick.

    Tick order:
    1. Handle food consumption (organism cells touching Food → convert to Live)
    2. Handle toxic contact (record bad-zone memory, decay old entries)
    3. Apply gentle steering bias

    Parameters
    ----------
    grid:
        Grid state after D2 update (will be mutated in-place and returned).
    organisms:
        Organisms detected in this tick.
    tick:
        Current simulation tick.
    rules:
        Loaded rules dictionary.
    rng:
        Optional seeded random instance.

    Returns
    -------
    Grid
        Updated grid (same object, modified in-place).
    """
    if rng is None:
        rng = random.Random()

    tox_memory_ticks: int = int(rules.get("toxicMemoryTicks", 30))
    d3_weight: float = float(rules.get("d3GuidanceWeight", 0.30))
    min_size: int = int(rules.get("minimumOrganismSize", 4))

    for org in organisms:
        if org.size < min_size:
            continue  # tiny clusters get no D3

        _handle_food(grid, org)
        _handle_toxic(grid, org, tick, tox_memory_ticks)
        _decay_bad_zones(org, tick)
        _apply_steering(grid, org, tick, d3_weight, rng, rules)

    return grid


# ---------------------------------------------------------------------------
# Food handling
# ---------------------------------------------------------------------------

def _handle_food(grid: Grid, org: Organism) -> None:
    """Convert food cells adjacent to organism cells into Live cells."""
    new_live: set[tuple[int, int]] = set()
    for cx, cy in list(org.cells):
        for dx, dy in _NEIGHBOR_OFFSETS:
            nx, ny = cx + dx, cy + dy
            if grid.get(nx, ny) == CellType.FOOD:
                grid.set(nx, ny, CellType.LIVE)
                new_live.add((nx, ny))
    org.cells.update(new_live)


# ---------------------------------------------------------------------------
# Toxic handling
# ---------------------------------------------------------------------------

def _handle_toxic(
    grid: Grid, org: Organism, tick: int, memory_ticks: int
) -> None:
    """Record bad-zone memory when the organism touches Toxic cells."""
    for cx, cy in list(org.cells):
        for dx, dy in _NEIGHBOR_OFFSETS:
            nx, ny = cx + dx, cy + dy
            if grid.get(nx, ny) == CellType.TOXIC:
                org.bad_zones[(nx, ny)] = tick + memory_ticks


def _decay_bad_zones(org: Organism, tick: int) -> None:
    """Remove expired bad-zone entries."""
    expired = [pos for pos, exp in org.bad_zones.items() if exp <= tick]
    for pos in expired:
        del org.bad_zones[pos]


# ---------------------------------------------------------------------------
# Gentle steering
# ---------------------------------------------------------------------------

def _apply_steering(
    grid: Grid,
    org: Organism,
    tick: int,
    d3_weight: float,
    rng: random.Random,
    rules: dict[str, Any],
) -> None:
    """Gently bias the organism's growth direction.

    D3 may only bias candidate boundary-cell births — it does not
    teleport or directly move the cluster.  Candidate cells on the
    organism boundary are scored and, with probability d3_weight, the
    highest-scoring candidate is activated as Live.
    """
    if not org.cells:
        return

    # Collect empty boundary positions (adjacent to organism, not already Live)
    candidates: list[tuple[int, int]] = []
    for cx, cy in org.cells:
        for dx, dy in _NEIGHBOR_OFFSETS:
            nx, ny = cx + dx, cy + dy
            if grid.get(nx, ny) == CellType.EMPTY:
                candidates.append((nx, ny))

    if not candidates:
        return

    # Only act with probability d3_weight (keep D2 dominant)
    if rng.random() > d3_weight:
        return

    # Score each candidate
    food_positions = _nearby_food(grid, org)
    scored = [
        (_score_candidate(nx, ny, org, food_positions, grid), (nx, ny))
        for (nx, ny) in candidates
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best_pos = scored[0]

    # Only apply if the best score is actually positive (beneficial direction)
    if best_score > 0:
        bx, by = best_pos
        grid.set(bx, by, CellType.LIVE)
        org.cells.add(best_pos)


def _score_candidate(
    cx: int,
    cy: int,
    org: Organism,
    food_positions: list[tuple[int, int]],
    grid: Grid,
) -> float:
    """Score a candidate growth cell.

    Positive score: toward food.
    Negative score: toward bad zones (toxic memory).
    """
    score = 0.0
    for fx, fy in food_positions:
        dist = abs(cx - fx) + abs(cy - fy)
        if dist == 0:
            score += 10.0
        else:
            score += 1.0 / dist

    for (bx, by) in org.bad_zones:
        dist = abs(cx - bx) + abs(cy - by)
        if dist == 0:
            score -= 5.0
        else:
            score -= 0.5 / dist

    return score


def _nearby_food(
    grid: Grid, org: Organism, search_radius: int = 10
) -> list[tuple[int, int]]:
    """Return food cell positions within search_radius of the organism centroid."""
    cx, cy = org.centroid()
    food: list[tuple[int, int]] = []
    r = search_radius
    for y in range(max(0, int(cy) - r), min(grid.height, int(cy) + r + 1)):
        for x in range(max(0, int(cx) - r), min(grid.width, int(cx) + r + 1)):
            if grid.get(x, y) == CellType.FOOD:
                food.append((x, y))
    return food
