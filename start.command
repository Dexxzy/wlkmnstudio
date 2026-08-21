#!/bin/bash
# WLKMN Studio launcher (macOS) — double-click in Finder.
cd "$(dirname "$0")"

# Finder-launched apps DON'T inherit your Terminal's PATH, so a `brew install android-platform-tools`
# adb (and python.org / Homebrew Python) can be invisible. Add the usual spots so they're found.
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:$PATH"

PY=python3.13
command -v "$PY" >/dev/null 2>&1 || PY=python3

# Use an 'adb' file dropped in this folder if present; otherwise rely on the system PATH.
[ -x "./adb" ] && export WLKMN_ADB="$PWD/adb"

echo "Setting up WLKMN Studio (first run downloads a few things)..."
"$PY" -m pip install -r requirements.txt || { echo; echo "Setup failed. Install Homebrew Python:  brew install python@3.13 python-tk@3.13"; read -n1 -r -p "Press any key…"; exit 1; }

# adb is what lets the app see your Walkman — warn clearly if it's missing.
if [ -z "$WLKMN_ADB" ] && ! command -v adb >/dev/null 2>&1; then
  echo
  echo "  NOTE: 'adb' is not installed, so the app won't see your Walkman yet."
  echo "  Install it (needs Homebrew from https://brew.sh):"
  echo "      brew install android-platform-tools"
  echo "  Then run this again. (Opening the app anyway...)"
  echo
fi

echo "Launching…"
"$PY" run.py
