"""Grid representation and random-world generation."""

from __future__ import annotations

import random
from typing import Any

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.layers import LayerId, LayerState, LegacyBoardAdapter


class Grid:
    """2D grid facade backed by explicit layer containers."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.layers = LayerState(width, height)
        self._legacy_board = LegacyBoardAdapter(self.layers)

    @property
    def _cells(self) -> list[list[int]]:
        """Legacy mixed-board snapshot for compatibility with older code paths."""
        return self._legacy_board.as_mixed_board()

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    def get(self, x: int, y: int) -> int:
        """Return the cell type at (x, y) or EMPTY if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._legacy_board.get(x, y)
        return CellType.EMPTY

    def set(self, x: int, y: int, value: int) -> None:
        """Set the cell type at (x, y). Ignores out-of-bounds writes."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._legacy_board.set(x, y, value)

    def clone(self) -> "Grid":
        """Return a deep copy of this grid (used for double-buffering)."""
        new_grid = Grid(self.width, self.height)
        new_grid.layers = self.layers.clone()
        new_grid._legacy_board = LegacyBoardAdapter(new_grid.layers)
        return new_grid


    # ------------------------------------------------------------------
    # Layer queries
    # ------------------------------------------------------------------

    def get_layer_state(self) -> LayerState:
        """Return full layer state object for independent subsystem queries."""
        return self.layers

    def get_layer_grid(self, layer_id: LayerId) -> Any:
        """Return a specific layer container by registered layer id."""
        if layer_id == LayerId.BASE_TILES:
            return self.layers.baseTilesGrid
        if layer_id == LayerId.RESOURCES:
            return self.layers.resourceGrid
        if layer_id == LayerId.ORGANISMS:
            return self.layers.organismGrid
        if layer_id == LayerId.GENES:
            return self.layers.geneStore
        raise ValueError(f"Unknown layer id: {layer_id}")

    def set_organism_cell(self, x: int, y: int, organism_id: int) -> None:
        """Set organism occupancy in the organism layer only."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.layers.organismGrid[y][x] = organism_id

    def set_gene_store(self, gene_store: dict[int, Any]) -> None:
        """Replace gene layer data (indexed by organism id)."""
        self.layers.geneStore = dict(gene_store)

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
                if self.get(x, y) == CellType.WALL:
                    continue
                r = rng.random()
                if r < food_density:
                    self.set(x, y, CellType.FOOD)
                elif r < food_density + live_density:
                    self.set(x, y, CellType.LIVE)
                else:
                    self.set(x, y, CellType.EMPTY)

        self._seed_toxic_clusters(rng, rules)

    def clear(self) -> None:
        """Reset all cells to EMPTY."""
        for y in range(self.height):
            for x in range(self.width):
                self.set(x, y, CellType.EMPTY)

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
                self.set(x, y, CellType.TOXIC)

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
        if self.get(x, y) == CellType.WALL or (x, y) in occupied:
            return False
        return all((nx, ny) not in occupied for nx, ny in _neighbor_positions(x, y))

    def _can_extend_toxic(
        self,
        x: int,
        y: int,
        cluster: set[tuple[int, int]],
        occupied: set[tuple[int, int]],
    ) -> bool:
        if self.get(x, y) == CellType.WALL or (x, y) in occupied or (x, y) in cluster:
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
