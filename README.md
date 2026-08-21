# WLKMN Studio (beta) 
# This software is inherently risky to use. It has never bricked my device, but some patches are riskier than others. Use with discretion.
I am not responsible for any damage caused by use of WLKMN.studio, but I doubt anything will break. It's all been pretty thoroughly tested.

This is currently in development; some things will be slightly broken (sorry!)

Design your Sony **NW-A30 - A50** Walkman's visual identity — **boot animation, power-on splash, UI font** —
from your own logo/GIF/colors, preview it, and flash it safely. A native cross-platform GUI (Mac +
Windows + Linux).

Built on top of **[Walkman One](https://www.mrwalkman.com/)** — it *requires* WM1 and a rooted device,
so it drives people to Mr Walkman's firmware, and it's designed to sit alongside
**[wampy](https://github.com/unknown321/wampy)** (which skins the player UI) rather than compete.

> Ships **no proprietary Sony files.** Every mod operates on *your* device's own assets + *your* uploads
> + bundled open-license fonts. Original files are backed up and md5-verified before anything is written.

## Requirements
- A **Sony NW-A30 - A50 series** Walkman running **Walkman One**, rooted, USB-debugging on.
- **adb** on your PATH (Android platform-tools).
- **Python 3.10+** with Tk (see `requirements.txt` for the per-OS Tk install).

<<<<<<< HEAD
## Compatibility

### Devices
WLKMN Studio targets Sony's non-Android **"Walkman OS" (Hagoromo) platform**. Developed and tested on the
**NW-A55**; other models on the same platform (running a Walkman One build) should work — every binpatch
mod md5-verifies and looks for its exact target first, so on a model where an offset differs it **aborts
cleanly instead of bricking**. Trying is low-risk.

| Support | Models | Notes |
|---|---|---|
| ✅ Tested / expected | NW-A50 (A55/56/57), NW-A40 (A45/46/47), NW-A30 (A35/36/37) | A30/A40 have no LDAC → skip that one mod |
| 🟡 Same platform, verify audio patches | NW-ZX300 / ZX300A, NW-WM1A / WM1Z | Theme + QOL should port; audio binpatch offsets differ per model |
| ❌ Not supported (Android) | NW-A100, NW-ZX500, NW-A300 | Different OS entirely |

Requires **Walkman One** firmware + root on any of the supported models.

### Works with wampy
Runs alongside **[wampy](https://github.com/unknown321/wampy)** (unknown321's Winamp/cassette/clock
overlay) — *verified from wampy's source*, not assumed. wampy installs its own binaries under
`/system/vendor/unknown321/` and starts them as a **separate boot service** (`init.wampy.rc`); it does
**not** modify the Sony player, boot animation, splash, or fonts that WLKMN Studio edits, so there is **no
file overlap**. Clean install order: **wampy first, then WLKMN mods** (they pull the current app and patch
on top, md5-verified). Your themed stock UI stays put; Hold-toggle brings up wampy's overlay.
=======
  This software was developed on and for an A50 series walkman, although it should work on the A30 & A40 as well.
>>>>>>> 94acd7c4af9e96a18f8f550e164bd727a3e6dead

## Install & run
**Full step-by-step for macOS / Windows / Linux → [INSTALL.md](INSTALL.md).** Quick version:
```bash
pip install -r requirements.txt
python run.py            # or: python -m wlkmnstudio
```
> **macOS:** don't use the system `/usr/bin/python3` — it ships **Tk 8.5**, which renders **blank
> windows**. Use Homebrew (`brew install python@3.13 python-tk@3.13`, run with `python3.13`) or
> python.org. The app checks your Tk version at startup and tells you if it's too old.

## Modules (21)
Grouped by category in the app. Fill a mod's fields → **Preview** → **Apply** (backs up first, flashes,
md5-verifies) → **Revert** restores from the backup ledger (`~/.wlkmnstudio/backups`). Reboot to see it.

**🎨 Theme**
| Module | What it does | Risk |
|---|---|---|
| **Boot Animation** | Your own GIF, or a logo→line→waves intro | low |
| **Power-on Splash** | Replace the orange WALKMAN logo | med |
| **UI Font** | Swap SST / SST UI for a bundled or uploaded typeface | low |
| **UI Accent + Icons** | Recolor home icons + the EQ/streaming accent | high |
| **UI Text Themer** | Recolor *all* main UI text + background — 4 one-click presets or any color per element | high |
| **Marquee Scroll Speed** | Tune how fast long titles scroll (slower ↔ fastest) | med |
| **Alternate Theme** | Switch the whole UI to the firmware's second (reverse) palette | med |

**🔊 Audio**
| Module | What it does | Risk |
|---|---|---|
| **AirPods / A2DP Fix** | The BT compatibility fix | med |
| **SBC-XQ** | Raise the SBC max bitpool for near-transparent SBC | med |
| **LDAC 990** | Force LDAC to 990 kbps and stop ABR auto-downgrade | med |
| **BT Monitor** | Live read of the active BT codec / RTP state (read-only) | — |

**⚡ Quality of life**
| Module | What it does | Risk |
|---|---|---|
| **Clock Fix (DB-rebuild)** | Set the RTC so the media DB stops rebuilding every boot — much faster startups | low |
| **Clean /contents Junk** | Strip Mac/Windows junk files the host wrote to the card | low |
| **Library Stats** | Track/format/hi-res/artist/album counts + size, from the media DB (read-only) | — |
| **Find Duplicates** | Scan the media DB for duplicate tracks + wasted space (read-only) | — |
| **Storage Info** | Report device + card usage (read-only) | — |
| **Boot Log** | Pull boot/hang logs (read-only) | — |

**⚙️ System**
| Module | What it does | Risk |
|---|---|---|
| **Walkman One Settings** | GUI over `settings.txt` (sound sig, region, gain, icon color…) | low |
| **NVP Flags** | Inspect NVP region/dest flags (read-only) | — |
| **Full Backup** | Snapshot all mod targets to disk (read-only) | — |
| **Reboot / Restart UI** | Reboot, or just respawn the player | low |

Top bar also has **Screenshot** (grabs the live framebuffer), **Save/Load Profile**, and **Revert All**.

## How it works
- `wlkmnstudio/formats/` — the reverse-engineered codecs: Sony `icx_bootanimation` (RGB565 BMP/desc/zip),
  the MTK `logo` container (0x200 offset-table, 565), font name-table impersonation, and the `viewstyle`
  QML palette rewriter (the text themer).
- `wlkmnstudio/module.py` — every mod is a module (`build → apply(backup→write→verify) ⇄ revert`) sharing
  one device engine + backup ledger.
- `wlkmnstudio/device.py` — adb wrapper (partition dd-staging, system-file install, framebuffer
  screenshot, md5 everywhere).
- Deeper mods (UI text palette, LDAC ABR) were found with **Ghidra** headless; see `../NOTES.md`.

## CLI
```bash
wlkmn list                 # all modules
wlkmn detect               # device / root / Walkman One status
wlkmn shot [out.png]       # grab the live screen
wlkmn preview <mod> k=v …  # dry-run
wlkmn apply   <mod> k=v …  # back up + flash
wlkmn revert  <mod> | revert-all
```

## Roadmap
EQ / DSP presets · force bit-perfect (Source Direct) · AAC max bitrate (AirPods) · live codec/bitrate
HUD · volume-bar + status-bar theming · web gallery at **wlkmn.studio**.

## Credits
Base firmware: **Mr Walkman / Walkman One**. Companion tooling: **unknown321 / wampy, fix-coverart, wbrt**.
Format references: `bgcngm/mtk-tools`, `rom1nux/mtkimg`, `roobscoob/SonyWalkmanFirmwarePatcher`,
`97lily/2019_android_walkman`.

## License
MIT.
