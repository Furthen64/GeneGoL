"""GIF recording support for the GeneGoL pygame renderer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time

import pygame

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised through app error handling
    Image = None


MAX_RECORD_SECONDS = 10.0
MIN_FRAME_DURATION_MS = 20


class GifRecorder:
    """Capture pygame frames and persist them as a GIF."""

    def __init__(
        self,
        output_dir: Path,
        max_duration_seconds: float = MAX_RECORD_SECONDS,
    ) -> None:
        self.output_dir = output_dir
        self.max_duration_seconds = max_duration_seconds
        self._frames: list[Image.Image] = []
        self._durations_ms: list[int] = []
        self._started_at: float | None = None

    @property
    def is_recording(self) -> bool:
        return self._started_at is not None

    def start(self) -> None:
        """Begin a new recording session."""
        if Image is None:
            raise RuntimeError("GIF export requires Pillow. Install requirements.txt.")
        if self.is_recording:
            return

        self._frames = []
        self._durations_ms = []
        self._started_at = time.monotonic()

    def elapsed_seconds(self) -> float:
        """Return the elapsed recording time in seconds."""
        if self._started_at is None:
            return 0.0
        return max(0.0, time.monotonic() - self._started_at)

    def should_auto_stop(self) -> bool:
        """Return whether the maximum recording duration has been reached."""
        return self.is_recording and self.elapsed_seconds() >= self.max_duration_seconds

    def capture_frame(self, surface: pygame.Surface, duration_ms: int) -> None:
        """Append the current surface contents as a GIF frame."""
        if not self.is_recording:
            return
        if Image is None:
            raise RuntimeError("GIF export requires Pillow. Install requirements.txt.")

        frame_bytes = pygame.image.tobytes(surface, "RGB")
        frame = Image.frombytes("RGB", surface.get_size(), frame_bytes)
        self._frames.append(frame)
        self._durations_ms.append(max(MIN_FRAME_DURATION_MS, duration_ms))

    def stop(self) -> Path | None:
        """Finish the recording session and save the GIF to disk."""
        if not self.is_recording:
            return None

        self._started_at = None
        if not self._frames:
            self._durations_ms = []
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"genegol_{timestamp}.gif"

        first_frame, *remaining_frames = self._frames
        first_frame.save(
            output_path,
            save_all=True,
            append_images=remaining_frames,
            duration=self._durations_ms,
            loop=0,
        )

        self._frames = []
        self._durations_ms = []
        return output_path