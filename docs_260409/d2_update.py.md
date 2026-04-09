# d2_update.py

## Overview
Implements the D2 cellular automaton update pass, advancing the grid by one tick using double-buffering. Applies rules for cell survival and birth based on visible live neighbors.

## Key Components
- **d2_update()**: Advances the grid by one D2 tick.
- **count_visible_live_neighbors()**: Used to determine neighbor counts for rules.

## Main Responsibilities
- Applies survival and birth rules to each cell.
- Uses double-buffering to avoid in-place mutation issues.
- Leaves static cell types (walls, food, toxic) unchanged.

## Usage
Called each tick to advance the simulation grid before organism detection and D3 logic.

## Related Files
- `grid.py`: Grid structure.
- `rules_engine.py`: Provides rules for cell updates.
- `visibility.py`: Neighbor counting helpers.
