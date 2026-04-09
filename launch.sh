#!/bin/bash
# launch.sh - Setup venv, install requirements, and launch GeneGoL
set -e

VENV_DIR=".venv"
PYTHON="python3"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating virtual environment in $VENV_DIR..."
    $PYTHON -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip and install requirements
echo "[INFO] Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# Launch the app
exec $PYTHON -m gol_multiworld.main "$@"
