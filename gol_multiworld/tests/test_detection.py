"""Tests for organism detection (D3 BFS/connected-component logic)."""

from __future__ import annotations

import pytest

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.organism_detection import Organism, detect_organisms

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


def _grid_with_cluster(cells: list[tuple[int, int]], size: int = 20) -> Grid:
    grid = Grid(size, size)
    for x, y in cells:
        grid.set(x, y, CellType.LIVE)
    return grid


def test_empty_grid_has_no_organisms() -> None:
    grid = Grid(10, 10)
    orgs = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    assert orgs == []


def test_small_cluster_not_detected() -> None:
    # 3 live cells — below minimum size of 4
    grid = _grid_with_cluster([(5, 5), (5, 6), (5, 7)])
    orgs = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    assert orgs == []


def test_cluster_of_four_is_detected() -> None:
    cells = [(5, 5), (5, 6), (6, 5), (6, 6)]
    grid = _grid_with_cluster(cells)
    orgs = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    assert len(orgs) == 1
    assert orgs[0].size == 4


def test_two_separate_clusters_detected() -> None:
    cells_a = [(1, 1), (1, 2), (2, 1), (2, 2)]
    cells_b = [(10, 10), (10, 11), (11, 10), (11, 11)]
    grid = _grid_with_cluster(cells_a + cells_b)
    orgs = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    assert len(orgs) == 2


def test_diagonal_connectivity_is_used() -> None:
    # Diagonal chain — should be one connected component
    cells = [(0, 0), (1, 1), (2, 2), (3, 3)]
    grid = _grid_with_cluster(cells)
    orgs = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    assert len(orgs) == 1
    assert orgs[0].size == 4


def test_organism_id_preserved_across_ticks() -> None:
    cells = [(5, 5), (5, 6), (6, 5), (6, 6)]
    grid = _grid_with_cluster(cells)
    orgs_tick0 = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    assert len(orgs_tick0) == 1
    oid = orgs_tick0[0].organism_id

    orgs_tick1 = detect_organisms(grid, tick=1, previous=orgs_tick0, rules=RULES)
    assert len(orgs_tick1) == 1
    assert orgs_tick1[0].organism_id == oid


def test_birth_tick_is_recorded() -> None:
    cells = [(5, 5), (5, 6), (6, 5), (6, 6)]
    grid = _grid_with_cluster(cells)
    orgs = detect_organisms(grid, tick=7, previous=[], rules=RULES)
    assert orgs[0].birth_tick == 7


def test_survival_time_increases() -> None:
    cells = [(5, 5), (5, 6), (6, 5), (6, 6)]
    grid = _grid_with_cluster(cells)
    orgs0 = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    orgs5 = detect_organisms(grid, tick=5, previous=orgs0, rules=RULES)
    assert orgs5[0].survival_time(5) == 5


def test_travel_distance_stays_zero_when_centroid_does_not_move() -> None:
    cells = [(5, 5), (5, 6), (6, 5), (6, 6)]
    grid = _grid_with_cluster(cells)
    orgs0 = detect_organisms(grid, tick=0, previous=[], rules=RULES)

    orgs1 = detect_organisms(grid, tick=1, previous=orgs0, rules=RULES)

    assert orgs1[0].travel_distance == pytest.approx(0.0)


def test_travel_distance_accumulates_centroid_motion() -> None:
    grid0 = _grid_with_cluster([(5, 5), (5, 6), (6, 5), (6, 6)])
    orgs0 = detect_organisms(grid0, tick=0, previous=[], rules=RULES)

    grid1 = _grid_with_cluster([(6, 5), (6, 6), (7, 5), (7, 6)])
    orgs1 = detect_organisms(grid1, tick=1, previous=orgs0, rules=RULES)

    assert orgs1[0].organism_id == orgs0[0].organism_id
    assert orgs1[0].travel_distance == pytest.approx(1.0)
    assert orgs1[0].fitness(1) == pytest.approx(1.0)


def test_new_organism_starts_with_zero_travel_distance() -> None:
    grid0 = _grid_with_cluster([(1, 1), (1, 2), (2, 1), (2, 2)])
    orgs0 = detect_organisms(grid0, tick=0, previous=[], rules=RULES)

    grid1 = _grid_with_cluster([(10, 10), (10, 11), (11, 10), (11, 11)])
    orgs1 = detect_organisms(grid1, tick=1, previous=orgs0, rules=RULES)

    assert orgs1[0].travel_distance == pytest.approx(0.0)
    assert orgs1[0].fitness(1) == pytest.approx(0.0)


def test_bounding_box_correct() -> None:
    # Diagonal chain (8-connected): (2,3)→(3,4)→(4,5) plus (4,4)
    # Bounding box should be x: 2..4, y: 3..5
    cells = [(2, 3), (3, 4), (4, 5), (4, 4)]
    grid = _grid_with_cluster(cells)
    orgs = detect_organisms(grid, tick=0, previous=[], rules=RULES)
    assert len(orgs) == 1
    min_x, min_y, max_x, max_y = orgs[0].bounding_box()
    assert min_x == 2
    assert min_y == 3
    assert max_x == 4
    assert max_y == 5


def test_cluster_smaller_than_min_size_custom_rule() -> None:
    custom_rules = dict(RULES)
    custom_rules["minimumOrganismSize"] = 6
    cells = [(5, 5), (5, 6), (6, 5), (6, 6)]  # only 4 cells
    grid = _grid_with_cluster(cells)
    orgs = detect_organisms(grid, tick=0, previous=[], rules=custom_rules)
    assert orgs == []


def test_new_organism_gets_new_id() -> None:
    cells_a = [(1, 1), (1, 2), (2, 1), (2, 2)]
    grid_a = _grid_with_cluster(cells_a)
    orgs0 = detect_organisms(grid_a, tick=0, previous=[], rules=RULES)

    cells_b = [(10, 10), (10, 11), (11, 10), (11, 11)]
    grid_b = _grid_with_cluster(cells_b)
    orgs1 = detect_organisms(grid_b, tick=1, previous=orgs0, rules=RULES)

    ids0 = {o.organism_id for o in orgs0}
    ids1 = {o.organism_id for o in orgs1}
    assert ids0.isdisjoint(ids1), "New organism should have a fresh ID"
