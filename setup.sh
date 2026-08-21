#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Find a Python interpreter that satisfies project requirements (3.11+).
# Prefer an explicit 3.11/3.12 binary; fall back to python3 if necessary.
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        version=$("$cmd" --version 2>&1 | awk '{print $2}')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3.11 or newer is required, but was not found."
    echo "Please install Python 3.11+ and try again."
    exit 1
fi

echo "Using $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
echo "Setting up Minesweeper project..."

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

echo "Setup complete. You can now run:"
echo "  ./run.sh    # play the game"
echo "  ./play.sh   # run the benchmark"
