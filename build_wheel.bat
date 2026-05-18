@echo off
cd /d "%~dp0"
python -m pip wheel . --no-deps --wheel-dir dist
