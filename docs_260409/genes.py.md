# genes.py

## Overview
Defines the `Gene` dataclass, which encapsulates genetic parameters for each organism in the simulation (D0 layer).

## Key Components
- **Gene dataclass**: Holds genetic parameters such as `max_cells` and `guidance_strength`.
- **clamp() method**: Ensures gene values remain within safe, valid ranges.

## Main Responsibilities
- Stores per-organism genetic configuration.
- Provides a method to clamp values to valid ranges.

## Usage
Each `Organism` instance contains a `Gene` object, which can be modified and clamped as needed during simulation.

## Related Files
- `organism_detection.py`: Uses `Gene` for organism metadata.
