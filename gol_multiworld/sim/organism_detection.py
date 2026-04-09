"""Organism detection (D3 layer) using BFS over connected Live cells."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.genes import Gene
from gol_multiworld.sim.grid import Grid

# 8-connected offsets
_NEIGHBOR_OFFSETS: list[tuple[int, int]] = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
]


@dataclass
class Organism:
    """Metadata for a single detected organism."""

    organism_id: int
    cells: set[tuple[int, int]]
    birth_tick: int
    last_seen_tick: int
    gene: Gene = field(default_factory=Gene)
    bad_zones: dict[tuple[int, int], int] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.cells)

    def centroid(self) -> tuple[float, float]:
        xs = [c[0] for c in self.cells]
        ys = [c[1] for c in self.cells]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    def bounding_box(self) -> tuple[int, int, int, int]:
        """Return (min_x, min_y, max_x, max_y)."""
        xs = [c[0] for c in self.cells]
        ys = [c[1] for c in self.cells]
        return min(xs), min(ys), max(xs), max(ys)

    def survival_time(self, current_tick: int) -> int:
        return current_tick - self.birth_tick


def detect_organisms(
    grid: Grid,
    tick: int,
    previous: list[Organism],
    rules: dict[str, Any],
) -> list[Organism]:
    """Detect all organisms in the current grid.

    An organism is an 8-connected cluster of Live cells with size >=
    ``minimumOrganismSize``.  Clusters smaller than that are ignored.

    Previously detected organisms are matched by cell-overlap to
    preserve IDs, birth ticks, genes, and bad-zone memory.

    Parameters
    ----------
    grid:
        Current grid state.
    tick:
        Current simulation tick.
    previous:
        Organism list from the previous tick.
    rules:
        Loaded rules dictionary.

    Returns
    -------
    list[Organism]
        Newly detected organisms for this tick.
    """
    min_size: int = rules.get("minimumOrganismSize", 4)

    # BFS to find all connected Live clusters
    visited: set[tuple[int, int]] = set()
    clusters: list[set[tuple[int, int]]] = []

    for y in range(grid.height):
        for x in range(grid.width):
            if grid.get(x, y) == CellType.LIVE and (x, y) not in visited:
                cluster = _bfs(grid, x, y, visited)
                if len(cluster) >= min_size:
                    clusters.append(cluster)

    # Build a map from cell → previous organism for identity continuity
    cell_to_prev: dict[tuple[int, int], Organism] = {}
    for org in previous:
        for cell in org.cells:
            cell_to_prev[cell] = org

    # Assign IDs: reuse old ID if majority of cells overlap with a prior organism
    used_ids: set[int] = set()
    next_id: int = _next_free_id(previous)
    result: list[Organism] = []

    for cluster in clusters:
        # Vote for the best matching previous organism
        votes: dict[int, int] = {}
        for cell in cluster:
            prev_org = cell_to_prev.get(cell)
            if prev_org is not None:
                votes[prev_org.organism_id] = votes.get(prev_org.organism_id, 0) + 1

        matched_org: Organism | None = None
        if votes:
            best_id = max(votes, key=lambda k: votes[k])
            if best_id not in used_ids:
                matched_org = next(
                    (o for o in previous if o.organism_id == best_id), None
                )

        if matched_org is not None:
            oid = matched_org.organism_id
            birth = matched_org.birth_tick
            gene = matched_org.gene
            bad_zones = matched_org.bad_zones
        else:
            oid = next_id
            next_id += 1
            birth = tick
            gene = Gene()
            bad_zones = {}

        used_ids.add(oid)
        result.append(
            Organism(
                organism_id=oid,
                cells=cluster,
                birth_tick=birth,
                last_seen_tick=tick,
                gene=gene,
                bad_zones=bad_zones,
            )
        )

    return result


def _bfs(
    grid: Grid,
    start_x: int,
    start_y: int,
    visited: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    """BFS over 8-connected Live cells starting at (start_x, start_y)."""
    cluster: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    queue.append((start_x, start_y))
    visited.add((start_x, start_y))

    while queue:
        x, y = queue.popleft()
        cluster.add((x, y))
        for dx, dy in _NEIGHBOR_OFFSETS:
            nx, ny = x + dx, y + dy
            if (
                (nx, ny) not in visited
                and 0 <= nx < grid.width
                and 0 <= ny < grid.height
                and grid.get(nx, ny) == CellType.LIVE
            ):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return cluster


def _next_free_id(previous: list[Organism]) -> int:
    if not previous:
        return 1
    return max(o.organism_id for o in previous) + 1
