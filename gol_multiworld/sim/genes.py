"""Gene dataclass for D0 layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Gene:
    """Genetic parameters assigned to each organism."""

    max_cells: int = 200
    guidance_strength: float = 0.30

    def clamp(self) -> None:
        """Clamp gene values to safe ranges."""
        self.max_cells = max(4, self.max_cells)
        self.guidance_strength = max(0.0, min(1.0, self.guidance_strength))
