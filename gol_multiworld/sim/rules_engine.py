"""Rules loader and validator for the JSON-based rules file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_TOP_KEYS: list[str] = [
    "minimumOrganismSize",
    "d3GuidanceWeight",
    "caWeight",
    "foodScarcity",
    "toxicMemoryTicks",
    "states",
    "liveCell",
    "emptyCell",
    "foodCell",
    "toxicCell",
    "wallCell",
]


class RulesValidationError(ValueError):
    """Raised when the rules JSON file is missing required fields or has invalid values."""


def load_rules(path: str | Path) -> dict[str, Any]:
    """Load and validate a rules JSON file.

    Parameters
    ----------
    path:
        Path to the JSON rules file.

    Returns
    -------
    dict
        Validated rules dictionary.

    Raises
    ------
    RulesValidationError
        If any required field is missing or a value is out of range.
    FileNotFoundError
        If the file does not exist.
    json.JSONDecodeError
        If the file is not valid JSON.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        rules: dict[str, Any] = json.load(fh)

    _validate_rules(rules)
    return rules


def _validate_rules(rules: dict[str, Any]) -> None:
    """Validate the rules dictionary in-place."""
    missing = [k for k in REQUIRED_TOP_KEYS if k not in rules]
    if missing:
        raise RulesValidationError(f"Rules file is missing required keys: {missing}")

    # Numeric range checks
    min_org: int = rules["minimumOrganismSize"]
    if not isinstance(min_org, int) or min_org < 1:
        raise RulesValidationError(
            f"minimumOrganismSize must be a positive integer, got {min_org!r}"
        )

    d3w: float = rules["d3GuidanceWeight"]
    caw: float = rules["caWeight"]
    for name, val in [("d3GuidanceWeight", d3w), ("caWeight", caw)]:
        if not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0):
            raise RulesValidationError(
                f"{name} must be a float in [0, 1], got {val!r}"
            )

    food_s: float = rules["foodScarcity"]
    if not isinstance(food_s, (int, float)) or not (0.0 <= food_s <= 1.0):
        raise RulesValidationError(
            f"foodScarcity must be a float in [0, 1], got {food_s!r}"
        )

    tox_mem: int = rules["toxicMemoryTicks"]
    if not isinstance(tox_mem, int) or tox_mem < 0:
        raise RulesValidationError(
            f"toxicMemoryTicks must be a non-negative integer, got {tox_mem!r}"
        )

    # liveCell / emptyCell neighbor lists
    live_cell: dict[str, Any] = rules["liveCell"]
    if "surviveIfVisibleLiveNeighborsIn" not in live_cell:
        raise RulesValidationError(
            "liveCell must contain 'surviveIfVisibleLiveNeighborsIn'"
        )

    empty_cell: dict[str, Any] = rules["emptyCell"]
    if "bornIfVisibleLiveNeighborsIn" not in empty_cell:
        raise RulesValidationError(
            "emptyCell must contain 'bornIfVisibleLiveNeighborsIn'"
        )
