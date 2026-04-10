"""Layer registry and state containers for the simulation core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from gol_multiworld.sim.cell_types import CellType


class LayerId(IntEnum):
    """Stable layer IDs used by simulation, renderer, and UI queries."""

    BASE_TILES = 1
    RESOURCES = 2
    ORGANISMS = 3
    GENES = 4


class BaseTile(IntEnum):
    """Substrate state for the base tile layer."""

    DEAD_SUBSTRATE = 0
    LIVE_SUBSTRATE = 1


class ResourceType(IntEnum):
    """Typed resources that live above base substrate."""

    NONE = 0
    FOOD = 1
    TOXIN = 2
    WALL = 3


@dataclass
class LayerState:
    """Container for independent simulation layers.

    The mixed-board legacy representation is intentionally not stored here.
    Use ``LegacyBoardAdapter`` for migration paths that still expect a single board.
    """

    width: int
    height: int
    baseTilesGrid: list[list[int]] = field(init=False)
    resourceGrid: list[list[int]] = field(init=False)
    organismGrid: list[list[int]] = field(init=False)
    geneStore: dict[int, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.baseTilesGrid = [
            [BaseTile.DEAD_SUBSTRATE] * self.width for _ in range(self.height)
        ]
        self.resourceGrid = [
            [ResourceType.NONE] * self.width for _ in range(self.height)
        ]
        self.organismGrid = [[0] * self.width for _ in range(self.height)]

    def clone(self) -> "LayerState":
        clone = LayerState(self.width, self.height)
        clone.baseTilesGrid = [row[:] for row in self.baseTilesGrid]
        clone.resourceGrid = [row[:] for row in self.resourceGrid]
        clone.organismGrid = [row[:] for row in self.organismGrid]
        clone.geneStore = dict(self.geneStore)
        return clone


class LegacyBoardAdapter:
    """Compatibility adapter exposing classic CellType board operations."""

    def __init__(self, layers: LayerState) -> None:
        self.layers = layers

    def get(self, x: int, y: int) -> int:
        if not self._in_bounds(x, y):
            return CellType.EMPTY

        resource = self.layers.resourceGrid[y][x]
        if resource == ResourceType.WALL:
            return CellType.WALL
        if resource == ResourceType.TOXIN:
            return CellType.TOXIC
        if resource == ResourceType.FOOD:
            return CellType.FOOD

        if self.layers.organismGrid[y][x] != 0:
            return CellType.LIVE
        if self.layers.baseTilesGrid[y][x] == BaseTile.LIVE_SUBSTRATE:
            return CellType.LIVE
        return CellType.EMPTY

    def set(self, x: int, y: int, value: int) -> None:
        if not self._in_bounds(x, y):
            return
        if (
            self.layers.resourceGrid[y][x] == ResourceType.WALL
            and value != CellType.WALL
        ):
            return

        if value == CellType.WALL:
            self.layers.resourceGrid[y][x] = ResourceType.WALL
            self.layers.organismGrid[y][x] = 0
            self.layers.baseTilesGrid[y][x] = BaseTile.DEAD_SUBSTRATE
            return

        if value == CellType.TOXIC:
            self.layers.resourceGrid[y][x] = ResourceType.TOXIN
            self.layers.organismGrid[y][x] = 0
            self.layers.baseTilesGrid[y][x] = BaseTile.DEAD_SUBSTRATE
            return

        if value == CellType.FOOD:
            self.layers.resourceGrid[y][x] = ResourceType.FOOD
            self.layers.organismGrid[y][x] = 0
            self.layers.baseTilesGrid[y][x] = BaseTile.DEAD_SUBSTRATE
            return

        if value == CellType.LIVE:
            self.layers.resourceGrid[y][x] = ResourceType.NONE
            self.layers.organismGrid[y][x] = -1
            self.layers.baseTilesGrid[y][x] = BaseTile.LIVE_SUBSTRATE
            return

        # EMPTY
        self.layers.resourceGrid[y][x] = ResourceType.NONE
        self.layers.organismGrid[y][x] = 0
        self.layers.baseTilesGrid[y][x] = BaseTile.DEAD_SUBSTRATE

    def as_mixed_board(self) -> list[list[int]]:
        return [
            [self.get(x, y) for x in range(self.layers.width)]
            for y in range(self.layers.height)
        ]

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.layers.width and 0 <= y < self.layers.height
