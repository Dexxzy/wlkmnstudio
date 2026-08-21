#!/bin/bash
# WLKMN Studio launcher (macOS) — double-click in Finder.
cd "$(dirname "$0")"
PY=python3.13
command -v "$PY" >/dev/null 2>&1 || PY=python3
echo "Setting up WLKMN Studio (first run downloads a few things)..."
"$PY" -m pip install -r requirements.txt || { echo; echo "Setup failed. Install Homebrew Python: brew install python@3.13 python-tk@3.13"; read -n1 -r -p "Press any key…"; exit 1; }
echo "Launching…"
"$PY" run.py
