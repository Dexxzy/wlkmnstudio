# Installing WLKMN Studio

WLKMN Studio is a Python app (GUI + CLI). It talks to your Walkman over `adb`. You need three things:
a **rooted Walkman One device**, **adb** on your PATH, and a **Python 3.10+ with Tk 8.6+**.

> ⚠️ **macOS:** do **not** use the system `/usr/bin/python3` — it ships Tk 8.5, which renders **blank
> windows**. Use a Homebrew or python.org Python (below). The app checks your Tk version on startup and
> tells you if it's too old.

---

## 1. Prerequisites

### Your Walkman
- A **Sony NW-A50 series** Walkman running **[Walkman One](https://www.mrwalkman.com/)** (rooted).
- Connect it by USB. On the device, turn **OFF** *USB Mass Storage* (Settings → USB) so the player UI
  and `adb` stay active while it's plugged in.

### Python + Tk + adb, per OS

**macOS (Homebrew):**
```bash
brew install python@3.13 python-tk@3.13 android-platform-tools
```
Run everything below with `python3.13`.

**Windows:**
- Install **Python** from [python.org](https://www.python.org/downloads/) — it bundles a working Tk.
  Tick **“Add python.exe to PATH”** in the installer.
- Install **platform-tools** (adb): download from
  [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools), unzip, and
  add the folder to your PATH.

**Linux (Debian/Ubuntu):**
```bash
sudo apt install python3 python3-tk python3-pip adb
```

### Verify adb sees your device
```bash
adb devices
```
You should see your Walkman listed as `device` (not `unauthorized`/`offline`).

---

## 2. Get the code
```bash
git clone https://github.com/Dexxzy/wlkmnstudio.git
cd wlkmnstudio
```

## 3. Install the Python dependencies
```bash
python3.13 -m pip install -r requirements.txt     # macOS
# Windows:      py -m pip install -r requirements.txt
# Linux:        python3 -m pip install -r requirements.txt
```

## 4. Run it

**GUI:**
```bash
python3.13 run.py       # macOS   (Windows: py run.py    Linux: python3 run.py)
```
On first launch you'll accept the risk agreement, then the device status bar turns green
(`model · root ✓ · Walkman One ✓`). Pick a module tab → **Preview** → **Apply**. **Revert** or
**Revert All** restores from the automatic backups in `~/.wlkmnstudio/backups`.

**CLI** (same engine, scriptable):
```bash
python3.13 -m wlkmnstudio.cli list                 # all modules
python3.13 -m wlkmnstudio.cli detect               # device / root / Walkman One
python3.13 -m wlkmnstudio.cli shot                 # grab the live screen
python3.13 -m wlkmnstudio.cli preview <mod> k=v    # dry-run
python3.13 -m wlkmnstudio.cli apply   <mod> k=v    # back up + flash
python3.13 -m wlkmnstudio.cli revert  <mod>        # or: revert-all
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| **Blank / empty window** (macOS) | You're on Tk 8.5. Use Homebrew/python.org Python (see step 1). |
| **`no device` / status stays red** | `adb devices` empty → check USB, enable USB debugging, turn off Mass Storage. |
| **`NOT root`** | The device isn't rooted / adb isn't running as root. Walkman One provides root. |
| **`settings.txt not readable`** | Turn **off** USB Mass Storage on the Walkman so `/contents` is mounted for the player. |
| **`ModuleNotFoundError: PIL` / `_tkinter`** | Wrong Python. Install deps into the same Python that has Tk (step 3). |

## Uninstall / reset
- Remove the app folder.
- Backups + settings live in `~/.wlkmnstudio/` — delete it to reset (this also re-shows the risk dialog).
