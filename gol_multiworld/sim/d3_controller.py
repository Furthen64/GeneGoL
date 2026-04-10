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
from gol_multiworld.sim.layers import ResourceType
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
_LOCAL_ENV_RADIUS = 2


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

        phenotype = org.gene.derive_phenotype()
        org.phenotype = phenotype
        local_env = _sample_local_environment(grid, org, _LOCAL_ENV_RADIUS)

        food_writes = _handle_food(grid, org, phenotype.resource_appetite, debugger)
        _handle_toxic(grid, org, tick, tox_memory_ticks)
        _decay_bad_zones(org, tick, phenotype.decay_tolerance)
        guided_write = _apply_steering(
            grid,
            org,
            tick,
            d3_weight,
            rng,
            rules,
            local_env,
            debugger,
        )
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
    appetite: float,
    debugger: BirthCauseTracer | None = None,
) -> set[tuple[int, int]]:
    """Convert food cells adjacent to organism cells into Live cells."""
    max_conversions = max(1, int(1 + appetite * 3))
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
                if len(new_live) >= max_conversions:
                    org.cells.update(new_live)
                    return new_live
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


def _decay_bad_zones(org: Organism, tick: int, decay_tolerance: float) -> None:
    """Remove expired bad-zone entries."""
    grace_ticks = int(1 + decay_tolerance * 5)
    expired = [
        pos for pos, exp in org.bad_zones.items() if exp + grace_ticks <= tick
    ]
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
    local_env: dict[str, float],
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
    action_weight = d3_weight * (0.25 + (0.75 * org.phenotype.guidance_strength))
    if rng.random() > action_weight:
        return None

    # Score each candidate
    food_positions = _nearby_food(grid, org)
    scored = [
        (
            _score_candidate(
                nx,
                ny,
                org,
                food_positions,
                grid,
                local_env,
            ),
            (nx, ny),
        )
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
    local_env: dict[str, float],
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
        resistance = org.phenotype.toxin_resistance if org.phenotype else 0.0
        resistance_factor = max(0.1, 1.0 - resistance)
        if dist == 0:
            score -= _TOXIC_DIRECT_PENALTY * resistance_factor
        else:
            score -= (_TOXIC_INVERSE_PENALTY / dist) * resistance_factor

    wall_density = local_env.get("wall_density", 0.0)
    toxin_density = local_env.get("toxin_density", 0.0)
    food_density = local_env.get("food_density", 0.0)
    appetite = org.phenotype.resource_appetite if org.phenotype else 0.5
    resistance = org.phenotype.toxin_resistance if org.phenotype else 0.0
    score += food_density * (0.5 + appetite)
    score -= toxin_density * (1.0 - resistance)
    score -= wall_density * 0.25

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


def _sample_local_environment(
    grid: Grid,
    org: Organism,
    radius: int,
) -> dict[str, float]:
    """Read environment-layer values around the organism centroid."""
    cx, cy = org.centroid()
    start_x = max(0, int(cx) - radius)
    end_x = min(grid.width - 1, int(cx) + radius)
    start_y = max(0, int(cy) - radius)
    end_y = min(grid.height - 1, int(cy) + radius)
    sample_count = max(1, (end_x - start_x + 1) * (end_y - start_y + 1))

    layer_state = grid.get_layer_state()
    food = 0
    toxin = 0
    wall = 0
    for y in range(start_y, end_y + 1):
        for x in range(start_x, end_x + 1):
            value = layer_state.resourceGrid[y][x]
            if value == ResourceType.FOOD:
                food += 1
            elif value == ResourceType.TOXIN:
                toxin += 1
            elif value == ResourceType.WALL:
                wall += 1

    return {
        "food_density": food / sample_count,
        "toxin_density": toxin / sample_count,
        "wall_density": wall / sample_count,
    }
