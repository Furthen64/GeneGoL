# controls.py

## Overview
Implements keyboard and event controls for the simulation, translating user input into simulation commands and state changes.

## Key Components
- **Controls class**: Handles keyboard/mouse events and updates control flags.
- **process_events()**: Polls and processes Pygame events.
- **key_help()**: Returns a list of key-binding descriptions for the UI.

## Main Responsibilities
- Maps user input to simulation control flags (pause, step, reset, etc).
- Provides key help for display in the UI.

## Usage
Instantiated by the main app and called each frame to process user input.

## Related Files
- `app.py`: Uses Controls for event handling.
