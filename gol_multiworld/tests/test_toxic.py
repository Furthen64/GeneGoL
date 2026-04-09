"""Tests for toxic-cell lifecycle and clustered spawning."""

from __future__ import annotations

from collections import deque

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.d2_update import d2_update
from gol_multiworld.sim.grid import Grid


RULES = {
    "minimumOrganismSize": 4,
    "d3GuidanceWeight": 0.30,
    "caWeight": 0.70,
    "foodScarcity": 0.02,
    "foodSpoilChance": 0.10,
    "toxicMemoryTicks": 30,
    "toxicSpawnClusters": {
        "countRange": [3, 6],
        "sizeRange": [2, 5],
    },
    "states": ["Empty", "Live", "Food", "Wall", "Toxic"],
    "liveCell": {"surviveIfVisibleLiveNeighborsIn": [2, 3]},
    "emptyCell": {"bornIfVisibleLiveNeighborsIn": [3]},
    "foodCell": {"staticUntilConsumedByD3": True},
    "toxicCell": {"static": True, "emitAvoidSignalOnContact": True},
    "wallCell": {"static": True, "blocksVisibilityCompletely": True},
}

_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),           (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
]


class _AlwaysSpoil:
    def random(self) -> float:
        return 0.0


class _NeverSpoil:
    def random(self) -> float:
        return 1.0


def test_food_can_spoil_into_toxic() -> None:
    grid = Grid(8, 8)
    grid.set(4, 4, CellType.FOOD)

    updated = d2_update(grid, RULES, _AlwaysSpoil())

    assert updated.get(4, 4) == CellType.TOXIC


def test_food_stays_food_when_spoil_does_not_trigger() -> None:
    grid = Grid(8, 8)
    grid.set(4, 4, CellType.FOOD)

    updated = d2_update(grid, RULES, _NeverSpoil())

    assert updated.get(4, 4) == CellType.FOOD


def test_randomize_spawns_toxic_in_clusters() -> None:
    grid = Grid(30, 30)

    grid.randomize(RULES, seed=123)

    toxic_cells = {
        (x, y)
        for y in range(grid.height)
        for x in range(grid.width)
        if grid.get(x, y) == CellType.TOXIC
    }
    components = _connected_components(toxic_cells)

    assert 3 <= len(components) <= 6
    assert all(2 <= len(component) <= 5 for component in components)


def _connected_components(
    cells: set[tuple[int, int]]
) -> list[set[tuple[int, int]]]:
    remaining = set(cells)
    components: list[set[tuple[int, int]]] = []

    while remaining:
        start = remaining.pop()
        component = {start}
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            x, y = queue.popleft()
            for dx, dy in _OFFSETS:
                neighbor = (x + dx, y + dy)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)

        components.append(component)

    return components