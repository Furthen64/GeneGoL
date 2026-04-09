"""D3 controller: food consumption, toxic memory, and gentle steering."""

from __future__ import annotations

import random
from typing import Any

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.debug_trace import (
    BirthCauseTracer,
    D3_FOOD_CONVERSION,
    D3_GUIDED_GROWTH,
    is_adjacent_to_organism_boundary,
)
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.organism_detection import Organism

# 8-connected offsets
_NEIGHBOR_OFFSETS: list[tuple[int, int]] = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
]

# Steering scoring constants (positive = attractive, negative = repulsive)
_FOOD_DIRECT_SCORE = 10.0    # Score when candidate IS a food cell
_FOOD_INVERSE_SCORE = 1.0    # Numerator for 1/dist food attraction
_TOXIC_DIRECT_PENALTY = 5.0  # Penalty when candidate is on a bad-zone cell
_TOXIC_INVERSE_PENALTY = 0.5 # Numerator for 1/dist toxic repulsion

# Default food search radius in cells around the organism centroid
_DEFAULT_FOOD_SEARCH_RADIUS = 10


def d3_tick(
    grid: Grid,
    organisms: list[Organism],
    tick: int,
    rules: dict[str, Any],
    rng: random.Random | None = None,
    debugger: BirthCauseTracer | None = None,
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
    explicit_max_writes = rules.get("d3MaxWritesPerOrganismPerTick")

    for org in organisms:
        if org.size < min_size:
            continue  # tiny clusters get no D3

        food_writes = _handle_food(grid, org, debugger)
        _handle_toxic(grid, org, tick, tox_memory_ticks)
        _decay_bad_zones(org, tick)
        guided_write = _apply_steering(grid, org, tick, d3_weight, rng, rules, debugger)
        if debugger is not None:
            allowed_writes = len(food_writes) + 1
            if explicit_max_writes is not None:
                allowed_writes = min(allowed_writes, int(explicit_max_writes))
            debugger.set_d3_write_limit(org.organism_id, allowed_writes)

    if debugger is not None:
        debugger.check_d3_write_limits()

    return grid


# ---------------------------------------------------------------------------
# Food handling
# ---------------------------------------------------------------------------

def _handle_food(
    grid: Grid,
    org: Organism,
    debugger: BirthCauseTracer | None = None,
) -> set[tuple[int, int]]:
    """Convert food cells adjacent to organism cells into Live cells."""
    new_live: set[tuple[int, int]] = set()
    for cx, cy in list(org.cells):
        for dx, dy in _NEIGHBOR_OFFSETS:
            nx, ny = cx + dx, cy + dy
            if grid.get(nx, ny) == CellType.FOOD:
                if debugger is not None:
                    debugger.record_transition(
                        grid,
                        nx,
                        ny,
                        CellType.FOOD,
                        CellType.LIVE,
                        cause=D3_FOOD_CONVERSION,
                        phase="D3",
                        source_organism_id=org.organism_id,
                        near_organism_boundary=is_adjacent_to_organism_boundary(
                            org.cells, (nx, ny)
                        ),
                    )
                grid.set(nx, ny, CellType.LIVE)
                new_live.add((nx, ny))
    org.cells.update(new_live)
    return new_live


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
    debugger: BirthCauseTracer | None = None,
) -> tuple[int, int] | None:
    """Gently bias the organism's growth direction.

    D3 may only bias candidate boundary-cell births — it does not
    teleport or directly move the cluster.  Candidate cells on the
    organism boundary are scored and, with probability d3_weight, the
    highest-scoring candidate is activated as Live.
    """
    if not org.cells:
        return None

    # Collect empty boundary positions (adjacent to organism, not already Live)
    candidates: set[tuple[int, int]] = set()
    for cx, cy in org.cells:
        for dx, dy in _NEIGHBOR_OFFSETS:
            nx, ny = cx + dx, cy + dy
            if grid.get(nx, ny) == CellType.EMPTY:
                candidates.add((nx, ny))

    if not candidates:
        return None

    # Only act with probability d3_weight (keep D2 dominant)
    if rng.random() > d3_weight:
        return None

    # Score each candidate
    food_positions = _nearby_food(grid, org)
    scored = [
        (_score_candidate(nx, ny, org, food_positions, grid), (nx, ny))
        for (nx, ny) in sorted(candidates, key=lambda pos: (pos[1], pos[0]))
    ]
    scored.sort(key=lambda item: (-item[0], item[1][1], item[1][0]))
    best_score, best_pos = scored[0]

    # Only apply if the best score is actually positive (beneficial direction)
    if best_score > 0:
        bx, by = best_pos
        if debugger is not None:
            debugger.record_transition(
                grid,
                bx,
                by,
                CellType.EMPTY,
                CellType.LIVE,
                cause=D3_GUIDED_GROWTH,
                phase="D3",
                source_organism_id=org.organism_id,
                near_organism_boundary=is_adjacent_to_organism_boundary(
                    org.cells, best_pos
                ),
            )
        grid.set(bx, by, CellType.LIVE)
        org.cells.add(best_pos)
        return best_pos

    return None


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
            score += _FOOD_DIRECT_SCORE
        else:
            score += _FOOD_INVERSE_SCORE / dist

    for (bx, by) in org.bad_zones:
        dist = abs(cx - bx) + abs(cy - by)
        if dist == 0:
            score -= _TOXIC_DIRECT_PENALTY
        else:
            score -= _TOXIC_INVERSE_PENALTY / dist

    return score


def _nearby_food(
    grid: Grid, org: Organism, search_radius: int = _DEFAULT_FOOD_SEARCH_RADIUS
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
