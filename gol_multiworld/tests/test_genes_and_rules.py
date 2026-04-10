"""Tests for gene schema mapping and deterministic occupancy behavior."""

from __future__ import annotations

from gol_multiworld.sim.cell_types import CellType
from gol_multiworld.sim.genes import Gene
from gol_multiworld.sim.grid import Grid


def test_gene_derives_expected_phenotype_ranges() -> None:
    gene = Gene(
        growth_cap_locus=1.0,
        guidance_locus=0.6,
        toxin_resistance_locus=0.8,
        appetite_locus=0.7,
        decay_tolerance_locus=0.4,
    )
    phenotype = gene.derive_phenotype()

    assert phenotype.max_cells >= 4
    assert phenotype.guidance_strength == 0.6
    assert phenotype.toxin_resistance == 0.8
    assert phenotype.resource_appetite == 0.7
    assert phenotype.decay_tolerance == 0.4


def test_wall_tiles_are_immutable_for_non_wall_writes() -> None:
    grid = Grid(6, 6)
    grid.set(2, 2, CellType.WALL)

    grid.set(2, 2, CellType.LIVE)
    assert grid.get(2, 2) == CellType.WALL

    grid.set(2, 2, CellType.FOOD)
    assert grid.get(2, 2) == CellType.WALL
