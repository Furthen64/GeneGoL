"""Keyboard and event controls for the simulation."""

from __future__ import annotations

import pygame


class Controls:
    """Translate keyboard/mouse events into simulation commands.

    Attributes
    ----------
    paused : bool
        Whether the simulation is paused.
    step_once : bool
        True for one tick only when the user presses the step key.
    quit : bool
        True when the user requests the app to close.
    reset : bool
        True when the user requests a world reset.
    reload_rules : bool
        True when the user requests a rules JSON hot-reload.
    speed_up : bool
        True when the user pressed the speed-up key this frame.
    speed_down : bool
        True when the user pressed the speed-down key this frame.
    toggle_ids : bool
        Toggle organism ID overlay.
    toggle_vectors : bool
        Toggle organism direction-vector overlay.
    delete_walls : bool
        Trigger staged wall deletion.
    start_recording : bool
        Begin GIF recording.
    stop_recording : bool
        End GIF recording and save the result.
    events : list[pygame.event.Event]
        Raw event queue from the last poll for other UI components.
    clicked_cell_pixel : tuple[int, int] | None
        Mouse pixel coordinate clicked in current frame.
    pan_delta : tuple[int, int]
        Mouse drag delta in pixels used to pan the gameboard.
    zoom_steps : int
        Mouse-wheel zoom direction for this frame (+in, -out).
    """

    def __init__(self) -> None:
        self.paused: bool = False
        self.step_once: bool = False
        self.quit: bool = False
        self.reset: bool = False
        self.reload_rules: bool = False
        self.speed_up: bool = False
        self.speed_down: bool = False
        self.toggle_ids: bool = False
        self.toggle_vectors: bool = False
        self.delete_walls: bool = False
        self.start_recording: bool = False
        self.stop_recording: bool = False
        self.events: list[pygame.event.Event] = []
        self.clicked_cell_pixel: tuple[int, int] | None = None
        self.pan_delta: tuple[int, int] = (0, 0)
        self.zoom_steps: int = 0

    def process_events(self) -> None:
        """Poll all pending pygame events and update state flags."""
        # Reset single-frame flags
        self.step_once = False
        self.reset = False
        self.reload_rules = False
        self.speed_up = False
        self.speed_down = False
        self.toggle_ids = False
        self.toggle_vectors = False
        self.delete_walls = False
        self.start_recording = False
        self.stop_recording = False
        self.clicked_cell_pixel = None
        self.pan_delta = (0, 0)
        self.zoom_steps = 0

        self.events = pygame.event.get()
        for event in self.events:
            if event.type == pygame.QUIT:
                self.quit = True

            elif event.type == pygame.KEYDOWN:
                key = event.key

                if key == pygame.K_SPACE:
                    self.paused = not self.paused

                elif key == pygame.K_s:
                    # Single step while paused
                    self.step_once = True

                elif key == pygame.K_r:
                    self.reset = True

                elif key == pygame.K_l:
                    self.reload_rules = True

                elif key == pygame.K_EQUALS or key == pygame.K_PLUS:
                    self.speed_up = True

                elif key == pygame.K_MINUS:
                    self.speed_down = True

                elif key == pygame.K_i:
                    self.toggle_ids = True

                elif key == pygame.K_v:
                    self.toggle_vectors = True

                elif key == pygame.K_w:
                    self.delete_walls = True

                elif key == pygame.K_j:
                    self.start_recording = True

                elif key == pygame.K_k:
                    self.stop_recording = True

                elif key == pygame.K_ESCAPE or key == pygame.K_q:
                    self.quit = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.clicked_cell_pixel = event.pos

            elif event.type == pygame.MOUSEMOTION and event.buttons[1]:
                dx, dy = self.pan_delta
                mx, my = event.rel
                self.pan_delta = (dx + mx, dy + my)

            elif event.type == pygame.MOUSEWHEEL:
                self.zoom_steps += event.y

    def key_help(self) -> list[str]:
        """Return a list of key-binding descriptions for the debug panel."""
        return [
            "[SPACE] pause/resume",
            "[S] step once",
            "[R] reset world",
            "[L] reload rules",
            "[+/-] speed",
            "[1/2/3] presets",
            "[Shift+1/2/3] group toggles",
            "[W] delete walls 25/50/100%",
            "[J] start GIF",
            "[K] stop GIF",
            "[I] toggle IDs",
            "[V] toggle vectors",
            "[LMB] inspect tile/organism",
            "[MMB drag] pan board",
            "[Mouse wheel] zoom",
            "[Q/ESC] quit",
        ]
