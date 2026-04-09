"""Main application loop for GeneGoL."""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

import pygame

from gol_multiworld.sim.coordinator import coordinator_tick
from gol_multiworld.sim.d2_update import d2_update
from gol_multiworld.sim.d3_controller import d3_tick
from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.organism_detection import Organism, detect_organisms
from gol_multiworld.sim.rules_engine import load_rules
from gol_multiworld.ui.controls import Controls
from gol_multiworld.ui.overlays import draw_grid_lines, draw_key_help
from gol_multiworld.ui.renderer import Renderer

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
    ) -> None:
        self.rules_path = rules_path
        self.seed = seed
        self.fps = fps
        self.cell_size = cell_size

        # Derived dimensions
        self.grid_w = (WINDOW_WIDTH - PANEL_WIDTH) // cell_size
        self.grid_h = WINDOW_HEIGHT // cell_size

        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("GeneGoL – Multi-layer Cellular Automaton")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 12)

        self.rules: dict[str, Any] = load_rules(rules_path)
        self.rng = random.Random(seed)

        self.grid = Grid(self.grid_w, self.grid_h)
        self.grid.randomize(self.rules, seed=seed)

        self.organisms: list[Organism] = []
        self.tick: int = 0
        self.show_ids: bool = True
        self.show_vectors: bool = False

        self.renderer = Renderer(
            self.screen,
            cell_size=cell_size,
            grid_offset_x=0,
            grid_offset_y=0,
        )
        self.controls = Controls()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Enter the main event/render loop."""
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
            if self.controls.speed_up:
                self.fps = min(MAX_FPS, self.fps + 1)
            if self.controls.speed_down:
                self.fps = max(MIN_FPS, self.fps - 1)

            # Advance simulation
            if not self.controls.paused or self.controls.step_once:
                self._advance()

            # Draw
            self.screen.fill((20, 20, 30))
            self.renderer.draw_grid(self.grid)
            if self.cell_size >= 4:
                draw_grid_lines(
                    self.screen,
                    self.grid,
                    self.cell_size,
                    0,
                    0,
                )
            self.renderer.draw_overlays(
                self.organisms,
                show_ids=self.show_ids,
                show_vectors=self.show_vectors,
            )

            panel_x = WINDOW_WIDTH - PANEL_WIDTH
            self.renderer.draw_status(
                self.tick,
                self.organisms,
                self.controls.paused,
                panel_x=panel_x,
                panel_y=0,
            )
            draw_key_help(
                self.screen,
                self.font,
                self.controls.key_help(),
                x=panel_x + 4,
                y=160,
            )

            pygame.display.flip()
            self.clock.tick(self.fps)

        pygame.quit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _advance(self) -> None:
        """Run one full simulation tick."""
        # 1. D2 update
        self.grid = d2_update(self.grid, self.rules)

        # 2. D3 detect organisms
        self.organisms = detect_organisms(
            self.grid, self.tick, self.organisms, self.rules
        )

        # 3 & 4 & 5. D3 food, toxic, steering
        self.grid = d3_tick(
            self.grid, self.organisms, self.tick, self.rules, self.rng
        )

        # D1 coordinator: spawn if needed
        coordinator_tick(
            self.grid, self.organisms, self.tick, self.rules, self.rng
        )

        self.tick += 1

    def _reload_rules(self) -> None:
        """Hot-reload the rules JSON file."""
        try:
            self.rules = load_rules(self.rules_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[rules reload] Error: {exc}", file=sys.stderr)

    def _reset_world(self) -> None:
        """Reset the grid and organisms to a new random state."""
        self.tick = 0
        self.organisms = []
        new_seed = self.rng.randint(0, 2**31)
        self.grid = Grid(self.grid_w, self.grid_h)
        self.grid.randomize(self.rules, seed=new_seed)
