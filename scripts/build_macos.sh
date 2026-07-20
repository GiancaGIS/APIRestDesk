#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

"$PYTHON_BIN" -m pip install --no-build-isolation -e ".[packaging]"
"$PYTHON_BIN" -m PyInstaller --noconfirm packaging/pyinstaller/APIRestDesk.spec

echo "macOS app completed: dist/APIRestDesk.app"
