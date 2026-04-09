# overlays.py

## Overview

Provides additional overlay helpers for the simulation UI, such as drawing key help and grid lines.

## Key Components

- `draw_key_help()`: Renders a list of help-text lines on the UI.
- `draw_grid_lines()`: Draws subtle grid lines for better visualization.

## Main Responsibilities

- Enhances the UI with overlays for usability and debugging.
- Integrates with the main renderer and app.

## Usage

Called by the main app and renderer to display overlays and help text.

## Related Files

- `renderer.py`: Main rendering logic.
- `app.py`: Calls overlay helpers for UI.
