# main.py

## Overview
Entry point for the GeneGoL application. Parses command-line arguments, configures the simulation, and launches the main application loop.

## Key Components
- **main()**: Parses CLI arguments and runs the app.
- **App**: Instantiated and run with user-specified or default parameters.

## Main Responsibilities
- Handles command-line argument parsing for rules, seed, FPS, and cell size.
- Instantiates the main `App` class and starts the simulation loop.

## Usage
Run this file directly to start the simulation:

```bash
python -m gol_multiworld.main [--rules RULES] [--seed SEED] [--fps FPS] [--cell-size SIZE]
```

## Related Files
- `app.py`: Main application logic.
