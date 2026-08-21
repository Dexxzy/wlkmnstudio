# Installing WLKMN Studio

WLKMN Studio runs on your **computer** and talks to your **Walkman** over a USB cable.

**First:** your Walkman must already be running **[Walkman One](https://www.mrwalkman.com/)** (rooted).
WLKMN Studio doesn't install that — do it first with Mr Walkman's guide.

**Get WLKMN Studio:** on the [project page](https://github.com/Dexxzy/wlkmnstudio), click the green
**“Code”** button → **“Download ZIP”**, then right-click the ZIP → **“Extract All”** (put it somewhere
easy, like your Desktop). That extracted folder is your WLKMN Studio folder.

---

## 🪟 Windows

1. **Install Python** from [python.org/downloads](https://www.python.org/downloads/). In the installer,
   **tick “Add python.exe to PATH.”**
2. **Get adb, and drop it in the folder:** download
   [Platform Tools](https://developer.android.com/tools/releases/platform-tools), unzip it, and copy these
   3 files — **`adb.exe`, `AdbWinApi.dll`, `AdbWinUsbApi.dll`** — into your WLKMN Studio folder (next to
   `START.bat`). *(This is instead of the confusing “add to PATH” stuff.)*
3. **Double-click `START.bat`.** The first run sets things up, then the app opens. That's it.

## 🍎 macOS

1. Install Homebrew Python (the built-in one shows blank windows):
   ```bash
   brew install python@3.13 python-tk@3.13 android-platform-tools
   ```
2. **Double-click `start.command`** (or run `./start.command` in Terminal).

## 🐧 Linux

```bash
sudo apt install python3 python3-tk python3-pip adb
./start.sh
```

---

## Then: plug in your Walkman and use it
1. Connect the Walkman by USB. On it, **do NOT turn on “USB Mass Storage”** — leave the player screen up.
2. In WLKMN Studio, accept the one-time risk notice. When the top bar turns **green**
   (`… · root ✓ · Walkman One ✓`) you're connected.
3. Pick a tab → pick a mod → **Preview** → **Apply** → **⟳ Reboot** to see it. **Revert** undoes any mod.

*(After the first time, you only need to plug in and double-click the START file again.)*

---

## If something goes wrong

| Problem | Fix |
|---|---|
| **"Python was not found"** (Windows) | Re-run the python.org installer → **Modify** → tick **“Add python.exe to PATH,”** then double-click `START.bat` again. |
| **App can't see the Walkman** (status stays red) | Check the USB cable (some only charge), the Walkman is on, and **USB Mass Storage is OFF**. |
| **"unauthorized" device** | Look at the Walkman screen and tap **Allow / Trust**. |
| **"'adb' is not recognized"** (Windows) | You didn't copy `adb.exe` + the two `.dll`s into the WLKMN Studio folder — see Windows step 2. |
| **`NOT root`** | The Walkman isn't rooted — install **Walkman One** first. |
| **Blank / empty window** (macOS) | You used the built-in Python; use Homebrew's (macOS step 1). |

## Advanced / command-line
Prefer a terminal? See the CLI section of the [README](README.md#cli). The `START` scripts just run
`pip install -r requirements.txt` then `run.py` for you.

## Uninstall / reset
Delete the WLKMN Studio folder. Your backups + settings live in a hidden `.wlkmnstudio` folder in your
home directory (`C:\Users\You\.wlkmnstudio` on Windows) — delete it to fully reset.
