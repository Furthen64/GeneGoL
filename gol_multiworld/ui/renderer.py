"""Pygame-ce renderer for the grid and overlays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pygame

from gol_multiworld.sim.cell_types import CELL_COLORS, CellType
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.layers import BaseTile, LayerId, LayerState, ResourceType
from gol_multiworld.sim.organism_detection import Organism
from gol_multiworld.ui.layer_manager import LayerViewModel

# Organism overlay colors
_ORGANISM_CELL_COLOR = CELL_COLORS[CellType.LIVE]
_NON_ORGANISM_CELL_COLOR = (25, 90, 25)
_OVERLAY_BOX_COLOR = (80, 200, 255)
_OVERLAY_TEXT_COLOR = (255, 255, 255)
_OVERLAY_LABEL_BG = (10, 10, 20)
_TINY_CLUSTER_COLOR = (60, 100, 60)

# Environment layer palette + legend data
_ENVIRONMENT_COLORS: dict[ResourceType, tuple[int, int, int]] = {
    ResourceType.NONE: CELL_COLORS[CellType.EMPTY],
    ResourceType.FOOD: CELL_COLORS[CellType.FOOD],
    ResourceType.WALL: CELL_COLORS[CellType.WALL],
    ResourceType.TOXIN: CELL_COLORS[CellType.TOXIC],
}
_ENVIRONMENT_LEGEND: list[tuple[str, tuple[int, int, int]]] = [
    ("Food", _ENVIRONMENT_COLORS[ResourceType.FOOD]),
    ("Wall", _ENVIRONMENT_COLORS[ResourceType.WALL]),
    ("Toxin", _ENVIRONMENT_COLORS[ResourceType.TOXIN]),
]

_LINE_SPACING = 2       # Pixels between text lines
_STATUS_PANEL_WIDTH = 220

GeneOverlayMode = Literal["trait_tint", "selected_numeric_badge", "gene_heatmap"]


@dataclass(frozen=True)
class LayerRenderStep:
    """Resolved render step derived from a layer id and LayerViewModel."""

    layer_id: LayerId
    opacity: float = 1.0
    blend_mode: Literal["normal", "multiply", "add"] = "normal"


@dataclass(frozen=True)
class GeneOverlayConfig:
    """Configuration for optional gene overlays."""

    enabled: bool = False
    mode: GeneOverlayMode = "trait_tint"
    trait_name: Literal["aggression", "metabolism", "speed"] = "aggression"
    selected_organism_id: int | None = None
    heatmap_gene_name: str = "guidance_strength"


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
        layer_view_models: dict[LayerId, LayerViewModel] | None = None,
        gene_overlay: GeneOverlayConfig | None = None,
    ) -> None:
        """Draw selected simulation layers using view-model aware composition."""
        organisms = organisms or []
        steps = self._compose_render_steps(renderable_layers, layer_view_models)
        if not steps:
            return

        for step in steps:
            if step.layer_id == LayerId.BASE_TILES:
                self.renderBaseTiles(layer_state, step)
            elif step.layer_id == LayerId.RESOURCES:
                self.renderEnvironment(layer_state, step)
            elif step.layer_id == LayerId.ORGANISMS:
                self.renderOrganisms(layer_state, organisms, step)
            elif step.layer_id == LayerId.GENES:
                self.renderGeneOverlay(layer_state, organisms, step, gene_overlay)

    def _compose_render_steps(
        self,
        renderable_layers: list[LayerId],
        layer_view_models: dict[LayerId, LayerViewModel] | None,
    ) -> list[LayerRenderStep]:
        """Resolve draw order and style from LayerViewModel state."""
        if layer_view_models is None:
            return [LayerRenderStep(layer_id=layer_id) for layer_id in renderable_layers]

        solo_layers = [
            layer_id for layer_id in renderable_layers if layer_view_models[layer_id].solo
        ]
        ordered_layers = solo_layers if solo_layers else renderable_layers

        steps: list[LayerRenderStep] = []
        for layer_id in ordered_layers:
            vm = layer_view_models[layer_id]
            if not vm.visible:
                continue
            steps.append(
                LayerRenderStep(
                    layer_id=layer_id,
                    opacity=max(0.0, min(1.0, vm.opacity)),
                    blend_mode=vm.blendMode,
                )
            )
        return steps

    def _new_layer_surface(self, width: int, height: int) -> pygame.Surface:
        pixel_w = width * self.cell_size
        pixel_h = height * self.cell_size
        return pygame.Surface((pixel_w, pixel_h), flags=pygame.SRCALPHA)

    def _composite_layer(self, layer_surface: pygame.Surface, step: LayerRenderStep) -> None:
        if step.opacity <= 0.0:
            return
        if step.opacity < 1.0:
            layer_surface.set_alpha(int(step.opacity * 255))

        special_flags = 0
        if step.blend_mode == "add":
            special_flags = pygame.BLEND_RGB_ADD
        elif step.blend_mode == "multiply":
            special_flags = pygame.BLEND_RGB_MULT

        self.surface.blit(
            layer_surface,
            (self.grid_offset_x, self.grid_offset_y),
            special_flags=special_flags,
        )

    def renderBaseTiles(self, layer_state: LayerState, step: LayerRenderStep) -> None:
        """Render base substrate tiles (empty/dead substrate)."""
        cs = self.cell_size
        layer_surface = self._new_layer_surface(layer_state.width, layer_state.height)
        for y in range(layer_state.height):
            for x in range(layer_state.width):
                color = CELL_COLORS[CellType.EMPTY]
                if layer_state.baseTilesGrid[y][x] == BaseTile.LIVE_SUBSTRATE:
                    color = _NON_ORGANISM_CELL_COLOR
                rect = pygame.Rect(x * cs, y * cs, cs, cs)
                pygame.draw.rect(layer_surface, color, rect)
        self._composite_layer(layer_surface, step)

    def renderEnvironment(self, layer_state: LayerState, step: LayerRenderStep) -> None:
        """Render environment resources (food/toxin/walls) with distinct palette."""
        cs = self.cell_size
        layer_surface = self._new_layer_surface(layer_state.width, layer_state.height)
        for y in range(layer_state.height):
            for x in range(layer_state.width):
                resource = ResourceType(layer_state.resourceGrid[y][x])
                if resource == ResourceType.NONE:
                    continue
                rect = pygame.Rect(x * cs, y * cs, cs, cs)
                pygame.draw.rect(layer_surface, _ENVIRONMENT_COLORS[resource], rect)
        self._composite_layer(layer_surface, step)

    def renderOrganisms(
        self,
        layer_state: LayerState,
        organisms: list[Organism],
        step: LayerRenderStep,
    ) -> None:
        """Render organism occupancy layer."""
        cs = self.cell_size
        organism_cells = {cell for org in organisms for cell in org.cells}
        layer_surface = self._new_layer_surface(layer_state.width, layer_state.height)

        for y in range(layer_state.height):
            for x in range(layer_state.width):
                if layer_state.organismGrid[y][x] == 0:
                    continue
                color = _ORGANISM_CELL_COLOR if (x, y) in organism_cells else _NON_ORGANISM_CELL_COLOR
                rect = pygame.Rect(x * cs, y * cs, cs, cs)
                pygame.draw.rect(layer_surface, color, rect)
        self._composite_layer(layer_surface, step)

    def renderGeneOverlay(
        self,
        layer_state: LayerState,
        organisms: list[Organism],
        step: LayerRenderStep,
        config: GeneOverlayConfig | None = None,
    ) -> None:
        """Render optional gene overlays (tint, badge, heatmap)."""
        cfg = config or GeneOverlayConfig(enabled=False)
        if not cfg.enabled:
            return

        if cfg.mode == "trait_tint":
            self._render_gene_trait_tint(layer_state, organisms, step, cfg.trait_name)
            return
        if cfg.mode == "selected_numeric_badge":
            self._render_selected_organism_badge(organisms, step, cfg.selected_organism_id)
            return
        self._render_gene_heatmap(layer_state, organisms, step, cfg.heatmap_gene_name)

    def _render_gene_trait_tint(
        self,
        layer_state: LayerState,
        organisms: list[Organism],
        step: LayerRenderStep,
        trait_name: str,
    ) -> None:
        cs = self.cell_size
        layer_surface = self._new_layer_surface(layer_state.width, layer_state.height)
        for org in organisms:
            trait_value = self._gene_value_for_trait(org.gene, trait_name)
            tint = self._trait_tint_color(trait_name, trait_value)
            for x, y in org.cells:
                rect = pygame.Rect(x * cs, y * cs, cs, cs)
                pygame.draw.rect(layer_surface, tint, rect)
        self._composite_layer(layer_surface, step)

    def _render_selected_organism_badge(
        self,
        organisms: list[Organism],
        step: LayerRenderStep,
        selected_organism_id: int | None,
    ) -> None:
        if selected_organism_id is None:
            return
        font = self._get_font()
        target = next((org for org in organisms if org.organism_id == selected_organism_id), None)
        if target is None:
            return

        min_x, min_y, max_x, _ = target.bounding_box()
        badge_value = f"ID:{target.organism_id} sz:{target.size}"
        badge_surface = font.render(badge_value, True, (250, 250, 250))
        bg = pygame.Surface((badge_surface.get_width() + 6, badge_surface.get_height() + 4), pygame.SRCALPHA)
        bg.fill((20, 20, 30, int(step.opacity * 255)))
        bg.blit(badge_surface, (3, 2))
        self.surface.blit(
            bg,
            (
                self.grid_offset_x + min_x * self.cell_size,
                self.grid_offset_y + (min_y - 1 if min_y > 0 else 0) * self.cell_size,
            ),
        )
        pygame.draw.rect(
            self.surface,
            (255, 255, 255),
            pygame.Rect(
                self.grid_offset_x + min_x * self.cell_size,
                self.grid_offset_y + min_y * self.cell_size,
                (max_x - min_x + 1) * self.cell_size,
                self.cell_size,
            ),
            width=1,
        )

    def _render_gene_heatmap(
        self,
        layer_state: LayerState,
        organisms: list[Organism],
        step: LayerRenderStep,
        gene_name: str,
    ) -> None:
        cs = self.cell_size
        values: list[float] = [self._safe_gene_numeric(getattr(org.gene, gene_name, 0.0)) for org in organisms]
        if not values:
            return
        lo = min(values)
        hi = max(values)
        denom = max(1e-6, hi - lo)

        layer_surface = self._new_layer_surface(layer_state.width, layer_state.height)
        for org in organisms:
            value = self._safe_gene_numeric(getattr(org.gene, gene_name, 0.0))
            norm = (value - lo) / denom
            color = self._heatmap_color(norm)
            for x, y in org.cells:
                rect = pygame.Rect(x * cs, y * cs, cs, cs)
                pygame.draw.rect(layer_surface, color, rect)
        self._composite_layer(layer_surface, step)

    def environment_legend(self) -> list[tuple[str, tuple[int, int, int]]]:
        """Return renderer-owned environment legend entries."""
        return list(_ENVIRONMENT_LEGEND)

    def _safe_gene_numeric(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _gene_value_for_trait(self, gene: Any, trait_name: str) -> float:
        trait_fallbacks = {
            "aggression": ["aggression", "guidance_strength"],
            "metabolism": ["metabolism", "max_cells"],
            "speed": ["speed", "guidance_strength"],
        }
        for attr in trait_fallbacks.get(trait_name, [trait_name]):
            if hasattr(gene, attr):
                return self._safe_gene_numeric(getattr(gene, attr))
        return 0.0

    def _trait_tint_color(self, trait_name: str, value: float) -> tuple[int, int, int, int]:
        normalized = max(0.0, min(1.0, value if value <= 1.0 else value / 200.0))
        alpha = int(70 + normalized * 120)
        if trait_name == "aggression":
            return (220, 80, 80, alpha)
        if trait_name == "metabolism":
            return (80, 220, 120, alpha)
        return (80, 140, 240, alpha)

    def _heatmap_color(self, normalized: float) -> tuple[int, int, int, int]:
        n = max(0.0, min(1.0, normalized))
        r = int(255 * n)
        b = int(255 * (1.0 - n))
        g = int(120 * (1.0 - abs(0.5 - n) * 2.0))
        return (r, g, b, 180)

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
