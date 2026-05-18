#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python -m pip wheel . --no-deps --wheel-dir dist
