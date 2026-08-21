# WLKMN Studio (beta)

Design your Sony **NW-A50** Walkman's visual identity — **boot animation, power-on splash, UI font** —
from your own logo/GIF/colors, preview it, and flash it safely. A native cross-platform GUI (Mac +
Windows + Linux).

Built on top of **[Walkman One](https://www.mrwalkman.com/)** — it *requires* WM1 and a rooted device,
so it drives people to Mr Walkman's firmware, and it's designed to sit alongside
**[wampy](https://github.com/unknown321/wampy)** (which skins the player UI) rather than compete.

> Ships **no proprietary Sony files.** Every mod operates on *your* device's own assets + *your* uploads
> + bundled open-license fonts. Original files are backed up and md5-verified before anything is written.

## Requirements
- A **Sony NW-A50 series** Walkman running **Walkman One**, rooted, USB-debugging on.
- **adb** on your PATH (Android platform-tools).
- **Python 3.10+** with Tk (see `requirements.txt` for the per-OS Tk install).

## Install & run
```bash
pip install -r requirements.txt
python run.py            # or: python -m wlkmnstudio
```
> **macOS:** don't use the system `/usr/bin/python3` — it ships **Tk 8.5**, which renders **blank
> windows**. Use Homebrew (`brew install python@3.13 python-tk@3.13`, run with `python3.13`) or
> python.org. The app checks your Tk version at startup and tells you if it's too old.

## Modules (17)
Grouped by category in the app. Fill a mod's fields → **Preview** → **Apply** (backs up first, flashes,
md5-verifies) → **Revert** restores from the backup ledger (`~/.wlkmnstudio/backups`). Reboot to see it.

**🎨 Theme**
| Module | What it does | Risk |
|---|---|---|
| **Boot Animation** | Your own GIF, or a logo→line→waves intro | low |
| **Power-on Splash** | Replace the orange WALKMAN logo | med |
| **UI Font** | Swap SST / SST UI for a bundled or uploaded typeface | low |
| **UI Accent + Icons** | Recolor home icons + the EQ/streaming accent | high |
| **UI Text Themer** | Recolor *all* main UI text + background — any color, per element | high |

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
