# rules_engine.py

## Overview
Handles loading and validating the JSON-based rules file for the simulation. Ensures all required fields are present and values are within valid ranges.

## Key Components
- **load_rules()**: Loads and validates a rules JSON file.
- **_validate_rules()**: Checks for required keys and value ranges.
- **RulesValidationError**: Custom exception for invalid rules.

## Main Responsibilities
- Loads rules from a JSON file.
- Validates presence and correctness of all required fields.
- Raises informative errors for missing or invalid data.

## Usage
Used by the main app to load simulation rules at startup and on reload.

## Related Files
- `app.py`: Loads rules at initialization and on reload.
- `config/rules.json`: The rules file format.
