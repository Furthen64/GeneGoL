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
            Legacy argument kept for compatibility; toxic cells now spawn in clumps.
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
                if r < food_density:
                    self._cells[y][x] = CellType.FOOD
                elif r < food_density + live_density:
                    self._cells[y][x] = CellType.LIVE
                else:
                    self._cells[y][x] = CellType.EMPTY

        self._seed_toxic_clusters(rng, rules)

    def clear(self) -> None:
        """Reset all cells to EMPTY."""
        for y in range(self.height):
            for x in range(self.width):
                self._cells[y][x] = CellType.EMPTY

    def _seed_toxic_clusters(self, rng: random.Random, rules: dict[str, Any]) -> None:
        toxic_config = rules.get("toxicSpawnClusters", {})
        count_range = toxic_config.get("countRange", [3, 6])
        size_range = toxic_config.get("sizeRange", [2, 5])
        min_count, max_count = int(count_range[0]), int(count_range[1])
        min_size, max_size = int(size_range[0]), int(size_range[1])
        cluster_target = rng.randint(min_count, max_count)
        occupied: set[tuple[int, int]] = set()

        for _ in range(cluster_target):
            cluster = self._build_toxic_cluster(rng, occupied, min_size, max_size)
            if not cluster:
                continue
            occupied.update(cluster)
            for x, y in cluster:
                self._cells[y][x] = CellType.TOXIC

    def _build_toxic_cluster(
        self,
        rng: random.Random,
        occupied: set[tuple[int, int]],
        min_size: int,
        max_size: int,
    ) -> set[tuple[int, int]]:
        for _ in range(40):
            candidates = [
                (x, y)
                for y in range(self.height)
                for x in range(self.width)
                if self._can_seed_toxic(x, y, occupied)
            ]
            if not candidates:
                return set()

            target_size = rng.randint(min_size, max_size)
            cluster = {rng.choice(candidates)}
            frontier = self._cluster_frontier(cluster, occupied)

            while frontier and len(cluster) < target_size:
                nx, ny = rng.choice(tuple(frontier))
                frontier.remove((nx, ny))
                if not self._can_extend_toxic(nx, ny, cluster, occupied):
                    continue
                cluster.add((nx, ny))
                frontier.update(self._cluster_frontier(cluster, occupied))

            if len(cluster) >= min_size:
                return cluster

        return set()

    def _cluster_frontier(
        self,
        cluster: set[tuple[int, int]],
        occupied: set[tuple[int, int]],
    ) -> set[tuple[int, int]]:
        frontier: set[tuple[int, int]] = set()
        for x, y in cluster:
            for nx, ny in _neighbor_positions(x, y):
                if (nx, ny) in cluster or (nx, ny) in occupied:
                    continue
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    frontier.add((nx, ny))
        return frontier

    def _can_seed_toxic(
        self,
        x: int,
        y: int,
        occupied: set[tuple[int, int]],
    ) -> bool:
        if self._cells[y][x] == CellType.WALL or (x, y) in occupied:
            return False
        return all((nx, ny) not in occupied for nx, ny in _neighbor_positions(x, y))

    def _can_extend_toxic(
        self,
        x: int,
        y: int,
        cluster: set[tuple[int, int]],
        occupied: set[tuple[int, int]],
    ) -> bool:
        if self._cells[y][x] == CellType.WALL or (x, y) in occupied or (x, y) in cluster:
            return False
        for nx, ny in _neighbor_positions(x, y):
            if (nx, ny) in occupied and (nx, ny) not in cluster:
                return False
        return True


def _neighbor_positions(x: int, y: int) -> list[tuple[int, int]]:
    return [
        (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
        (x - 1, y),                 (x + 1, y),
        (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
    ]
