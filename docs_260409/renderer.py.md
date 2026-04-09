# renderer.py

## Overview
Handles all drawing operations for the simulation using Pygame. Renders the grid, organism overlays, and debug/status panels.

## Key Components
- **Renderer class**: Manages drawing of grid, overlays, and status panel.
- **draw_grid()**: Draws all cells in the grid.
- **draw_overlays()**: Draws organism bounding boxes and labels.
- **draw_status()**: Renders debug/status information in a panel.

## Main Responsibilities
- Visualizes the simulation state for the user.
- Provides overlays for organism metadata and simulation status.
- Integrates with the main app for rendering each frame.

## Usage
Instantiated by the main app and called each frame to render the current state.

## Related Files
- `app.py`: Uses Renderer for all drawing.
- `overlays.py`: Additional overlay helpers.
