#!/bin/bash
# debuglaunch.sh - Setup venv, install requirements, and launch GeneGoL with birth tracing enabled
set -euo pipefail

VENV_DIR=".venv"
PYTHON="python3"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating virtual environment in $VENV_DIR..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip and install requirements
echo "[INFO] Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

TEMP_RULES_FILE="$(mktemp)"
trap 'rm -f "$TEMP_RULES_FILE"' EXIT

"$VENV_DIR/bin/python" - <<'PY' "gol_multiworld/config/rules.json" "$TEMP_RULES_FILE"
import json
import sys

source_path = sys.argv[1]
target_path = sys.argv[2]

with open(source_path, "r", encoding="utf-8") as source_file:
    rules = json.load(source_file)

wall_generation = dict(rules.get("wallGeneration", {}))
wall_generation["mode"] = "none"
wall_generation["legacyWallDensity"] = 0.0
rules["wallGeneration"] = wall_generation

with open(target_path, "w", encoding="utf-8") as target_file:
    json.dump(rules, target_file)
PY

ARGS=(--birth-debug --rules "$TEMP_RULES_FILE")

if [ "${BIRTH_DEBUG_STRICT:-0}" = "1" ]; then
    ARGS+=(--birth-debug-strict)
fi

# Launch the app with unbuffered output so debug logs appear immediately
exec "$VENV_DIR/bin/python" -u -m gol_multiworld.main "${ARGS[@]}" "$@"