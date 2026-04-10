# GeneGoL
Gene based Game of Life clone

Controls include GIF recording: press `J` to start capture and `K` to stop. Recordings also stop automatically after 10 seconds and are saved as timestamped `.gif` files in `gifs/`.

## Deterministic interaction rules

| Category | Trigger | Deterministic outcome |
|---|---|---|
| Tile occupancy constraints | Any write attempts to occupy a wall tile | Write is rejected; wall remains immutable and occupant is unchanged. |
| Tile occupancy constraints | LIVE/organism writes to non-wall tiles | Resource layer is cleared, organism layer set occupied, and substrate set live. |
| Resource consumption and decay | D3 food-adjacent update | Food converts to LIVE up to an appetite-derived per-tick cap. |
| Resource consumption and decay | D2 food spoil check | FOOD transitions to TOXIN iff RNG draw is `< foodSpoilChance`. |
| Toxin effects and resistance | Toxic adjacency detected | Bad-zone memory is recorded; phenotype resistance scales toxin penalties. |
| Toxin effects and resistance | Bad-zone decay pass | Expired memories are removed after phenotype-derived grace ticks. |
| Wall collision behavior | Guided growth candidate selection | Only EMPTY non-wall boundary candidates are considered, with deterministic y/x tie-break ordering. |
| Wall collision behavior | Out-of-bounds access | Reads return EMPTY; writes are ignored. |

The same canonical table is also available in code at `gol_multiworld/sim/interaction_rules.py`.

## Gene schema and phenotype mapping

Gene loci are normalized `[0, 1]` values:

- `growth_cap_locus` → `phenotype.max_cells`
- `guidance_locus` → `phenotype.guidance_strength`
- `toxin_resistance_locus` → `phenotype.toxin_resistance`
- `appetite_locus` → `phenotype.resource_appetite`
- `decay_tolerance_locus` → `phenotype.decay_tolerance`

During each organism update, the D3 controller reads both:
1. local environment-layer densities (food/toxin/wall around centroid), and
2. the organism's derived phenotype.

These jointly influence food consumption cap, steering probability, and toxin-memory penalties.

## Debug inspectors

- Left click (`LMB`) on an organism to inspect:
  - genome loci,
  - derived phenotype,
  - current organism state (size, age, bad-zone memory count).
- Left click any tile to inspect per-layer values at that coordinate:
  - base tile value,
  - resource layer value,
  - organism occupancy id,
  - mixed/legacy cell type.
