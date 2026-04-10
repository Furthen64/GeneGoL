"""Gene schema and phenotype derivation for the D0 layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phenotype:
    """Derived behavior parameters read by simulation updates."""

    max_cells: int
    guidance_strength: float
    toxin_resistance: float
    resource_appetite: float
    decay_tolerance: float


GENE_SCHEMA: dict[str, dict[str, float | str]] = {
    "growth_cap_locus": {
        "default": 0.55,
        "maps_to": "max_cells",
        "weight": 240.0,
    },
    "guidance_locus": {
        "default": 0.30,
        "maps_to": "guidance_strength",
        "weight": 1.0,
    },
    "toxin_resistance_locus": {
        "default": 0.20,
        "maps_to": "toxin_resistance",
        "weight": 1.0,
    },
    "appetite_locus": {
        "default": 0.50,
        "maps_to": "resource_appetite",
        "weight": 1.0,
    },
    "decay_tolerance_locus": {
        "default": 0.35,
        "maps_to": "decay_tolerance",
        "weight": 1.0,
    },
}


@dataclass
class Gene:
    """Genetic parameters assigned to each organism."""

    growth_cap_locus: float = float(GENE_SCHEMA["growth_cap_locus"]["default"])
    guidance_locus: float = float(GENE_SCHEMA["guidance_locus"]["default"])
    toxin_resistance_locus: float = float(
        GENE_SCHEMA["toxin_resistance_locus"]["default"]
    )
    appetite_locus: float = float(GENE_SCHEMA["appetite_locus"]["default"])
    decay_tolerance_locus: float = float(
        GENE_SCHEMA["decay_tolerance_locus"]["default"]
    )

    def clamp(self) -> None:
        """Clamp gene values to safe ranges."""
        self.growth_cap_locus = max(0.0, min(1.0, self.growth_cap_locus))
        self.guidance_locus = max(0.0, min(1.0, self.guidance_locus))
        self.toxin_resistance_locus = max(0.0, min(1.0, self.toxin_resistance_locus))
        self.appetite_locus = max(0.0, min(1.0, self.appetite_locus))
        self.decay_tolerance_locus = max(0.0, min(1.0, self.decay_tolerance_locus))

    @property
    def max_cells(self) -> int:
        return max(4, int(40 + self.growth_cap_locus * float(GENE_SCHEMA["growth_cap_locus"]["weight"])))

    @property
    def guidance_strength(self) -> float:
        return self.guidance_locus

    @property
    def aggression(self) -> float:
        return self.appetite_locus

    @property
    def metabolism(self) -> float:
        return self.decay_tolerance_locus

    @property
    def speed(self) -> float:
        return self.guidance_locus

    def derive_phenotype(self) -> Phenotype:
        """Resolve loci into simulation-ready phenotype parameters."""
        self.clamp()
        return Phenotype(
            max_cells=self.max_cells,
            guidance_strength=self.guidance_strength,
            toxin_resistance=self.toxin_resistance_locus,
            resource_appetite=self.appetite_locus,
            decay_tolerance=self.decay_tolerance_locus,
        )
