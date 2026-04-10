"""Deterministic interaction rule table for simulation and debugging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InteractionRule:
    category: str
    trigger: str
    deterministic_outcome: str


INTERACTION_RULES: list[InteractionRule] = [
    InteractionRule(
        category="Tile occupancy constraints",
        trigger="Any write attempts to occupy a wall tile",
        deterministic_outcome="Write is rejected; wall remains immutable and occupant is unchanged.",
    ),
    InteractionRule(
        category="Tile occupancy constraints",
        trigger="LIVE/organism writes to non-wall tiles",
        deterministic_outcome="Resource layer is cleared, organism layer set occupied, and substrate set live.",
    ),
    InteractionRule(
        category="Resource consumption and decay",
        trigger="D3 food-adjacent update",
        deterministic_outcome="Food is converted to LIVE up to appetite-derived per-tick cap.",
    ),
    InteractionRule(
        category="Resource consumption and decay",
        trigger="D2 food spoil check",
        deterministic_outcome="FOOD transitions to TOXIN if RNG draw < foodSpoilChance.",
    ),
    InteractionRule(
        category="Toxin effects and resistance",
        trigger="Toxic cell adjacent to organism",
        deterministic_outcome="Bad-zone memory is stamped with expiry; resistance weakens toxicity penalty.",
    ),
    InteractionRule(
        category="Toxin effects and resistance",
        trigger="Bad-zone decay pass",
        deterministic_outcome="Expired memories are dropped after phenotype-derived grace ticks.",
    ),
    InteractionRule(
        category="Wall collision behavior",
        trigger="Guided growth candidate selection",
        deterministic_outcome="Only EMPTY non-wall boundary candidates are considered; ties break by y/x sort order.",
    ),
    InteractionRule(
        category="Wall collision behavior",
        trigger="Out-of-bounds get/set access",
        deterministic_outcome="Reads return EMPTY and writes are ignored.",
    ),
]
