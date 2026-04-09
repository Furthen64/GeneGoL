"""Entry point for GeneGoL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gol_multiworld.app import App, DEFAULT_RULES_PATH


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GeneGoL – Multi-layer Cellular Automaton Sandbox"
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help="Path to the JSON rules file",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic runs",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Initial simulation speed (ticks per second)",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=8,
        dest="cell_size",
        help="Pixel size of each grid cell",
    )
    parser.add_argument(
        "--birth-debug",
        action="store_true",
        help="Log every new live cell and enforce birth-cause invariants",
    )
    parser.add_argument(
        "--birth-debug-strict",
        action="store_true",
        help="Raise on birth-cause invariant failures instead of only logging them",
    )
    args = parser.parse_args()

    app = App(
        rules_path=args.rules,
        seed=args.seed,
        fps=args.fps,
        cell_size=args.cell_size,
        birth_debug=args.birth_debug,
        birth_debug_strict=args.birth_debug_strict,
    )
    app.run()


if __name__ == "__main__":
    main()
