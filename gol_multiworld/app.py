"""Main application loop for GeneGoL."""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

import pygame

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.d2_update import d2_update
from gol_multiworld.sim.d3_controller import d3_tick
from gol_multiworld.sim.debug_trace import BirthCauseTracer
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.layers import LayerId
from gol_multiworld.sim.organism_detection import (
    Organism,
    cull_stagnating_organisms,
    detect_organisms,
)
from gol_multiworld.sim.rules_engine import load_rules
from gol_multiworld.sim.wall_generator import generate_walls
from gol_multiworld.ui.controls import Controls
from gol_multiworld.ui.gif_recorder import GifRecorder, MAX_RECORD_SECONDS
from gol_multiworld.ui.layer_manager import LayerManager, getRenderableLayers
from gol_multiworld.ui.layers_panel import LayersPanel
from gol_multiworld.ui.overlays import draw_grid_lines, draw_key_help
from gol_multiworld.ui.renderer import GeneOverlayConfig, Renderer

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 720
PANEL_WIDTH = 230          # Width of the right-side debug panel
CELL_SIZE = 8
DEFAULT_RULES_PATH = Path(__file__).parent / "config" / "rules.json"
DEFAULT_FPS = 10
MIN_FPS = 1
MAX_FPS = 60
MIN_CELL_SIZE = 2
MAX_CELL_SIZE = 32
GIF_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "gifs"
RANDOM_SEED: int | None = None   # Set to an int for deterministic runs


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class App:
    """Top-level application object."""

    def __init__(
        self,
        rules_path: Path = DEFAULT_RULES_PATH,
        seed: int | None = RANDOM_SEED,
        fps: int = DEFAULT_FPS,
        cell_size: int = CELL_SIZE,
        birth_debug: bool = False,
        birth_debug_strict: bool = False,
    ) -> None:
        self.rules_path = rules_path
        self.seed = seed
        self.fps = fps
        self.cell_size = cell_size
        self.grid_offset_x = 0
        self.grid_offset_y = 0

        # Derived dimensions
        self.grid_w = (WINDOW_WIDTH - PANEL_WIDTH) // cell_size
        self.grid_h = WINDOW_HEIGHT // cell_size

        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("GeneGoL – Multi-layer Cellular Automaton")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 12)

        self.rules: dict[str, Any] = load_rules(rules_path)
        self.debugger = BirthCauseTracer.from_settings(
            self.rules,
            enabled=birth_debug,
            strict=birth_debug_strict,
        )
        self.rng = random.Random(seed)
        world_seed = seed if seed is not None else self.rng.randint(0, 2**31)

        self.grid = Grid(self.grid_w, self.grid_h)
        generate_walls(self.grid, self.rules, random.Random(world_seed))
        self.grid.randomize(self.rules, seed=world_seed)

        self.organisms: list[Organism] = []
        self.organism_id_state: dict[str, int] = {"next_organism_id": 1}
        self.tick: int = 0
        self.show_ids: bool = True
        self.show_vectors: bool = False
        self.wall_delete_stage: int = 0
        self.inspected_tile: tuple[int, int] | None = None
        self.inspected_organism_id: int | None = None

        self.renderer = Renderer(
            self.screen,
            cell_size=self.cell_size,
            grid_offset_x=self.grid_offset_x,
            grid_offset_y=self.grid_offset_y,
        )
        self.controls = Controls()
        self.recorder = GifRecorder(GIF_OUTPUT_DIR)
        self.recording_notice: str | None = None
        self.wall_delete_notice: str | None = None
        self.layer_manager = LayerManager()
        panel_x = WINDOW_WIDTH - PANEL_WIDTH
        self.layers_panel = LayersPanel(panel_x, 160, PANEL_WIDTH - 4, self.font)
        self._sync_layer_registry()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Enter the main event/render loop."""
        try:
            while not self.controls.quit:
                self.controls.process_events()

                # Apply single-frame toggle flags
                if self.controls.toggle_ids:
                    self.show_ids = not self.show_ids
                if self.controls.toggle_vectors:
                    self.show_vectors = not self.show_vectors
                if self.controls.reload_rules:
                    self._reload_rules()
                if self.controls.reset:
                    self._reset_world()
                if self.controls.delete_walls:
                    self._delete_walls_stage()
                if self.controls.speed_up:
                    self.fps = min(MAX_FPS, self.fps + 1)
                if self.controls.speed_down:
                    self.fps = max(MIN_FPS, self.fps - 1)
                if self.controls.start_recording:
                    self._start_recording()
                if self.controls.stop_recording:
                    self._stop_recording()
                if self.controls.clicked_cell_pixel is not None:
                    self._inspect_click(self.controls.clicked_cell_pixel)
                if self.controls.pan_delta != (0, 0):
                    self._pan_view(*self.controls.pan_delta)
                if self.controls.zoom_steps != 0:
                    mouse_pos = pygame.mouse.get_pos()
                    self._zoom_view(self.controls.zoom_steps, mouse_pos)

                self._handle_layer_shortcuts_and_panel_events()

                # Advance simulation
                if not self.controls.paused or self.controls.step_once:
                    self._advance()

                # Draw
                self.screen.fill((20, 20, 30))
                renderable_layers = getRenderableLayers(self.layer_manager)
                self.renderer.draw_layers(
                    self.grid.get_layer_state(),
                    renderable_layers,
                    self.organisms,
                    layer_view_models=self.layer_manager.layers,
                    gene_overlay=GeneOverlayConfig(
                        enabled=LayerId.GENES in renderable_layers,
                        mode="trait_tint",
                        trait_name="aggression",
                    ),
                )
                if self.cell_size >= 4:
                    draw_grid_lines(
                        self.screen,
                        self.grid,
                        self.renderer.cell_size,
                        self.renderer.grid_offset_x,
                        self.renderer.grid_offset_y,
                    )
                if LayerId.ORGANISMS in renderable_layers:
                    self.renderer.draw_overlays(
                        self.organisms,
                        self.tick,
                        show_ids=self.show_ids,
                        show_vectors=self.show_vectors,
                    )

                panel_x = WINDOW_WIDTH - PANEL_WIDTH
                self.renderer.draw_status(
                    self.tick,
                    self.organisms,
                    self.controls.paused,
                    extra_lines=self._status_lines(),
                    panel_x=panel_x,
                    panel_y=0,
                )
                # Draw legend panel below status, above key help
                self.layers_panel.draw(self.screen, self.layer_manager)
                self._draw_legend_panel(panel_x=panel_x, panel_y=430)
                draw_key_help(
                    self.screen,
                    self.font,
                    self.controls.key_help(),
                    x=panel_x + 4,
                    y=530,
                )

                pygame.display.flip()

                if self.recorder.is_recording:
                    self.recorder.capture_frame(
                        self.screen,
                        duration_ms=max(20, round(1000 / self.fps)),
                    )
                    if self.recorder.should_auto_stop():
                        self._stop_recording()

                self.clock.tick(self.fps)
        finally:
            if self.recorder.is_recording:
                self._stop_recording()
            pygame.quit()

    def _draw_legend_panel(self, panel_x: int, panel_y: int) -> None:
        """Draw a legend for cell colors and their meanings."""
        font = self.font
        labels = [
            ("Empty", (20, 20, 30)),
            ("Organism cell", (100, 220, 100)),
            ("Non-organism live", (25, 90, 25)),
            *self.renderer.environment_legend(),
        ]
        line_h = font.get_height() + 2
        panel_w = 220
        panel_h = len(labels) * line_h + 8
        bg_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, (10, 10, 20), bg_rect)
        title = font.render("Legend:", True, (200, 230, 200))
        self.screen.blit(title, (panel_x + 4, panel_y + 4))
        for i, (label, color) in enumerate(labels):
            y = panel_y + 4 + (i + 1) * line_h
            # Draw color box
            pygame.draw.rect(self.screen, color, (panel_x + 8, y + 2, 18, 12))
            # Draw label
            text = font.render(label, True, (200, 230, 200))
            self.screen.blit(text, (panel_x + 32, y))

    def _status_lines(self) -> list[str]:
        """Build extra status text for the debug panel."""
        lines = [f"FPS: {self.fps}", f"Zoom: {self.cell_size}px"]
        lines.append(
            "Renderable: "
            + ",".join(layer_id.name for layer_id in self.layer_manager.get_renderable_layers())
        )
        if self.debugger.enabled:
            lines.append(f"BirthDebug: on ({self.debugger.violation_count} errs)")
        if self.recorder.is_recording:
            lines.append(
                f"REC: {self.recorder.elapsed_seconds():.1f}/{MAX_RECORD_SECONDS:.0f}s"
            )
        elif self.recording_notice:
            lines.append(self.recording_notice)
        if self.wall_delete_notice:
            lines.append(self.wall_delete_notice)
        lines.extend(self._inspector_lines())
        return lines

    def _inspector_lines(self) -> list[str]:
        lines: list[str] = []
        if self.inspected_tile is not None:
            tx, ty = self.inspected_tile
            tile = self._tile_debug_snapshot(tx, ty)
            lines.append(f"Tile({tx},{ty}) base={tile['base']}")
            lines.append(
                "  res={res} occ={occ}".format(
                    res=tile["resource"],
                    occ=tile["occupant"],
                )
            )
            lines.append(f"  mixed={tile['mixed_cell_type']}")

        if self.inspected_organism_id is not None:
            org = next(
                (o for o in self.organisms if o.organism_id == self.inspected_organism_id),
                None,
            )
            if org is not None:
                phenotype = org.phenotype or org.gene.derive_phenotype()
                lines.append(f"Org#{org.organism_id} size={org.size} age={org.survival_time(self.tick)}")
                lines.append(
                    "  loci gcap={:.2f} guide={:.2f} tox={:.2f}".format(
                        org.gene.growth_cap_locus,
                        org.gene.guidance_locus,
                        org.gene.toxin_resistance_locus,
                    )
                )
                lines.append(
                    "  loci app={:.2f} decay={:.2f}".format(
                        org.gene.appetite_locus,
                        org.gene.decay_tolerance_locus,
                    )
                )
                lines.append(
                    "  pheno max={} steer={:.2f} toxR={:.2f}".format(
                        phenotype.max_cells,
                        phenotype.guidance_strength,
                        phenotype.toxin_resistance,
                    )
                )
                lines.append(
                    "  pheno app={:.2f} decay={:.2f} bad={}".format(
                        phenotype.resource_appetite,
                        phenotype.decay_tolerance,
                        len(org.bad_zones),
                    )
                )
        return lines

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _handle_layer_shortcuts_and_panel_events(self) -> None:
        """Handle panel interactions and keyboard shortcuts for layer controls."""
        for event in self.controls.events:
            self.layers_panel.handle_event(event, self.layer_manager)
            if event.type != pygame.KEYDOWN:
                continue

            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                if event.key == pygame.K_1:
                    self.layer_manager.toggle_group_visibility("Group A: Simulation substrate")
                elif event.key == pygame.K_2:
                    self.layer_manager.toggle_group_visibility("Group B: Environment")
                elif event.key == pygame.K_3:
                    self.layer_manager.toggle_group_visibility("Group C: Biology/Genes")
                continue

            if event.key == pygame.K_1:
                self.layer_manager.apply_preset("Ecology")
            elif event.key == pygame.K_2:
                self.layer_manager.apply_preset("Genetics")
            elif event.key == pygame.K_3:
                self.layer_manager.apply_preset("Structure")

    def _inspect_click(self, pixel_pos: tuple[int, int]) -> None:
        px, py = pixel_pos
        if not self._point_in_board(px, py):
            return

        gx = (px - self.renderer.grid_offset_x) // self.renderer.cell_size
        gy = (py - self.renderer.grid_offset_y) // self.renderer.cell_size
        if gx < 0 or gy < 0 or gx >= self.grid.width or gy >= self.grid.height:
            return

        self.inspected_tile = (gx, gy)
        clicked = next(
            (org for org in self.organisms if (gx, gy) in org.cells),
            None,
        )
        self.inspected_organism_id = clicked.organism_id if clicked else None

    def _point_in_board(self, px: int, py: int) -> bool:
        return 0 <= px < (WINDOW_WIDTH - PANEL_WIDTH) and 0 <= py < WINDOW_HEIGHT

    def _pan_view(self, dx: int, dy: int) -> None:
        self.grid_offset_x += dx
        self.grid_offset_y += dy
        self.renderer.set_view(self.cell_size, self.grid_offset_x, self.grid_offset_y)

    def _zoom_view(self, zoom_steps: int, pivot_px: tuple[int, int]) -> None:
        px, py = pivot_px
        if not self._point_in_board(px, py):
            return

        old_size = self.cell_size
        target_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, old_size + zoom_steps))
        if target_size == old_size:
            return

        world_x = (px - self.grid_offset_x) / old_size
        world_y = (py - self.grid_offset_y) / old_size
        self.cell_size = target_size
        self.grid_offset_x = int(round(px - world_x * target_size))
        self.grid_offset_y = int(round(py - world_y * target_size))
        self.renderer.set_view(self.cell_size, self.grid_offset_x, self.grid_offset_y)

    def _tile_debug_snapshot(self, x: int, y: int) -> dict[str, int]:
        layer_state = self.grid.get_layer_state()
        return {
            "base": int(layer_state.baseTilesGrid[y][x]),
            "resource": int(layer_state.resourceGrid[y][x]),
            "occupant": int(layer_state.organismGrid[y][x]),
            "mixed_cell_type": int(self.grid.get(x, y)),
        }

    def _advance(self) -> None:
        """Run one full simulation tick with explicit layer-update ordering."""
        self.debugger.begin_tick(self.tick, self.grid)

        # 1) Environment diffusion/decay (resource and substrate effects).
        self.grid = d2_update(self.grid, self.rules, self.rng, self.debugger)

        # 2) Organism decisions from genes (detect living clusters and carry gene state).
        self.organisms = detect_organisms(
            self.grid,
            self.tick,
            self.organisms,
            self.rules,
            self.debugger,
            self.organism_id_state,
        )
        self.organisms = cull_stagnating_organisms(
            self.grid, self.organisms, self.rules
        )

        # 3) Movement/consumption/reproduction style actions (D3 controller).
        self.grid = d3_tick(
            self.grid,
            self.organisms,
            self.tick,
            self.rules,
            self.rng,
            self.debugger,
        )

        # Sync independent layer containers for renderer/UI and migration adapters.
        self._sync_layer_registry()

        self.debugger.finalize_tick(self.grid)
        self.tick += 1

    def _sync_layer_registry(self) -> None:
        """Refresh organism and gene layers from detected organisms."""
        organism_layer = self.grid.get_layer_grid(LayerId.ORGANISMS)
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                organism_layer[y][x] = 0

        gene_store: dict[int, Any] = {}
        for org in self.organisms:
            gene_store[org.organism_id] = org.gene
            for x, y in org.cells:
                self.grid.set_organism_cell(x, y, org.organism_id)

        self.grid.set_gene_store(gene_store)

    def _reload_rules(self) -> None:
        """Hot-reload the rules JSON file."""
        import json
        from gol_multiworld.sim.rules_engine import RulesValidationError
        try:
            self.rules = load_rules(self.rules_path)
            self.debugger = BirthCauseTracer.from_settings(
                self.rules,
                enabled=self.debugger.enabled,
                strict=self.debugger.strict,
            )
        except FileNotFoundError as exc:
            print(f"[rules reload] File not found: {exc}", file=sys.stderr)
        except json.JSONDecodeError as exc:
            print(f"[rules reload] Invalid JSON: {exc}", file=sys.stderr)
        except RulesValidationError as exc:
            print(f"[rules reload] Validation error: {exc}", file=sys.stderr)

    def _reset_world(self) -> None:
        """Reset the grid and organisms to a new random state."""
        self.tick = 0
        self.organisms = []
        self.organism_id_state = {"next_organism_id": 1}
        self.wall_delete_stage = 0
        self.wall_delete_notice = None
        new_seed = self.rng.randint(0, 2**31)
        self.grid = Grid(self.grid_w, self.grid_h)
        generate_walls(self.grid, self.rules, random.Random(new_seed))
        self.grid.randomize(self.rules, seed=new_seed)
        self._sync_layer_registry()

    def _start_recording(self) -> None:
        """Begin capturing frames for GIF export."""
        try:
            self.recorder.start()
        except RuntimeError as exc:
            self.recording_notice = str(exc)
            return

        self.recording_notice = "REC: saving on stop"

    def _stop_recording(self) -> None:
        """Stop capturing frames and write the GIF to disk."""
        output_path = self.recorder.stop()
        if output_path is None:
            self.recording_notice = "REC: no frames captured"
            return

        self.recording_notice = f"Saved: {output_path.name}"
        print(f"[gif] Saved recording to {output_path}")

    def _delete_walls_stage(self) -> None:
        """Delete walls in three presses: leave 75%, then 50%, then none."""
        wall_cells = [
            (x, y)
            for y in range(self.grid.height)
            for x in range(self.grid.width)
            if self.grid.get(x, y) == CellType.WALL
        ]
        if not wall_cells:
            self.wall_delete_stage = 3
            self.wall_delete_notice = "W pressed: no walls found"
            print("[walls] W pressed but no walls are present")
            return

        before_count = len(wall_cells)
        self.wall_delete_stage = min(3, self.wall_delete_stage + 1)
        if self.wall_delete_stage < 3:
            # Stage 1 removes 25% of current walls (leaves ~75%).
            # Stage 2 removes 33% of current walls (leaves ~50% of original).
            remove_fraction = 0.25 if self.wall_delete_stage == 1 else (1.0 / 3.0)
            remove_count = max(1, int(round(len(wall_cells) * remove_fraction)))
            walls_to_remove = self.rng.sample(wall_cells, remove_count)
        else:
            walls_to_remove = wall_cells

        removed_count = 0
        for x, y in walls_to_remove:
            if self.grid.clear_wall(x, y):
                removed_count += 1

        remaining_count = sum(
            1
            for y in range(self.grid.height)
            for x in range(self.grid.width)
            if self.grid.get(x, y) == CellType.WALL
        )
        self.wall_delete_notice = (
            f"W pressed: stage {self.wall_delete_stage}/3, "
            f"removed {removed_count}, remaining {remaining_count}"
        )
        print(
            "[walls] stage=%d before=%d removed=%d remaining=%d"
            % (self.wall_delete_stage, before_count, removed_count, remaining_count)
        )
