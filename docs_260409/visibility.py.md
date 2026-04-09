# visibility.py

## Overview
Provides helper functions for neighbor visibility, accounting for wall occlusion. Used to determine which neighbors are visible and to count visible live neighbors for cellular automaton rules.

## Key Components
- **get_visible_neighbors()**: Returns visible (non-wall) neighbors for a cell.
- **count_visible_live_neighbors()**: Counts visible live neighbors for a cell.

## Main Responsibilities
- Implements wall-occlusion logic for neighbor visibility.
- Supports D2 update logic for survival and birth rules.

## Usage
Used by the D2 update logic to determine neighbor counts for each cell.

## Related Files
- `d2_update.py`: Uses these helpers for update logic.
- `cell_types.py`: Defines cell types.
