"""Tests for GIF recording support."""

from __future__ import annotations

import time

import pygame

from gol_multiworld.ui.gif_recorder import GifRecorder


def test_stop_saves_gif(tmp_path) -> None:
    recorder = GifRecorder(tmp_path)
    surface = pygame.Surface((8, 8))
    surface.fill((255, 0, 0))

    recorder.start()
    recorder.capture_frame(surface, duration_ms=100)

    output_path = recorder.stop()

    assert output_path is not None
    assert output_path.exists()
    assert output_path.parent == tmp_path
    assert output_path.suffix == ".gif"


def test_auto_stop_after_max_duration(tmp_path) -> None:
    recorder = GifRecorder(tmp_path, max_duration_seconds=0.01)

    recorder.start()
    recorder._started_at = time.monotonic() - 0.02

    assert recorder.should_auto_stop() is True