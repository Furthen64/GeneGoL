"""Tests for birth-cause tracing and invariants."""

from __future__ import annotations

import copy
import random

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.d2_update import d2_update
from gol_multiworld.sim.d3_controller import d3_tick
from gol_multiworld.sim.debug_trace import (
    BirthCauseTracer,
    D2_BIRTH,
    D3_FOOD_CONVERSION,
    D3_GUIDED_GROWTH,
)
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.organism_detection import detect_organisms

RULES = {
    "minimumOrganismSize": 4,
    "d3GuidanceWeight": 0.30,
    "caWeight": 0.70,
    "foodScarcity": 0.02,
    "toxicMemoryTicks": 30,
    "states": ["Empty", "Live", "Food", "Wall", "Toxic"],
    "liveCell": {"surviveIfVisibleLiveNeighborsIn": [2, 3]},
    "emptyCell": {"bornIfVisibleLiveNeighborsIn": [3]},
    "foodCell": {"staticUntilConsumedByD3": True},
    "toxicCell": {"static": True, "emitAvoidSignalOnContact": True},
    "wallCell": {"static": True, "blocksVisibilityCompletely": True},
}


def _rules(**overrides: object) -> dict[str, object]:
    rules = copy.deepcopy(RULES)
    rules.update(overrides)
    return rules


def test_d2_birth_is_logged_with_neighbor_count() -> None:
    grid = Grid(8, 8)
    for pos in [(1, 1), (1, 2), (2, 1)]:
        grid.set(*pos, CellType.LIVE)

    tracer = BirthCauseTracer(enabled=True)
    tracer.begin_tick(0, grid)
    updated = d2_update(grid, _rules(), random.Random(0), tracer)
    tracer.finalize_tick(updated)

    record = tracer.live_births[(2, 2)]
    assert record.tick == 0
    assert record.cause == D2_BIRTH
    assert record.phase == "D2"
    assert record.visible_live_neighbor_count == 3
    assert tracer.violation_count == 0


def test_d3_guided_growth_is_logged() -> None:
    grid = Grid(16, 16)
    for pos in [(5, 5), (5, 6), (6, 5), (6, 6)]:
        grid.set(*pos, CellType.LIVE)
    grid.set(9, 5, CellType.FOOD)

    rules = _rules(d3GuidanceWeight=1.0)
    organisms = detect_organisms(grid, tick=0, previous=[], rules=rules)
    organisms[0].gene.guidance_locus = 1.0
    tracer = BirthCauseTracer(enabled=True)
    tracer.begin_tick(0, grid)
    updated = d3_tick(grid, organisms, tick=0, rules=rules, rng=random.Random(0), debugger=tracer)
    tracer.finalize_tick(updated)

    guided_records = [
        birth
        for birth in tracer.live_births.values()
        if birth.cause == D3_GUIDED_GROWTH
    ]
    assert guided_records, "Expected one D3 guided growth birth record"
    record = guided_records[0]
    assert record.cause == D3_GUIDED_GROWTH
    assert record.phase == "D3"
    assert record.source_organism_id == organisms[0].organism_id
    assert record.near_organism_boundary is True
    assert tracer.violation_count == 0


def test_new_organism_logs_preexisting_and_d2_birth_cells() -> None:
    grid = Grid(8, 8)
    for pos in [(1, 1), (1, 2), (2, 1)]:
        grid.set(*pos, CellType.LIVE)

    tracer = BirthCauseTracer(enabled=True)
    tracer.begin_tick(4, grid)
    updated = d2_update(grid, _rules(), random.Random(0), tracer)
    organisms = detect_organisms(updated, tick=4, previous=[], rules=_rules(), debugger=tracer)

    assert len(organisms) == 1
    assert len(tracer.organism_appearances) == 1

    appearance = tracer.organism_appearances[0]
    by_position = {cell.position: cell for cell in appearance.cells}
    assert by_position[(1, 1)].source == "pre-existing live cells"
    assert by_position[(1, 2)].source == "pre-existing live cells"
    assert by_position[(2, 1)].source == "pre-existing live cells"
    assert by_position[(2, 2)].source == "D2 births this tick"
    assert by_position[(2, 2)].cause == D2_BIRTH
    assert tracer.violation_count == 0


def test_unknown_live_cell_is_reported() -> None:
    grid = Grid(8, 8)
    tracer = BirthCauseTracer(enabled=True)

    tracer.begin_tick(2, grid)
    grid.set(3, 3, CellType.LIVE)
    tracer.finalize_tick(grid)

    assert tracer.violation_count == 1
    assert "without recorded cause" in tracer.violations[0]


def test_d3_write_limit_violation_is_reported() -> None:
    grid = Grid(16, 16)
    for pos in [(5, 5), (5, 6), (6, 5), (6, 6)]:
        grid.set(*pos, CellType.LIVE)
    grid.set(7, 5, CellType.FOOD)

    rules = _rules(d3MaxWritesPerOrganismPerTick=0)
    organisms = detect_organisms(grid, tick=0, previous=[], rules=rules)
    tracer = BirthCauseTracer(enabled=True)
    tracer.begin_tick(0, grid)
    d3_tick(grid, organisms, tick=0, rules=rules, rng=random.Random(0), debugger=tracer)

    assert any(
        "more live cells than allowed" in violation for violation in tracer.violations
    )


def test_d3_food_conversion_is_logged() -> None:
    grid = Grid(12, 12)
    for pos in [(4, 4), (4, 5), (5, 4), (5, 5)]:
        grid.set(*pos, CellType.LIVE)
    grid.set(6, 4, CellType.FOOD)

    organisms = detect_organisms(grid, tick=0, previous=[], rules=_rules())
    tracer = BirthCauseTracer(enabled=True)
    tracer.begin_tick(0, grid)
    updated = d3_tick(grid, organisms, tick=0, rules=_rules(), rng=random.Random(0), debugger=tracer)
    tracer.finalize_tick(updated)

    record = tracer.live_births[(6, 4)]
    assert record.cause == D3_FOOD_CONVERSION
    assert record.phase == "D3"
    assert record.source_organism_id == organisms[0].organism_id


def test_toxic_outer_contour_creates_avoidance_memory() -> None:
    grid = Grid(12, 12)
    for pos in [(5, 5), (5, 6), (6, 5), (6, 6)]:
        grid.set(*pos, CellType.LIVE)
    # Top contour (+1 above organism bbox) should be sensed as threat.
    grid.set(5, 4, CellType.TOXIC)

    organisms = detect_organisms(grid, tick=0, previous=[], rules=_rules())
    d3_tick(grid, organisms, tick=0, rules=_rules(toxicMemoryTicks=5), rng=random.Random(0))

    assert (5, 4) in organisms[0].bad_zones
    assert organisms[0].bad_zones[(5, 4)] == 5


def test_toxic_north_biases_guided_growth_southward() -> None:
    grid = Grid(16, 16)
    for pos in [(5, 5), (5, 6), (6, 5), (6, 6)]:
        grid.set(*pos, CellType.LIVE)
    # Toxic directly north of centroid on the +1 contour.
    grid.set(5, 4, CellType.TOXIC)

    rules = _rules(d3GuidanceWeight=1.0, foodScarcity=0.0, toxicMemoryTicks=10)
    organisms = detect_organisms(grid, tick=0, previous=[], rules=rules)
    organisms[0].gene.guidance_locus = 1.0
    d3_tick(grid, organisms, tick=0, rules=rules, rng=random.Random(0))

    # Expected nudge opposite the threat: a southern boundary cell becomes live.
    assert grid.get(5, 7) == CellType.LIVE or grid.get(6, 7) == CellType.LIVE


def test_toxic_east_biases_guided_growth_westward() -> None:
    grid = Grid(16, 16)
    for pos in [(5, 5), (5, 6), (6, 5), (6, 6)]:
        grid.set(*pos, CellType.LIVE)
    # Toxic on +1 contour to the east of centroid.
    grid.set(7, 5, CellType.TOXIC)

    rules = _rules(d3GuidanceWeight=1.0, foodScarcity=0.0, toxicMemoryTicks=10)
    organisms = detect_organisms(grid, tick=0, previous=[], rules=rules)
    organisms[0].gene.guidance_locus = 1.0
    d3_tick(grid, organisms, tick=0, rules=rules, rng=random.Random(0))

    # Expected nudge opposite the threat: a western boundary cell becomes live.
    assert grid.get(4, 5) == CellType.LIVE or grid.get(4, 6) == CellType.LIVE
