#!/usr/bin/env python3
"""Launch WLKMN Studio: `python run.py` (or `python -m wlkmnstudio`)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Make sure adb is available before the GUI opens — auto-download Google Platform Tools once if the
# user hasn't installed it. Prints to the console (visible in the launcher window); never fatal.
try:
    from wlkmnstudio import adb_setup, device
    device.set_adb(adb_setup.ensure_adb())
except Exception as e:
    print("Note: couldn't set up adb automatically (%s). The app will open but won't see a device "
          "until adb is available." % e)

from wlkmnstudio.gui.app import main

if __name__ == "__main__":
    main()
