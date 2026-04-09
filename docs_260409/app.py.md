# app.py

## Overview
This file contains the main application class `App` for the GeneGoL simulation. It manages the top-level application state, initializes the simulation, handles the main event/render loop, and coordinates simulation ticks, rendering, and user controls.

## Key Components
- **App class**: Handles initialization, main loop, and simulation state.
- **Main loop**: Processes user input, advances the simulation, and renders the grid and overlays.
- **Helpers**: Methods for advancing the simulation, reloading rules, and resetting the world.

## Main Responsibilities
- Initializes Pygame and sets up the window.
- Loads simulation rules and initializes the grid.
- Handles user controls (pause, step, reset, speed, overlays).
- Advances the simulation by running D2, D3, and coordinator logic.
- Renders the grid, overlays, and debug/status panels.

## Usage
The `App` class is instantiated and run from `main.py`. It can be configured with different rules, random seeds, FPS, and cell sizes.

## Related Files
- `main.py`: Entry point, parses CLI args and runs the app.
- `sim/`: Simulation logic (grid, rules, organisms, etc).
- `ui/`: Rendering and controls.
