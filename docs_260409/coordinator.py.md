# coordinator.py

## Overview
Implements the D1 coordinator logic, responsible for seeding new organisms when the world is too sparse. Ensures the simulation remains active by planting new live-cell clumps as needed.

## Key Components
- **coordinator_tick()**: Main entry for D1 logic per tick.
- **_area_free()**: Checks if a region is empty for seeding.
- **_plant_clump()**: Plants a new clump of live cells.

## Main Responsibilities
- Monitors organism count and seeds new organisms if below threshold.
- Ensures new clumps are only planted in free areas.
- Integrates with the main simulation tick order.

## Usage
Called each tick after D3 logic to ensure the world remains populated.

## Related Files
- `grid.py`: Grid structure to be seeded.
- `organism_detection.py`: Provides organism count.
