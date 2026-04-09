"""Additional overlay helpers (key help, grid lines, etc.)."""

from __future__ import annotations

import pygame

from gol_multiworld.sim.grid import Grid
from gol_multiworld.sim.organism_detection import Organism

_LINE_SPACING = 2   # Pixels between text lines (shared constant)


def draw_key_help(
    surface: pygame.Surface,
    font: pygame.font.Font,
    lines: list[str],
    x: int,
    y: int,
) -> None:
    """Draw a list of help-text lines at (x, y)."""
    line_h = font.get_height() + _LINE_SPACING
    for i, line in enumerate(lines):
        surf = font.render(line, True, (160, 160, 180))
        surface.blit(surf, (x, y + i * line_h))


def draw_grid_lines(
    surface: pygame.Surface,
    grid: Grid,
    cell_size: int,
    offset_x: int,
    offset_y: int,
    color: tuple[int, int, int] = (40, 40, 50),
) -> None:
    """Draw subtle grid lines (useful for small cell sizes)."""
    if cell_size < 4:
        return  # Too small to show grid lines
    w = grid.width * cell_size
    h = grid.height * cell_size
    for x in range(grid.width + 1):
        pygame.draw.line(
            surface,
            color,
            (offset_x + x * cell_size, offset_y),
            (offset_x + x * cell_size, offset_y + h),
        )
    for y in range(grid.height + 1):
        pygame.draw.line(
            surface,
            color,
            (offset_x, offset_y + y * cell_size),
            (offset_x + w, offset_y + y * cell_size),
        )
