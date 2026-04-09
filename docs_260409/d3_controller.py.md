# d3_controller.py

## Overview
Implements the D3 layer of the simulation, handling food consumption, toxic memory, and gentle steering for organisms. Modifies the grid and organism state based on environmental cues and organism memory.

## Key Components
- **d3_tick()**: Main entry for D3 logic per tick.
- **_handle_food()**: Converts adjacent food cells to live cells.
- **_handle_toxic()**: Records toxic contact in organism memory.
- **_decay_bad_zones()**: Removes expired toxic memory.
- **_apply_steering()**: Biases organism growth toward food and away from toxic zones.

## Main Responsibilities
- Handles food consumption and toxic contact for each organism.
- Applies steering bias to organism growth based on food and toxic memory.
- Updates the grid and organism state in-place.

## Usage
Called each tick after organism detection to update organism state and grid.

## Related Files
- `organism_detection.py`: Provides organism metadata.
- `grid.py`: Grid structure to be updated.
