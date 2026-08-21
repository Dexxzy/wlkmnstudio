"""Find (or auto-download) adb so users don't have to install Platform Tools by hand.

Resolution order: `$WLKMN_ADB` → `adb` on PATH → an `adb` next to the app or in our cache →
otherwise download Google's official Platform Tools ZIP for this OS (one time) and cache it in
`~/.wlkmnstudio/platform-tools/`. Python is the only hard prerequisite, so doing this in Python
works the same on Windows, macOS, and Linux — no Homebrew / PATH editing / manual unzip needed.
"""
import io
import os
import platform
import stat
import subprocess
import urllib.request
import zipfile

CACHE_ROOT = os.path.expanduser("~/.wlkmnstudio")
CACHE_DIR = os.path.join(CACHE_ROOT, "platform-tools")   # the ZIP extracts a platform-tools/ folder here

# Official Google Platform Tools (public, no auth). Latest stable, per-OS.
_URLS = {
    "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "Darwin":  "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "Linux":   "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}


def _exe():
    return "adb.exe" if os.name == "nt" else "adb"


def _works(adb):
    """True if `adb version` runs (a real adb binary)."""
    if not adb:
        return False
    try:
        r = subprocess.run([adb, "version"], capture_output=True, timeout=12)
        return r.returncode == 0
    except Exception:
        return False


def _candidates():
    yield os.environ.get("WLKMN_ADB")
    yield "adb"                                              # PATH
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for base in (app_dir, CACHE_DIR):                        # next to the app, or our extracted cache
        yield os.path.join(base, _exe())


def find_adb():
    """Return a working adb path/command, or None if adb isn't available anywhere yet."""
    for c in _candidates():
        if c and _works(c):
            return c
    return None


def download_adb(on_log=print):
    """Download Google's Platform Tools for this OS into the cache and return the adb path."""
    url = _URLS.get(platform.system())
    if not url:
        raise RuntimeError("no Platform Tools download available for %s" % platform.system())
    on_log("Downloading adb (Google Platform Tools, ~5 MB, one time)…")
    data = urllib.request.urlopen(url, timeout=120).read()
    os.makedirs(CACHE_ROOT, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(CACHE_ROOT)                             # creates ~/.wlkmnstudio/platform-tools/
    adb = os.path.join(CACHE_DIR, _exe())
    if not os.path.exists(adb):
        raise RuntimeError("adb not found in the downloaded Platform Tools")
    if os.name != "nt":
        os.chmod(adb, os.stat(adb).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    if not _works(adb):
        raise RuntimeError("downloaded adb did not run")
    on_log("adb ready.")
    return adb


def ensure_adb(on_log=print):
    """Return a usable adb, downloading Platform Tools once if needed. Sets $WLKMN_ADB so child
    processes (and device.py) use the same one. Raises on failure (caller decides whether fatal)."""
    adb = find_adb()
    if not adb:
        adb = download_adb(on_log)
    os.environ["WLKMN_ADB"] = adb
    return adb
