#!/bin/bash
# WLKMN Studio launcher (Linux).
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt || { echo "Setup failed — try: sudo apt install python3 python3-tk python3-pip adb"; exit 1; }
python3 run.py
