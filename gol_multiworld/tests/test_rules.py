"""Tests for the rules loader and validator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from gol_multiworld.sim.rules_engine import load_rules, RulesValidationError


VALID_RULES = {
    "minimumOrganismSize": 4,
    "d3GuidanceWeight": 0.30,
    "caWeight": 0.70,
    "foodScarcity": 0.02,
    "toxicMemoryTicks": 30,
    "states": ["Empty", "Live", "Food", "Wall", "Toxic"],
    "liveCell": {"surviveIfVisibleLiveNeighborsIn": [2, 3]},
    "emptyCell": {"bornIfVisibleLiveNeighborsIn": [3]},
    "foodCell": {"staticUntilConsumedByD3": True},
    "toxicCell": {"static": True, "emitAvoidSignalOnContact": True},
    "wallCell": {"static": True, "blocksVisibilityCompletely": True},
}


def _write_rules(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "rules.json"
    p.write_text(json.dumps(data))
    return p


def test_load_valid_rules(tmp_path: Path) -> None:
    p = _write_rules(tmp_path, VALID_RULES)
    rules = load_rules(p)
    assert rules["minimumOrganismSize"] == 4
    assert rules["d3GuidanceWeight"] == pytest.approx(0.30)


def test_missing_key_raises(tmp_path: Path) -> None:
    bad = dict(VALID_RULES)
    del bad["minimumOrganismSize"]
    p = _write_rules(tmp_path, bad)
    with pytest.raises(RulesValidationError, match="minimumOrganismSize"):
        load_rules(p)


def test_invalid_organism_size(tmp_path: Path) -> None:
    bad = dict(VALID_RULES)
    bad["minimumOrganismSize"] = 0
    p = _write_rules(tmp_path, bad)
    with pytest.raises(RulesValidationError, match="minimumOrganismSize"):
        load_rules(p)


def test_invalid_d3_weight_out_of_range(tmp_path: Path) -> None:
    bad = dict(VALID_RULES)
    bad["d3GuidanceWeight"] = 1.5
    p = _write_rules(tmp_path, bad)
    with pytest.raises(RulesValidationError, match="d3GuidanceWeight"):
        load_rules(p)


def test_invalid_food_scarcity(tmp_path: Path) -> None:
    bad = dict(VALID_RULES)
    bad["foodScarcity"] = -0.1
    p = _write_rules(tmp_path, bad)
    with pytest.raises(RulesValidationError, match="foodScarcity"):
        load_rules(p)


def test_missing_live_cell_survive_key(tmp_path: Path) -> None:
    bad = dict(VALID_RULES)
    bad["liveCell"] = {}
    p = _write_rules(tmp_path, bad)
    with pytest.raises(RulesValidationError, match="surviveIfVisibleLiveNeighborsIn"):
        load_rules(p)


def test_missing_empty_cell_born_key(tmp_path: Path) -> None:
    bad = dict(VALID_RULES)
    bad["emptyCell"] = {}
    p = _write_rules(tmp_path, bad)
    with pytest.raises(RulesValidationError, match="bornIfVisibleLiveNeighborsIn"):
        load_rules(p)


def test_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_rules(Path("/nonexistent/path/rules.json"))


def test_default_rules_file_loads() -> None:
    default = Path(__file__).parent.parent / "config" / "rules.json"
    rules = load_rules(default)
    assert "minimumOrganismSize" in rules
