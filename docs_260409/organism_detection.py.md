# organism_detection.py

## Overview
Implements organism detection in the D3 layer using BFS to find connected clusters of live cells. Maintains organism identity, metadata, and continuity across simulation ticks.

## Key Components
- **Organism dataclass**: Stores metadata for each detected organism (ID, cells, gene, etc).
- **detect_organisms()**: Finds all organisms in the grid, matches them to previous tick's organisms for continuity.
- **_bfs()**: Helper for BFS traversal to find clusters.
- **_next_free_id()**: Helper to assign unique organism IDs.

## Main Responsibilities
- Detects 8-connected clusters of live cells as organisms.
- Maintains organism identity and metadata across ticks.
- Filters out clusters below minimum size.

## Usage
Called each tick to update the list of organisms in the simulation.

## Related Files
- `grid.py`: Provides the grid structure.
- `genes.py`: Used for organism genetic data.
