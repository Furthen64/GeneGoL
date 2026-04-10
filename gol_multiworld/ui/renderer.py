"""Pygame-ce renderer for the grid and overlays."""

from __future__ import annotations

from typing import Any

import pygame

from gol_multiworld.sim.cell_types import CELL_COLORS, CellType
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.layers import BaseTile, LayerId, LayerState, ResourceType
from gol_multiworld.sim.organism_detection import Organism

# Organism overlay colors
_ORGANISM_CELL_COLOR = CELL_COLORS[CellType.LIVE]
_NON_ORGANISM_CELL_COLOR = (25, 90, 25)
_OVERLAY_BOX_COLOR = (80, 200, 255)
_OVERLAY_TEXT_COLOR = (255, 255, 255)
_OVERLAY_LABEL_BG = (10, 10, 20)
_TINY_CLUSTER_COLOR = (60, 100, 60)

_LINE_SPACING = 2       # Pixels between text lines
_STATUS_PANEL_WIDTH = 220


class Renderer:
    """Handles all drawing operations for the simulation."""

    def __init__(
        self,
        surface: pygame.Surface,
        cell_size: int = 8,
        grid_offset_x: int = 0,
        grid_offset_y: int = 0,
    ) -> None:
        self.surface = surface
        self.cell_size = cell_size
        self.grid_offset_x = grid_offset_x
        self.grid_offset_y = grid_offset_y
        self._font: pygame.font.Font | None = None

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", max(10, self.cell_size))
        return self._font

    # ------------------------------------------------------------------
    # Grid rendering
    # ------------------------------------------------------------------

    def draw_grid(self, grid: Grid, organisms: list[Organism] | None = None) -> None:
        """Draw all cells in the grid."""
        self.draw_layers(
            grid.get_layer_state(),
            [layer_id for layer_id in LayerId],
            organisms=organisms,
        )

    def draw_layers(
        self,
        layer_state: LayerState,
        renderable_layers: list[LayerId],
        organisms: list[Organism] | None = None,
    ) -> None:
        """Draw selected simulation layers in stable layer order."""
        cs = self.cell_size
        ox, oy = self.grid_offset_x, self.grid_offset_y
        organism_cells = {
            cell for org in organisms or [] for cell in org.cells
        }
        renderable = set(renderable_layers)

        for y in range(layer_state.height):
            for x in range(layer_state.width):
                color = CELL_COLORS[CellType.EMPTY]
                if LayerId.BASE_TILES in renderable:
                    base_tile = layer_state.baseTilesGrid[y][x]
                    if base_tile == BaseTile.LIVE_SUBSTRATE:
                        color = _NON_ORGANISM_CELL_COLOR

                if LayerId.RESOURCES in renderable:
                    resource = layer_state.resourceGrid[y][x]
                    if resource == ResourceType.FOOD:
                        color = CELL_COLORS[CellType.FOOD]
                    elif resource == ResourceType.WALL:
                        color = CELL_COLORS[CellType.WALL]
                    elif resource == ResourceType.TOXIN:
                        color = CELL_COLORS[CellType.TOXIC]

                if LayerId.ORGANISMS in renderable and layer_state.organismGrid[y][x] != 0:
                    color = (
                        _ORGANISM_CELL_COLOR
                        if (x, y) in organism_cells
                        else _NON_ORGANISM_CELL_COLOR
                    )

                rect = pygame.Rect(ox + x * cs, oy + y * cs, cs, cs)
                pygame.draw.rect(self.surface, color, rect)

    # ------------------------------------------------------------------
    # Organism overlay
    # ------------------------------------------------------------------

    def draw_overlays(
        self,
        organisms: list[Organism],
        tick: int,
        show_ids: bool = True,
        show_vectors: bool = False,
    ) -> None:
        """Draw organism bounding boxes and optional labels."""
        cs = self.cell_size
        ox, oy = self.grid_offset_x, self.grid_offset_y
        font = self._get_font()

        for org in organisms:
            min_x, min_y, max_x, max_y = org.bounding_box()
            rect = pygame.Rect(
                ox + min_x * cs,
                oy + min_y * cs,
                (max_x - min_x + 1) * cs,
                (max_y - min_y + 1) * cs,
            )
            pygame.draw.rect(self.surface, _OVERLAY_BOX_COLOR, rect, 1)

            label_lines: list[str] = []
            if show_ids:
                label_lines.append(f"({org.organism_id})")
            label_lines.append(f"[d {org.travel_distance:.0f}]")
            label_lines.append(f"[t {org.survival_time(tick)}]")

            label_surfaces = [
                font.render(line, True, _OVERLAY_TEXT_COLOR) for line in label_lines
            ]
            line_h = font.get_height() + _LINE_SPACING
            label_w = max(surface.get_width() for surface in label_surfaces) + 6
            label_h = len(label_surfaces) * line_h + 4
            label_rect = pygame.Rect(
                rect.x + 1,
                rect.bottom + 1,
                label_w,
                label_h,
            )
            pygame.draw.rect(self.surface, _OVERLAY_LABEL_BG, label_rect)

            for index, surface in enumerate(label_surfaces):
                self.surface.blit(
                    surface,
                    (label_rect.x + 3, label_rect.y + 2 + index * line_h),
                )

    # ------------------------------------------------------------------
    # Debug / status panel
    # ------------------------------------------------------------------

    def draw_status(
        self,
        tick: int,
        organisms: list[Organism],
        paused: bool,
        extra_lines: list[str] | None = None,
        panel_x: int = 0,
        panel_y: int = 0,
    ) -> None:
        """Draw a debug status panel in the top-right or specified area."""
        font = self._get_font()
        lines: list[str] = [
            f"Tick: {tick}",
            f"Organisms: {len(organisms)}",
        ]
        if organisms:
            sizes = [o.size for o in organisms]
            lines.append(f"Largest: {max(sizes)}")
            avg_survival = sum(
                o.survival_time(tick) for o in organisms
            ) / len(organisms)
            lines.append(f"Avg survival: {avg_survival:.1f}")
            avg_travel = sum(o.travel_distance for o in organisms) / len(organisms)
            lines.append(f"Avg travel: {avg_travel:.2f}")
            best_org = max(organisms, key=lambda org: org.fitness(tick))
            lines.append(
                f"Top fitness: #{best_org.organism_id} {best_org.fitness(tick):.2f}"
            )
        lines.append("PAUSED" if paused else "RUNNING")
        if extra_lines:
            lines.extend(extra_lines)

        line_h = font.get_height() + _LINE_SPACING
        bg_height = len(lines) * line_h + 4
        bg_rect = pygame.Rect(panel_x, panel_y, _STATUS_PANEL_WIDTH, bg_height)
        pygame.draw.rect(self.surface, (10, 10, 20), bg_rect)

        for i, line in enumerate(lines):
            surf = font.render(line, True, (200, 230, 200))
            self.surface.blit(surf, (panel_x + 4, panel_y + 4 + i * line_h))
