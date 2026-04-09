# grid.py

## Overview
Defines the `Grid` class, which represents the 2D simulation grid and provides methods for cell access, mutation, and random world generation.

## Key Components
- **Grid class**: Manages a 2D array of cell types.
- **get/set methods**: Access and mutate cell values safely.
- **clone()**: Deep-copies the grid for double-buffering.
- **randomize()**: Fills the grid with a random initial state based on rules and densities.
- **clear()**: Resets all cells to empty.

## Main Responsibilities
- Encapsulates the simulation grid state.
- Provides safe access and mutation of cells.
- Supports random world generation and clearing.

## Usage
Used throughout the simulation for all grid operations, including updates, rendering, and organism detection.

## Related Files
- `cell_types.py`: Defines cell type enums and colors.
- `d2_update.py`, `d3_controller.py`: Operate on the grid.
