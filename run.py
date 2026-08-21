#!/usr/bin/env python3
"""Launch WLKMN Studio: `python run.py` (or `python -m wlkmnstudio`)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wlkmnstudio.gui.app import main

if __name__ == "__main__":
    main()
