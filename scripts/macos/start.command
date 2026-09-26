#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then echo "Dobby is not installed. Run scripts/macos/setup.command first."; exit 1; fi
exec "$ROOT/.venv/bin/python" -m dobby "$@"
