# app.py

## Overview

This file contains the main application class `App` for the GeneGoL simulation. It manages the top-level application state, initializes the simulation, handles the main event/render loop, and coordinates simulation ticks, rendering, and user controls.

## Key Components

- `App class`: Handles initialization, main loop, and simulation state.
- `Main loop`: Processes user input, advances the simulation, and renders the grid and overlays.
- `Helpers`: Methods for advancing the simulation, reloading rules, and resetting the world.

## Main Responsibilities

- Initializes Pygame and sets up the window.
- Loads simulation rules and initializes the grid.
- Handles user controls (pause, step, reset, speed, overlays).
- Advances the simulation by running D2, D3, and coordinator logic.
- Renders the grid, overlays, and debug/status panels.

## Called by

- main.py

## Calls

- `sim/coordinator`
- `sim/d2_update`
- `sim/d3_controller`
- `sim/grid`
- `sim/organism_detection`
- `sim/rules_engine`

- `ui/controls`
- `ui/overlays`
etc..
