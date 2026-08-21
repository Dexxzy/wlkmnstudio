#!/bin/bash
# WLKMN Studio launcher (Linux).
cd "$(dirname "$0")"
[ -x "./adb" ] && export WLKMN_ADB="$PWD/adb"
python3 -m pip install -r requirements.txt || { echo "Setup failed — try: sudo apt install python3 python3-tk python3-pip adb"; exit 1; }
if [ -z "$WLKMN_ADB" ] && ! command -v adb >/dev/null 2>&1; then
  echo
  echo "  NOTE: 'adb' is not installed, so the app won't see your Walkman yet."
  echo "  Install it:  sudo apt install adb   (then run this again). Opening the app anyway..."
  echo
fi
python3 run.py
