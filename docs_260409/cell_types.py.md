# cell_types.py

## Overview
Defines the `CellType` enum for all possible cell states in the simulation and provides default color mappings for rendering.

## Key Components
- **CellType (IntEnum)**: Enumerates EMPTY, LIVE, FOOD, WALL, TOXIC.
- **CELL_COLORS**: Maps each cell type to an RGB color for rendering.

## Main Responsibilities
- Standardizes cell type values across the simulation.
- Provides color information for rendering.

## Usage
Used throughout the simulation for cell state checks and rendering.

## Related Files
- `grid.py`, `renderer.py`: Use these enums and color mappings.
