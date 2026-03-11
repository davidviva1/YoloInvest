#!/bin/bash
# Update locked dependency set from top-level requirements.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source venv/bin/activate
python -m pip install --upgrade pip pip-tools
pip-compile --output-file requirements.txt requirements.in

echo "requirements.txt updated from requirements.in"
