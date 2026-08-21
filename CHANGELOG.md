# Changelog

All notable changes to WLKMN Studio. Dates are ISO (YYYY-MM-DD).

## [0.1.0-beta] — 2026-08-21

First public beta. A native cross-platform GUI + CLI to safely theme and tweak a rooted
Sony Walkman One device — 22 modules, every write backed up and md5-verified, one-click Revert.

### Added
- **Fast Boot (skip DB scan)** — the flagship. Kills the "Creating Database" media scan that
  blocks *every* boot (the #1 A50/A55 complaint) **without** losing USB library scanning.
  Marker-gates the scan worker inside `libMediaStoreService.so` (a `.text` code-cave stub that
  `unlink()`s a marker — crawl if present, skip if not) plus a boot watcher that drops the marker
  when a USB mass-storage session is detected (`/contents` unmounts). Verified end-to-end on
  hardware (scan revision `1→2` after a transfer). Found + built with Ghidra headless.
- **🚑 Bootloop Recovery** — catches a rebooting device's brief adb window and restores a known-good
  player app with the correct `755 root:root` perms (a restore that drops the execute bit is itself
  the usual cause of the loop).
- **UI Text Themer** — recolor *all* main UI text + background (per element), via the QML `viewstyle`
  palette. **UI Accent + Icons**, **Alternate Theme**, **Marquee Scroll Speed**.
- **Audio**: LDAC 990 (no ABR downgrade), SBC-XQ bitpool, AirPods/A2DP RTP fix, live BT Monitor.
- **QOL/System**: Clock Fix, Clean /contents Junk, Library Stats, Find Duplicates, Storage Info,
  Boot Log, Walkman One Settings, NVP Flags, Full Backup, Reboot/Restart UI.
- Theme: Boot Animation, Power-on Splash, UI Font.
- Live **framebuffer screenshot**, Save/Load **profiles**, **Revert All**.
- A shared risk disclaimer across the GUI and CLI (accept once, either front-end).
- README screenshot gallery; regression tests for the engine + the Fast Boot patch bytes.

### Fixed
- `ledger.restore` now restores each file's **original mode** — it was hardcoding `644`, which
  dropped the execute bit on the player app and could bootloop on Revert.
- GUI: force-map the risk-agreement modal (a Toplevel transient to a withdrawn window never
  showed on macOS); white/high-contrast text (the default ttk theme rendered low-contrast).
- Fast Boot apply is now partial-state-safe (repairs a missing watcher/hook without re-backing-up
  an already-patched service).

### Notes
- Binpatch mods md5-verify their exact target and **abort cleanly on an unrecognized build** rather
  than risking a bad patch. Fast Boot currently targets the NW-A50 Walkman One `libMediaStoreService.so`.
