"""Interactive layers sidebar panel."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from gol_multiworld.sim.layers import LayerId
from gol_multiworld.ui.layer_manager import LayerManager


@dataclass
class LayerRowLayout:
    layer_id: LayerId
    row_rect: pygame.Rect
    eye_rect: pygame.Rect
    name_rect: pygame.Rect
    slider_rect: pygame.Rect
    solo_rect: pygame.Rect
    lock_rect: pygame.Rect


class LayersPanel:
    """Draw and handle interactions for layer controls."""

    def __init__(self, x: int, y: int, width: int, font: pygame.font.Font) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.font = font
        self.presets = ["Ecology", "Genetics", "Structure"]
        self._drag_layer: LayerId | None = None

    def handle_event(self, event: pygame.event.Event, manager: LayerManager) -> None:
        layout = self._compute_layout(manager)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for row in layout["rows"]:
                if row.eye_rect.collidepoint(pos):
                    manager.toggle_visibility(row.layer_id)
                    return
                if row.solo_rect.collidepoint(pos):
                    manager.toggle_solo(row.layer_id)
                    return
                if row.lock_rect.collidepoint(pos):
                    manager.toggle_locked(row.layer_id)
                    return
                if row.slider_rect.collidepoint(pos):
                    self._drag_layer = row.layer_id
                    self._set_slider_opacity(row, pos[0], manager)
                    return

            for name, rect in layout["group_buttons"]:
                if rect.collidepoint(pos):
                    manager.toggle_group_visibility(name)
                    return

            for preset, rect in layout["preset_buttons"]:
                if rect.collidepoint(pos):
                    manager.apply_preset(preset)
                    return

        if event.type == pygame.MOUSEMOTION and self._drag_layer is not None:
            row = next((r for r in layout["rows"] if r.layer_id == self._drag_layer), None)
            if row is not None:
                self._set_slider_opacity(row, event.pos[0], manager)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag_layer = None

    def draw(self, surface: pygame.Surface, manager: LayerManager) -> None:
        layout = self._compute_layout(manager)
        panel_h = layout["height"]
        pygame.draw.rect(surface, (12, 12, 20), (self.x, self.y, self.width, panel_h))
        title = self.font.render("Layers", True, (220, 220, 240))
        surface.blit(title, (self.x + 6, self.y + 4))

        for name, rect in layout["group_buttons"]:
            pygame.draw.rect(surface, (28, 28, 42), rect, border_radius=4)
            text = self.font.render(name.split(":")[0], True, (180, 180, 210))
            surface.blit(text, (rect.x + 6, rect.y + 2))

        for row in layout["rows"]:
            vm = manager.layers[row.layer_id]
            pygame.draw.rect(surface, (20, 20, 30), row.row_rect, border_radius=3)

            eye = "◉" if vm.visible else "○"
            solo = "S*" if vm.solo else "S"
            lock = "L" if vm.locked else "U"
            color = (120, 220, 120) if vm.visible else (120, 120, 120)
            surface.blit(self.font.render(eye, True, color), (row.eye_rect.x, row.eye_rect.y))
            surface.blit(self.font.render(manager.layer_label(row.layer_id), True, (220, 220, 220)), (row.name_rect.x, row.name_rect.y))
            pygame.draw.rect(surface, (60, 60, 80), row.slider_rect, border_radius=2)
            fill_w = max(2, round(row.slider_rect.width * vm.opacity))
            pygame.draw.rect(
                surface,
                (90, 170, 255),
                (row.slider_rect.x, row.slider_rect.y, fill_w, row.slider_rect.height),
                border_radius=2,
            )
            pygame.draw.rect(surface, (80, 80, 80), row.solo_rect, border_radius=3)
            pygame.draw.rect(surface, (80, 80, 80), row.lock_rect, border_radius=3)
            surface.blit(self.font.render(solo, True, (240, 240, 240)), (row.solo_rect.x + 5, row.solo_rect.y + 1))
            surface.blit(self.font.render(lock, True, (240, 240, 240)), (row.lock_rect.x + 6, row.lock_rect.y + 1))

        for preset, rect in layout["preset_buttons"]:
            pygame.draw.rect(surface, (30, 45, 65), rect, border_radius=4)
            surface.blit(self.font.render(preset, True, (220, 230, 255)), (rect.x + 6, rect.y + 2))

    def _set_slider_opacity(self, row: LayerRowLayout, mouse_x: int, manager: LayerManager) -> None:
        rel = (mouse_x - row.slider_rect.x) / max(1, row.slider_rect.width)
        manager.set_opacity(row.layer_id, rel)

    def _compute_layout(self, manager: LayerManager) -> dict[str, object]:
        cursor_y = self.y + 24

        group_buttons: list[tuple[str, pygame.Rect]] = []
        for group_name in manager.groups():
            rect = pygame.Rect(self.x + 6, cursor_y, self.width - 12, 18)
            group_buttons.append((group_name, rect))
            cursor_y += 20

        cursor_y += 4
        rows: list[LayerRowLayout] = []
        for layer_id in LayerId:
            row_rect = pygame.Rect(self.x + 4, cursor_y, self.width - 8, 22)
            rows.append(
                LayerRowLayout(
                    layer_id=layer_id,
                    row_rect=row_rect,
                    eye_rect=pygame.Rect(self.x + 8, cursor_y + 3, 18, 16),
                    name_rect=pygame.Rect(self.x + 30, cursor_y + 3, 70, 16),
                    slider_rect=pygame.Rect(self.x + 98, cursor_y + 7, 72, 8),
                    solo_rect=pygame.Rect(self.x + 174, cursor_y + 2, 22, 18),
                    lock_rect=pygame.Rect(self.x + 198, cursor_y + 2, 22, 18),
                )
            )
            cursor_y += 24

        cursor_y += 4
        preset_buttons: list[tuple[str, pygame.Rect]] = []
        for preset in self.presets:
            rect = pygame.Rect(self.x + 6, cursor_y, self.width - 12, 18)
            preset_buttons.append((preset, rect))
            cursor_y += 20

        return {
            "rows": rows,
            "group_buttons": group_buttons,
            "preset_buttons": preset_buttons,
            "height": cursor_y - self.y + 4,
        }
