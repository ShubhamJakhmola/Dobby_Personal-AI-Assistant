#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo "Python 3 is required."; exit 1; }
python3 -m venv .venv
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" setup.py
echo "Dobby macOS setup complete. Start with scripts/macos/start.command"
