# Installing WLKMN Studio

WLKMN Studio runs on your **computer** and talks to your **Walkman** over a USB cable.

**First:** your Walkman must already be running **[Walkman One](https://www.mrwalkman.com/)** (rooted).
WLKMN Studio doesn't install that — do it first with Mr Walkman's guide.

**Get WLKMN Studio:** on the [project page](https://github.com/Dexxzy/wlkmnstudio), click the green
**“Code”** button → **“Download ZIP”**, then right-click the ZIP → **“Extract All”** (put it somewhere
easy, like your Desktop). That extracted folder is your WLKMN Studio folder.

> The only thing you need to install yourself is **Python** — the app downloads everything else
> (including **adb**) automatically the first time you run it.

---

## 🪟 Windows

1. **Install Python** from [python.org/downloads](https://www.python.org/downloads/). In the installer,
   **tick “Add python.exe to PATH.”**
2. **Double-click `START.bat`** in your WLKMN Studio folder.

That's it. The first run installs what it needs (and grabs adb for you), then the app opens.

## 🍎 macOS

1. **Install Python** from [python.org/downloads](https://www.python.org/downloads/) (don't rely on the
   built-in one — it shows blank windows). *Or*, if you use Homebrew: `brew install python@3.13 python-tk@3.13`.
2. **Double-click `start.command`.**

## 🐧 Linux

```bash
sudo apt install python3 python3-tk python3-pip
./start.sh
```

---

## Then: plug in your Walkman and use it
1. Connect the Walkman by USB. On it, **do NOT turn on “USB Mass Storage”** — leave the player screen up.
   (There's no “USB debugging” setting to find — Walkman One turns the connection on for you.)
2. In WLKMN Studio, accept the one-time risk notice. When the top bar turns **green**
   (`… · root ✓ · Walkman One ✓`) you're connected.
3. Pick a tab → pick a mod → **Preview** → **Apply** → **⟳ Reboot** to see it. **Revert** undoes any mod.

*(After the first time, opening it = double-click the START file again.)*

---

## If something goes wrong

| Problem | Fix |
|---|---|
| **"Python was not found"** (Windows) | Re-run the python.org installer → **Modify** → tick **“Add python.exe to PATH,”** then double-click `START.bat` again. |
| **App can't see the Walkman** (status stays red) | Check the USB cable (some only charge), the Walkman is on, and **USB Mass Storage is OFF**. |
| **"unauthorized" device** | Look at the Walkman screen and tap **Allow / Trust**. |
| **`NOT root`** | The Walkman isn't rooted — install **Walkman One** first. |
| **adb didn't download** (no internet on first run, or a firewall) | Install it yourself: **Windows** `winget install Google.PlatformTools` · **macOS** `brew install android-platform-tools` · **Linux** `sudo apt install adb`. Or drop an `adb` (`adb.exe` on Windows) file into the WLKMN Studio folder — the launcher will use it. |
| **Blank / empty window** (macOS) | You used the built-in Python; install Python from python.org (or Homebrew). |

## Uninstall / reset
Delete the WLKMN Studio folder. Your backups, settings, and the downloaded adb live in a hidden
`.wlkmnstudio` folder in your home directory (`C:\Users\You\.wlkmnstudio` on Windows) — delete it to fully reset.
