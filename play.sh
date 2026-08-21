#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: virtual environment not found at $SCRIPT_DIR/.venv"
    echo "Run ./setup.sh first to create it and install dependencies."
    exit 1
fi

exec "$VENV_PYTHON" "$SCRIPT_DIR/main.py" "$@"
